"""Tyre degradation curve fitting.

Per-stint: extract clean laps, apply fuel correction (~30ms/lap),
exclude SC periods. Fit linear and quadratic models.
"""

import json
import logging

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models import TyreDegCurve

logger = logging.getLogger(__name__)

FUEL_CORRECTION_MS_PER_LAP = 30  # Approximate fuel effect reduction per lap


def _get_stint_laps(
    db: Session, session_id: int, driver_id: int, stint_number: int
) -> list[dict]:
    """Get clean laps for a stint, excluding safety car periods."""
    # Get stint boundaries
    stint = db.execute(text("""
        SELECT start_lap, end_lap, compound
        FROM tyre_stints
        WHERE session_id = :sid AND driver_id = :did AND stint_number = :sn
    """), {"sid": session_id, "did": driver_id, "sn": stint_number}).fetchone()

    if not stint or stint[0] is None or stint[1] is None:
        return []

    start_lap, end_lap, compound = stint

    # Get safety car laps for this session
    sc_laps = set()
    sc_msgs = db.execute(text("""
        SELECT DISTINCT lap_number
        FROM race_control_messages
        WHERE session_id = :sid
          AND (flag = 'YELLOW' OR category = 'SafetyCar' OR message LIKE '%%SAFETY CAR%%')
          AND lap_number IS NOT NULL
    """), {"sid": session_id}).fetchall()
    for row in sc_msgs:
        sc_laps.add(row[0])
        sc_laps.add(row[0] + 1)  # Also exclude lap after SC

    # Get laps
    laps = db.execute(text("""
        SELECT lap_number, lap_time_ms, tyre_life
        FROM laps
        WHERE session_id = :sid
          AND driver_id = :did
          AND lap_number >= :start
          AND lap_number <= :end
          AND is_pit_in_lap IS NOT TRUE
          AND is_pit_out_lap IS NOT TRUE
          AND lap_time_ms IS NOT NULL
        ORDER BY lap_number
    """), {
        "sid": session_id, "did": driver_id,
        "start": start_lap, "end": end_lap,
    }).fetchall()

    result = []
    for lap_num, lap_time_ms, tyre_life in laps:
        if lap_num in sc_laps:
            continue
        # Exclude lap 1 of the race (standing start is much slower)
        if lap_num == 1:
            continue
        result.append({
            "lap_number": lap_num,
            "lap_time_ms": lap_time_ms,
            "tyre_life": tyre_life or (lap_num - start_lap + 1),
        })

    # Remove outliers: laps >107% of median lap time (likely slow due to traffic/incidents)
    if len(result) >= 4:
        times = sorted(r["lap_time_ms"] for r in result)
        median_time = times[len(times) // 2]
        threshold = median_time * 1.07
        result = [r for r in result if r["lap_time_ms"] <= threshold]

    return result, compound


def _fuel_correct(lap_times: np.ndarray, total_laps: int, first_lap_num: int) -> np.ndarray:
    """Apply fuel correction: subtract estimated fuel effect."""
    corrected = lap_times.copy().astype(float)
    for i in range(len(corrected)):
        # Laps remaining decreases, so fuel saving increases with lap number
        laps_done = first_lap_num + i
        fuel_saving = laps_done * FUEL_CORRECTION_MS_PER_LAP
        corrected[i] += fuel_saving  # Add back fuel time to see pure tyre deg
    return corrected


def fit_stint_degradation(
    db: Session, session_id: int, driver_id: int, stint_number: int
) -> TyreDegCurve | None:
    """Fit degradation curves for a single stint."""
    result = _get_stint_laps(db, session_id, driver_id, stint_number)
    if not result:
        return None

    laps_data, compound = result
    if len(laps_data) < 4:  # Need at least 4 laps for meaningful fit
        return None

    tyre_life = np.array([l["tyre_life"] for l in laps_data])
    lap_times = np.array([l["lap_time_ms"] for l in laps_data])
    first_lap_num = laps_data[0]["lap_number"]

    # Get total race laps for fuel correction
    total_laps = db.execute(text("""
        SELECT MAX(lap_number) FROM laps
        WHERE session_id = :sid AND driver_id = :did
    """), {"sid": session_id, "did": driver_id}).scalar() or 60

    # Fuel-correct
    corrected = _fuel_correct(lap_times, total_laps, first_lap_num)

    # Normalize: delta from first lap
    baseline = corrected[0]
    delta_ms = corrected - baseline

    # Fit linear: delta_ms = a * tyre_life + b
    try:
        lin_coeffs = np.polyfit(tyre_life, delta_ms, 1)
        lin_pred = np.polyval(lin_coeffs, tyre_life)
        ss_res_lin = np.sum((delta_ms - lin_pred) ** 2)
        ss_tot = np.sum((delta_ms - np.mean(delta_ms)) ** 2)
        r2_lin = 1 - ss_res_lin / ss_tot if ss_tot > 0 else 0.0
    except Exception:
        lin_coeffs = [0.0, 0.0]
        r2_lin = 0.0

    # Fit quadratic: delta_ms = a * tyre_life² + b * tyre_life + c
    try:
        quad_coeffs = np.polyfit(tyre_life, delta_ms, 2)
        quad_pred = np.polyval(quad_coeffs, tyre_life)
        ss_res_quad = np.sum((delta_ms - quad_pred) ** 2)
        r2_quad = 1 - ss_res_quad / ss_tot if ss_tot > 0 else 0.0
    except Exception:
        quad_coeffs = [0.0, 0.0, 0.0]
        r2_quad = 0.0

    # Use quadratic if R² improves >0.1 over linear
    if r2_quad - r2_lin > 0.1:
        model_type = "quadratic"
        coefficients = [float(c) for c in quad_coeffs]
        r_squared = float(r2_quad)
        # Average deg rate: total degradation / number of laps
        total_deg = float(np.polyval(quad_coeffs, tyre_life[-1]) - np.polyval(quad_coeffs, tyre_life[0]))
        deg_rate = total_deg / max(1, len(tyre_life) - 1)

        # Predict cliff lap: where 2nd derivative contribution is significant
        # Cliff = where quadratic term adds >500ms
        if quad_coeffs[0] > 0:
            cliff_lap = int(np.sqrt(500 / quad_coeffs[0])) if quad_coeffs[0] > 0.01 else None
        else:
            cliff_lap = None
    else:
        model_type = "linear"
        coefficients = [float(c) for c in lin_coeffs]
        r_squared = float(r2_lin)
        deg_rate = float(lin_coeffs[0])  # Slope = ms per lap of tyre life
        cliff_lap = None

    curve = TyreDegCurve(
        session_id=session_id,
        driver_id=driver_id,
        stint_number=stint_number,
        compound=compound,
        model_type=model_type,
        coefficients=json.dumps(coefficients),
        r_squared=r_squared,
        deg_rate_ms_per_lap=deg_rate,
        predicted_cliff_lap=cliff_lap,
        num_laps=len(laps_data),
    )
    return curve


def compute_deg_for_session(db: Session, session_id: int) -> int:
    """Compute tyre degradation curves for all stints in a session."""
    stints = db.execute(text("""
        SELECT driver_id, stint_number
        FROM tyre_stints
        WHERE session_id = :sid
        ORDER BY driver_id, stint_number
    """), {"sid": session_id}).fetchall()

    # Delete existing
    db.execute(
        text("DELETE FROM tyre_deg_curves WHERE session_id = :sid"),
        {"sid": session_id},
    )

    count = 0
    for driver_id, stint_number in stints:
        curve = fit_stint_degradation(db, session_id, driver_id, stint_number)
        if curve:
            db.add(curve)
            count += 1

    db.commit()
    logger.info(f"Session {session_id}: fitted {count} deg curves")
    return count


def compute_all_deg(db: Session) -> dict[int, int]:
    """Compute tyre degradation for all race sessions."""
    sessions = db.execute(text("""
        SELECT DISTINCT s.id, r.name
        FROM sessions s
        JOIN races r ON s.race_id = r.id
        JOIN tyre_stints ts ON ts.session_id = s.id
        WHERE s.session_type = 'R'
        ORDER BY s.id
    """)).fetchall()

    results = {}
    for session_id, race_name in sessions:
        count = compute_deg_for_session(db, session_id)
        results[session_id] = count
        logger.info(f"  {race_name}: {count} curves")

    return results
