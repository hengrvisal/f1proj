"""CLI orchestrator for the F1 data ingestion pipeline."""

import argparse
import logging
import sys

from sqlalchemy import select

from backend.database import SessionLocal
from backend.ingestion.ingest_laps import ingest_laps
from backend.ingestion.ingest_pitstops import ingest_pitstops
from backend.ingestion.ingest_qualifying import upsert_qualifying
from backend.ingestion.ingest_race_control import (
    backfill_openf1_keys,
    ingest_race_control_messages,
    ingest_team_radio,
)
from backend.ingestion.ingest_races import get_race_id, ingest_races
from backend.ingestion.ingest_static import ingest_static
from backend.ingestion.ingest_stints import ingest_stints
from backend.ingestion.ingest_telemetry import ingest_telemetry
from backend.ingestion.ingest_weather import ingest_weather
from backend.ingestion.jolpica_client import JolpicaClient
from backend.ingestion.openf1_client import OpenF1Client
from backend.models import Race, Session

logger = logging.getLogger(__name__)


def run_pipeline(
    years: list[int],
    rounds: list[int] | None = None,
    session_types: list[str] | None = None,
    skip_telemetry: bool = False,
    skip_openf1: bool = False,
):
    if session_types is None:
        session_types = ["R", "Q"]

    db = SessionLocal()
    jolpica = JolpicaClient()

    try:
        # Phase 1: Static data
        logger.info("=== Ingesting static data ===")
        ingest_static(db, jolpica, years)

        # Phase 2: Races + results per year
        for year in years:
            logger.info("=== Processing year %d ===", year)
            ingest_races(db, jolpica, year)

            # Get all races for this year
            all_races = db.execute(
                select(Race)
                .join(Race.season)
                .where(Race.season.has(year=year))
                .order_by(Race.round_number)
            ).scalars().all()

            for race in all_races:
                if rounds and race.round_number not in rounds:
                    continue

                logger.info("--- %d Round %d: %s ---", year, race.round_number, race.name)

                try:
                    # Qualifying results
                    upsert_qualifying(db, jolpica, year, race.round_number, race.id)
                except Exception as e:
                    logger.error("Qualifying failed for %d R%d: %s", year, race.round_number, e)

                try:
                    # Pit stops
                    ingest_pitstops(db, jolpica, year, race.round_number, race.id)
                except Exception as e:
                    logger.error("Pit stops failed for %d R%d: %s", year, race.round_number, e)

                # FastF1 data per session type
                for stype in session_types:
                    try:
                        ingest_laps(db, year, race.round_number, race.id, stype)
                    except Exception as e:
                        logger.error("Laps failed for %d R%d %s: %s", year, race.round_number, stype, e)

                    try:
                        ingest_stints(db, year, race.round_number, race.id, stype)
                    except Exception as e:
                        logger.error("Stints failed for %d R%d %s: %s", year, race.round_number, stype, e)

                    try:
                        ingest_weather(db, year, race.round_number, race.id, stype)
                    except Exception as e:
                        logger.error("Weather failed for %d R%d %s: %s", year, race.round_number, stype, e)

                    if not skip_telemetry:
                        try:
                            ingest_telemetry(db, year, race.round_number, race.id, stype)
                        except Exception as e:
                            logger.error("Telemetry failed for %d R%d %s: %s", year, race.round_number, stype, e)

        # Phase 3: OpenF1 data
        if not skip_openf1:
            openf1 = OpenF1Client()
            try:
                for year in years:
                    logger.info("=== Backfilling OpenF1 keys for %d ===", year)
                    try:
                        backfill_openf1_keys(db, openf1, year)
                    except Exception as e:
                        logger.error("OpenF1 key backfill failed for %d: %s", year, e)
                        continue

                    # Ingest race control + team radio for sessions with OpenF1 keys
                    sessions = db.execute(
                        select(Session)
                        .join(Session.race)
                        .where(
                            Race.season.has(year=year),
                            Session.openf1_session_key.isnot(None),
                        )
                    ).scalars().all()

                    for sess in sessions:
                        try:
                            ingest_race_control_messages(db, openf1, sess.id, sess.openf1_session_key)
                        except Exception as e:
                            logger.error("Race control failed for session %d: %s", sess.id, e)

                        try:
                            ingest_team_radio(db, openf1, sess.id, sess.openf1_session_key)
                        except Exception as e:
                            logger.error("Team radio failed for session %d: %s", sess.id, e)
            finally:
                openf1.close()

        logger.info("=== Pipeline complete ===")

    finally:
        jolpica.close()
        db.close()


def main():
    parser = argparse.ArgumentParser(description="F1 Data Ingestion Pipeline")
    parser.add_argument("--year", type=int, action="append", required=True, help="Year(s) to ingest")
    parser.add_argument("--round", type=int, action="append", help="Specific round(s) to process")
    parser.add_argument("--sessions", type=str, nargs="+", default=["R", "Q"], help="Session types to process")
    parser.add_argument("--skip-telemetry", action="store_true", help="Skip telemetry ingestion")
    parser.add_argument("--skip-openf1", action="store_true", help="Skip OpenF1 data")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    run_pipeline(
        years=args.year,
        rounds=args.round,
        session_types=args.sessions,
        skip_telemetry=args.skip_telemetry,
        skip_openf1=args.skip_openf1,
    )


if __name__ == "__main__":
    main()
