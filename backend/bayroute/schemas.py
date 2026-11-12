from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RouteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    short_name: str
    long_name: str
    color: str


class StopOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str | None
    name: str
    latitude: float
    longitude: float


class LiveVehicleOut(BaseModel):
    vehicle_id: str
    route_id: str
    route_name: str
    route_color: str
    stop_id: str
    stop_name: str
    latitude: float
    longitude: float
    delay_seconds: int
    captured_at: datetime


class PredictionRequest(BaseModel):
    route_id: str
    stop_id: str
    prediction_time: datetime
    current_delay_seconds: int = Field(default=0, ge=-1800, le=7200)
    previous_stop_delay_seconds: int = Field(default=0, ge=-1800, le=7200)
    headway_minutes: float = Field(default=15.0, ge=1, le=180)


class PredictionResponse(BaseModel):
    predicted_delay_seconds: int
    predicted_delay_minutes: float
    status: str
    interval_low_seconds: int
    interval_high_seconds: int
    model_version: str


class ModelMetricsOut(BaseModel):
    trained_records: int
    test_records: int
    mae_seconds: float
    baseline_mae_seconds: float
    improvement_percent: float
    within_two_minutes_percent: float
    residual_p90_seconds: float
    trained_at: datetime
    model_version: str


class ReliabilityPoint(BaseModel):
    route_id: str
    route_name: str
    color: str
    samples: int
    average_delay_seconds: float
    on_time_percent: float
    reliability_score: float


class AlertOut(BaseModel):
    severity: str
    title: str
    detail: str


class OverviewOut(BaseModel):
    active_routes: int
    tracked_vehicles: int
    average_delay_seconds: float
    on_time_percent: float
    data_mode: str
    last_updated: datetime
    alerts: list[AlertOut]


class IngestResult(BaseModel):
    received_entities: int
    inserted_observations: int
    skipped_observations: int
    feed_timestamp: datetime | None
