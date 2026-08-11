"""add normalized search document

Revision ID: 0002_search_document
Revises: 0001_initial
Create Date: 2026-08-11
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_search_document"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "expedients", sa.Column("search_document", sa.Text(), nullable=False, server_default="")
    )
    op.execute(
        "CREATE INDEX ix_expedients_search_document_tsv "
        "ON expedients USING gin (to_tsvector('spanish', search_document))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ix_expedients_search_document_tsv")
    op.drop_column("expedients", "search_document")
