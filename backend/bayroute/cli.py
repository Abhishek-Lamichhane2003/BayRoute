from __future__ import annotations

import argparse
import asyncio
import time

from bayroute.config import Settings
from bayroute.db import Database
from bayroute.gtfs import fetch_and_ingest
from bayroute.ml import DelayModelService
from bayroute.seed import seed_demo_data


def _database(settings: Settings) -> Database:
    database = Database(settings.database_url)
    database.create_schema()
    return database


def seed_command(settings: Settings) -> None:
    database = _database(settings)
    with database.session_factory() as session:
        inserted = seed_demo_data(session)
    print(f"Seed complete: {inserted} observations inserted")


def train_command(settings: Settings) -> None:
    database = _database(settings)
    service = DelayModelService()
    with database.session_factory() as session:
        metrics = service.train(session)
    path = service.save(settings.model_artifact_path)
    print(f"Model saved to {path}")
    print(metrics)


async def ingest_once(settings: Settings) -> None:
    url = settings.resolved_gtfs_url()
    if not url:
        raise SystemExit("GTFS_RT_TRIP_UPDATES_URL is not configured")
    database = _database(settings)
    with database.session_factory() as session:
        stats = await fetch_and_ingest(session, url)
    print(stats)


def collect_command(settings: Settings, interval_seconds: int) -> None:
    while True:
        try:
            asyncio.run(ingest_once(settings))
        except Exception as exc:  # noqa: BLE001 - collector must survive transient feed failures
            print(f"Collection failed: {exc}")
        time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="BayRoute data and model commands")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("seed", help="Insert deterministic demo data")
    subparsers.add_parser("train", help="Train and save the delay model")
    subparsers.add_parser("ingest-once", help="Fetch one configured GTFS-RT snapshot")
    collect = subparsers.add_parser("collect", help="Continuously collect GTFS-RT snapshots")
    collect.add_argument("--interval", type=int, default=60, help="Seconds between polls")
    args = parser.parse_args()
    settings = Settings.from_env()

    if args.command == "seed":
        seed_command(settings)
    elif args.command == "train":
        train_command(settings)
    elif args.command == "ingest-once":
        asyncio.run(ingest_once(settings))
    elif args.command == "collect":
        collect_command(settings, max(30, args.interval))


if __name__ == "__main__":
    main()
