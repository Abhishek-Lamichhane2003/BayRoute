from __future__ import annotations

from bayroute.config import Settings


def test_settings_resolve_api_key_placeholder(monkeypatch) -> None:
    monkeypatch.setenv(
        "GTFS_RT_TRIP_UPDATES_URL",
        "https://example.test/trip-updates?api_key={api_key}",
    )
    monkeypatch.setenv("TRANSIT_511_API_KEY", "secret-token")

    settings = Settings.from_env()

    assert settings.resolved_gtfs_url() == "https://example.test/trip-updates?api_key=secret-token"


def test_settings_parse_boolean_and_origins(monkeypatch) -> None:
    monkeypatch.setenv("AUTO_SEED_DEMO", "off")
    monkeypatch.setenv("CORS_ORIGINS", "https://one.test, https://two.test")

    settings = Settings.from_env()

    assert settings.auto_seed_demo is False
    assert settings.cors_origins == ("https://one.test", "https://two.test")
