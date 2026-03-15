"""Driver DNA endpoints: clusters, similarity, comparison."""

import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api.deps import get_db

router = APIRouter(prefix="/api/dna", tags=["driver-dna"])


@router.get("/clusters")
def get_clusters(season: int = Query(...), db: Session = Depends(get_db)):
    """Cluster assignments, PCA/t-SNE coords, feature vectors, and PCA metadata."""
    rows = db.execute(text("""
        SELECT DISTINCT ON (d.id)
               d.id, d.code, d.first_name, d.last_name,
               c.name as team_name,
               dna.cluster_id, dna.cluster_label,
               dna.pca_x, dna.pca_y, dna.tsne_x, dna.tsne_y,
               dna.feature_vector
        FROM driver_dna_features dna
        JOIN drivers d ON dna.driver_id = d.id
        JOIN seasons s ON dna.season_id = s.id
        JOIN driver_race_entries dre ON dre.driver_id = d.id
        JOIN races r ON dre.race_id = r.id AND r.season_id = s.id
        JOIN constructors c ON dre.constructor_id = c.id
        WHERE s.year = :year
        ORDER BY d.id, r.round_number DESC
    """), {"year": season}).fetchall()

    # Extract PCA info from the first record that has it
    pca_info = None
    drivers = []
    for r in rows:
        features = json.loads(r[11]) if r[11] else {}
        if "_pca_info" in features:
            pca_info = features.pop("_pca_info")

        drivers.append({
            "driver_id": r[0], "code": r[1], "first_name": r[2], "last_name": r[3],
            "team": r[4], "cluster_id": r[5], "cluster_label": r[6],
            "pca_x": r[7], "pca_y": r[8], "tsne_x": r[9], "tsne_y": r[10],
            "features": features,
        })

    return {
        "drivers": drivers,
        "pca_info": pca_info,
    }


@router.get("/similarity")
def get_similarity(season: int = Query(...), db: Session = Depends(get_db)):
    """n*n similarity matrix."""
    rows = db.execute(text("""
        SELECT da.code as driver_a, db.code as driver_b,
               ds.cosine_similarity
        FROM driver_similarities ds
        JOIN drivers da ON ds.driver_a_id = da.id
        JOIN drivers db ON ds.driver_b_id = db.id
        JOIN seasons s ON ds.season_id = s.id
        WHERE s.year = :year
        ORDER BY da.code, db.code
    """), {"year": season}).fetchall()

    # Build matrix
    drivers = sorted(set(r[0] for r in rows) | set(r[1] for r in rows))
    matrix = {d: {d: 1.0} for d in drivers}
    for a, b, sim in rows:
        matrix.setdefault(a, {})[b] = sim
        matrix.setdefault(b, {})[a] = sim

    return {"drivers": drivers, "matrix": matrix}


@router.get("/compare")
def compare_drivers(
    driver_a: int = Query(...),
    driver_b: int = Query(...),
    season: int = Query(...),
    db: Session = Depends(get_db),
):
    """Head-to-head radar chart data."""
    rows = db.execute(text("""
        SELECT d.id, d.code, dna.feature_vector
        FROM driver_dna_features dna
        JOIN drivers d ON dna.driver_id = d.id
        JOIN seasons s ON dna.season_id = s.id
        WHERE s.year = :year AND d.id IN (:a, :b)
    """), {"year": season, "a": driver_a, "b": driver_b}).fetchall()

    result = []
    for r in rows:
        features = json.loads(r[2]) if r[2] else {}
        features.pop("_pca_info", None)
        result.append({"driver_id": r[0], "code": r[1], "features": features})

    # Get similarity between them
    sim = db.execute(text("""
        SELECT cosine_similarity
        FROM driver_similarities ds
        JOIN seasons s ON ds.season_id = s.id
        WHERE s.year = :year
          AND ((driver_a_id = :a AND driver_b_id = :b) OR (driver_a_id = :b AND driver_b_id = :a))
    """), {"year": season, "a": driver_a, "b": driver_b}).scalar()

    return {"drivers": result, "similarity": sim}


@router.get("/driver/{driver_id}")
def get_driver_dna(
    driver_id: int,
    season: int = Query(...),
    db: Session = Depends(get_db),
):
    """Individual DNA profile + most/least similar drivers."""
    dna = db.execute(text("""
        SELECT dna.feature_vector, dna.cluster_id, dna.cluster_label,
               dna.pca_x, dna.pca_y, dna.tsne_x, dna.tsne_y
        FROM driver_dna_features dna
        JOIN seasons s ON dna.season_id = s.id
        WHERE s.year = :year AND dna.driver_id = :did
    """), {"year": season, "did": driver_id}).fetchone()

    if not dna:
        return {"error": "No DNA data found"}

    features = json.loads(dna[0]) if dna[0] else {}
    features.pop("_pca_info", None)

    # Most similar
    most_similar = db.execute(text("""
        SELECT d.id, d.code, ds.cosine_similarity
        FROM driver_similarities ds
        JOIN drivers d ON d.id = CASE
            WHEN ds.driver_a_id = :did THEN ds.driver_b_id
            ELSE ds.driver_a_id
        END
        JOIN seasons s ON ds.season_id = s.id
        WHERE s.year = :year
          AND (ds.driver_a_id = :did OR ds.driver_b_id = :did)
        ORDER BY ds.cosine_similarity DESC
        LIMIT 5
    """), {"year": season, "did": driver_id}).fetchall()

    # Least similar
    least_similar = db.execute(text("""
        SELECT d.id, d.code, ds.cosine_similarity
        FROM driver_similarities ds
        JOIN drivers d ON d.id = CASE
            WHEN ds.driver_a_id = :did THEN ds.driver_b_id
            ELSE ds.driver_a_id
        END
        JOIN seasons s ON ds.season_id = s.id
        WHERE s.year = :year
          AND (ds.driver_a_id = :did OR ds.driver_b_id = :did)
        ORDER BY ds.cosine_similarity ASC
        LIMIT 5
    """), {"year": season, "did": driver_id}).fetchall()

    return {
        "features": features,
        "cluster_id": dna[1],
        "cluster_label": dna[2],
        "pca_x": dna[3], "pca_y": dna[4],
        "tsne_x": dna[5], "tsne_y": dna[6],
        "most_similar": [{"id": r[0], "code": r[1], "similarity": r[2]} for r in most_similar],
        "least_similar": [{"id": r[0], "code": r[1], "similarity": r[2]} for r in least_similar],
    }
