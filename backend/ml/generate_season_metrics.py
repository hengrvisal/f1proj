"""Generate per-race-round driver metrics CSV for season trajectory charts.

Outputs: data/season_metrics.csv

Metrics computed per (driver, race_round):
  - consistency: 1 - CV of lap times (higher = more consistent)
  - entry_speed: avg corner entry speed (km/h)
  - throttle_application: avg throttle-on delay after apex (inverted: lower delay = higher score)
  - overtake_rate: performance vs expectation (50 = met expectation for grid slot)
  - tyre_management: avg deg rate (inverted: lower deg = higher score)
  - quali_proxy: best quali time percentile vs field (higher = faster) — per-race normalised

Telemetry metrics (consistency, entry_speed, throttle_application,
tyre_management) are normalised PER-RACE to 0–100, excluding DNF drivers
from the normalisation pool (but still assigning them a score).
quali_proxy is per-race percentile (unchanged).
overtake_rate is 0-100 by construction using expectation-relative scoring.

Also includes:
  - *_raw columns: pre-normalisation raw values
  - had_dnf: whether the driver DNF'd that race
  - had_safety_car: whether a safety car was deployed during the race session
"""

import csv
import sys
from pathlib import Path

import numpy as np
from sqlalchemy import text

from backend.database import engine

# Columns that get per-race normalisation (DNF-excluded)
PER_RACE_NORM_COLS = [
    "consistency", "entry_speed", "throttle_application",
    "tyre_management",
]

# Which columns are "inverted" (raw high = bad, so score should be inverted)
INVERTED_COLS = {"throttle_application", "tyre_management"}

# Statuses that count as finishing the race
FINISHED_STATUSES = {"Finished", "Lapped", "+1 Lap", "+2 Laps", "+3 Laps"}


