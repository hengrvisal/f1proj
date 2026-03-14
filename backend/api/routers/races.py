"""Race list endpoint."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api.deps import get_db

router = APIRouter(prefix="/api/races", tags=["races"])


@router.get("")
def list_races(season: int = Query(...), db: Session = Depends(get_db)):
    """Race list with session IDs."""
    rows = db.execute(text("""
        SELECT r.id, r.round_number, r.name, r.date,
               c.name as circuit_name, c.id as circuit_id, c.country
        FROM races r
        JOIN seasons s ON r.season_id = s.id
        JOIN circuits c ON r.circuit_id = c.id
        WHERE s.year = :year
        ORDER BY r.round_number
    """), {"year": season}).fetchall()

    result = []
    for r in rows:
        sessions = db.execute(text("""
            SELECT id, session_type, date FROM sessions
            WHERE race_id = :rid ORDER BY date
        """), {"rid": r[0]}).fetchall()

        result.append({
            "id": r[0], "round": r[1], "name": r[2],
            "date": str(r[3]) if r[3] else None,
            "circuit": r[4], "circuit_id": r[5], "country": r[6],
            "sessions": [
                {"id": s[0], "type": s[1], "date": str(s[2]) if s[2] else None}
                for s in sessions
            ],
        })

    return result
