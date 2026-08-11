"""recoverable sync state and legislative periods

Revision ID: 0003_recovery_sync
Revises: 0002_search_document
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_recovery_sync"
down_revision = "0002_search_document"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("expedients", sa.Column("legislative_period", sa.String(16)))
    op.create_index("ix_expedients_legislative_period", "expedients", ["legislative_period"])
    for name, column in (
        ("total_count", sa.Integer()),
        ("created_count", sa.Integer()),
        ("updated_count", sa.Integer()),
        ("skipped_count", sa.Integer()),
        ("invalid_count", sa.Integer()),
        ("failed_count", sa.Integer()),
        ("current_page", sa.Integer()),
        ("last_progress_at", sa.DateTime(timezone=True)),
    ):
        op.add_column("sync_runs", sa.Column(name, column))
    op.create_table(
        "sync_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("resource", sa.String(64), nullable=False),
        sa.Column("period", sa.String(16), nullable=False),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("run_id", postgresql.UUID(as_uuid=True)),
        sa.Column("error_summary", sa.Text()),
    )
    op.create_index("ix_sync_requests_status", "sync_requests", ["status"])


def downgrade() -> None:
    op.drop_table("sync_requests")
    for name in (
        "last_progress_at",
        "current_page",
        "failed_count",
        "invalid_count",
        "skipped_count",
        "updated_count",
        "created_count",
        "total_count",
    ):
        op.drop_column("sync_runs", name)
    op.drop_index("ix_expedients_legislative_period", table_name="expedients")
    op.drop_column("expedients", "legislative_period")
