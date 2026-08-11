"""initial expedient and sync tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-11
"""

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def source_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_system", sa.String(32), nullable=False),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    ]


def upgrade() -> None:
    op.create_table(
        "expedients",
        *source_columns(),
        sa.Column("number", sa.String(64)),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("source_url", sa.Text),
        sa.Column("project_type", sa.String(128)),
        sa.Column("chamber", sa.String(128)),
        sa.Column("initiative", sa.Text),
        sa.Column("status", sa.String(128)),
        sa.Column("stage", sa.String(256)),
        sa.Column("substage", sa.String(256)),
        sa.Column("urgency", sa.String(64)),
        sa.Column("filed_on", sa.Date),
        sa.UniqueConstraint("source_system", "source_id", name="uq_expedients_source"),
    )
    for column in ("number", "project_type", "chamber", "status", "filed_on"):
        op.create_index(f"ix_expedients_{column}", "expedients", [column])
    for name, cols in (
        (
            "expedient_authors",
            [
                sa.Column("source_id", sa.String(64)),
                sa.Column("full_name", sa.String(256), nullable=False),
                sa.Column("party", sa.String(256)),
                sa.Column("chamber", sa.String(128)),
            ],
        ),
        (
            "attachments",
            [
                sa.Column("source_id", sa.String(64)),
                sa.Column("url", sa.Text),
                sa.Column("info", sa.String(128)),
                sa.Column("mime_type", sa.String(128)),
            ],
        ),
        ("committee_assignments", [sa.Column("name", sa.String(256), nullable=False)]),
    ):
        op.create_table(
            name,
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "expedient_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("expedients.id", ondelete="CASCADE"),
                nullable=False,
            ),
            *cols,
        )
    op.create_table(
        "sync_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("resource", sa.String(64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("processed_count", sa.Integer, nullable=False),
        sa.Column("error_summary", sa.Text),
    )
    op.create_index("ix_sync_runs_resource", "sync_runs", ["resource"])
    op.create_table(
        "sync_checkpoints",
        sa.Column("resource", sa.String(64), primary_key=True),
        sa.Column("cursor", sa.String(128)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "sync_items_failed",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("resource", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(64)),
        sa.Column("payload", postgresql.JSONB),
        sa.Column("error", sa.Text, nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "data_quality_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(64)),
        sa.Column("rule", sa.String(128), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("details", postgresql.JSONB),
    )
    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("topic", sa.String(128), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    for name in (
        "outbox_events",
        "data_quality_issues",
        "sync_items_failed",
        "sync_checkpoints",
        "sync_runs",
        "committee_assignments",
        "attachments",
        "expedient_authors",
        "expedients",
    ):
        op.drop_table(name)
