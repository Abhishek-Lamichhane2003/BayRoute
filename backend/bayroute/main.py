from __future__ import annotations

from collections import defaultdict
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from datetime import timedelta

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from google.protobuf.message import DecodeError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from bayroute.config import Settings
from bayroute.db import Database
from bayroute.gtfs import fetch_and_ingest
from bayroute.ml import DelayModelService, ModelNotReadyError
from bayroute.models import Route, Stop, TransitObservation
from bayroute.schemas import (
    AlertOut,
    IngestResult,
    LiveVehicleOut,
    ModelMetricsOut,
    OverviewOut,
    PredictionRequest,
    PredictionResponse,
    ReliabilityPoint,
    RouteOut,
    StopOut,
)
from bayroute.seed import seed_demo_data


def create_app(
    *,
    database_url: str | None = None,
    auto_seed: bool | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    app_settings = settings or Settings.from_env()
    if database_url is not None or auto_seed is not None:
        app_settings = Settings(
            database_url=database_url or app_settings.database_url,
            cors_origins=app_settings.cors_origins,
            auto_seed_demo=app_settings.auto_seed_demo if auto_seed is None else auto_seed,
            model_artifact_path=app_settings.model_artifact_path,
            gtfs_rt_trip_updates_url=app_settings.gtfs_rt_trip_updates_url,
            transit_511_api_key=app_settings.transit_511_api_key,
            collector_key=app_settings.collector_key,
        )

    database = Database(app_settings.database_url)
    model_service = DelayModelService()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        database.create_schema()
        with database.session_factory() as session:
            if app_settings.auto_seed_demo:
                seed_demo_data(session)
            try:
                if not model_service.load(app_settings.model_artifact_path):
                    model_service.train(session)
            except ModelNotReadyError:
                # The API can collect data before enough rows exist to train.
                pass
        try:
            yield
        finally:
            database.engine.dispose()

    api = FastAPI(
        title="BayRoute API",
        version="1.0.0",
        description="Transit reliability analytics and delay prediction from GTFS-Realtime data.",
        lifespan=lifespan,
    )
    api.state.database = database
    api.state.model_service = model_service
    api.state.settings = app_settings
    api.add_middleware(
        CORSMiddleware,
        allow_origins=list(app_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    def get_session(request: Request) -> Iterator[Session]:
        with request.app.state.database.session_factory() as session:
            yield session

    def get_model(request: Request) -> DelayModelService:
        return request.app.state.model_service

    @api.get("/api/health")
    def health(model: DelayModelService = Depends(get_model)) -> dict[str, str]:
        return {
            "status": "ok",
            "model": "ready" if model.pipeline is not None else "collecting_data",
        }

    @api.get("/api/routes", response_model=list[RouteOut])
    def routes(session: Session = Depends(get_session)) -> list[Route]:
        return list(session.scalars(select(Route).order_by(Route.short_name)))

    @api.get("/api/stops", response_model=list[StopOut])
    def stops(session: Session = Depends(get_session)) -> list[Stop]:
        return list(session.scalars(select(Stop).order_by(Stop.name)))

    @api.get("/api/overview", response_model=OverviewOut)
    def overview(session: Session = Depends(get_session)) -> OverviewOut:
        last_updated = session.scalar(select(func.max(TransitObservation.captured_at)))
        if last_updated is None:
            raise HTTPException(status_code=404, detail="No transit observations are available")
        recent_start = last_updated - timedelta(hours=24)
        recent = list(
            session.scalars(
                select(TransitObservation).where(TransitObservation.captured_at >= recent_start)
            )
        )
        delays = [observation.delay_seconds for observation in recent]
        average_delay = sum(delays) / len(delays) if delays else 0
        on_time = sum(abs(delay) <= 300 for delay in delays) / len(delays) * 100 if delays else 0
        active_routes = len({observation.route_id for observation in recent})
        tracked_vehicles = len(
            {observation.vehicle_id for observation in recent if observation.vehicle_id}
        )
        sources = set(session.scalars(select(TransitObservation.source).distinct()))
        data_mode = "live" if any(source != "demo" for source in sources) else "demo"
        alerts: list[AlertOut] = []
        route_delays: dict[str, list[int]] = defaultdict(list)
        for observation in recent:
            route_delays[observation.route_id].append(observation.delay_seconds)
        for route_id, values in route_delays.items():
            route_average = sum(values) / len(values)
            if route_average > 300:
                alerts.append(
                    AlertOut(
                        severity="warning",
                        title=f"Route {route_id} running behind",
                        detail=f"Average delay is {round(route_average / 60, 1)} minutes.",
                    )
                )
        if not alerts:
            alerts.append(
                AlertOut(
                    severity="info",
                    title="Network operating normally",
                    detail="No route-level delay threshold has been exceeded.",
                )
            )
        return OverviewOut(
            active_routes=active_routes,
            tracked_vehicles=tracked_vehicles,
            average_delay_seconds=round(average_delay, 1),
            on_time_percent=round(on_time, 1),
            data_mode=data_mode,
            last_updated=last_updated,
            alerts=alerts[:3],
        )

    @api.get("/api/live", response_model=list[LiveVehicleOut])
    def live_vehicles(
        limit: int = Query(default=12, ge=1, le=100),
        session: Session = Depends(get_session),
    ) -> list[LiveVehicleOut]:
        observations = list(
            session.scalars(
                select(TransitObservation)
                .where(
                    TransitObservation.vehicle_id.is_not(None),
                    TransitObservation.latitude.is_not(None),
                    TransitObservation.longitude.is_not(None),
                )
                .order_by(TransitObservation.captured_at.desc())
                .limit(500)
            )
        )
        route_map = {route.id: route for route in session.scalars(select(Route))}
        stop_map = {stop.id: stop for stop in session.scalars(select(Stop))}
        seen: set[str] = set()
        result: list[LiveVehicleOut] = []
        for observation in observations:
            vehicle_id = observation.vehicle_id or "unknown"
            if vehicle_id in seen or not observation.latitude or not observation.longitude:
                continue
            seen.add(vehicle_id)
            route = route_map[observation.route_id]
            stop = stop_map[observation.stop_id]
            result.append(
                LiveVehicleOut(
                    vehicle_id=vehicle_id,
                    route_id=route.id,
                    route_name=route.short_name,
                    route_color=route.color,
                    stop_id=stop.id,
                    stop_name=stop.name,
                    latitude=observation.latitude,
                    longitude=observation.longitude,
                    delay_seconds=observation.delay_seconds,
                    captured_at=observation.captured_at,
                )
            )
            if len(result) >= limit:
                break
        return result

    @api.get("/api/reliability", response_model=list[ReliabilityPoint])
    def reliability(
        days: int = Query(default=28, ge=1, le=365),
        session: Session = Depends(get_session),
    ) -> list[ReliabilityPoint]:
        latest = session.scalar(select(func.max(TransitObservation.captured_at)))
        if latest is None:
            return []
        observations = list(
            session.scalars(
                select(TransitObservation).where(
                    TransitObservation.captured_at >= latest - timedelta(days=days)
                )
            )
        )
        route_map = {route.id: route for route in session.scalars(select(Route))}
        grouped: dict[str, list[int]] = defaultdict(list)
        for observation in observations:
            grouped[observation.route_id].append(observation.delay_seconds)
        points: list[ReliabilityPoint] = []
        for route_id, delays in grouped.items():
            on_time = sum(abs(delay) <= 300 for delay in delays) / len(delays) * 100
            route = route_map[route_id]
            points.append(
                ReliabilityPoint(
                    route_id=route_id,
                    route_name=route.short_name,
                    color=route.color,
                    samples=len(delays),
                    average_delay_seconds=round(sum(delays) / len(delays), 1),
                    on_time_percent=round(on_time, 1),
                    reliability_score=round(max(0, min(100, on_time)), 1),
                )
            )
        return sorted(points, key=lambda point: point.reliability_score, reverse=True)

    @api.get("/api/model/metrics", response_model=ModelMetricsOut)
    def model_metrics(model: DelayModelService = Depends(get_model)) -> dict[str, object]:
        if model.metrics is None:
            raise HTTPException(status_code=503, detail="Model is still collecting training data")
        return model.metrics

    @api.post("/api/predict", response_model=PredictionResponse)
    def predict(
        payload: PredictionRequest,
        session: Session = Depends(get_session),
        model: DelayModelService = Depends(get_model),
    ) -> dict[str, object]:
        if session.get(Route, payload.route_id) is None:
            raise HTTPException(status_code=404, detail="Unknown route")
        if session.get(Stop, payload.stop_id) is None:
            raise HTTPException(status_code=404, detail="Unknown stop")
        try:
            return model.predict(payload)
        except ModelNotReadyError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @api.post("/api/ingest/gtfs", response_model=IngestResult)
    async def ingest_gtfs(
        request: Request,
        x_collector_key: str | None = Header(default=None),
        session: Session = Depends(get_session),
    ) -> IngestResult:
        settings_value: Settings = request.app.state.settings
        if not settings_value.collector_key:
            raise HTTPException(
                status_code=503,
                detail="COLLECTOR_KEY is not configured",
            )
        if x_collector_key != settings_value.collector_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid key")
        url = settings_value.resolved_gtfs_url()
        if not url:
            raise HTTPException(
                status_code=503,
                detail="GTFS_RT_TRIP_UPDATES_URL is not configured",
            )
        try:
            stats = await fetch_and_ingest(session, url)
        except (DecodeError, httpx.HTTPError, ValueError, OSError) as exc:
            raise HTTPException(status_code=502, detail="GTFS feed could not be processed") from exc
        return IngestResult(
            received_entities=stats.received_entities,
            inserted_observations=stats.inserted_observations,
            skipped_observations=stats.skipped_observations,
            feed_timestamp=stats.feed_timestamp,
        )

    return api


app = create_app()
