"""Ingest weather data from FastF1 session weather_data."""

import logging

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from backend.ingestion.fastf1_loader import load_session
from backend.models import Session, Weather

logger = logging.getLogger(__name__)


def get_session_id(db: DBSession, race_id: int, session_type: str) -> int | None:
    return db.execute(
        select(Session.id).where(Session.race_id == race_id, Session.session_type == session_type)
    ).scalar_one_or_none()


def ingest_weather(db: DBSession, year: int, round_num: int, race_id: int, session_type: str = "R"):
    session_id = get_session_id(db, race_id, session_type)
    if not session_id:
        return

    ff1_session = load_session(year, round_num, session_type)
    if ff1_session is None:
        return

    weather_df = ff1_session.weather_data
    if weather_df is None or weather_df.empty:
        logger.info("No weather data for %d R%d %s", year, round_num, session_type)
        return

    # Delete existing weather for this session (no unique constraint, simpler to replace)
    db.query(Weather).filter(Weather.session_id == session_id).delete()

    rows = []
    for _, w in weather_df.iterrows():
        timestamp = None
        if "Time" in w and pd.notna(w["Time"]):
            # Time is a timedelta from session start; combine with session date
            sess_obj = db.execute(select(Session).where(Session.id == session_id)).scalar_one()
            if sess_obj.date:
                timestamp = sess_obj.date + w["Time"]

        rows.append(Weather(
            session_id=session_id,
            timestamp=timestamp,
            air_temp=float(w["AirTemp"]) if pd.notna(w.get("AirTemp")) else None,
            track_temp=float(w["TrackTemp"]) if pd.notna(w.get("TrackTemp")) else None,
            humidity=float(w["Humidity"]) if pd.notna(w.get("Humidity")) else None,
            pressure=float(w["Pressure"]) if pd.notna(w.get("Pressure")) else None,
            wind_speed=float(w["WindSpeed"]) if pd.notna(w.get("WindSpeed")) else None,
            wind_direction=int(w["WindDirection"]) if pd.notna(w.get("WindDirection")) else None,
            rainfall=bool(w["Rainfall"]) if pd.notna(w.get("Rainfall")) else None,
        ))

    db.add_all(rows)
    db.commit()
    logger.info("Inserted %d weather rows for %d R%d %s", len(rows), year, round_num, session_type)
