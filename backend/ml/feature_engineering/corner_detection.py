"""Detect corners from telemetry speed profiles.

Corners are circuit-level — computed once per circuit using median speed
across all drivers and clean laps from race sessions.
"""

import logging

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models import CircuitCorner

logger = logging.getLogger(__name__)

# Parameters
SMOOTHING_WINDOW = 5  # 5 samples = 50m at 10m resolution
MIN_SPEED_DROP = 30  # km/h drop from local max to qualify as corner
MIN_CORNER_SEPARATION = 30  # meters — merge corners closer than this
THROTTLE_EXIT_THRESHOLD = 90  # throttle % to define corner exit


def _get_median_speed_profile(db: Session, circuit_id: int) -> pd.DataFrame | None:
    """Get median speed at each distance_m across all drivers/laps for race sessions on this circuit."""
    query = text("""
        SELECT ts.distance_m,
               PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ts.speed) as median_speed,
               PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ts.throttle) as median_throttle
        FROM telemetry_samples ts
        JOIN sessions s ON ts.session_id = s.id
        JOIN races r ON s.race_id = r.id
        JOIN laps l ON l.session_id = ts.session_id
                   AND l.driver_id = ts.driver_id
                   AND l.lap_number = ts.lap_number
        WHERE r.circuit_id = :circuit_id
          AND s.session_type = 'R'
          AND ts.speed IS NOT NULL
          AND l.is_pit_in_lap IS NOT TRUE
          AND l.is_pit_out_lap IS NOT TRUE
          AND l.lap_time_ms IS NOT NULL
        GROUP BY ts.distance_m
        HAVING COUNT(*) >= 5
        ORDER BY ts.distance_m
    """)
    result = db.execute(query, {"circuit_id": circuit_id})
    rows = result.fetchall()
    if not rows:
        return None
    return pd.DataFrame(rows, columns=["distance_m", "median_speed", "median_throttle"])


def _find_local_minima(speeds: np.ndarray, distances: np.ndarray) -> list[dict]:
    """Find speed local minima that represent corners (speed drop >= MIN_SPEED_DROP)."""
    corners = []
    n = len(speeds)
    if n < 3:
        return corners

    # Find all local minima
    for i in range(1, n - 1):
        if speeds[i] < speeds[i - 1] and speeds[i] <= speeds[i + 1]:
            # Find preceding local max
            max_speed = speeds[i]
            for j in range(i - 1, -1, -1):
                if speeds[j] > max_speed:
                    max_speed = speeds[j]
                if j > 0 and speeds[j] > speeds[j - 1] and speeds[j] >= speeds[j + 1]:
                    break  # Found the local max

            speed_drop = max_speed - speeds[i]
            if speed_drop >= MIN_SPEED_DROP:
                corners.append({
                    "apex_idx": i,
                    "apex_distance": distances[i],
                    "apex_speed": speeds[i],
                    "speed_drop": speed_drop,
                })

    return corners


def _find_entry_exit(
    speeds: np.ndarray,
    throttles: np.ndarray,
    distances: np.ndarray,
    apex_idx: int,
) -> tuple[int, int]:
    """Find corner entry (brake onset) and exit (throttle > threshold) around apex."""
    n = len(speeds)

    # Entry: walk backwards from apex to find where braking starts
    # (speed starts decreasing consistently)
    entry_idx = apex_idx
    for i in range(apex_idx - 1, -1, -1):
        if speeds[i] >= speeds[i + 1]:
            entry_idx = i + 1
            # Go one more back to the actual brake point
            entry_idx = max(0, i)
            break
    else:
        entry_idx = 0

    # Exit: walk forward from apex to find where throttle > threshold
    exit_idx = apex_idx
    for i in range(apex_idx + 1, n):
        if throttles[i] >= THROTTLE_EXIT_THRESHOLD:
            exit_idx = i
            break
    else:
        exit_idx = min(n - 1, apex_idx + 10)

    return entry_idx, exit_idx


def _merge_close_corners(corners: list[dict], min_separation: float) -> list[dict]:
    """Merge corners whose apexes are within min_separation meters."""
    if not corners:
        return corners

    merged = [corners[0]]
    for c in corners[1:]:
        prev = merged[-1]
        if c["apex_distance"] - prev["apex_distance"] < min_separation:
            # Keep the one with larger speed drop
            if c["speed_drop"] > prev["speed_drop"]:
                merged[-1] = c
        else:
            merged.append(c)

    return merged


def _classify_corner(apex_speed: float) -> str:
    """Classify corner as slow/medium/fast based on apex speed."""
    if apex_speed < 120:
        return "slow"
    elif apex_speed < 200:
        return "medium"
    else:
        return "fast"


def detect_corners_for_circuit(db: Session, circuit_id: int) -> list[CircuitCorner]:
    """Detect corners for a circuit from telemetry and write to DB."""
    profile = _get_median_speed_profile(db, circuit_id)
    if profile is None or len(profile) < 20:
        logger.warning(f"Insufficient telemetry for circuit {circuit_id}")
        return []

    distances = profile["distance_m"].values.astype(float)
    speeds = profile["median_speed"].values.astype(float)
    throttles = profile["median_throttle"].values.astype(float)

    # Smooth speed profile
    smoothed = pd.Series(speeds).rolling(window=SMOOTHING_WINDOW, center=True, min_periods=1).mean().values

    # Find corners
    raw_corners = _find_local_minima(smoothed, distances)
    corners = _merge_close_corners(raw_corners, MIN_CORNER_SEPARATION)

    if not corners:
        logger.warning(f"No corners detected for circuit {circuit_id}")
        return []

    # Delete existing corners for this circuit
    db.execute(
        text("DELETE FROM circuit_corners WHERE circuit_id = :cid"),
        {"cid": circuit_id},
    )

    result = []
    for i, c in enumerate(corners, 1):
        apex_idx = c["apex_idx"]
        entry_idx, exit_idx = _find_entry_exit(speeds, throttles, distances, apex_idx)

        corner = CircuitCorner(
            circuit_id=circuit_id,
            corner_number=i,
            entry_distance_m=float(distances[entry_idx]),
            apex_distance_m=float(distances[apex_idx]),
            exit_distance_m=float(distances[exit_idx]),
            entry_speed_median=float(speeds[entry_idx]),
            apex_speed_median=float(speeds[apex_idx]),
            exit_speed_median=float(speeds[exit_idx]),
            corner_type=_classify_corner(float(speeds[apex_idx])),
        )
        db.add(corner)
        result.append(corner)

    db.commit()
    logger.info(f"Detected {len(result)} corners for circuit {circuit_id}")
    return result


def detect_all_corners(db: Session) -> dict[int, int]:
    """Detect corners for all circuits that have telemetry data."""
    circuits = db.execute(text("""
        SELECT DISTINCT c.id, c.name
        FROM circuits c
        JOIN races r ON r.circuit_id = c.id
        JOIN sessions s ON s.race_id = r.id
        JOIN telemetry_samples ts ON ts.session_id = s.id
        WHERE s.session_type = 'R'
    """)).fetchall()

    results = {}
    for circuit_id, circuit_name in circuits:
        corners = detect_corners_for_circuit(db, circuit_id)
        results[circuit_id] = len(corners)
        logger.info(f"  {circuit_name}: {len(corners)} corners")

    return results
