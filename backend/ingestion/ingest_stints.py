"""Ingest tyre stint data derived from FastF1 lap data."""

import logging

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DBSession

from backend.ingestion.fastf1_loader import load_session
from backend.ingestion.helpers import resolve_driver_id
from backend.models import Session, TyreStint

logger = logging.getLogger(__name__)


def get_session_id(db: DBSession, race_id: int, session_type: str) -> int | None:
    return db.execute(
        select(Session.id).where(Session.race_id == race_id, Session.session_type == session_type)
    ).scalar_one_or_none()


def ingest_stints(db: DBSession, year: int, round_num: int, race_id: int, session_type: str = "R"):
    session_id = get_session_id(db, race_id, session_type)
    if not session_id:
        return

    ff1_session = load_session(year, round_num, session_type)
    if ff1_session is None:
        return

    laps_df = ff1_session.laps
    if laps_df is None or laps_df.empty:
        return

    rows = []
    for driver_num in laps_df["DriverNumber"].unique():
        driver_laps = laps_df[laps_df["DriverNumber"] == driver_num].sort_values("LapNumber")
        driver_id = resolve_driver_id(
            db,
            number=int(driver_num) if pd.notna(driver_num) else None,
            code=str(driver_laps.iloc[0].get("Driver", "")) if pd.notna(driver_laps.iloc[0].get("Driver")) else None,
        )
        if not driver_id:
            continue

        stint_num = 0
        current_compound = None
        stint_start = None

        for _, lap in driver_laps.iterrows():
            compound = str(lap.get("Compound")) if pd.notna(lap.get("Compound")) else None
            lap_num = int(lap["LapNumber"])
            stint_number_col = int(lap["Stint"]) if pd.notna(lap.get("Stint")) else None

            if compound != current_compound or (stint_number_col is not None and stint_number_col != stint_num):
                # Save previous stint
                if current_compound is not None and stint_start is not None:
                    rows.append({
                        "session_id": session_id,
                        "driver_id": driver_id,
                        "stint_number": stint_num,
                        "compound": current_compound,
                        "start_lap": stint_start,
                        "end_lap": prev_lap,
                        "tyre_age_at_start": tyre_age_start,
                    })
                # Start new stint
                stint_num = stint_number_col if stint_number_col is not None else stint_num + 1
                current_compound = compound
                stint_start = lap_num
                tyre_age_start = int(lap["TyreLife"]) if pd.notna(lap.get("TyreLife")) else 0

            prev_lap = lap_num

        # Save last stint
        if current_compound is not None and stint_start is not None:
            rows.append({
                "session_id": session_id,
                "driver_id": driver_id,
                "stint_number": stint_num,
                "compound": current_compound,
                "start_lap": stint_start,
                "end_lap": prev_lap,
                "tyre_age_at_start": tyre_age_start,
            })

    if not rows:
        return

    stmt = insert(TyreStint).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_tyre_stint",
        set_={
            "compound": stmt.excluded.compound,
            "start_lap": stmt.excluded.start_lap,
            "end_lap": stmt.excluded.end_lap,
            "tyre_age_at_start": stmt.excluded.tyre_age_at_start,
        },
    )
    db.execute(stmt)
    db.commit()
    logger.info("Upserted %d stints for %d R%d %s", len(rows), year, round_num, session_type)
