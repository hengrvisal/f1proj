"""Telemetry endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api.deps import get_db

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


@router.get("/drivers")
def get_telemetry_drivers(
    session_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """List drivers who have telemetry data for a given session."""
    rows = db.execute(text("""
        SELECT DISTINCT d.id, d.code, d.first_name, d.last_name
        FROM drivers d
        JOIN telemetry_samples ts ON ts.driver_id = d.id
        WHERE ts.session_id = :sid
        ORDER BY d.code
    """), {"sid": session_id}).fetchall()

    return [
        {"id": r[0], "code": r[1], "first_name": r[2], "last_name": r[3]}
        for r in rows
    ]


@router.get("/lap")
def get_lap_telemetry(
    session_id: int = Query(...),
    driver_id: int = Query(...),
    lap: int = Query(...),
    db: Session = Depends(get_db),
):
    """Raw telemetry trace for a single lap."""
    rows = db.execute(text("""
        SELECT distance_m, speed, throttle, brake, gear, rpm, drs, x, y
        FROM telemetry_samples
        WHERE session_id = :sid AND driver_id = :did AND lap_number = :lap
        ORDER BY distance_m
    """), {"sid": session_id, "did": driver_id, "lap": lap}).fetchall()

    return {
        "session_id": session_id,
        "driver_id": driver_id,
        "lap": lap,
        "samples": [
            {
                "distance_m": r[0], "speed": r[1], "throttle": r[2],
                "brake": r[3], "gear": r[4], "rpm": r[5],
                "drs": r[6], "x": r[7], "y": r[8],
            }
            for r in rows
        ],
    }


@router.get("/compare")
def compare_telemetry(
    session_id: int = Query(...),
    driver_a: int = Query(...),
    driver_b: int = Query(...),
    lap: int | None = Query(None, description="Specific lap or best lap"),
    db: Session = Depends(get_db),
):
    """Overlay comparison of two drivers' telemetry."""
    def get_best_lap(driver_id: int) -> int | None:
        r = db.execute(text("""
            SELECT l.lap_number FROM laps l
            JOIN telemetry_samples ts ON ts.session_id = l.session_id
                AND ts.driver_id = l.driver_id AND ts.lap_number = l.lap_number
            WHERE l.session_id = :sid AND l.driver_id = :did
              AND l.lap_time_ms IS NOT NULL
              AND l.is_pit_in_lap IS NOT TRUE AND l.is_pit_out_lap IS NOT TRUE
            GROUP BY l.lap_number, l.lap_time_ms
            HAVING COUNT(ts.id) > 10
            ORDER BY l.lap_time_ms ASC LIMIT 1
        """), {"sid": session_id, "did": driver_id}).fetchone()
        return r[0] if r else None

    lap_a = lap or get_best_lap(driver_a)
    lap_b = lap or get_best_lap(driver_b)

    if not lap_a or not lap_b:
        return {"error": "No valid laps with telemetry found", "driver_a": None, "driver_b": None}

    def get_trace(driver_id: int, lap_num: int):
        rows = db.execute(text("""
            SELECT distance_m, speed, throttle, brake, gear
            FROM telemetry_samples
            WHERE session_id = :sid AND driver_id = :did AND lap_number = :lap
            ORDER BY distance_m
        """), {"sid": session_id, "did": driver_id, "lap": lap_num}).fetchall()
        return [
            {"distance_m": r[0], "speed": r[1], "throttle": r[2], "brake": r[3], "gear": r[4]}
            for r in rows
        ]

    return {
        "driver_a": {"driver_id": driver_a, "lap": lap_a, "trace": get_trace(driver_a, lap_a)},
        "driver_b": {"driver_id": driver_b, "lap": lap_b, "trace": get_trace(driver_b, lap_b)},
    }
