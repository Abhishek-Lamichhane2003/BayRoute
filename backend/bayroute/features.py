from __future__ import annotations

import math
from datetime import datetime

import pandas as pd

CATEGORICAL_FEATURES = ["route_id", "stop_id"]
NUMERIC_FEATURES = [
    "hour_sin",
    "hour_cos",
    "weekday_sin",
    "weekday_cos",
    "is_peak",
    "current_delay_seconds",
    "previous_stop_delay_seconds",
    "headway_minutes",
]
MODEL_FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES


def temporal_features(moment: datetime) -> dict[str, float]:
    hour = moment.hour + moment.minute / 60
    weekday = moment.weekday()
    return {
        "hour_sin": math.sin(2 * math.pi * hour / 24),
        "hour_cos": math.cos(2 * math.pi * hour / 24),
        "weekday_sin": math.sin(2 * math.pi * weekday / 7),
        "weekday_cos": math.cos(2 * math.pi * weekday / 7),
        "is_peak": float((7 <= hour < 10) or (16 <= hour < 19)),
    }


def feature_row(
    *,
    route_id: str,
    stop_id: str,
    prediction_time: datetime,
    current_delay_seconds: int,
    previous_stop_delay_seconds: int,
    headway_minutes: float,
) -> dict[str, str | float | int]:
    return {
        "route_id": route_id,
        "stop_id": stop_id,
        **temporal_features(prediction_time),
        "current_delay_seconds": current_delay_seconds,
        "previous_stop_delay_seconds": previous_stop_delay_seconds,
        "headway_minutes": headway_minutes,
    }


def observations_to_frame(observations: list[object]) -> pd.DataFrame:
    rows: list[dict[str, str | float | int | datetime]] = []
    for observation in observations:
        rows.append(
            {
                **feature_row(
                    route_id=observation.route_id,
                    stop_id=observation.stop_id,
                    prediction_time=observation.captured_at,
                    current_delay_seconds=observation.current_delay_seconds,
                    previous_stop_delay_seconds=observation.previous_stop_delay_seconds,
                    headway_minutes=observation.headway_minutes,
                ),
                "captured_at": observation.captured_at,
                "target_delay_seconds": observation.delay_seconds,
            }
        )
    return pd.DataFrame(rows).sort_values("captured_at").reset_index(drop=True)
