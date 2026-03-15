"""Driver DNA: feature computation, clustering, and similarity.

Builds a ~10-dimensional feature vector per driver per season, runs KMeans
clustering, PCA/t-SNE for visualization, and computes pairwise cosine similarity.
"""

import json
import logging

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models import DriverDnaFeature, DriverSimilarity

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "brake_aggression",
    "corner_entry_speed",
    "corner_exit_efficiency",
    "throttle_application",
    "tyre_management",
    "quali_vs_race",
    "overtake_aggression",
    "consistency",
    "avg_corner_time_delta",
    "gear_usage_style",
]

# Minimum number of races with corner data to include a driver in clustering
MIN_RACES_FOR_CLUSTERING = 3


def _compute_corner_features(db: Session, driver_id: int, season_year: int) -> dict[str, float | None]:
    """Compute corner-derived features using raw physical units and ratios."""
    result = db.execute(text("""
        WITH driver_stats AS (
            SELECT dcs.corner_id,
                   cc.corner_type,
                   dcs.brake_point_m,
                   dcs.entry_speed,
                   dcs.exit_speed,
                   dcs.min_speed,
                   dcs.throttle_on_distance,
                   dcs.gear_at_apex,
                   dcs.time_in_corner_ms,
                   cc.entry_distance_m,
                   cc.apex_distance_m
            FROM driver_corner_stats dcs
            JOIN sessions s ON dcs.session_id = s.id
            JOIN races r ON s.race_id = r.id
            JOIN seasons se ON r.season_id = se.id
            JOIN circuit_corners cc ON dcs.corner_id = cc.id
            WHERE se.year = :year AND dcs.driver_id = :did
        ),
        field_corner_times AS (
            SELECT dcs.corner_id,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY dcs.time_in_corner_ms) as med_time
            FROM driver_corner_stats dcs
            JOIN sessions s ON dcs.session_id = s.id
            JOIN races r ON s.race_id = r.id
            JOIN seasons se ON r.season_id = se.id
            WHERE se.year = :year
              AND dcs.time_in_corner_ms IS NOT NULL
            GROUP BY dcs.corner_id
        )
        SELECT
            -- brake_aggression: distance from brake point to corner entry (meters before entry)
            -- Higher = later braker (brakes closer to entry). Use entry_distance - brake_point.
            AVG(CASE WHEN ds.brake_point_m IS NOT NULL AND ds.entry_distance_m IS NOT NULL
                THEN ds.entry_distance_m - ds.brake_point_m END) as brake_aggression,
            -- corner_entry_speed: entry speed as fraction of max straight-line speed for session
            -- We approximate by using entry_speed directly (raw km/h)
            AVG(ds.entry_speed) as avg_entry_speed,
            -- corner_exit_efficiency: exit_speed / entry_speed ratio
            AVG(CASE WHEN ds.entry_speed > 0 THEN ds.exit_speed / ds.entry_speed END) as exit_efficiency,
            -- throttle_application: distance from apex to throttle point (lower = earlier throttle)
            AVG(CASE WHEN ds.throttle_on_distance IS NOT NULL AND ds.apex_distance_m IS NOT NULL
                THEN ds.throttle_on_distance - ds.apex_distance_m END) as throttle_app,
            -- avg_corner_time_delta: mean time-in-corner vs field median (ms, negative = faster)
            AVG(CASE WHEN ds.time_in_corner_ms IS NOT NULL AND fct.med_time IS NOT NULL
                THEN ds.time_in_corner_ms - fct.med_time END) as corner_time_delta,
            -- gear_usage_style: avg gear at apex for slow corners
            AVG(CASE WHEN ds.corner_type = 'slow' AND ds.gear_at_apex IS NOT NULL
                THEN ds.gear_at_apex END) as gear_slow_corners
        FROM driver_stats ds
        LEFT JOIN field_corner_times fct ON fct.corner_id = ds.corner_id
    """), {"year": season_year, "did": driver_id}).fetchone()

    if result is None:
        return {}

    return {
        "brake_aggression": _to_float(result[0]),
        "corner_entry_speed": _to_float(result[1]),
        "corner_exit_efficiency": _to_float(result[2]),
        "throttle_application": _to_float(result[3]),
        "avg_corner_time_delta": _to_float(result[4]),
        "gear_usage_style": _to_float(result[5]),
    }


