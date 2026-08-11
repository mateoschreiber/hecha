from __future__ import annotations

import argparse
import asyncio
import json
import logging
from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.application.sync_expedients import payload_hash, persist_expedient, quarantine
from backend.infrastructure.database import SessionLocal
from backend.infrastructure.models import (
    Commission,
    Expedient,
    LegislativeSession,
    Legislator,
    SyncRequest,
    SyncRun,
    Vote,
)
from backend.infrastructure.silpy_portal_client import SilpyPortalClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)
LOCK_KEY = 348_821_447


def persist_public_rows(
    model: type[Legislator] | type[Commission] | type[LegislativeSession] | type[Vote],
    rows: list[dict[str, object]],
) -> int:
    """Idempotently persist lightweight public SILpy lists without private fields."""
    now = datetime.now(UTC)
    saved = 0
    with SessionLocal() as session:
        for row in rows:
            raw = json.loads(json.dumps(row, default=str))
            source_id = str(row["source_id"])
            digest = payload_hash(raw)
            existing = session.scalar(
                select(model).where(model.source_system == "silpy", model.source_id == source_id)
            )
            values = {
                **{key: value for key, value in row.items() if key != "source_id"},
                "source_system": "silpy",
                "source_id": source_id,
                "content_hash": digest,
                "raw_payload": raw,
                "search_document": " ".join(str(value) for value in row.values() if value),
                "last_seen_at": now,
                "synced_at": now,
                "is_active": True,
            }
            values.setdefault("legislative_period", "2023-2028")
            values.setdefault("chamber", None)
            if existing is None:
                session.add(model(**values))
                saved += 1
            elif existing.content_hash != digest:
                for key, value in values.items():
                    setattr(existing, key, value)
                saved += 1
            else:
                existing.last_seen_at = now
                existing.synced_at = now
        session.commit()
    return saved


def acquire_lock() -> Session | None:
    session = SessionLocal()
    acquired = bool(session.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY}))
    if acquired:
        return session
    session.close()
    return None


def release_lock(session: Session) -> None:
    session.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_KEY})
    session.commit()
    session.close()


async def sync_portal(period: str, request_id: UUID | None = None) -> UUID | None:
    """Persist one current-portal sync request in committed monthly batches."""
    lock_session = acquire_lock()
    if lock_session is None:
        log.info("expedient sync skipped: another run owns the lock")
        return None
    client = SilpyPortalClient()
    try:
        ranges = client.ranges(period)
        with SessionLocal() as session:
            run = SyncRun(
                resource="expedients",
                status="running",
                processed_count=0,
                total_count=len(ranges),
                current_page=0,
                last_progress_at=datetime.now(UTC),
            )
            session.add(run)
            session.flush()
            run_id = run.id
            if request_id:
                request = session.get(SyncRequest, request_id)
                if request:
                    request.run_id = run_id
            session.commit()

        if request_id:
            sessions, votes, legislators, commissions = await asyncio.gather(
                client.list_sessions(),
                client.list_votes(),
                client.list_legislators(),
                client.list_commission_meetings(),
            )
            persist_public_rows(LegislativeSession, sessions)
            persist_public_rows(Vote, votes)
            persist_public_rows(Legislator, legislators)
            persist_public_rows(Commission, commissions)

        async with httpx.AsyncClient(
            base_url="https://silpy.congreso.gov.py", timeout=20, follow_redirects=True
        ) as http_client:
            for page, (since, until) in enumerate(ranges, start=1):
                records = await client.list_range(http_client, since, until)
                created = updated = skipped = invalid = failed = 0
                with SessionLocal() as session:
                    for record in records:
                        try:
                            existing = session.scalar(
                                select(Expedient).where(
                                    Expedient.source_system == "silpy",
                                    Expedient.source_id == str(record.id_proyecto),
                                )
                            )
                            old_hash = existing.content_hash if existing else None
                            if existing is None or not existing.authors or not existing.attachments:
                                record = await client.enrich_expedient(http_client, record)
                            persist_expedient(session, record)
                            if existing is None:
                                created += 1
                            elif old_hash == existing.content_hash:
                                skipped += 1
                            else:
                                updated += 1
                        except Exception as error:
                            failed += 1
                            quarantine(
                                session,
                                str(record.id_proyecto),
                                record.model_dump(by_alias=True, mode="json"),
                                str(error),
                            )
                    progress_run = session.get(SyncRun, run_id)
                    assert progress_run is not None
                    progress_run.current_page = page
                    progress_run.processed_count += len(records)
                    progress_run.created_count += created
                    progress_run.updated_count += updated
                    progress_run.skipped_count += skipped
                    progress_run.invalid_count += invalid
                    progress_run.failed_count += failed
                    progress_run.last_progress_at = datetime.now(UTC)
                    session.commit()  # progress only advances with a persisted range
                log.info(
                    "SILpy portal sync period=%s range=%s..%s records=%s",
                    period,
                    since,
                    until,
                    len(records),
                )

        with SessionLocal() as session:
            completed_run = session.get(SyncRun, run_id)
            assert completed_run is not None
            completed_run.status = "completed"
            completed_run.finished_at = datetime.now(UTC)
            completed_run.last_progress_at = completed_run.finished_at
            session.commit()
        return run_id
    except Exception as error:
        log.exception("SILpy portal sync failed")
        if "run_id" in locals():
            with SessionLocal() as session:
                failed_run = session.get(SyncRun, run_id)
                if failed_run:
                    failed_run.status = "failed"
                    failed_run.error_summary = str(error)[:1000]
                    failed_run.finished_at = datetime.now(UTC)
                    failed_run.last_progress_at = failed_run.finished_at
                    session.commit()
        raise
    finally:
        release_lock(lock_session)


async def forever() -> None:
    """An idle worker only acts on an explicit queued request."""
    while True:
        request_id: UUID | None = None
        period: str | None = None
        try:
            with SessionLocal() as session:
                requested = session.scalar(
                    select(SyncRequest)
                    .where(
                        SyncRequest.resource.in_(("expedients", "public_data")),
                        SyncRequest.status == "queued",
                    )
                    .order_by(SyncRequest.created_at)
                    .limit(1)
                )
                if requested:
                    requested.status = "running"
                    requested.started_at = datetime.now(UTC)
                    request_id = requested.id
                    period = "2023-2028" if requested.period == "all" else requested.period
                    session.commit()
            if request_id and period:
                error_summary: str | None = None
                try:
                    run_id = await sync_portal(period, request_id)
                    request_status = "completed"
                except Exception as exc:
                    run_id, request_status = None, "failed"
                    error_summary = str(exc)[:1000]
                with SessionLocal() as session:
                    request = session.get(SyncRequest, request_id)
                    if request:
                        request.status = request_status
                        request.finished_at = datetime.now(UTC)
                        request.error_summary = error_summary
                        if run_id:
                            request.run_id = run_id
                        session.commit()
        except Exception:
            log.exception("expedient worker loop failed")
        await asyncio.sleep(30)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synchronize current SILpy portal expedients")
    parser.add_argument("--period", default="2023-2028", choices=("2018-2023", "2023-2028"))
    parser.add_argument("--forever", action="store_true", help="process explicitly queued requests")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(forever() if args.forever else sync_portal(args.period))
