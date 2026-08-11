from __future__ import annotations

from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.infrastructure.database import get_session
from backend.infrastructure.models import Expedient

app = FastAPI(title="Hecha API", version="0.1.0", openapi_url="/api/v1/openapi.json", docs_url=None)


def result(data: object, meta: dict[str, object] | None = None) -> dict[str, object]:
    return {"data": data, "meta": meta or {}, "links": {}}


def serialize(item: Expedient, detail: bool = False) -> dict[str, object]:
    data: dict[str, object] = {
        "id": str(item.id),
        "source_id": item.source_id,
        "number": item.number,
        "title": item.title,
        "type": item.project_type,
        "chamber": item.chamber,
        "status": item.status,
        "stage": item.stage,
        "substage": item.substage,
        "urgency": item.urgency,
        "filed_on": item.filed_on,
        "source_url": item.source_url,
        "synced_at": item.synced_at,
    }
    if detail:
        data |= {
            "initiative": item.initiative,
            "authors": [
                {"name": a.full_name, "party": a.party, "chamber": a.chamber} for a in item.authors
            ],
            "attachments": [
                {"id": a.source_id, "url": a.url, "info": a.info, "mime_type": a.mime_type}
                for a in item.attachments
            ],
            "committees": [c.name for c in item.committees],
        }
    return data


@app.get("/api/v1/health/live")
def live() -> dict[str, str]:
    return {"status": "live"}


@app.get("/api/v1/health/ready")
def ready(session: Session = Depends(get_session)) -> dict[str, str]:
    session.execute(select(1))
    return {"status": "ready"}


@app.get("/api/v1/meta/freshness")
def freshness(session: Session = Depends(get_session)) -> dict[str, object]:
    latest = session.scalar(select(func.max(Expedient.synced_at)))
    return result({"expedients": latest})


@app.get("/api/v1/expedients")
def list_expedients(
    q: str | None = None,
    chamber: str | None = None,
    status: str | None = None,
    project_type: str | None = Query(default=None, alias="type"),
    filed_from: date | None = None,
    filed_to: date | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    stmt = select(Expedient).where(Expedient.is_active.is_(True))
    if q:
        stmt = stmt.where(or_(Expedient.title.ilike(f"%{q}%"), Expedient.number.ilike(f"%{q}%")))
    for field, value in (
        (Expedient.chamber, chamber),
        (Expedient.status, status),
        (Expedient.project_type, project_type),
    ):
        if value:
            stmt = stmt.where(field == value)
    if filed_from:
        stmt = stmt.where(Expedient.filed_on >= filed_from)
    if filed_to:
        stmt = stmt.where(Expedient.filed_on <= filed_to)
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = session.scalars(
        stmt.order_by(Expedient.filed_on.desc().nullslast(), Expedient.id)
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return result([serialize(row) for row in rows], {"page": page, "limit": limit, "total": total})


@app.get("/api/v1/expedients/{id_or_number}")
def detail(id_or_number: str, session: Session = Depends(get_session)) -> dict[str, object]:
    stmt = (
        select(Expedient)
        .options(
            selectinload(Expedient.authors),
            selectinload(Expedient.attachments),
            selectinload(Expedient.committees),
        )
        .where(or_(Expedient.source_id == id_or_number, Expedient.number == id_or_number))
    )
    item = session.scalar(stmt)
    if not item:
        raise HTTPException(
            404, detail={"code": "not_found", "message": "Expediente no encontrado"}
        )
    return result(serialize(item, detail=True))


@app.get("/api/v1/search")
def search(
    q: str = Query(min_length=2, max_length=120), session: Session = Depends(get_session)
) -> dict[str, object]:
    return list_expedients(q=q, session=session)


@app.get("/api/v1/catalogs/{name}")
def catalogs(name: str, session: Session = Depends(get_session)) -> dict[str, object]:
    fields = {
        "chambers": Expedient.chamber,
        "statuses": Expedient.status,
        "types": Expedient.project_type,
    }
    if name not in fields:
        raise HTTPException(
            404, detail={"code": "catalog_not_found", "message": "Catálogo no encontrado"}
        )
    values = session.scalars(
        select(fields[name]).where(fields[name].is_not(None)).distinct().order_by(fields[name])
    ).all()
    return result(values)
