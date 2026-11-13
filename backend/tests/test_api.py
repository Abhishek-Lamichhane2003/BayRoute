from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from bayroute.config import Settings
from bayroute.main import create_app


def test_demo_api_end_to_end(tmp_path) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'test.db'}", auto_seed=True)

    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok", "model": "ready"}

        routes = client.get("/api/routes")
        assert routes.status_code == 200
        assert len(routes.json()) == 4

        overview = client.get("/api/overview")
        assert overview.status_code == 200
        assert overview.json()["data_mode"] == "demo"
        assert overview.json()["active_routes"] == 4

        reliability = client.get("/api/reliability")
        assert reliability.status_code == 200
        assert len(reliability.json()) == 4

        live = client.get("/api/live")
        assert live.status_code == 200
        assert len(live.json()) >= 4

        metrics = client.get("/api/model/metrics")
        assert metrics.status_code == 200
        assert metrics.json()["trained_records"] > 500
        assert metrics.json()["mae_seconds"] < metrics.json()["baseline_mae_seconds"]

        prediction = client.post(
            "/api/predict",
            json={
                "route_id": "22",
                "stop_id": "DIRIDON",
                "prediction_time": datetime(2026, 11, 12, 17, 30).isoformat(),
                "current_delay_seconds": 240,
                "previous_stop_delay_seconds": 180,
                "headway_minutes": 15,
            },
        )
        assert prediction.status_code == 200
        body = prediction.json()
        assert body["model_version"] == "bayroute-hgbt-v1"
        assert body["interval_low_seconds"] < body["interval_high_seconds"]


def test_prediction_rejects_unknown_route(tmp_path) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'test.db'}", auto_seed=True)
    with TestClient(app) as client:
        response = client.post(
            "/api/predict",
            json={
                "route_id": "NOT-A-ROUTE",
                "stop_id": "DIRIDON",
                "prediction_time": "2026-11-12T12:00:00",
            },
        )
    assert response.status_code == 404
    assert response.json()["detail"] == "Unknown route"


def test_ingest_endpoint_requires_collector_configuration(tmp_path) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'test.db'}", auto_seed=False)
    with TestClient(app) as client:
        response = client.post("/api/ingest/gtfs")

    assert response.status_code == 503
    assert response.json()["detail"] == "COLLECTOR_KEY is not configured"


def test_ingest_endpoint_rejects_invalid_key(tmp_path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        cors_origins=("http://localhost:3000",),
        auto_seed_demo=False,
        model_artifact_path=str(tmp_path / "model.joblib"),
        gtfs_rt_trip_updates_url="https://example.test/feed.pb",
        transit_511_api_key=None,
        collector_key="expected-key",
    )
    app = create_app(settings=settings)
    with TestClient(app) as client:
        response = client.post(
            "/api/ingest/gtfs",
            headers={"x-collector-key": "wrong-key"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid key"
