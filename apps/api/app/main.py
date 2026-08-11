from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session, selectinload

from backend.infrastructure.config import get_settings
from backend.infrastructure.database import get_session
from backend.infrastructure.models import (
    Commission,
    Expedient,
    LegislativeSession,
    Legislator,
    SyncRequest,
    SyncRun,
    Vote,
)

app = FastAPI(title="Hecha API", version="0.1.0", openapi_url="/api/v1/openapi.json", docs_url=None)
GOVERNMENT_PERIODS = {
    "2018-2023": (date(2018, 7, 1), date(2023, 6, 30)),
    "2023-2028": (date(2023, 7, 1), date(2028, 6, 30)),
}
CURRENT_PERIOD = "2023-2028"
PUBLIC_SYNC_COOLDOWN = timedelta(minutes=5)


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


@app.post("/api/v1/sync/expedients", status_code=status.HTTP_202_ACCEPTED)
def request_expedients_sync(
    period: str = CURRENT_PERIOD, session: Session = Depends(get_session)
) -> dict[str, object]:
    if period not in GOVERNMENT_PERIODS:
        raise HTTPException(422, detail={"code": "invalid_period", "message": "Período inválido"})
    active = session.scalar(
        select(SyncRequest).where(
            SyncRequest.resource == "expedients",
            SyncRequest.period == period,
            SyncRequest.status.in_(("queued", "running")),
        )
    )
    if active:
        return result({"status": active.status, "request_id": str(active.id)})
    request = SyncRequest(period=period, mode="refresh", status="queued")
    session.add(request)
    session.commit()
    return result({"status": "queued", "request_id": str(request.id)})


@app.post("/api/v1/sync", status_code=status.HTTP_202_ACCEPTED)
def request_public_sync(session: Session = Depends(get_session)) -> dict[str, object]:
    """Queue the single public refresh; never invokes SILpy during a visitor request."""
    active = session.scalar(
        select(SyncRequest).where(
            SyncRequest.resource == "public_data", SyncRequest.status.in_(("queued", "running"))
        )
    )
    if active:
        return result({"status": active.status, "request_id": str(active.id), "deduplicated": True})
    recent = session.scalar(
        select(SyncRequest)
        .where(SyncRequest.resource == "public_data", SyncRequest.status == "completed")
        .order_by(SyncRequest.finished_at.desc())
    )
    if (
        recent
        and recent.finished_at
        and datetime.now(UTC) - recent.finished_at < PUBLIC_SYNC_COOLDOWN
    ):
        return result(
            {
                "status": "cooldown",
                "request_id": str(recent.id),
                "retry_at": recent.finished_at + PUBLIC_SYNC_COOLDOWN,
            }
        )
    request = SyncRequest(resource="public_data", period="all", mode="refresh", status="queued")
    session.add(request)
    session.commit()
    return result({"status": "queued", "request_id": str(request.id), "deduplicated": False})


@app.get("/api/v1/sync/expedients/progress")
def sync_progress(session: Session = Depends(get_session)) -> dict[str, object]:
    run = session.scalar(select(SyncRun).order_by(SyncRun.started_at.desc()))
    if not run:
        return result({"status": "idle"})
    return result(
        {
            "status": run.status,
            "page": run.current_page,
            "total": run.total_count,
            "processed": run.processed_count,
            "added": run.created_count,
            "modified": run.updated_count,
            "skipped": run.skipped_count,
            "invalid": run.invalid_count,
            "failed": run.failed_count,
            "updated_at": run.last_progress_at,
        }
    )


