"""Driver DNA: feature computation, clustering, and similarity.

Builds a ~15-dimensional feature vector per driver per season, runs KMeans
clustering, PCA/t-SNE for visualization, and computes pairwise cosine similarity.
"""

import json
import logging

import numpy as np
from scipy.spatial.distance import cosine
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models import DriverDnaFeature, DriverSimilarity

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "brake_point_rel_mean",
    "brake_point_rel_std",
    "corner_entry_speed_rel",
    "corner_apex_speed_rel",
    "corner_exit_speed_rel",
    "throttle_delay_after_apex",
    "trail_braking_score",
    "slow_corner_speed",
    "medium_corner_speed",
    "fast_corner_speed",
    "avg_tyre_deg_rate",
    "quali_race_pace_delta",
    "overtake_aggression",
    "consistency_score",
    "wet_performance_delta",
]


def _compute_corner_features(db: Session, driver_id: int, season_year: int) -> dict[str, float | None]:
    """Compute corner-derived features averaged across all circuits in the season."""
    # Get driver's corner stats relative to field medians
    result = db.execute(text("""
        WITH field_medians AS (
            SELECT dcs.corner_id,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY dcs.brake_point_m) as med_brake,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY dcs.min_speed) as med_min_speed,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY dcs.entry_speed) as med_entry,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY dcs.exit_speed) as med_exit,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY dcs.throttle_on_distance) as med_throttle_delay
            FROM driver_corner_stats dcs
            JOIN sessions s ON dcs.session_id = s.id
            JOIN races r ON s.race_id = r.id
            JOIN seasons se ON r.season_id = se.id
            WHERE se.year = :year
            GROUP BY dcs.corner_id
        ),
        driver_stats AS (
            SELECT dcs.corner_id,
                   cc.corner_type,
                   dcs.brake_point_m,
                   dcs.min_speed,
                   dcs.entry_speed,
                   dcs.exit_speed,
                   dcs.throttle_on_distance,
                   dcs.trail_braking_score,
                   fm.med_brake,
                   fm.med_min_speed,
                   fm.med_entry,
                   fm.med_exit,
                   fm.med_throttle_delay
            FROM driver_corner_stats dcs
            JOIN sessions s ON dcs.session_id = s.id
            JOIN races r ON s.race_id = r.id
            JOIN seasons se ON r.season_id = se.id
            JOIN circuit_corners cc ON dcs.corner_id = cc.id
            JOIN field_medians fm ON fm.corner_id = dcs.corner_id
            WHERE se.year = :year AND dcs.driver_id = :did
        )
        SELECT
            AVG(CASE WHEN med_brake > 0 THEN (brake_point_m - med_brake) / NULLIF(med_brake, 0) END) as brake_rel_mean,
            COALESCE(STDDEV(CASE WHEN med_brake > 0 THEN (brake_point_m - med_brake) / NULLIF(med_brake, 0) END), 0) as brake_rel_std,
            AVG(CASE WHEN med_entry > 0 THEN (entry_speed - med_entry) / NULLIF(med_entry, 0) END) as entry_speed_rel,
            AVG(CASE WHEN med_min_speed > 0 THEN (min_speed - med_min_speed) / NULLIF(med_min_speed, 0) END) as apex_speed_rel,
            AVG(CASE WHEN med_exit > 0 THEN (exit_speed - med_exit) / NULLIF(med_exit, 0) END) as exit_speed_rel,
            AVG(throttle_on_distance - med_throttle_delay) as throttle_delay,
            AVG(trail_braking_score) as trail_braking,
            AVG(CASE WHEN corner_type = 'slow' THEN min_speed END) as slow_speed,
            AVG(CASE WHEN corner_type = 'medium' THEN min_speed END) as med_speed,
            AVG(CASE WHEN corner_type = 'fast' THEN min_speed END) as fast_speed
        FROM driver_stats
    """), {"year": season_year, "did": driver_id}).fetchone()

    if result is None:
        return {}

    return {
        "brake_point_rel_mean": _to_float(result[0]),
        "brake_point_rel_std": _to_float(result[1]),
        "corner_entry_speed_rel": _to_float(result[2]),
        "corner_apex_speed_rel": _to_float(result[3]),
        "corner_exit_speed_rel": _to_float(result[4]),
        "throttle_delay_after_apex": _to_float(result[5]),
        "trail_braking_score": _to_float(result[6]),
        "slow_corner_speed": _to_float(result[7]),
        "medium_corner_speed": _to_float(result[8]),
        "fast_corner_speed": _to_float(result[9]),
    }


