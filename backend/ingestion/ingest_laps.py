"""Ingest lap data from FastF1."""

import logging
import math

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DBSession

from backend.ingestion.fastf1_loader import load_session
from backend.ingestion.helpers import resolve_driver_id, timedelta_to_ms
from backend.models import Lap, Session

logger = logging.getLogger(__name__)


def get_session_id(db: DBSession, race_id: int, session_type: str) -> int | None:
    return db.execute(
        select(Session.id).where(Session.race_id == race_id, Session.session_type == session_type)
    ).scalar_one_or_none()


def ingest_laps(db: DBSession, year: int, round_num: int, race_id: int, session_type: str = "R"):
    session_id = get_session_id(db, race_id, session_type)
    if not session_id:
        logger.warning("No session found for race %d type %s", race_id, session_type)
        return

    ff1_session = load_session(year, round_num, session_type)
    if ff1_session is None:
        return

    laps_df = ff1_session.laps
    if laps_df is None or laps_df.empty:
        logger.warning("No laps data for %d R%d %s", year, round_num, session_type)
        return

    rows = []
    for _, lap in laps_df.iterrows():
        driver_number = int(lap["DriverNumber"]) if pd.notna(lap.get("DriverNumber")) else None
        driver_code = str(lap.get("Driver", "")) if pd.notna(lap.get("Driver")) else None
        driver_id = resolve_driver_id(db, number=driver_number, code=driver_code)

        if not driver_id:
            logger.debug("Could not resolve driver: number=%s code=%s", driver_number, driver_code)
            continue

        lap_num = int(lap["LapNumber"]) if pd.notna(lap.get("LapNumber")) else None
        if not lap_num:
            continue

        rows.append({
            "session_id": session_id,
            "driver_id": driver_id,
            "lap_number": lap_num,
            "lap_time_ms": timedelta_to_ms(lap.get("LapTime")),
            "sector1_ms": timedelta_to_ms(lap.get("Sector1Time")),
            "sector2_ms": timedelta_to_ms(lap.get("Sector2Time")),
            "sector3_ms": timedelta_to_ms(lap.get("Sector3Time")),
            "compound": str(lap.get("Compound")) if pd.notna(lap.get("Compound")) else None,
            "tyre_life": int(lap["TyreLife"]) if pd.notna(lap.get("TyreLife")) else None,
            "is_pit_in_lap": bool(lap.get("PitInTime") is not None and pd.notna(lap.get("PitInTime"))),
            "is_pit_out_lap": bool(lap.get("PitOutTime") is not None and pd.notna(lap.get("PitOutTime"))),
            "is_personal_best": bool(lap.get("IsPersonalBest")) if pd.notna(lap.get("IsPersonalBest")) else None,
            "position": int(lap["Position"]) if pd.notna(lap.get("Position")) else None,
            "speed_trap": float(lap["SpeedST"]) if pd.notna(lap.get("SpeedST")) else None,
        })

    # Bulk upsert in batches
    batch_size = 500
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        stmt = insert(Lap).values(batch)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_lap",
            set_={
                "lap_time_ms": stmt.excluded.lap_time_ms,
                "sector1_ms": stmt.excluded.sector1_ms,
                "sector2_ms": stmt.excluded.sector2_ms,
                "sector3_ms": stmt.excluded.sector3_ms,
                "compound": stmt.excluded.compound,
                "tyre_life": stmt.excluded.tyre_life,
                "is_pit_in_lap": stmt.excluded.is_pit_in_lap,
                "is_pit_out_lap": stmt.excluded.is_pit_out_lap,
                "is_personal_best": stmt.excluded.is_personal_best,
                "position": stmt.excluded.position,
                "speed_trap": stmt.excluded.speed_trap,
            },
        )
        db.execute(stmt)

    db.commit()
    logger.info("Upserted %d laps for %d R%d %s", len(rows), year, round_num, session_type)
