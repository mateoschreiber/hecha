from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.domain.silpy import SilpyExpedient
from backend.infrastructure.models import (
    Attachment,
    CommitteeAssignment,
    Expedient,
    ExpedientAuthor,
    OutboxEvent,
    SyncCheckpoint,
    SyncItemFailed,
)


def payload_hash(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()


def persist_expedient(session: Session, item: SilpyExpedient) -> Expedient:
    raw = item.model_dump(by_alias=True, mode="json")
    digest = payload_hash(raw)
    expedient = session.scalar(
        select(Expedient).where(
            Expedient.source_system == "silpy", Expedient.source_id == str(item.id_proyecto)
        )
    )
    now = datetime.now(UTC)
    author_names = [f"{author.nombres} {author.apellidos}".strip() for author in item.authors]
    values = {
        "number": item.number,
        "title": item.title,
        "source_url": item.source_url,
        "project_type": item.project_type,
        "chamber": item.chamber,
        "initiative": item.initiative,
        "status": item.status,
        "stage": item.stage,
        "substage": item.substage,
        "urgency": item.urgency,
        "filed_on": item.filed_on,
        "raw_payload": raw,
        "search_document": " ".join(filter(None, [item.number, item.title, *author_names])),
        "content_hash": digest,
        "last_seen_at": now,
        "synced_at": now,
        "is_active": True,
    }
    if expedient is None:
        expedient = Expedient(source_system="silpy", source_id=str(item.id_proyecto), **values)
        session.add(expedient)
        session.flush()
    elif expedient.content_hash != digest:
        for key, value in values.items():
            setattr(expedient, key, value)
        expedient.authors.clear()
        expedient.attachments.clear()
        expedient.committees.clear()
        session.flush()
    else:
        expedient.last_seen_at = now
        expedient.synced_at = now
        return expedient
    for author in item.authors:
        expedient.authors.append(
            ExpedientAuthor(
                source_id=str(author.id_parlamentario),
                full_name=f"{author.nombres} {author.apellidos}".strip(),
                party=author.partido_politico,
                chamber=author.camara,
            )
        )
    for attachment in item.attachments:
        expedient.attachments.append(
            Attachment(
                source_id=str(attachment.id_adjunto),
                url=attachment.url,
                info=attachment.info,
                mime_type=attachment.mime_type,
            )
        )
    if item.committees_text:
        for name in item.committees_text.split(")"):
            clean = name.strip(" 0123456789.(")
            if clean:
                expedient.committees.append(CommitteeAssignment(name=clean))
    session.add(
        OutboxEvent(topic="expedient.changed", payload={"source_id": str(item.id_proyecto)})
    )
    return expedient


def advance_checkpoint(session: Session, page: int, resource: str = "expedients") -> None:
    checkpoint = session.get(SyncCheckpoint, resource)
    if checkpoint is None:
        session.add(SyncCheckpoint(resource=resource, cursor=str(page)))
    else:
        checkpoint.cursor = str(page)


def quarantine(
    session: Session, source_id: str | None, payload: dict[str, object] | None, error: str
) -> None:
    session.add(
        SyncItemFailed(
            resource="expedients", source_id=source_id, payload=payload, error=error[:1000]
        )
    )
