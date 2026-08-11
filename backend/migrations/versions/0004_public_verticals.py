"""public legislative verticals and global sync guard

Revision ID: 0004_public_verticals
Revises: 0003_recovery_sync
"""

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_public_verticals"
down_revision = "0003_recovery_sync"
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
        sa.Column("search_document", sa.Text, nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    ]


def upgrade() -> None:
    definitions = {
        "legislators": [
            "full_name",
            "chamber",
            "party",
            "caucus",
            "legislative_period",
            "profile_url",
        ],
        "commissions": ["name", "chamber", "commission_type", "legislative_period", "source_url"],
        "legislative_sessions": [
            "title",
            "chamber",
            "session_type",
            "held_on",
            "legislative_period",
            "source_url",
        ],
        "votes": [
            "motion",
            "result",
            "chamber",
            "voted_on",
            "legislative_period",
            "session_source_id",
            "expedient_source_id",
            "source_url",
        ],
    }
    for table, fields in definitions.items():
        columns: list[sa.Column[Any]] = source_columns()
        for field in fields:
            if field in {"held_on", "voted_on"}:
                columns.append(sa.Column(field, sa.Date()))
            elif field in {"profile_url", "source_url", "motion"}:
                columns.append(sa.Column(field, sa.Text(), nullable=field != "motion"))
            else:
                columns.append(
                    sa.Column(
                        field, sa.String(256), nullable=field not in {"full_name", "name", "title"}
                    )
                )
        op.create_table(
            table,
            *columns,
            sa.UniqueConstraint("source_system", "source_id", name=f"uq_{table}_source"),
        )
        for field in ("legislative_period", "chamber", "held_on", "voted_on", "result"):
            if field in fields:
                op.create_index(f"ix_{table}_{field}", table, [field])
    op.create_index(
        "uq_sync_requests_active_global",
        "sync_requests",
        ["resource"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_index("uq_sync_requests_active_global", table_name="sync_requests")
    for table in ("votes", "legislative_sessions", "commissions", "legislators"):
        op.drop_table(table)
