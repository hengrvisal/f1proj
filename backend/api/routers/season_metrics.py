"""Season metrics API — serves per-race-round driver metrics from CSV."""

import csv
from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/season-metrics", tags=["season-metrics"])

CSV_PATH = Path(__file__).resolve().parents[3] / "data" / "season_metrics.csv"


def _load_csv() -> list[dict]:
    if not CSV_PATH.exists():
        return []
    with open(CSV_PATH) as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            # Convert integer fields
            for key in ("race_round", "lap_count", "season", "overtake_passes"):
                if row.get(key):
                    row[key] = int(row[key])
                elif key == "overtake_passes":
                    row[key] = None
            # Convert float fields (normalised scores)
            for key in ("consistency", "entry_speed", "throttle_application",
                         "overtake_rate", "tyre_management", "quali_proxy"):
                if row.get(key) and row[key] != "":
                    row[key] = float(row[key])
                else:
                    row[key] = None
            # Convert raw float fields
            for key in ("consistency_raw", "entry_speed_raw", "throttle_application_raw",
                         "overtake_rate_raw", "tyre_management_raw", "quali_proxy_raw"):
                if row.get(key) and row[key] != "" and row[key] != "None":
                    row[key] = float(row[key])
                else:
                    row[key] = None
            # Convert boolean fields
            for key in ("had_dnf", "had_safety_car"):
                row[key] = row.get(key, "").strip().lower() == "true"
            rows.append(row)
        return rows


@router.get("")
def get_season_metrics(
    driver: str | None = Query(None, description="Driver code e.g. VER (omit for all drivers)"),
    season: int = Query(2024, description="Season year"),
):
    rows = _load_csv()
    filtered = [
        r for r in rows
        if r["season"] == season and (driver is None or r["driver"] == driver)
    ]
    filtered.sort(key=lambda r: r["race_round"])
    return filtered
