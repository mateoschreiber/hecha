from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from backend.application.sync_expedients import advance_checkpoint, persist_expedient, quarantine
from backend.infrastructure.config import get_settings
from backend.infrastructure.database import SessionLocal
from backend.infrastructure.models import SyncCheckpoint, SyncRun
from backend.infrastructure.silpy_client import SilpyClient, SilpyUnavailable

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


async def sync(partial: bool = True) -> None:
    settings = get_settings()
    client = SilpyClient(settings)
    with SessionLocal() as session:
        checkpoint = session.get(SyncCheckpoint, "expedients")
        start = int(checkpoint.cursor or "0") + 1 if checkpoint else 1
        run = SyncRun(resource="expedients")
        session.add(run)
        session.commit()
        processed = 0
        try:
            page = start
            while True:
                rows = await client.list_expedients(page)
                if not rows:
                    break
                for summary in rows:
                    try:
                        persist_expedient(session, await client.get_expedient(summary.id_proyecto))
                        processed += 1
                    except Exception as error:
                        quarantine(
                            session,
                            str(summary.id_proyecto),
                            summary.model_dump(by_alias=True),
                            str(error),
                        )
                advance_checkpoint(session, page)
                session.commit()  # checkpoint only after item transaction
                if partial and page - start + 1 >= settings.silpy_partial_pages:
                    break
                page += 1
            run.status = "completed"
            run.processed_count = processed
            run.finished_at = datetime.now(UTC)
            session.commit()
        except SilpyUnavailable as error:
            run.status = "failed"
            run.error_summary = str(error)
            run.finished_at = datetime.now(UTC)
            session.commit()
            raise


async def forever() -> None:
    while True:
        try:
            await sync(partial=True)
        except Exception:
            log.exception("expedient sync failed")
        await asyncio.sleep(15 * 60)


if __name__ == "__main__":
    asyncio.run(forever())
