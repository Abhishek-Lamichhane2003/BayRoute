from __future__ import annotations

from datetime import datetime

import pytest

from bayroute.features import feature_row, temporal_features


def test_temporal_features_mark_commute_period() -> None:
    morning = temporal_features(datetime(2026, 11, 12, 8, 30))
    midday = temporal_features(datetime(2026, 11, 12, 13, 0))

    assert morning["is_peak"] == 1.0
    assert midday["is_peak"] == 0.0
    assert morning["hour_sin"] == pytest.approx(0.793353, abs=1e-5)


def test_feature_row_keeps_operational_inputs() -> None:
    row = feature_row(
        route_id="22",
        stop_id="DIRIDON",
        prediction_time=datetime(2026, 11, 12, 17, 10),
        current_delay_seconds=180,
        previous_stop_delay_seconds=120,
        headway_minutes=15,
    )

    assert row["route_id"] == "22"
    assert row["stop_id"] == "DIRIDON"
    assert row["current_delay_seconds"] == 180
    assert row["is_peak"] == 1.0
