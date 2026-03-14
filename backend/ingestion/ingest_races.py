"""Ingest race metadata, sessions, driver_race_entries, and race results."""

import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DBSession

from backend.ingestion.helpers import (
    get_circuit_id,
    get_constructor_id,
    get_driver_id,
    get_season_id,
    time_str_to_ms,
)
from backend.ingestion.jolpica_client import JolpicaClient
from backend.models import (
    DriverRaceEntry,
    Race,
    RaceResult,
    Session,
)

logger = logging.getLogger(__name__)

SESSION_TYPES = ["FP1", "FP2", "FP3", "Q", "S", "R"]


def _parse_date(d: str | None):
    if not d:
        return None
    return date.fromisoformat(d)


def _parse_datetime(d: str | None, t: str | None):
    if not d:
        return None
    if t:
        # Strip trailing 'Z' if present
        t = t.rstrip("Z")
        return datetime.fromisoformat(f"{d}T{t}")
    return datetime.fromisoformat(d)


def upsert_races(session: DBSession, client: JolpicaClient, year: int) -> list[dict]:
    """Upsert races for a year, return the race list from Jolpica."""
    season_id = get_season_id(session, year)
    races_data = client.races(year)
    race_ids = {}

    for r in races_data:
        circuit_ref = r["Circuit"]["circuitId"]
        circuit_id = get_circuit_id(session, circuit_ref)
        round_num = int(r["round"])

        existing = session.execute(
            select(Race).where(Race.season_id == season_id, Race.round_number == round_num)
        ).scalar_one_or_none()

        if existing:
            existing.name = r["raceName"]
            existing.date = _parse_date(r.get("date"))
            existing.url = r.get("url")
            race_ids[round_num] = existing.id
        else:
            new_race = Race(
                season_id=season_id,
                circuit_id=circuit_id,
                round_number=round_num,
                name=r["raceName"],
                date=_parse_date(r.get("date")),
                url=r.get("url"),
            )
            session.add(new_race)
            session.flush()
            race_ids[round_num] = new_race.id

        # Create session stubs for each session type
        for stype in SESSION_TYPES:
            date_key = {
                "FP1": "FirstPractice", "FP2": "SecondPractice", "FP3": "ThirdPractice",
                "Q": "Qualifying", "S": "Sprint", "R": None,
            }[stype]

            if stype == "R":
                s_date = _parse_datetime(r.get("date"), r.get("time"))
            elif date_key and date_key in r:
                s_date = _parse_datetime(r[date_key].get("date"), r[date_key].get("time"))
            else:
                continue  # Skip if no data for this session (e.g., no Sprint)

            race_id = race_ids[round_num]
            existing_sess = session.execute(
                select(Session).where(Session.race_id == race_id, Session.session_type == stype)
            ).scalar_one_or_none()

            if not existing_sess:
                session.add(Session(race_id=race_id, session_type=stype, date=s_date))

    session.commit()
    logger.info("Upserted %d races for %d", len(races_data), year)
    return races_data


def upsert_race_results(session: DBSession, client: JolpicaClient, year: int, round_num: int, race_id: int):
    """Fetch and upsert race results, also creates driver_race_entries."""
    results = client.race_results(year, round_num)
    if not results:
        logger.warning("No race results for %d round %d", year, round_num)
        return

    for r in results:
        driver_ref = r["Driver"]["driverId"]
        constructor_ref = r["Constructor"]["constructorId"]
        driver_id = get_driver_id(session, driver_ref)
        constructor_id = get_constructor_id(session, constructor_ref)

        if not driver_id or not constructor_id:
            logger.warning("Missing driver/constructor: %s / %s", driver_ref, constructor_ref)
            continue

        driver_number = int(r.get("number", 0))

        # Driver race entry
        stmt = insert(DriverRaceEntry).values(
            race_id=race_id,
            driver_id=driver_id,
            constructor_id=constructor_id,
            driver_number=driver_number,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_driver_race_entry",
            set_={"constructor_id": stmt.excluded.constructor_id, "driver_number": stmt.excluded.driver_number},
        )
        session.execute(stmt)

        # Race result
        finish_pos = int(r["position"]) if r.get("position") and r["position"].isdigit() else None
        time_data = r.get("Time", {})
        time_ms = time_str_to_ms(time_data.get("time")) if time_data else None
        # For winner, Time.millis is total race time
        if time_data and time_data.get("millis"):
            time_ms = int(time_data["millis"])

        fastest_lap = r.get("FastestLap", {})
        fl_time = fastest_lap.get("Time", {}).get("time") if fastest_lap else None
        fl_lap = int(fastest_lap.get("lap", 0)) if fastest_lap and fastest_lap.get("lap") else None

        stmt = insert(RaceResult).values(
            race_id=race_id,
            driver_id=driver_id,
            constructor_id=constructor_id,
            grid_position=int(r.get("grid", 0)) or None,
            finish_position=finish_pos,
            position_text=r.get("positionText"),
            points=float(r.get("points", 0)),
            laps_completed=int(r.get("laps", 0)),
            status=r.get("status"),
            time_ms=time_ms,
            fastest_lap_time_ms=time_str_to_ms(fl_time),
            fastest_lap_number=fl_lap,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_race_result",
            set_={
                "grid_position": stmt.excluded.grid_position,
                "finish_position": stmt.excluded.finish_position,
                "points": stmt.excluded.points,
                "laps_completed": stmt.excluded.laps_completed,
                "status": stmt.excluded.status,
                "time_ms": stmt.excluded.time_ms,
                "fastest_lap_time_ms": stmt.excluded.fastest_lap_time_ms,
                "fastest_lap_number": stmt.excluded.fastest_lap_number,
            },
        )
        session.execute(stmt)

    session.commit()
    logger.info("Upserted %d race results for %d R%d", len(results), year, round_num)


def get_race_id(session: DBSession, year: int, round_num: int) -> int | None:
    season_id = get_season_id(session, year)
    return session.execute(
        select(Race.id).where(Race.season_id == season_id, Race.round_number == round_num)
    ).scalar_one_or_none()


def ingest_races(session: DBSession, client: JolpicaClient, year: int):
    """Full race ingestion: metadata + results for all rounds."""
    races_data = upsert_races(session, client, year)
    for r in races_data:
        round_num = int(r["round"])
        race_id = get_race_id(session, year, round_num)
        if race_id:
            upsert_race_results(session, client, year, round_num, race_id)
