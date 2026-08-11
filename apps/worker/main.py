from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.application.sync_expedients import advance_checkpoint, persist_expedient, quarantine
from backend.domain.silpy import SilpyExpedient
from backend.infrastructure.config import get_settings
from backend.infrastructure.database import SessionLocal
from backend.infrastructure.models import Expedient, OutboxEvent, SyncCheckpoint, SyncRun
from backend.infrastructure.silpy_client import SilpyClient, SilpyUnavailable

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)
LOCK_KEY = 348_821_447
ASUNCION = ZoneInfo("America/Asuncion")
MISSING_SYNC_TOPIC = "sync.expedients.missing.requested"


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


async def fetch_detail(client: SilpyClient, source_id: int) -> SilpyExpedient:
    return await client.get_expedient(source_id)


async def sync(mode: str = "partial", resume: bool = False) -> int | None:
    """Synchronize SILpy without making public requests depend on the source."""
    settings = get_settings()
    full = mode in {"full", "seed", "missing"}
    lock_session = acquire_lock()
    if lock_session is None:
        log.info("expedient sync skipped: another run owns the lock")
        return None
    client = SilpyClient(settings)
    try:
        await client.open()
        with SessionLocal() as session:
            checkpoint_resource = "expedients_missing" if mode == "missing" else "expedients"
            checkpoint = session.get(SyncCheckpoint, checkpoint_resource)
            if full and not resume:
                start = 1
            else:
                start = int(checkpoint.cursor or "0") + 1 if checkpoint else 1
            run = SyncRun(resource="expedients", status="running", processed_count=0)
            session.add(run)
            session.commit()
            processed = 0
            page = start
            try:
                while True:
                    raw_rows = await client.list_expedients(page)
                    if not raw_rows:
                        if not full:
                            advance_checkpoint(session, 0)
                            session.commit()
                        break
                    summaries: list[SilpyExpedient] = []
                    for raw in raw_rows:
                        try:
                            summaries.append(SilpyExpedient.model_validate(raw))
                        except Exception as error:
                            payload = raw if isinstance(raw, dict) else {"invalid_item": raw}
                            source_id = (
                                str(raw.get("idProyecto")) if isinstance(raw, dict) else None
                            )
                            quarantine(session, source_id, payload, str(error))
                    if mode == "missing" and summaries:
                        existing_ids = set(
                            session.scalars(
                                select(Expedient.source_id).where(
                                    Expedient.source_system == "silpy",
                                    Expedient.source_id.in_(
                                        [str(summary.id_proyecto) for summary in summaries]
                                    ),
                                )
                            ).all()
                        )
                        summaries = [
                            summary
                            for summary in summaries
                            if str(summary.id_proyecto) not in existing_ids
                        ]
                    details = await asyncio.gather(
                        *(fetch_detail(client, summary.id_proyecto) for summary in summaries),
                        return_exceptions=True,
                    )
                    for summary, detail in zip(summaries, details, strict=True):
                        if isinstance(detail, BaseException):
                            quarantine(
                                session,
                                str(summary.id_proyecto),
                                summary.model_dump(by_alias=True),
                                str(detail),
                            )
                            continue
                        try:
                            with session.begin_nested():
                                persist_expedient(session, detail)
                            processed += 1
                        except Exception as error:
                            quarantine(
                                session,
                                str(summary.id_proyecto),
                                summary.model_dump(by_alias=True),
                                str(error),
                            )
                    session.commit()  # persist/quarantine batch before moving its checkpoint
                    advance_checkpoint(session, page, checkpoint_resource)
                    session.commit()
                    log.info(
                        "expedient sync progress mode=%s page=%s processed=%s",
                        mode,
                        page,
                        processed,
                    )
                    if not full and page - start + 1 >= settings.silpy_partial_pages:
                        break
                    page += 1
                run.status = "completed"
                run.processed_count = processed
                run.finished_at = datetime.now(UTC)
                session.commit()
                log.info(
                    "expedient sync completed mode=%s start_page=%s processed=%s",
                    mode,
                    start,
                    processed,
                )
                return processed
            except SilpyUnavailable as error:
                run.status = "failed"
                run.error_summary = str(error)
                run.finished_at = datetime.now(UTC)
                session.commit()
                raise
    finally:
        await client.close()
        release_lock(lock_session)


async def forever() -> None:
    last_full_date: date | None = None
    next_partial_at: datetime | None = None
    while True:
        local_now = datetime.now(ASUNCION)
        try:
            with SessionLocal() as session:
                requested = session.scalar(
                    select(OutboxEvent)
                    .where(
                        OutboxEvent.topic == MISSING_SYNC_TOPIC,
                        OutboxEvent.processed_at.is_(None),
                    )
                    .order_by(OutboxEvent.id)
                    .limit(1)
                )
                request_id = requested.id if requested else None
            if request_id:
                processed = await sync("missing")
                if processed is not None:
                    with SessionLocal() as session:
                        event = session.get(OutboxEvent, request_id)
                        if event:
                            event.processed_at = datetime.now(UTC)
                            session.commit()
            elif (
                local_now.hour == 2
                and local_now.minute >= 15
                and last_full_date != local_now.date()
            ):
                await sync("full")
                last_full_date = local_now.date()
            elif next_partial_at is None or datetime.now(UTC) >= next_partial_at:
                await sync("partial")
                next_partial_at = datetime.now(UTC) + timedelta(minutes=15)
        except Exception:
            log.exception("expedient sync failed")
        await asyncio.sleep(30)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synchronize SILpy expedients")
    parser.add_argument("--mode", choices=("partial", "full", "seed"), default="partial")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="continue a full or seed run from the committed checkpoint",
    )
    parser.add_argument("--forever", action="store_true", help="run the scheduled worker loop")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(forever() if args.forever else sync(args.mode, resume=args.resume))
