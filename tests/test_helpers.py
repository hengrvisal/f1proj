"""Tests for ingestion helper functions."""

from backend.ingestion.helpers import time_str_to_ms, timedelta_to_ms
from datetime import timedelta


def test_time_str_minutes_seconds():
    assert time_str_to_ms("1:23.456") == 83456


def test_time_str_seconds_only():
    assert time_str_to_ms("23.456") == 23456


def test_time_str_hours():
    assert time_str_to_ms("1:30:00.000") == 5400000


def test_time_str_none():
    assert time_str_to_ms(None) is None


def test_time_str_dnf():
    assert time_str_to_ms("DNF") is None


def test_time_str_plus_lap():
    assert time_str_to_ms("+1 Lap") is None


def test_timedelta_to_ms():
    td = timedelta(minutes=1, seconds=23, milliseconds=456)
    assert timedelta_to_ms(td) == 83456


def test_timedelta_to_ms_none():
    assert timedelta_to_ms(None) is None