def _compute_race_features(db: Session, driver_id: int, season_year: int) -> dict[str, float | None]:
    """Compute race-level features for a driver in a season."""
    # Avg tyre deg rate
    deg_result = db.execute(text("""
        SELECT AVG(tdc.deg_rate_ms_per_lap)
        FROM tyre_deg_curves tdc
        JOIN sessions s ON tdc.session_id = s.id
        JOIN races r ON s.race_id = r.id
        JOIN seasons se ON r.season_id = se.id
        WHERE se.year = :year AND tdc.driver_id = :did
          AND tdc.deg_rate_ms_per_lap IS NOT NULL
    """), {"year": season_year, "did": driver_id}).scalar()

    # Normalize deg rate relative to field
    field_avg_deg = db.execute(text("""
        SELECT AVG(tdc.deg_rate_ms_per_lap)
        FROM tyre_deg_curves tdc
        JOIN sessions s ON tdc.session_id = s.id
        JOIN races r ON s.race_id = r.id
        JOIN seasons se ON r.season_id = se.id
        WHERE se.year = :year AND tdc.deg_rate_ms_per_lap IS NOT NULL
    """), {"year": season_year}).scalar()

    avg_deg_normalized = None
    if deg_result is not None and field_avg_deg and field_avg_deg > 0:
        avg_deg_normalized = (deg_result - field_avg_deg) / field_avg_deg

    # Quali vs race pace delta
    quali_race_delta = db.execute(text("""
        WITH quali_pace AS (
            SELECT r.id as race_id,
                   LEAST(COALESCE(qr.q1_ms, 999999999), COALESCE(qr.q2_ms, 999999999), COALESCE(qr.q3_ms, 999999999)) as best_quali_ms
            FROM qualifying_results qr
            JOIN races r ON qr.race_id = r.id
            JOIN seasons s ON r.season_id = s.id
            WHERE s.year = :year AND qr.driver_id = :did
              AND LEAST(COALESCE(qr.q1_ms, 999999999), COALESCE(qr.q2_ms, 999999999), COALESCE(qr.q3_ms, 999999999)) < 999999999
        ),
        race_pace AS (
            SELECT l.session_id, MIN(l.lap_time_ms) as best_race_lap_ms
            FROM laps l
            JOIN sessions s ON l.session_id = s.id
            JOIN races r ON s.race_id = r.id
            JOIN seasons se ON r.season_id = se.id
            WHERE se.year = :year AND l.driver_id = :did
              AND s.session_type = 'R'
              AND l.is_pit_in_lap IS NOT TRUE
              AND l.is_pit_out_lap IS NOT TRUE
              AND l.lap_time_ms IS NOT NULL
            GROUP BY l.session_id
        )
        SELECT AVG(rp.best_race_lap_ms - qp.best_quali_ms)
        FROM quali_pace qp
        JOIN races r ON qp.race_id = r.id
        JOIN sessions s ON s.race_id = r.id AND s.session_type = 'R'
        JOIN race_pace rp ON rp.session_id = s.id
    """), {"year": season_year, "did": driver_id}).scalar()

    # Overtake aggression: avg position gains in first 5 laps
    overtake = db.execute(text("""
        SELECT AVG(rr.grid_position - pos_5.position)
        FROM race_results rr
        JOIN races r ON rr.race_id = r.id
        JOIN seasons s ON r.season_id = s.id
        JOIN sessions se ON se.race_id = r.id AND se.session_type = 'R'
        LEFT JOIN LATERAL (
            SELECT position FROM laps
            WHERE session_id = se.id AND driver_id = rr.driver_id AND lap_number = 5
            LIMIT 1
        ) pos_5 ON true
        WHERE s.year = :year AND rr.driver_id = :did
          AND rr.grid_position IS NOT NULL
          AND pos_5.position IS NOT NULL
    """), {"year": season_year, "did": driver_id}).scalar()

    # Consistency score: avg lap time std dev across races
    consistency = db.execute(text("""
        SELECT AVG(lap_std)
        FROM (
            SELECT STDDEV(l.lap_time_ms) as lap_std
            FROM laps l
            JOIN sessions s ON l.session_id = s.id
            JOIN races r ON s.race_id = r.id
            JOIN seasons se ON r.season_id = se.id
            WHERE se.year = :year AND l.driver_id = :did
              AND s.session_type = 'R'
              AND l.is_pit_in_lap IS NOT TRUE
              AND l.is_pit_out_lap IS NOT TRUE
              AND l.lap_time_ms IS NOT NULL
            GROUP BY l.session_id
            HAVING COUNT(*) >= 5
        ) sub
    """), {"year": season_year, "did": driver_id}).scalar()

    # Normalize consistency (lower = more consistent, invert for feature)
    field_consistency = db.execute(text("""
        SELECT AVG(lap_std)
        FROM (
            SELECT driver_id, STDDEV(l.lap_time_ms) as lap_std
            FROM laps l
            JOIN sessions s ON l.session_id = s.id
            JOIN races r ON s.race_id = r.id
            JOIN seasons se ON r.season_id = se.id
            WHERE se.year = :year
              AND s.session_type = 'R'
              AND l.is_pit_in_lap IS NOT TRUE
              AND l.is_pit_out_lap IS NOT TRUE
              AND l.lap_time_ms IS NOT NULL
            GROUP BY l.session_id, l.driver_id
            HAVING COUNT(*) >= 5
        ) sub
    """), {"year": season_year}).scalar()

    consistency_normalized = None
    if consistency is not None and field_consistency and field_consistency > 0:
        consistency_normalized = (field_consistency - consistency) / field_consistency  # positive = more consistent

    # Wet performance (placeholder — requires identifying wet sessions)
    wet_delta = db.execute(text("""
        SELECT AVG(wet_pos - dry_pos)
        FROM (
            SELECT rr.driver_id,
                   rr.finish_position as wet_pos,
                   AVG(rr2.finish_position) as dry_pos
            FROM race_results rr
            JOIN races r ON rr.race_id = r.id
            JOIN seasons s ON r.season_id = s.id
            JOIN sessions se ON se.race_id = r.id AND se.session_type = 'R'
            JOIN weather w ON w.session_id = se.id AND w.rainfall = true
            LEFT JOIN LATERAL (
                SELECT AVG(finish_position) as finish_position
                FROM race_results
                WHERE driver_id = rr.driver_id
                  AND race_id IN (
                      SELECT r2.id FROM races r2
                      JOIN seasons s2 ON r2.season_id = s2.id
                      WHERE s2.year = :year
                  )
            ) rr2 ON true
            WHERE s.year = :year AND rr.driver_id = :did
              AND rr.finish_position IS NOT NULL
            GROUP BY rr.driver_id, rr.finish_position
        ) sub
    """), {"year": season_year, "did": driver_id}).scalar()

    return {
        "avg_tyre_deg_rate": _to_float(avg_deg_normalized),
        "quali_race_pace_delta": _to_float(quali_race_delta),
        "overtake_aggression": _to_float(overtake),
        "consistency_score": _to_float(consistency_normalized),
        "wet_performance_delta": _to_float(wet_delta),
    }