def _build_expected_finish_table(conn) -> dict[int, dict[int, float]]:
    """Build per-season expected finish position for each grid slot.

    Returns {season_year: {grid_position: avg_finish_position}}.
    Only includes drivers who finished the race (not DNF).
    """
    results = conn.execute(text("""
        SELECT se.year, rr.grid_position, rr.finish_position, rr.status
        FROM race_results rr
        JOIN races r ON rr.race_id = r.id
        JOIN seasons se ON r.season_id = se.id
        WHERE rr.grid_position IS NOT NULL
          AND rr.finish_position IS NOT NULL
    """)).fetchall()

    # Group by (season, grid_position) — only finished drivers
    from collections import defaultdict
    grid_finishes: dict[int, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for year, grid_pos, finish_pos, status in results:
        if status in FINISHED_STATUSES:
            grid_finishes[year][grid_pos].append(finish_pos)

    expected: dict[int, dict[int, float]] = {}
    for year, grid_data in grid_finishes.items():
        expected[year] = {}
        for grid_pos, finishes in grid_data.items():
            expected[year][grid_pos] = sum(finishes) / len(finishes)
        # Fill missing grid slots with neutral expectation
        for i in range(1, 25):
            if i not in expected[year]:
                expected[year][i] = float(i)

    return expected


def _compute_overtake_rate(
    grid_pos: int,
    finish_pos: int,
    status: str,
    expected_table: dict[int, float],
    total_drivers: int,
) -> tuple[float | None, float | None]:
    """Compute expectation-relative overtake rate.

    Uses a symmetric scale: delta is mapped to 0-100 where 50 = met expectation.
    The max possible delta (total_drivers - 1) maps to the extremes.
    This avoids front-row bias where tiny deltas near P1 get inflated.

    Returns (score 0-100, raw delta vs expectation).
    """
    if status not in FINISHED_STATUSES:
        return None, None

    expected = expected_table.get(int(grid_pos), float(grid_pos))
    delta = expected - finish_pos  # positive = beat expectation

    # Symmetric scale: max possible delta is roughly total_drivers - 1
    max_delta = max(total_drivers - 1, 1)
    score = 50 + (delta / max_delta * 50)

    raw = round(delta, 1)
    return round(min(100.0, max(0.0, score)), 1), raw


def _count_overtakes(conn, session_id: int) -> dict[int, int]:
    """Count on-track passes per driver from lap-by-lap position changes.

    Excludes pit-out laps (strategy gains) and safety car laps (shuffles).
    Returns {driver_id: pass_count}.
    """
    # Get lap position data
    lap_rows = conn.execute(text("""
        SELECT driver_id, lap_number, position, is_pit_out_lap
        FROM laps
        WHERE session_id = :sid AND position IS NOT NULL
        ORDER BY driver_id, lap_number
    """), {"sid": session_id}).fetchall()

    # Build safety car active laps
    sc_laps: set[int] = set()
    sc_messages = conn.execute(text("""
        SELECT lap_number, message
        FROM race_control_messages
        WHERE session_id = :sid AND category = 'SafetyCar'
        ORDER BY lap_number, id
    """), {"sid": session_id}).fetchall()

    # Only filter SC laps if all messages have lap numbers
    has_null_laps = any(row[0] is None for row in sc_messages)
    if not has_null_laps and sc_messages:
        sc_start = None
        for lap_num, message in sc_messages:
            msg_upper = (message or "").upper()
            if "DEPLOYED" in msg_upper:
                sc_start = lap_num
            elif sc_start is not None and ("ENDING" in msg_upper or "IN THIS LAP" in msg_upper):
                for lap in range(sc_start, lap_num + 1):
                    sc_laps.add(lap)
                sc_start = None
        # If SC was deployed but never ended, mark remaining laps
        if sc_start is not None:
            max_lap = max((r[1] for r in lap_rows), default=sc_start)
            for lap in range(sc_start, max_lap + 1):
                sc_laps.add(lap)

    # Count passes per driver
    from collections import defaultdict
    driver_passes: dict[int, int] = defaultdict(int)
    prev: dict[int, int] = {}  # driver_id -> previous position

    for driver_id, lap_number, position, is_pit_out in lap_rows:
        if driver_id in prev:
            if (not is_pit_out
                    and lap_number not in sc_laps
                    and position < prev[driver_id]):
                driver_passes[driver_id] += prev[driver_id] - position
        prev[driver_id] = position

    return dict(driver_passes)


def _normalize_per_race_clean(rows: list[dict], col: str) -> None:
    """Per-race min-max normalisation, excluding DNF drivers from the pool.

    DNF drivers are still assigned a score (clipped to 0-100) using the
    clean pool's range. Rounds with < 5 clean data points get None.
    """
    inverted = col in INVERTED_COLS

    # Group rows by (season, race_round)
    from collections import defaultdict
    round_groups: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for r in rows:
        round_groups[(r["season"], r["race_round"])].append(r)

    for (_yr, _rnd), round_rows in round_groups.items():
        # Clean pool: non-DNF with non-None values
        clean_vals = [r[col] for r in round_rows if r[col] is not None and not r["had_dnf"]]

        if len(clean_vals) < 5:
            for r in round_rows:
                r[col] = None
            continue

        col_min = min(clean_vals)
        col_max = max(clean_vals)

        if col_max == col_min:
            for r in round_rows:
                if r[col] is not None:
                    r[col] = 50.0
            continue

        rng = col_max - col_min
        for r in round_rows:
            if r[col] is not None:
                normed = (r[col] - col_min) / rng
                if inverted:
                    normed = 1.0 - normed
                r[col] = round(min(100.0, max(0.0, normed * 100)), 1)


def generate(output_path: str = "data/season_metrics.csv") -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with engine.connect() as conn:
        # --- Step 1: Build expected finish table (all seasons) ---
        expected_finish = _build_expected_finish_table(conn)

        # Get all race sessions grouped by race
        races = conn.execute(text("""
            SELECT r.id, r.round_number, r.name, se.year,
                   s_race.id as race_session_id, s_quali.id as quali_session_id
            FROM races r
            JOIN seasons se ON r.season_id = se.id
            LEFT JOIN sessions s_race ON s_race.race_id = r.id AND s_race.session_type = 'R'
            LEFT JOIN sessions s_quali ON s_quali.race_id = r.id AND s_quali.session_type = 'Q'
            ORDER BY se.year, r.round_number
        """)).fetchall()

        rows: list[dict] = []

        for race in races:
            race_id, round_num, race_name, year, race_sid, quali_sid = race
            short_name = _short_race_name(race_name)

            if not race_sid:
                continue

            # --- Safety car detection for this race session ---
            sc_row = conn.execute(text("""
                SELECT EXISTS(
                    SELECT 1 FROM race_control_messages
                    WHERE session_id = :sid
                      AND message ILIKE '%%SAFETY CAR%%'
                )
            """), {"sid": race_sid}).fetchone()
            had_safety_car = bool(sc_row[0]) if sc_row else False

            # --- DNF detection per driver ---
            dnf_data = conn.execute(text("""
                SELECT driver_id, status
                FROM race_results
                WHERE race_id = :race_id
            """), {"race_id": race_id}).fetchall()
            driver_dnf: dict[int, bool] = {}
            for did, status in dnf_data:
                driver_dnf[did] = status not in FINISHED_STATUSES if status else False

            # --- Consistency: 1 - CV of lap times per driver ---
            lap_data = conn.execute(text("""
                SELECT driver_id, array_agg(lap_time_ms ORDER BY lap_number) as times
                FROM laps
                WHERE session_id = :sid
                  AND lap_time_ms IS NOT NULL
                  AND is_pit_in_lap IS NOT TRUE
                  AND is_pit_out_lap IS NOT TRUE
                GROUP BY driver_id
                HAVING count(*) >= 5
            """), {"sid": race_sid}).fetchall()

            driver_consistency_raw: dict[int, float] = {}
            for did, times in lap_data:
                arr = np.array([t for t in times if t is not None], dtype=float)
                if len(arr) >= 5:
                    cv = float(np.std(arr) / np.mean(arr))
                    driver_consistency_raw[did] = round(1 - cv, 6)

            # --- Corner features: entry_speed (raw values) ---
            corner_data = conn.execute(text("""
                SELECT dcs.driver_id,
                       avg(dcs.entry_speed) as avg_entry
                FROM driver_corner_stats dcs
                JOIN sessions s ON dcs.session_id = s.id
                WHERE s.race_id = :race_id
                GROUP BY dcs.driver_id
            """), {"race_id": race_id}).fetchall()

            driver_entry_raw: dict[int, float] = {}
            for did, avg_e in corner_data:
                if avg_e is not None:
                    driver_entry_raw[did] = round(float(avg_e), 4)

            # --- Overtake rate: expectation-relative ---
            race_results = conn.execute(text("""
                SELECT driver_id, grid_position, finish_position, status
                FROM race_results
                WHERE race_id = :race_id
            """), {"race_id": race_id}).fetchall()

            total_drivers = len(race_results)
            season_expected = expected_finish.get(year, {})
            driver_overtake: dict[int, float] = {}
            driver_overtake_raw: dict[int, float] = {}
            for did, grid_pos, finish_pos, status in race_results:
                if grid_pos is None or finish_pos is None:
                    continue
                score, raw = _compute_overtake_rate(
                    grid_pos, finish_pos, status or "",
                    season_expected, total_drivers,
                )
                if score is not None:
                    driver_overtake[did] = score
                if raw is not None:
                    driver_overtake_raw[did] = raw

            # --- On-track pass counting ---
            driver_passes = _count_overtakes(conn, race_sid)

            # --- Throttle application: avg delay after apex (raw, lower = better) ---
            throttle_data = conn.execute(text("""
                SELECT dcs.driver_id,
                       avg(dcs.throttle_on_distance - cc.apex_distance_m) as avg_delay
                FROM driver_corner_stats dcs
                JOIN sessions s ON dcs.session_id = s.id
                JOIN circuit_corners cc ON dcs.corner_id = cc.id
                WHERE s.race_id = :race_id
                  AND dcs.throttle_on_distance IS NOT NULL
                GROUP BY dcs.driver_id
            """), {"race_id": race_id}).fetchall()

            driver_throttle_raw: dict[int, float] = {}
            for did, avg_delay in throttle_data:
                if avg_delay is not None:
                    driver_throttle_raw[did] = round(float(avg_delay), 4)

            # --- Tyre management: avg deg rate (raw, lower = better) ---
            deg_data = conn.execute(text("""
                SELECT driver_id, avg(deg_rate_ms_per_lap) as avg_deg
                FROM tyre_deg_curves
                WHERE session_id = :sid
                  AND deg_rate_ms_per_lap IS NOT NULL
                GROUP BY driver_id
            """), {"sid": race_sid}).fetchall()

            driver_tyre_raw: dict[int, float] = {}
            for did, avg_deg in deg_data:
                if avg_deg is not None:
                    driver_tyre_raw[did] = round(float(avg_deg), 4)

            # --- Quali proxy: best Q time percentile (per-race, unchanged) ---
            driver_quali: dict[int, float] = {}
            driver_quali_raw: dict[int, float] = {}
            if quali_sid:
                quali_data = conn.execute(text("""
                    SELECT driver_id,
                           LEAST(
                               COALESCE(q1_ms, 999999),
                               COALESCE(q2_ms, 999999),
                               COALESCE(q3_ms, 999999)
                           ) as best_time
                    FROM qualifying_results
                    WHERE race_id = :race_id
                """), {"race_id": race_id}).fetchall()

                all_qtimes = []
                for did, best in quali_data:
                    if best and best < 999999:
                        driver_quali_raw[did] = float(best)
                        all_qtimes.append(float(best))

                if all_qtimes:
                    sorted_q = sorted(all_qtimes, reverse=True)  # worst first
                    for did in list(driver_quali_raw):
                        rank = sorted_q.index(driver_quali_raw[did])
                        driver_quali[did] = round(rank / max(len(sorted_q) - 1, 1) * 100, 1)

            # --- Lap count per driver ---
            lap_counts = conn.execute(text("""
                SELECT driver_id, count(*) as cnt
                FROM laps
                WHERE session_id = :sid AND lap_time_ms IS NOT NULL
                GROUP BY driver_id
            """), {"sid": race_sid}).fetchall()
            driver_laps: dict[int, int] = {did: cnt for did, cnt in lap_counts}

            # --- Get driver codes ---
            all_dids = (set(driver_consistency_raw) | set(driver_entry_raw) |
                        set(driver_overtake) | set(driver_throttle_raw) |
                        set(driver_tyre_raw) | set(driver_quali))
            if not all_dids:
                continue

            driver_codes = conn.execute(text("""
                SELECT id, code FROM drivers WHERE id = ANY(:ids)
            """), {"ids": list(all_dids)}).fetchall()
            code_map = {did: code for did, code in driver_codes}

            for did in all_dids:
                code = code_map.get(did)
                if not code:
                    continue

                row = {
                    "driver": code,
                    "race_round": round_num,
                    "race_name": short_name,
                    "season": year,
                    # Raw values (pre-normalisation)
                    "consistency_raw": driver_consistency_raw.get(did),
                    "entry_speed_raw": driver_entry_raw.get(did),
                    "throttle_application_raw": driver_throttle_raw.get(did),
                    "overtake_rate_raw": driver_overtake_raw.get(did),
                    "overtake_passes": driver_passes.get(did),
                    "tyre_management_raw": driver_tyre_raw.get(did),
                    "quali_proxy_raw": driver_quali_raw.get(did),
                    # Placeholders — telemetry cols normalised below per-race
                    "consistency": driver_consistency_raw.get(did),
                    "entry_speed": driver_entry_raw.get(did),
                    "throttle_application": driver_throttle_raw.get(did),
                    "overtake_rate": driver_overtake.get(did),  # already 0-100
                    "tyre_management": driver_tyre_raw.get(did),
                    "quali_proxy": driver_quali.get(did),
                    "lap_count": driver_laps.get(did, 0),
                    "had_dnf": driver_dnf.get(did, False),
                    "had_safety_car": had_safety_car,
                }
                rows.append(row)

    # --- Per-race normalisation for telemetry metrics (DNF-excluded) ---
    for col in PER_RACE_NORM_COLS:
        _normalize_per_race_clean(rows, col)

    # Write CSV
    fieldnames = [
        "driver", "race_round", "race_name", "season",
        "consistency", "entry_speed", "throttle_application",
        "overtake_rate", "tyre_management", "quali_proxy",
        "consistency_raw", "entry_speed_raw", "throttle_application_raw",
        "overtake_rate_raw", "overtake_passes", "tyre_management_raw", "quali_proxy_raw",
        "lap_count", "had_dnf", "had_safety_car",
    ]

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")


# Race name abbreviations
_RACE_ABBREVS: dict[str, str] = {
    "bahrain": "BHR", "saudi": "SAU", "jeddah": "JED",
    "australia": "AUS", "melbourne": "MEL",
    "japan": "JPN", "suzuka": "SUZ",
    "china": "CHN", "shanghai": "SHA",
    "miami": "MIA",
    "emilia": "IMO", "imola": "IMO",
    "monaco": "MON",
    "canada": "CAN", "montreal": "MTL",
    "spain": "ESP", "barcelona": "BCN",
    "austria": "AUT", "spielberg": "AUT",
    "britain": "GBR", "silverstone": "GBR",
    "hungary": "HUN", "budapest": "BUD",
    "belgium": "BEL", "spa": "SPA",
    "netherlands": "NED", "zandvoort": "ZAN",
    "italy": "ITA", "monza": "MON",
    "azerbaijan": "AZE", "baku": "BAK",
    "singapore": "SGP",
    "qatar": "QAT", "lusail": "QAT",
    "united states": "USA", "austin": "USA", "cota": "USA",
    "mexico": "MEX",
    "brazil": "BRA", "são paulo": "SAO", "sao paulo": "SAO", "interlagos": "SAO",
    "las vegas": "LVG",
    "abu dhabi": "ABU",
}


def _short_race_name(name: str) -> str:
    lower = name.lower()
    for key, abbr in _RACE_ABBREVS.items():
        if key in lower:
            return abbr
    return name[:3].upper()


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "data/season_metrics.csv"
    generate(output)
