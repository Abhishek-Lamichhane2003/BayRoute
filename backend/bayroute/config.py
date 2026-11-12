from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    cors_origins: tuple[str, ...]
    auto_seed_demo: bool
    model_artifact_path: str
    gtfs_rt_trip_updates_url: str | None
    transit_511_api_key: str | None
    collector_key: str | None

    @classmethod
    def from_env(cls) -> Settings:
        origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:///./bayroute.db"),
            cors_origins=tuple(origin.strip() for origin in origins.split(",") if origin.strip()),
            auto_seed_demo=_as_bool(os.getenv("AUTO_SEED_DEMO"), True),
            model_artifact_path=os.getenv("MODEL_ARTIFACT_PATH", "./artifacts/delay_model.joblib"),
            gtfs_rt_trip_updates_url=os.getenv("GTFS_RT_TRIP_UPDATES_URL") or None,
            transit_511_api_key=os.getenv("TRANSIT_511_API_KEY") or None,
            collector_key=os.getenv("COLLECTOR_KEY") or None,
        )

    def resolved_gtfs_url(self) -> str | None:
        if not self.gtfs_rt_trip_updates_url:
            return None
        return self.gtfs_rt_trip_updates_url.replace("{api_key}", self.transit_511_api_key or "")