@app.get("/api/v1/sync/progress")
def public_sync_progress(session: Session = Depends(get_session)) -> dict[str, object]:
    request = session.scalar(
        select(SyncRequest)
        .where(SyncRequest.resource == "public_data")
        .order_by(SyncRequest.created_at.desc())
    )
    if not request:
        return result({"status": "idle", "entity": None})
    run = session.get(SyncRun, request.run_id) if request.run_id else None
    progress: dict[str, object] = {
        "status": request.status,
        "entity": "expedients",
        "phase": request.mode,
        "last_error": request.error_summary,
        "started_at": request.started_at,
        "finished_at": request.finished_at,
    }
    if run:
        progress |= {
            "range": run.current_page,
            "total_ranges": run.total_count,
            "processed": run.processed_count,
            "created": run.created_count,
            "modified": run.updated_count,
            "skipped": run.skipped_count,
            "invalid": run.invalid_count,
            "failed": run.failed_count,
            "updated_at": run.last_progress_at,
        }
    return result(progress)


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
            raise HTTPException(
                422, detail={"code": "invalid_period", "message": "Período inválido"}
            )
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


@app.get("/api/v1/expedients/suggest")
def suggest_expedients(
    q: str = Query(min_length=1, max_length=120),
    period: str = CURRENT_PERIOD,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    """Lightweight, stable autocomplete for number, title and indexed author text."""
    if period != "all" and period not in GOVERNMENT_PERIODS:
        raise HTTPException(422, detail={"code": "invalid_period", "message": "Período inválido"})
    stmt = select(Expedient).where(
        Expedient.is_active.is_(True),
        or_(
            Expedient.number.ilike(f"%{q}%"),
            Expedient.title.ilike(f"%{q}%"),
            Expedient.search_document.ilike(f"%{q}%"),
        ),
    )
    if period != "all":
        stmt = stmt.where(Expedient.filed_on.between(*GOVERNMENT_PERIODS[period]))
    rows = session.scalars(
        stmt.order_by(Expedient.filed_on.desc().nullslast(), Expedient.id).limit(10)
    ).all()
    return result(
        [{"source_id": row.source_id, "number": row.number, "title": row.title} for row in rows]
    )


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
    period: str = CURRENT_PERIOD,
    session: Session = Depends(get_session),
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
    in_progress = (
        session.scalar(select(func.count()).select_from(base).where(base.c.status == "EN TRAMITE"))
        or 0
    )
    recent = session.scalars(
        select(Expedient)
        .where(*conditions)
        .order_by(Expedient.filed_on.desc().nullslast(), Expedient.id)
        .limit(3)
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


def public_listing(
    model: Any,
    period: str,
    page: int,
    limit: int,
    session: Session,
    date_column: Any,
    title_column: Any,
) -> dict[str, object]:
    if period != "all" and period not in GOVERNMENT_PERIODS:
        raise HTTPException(422, detail={"code": "invalid_period", "message": "Período inválido"})
    stmt = select(model).where(model.is_active.is_(True))
    if period != "all":
        stmt = stmt.where(model.legislative_period == period)
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = session.scalars(
        stmt.order_by(date_column.desc().nullslast(), model.id)
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return result(
        [
            {
                "id": str(row.id),
                "source_id": row.source_id,
                "title": getattr(row, title_column.key),
                "chamber": row.chamber,
                "period": row.legislative_period,
                "source_url": getattr(row, "source_url", None) or getattr(row, "profile_url", None),
            }
            for row in rows
        ],
        {"page": page, "limit": limit, "total": total},
    )


@app.get("/api/v1/legislators")
def list_legislators(
    period: str = CURRENT_PERIOD,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return public_listing(
        Legislator, period, page, limit, session, Legislator.synced_at, Legislator.full_name
    )


@app.get("/api/v1/commissions")
def list_commissions(
    period: str = CURRENT_PERIOD,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return public_listing(
        Commission, period, page, limit, session, Commission.synced_at, Commission.name
    )


@app.get("/api/v1/sessions")
def list_sessions(
    period: str = CURRENT_PERIOD,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return public_listing(
        LegislativeSession,
        period,
        page,
        limit,
        session,
        LegislativeSession.held_on,
        LegislativeSession.title,
    )


@app.get("/api/v1/votes")
def list_votes(
    period: str = CURRENT_PERIOD,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return public_listing(Vote, period, page, limit, session, Vote.voted_on, Vote.motion)


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
