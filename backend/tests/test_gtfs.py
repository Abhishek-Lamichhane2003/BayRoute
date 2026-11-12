from __future__ import annotations

from datetime import UTC, datetime

from google.transit import gtfs_realtime_pb2

from bayroute.gtfs import parse_trip_updates


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
