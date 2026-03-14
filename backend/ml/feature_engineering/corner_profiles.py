"""Per-corner driver feature extraction.

For each (session, driver, lap), extracts features at each corner zone from
telemetry. Aggregates across clean laps to session medians → writes to
driver_corner_stats table.
"""

import logging

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models import CircuitCorner, DriverCornerStat

logger = logging.getLogger(__name__)


def _get_clean_laps(db: Session, session_id: int) -> list[tuple[int, int]]:
    """Get (driver_id, lap_number) pairs for clean laps in a session."""
    result = db.execute(text("""
        SELECT driver_id, lap_number
        FROM laps
        WHERE session_id = :sid
          AND is_pit_in_lap IS NOT TRUE
          AND is_pit_out_lap IS NOT TRUE
          AND lap_time_ms IS NOT NULL
          AND lap_number > 1
        ORDER BY driver_id, lap_number
    """), {"sid": session_id})
    return [(r[0], r[1]) for r in result]


def _get_telemetry_for_driver_session(
    db: Session, session_id: int, driver_id: int, laps: list[int]
) -> pd.DataFrame:
    """Load telemetry for a specific driver's laps in a session."""
    if not laps:
        return pd.DataFrame()

    result = db.execute(text("""
        SELECT lap_number, distance_m, speed, throttle, brake, gear
        FROM telemetry_samples
        WHERE session_id = :sid
          AND driver_id = :did
          AND lap_number = ANY(:laps)
          AND speed IS NOT NULL
        ORDER BY lap_number, distance_m
    """), {"sid": session_id, "did": driver_id, "laps": laps})

    rows = result.fetchall()
    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows, columns=["lap_number", "distance_m", "speed", "throttle", "brake", "gear"])


def _extract_corner_features(
    telemetry: pd.DataFrame,
    corner: CircuitCorner,
) -> dict | None:
    """Extract features for a single corner from a single lap's telemetry."""
    entry_m = corner.entry_distance_m
    apex_m = corner.apex_distance_m
    exit_m = corner.exit_distance_m

    # Get telemetry in corner zone (with some buffer before entry for brake point)
    buffer = 100  # 100m before entry for brake detection
    zone = telemetry[
        (telemetry["distance_m"] >= entry_m - buffer)
        & (telemetry["distance_m"] <= exit_m + 50)
    ]

    if len(zone) < 3:
        return None

    # Core zone (entry to exit)
    core = telemetry[
        (telemetry["distance_m"] >= entry_m)
        & (telemetry["distance_m"] <= exit_m)
    ]

    if len(core) < 2:
        return None

    # Brake point: first sample where brake=True before apex
    pre_apex = zone[zone["distance_m"] <= apex_m]
    braking = pre_apex[pre_apex["brake"] == True]  # noqa: E712
    brake_point_m = float(braking["distance_m"].iloc[0]) if len(braking) > 0 else float(entry_m)

    # Min speed in corner
    min_speed = float(core["speed"].min())

    # Entry speed (at entry distance)
    entry_speeds = core.iloc[:2]["speed"]
    entry_speed = float(entry_speeds.iloc[0]) if len(entry_speeds) > 0 else None

    # Exit speed (at exit distance)
    exit_speeds = core.iloc[-2:]["speed"]
    exit_speed = float(exit_speeds.iloc[-1]) if len(exit_speeds) > 0 else None

    # Throttle on distance: first point after apex where throttle > 50
    post_apex = zone[zone["distance_m"] > apex_m]
    throttle_on = post_apex[post_apex["throttle"] > 50]
    throttle_on_distance = float(throttle_on["distance_m"].iloc[0]) - apex_m if len(throttle_on) > 0 else None

    # Trail braking score: fraction of entry-to-apex zone where both brake and throttle > 10
    entry_to_apex = zone[
        (zone["distance_m"] >= entry_m) & (zone["distance_m"] <= apex_m)
    ]
    if len(entry_to_apex) > 0:
        trail = entry_to_apex[(entry_to_apex["brake"] == True) & (entry_to_apex["throttle"] > 10)]  # noqa: E712
        trail_braking_score = len(trail) / len(entry_to_apex)
    else:
        trail_braking_score = 0.0

    # Gear at apex
    apex_zone = core[
        (core["distance_m"] >= apex_m - 20) & (core["distance_m"] <= apex_m + 20)
    ]
    gear_at_apex = int(apex_zone["gear"].median()) if len(apex_zone) > 0 and apex_zone["gear"].notna().any() else None

    # Time in corner (approximate from speed and distance)
    if len(core) >= 2:
        distances = core["distance_m"].values
        speeds = core["speed"].values
        # Convert km/h to m/s, compute time for each segment
        speeds_ms = np.maximum(speeds, 10) / 3.6  # avoid division by zero
        segment_lengths = np.diff(distances)
        avg_speeds = (speeds_ms[:-1] + speeds_ms[1:]) / 2
        time_s = np.sum(segment_lengths / avg_speeds)
        time_in_corner_ms = int(time_s * 1000)
    else:
        time_in_corner_ms = None

    return {
        "brake_point_m": brake_point_m,
        "min_speed": min_speed,
        "entry_speed": entry_speed,
        "exit_speed": exit_speed,
        "throttle_on_distance": throttle_on_distance,
        "trail_braking_score": trail_braking_score,
        "gear_at_apex": gear_at_apex,
        "time_in_corner_ms": time_in_corner_ms,
    }


