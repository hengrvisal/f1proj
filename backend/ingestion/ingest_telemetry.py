"""Ingest telemetry data from FastF1, resampled at 10m distance intervals."""

import logging

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DBSession

from backend.ingestion.fastf1_loader import load_session
from backend.ingestion.helpers import resolve_driver_id
from backend.models import Session, TelemetrySample

logger = logging.getLogger(__name__)

DISTANCE_INTERVAL = 10  # meters
BATCH_SIZE = 10_000


def get_session_id(db: DBSession, race_id: int, session_type: str) -> int | None:
    return db.execute(
        select(Session.id).where(Session.race_id == race_id, Session.session_type == session_type)
    ).scalar_one_or_none()


def resample_telemetry(tel_df: pd.DataFrame, lap_distance: float | None = None) -> pd.DataFrame:
    """Resample raw telemetry to 10m distance intervals using interpolation."""
    if tel_df.empty or "Distance" not in tel_df.columns:
        return pd.DataFrame()

    dist = tel_df["Distance"].values
    if len(dist) < 2:
        return pd.DataFrame()

    max_dist = lap_distance if lap_distance else dist.max()
    if max_dist <= 0:
        return pd.DataFrame()

    # Create regular 10m distance grid
    new_dist = np.arange(0, int(max_dist) + DISTANCE_INTERVAL, DISTANCE_INTERVAL)

    result = {"distance_m": new_dist.astype(int)}

    # Interpolate numeric columns
    for col in ["Speed", "Throttle", "RPM", "X", "Y"]:
        if col in tel_df.columns:
            vals = tel_df[col].values.astype(float)
            mask = ~np.isnan(vals)
            if mask.sum() >= 2:
                result[col.lower()] = np.interp(new_dist, dist[mask], vals[mask])
            else:
                result[col.lower()] = np.full(len(new_dist), np.nan)

    # Nearest-neighbor for discrete columns
    for col, out_key in [("nGear", "gear"), ("Brake", "brake"), ("DRS", "drs")]:
        if col in tel_df.columns:
            vals = tel_df[col].values
            indices = np.searchsorted(dist, new_dist, side="right") - 1
            indices = np.clip(indices, 0, len(vals) - 1)
            result[out_key] = vals[indices]

    return pd.DataFrame(result)


def ingest_telemetry(db: DBSession, year: int, round_num: int, race_id: int, session_type: str = "R"):
    session_id = get_session_id(db, race_id, session_type)
    if not session_id:
        return

    ff1_session = load_session(year, round_num, session_type)
    if ff1_session is None:
        return

    laps_df = ff1_session.laps
    if laps_df is None or laps_df.empty:
        return

    total_rows = 0
    batch = []

    for driver_num in laps_df["DriverNumber"].unique():
        driver_laps = laps_df[laps_df["DriverNumber"] == driver_num]
        driver_id = resolve_driver_id(
            db,
            number=int(driver_num) if pd.notna(driver_num) else None,
            code=str(driver_laps.iloc[0].get("Driver", "")) if pd.notna(driver_laps.iloc[0].get("Driver")) else None,
        )
        if not driver_id:
            continue

        for _, lap in driver_laps.iterrows():
            lap_num = int(lap["LapNumber"]) if pd.notna(lap.get("LapNumber")) else None
            if not lap_num:
                continue

            try:
                tel = lap.get_telemetry()
            except Exception:
                continue

            if tel is None or tel.empty:
                continue

            resampled = resample_telemetry(tel)
            if resampled.empty:
                continue

            for _, row in resampled.iterrows():
                batch.append({
                    "session_id": session_id,
                    "driver_id": driver_id,
                    "lap_number": lap_num,
                    "distance_m": int(row["distance_m"]),
                    "speed": float(row.get("speed")) if pd.notna(row.get("speed")) else None,
                    "throttle": int(row["throttle"]) if pd.notna(row.get("throttle")) else None,
                    "brake": bool(row["brake"]) if pd.notna(row.get("brake")) else None,
                    "gear": int(row["gear"]) if pd.notna(row.get("gear")) else None,
                    "rpm": int(row["rpm"]) if pd.notna(row.get("rpm")) else None,
                    "drs": int(row["drs"]) if pd.notna(row.get("drs")) else None,
                    "x": float(row["x"]) if pd.notna(row.get("x")) else None,
                    "y": float(row["y"]) if pd.notna(row.get("y")) else None,
                })

                if len(batch) >= BATCH_SIZE:
                    _flush_batch(db, batch)
                    total_rows += len(batch)
                    batch = []

    if batch:
        _flush_batch(db, batch)
        total_rows += len(batch)

    logger.info("Upserted %d telemetry samples for %d R%d %s", total_rows, year, round_num, session_type)


def _flush_batch(db: DBSession, batch: list[dict]):
    stmt = insert(TelemetrySample).values(batch)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_telemetry_sample",
        set_={
            "speed": stmt.excluded.speed,
            "throttle": stmt.excluded.throttle,
            "brake": stmt.excluded.brake,
            "gear": stmt.excluded.gear,
            "rpm": stmt.excluded.rpm,
            "drs": stmt.excluded.drs,
            "x": stmt.excluded.x,
            "y": stmt.excluded.y,
        },
    )
    db.execute(stmt)
    db.commit()
