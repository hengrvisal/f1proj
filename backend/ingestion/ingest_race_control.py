"""Ingest race control messages and team radio from OpenF1."""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from backend.ingestion.helpers import resolve_driver_id
from backend.ingestion.openf1_client import OpenF1Client
from backend.models import Race, RaceControlMessage, Session, TeamRadio

logger = logging.getLogger(__name__)

# Map OpenF1 session type names to our codes
OPENF1_SESSION_MAP = {
    "Race": "R",
    "Qualifying": "Q",
    "Sprint": "S",
    "Sprint Qualifying": "SQ",
    "Sprint Shootout": "SQ",
    "Practice 1": "FP1",
    "Practice 2": "FP2",
    "Practice 3": "FP3",
}


def _parse_ts(ts_str: str | None) -> datetime | None:
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def backfill_openf1_keys(db: DBSession, openf1: OpenF1Client, year: int):
    """Match OpenF1 meetings/sessions to our races/sessions and store keys."""
    meetings = openf1.meetings(year)
    races = db.execute(
        select(Race).join(Race.season).where(Race.season.has(year=year))
    ).scalars().all()

    # Match by date
    race_by_date = {str(r.date): r for r in races if r.date}

    for m in meetings:
        meeting_date = m.get("date_start", "")[:10]
        # Try matching by approximate date (meeting can span multiple days)
        matched_race = None
        for race in races:
            if race.date and abs((race.date - datetime.fromisoformat(meeting_date).date()).days) <= 3:
                matched_race = race
                break

        if not matched_race:
            continue

        matched_race.openf1_meeting_key = m["meeting_key"]

        # Match sessions
        of1_sessions = openf1.sessions(m["meeting_key"])
        our_sessions = db.execute(
            select(Session).where(Session.race_id == matched_race.id)
        ).scalars().all()

        for of1_s in of1_sessions:
            of1_type = OPENF1_SESSION_MAP.get(of1_s.get("session_name", ""))
            if not of1_type:
                continue
            for our_s in our_sessions:
                if our_s.session_type == of1_type:
                    our_s.openf1_session_key = of1_s["session_key"]
                    break

    db.commit()
    logger.info("Backfilled OpenF1 keys for %d", year)


def ingest_race_control_messages(db: DBSession, openf1: OpenF1Client, session_id: int, openf1_session_key: int):
    messages = openf1.race_control(openf1_session_key)
    if not messages:
        return

    # Delete existing and re-insert (no unique constraint)
    db.query(RaceControlMessage).filter(RaceControlMessage.session_id == session_id).delete()

    rows = []
    for m in messages:
        rows.append(RaceControlMessage(
            session_id=session_id,
            timestamp=_parse_ts(m.get("date")),
            lap_number=m.get("lap_number"),
            category=m.get("category"),
            flag=m.get("flag"),
            message=m.get("message"),
            driver_number=m.get("driver_number"),
        ))

    db.add_all(rows)
    db.commit()
    logger.info("Inserted %d race control messages for session %d", len(rows), session_id)


def ingest_team_radio(db: DBSession, openf1: OpenF1Client, session_id: int, openf1_session_key: int):
    radios = openf1.team_radio(openf1_session_key)
    if not radios:
        return

    # Delete existing and re-insert
    db.query(TeamRadio).filter(TeamRadio.session_id == session_id).delete()

    rows = []
    for r in radios:
        driver_num = r.get("driver_number")
        driver_id = resolve_driver_id(db, number=driver_num) if driver_num else None
        if not driver_id:
            continue

        rows.append(TeamRadio(
            session_id=session_id,
            driver_id=driver_id,
            timestamp=_parse_ts(r.get("date")),
            recording_url=r.get("recording_url"),
        ))

    db.add_all(rows)
    db.commit()
    logger.info("Inserted %d team radio entries for session %d", len(rows), session_id)
