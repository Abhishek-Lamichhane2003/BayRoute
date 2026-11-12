from __future__ import annotations

import math
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from bayroute.models import Route, Stop, TransitObservation

DEMO_ROUTES = (
    Route(id="22", short_name="22", long_name="Palo Alto - Eastridge", color="#E66A3C"),
    Route(id="522", short_name="522", long_name="Rapid Palo Alto - Eastridge", color="#1E6FA8"),
    Route(id="66", short_name="66", long_name="North Milpitas - Kaiser San Jose", color="#7C5CBF"),
    Route(id="GREEN", short_name="Green", long_name="Winchester - Old Ironsides", color="#16856C"),
)

DEMO_STOPS = (
    Stop(id="DIRIDON", code="6001", name="San Jose Diridon", latitude=37.3298, longitude=-121.9025),
    Stop(
        id="SANTA_CLARA",
        code="6002",
        name="Santa Clara & 1st",
        latitude=37.3375,
        longitude=-121.8903,
    ),
    Stop(
        id="JAPANTOWN", code="6003", name="Japantown / Ayer", latitude=37.3486, longitude=-121.8954
    ),
    Stop(
        id="BERRYESSA",
        code="6004",
        name="Berryessa Transit Center",
        latitude=37.3684,
        longitude=-121.8746,
    ),
    Stop(
        id="MILPITAS",
        code="6005",
        name="Milpitas Transit Center",
        latitude=37.4091,
        longitude=-121.8914,
    ),
    Stop(
        id="ALUM_ROCK",
        code="6006",
        name="Alum Rock Transit Center",
        latitude=37.3681,
        longitude=-121.8354,
    ),
    Stop(
        id="EASTRIDGE",
        code="6007",
        name="Eastridge Transit Center",
        latitude=37.3256,
        longitude=-121.8130,
    ),
    Stop(
        id="WINCHESTER",
        code="6008",
        name="Winchester Transit Center",
        latitude=37.2794,
        longitude=-121.9500,
    ),
)

ROUTE_STOPS = {
    "22": ["DIRIDON", "SANTA_CLARA", "JAPANTOWN", "BERRYESSA", "ALUM_ROCK", "EASTRIDGE"],
    "522": ["DIRIDON", "SANTA_CLARA", "BERRYESSA", "ALUM_ROCK", "EASTRIDGE"],
    "66": ["EASTRIDGE", "ALUM_ROCK", "BERRYESSA", "MILPITAS"],
    "GREEN": ["WINCHESTER", "DIRIDON", "SANTA_CLARA", "MILPITAS"],
}


def seed_demo_data(session: Session, days: int = 28) -> int:
    """Create deterministic, realistic demo observations for a zero-config run."""
    if session.scalar(select(func.count()).select_from(Route)):
        return 0

    routes = [
        Route(
            id=route.id,
            short_name=route.short_name,
            long_name=route.long_name,
            color=route.color,
        )
        for route in DEMO_ROUTES
    ]
    stop_rows = [
        Stop(
            id=stop.id,
            code=stop.code,
            name=stop.name,
            latitude=stop.latitude,
            longitude=stop.longitude,
        )
        for stop in DEMO_STOPS
    ]
    session.add_all(routes)
    session.add_all(stop_rows)
    session.flush()

    rng = random.Random(20271112)
    now = datetime.now(UTC).replace(tzinfo=None, second=0, microsecond=0)
    stops = {stop.id: stop for stop in stop_rows}
    route_bias = {"22": 70, "522": 20, "66": 45, "GREEN": 5}
    observations: list[TransitObservation] = []

    for day_offset in range(days, -1, -1):
        service_day = now - timedelta(days=day_offset)
        for route in routes:
            stop_ids = ROUTE_STOPS[route.id]
            for run_number, hour in enumerate((6, 8, 11, 14, 17, 20)):
                run_start = service_day.replace(hour=hour, minute=(run_number * 7) % 50)
                if run_start > now:
                    continue
                peak_penalty = 100 if hour in {8, 17} else 10
                weekend_relief = -25 if run_start.weekday() >= 5 else 0
                vehicle_id = f"DEMO-{route.id}-{day_offset:02d}-{run_number}"
                previous_delay = int(route_bias[route.id] + peak_penalty + weekend_relief)

                for stop_index, stop_id in enumerate(stop_ids):
                    captured_at = run_start + timedelta(minutes=stop_index * 9)
                    if captured_at > now:
                        continue
                    current_delay = int(previous_delay + rng.gauss(0, 55))
                    stop_pressure = 30 * math.sin((stop_index + 1) / len(stop_ids) * math.pi)
                    incident_delay = 300 if rng.random() < 0.035 else 0
                    actual_delay = int(
                        0.55 * current_delay
                        + 0.20 * previous_delay
                        + 0.35 * route_bias[route.id]
                        + 0.35 * peak_penalty
                        + weekend_relief
                        + stop_pressure
                        + incident_delay
                        + rng.gauss(0, 65)
                    )
                    actual_delay = max(-180, min(actual_delay, 1200))
                    scheduled = captured_at + timedelta(minutes=10)
                    stop = stops[stop_id]
                    observations.append(
                        TransitObservation(
                            source_event_key=(
                                f"demo:{route.id}:{day_offset}:{run_number}:{stop_index}"
                            ),
                            captured_at=captured_at,
                            trip_id=f"DEMO-TRIP-{route.id}-{day_offset:02d}-{run_number}",
                            vehicle_id=vehicle_id,
                            route_id=route.id,
                            stop_id=stop_id,
                            latitude=stop.latitude + rng.uniform(-0.0025, 0.0025),
                            longitude=stop.longitude + rng.uniform(-0.0025, 0.0025),
                            scheduled_arrival=scheduled,
                            predicted_arrival=scheduled + timedelta(seconds=actual_delay),
                            delay_seconds=actual_delay,
                            current_delay_seconds=current_delay,
                            previous_stop_delay_seconds=previous_delay,
                            headway_minutes=15.0 if route.id != "522" else 12.0,
                            source="demo",
                        )
                    )
                    previous_delay = actual_delay

    # Ensure every route has a fresh position for the live map.
    for route_index, route in enumerate(routes):
        stop_id = ROUTE_STOPS[route.id][min(1 + route_index, len(ROUTE_STOPS[route.id]) - 1)]
        stop = stops[stop_id]
        delay = 45 + route_index * 80
        captured_at = now - timedelta(minutes=route_index * 2)
        observations.append(
            TransitObservation(
                source_event_key=f"demo:live:{route.id}:{now.isoformat()}",
                captured_at=captured_at,
                trip_id=f"DEMO-LIVE-{route.id}",
                vehicle_id=f"VTA-{route.id}-{route_index + 21}",
                route_id=route.id,
                stop_id=stop_id,
                latitude=stop.latitude + 0.0015,
                longitude=stop.longitude - 0.0012,
                scheduled_arrival=captured_at + timedelta(minutes=8),
                predicted_arrival=captured_at + timedelta(minutes=8, seconds=delay),
                delay_seconds=delay,
                current_delay_seconds=max(0, delay - 30),
                previous_stop_delay_seconds=max(0, delay - 55),
                headway_minutes=12.0 if route.id == "522" else 15.0,
                source="demo",
            )
        )

    session.add_all(observations)
    session.commit()
    return len(observations)
