"""Driver list endpoint."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api.deps import get_db

router = APIRouter(prefix="/api/drivers", tags=["drivers"])


@router.get("")
def list_drivers(
    season: int | None = Query(None),
    db: Session = Depends(get_db),
):
    """Driver list with DNA cluster badges."""
    if season:
        rows = db.execute(text("""
            SELECT DISTINCT ON (d.id)
                   d.id, d.code, d.first_name, d.last_name, d.nationality,
                   d.permanent_number,
                   c.name as team_name,
                   dna.cluster_id, dna.cluster_label
            FROM drivers d
            JOIN driver_race_entries dre ON dre.driver_id = d.id
            JOIN races r ON dre.race_id = r.id
            JOIN seasons s ON r.season_id = s.id
            JOIN constructors c ON dre.constructor_id = c.id
            LEFT JOIN driver_dna_features dna ON dna.driver_id = d.id AND dna.season_id = s.id
            WHERE s.year = :year
            ORDER BY d.id, r.round_number DESC
        """), {"year": season}).fetchall()
    else:
        rows = db.execute(text("""
            SELECT DISTINCT d.id, d.code, d.first_name, d.last_name, d.nationality,
                   d.permanent_number, NULL, NULL, NULL
            FROM drivers d
            ORDER BY d.last_name
        """)).fetchall()

    return sorted(
        [
            {
                "id": r[0], "code": r[1], "first_name": r[2], "last_name": r[3],
                "nationality": r[4], "permanent_number": r[5],
                "team_name": r[6], "cluster_id": r[7], "cluster_label": r[8],
            }
            for r in rows
        ],
        key=lambda x: x["last_name"] or "",
    )
