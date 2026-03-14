"""Ingest qualifying results from Jolpica."""

import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DBSession

from backend.ingestion.helpers import get_constructor_id, get_driver_id, time_str_to_ms
from backend.ingestion.jolpica_client import JolpicaClient
from backend.models import QualifyingResult

logger = logging.getLogger(__name__)


def upsert_qualifying(session: DBSession, client: JolpicaClient, year: int, round_num: int, race_id: int):
    results = client.qualifying_results(year, round_num)
    if not results:
        logger.warning("No qualifying results for %d round %d", year, round_num)
        return

    for r in results:
        driver_ref = r["Driver"]["driverId"]
        constructor_ref = r["Constructor"]["constructorId"]
        driver_id = get_driver_id(session, driver_ref)
        constructor_id = get_constructor_id(session, constructor_ref)

        if not driver_id or not constructor_id:
            continue

        stmt = insert(QualifyingResult).values(
            race_id=race_id,
            driver_id=driver_id,
            constructor_id=constructor_id,
            position=int(r.get("position", 0)) or None,
            q1_ms=time_str_to_ms(r.get("Q1")),
            q2_ms=time_str_to_ms(r.get("Q2")),
            q3_ms=time_str_to_ms(r.get("Q3")),
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_qualifying_result",
            set_={
                "position": stmt.excluded.position,
                "q1_ms": stmt.excluded.q1_ms,
                "q2_ms": stmt.excluded.q2_ms,
                "q3_ms": stmt.excluded.q3_ms,
            },
        )
        session.execute(stmt)

    session.commit()
    logger.info("Upserted %d qualifying results for %d R%d", len(results), year, round_num)