def _compute_race_features(db: Session, driver_id: int, season_year: int) -> dict[str, float | None]:
    """Compute race-level features using rank percentiles to avoid scale issues."""

    # Tyre management: rank-based (driver's avg deg_rate rank, 1=best/lowest deg)
    tyre_rank = db.execute(text("""
        WITH driver_deg AS (
            SELECT tdc.driver_id,
                   AVG(tdc.deg_rate_ms_per_lap) as avg_deg
            FROM tyre_deg_curves tdc
            JOIN sessions s ON tdc.session_id = s.id
            JOIN races r ON s.race_id = r.id
            JOIN seasons se ON r.season_id = se.id
            WHERE se.year = :year
              AND tdc.deg_rate_ms_per_lap IS NOT NULL
            GROUP BY tdc.driver_id
        ),
        ranked AS (
            SELECT driver_id,
                   avg_deg,
                   PERCENT_RANK() OVER (ORDER BY avg_deg DESC) as pct_rank
            FROM driver_deg
        )
        SELECT pct_rank FROM ranked WHERE driver_id = :did
    """), {"year": season_year, "did": driver_id}).scalar()

    # Quali vs race: rank of (best_race_lap / best_quali_lap) ratio
    quali_race_rank = db.execute(text("""
        WITH driver_ratios AS (
            SELECT rr.driver_id,
                   AVG(best_race.lap_ms::float / NULLIF(best_quali.quali_ms, 0)) as pace_ratio
            FROM race_results rr
            JOIN races r ON rr.race_id = r.id
            JOIN seasons s ON r.season_id = s.id
            JOIN sessions se ON se.race_id = r.id AND se.session_type = 'R'
            LEFT JOIN LATERAL (
                SELECT MIN(l.lap_time_ms) as lap_ms
                FROM laps l
                WHERE l.session_id = se.id AND l.driver_id = rr.driver_id
                  AND l.is_pit_in_lap IS NOT TRUE
                  AND l.is_pit_out_lap IS NOT TRUE
                  AND l.lap_time_ms IS NOT NULL
            ) best_race ON true
            LEFT JOIN LATERAL (
                SELECT LEAST(
                    COALESCE(qr.q1_ms, 999999999),
                    COALESCE(qr.q2_ms, 999999999),
                    COALESCE(qr.q3_ms, 999999999)
                ) as quali_ms
                FROM qualifying_results qr
                WHERE qr.race_id = r.id AND qr.driver_id = rr.driver_id
            ) best_quali ON true
            WHERE s.year = :year
              AND best_race.lap_ms IS NOT NULL
              AND best_quali.quali_ms IS NOT NULL
              AND best_quali.quali_ms < 999999999
            GROUP BY rr.driver_id
        ),
        ranked AS (
            SELECT driver_id,
                   PERCENT_RANK() OVER (ORDER BY pace_ratio ASC) as pct_rank
            FROM driver_ratios
        )
        SELECT pct_rank FROM ranked WHERE driver_id = :did
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

    # Consistency: coefficient of variation (std/mean) of lap times, rank percentile
    consistency_rank = db.execute(text("""
        WITH driver_cv AS (
            SELECT sub.driver_id,
                   AVG(sub.cv) as avg_cv
            FROM (
                SELECT l.driver_id,
                       STDDEV(l.lap_time_ms) / NULLIF(AVG(l.lap_time_ms), 0) as cv
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
            GROUP BY sub.driver_id
        ),
        ranked AS (
            SELECT driver_id,
                   PERCENT_RANK() OVER (ORDER BY avg_cv DESC) as pct_rank
            FROM driver_cv
        )
        SELECT pct_rank FROM ranked WHERE driver_id = :did
    """), {"year": season_year, "did": driver_id}).scalar()

    return {
        "tyre_management": _to_float(tyre_rank),
        "quali_vs_race": _to_float(quali_race_rank),
        "overtake_aggression": _to_float(overtake),
        "consistency": _to_float(consistency_rank),
    }


def _count_races_with_corners(db: Session, driver_id: int, season_year: int) -> int:
    """Count how many races a driver has corner data for."""
    result = db.execute(text("""
        SELECT COUNT(DISTINCT r.id)
        FROM driver_corner_stats dcs
        JOIN sessions s ON dcs.session_id = s.id
        JOIN races r ON s.race_id = r.id
        JOIN seasons se ON r.season_id = se.id
        WHERE se.year = :year AND dcs.driver_id = :did
    """), {"year": season_year, "did": driver_id}).scalar()
    return int(result or 0)


def compute_driver_features(db: Session, driver_id: int, season_year: int) -> dict[str, float | None]:
    """Compute full feature vector for a driver in a season."""
    corner_features = _compute_corner_features(db, driver_id, season_year)
    race_features = _compute_race_features(db, driver_id, season_year)
    return {**corner_features, **race_features}


def compute_all_dna(db: Session, season_year: int) -> int:
    """Compute DNA features for all drivers in a season, then cluster."""
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

    # Check corner data availability per driver
    driver_race_counts = {}
    for driver_id, code in drivers:
        driver_race_counts[driver_id] = _count_races_with_corners(db, driver_id, season_year)

    # Compute features for all drivers
    driver_features = {}
    insufficient_drivers = []
    for driver_id, code in drivers:
        features = compute_driver_features(db, driver_id, season_year)
        has_corner_data = driver_race_counts[driver_id] >= MIN_RACES_FOR_CLUSTERING
        if any(v is not None for v in features.values()):
            driver_features[driver_id] = features
            if not has_corner_data:
                insufficient_drivers.append(driver_id)
                logger.info(f"  {code}: insufficient corner data ({driver_race_counts[driver_id]} races)")
            else:
                logger.info(f"  {code}: computed features ({driver_race_counts[driver_id]} races)")

    # Split into clusterable and insufficient
    clusterable_ids = [did for did in driver_features if did not in insufficient_drivers]

    if len(clusterable_ids) < 3:
        logger.warning("Too few drivers with sufficient data for clustering")
        return 0

    # Build feature matrix for clusterable drivers
    feature_matrix = []
    for did in clusterable_ids:
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
    best_k = 3
    best_score = -1
    max_k = min(7, len(clusterable_ids) - 1)

    for k in range(3, max_k + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        logger.info(f"  k={k}, silhouette={score:.3f}")
        if score > best_score:
            best_score = score
            best_k = k

    logger.info(f"Best k={best_k}, silhouette={best_score:.3f}")

    km = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    cluster_labels = km.fit_predict(X_scaled)

    # PCA 2D
    pca = PCA(n_components=2, random_state=42)
    pca_coords = pca.fit_transform(X_scaled)

    # Extract PCA metadata
    pca_info = _extract_pca_info(pca, FEATURE_NAMES)
    logger.info(f"PCA info: {pca_info}")

    # t-SNE 2D
    perplexity = min(5, len(clusterable_ids) - 1)
    tsne = TSNE(n_components=2, random_state=42, perplexity=max(2, perplexity))
    tsne_coords = tsne.fit_transform(X_scaled)

    # Auto-label clusters from dominant features
    cluster_names = _label_clusters(X_scaled, cluster_labels, best_k, FEATURE_NAMES)

    # Log cluster distribution
    for c in range(best_k):
        count = int(np.sum(cluster_labels == c))
        logger.info(f"  Cluster {c} '{cluster_names.get(c, '?')}': {count} drivers")

    # Cosine similarity (on clusterable drivers)
    sim_matrix = cosine_similarity(X_scaled)

    # Delete existing records
    db.execute(text("DELETE FROM driver_dna_features WHERE season_id = :sid"), {"sid": season_id})
    db.execute(text("DELETE FROM driver_similarities WHERE season_id = :sid"), {"sid": season_id})

    # Write DNA features for clusterable drivers
    for i, did in enumerate(clusterable_ids):
        feature_data = {f: float(X[i, j]) for j, f in enumerate(FEATURE_NAMES)}
        # Store PCA info on the first driver's record
        if i == 0:
            feature_data["_pca_info"] = pca_info

        dna = DriverDnaFeature(
            driver_id=did,
            season_id=season_id,
            feature_vector=json.dumps(feature_data),
            cluster_id=int(cluster_labels[i]),
            cluster_label=cluster_names.get(int(cluster_labels[i]), f"Cluster {cluster_labels[i]}"),
            pca_x=float(pca_coords[i, 0]),
            pca_y=float(pca_coords[i, 1]),
            tsne_x=float(tsne_coords[i, 0]),
            tsne_y=float(tsne_coords[i, 1]),
        )
        db.add(dna)

    # Write DNA features for insufficient-data drivers (no cluster)
    for did in insufficient_drivers:
        feature_data = {f: float(driver_features[did].get(f, 0.0) or 0.0) for f in FEATURE_NAMES}
        dna = DriverDnaFeature(
            driver_id=did,
            season_id=season_id,
            feature_vector=json.dumps(feature_data),
            cluster_id=-1,
            cluster_label="Insufficient Data",
            pca_x=None,
            pca_y=None,
            tsne_x=None,
            tsne_y=None,
        )
        db.add(dna)

    # Write similarities (only for clusterable drivers)
    for i, did_a in enumerate(clusterable_ids):
        for j, did_b in enumerate(clusterable_ids):
            if i < j:
                sim = DriverSimilarity(
                    driver_a_id=did_a,
                    driver_b_id=did_b,
                    season_id=season_id,
                    cosine_similarity=float(sim_matrix[i, j]),
                )
                db.add(sim)

    db.commit()
    logger.info(f"Wrote DNA features for {len(clusterable_ids)} clustered + {len(insufficient_drivers)} insufficient drivers, {best_k} clusters")
    return len(clusterable_ids) + len(insufficient_drivers)


def _extract_pca_info(pca: PCA, feature_names: list[str]) -> dict:
    """Extract PCA metadata for axis labels."""
    info = {
        "pc1_variance": round(float(pca.explained_variance_ratio_[0]) * 100, 1),
        "pc2_variance": round(float(pca.explained_variance_ratio_[1]) * 100, 1),
    }

    # Top 2 contributing features per axis (by absolute loading)
    for pc_idx, pc_key in enumerate(["pc1_features", "pc2_features"]):
        loadings = np.abs(pca.components_[pc_idx])
        top_indices = np.argsort(-loadings)[:2]
        info[pc_key] = [feature_names[i] for i in top_indices]

    return info


def _label_clusters(X_scaled: np.ndarray, labels: np.ndarray, k: int, feature_names: list[str]) -> dict[int, str]:
    """Auto-label clusters based on their dominant feature deviations."""
    # Map features to positive-direction labels and negative-direction labels
    label_map = {
        "brake_aggression": ("Late Braker", "Early Braker"),
        "corner_entry_speed": ("Brave Entry", "Cautious Entry"),
        "corner_exit_efficiency": ("Strong Exit", "Weak Exit"),
        "throttle_application": ("Late Throttle", "Early Throttle"),
        "tyre_management": ("Tyre Whisperer", "Hard on Tyres"),
        "quali_vs_race": ("Race Specialist", "Quali Specialist"),
        "overtake_aggression": ("Aggressive Racer", "Position Holder"),
        "consistency": ("Metronomic", "Erratic"),
        "avg_corner_time_delta": ("Slow through Corners", "Corner Speed Demon"),
        "gear_usage_style": ("Aggressive Gearing", "Conservative Gearing"),
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
            if fname in label_map:
                pos_label, neg_label = label_map[fname]
                name = pos_label if cluster_mean[fi] >= 0 else neg_label
                if name not in used_labels:
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
