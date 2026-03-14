"""Tyre degradation endpoints."""

import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api.deps import get_db

router = APIRouter(prefix="/api/tyres", tags=["tyres"])


@router.get("/deg-curves")
def get_deg_curves(
    session_id: int = Query(...),
    driver_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    """Fitted degradation curves + actual lap time points."""
    params: dict = {"sid": session_id}
    driver_filter = ""
    if driver_id:
        driver_filter = "AND tdc.driver_id = :did"
        params["did"] = driver_id

    curves = db.execute(text(f"""
        SELECT tdc.driver_id, d.code, tdc.stint_number, tdc.compound,
               tdc.model_type, tdc.coefficients, tdc.r_squared,
               tdc.deg_rate_ms_per_lap, tdc.predicted_cliff_lap, tdc.num_laps
        FROM tyre_deg_curves tdc
        JOIN drivers d ON tdc.driver_id = d.id
        WHERE tdc.session_id = :sid {driver_filter}
        ORDER BY tdc.driver_id, tdc.stint_number
    """), params).fetchall()

    result = []
    for r in curves:
        # Get actual lap times for this stint
        stint = db.execute(text("""
            SELECT ts.start_lap, ts.end_lap
            FROM tyre_stints ts
            WHERE ts.session_id = :sid AND ts.driver_id = :did AND ts.stint_number = :sn
        """), {"sid": session_id, "did": r[0], "sn": r[2]}).fetchone()

        actual_laps = []
        if stint and stint[0] and stint[1]:
            laps = db.execute(text("""
                SELECT lap_number, lap_time_ms, tyre_life
                FROM laps
                WHERE session_id = :sid AND driver_id = :did
                  AND lap_number >= :start AND lap_number <= :end
                  AND lap_time_ms IS NOT NULL
                  AND is_pit_in_lap IS NOT TRUE AND is_pit_out_lap IS NOT TRUE
                ORDER BY lap_number
            """), {"sid": session_id, "did": r[0], "start": stint[0], "end": stint[1]}).fetchall()
            actual_laps = [{"lap": l[0], "time_ms": l[1], "tyre_life": l[2]} for l in laps]

        result.append({
            "driver_id": r[0], "code": r[1], "stint_number": r[2], "compound": r[3],
            "model_type": r[4], "coefficients": json.loads(r[5]) if r[5] else [],
            "r_squared": r[6], "deg_rate_ms_per_lap": r[7],
            "predicted_cliff_lap": r[8], "num_laps": r[9],
            "actual_laps": actual_laps,
        })

    return result


@router.get("/strategy-summary")
def get_strategy_summary(
    session_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """All drivers' stint strategies for a session."""
    rows = db.execute(text("""
        SELECT d.id, d.code, ts.stint_number, ts.compound,
               ts.start_lap, ts.end_lap, ts.tyre_age_at_start,
               tdc.deg_rate_ms_per_lap, tdc.model_type
        FROM tyre_stints ts
        JOIN drivers d ON ts.driver_id = d.id
        LEFT JOIN tyre_deg_curves tdc ON tdc.session_id = ts.session_id
            AND tdc.driver_id = ts.driver_id AND tdc.stint_number = ts.stint_number
        WHERE ts.session_id = :sid
        ORDER BY d.code, ts.stint_number
    """), {"sid": session_id}).fetchall()

    # Group by driver
    drivers: dict = {}
    for r in rows:
        did = r[0]
        if did not in drivers:
            drivers[did] = {"driver_id": did, "code": r[1], "stints": []}
        drivers[did]["stints"].append({
            "stint_number": r[2], "compound": r[3],
            "start_lap": r[4], "end_lap": r[5],
            "tyre_age_at_start": r[6],
            "deg_rate_ms_per_lap": r[7], "model_type": r[8],
        })

    return list(drivers.values())
