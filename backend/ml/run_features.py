"""CLI orchestrator for the ML pipeline.

Usage:
    python -m backend.ml.run_features --all
    python -m backend.ml.run_features --corners
    python -m backend.ml.run_features --profiles
    python -m backend.ml.run_features --dna --year 2023
    python -m backend.ml.run_features --tyres
"""

import argparse
import logging
import sys

from backend.database import SessionLocal
from backend.ml.tracking import track_run, log_metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def run_corners(db):
    from backend.ml.feature_engineering.corner_detection import detect_all_corners
    with track_run(db, "corner_detection") as ml_run:
        results = detect_all_corners(db)
        total = sum(results.values())
        log_metrics(db, ml_run, {
            "circuits_processed": len(results),
            "total_corners": total,
        })
        logger.info(f"Corner detection complete: {total} corners across {len(results)} circuits")


def run_profiles(db):
    from backend.ml.feature_engineering.corner_profiles import compute_all_corner_profiles
    with track_run(db, "corner_profiles") as ml_run:
        results = compute_all_corner_profiles(db)
        total = sum(results.values())
        log_metrics(db, ml_run, {
            "sessions_processed": len(results),
            "total_stats": total,
        })
        logger.info(f"Corner profiles complete: {total} stats across {len(results)} sessions")


def run_dna(db, year: int):
    from backend.ml.models.driver_dna import compute_all_dna
    with track_run(db, "driver_dna", {"year": year}) as ml_run:
        count = compute_all_dna(db, year)
        log_metrics(db, ml_run, {
            "drivers_processed": count,
            "year": year,
        })
        logger.info(f"Driver DNA complete: {count} drivers for {year}")


def run_tyres(db):
    from backend.ml.models.tyre_degradation import compute_all_deg
    with track_run(db, "tyre_degradation") as ml_run:
        results = compute_all_deg(db)
        total = sum(results.values())
        log_metrics(db, ml_run, {
            "sessions_processed": len(results),
            "total_curves": total,
        })
        logger.info(f"Tyre deg complete: {total} curves across {len(results)} sessions")


def main():
    parser = argparse.ArgumentParser(description="F1 ML Pipeline Runner")
    parser.add_argument("--all", action="store_true", help="Run entire pipeline")
    parser.add_argument("--corners", action="store_true", help="Run corner detection")
    parser.add_argument("--profiles", action="store_true", help="Run corner profiles")
    parser.add_argument("--dna", action="store_true", help="Run Driver DNA clustering")
    parser.add_argument("--tyres", action="store_true", help="Run tyre degradation")
    parser.add_argument("--year", type=int, action="append", default=[], help="Season year(s) for DNA")
    args = parser.parse_args()

    if not any([args.all, args.corners, args.profiles, args.dna, args.tyres]):
        parser.print_help()
        sys.exit(1)

    years = args.year or [2023, 2024]

    db = SessionLocal()
    try:
        if args.all or args.corners:
            logger.info("=== Step 1: Corner Detection ===")
            run_corners(db)

        if args.all or args.profiles:
            logger.info("=== Step 2: Corner Profiles ===")
            run_profiles(db)

        if args.all or args.tyres:
            logger.info("=== Step 3: Tyre Degradation ===")
            run_tyres(db)

        if args.all or args.dna:
            for year in years:
                logger.info(f"=== Step 4: Driver DNA ({year}) ===")
                run_dna(db, year)

        logger.info("=== Pipeline complete ===")

    except Exception:
        logger.exception("Pipeline failed")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
