"""Tests for ORM model registration."""

from backend.models import Base


def test_all_16_tables_registered():
    tables = list(Base.metadata.tables.keys())
    assert len(tables) == 16


def test_expected_tables_present():
    tables = set(Base.metadata.tables.keys())
    expected = {
        "seasons", "circuits", "constructors", "drivers",
        "races", "sessions", "driver_race_entries",
        "race_results", "qualifying_results",
        "laps", "pit_stops", "tyre_stints", "weather",
        "telemetry_samples", "race_control_messages", "team_radio",
    }
    assert expected == tables
