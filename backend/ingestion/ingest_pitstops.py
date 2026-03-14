"""Ingest pit stop data from Jolpica API."""

import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DBSession

from backend.ingestion.helpers import resolve_driver_id, time_str_to_ms
from backend.ingestion.jolpica_client import JolpicaClient
from backend.models import PitStop

logger = logging.getLogger(__name__)


def ingest_pitstops(db: DBSession, client: JolpicaClient, year: int, round_num: int, race_id: int):
    pit_data = client.pit_stops(year, round_num)
    if not pit_data:
        logger.info("No pit stop data for %d R%d", year, round_num)
        return

    rows = []
    for p in pit_data:
        driver_ref = p.get("driverId")
        driver_id = resolve_driver_id(db, driver_ref=driver_ref)
        if not driver_id:
            logger.debug("Could not resolve driver for pit stop: %s", driver_ref)
            continue

        duration_str = p.get("duration")
        duration_ms = time_str_to_ms(duration_str) if duration_str else None

        rows.append({
            "race_id": race_id,
            "driver_id": driver_id,
            "stop_number": int(p["stop"]),
            "lap_number": int(p["lap"]),
            "duration_ms": duration_ms,
            "total_time_ms": None,
        })

    if not rows:
        return

    stmt = insert(PitStop).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_pit_stop",
        set_={
            "lap_number": stmt.excluded.lap_number,
            "duration_ms": stmt.excluded.duration_ms,
        },
    )
    db.execute(stmt)
    db.commit()
    logger.info("Upserted %d pit stops for %d R%d", len(rows), year, round_num)
