"""Ingest static reference data: seasons, circuits, drivers, constructors."""

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DBSession

from backend.ingestion.jolpica_client import JolpicaClient
from backend.models import Circuit, Constructor, Driver, Season

logger = logging.getLogger(__name__)


def upsert_seasons(session: DBSession, years: list[int]):
    for year in years:
        stmt = insert(Season).values(year=year)
        stmt = stmt.on_conflict_do_nothing(index_elements=["year"])
        session.execute(stmt)
    session.commit()
    logger.info("Upserted %d seasons", len(years))


def upsert_circuits(session: DBSession, client: JolpicaClient, years: list[int]):
    seen = set()
    rows = []
    for year in years:
        for c in client.circuits(year):
            ref = c["circuitId"]
            if ref in seen:
                continue
            seen.add(ref)
            loc = c.get("Location", {})
            rows.append({
                "circuit_ref": ref,
                "name": c["circuitName"],
                "location": loc.get("locality"),
                "country": loc.get("country"),
                "latitude": float(loc["lat"]) if loc.get("lat") else None,
                "longitude": float(loc["long"]) if loc.get("long") else None,
                "url": c.get("url"),
            })
    if rows:
        stmt = insert(Circuit).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["circuit_ref"],
            set_={col: stmt.excluded[col] for col in ["name", "location", "country", "latitude", "longitude", "url"]},
        )
        session.execute(stmt)
        session.commit()
    logger.info("Upserted %d circuits", len(rows))


def upsert_drivers(session: DBSession, client: JolpicaClient, years: list[int]):
    seen = set()
    rows = []
    for year in years:
        for d in client.drivers(year):
            ref = d["driverId"]
            if ref in seen:
                continue
            seen.add(ref)
            dob = d.get("dateOfBirth")
            rows.append({
                "driver_ref": ref,
                "code": d.get("code"),
                "permanent_number": int(d["permanentNumber"]) if d.get("permanentNumber") else None,
                "first_name": d["givenName"],
                "last_name": d["familyName"],
                "date_of_birth": date.fromisoformat(dob) if dob else None,
                "nationality": d.get("nationality"),
                "url": d.get("url"),
            })
    if rows:
        stmt = insert(Driver).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["driver_ref"],
            set_={col: stmt.excluded[col] for col in ["code", "permanent_number", "first_name", "last_name", "nationality", "url"]},
        )
        session.execute(stmt)
        session.commit()
    logger.info("Upserted %d drivers", len(rows))


def upsert_constructors(session: DBSession, client: JolpicaClient, years: list[int]):
    seen = set()
    rows = []
    for year in years:
        for c in client.constructors(year):
            ref = c["constructorId"]
            if ref in seen:
                continue
            seen.add(ref)
            rows.append({
                "constructor_ref": ref,
                "name": c["name"],
                "nationality": c.get("nationality"),
                "url": c.get("url"),
            })
    if rows:
        stmt = insert(Constructor).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["constructor_ref"],
            set_={col: stmt.excluded[col] for col in ["name", "nationality", "url"]},
        )
        session.execute(stmt)
        session.commit()
    logger.info("Upserted %d constructors", len(rows))


def ingest_static(session: DBSession, client: JolpicaClient, years: list[int]):
    logger.info("Ingesting static data for years: %s", years)
    upsert_seasons(session, years)
    upsert_circuits(session, client, years)
    upsert_drivers(session, client, years)
    upsert_constructors(session, client, years)
