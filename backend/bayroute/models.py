from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from bayroute.db import Base


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    short_name: Mapped[str] = mapped_column(String(32), index=True)
    long_name: Mapped[str] = mapped_column(String(160))
    color: Mapped[str] = mapped_column(String(7), default="#167A6A")


class Stop(Base):
    __tablename__ = "stops"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)


class TransitObservation(Base):
    __tablename__ = "transit_observations"
    __table_args__ = (
        UniqueConstraint("source_event_key", name="uq_observation_source_event"),
        Index("ix_observation_route_time", "route_id", "captured_at"),
        Index("ix_observation_stop_time", "stop_id", "captured_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_event_key: Mapped[str] = mapped_column(String(220))
    captured_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    trip_id: Mapped[str] = mapped_column(String(100), index=True)
    vehicle_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    route_id: Mapped[str] = mapped_column(ForeignKey("routes.id"), index=True)
    stop_id: Mapped[str] = mapped_column(ForeignKey("stops.id"), index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    scheduled_arrival: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    predicted_arrival: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delay_seconds: Mapped[int] = mapped_column(Integer)
    current_delay_seconds: Mapped[int] = mapped_column(Integer, default=0)
    previous_stop_delay_seconds: Mapped[int] = mapped_column(Integer, default=0)
    headway_minutes: Mapped[float] = mapped_column(Float, default=15.0)
    source: Mapped[str] = mapped_column(String(32), default="demo")
