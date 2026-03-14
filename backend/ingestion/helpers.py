"""Shared helpers for ingestion modules."""

import re
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from backend.models import Circuit, Constructor, Driver, Season


def time_str_to_ms(time_str: str | None) -> int | None:
    """Convert a time string like '1:23.456' or '23.456' to milliseconds."""
    if not time_str:
        return None
    # Handle '+1 Lap', 'DNF', etc.
    if not re.match(r'^[\d:.]+$', time_str):
        return None
    parts = time_str.split(":")
    if len(parts) == 2:
        minutes = int(parts[0])
        seconds = float(parts[1])
        return int((minutes * 60 + seconds) * 1000)
    elif len(parts) == 1:
        return int(float(parts[0]) * 1000)
    elif len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return int((hours * 3600 + minutes * 60 + seconds) * 1000)
    return None


def timedelta_to_ms(td) -> int | None:
    """Convert a pandas Timedelta or datetime.timedelta to milliseconds."""
    if td is None or (hasattr(td, 'total_seconds') is False):
        return None
    try:
        import pandas as pd
        if pd.isna(td):
            return None
    except (ImportError, TypeError, ValueError):
        pass
    return int(td.total_seconds() * 1000)


def get_season_id(session: DBSession, year: int) -> int:
    return session.execute(select(Season.id).where(Season.year == year)).scalar_one()


def get_circuit_id(session: DBSession, circuit_ref: str) -> int:
    return session.execute(select(Circuit.id).where(Circuit.circuit_ref == circuit_ref)).scalar_one()


def get_driver_id(session: DBSession, driver_ref: str) -> int | None:
    return session.execute(select(Driver.id).where(Driver.driver_ref == driver_ref)).scalar_one_or_none()


def get_driver_id_by_number(session: DBSession, number: int) -> int | None:
    results = session.execute(select(Driver.id).where(Driver.permanent_number == number)).scalars().all()
    return results[0] if len(results) == 1 else None


def get_driver_id_by_code(session: DBSession, code: str) -> int | None:
    results = session.execute(select(Driver.id).where(Driver.code == code)).scalars().all()
    return results[0] if len(results) == 1 else None


def get_constructor_id(session: DBSession, constructor_ref: str) -> int | None:
    return session.execute(select(Constructor.id).where(Constructor.constructor_ref == constructor_ref)).scalar_one_or_none()


def resolve_driver_id(session: DBSession, *, driver_ref: str | None = None, number: int | None = None, code: str | None = None) -> int | None:
    """Try multiple strategies to resolve a driver to our DB id.
    Prefers code (unique) over number (can have duplicates).
    """
    if driver_ref:
        did = get_driver_id(session, driver_ref)
        if did:
            return did
    if code:
        did = get_driver_id_by_code(session, code)
        if did:
            return did
    if number:
        did = get_driver_id_by_number(session, number)
        if did:
            return did
    return None
