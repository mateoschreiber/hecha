from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session, selectinload

from backend.infrastructure.config import get_settings
from backend.infrastructure.database import get_session
from backend.infrastructure.models import Expedient, OutboxEvent, SyncCheckpoint, SyncRun

app = FastAPI(title="Hecha API", version="0.1.0", openapi_url="/api/v1/openapi.json", docs_url=None)
GOVERNMENT_PERIODS = {
    "2018-2023": (date(2018, 7, 1), date(2023, 6, 30)),
    "2023-2028": (date(2023, 7, 1), date(2028, 6, 30)),
}
CURRENT_PERIOD = "2023-2028"


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
    count = session.scalar(select(func.count()).select_from(Expedient)) or 0
    last_success = session.scalar(
        select(SyncRun).where(SyncRun.status == "completed").order_by(SyncRun.finished_at.desc())
    )
    last_failure = session.scalar(
        select(SyncRun).where(SyncRun.status == "failed").order_by(SyncRun.finished_at.desc())
    )
    stale_after = datetime.now(UTC) - timedelta(minutes=get_settings().freshness_stale_minutes)
    state = (
        "empty" if count == 0 else "stale" if latest is None or latest < stale_after else "fresh"
    )
    return result(
        {
            "expedients": latest,
            "count": count,
            "state": state,
            "last_success_at": last_success.finished_at if last_success else None,
            "last_error_at": last_failure.finished_at if last_failure else None,
            "last_error": last_failure.error_summary if last_failure else None,
        }
    )


@app.post("/api/v1/sync/expedients/missing", status_code=status.HTTP_202_ACCEPTED)
def request_missing_expedients_sync(session: Session = Depends(get_session)) -> dict[str, object]:
    """Queue a worker-only reconciliation that fetches details only for missing IDs."""
    topic = "sync.expedients.missing.requested"
    pending = session.scalar(
        select(OutboxEvent).where(OutboxEvent.topic == topic, OutboxEvent.processed_at.is_(None))
    )
    if pending is None:
        session.add(OutboxEvent(topic=topic, payload={"requested_by": "public_portal"}))
        session.commit()
        return result({"status": "queued"})
    return result({"status": "already_queued"})


@app.get("/api/v1/sync/expedients/progress")
def sync_progress(session: Session = Depends(get_session)) -> dict[str, object]:
    run = session.scalar(
        select(SyncRun).where(SyncRun.status == "running").order_by(SyncRun.started_at.desc())
    )
    cursor = session.get(SyncCheckpoint, "expedients")
    processed = run.processed_count if run else 0
    return result(
        {"status": run.status if run else "idle",
         "page": int(cursor.cursor or "0") if cursor else 0,
         "total_pages": 501, "processed": processed, "added_or_modified": processed}
    )


@app.get("/api/v1/expedients")
def list_expedients(
    q: str | None = None,
    chamber: str | None = None,
    status: str | None = None,
    project_type: str | None = Query(default=None, alias="type"),
    filed_from: date | None = None,
    filed_to: date | None = None,
    period: str = CURRENT_PERIOD,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    session: Session = Depends(get_session),
    full_text: bool = Query(default=False, include_in_schema=False),
) -> dict[str, object]:
    stmt = select(Expedient).where(Expedient.is_active.is_(True))
    if period != "all":
        if period not in GOVERNMENT_PERIODS:
            raise HTTPException(422, detail={"code": "invalid_period", "message": "Periodo invalido"})
        period_from, period_to = GOVERNMENT_PERIODS[period]
        stmt = stmt.where(Expedient.filed_on.between(period_from, period_to))
    if q:
        if full_text:
            stmt = stmt.where(
                text(
                    "to_tsvector('spanish', search_document) "
                    "@@ websearch_to_tsquery('spanish', :search_query)"
                ).bindparams(search_query=q)
            )
        else:
            stmt = stmt.where(
                or_(Expedient.title.ilike(f"%{q}%"), Expedient.number.ilike(f"%{q}%"))
            )
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
    q: str = Query(min_length=1, max_length=120),
    period: str = CURRENT_PERIOD, session: Session = Depends(get_session)
) -> dict[str, object]:
    return list_expedients(
        q=q,
        chamber=None,
        status=None,
        project_type=None,
        filed_from=None,
        filed_to=None,
        page=1,
        limit=10,
        session=session,
        full_text=True,
        period=period,
    )


@app.get("/api/v1/dashboard/summary")
def dashboard_summary(
    period: str = CURRENT_PERIOD, session: Session = Depends(get_session)
) -> dict[str, object]:
    if period != "all" and period not in GOVERNMENT_PERIODS:
        raise HTTPException(422, detail={"code": "invalid_period", "message": "Período no válido"})
    conditions = [Expedient.is_active.is_(True)]
    if period != "all":
        conditions.append(Expedient.filed_on.between(*GOVERNMENT_PERIODS[period]))
    base = select(Expedient).where(*conditions).subquery()

    def distribution(column: Any) -> list[dict[str, object]]:
        rows = session.execute(
            select(column, func.count())
            .select_from(base)
            .group_by(column)
            .order_by(func.count().desc())
        ).all()
        return [{"label": label or "Sin datos", "count": count} for label, count in rows]

    monthly = session.execute(
        select(func.date_trunc("month", base.c.filed_on).label("month"), func.count())
        .where(base.c.filed_on.is_not(None))
        .group_by("month")
        .order_by("month")
    ).all()
    total = session.scalar(select(func.count()).select_from(base)) or 0
    in_progress = session.scalar(
        select(func.count()).select_from(base).where(base.c.status == "EN TRAMITE")
    ) or 0
    recent = session.scalars(
        select(Expedient)
        .where(*conditions)
        .order_by(Expedient.filed_on.desc().nullslast(), Expedient.id)
        .limit(6)
    ).all()
    return result(
        {
            "kpis": {"total": total, "in_progress": in_progress},
            "by_chamber": distribution(base.c.chamber),
            "by_status": distribution(base.c.status),
            "by_type": distribution(base.c.project_type),
            "evolution": [{"month": month, "count": count} for month, count in monthly],
            "recent": [serialize(item) for item in recent],
        }
    )


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