def compute_driver_features(db: Session, driver_id: int, season_year: int) -> dict[str, float | None]:
    """Compute full feature vector for a driver in a season."""
    corner_features = _compute_corner_features(db, driver_id, season_year)
    race_features = _compute_race_features(db, driver_id, season_year)
    return {**corner_features, **race_features}


def compute_all_dna(db: Session, season_year: int) -> int:
    """Compute DNA features for all drivers in a season, then cluster."""
    # Get season
    season = db.execute(
        text("SELECT id FROM seasons WHERE year = :year"),
        {"year": season_year},
    ).fetchone()
    if not season:
        logger.error(f"Season {season_year} not found")
        return 0

    season_id = season[0]

    # Get all drivers who participated in this season
    drivers = db.execute(text("""
        SELECT DISTINCT d.id, d.code
        FROM drivers d
        JOIN driver_race_entries dre ON dre.driver_id = d.id
        JOIN races r ON dre.race_id = r.id
        JOIN seasons s ON r.season_id = s.id
        WHERE s.year = :year
        ORDER BY d.id
    """), {"year": season_year}).fetchall()

    logger.info(f"Computing DNA features for {len(drivers)} drivers in {season_year}")

    # Compute features
    driver_features = {}
    for driver_id, code in drivers:
        features = compute_driver_features(db, driver_id, season_year)
        if any(v is not None for v in features.values()):
            driver_features[driver_id] = features
            logger.info(f"  {code}: computed features")

    if len(driver_features) < 3:
        logger.warning("Too few drivers with features for clustering")
        return 0

    # Build feature matrix
    driver_ids = list(driver_features.keys())
    feature_matrix = []
    for did in driver_ids:
        vec = [driver_features[did].get(f, 0.0) or 0.0 for f in FEATURE_NAMES]
        feature_matrix.append(vec)

    X = np.array(feature_matrix)

    # Impute NaN with column means
    col_means = np.nanmean(X, axis=0)
    for i in range(X.shape[1]):
        mask = np.isnan(X[:, i])
        X[mask, i] = col_means[i] if not np.isnan(col_means[i]) else 0.0

    # Scale
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # KMeans — try k=3..7, pick best silhouette
    from sklearn.metrics import silhouette_score

    best_k = 3
    best_score = -1
    max_k = min(7, len(driver_ids) - 1)

    for k in range(3, max_k + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        if score > best_score:
            best_score = score
            best_k = k

    logger.info(f"Best k={best_k}, silhouette={best_score:.3f}")

    km = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    cluster_labels = km.fit_predict(X_scaled)

    # PCA 2D
    pca = PCA(n_components=2, random_state=42)
    pca_coords = pca.fit_transform(X_scaled)

    # t-SNE 2D
    perplexity = min(5, len(driver_ids) - 1)
    tsne = TSNE(n_components=2, random_state=42, perplexity=max(2, perplexity))
    tsne_coords = tsne.fit_transform(X_scaled)

    # Auto-label clusters from dominant features
    cluster_names = _label_clusters(X_scaled, cluster_labels, best_k, FEATURE_NAMES)

    # Cosine similarity
    from sklearn.metrics.pairwise import cosine_similarity
    sim_matrix = cosine_similarity(X_scaled)

    # Delete existing records
    db.execute(text("DELETE FROM driver_dna_features WHERE season_id = :sid"), {"sid": season_id})
    db.execute(text("DELETE FROM driver_similarities WHERE season_id = :sid"), {"sid": season_id})

    # Write DNA features
    for i, did in enumerate(driver_ids):
        dna = DriverDnaFeature(
            driver_id=did,
            season_id=season_id,
            feature_vector=json.dumps({f: float(X[i, j]) for j, f in enumerate(FEATURE_NAMES)}),
            cluster_id=int(cluster_labels[i]),
            cluster_label=cluster_names.get(int(cluster_labels[i]), f"Cluster {cluster_labels[i]}"),
            pca_x=float(pca_coords[i, 0]),
            pca_y=float(pca_coords[i, 1]),
            tsne_x=float(tsne_coords[i, 0]),
            tsne_y=float(tsne_coords[i, 1]),
        )
        db.add(dna)

    # Write similarities
    for i, did_a in enumerate(driver_ids):
        for j, did_b in enumerate(driver_ids):
            if i < j:
                sim = DriverSimilarity(
                    driver_a_id=did_a,
                    driver_b_id=did_b,
                    season_id=season_id,
                    cosine_similarity=float(sim_matrix[i, j]),
                )
                db.add(sim)

    db.commit()
    logger.info(f"Wrote DNA features for {len(driver_ids)} drivers, {best_k} clusters")
    return len(driver_ids)


def _label_clusters(X_scaled: np.ndarray, labels: np.ndarray, k: int, feature_names: list[str]) -> dict[int, str]:
    """Auto-label clusters based on their dominant feature deviations."""
    label_map = {
        "brake_point_rel_mean": "Late Braker",
        "trail_braking_score": "Trail Braker",
        "overtake_aggression": "Aggressive",
        "consistency_score": "Consistent",
        "corner_exit_speed_rel": "Strong Exit",
        "corner_entry_speed_rel": "Brave Entry",
        "avg_tyre_deg_rate": "Tyre Whisperer",
        "slow_corner_speed": "Slow Corner Specialist",
        "fast_corner_speed": "High-Speed Specialist",
    }

    cluster_names = {}
    used_labels = set()

    for c in range(k):
        mask = labels == c
        if not mask.any():
            cluster_names[c] = f"Cluster {c}"
            continue

        cluster_mean = X_scaled[mask].mean(axis=0)
        # Find feature with highest absolute deviation
        sorted_features = np.argsort(-np.abs(cluster_mean))

        for fi in sorted_features:
            fname = feature_names[fi]
            if fname in label_map and label_map[fname] not in used_labels:
                name = label_map[fname]
                if cluster_mean[fi] < 0 and fname in ("brake_point_rel_mean",):
                    name = "Early Braker"
                cluster_names[c] = name
                used_labels.add(name)
                break
        else:
            cluster_names[c] = f"Cluster {c}"

    return cluster_names


def _to_float(val) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        return None if np.isnan(f) or np.isinf(f) else f
    except (TypeError, ValueError):
        return None
