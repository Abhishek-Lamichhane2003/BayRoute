from __future__ import annotations

from datetime import UTC, datetime

from google.transit import gtfs_realtime_pb2

from bayroute.db import Database
from bayroute.gtfs import ParsedFeed, parse_trip_updates, persist_parsed_feed
from bayroute.models import TransitObservation


def test_parse_trip_updates_extracts_delay_and_schedule() -> None:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1_800_000_000
    entity = feed.entity.add()
    entity.id = "entity-1"
    entity.trip_update.trip.trip_id = "trip-22"
    entity.trip_update.trip.route_id = "22"
    entity.trip_update.vehicle.id = "vehicle-7"
    update = entity.trip_update.stop_time_update.add()
    update.stop_id = "DIRIDON"
    update.stop_sequence = 4
    update.arrival.delay = 180
    update.arrival.time = 1_800_000_600

    parsed = parse_trip_updates(feed.SerializeToString())

    assert parsed.received_entities == 1
    assert parsed.feed_timestamp == datetime.fromtimestamp(1_800_000_000, UTC).replace(tzinfo=None)
    assert len(parsed.observations) == 1
    observation = parsed.observations[0]
    assert observation.route_id == "22"
    assert observation.stop_id == "DIRIDON"
    assert observation.delay_seconds == 180
    assert observation.predicted_arrival == datetime.fromtimestamp(1_800_000_600, UTC).replace(
        tzinfo=None
    )
    assert observation.scheduled_arrival == datetime.fromtimestamp(1_800_000_420, UTC).replace(
        tzinfo=None
    )


def test_parser_skips_entities_without_trip_updates() -> None:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.entity.add().id = "alert-only"

    parsed = parse_trip_updates(feed.SerializeToString())

    assert parsed.received_entities == 1
    assert parsed.observations == ()


def test_persisted_feed_is_idempotent(tmp_path) -> None:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1_800_000_000
    entity = feed.entity.add()
    entity.id = "entity-1"
    entity.trip_update.trip.trip_id = "trip-22"
    entity.trip_update.trip.route_id = "22"
    update = entity.trip_update.stop_time_update.add()
    update.stop_id = "DIRIDON"
    update.arrival.delay = 180
    parsed = parse_trip_updates(feed.SerializeToString())

    database = Database(f"sqlite:///{tmp_path / 'gtfs.db'}")
    database.create_schema()
    with database.session_factory() as session:
        first = persist_parsed_feed(session, parsed)
        second = persist_parsed_feed(session, parsed)
        assert session.query(TransitObservation).count() == 1
    database.engine.dispose()

    assert first.inserted_observations == 1
    assert first.skipped_observations == 0
    assert second.inserted_observations == 0
    assert second.skipped_observations == 1


def test_duplicate_event_inside_one_payload_is_skipped(tmp_path) -> None:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1_800_000_000
    entity = feed.entity.add()
    entity.id = "entity-1"
    entity.trip_update.trip.trip_id = "trip-22"
    entity.trip_update.trip.route_id = "22"
    update = entity.trip_update.stop_time_update.add()
    update.stop_id = "DIRIDON"
    update.arrival.delay = 180
    parsed = parse_trip_updates(feed.SerializeToString())
    duplicated = ParsedFeed(
        feed_timestamp=parsed.feed_timestamp,
        received_entities=2,
        observations=(parsed.observations[0], parsed.observations[0]),
    )

    database = Database(f"sqlite:///{tmp_path / 'duplicate.db'}")
    database.create_schema()
    with database.session_factory() as session:
        result = persist_parsed_feed(session, duplicated)
        assert session.query(TransitObservation).count() == 1
    database.engine.dispose()

    assert result.inserted_observations == 1
    assert result.skipped_observations == 1
