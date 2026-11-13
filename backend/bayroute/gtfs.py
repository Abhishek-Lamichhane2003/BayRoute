from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from google.transit import gtfs_realtime_pb2
from sqlalchemy import select
from sqlalchemy.orm import Session

from bayroute.models import Route, Stop, TransitObservation


@dataclass(frozen=True)
class ParsedObservation:
    source_event_key: str
    captured_at: datetime
    trip_id: str
    vehicle_id: str | None
    route_id: str
    stop_id: str
    scheduled_arrival: datetime | None
    predicted_arrival: datetime | None
    delay_seconds: int
    previous_stop_delay_seconds: int


@dataclass(frozen=True)
class ParsedFeed:
    feed_timestamp: datetime | None
    received_entities: int
    observations: tuple[ParsedObservation, ...]


@dataclass(frozen=True)
class IngestStats:
    feed_timestamp: datetime | None
    received_entities: int
    inserted_observations: int
    skipped_observations: int


def parse_trip_updates(payload: bytes, captured_fallback: datetime | None = None) -> ParsedFeed:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(payload)
    fallback = captured_fallback or datetime.now(UTC).replace(tzinfo=None)
    feed_timestamp = (
        datetime.fromtimestamp(feed.header.timestamp, UTC).replace(tzinfo=None)
        if feed.header.HasField("timestamp") and feed.header.timestamp
        else None
    )
    captured_at = feed_timestamp or fallback
    parsed: list[ParsedObservation] = []

    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        update = entity.trip_update
        trip_id = update.trip.trip_id or entity.id
        route_id = update.trip.route_id or "UNKNOWN"
        vehicle_id = update.vehicle.id if update.HasField("vehicle") else None
        previous_delay = 0

        for sequence, stop_update in enumerate(update.stop_time_update):
            stop_id = stop_update.stop_id
            if not stop_id:
                continue

            delay: int | None = None
            predicted_arrival: datetime | None = None
            if stop_update.HasField("arrival"):
                arrival = stop_update.arrival
                if arrival.HasField("delay"):
                    delay = int(arrival.delay)
                if arrival.HasField("time") and arrival.time:
                    predicted_arrival = datetime.fromtimestamp(arrival.time, UTC).replace(
                        tzinfo=None
                    )
            if delay is None and stop_update.HasField("departure"):
                departure = stop_update.departure
                if departure.HasField("delay"):
                    delay = int(departure.delay)
                if predicted_arrival is None and departure.HasField("time") and departure.time:
                    predicted_arrival = datetime.fromtimestamp(departure.time, UTC).replace(
                        tzinfo=None
                    )
            if delay is None:
                continue

            scheduled_arrival = (
                predicted_arrival - timedelta(seconds=delay) if predicted_arrival else None
            )
            event_key = f"gtfs:{int(captured_at.timestamp())}:{entity.id}:{stop_id}:{sequence}"
            parsed.append(
                ParsedObservation(
                    source_event_key=event_key,
                    captured_at=captured_at,
                    trip_id=trip_id,
                    vehicle_id=vehicle_id,
                    route_id=route_id,
                    stop_id=stop_id,
                    scheduled_arrival=scheduled_arrival,
                    predicted_arrival=predicted_arrival,
                    delay_seconds=delay,
                    previous_stop_delay_seconds=previous_delay,
                )
            )
            previous_delay = delay

    return ParsedFeed(
        feed_timestamp=feed_timestamp,
        received_entities=len(feed.entity),
        observations=tuple(parsed),
    )


def persist_parsed_feed(session: Session, parsed: ParsedFeed) -> IngestStats:
    if not parsed.observations:
        return IngestStats(parsed.feed_timestamp, parsed.received_entities, 0, 0)

    keys = [observation.source_event_key for observation in parsed.observations]
    existing = set(
        session.scalars(
            select(TransitObservation.source_event_key).where(
                TransitObservation.source_event_key.in_(keys)
            )
        )
    )
    inserted = 0
    skipped = 0

    for observation in parsed.observations:
        if observation.source_event_key in existing:
            skipped += 1
            continue
        if session.get(Route, observation.route_id) is None:
            session.add(
                Route(
                    id=observation.route_id,
                    short_name=observation.route_id,
                    long_name=f"GTFS route {observation.route_id}",
                    color="#2A6F97",
                )
            )
        if session.get(Stop, observation.stop_id) is None:
            session.add(
                Stop(
                    id=observation.stop_id,
                    code=None,
                    name=f"GTFS stop {observation.stop_id}",
                    latitude=0,
                    longitude=0,
                )
            )
        session.flush()
        session.add(
            TransitObservation(
                source_event_key=observation.source_event_key,
                captured_at=observation.captured_at,
                trip_id=observation.trip_id,
                vehicle_id=observation.vehicle_id,
                route_id=observation.route_id,
                stop_id=observation.stop_id,
                latitude=None,
                longitude=None,
                scheduled_arrival=observation.scheduled_arrival,
                predicted_arrival=observation.predicted_arrival,
                delay_seconds=observation.delay_seconds,
                current_delay_seconds=observation.delay_seconds,
                previous_stop_delay_seconds=observation.previous_stop_delay_seconds,
                headway_minutes=15,
                source="gtfs_rt",
            )
        )
        # A malformed feed can repeat an entity within the same payload. Track
        # newly staged keys as well as keys that were already in the database.
        existing.add(observation.source_event_key)
        inserted += 1
    session.commit()
    return IngestStats(
        feed_timestamp=parsed.feed_timestamp,
        received_entities=parsed.received_entities,
        inserted_observations=inserted,
        skipped_observations=skipped,
    )


async def fetch_and_ingest(session: Session, url: str) -> IngestStats:
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        response = await client.get(url, headers={"User-Agent": "BayRoute/1.0"})
        response.raise_for_status()
    parsed = parse_trip_updates(response.content)
    return persist_parsed_feed(session, parsed)