def compute_corner_profiles_for_session(db: Session, session_id: int) -> int:
    """Compute per-corner driver stats for a session. Returns count of records created."""
    # Get circuit for this session
    row = db.execute(text("""
        SELECT r.circuit_id
        FROM sessions s
        JOIN races r ON s.race_id = r.id
        WHERE s.id = :sid
    """), {"sid": session_id}).fetchone()

    if not row:
        return 0

    circuit_id = row[0]

    # Get corners for this circuit
    corners = db.query(CircuitCorner).filter(CircuitCorner.circuit_id == circuit_id).order_by(CircuitCorner.corner_number).all()
    if not corners:
        logger.warning(f"No corners found for circuit {circuit_id} (session {session_id})")
        return 0

    # Get clean laps
    clean_laps = _get_clean_laps(db, session_id)
    if not clean_laps:
        return 0

    # Group laps by driver
    driver_laps: dict[int, list[int]] = {}
    for driver_id, lap_number in clean_laps:
        driver_laps.setdefault(driver_id, []).append(lap_number)

    # Delete existing stats for this session
    db.execute(
        text("DELETE FROM driver_corner_stats WHERE session_id = :sid"),
        {"sid": session_id},
    )

    count = 0
    for driver_id, laps in driver_laps.items():
        telemetry = _get_telemetry_for_driver_session(db, session_id, driver_id, laps)
        if telemetry.empty:
            continue

        for corner in corners:
            # Extract features per lap, then take medians
            lap_features = []
            for lap_num in laps:
                lap_telem = telemetry[telemetry["lap_number"] == lap_num]
                if lap_telem.empty:
                    continue
                features = _extract_corner_features(lap_telem, corner)
                if features:
                    lap_features.append(features)

            if not lap_features:
                continue

            # Aggregate to medians
            df_feats = pd.DataFrame(lap_features)
            medians = df_feats.median(numeric_only=True)

            stat = DriverCornerStat(
                session_id=session_id,
                driver_id=driver_id,
                corner_id=corner.id,
                brake_point_m=_safe_float(medians.get("brake_point_m")),
                min_speed=_safe_float(medians.get("min_speed")),
                entry_speed=_safe_float(medians.get("entry_speed")),
                exit_speed=_safe_float(medians.get("exit_speed")),
                throttle_on_distance=_safe_float(medians.get("throttle_on_distance")),
                trail_braking_score=_safe_float(medians.get("trail_braking_score")),
                gear_at_apex=_safe_int(medians.get("gear_at_apex")),
                time_in_corner_ms=_safe_int(medians.get("time_in_corner_ms")),
            )
            db.add(stat)
            count += 1

    db.commit()
    logger.info(f"Session {session_id}: created {count} driver-corner stats")
    return count


def _safe_float(val) -> float | None:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    return float(val)


def _safe_int(val) -> int | None:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    return int(val)


def compute_all_corner_profiles(db: Session) -> dict[int, int]:
    """Compute corner profiles for all race sessions with telemetry."""
    sessions = db.execute(text("""
        SELECT DISTINCT s.id, r.name
        FROM sessions s
        JOIN races r ON s.race_id = r.id
        JOIN telemetry_samples ts ON ts.session_id = s.id
        WHERE s.session_type = 'R'
        ORDER BY s.id
    """)).fetchall()

    results = {}
    for session_id, race_name in sessions:
        count = compute_corner_profiles_for_session(db, session_id)
        results[session_id] = count
        logger.info(f"  {race_name}: {count} corner stats")

    return results
