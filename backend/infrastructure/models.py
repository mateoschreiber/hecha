from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.infrastructure.database import Base


class TimestampedSource(Base):
    __abstract__ = True
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_system: Mapped[str] = mapped_column(String(32), default="silpy")
    source_id: Mapped[str] = mapped_column(String(64))
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    content_hash: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Expedient(TimestampedSource):
    __tablename__ = "expedients"
    __table_args__ = (UniqueConstraint("source_system", "source_id", name="uq_expedients_source"),)
    number: Mapped[str | None] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    project_type: Mapped[str | None] = mapped_column(String(128), index=True)
    chamber: Mapped[str | None] = mapped_column(String(128), index=True)
    initiative: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(128), index=True)
    stage: Mapped[str | None] = mapped_column(String(256))
    substage: Mapped[str | None] = mapped_column(String(256))
    urgency: Mapped[str | None] = mapped_column(String(64))
    filed_on: Mapped[date | None] = mapped_column(Date, index=True)
    authors: Mapped[list[ExpedientAuthor]] = relationship(
        back_populates="expedient", cascade="all, delete-orphan"
    )
    attachments: Mapped[list[Attachment]] = relationship(
        back_populates="expedient", cascade="all, delete-orphan"
    )
    committees: Mapped[list[CommitteeAssignment]] = relationship(
        back_populates="expedient", cascade="all, delete-orphan"
    )


class ExpedientAuthor(Base):
    __tablename__ = "expedient_authors"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    expedient_id: Mapped[UUID] = mapped_column(ForeignKey("expedients.id", ondelete="CASCADE"))
    source_id: Mapped[str] = mapped_column(String(64))
    full_name: Mapped[str] = mapped_column(String(256))
    party: Mapped[str | None] = mapped_column(String(256))
    chamber: Mapped[str | None] = mapped_column(String(128))
    expedient: Mapped[Expedient] = relationship(back_populates="authors")


class Attachment(Base):
    __tablename__ = "attachments"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    expedient_id: Mapped[UUID] = mapped_column(ForeignKey("expedients.id", ondelete="CASCADE"))
    source_id: Mapped[str] = mapped_column(String(64))
    url: Mapped[str | None] = mapped_column(Text)
    info: Mapped[str | None] = mapped_column(String(128))
    mime_type: Mapped[str | None] = mapped_column(String(128))
    expedient: Mapped[Expedient] = relationship(back_populates="attachments")


class CommitteeAssignment(Base):
    __tablename__ = "committee_assignments"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    expedient_id: Mapped[UUID] = mapped_column(ForeignKey("expedients.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(256))
    expedient: Mapped[Expedient] = relationship(back_populates="committees")


class SyncRun(Base):
    __tablename__ = "sync_runs"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    resource: Mapped[str] = mapped_column(String(64), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="running")
    processed_count: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)


class SyncCheckpoint(Base):
    __tablename__ = "sync_checkpoints"
    resource: Mapped[str] = mapped_column(String(64), primary_key=True)
    cursor: Mapped[str | None] = mapped_column(String(128))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SyncItemFailed(Base):
    __tablename__ = "sync_items_failed"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    resource: Mapped[str] = mapped_column(String(64))
    source_id: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(64))
    source_id: Mapped[str | None] = mapped_column(String(64))
    rule: Mapped[str] = mapped_column(String(128))
    severity: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="open")
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    topic: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
