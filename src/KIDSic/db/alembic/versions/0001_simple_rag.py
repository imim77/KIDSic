"""Simplified KIDSic model with structured filters and RAG retrieval.

The adjacent SQL is an immutable part of this revision, not an application model.
"""

from pathlib import Path

from alembic import op

revision = "0001_simple_rag"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    ddl = Path(__file__).with_suffix(".sql").read_text(encoding="utf-8")
    for statement in ddl.split("\n-- statement\n"):
        if statement.strip():
            op.execute(statement)


def downgrade():
    for table in ('program', 'source_record', 'location', 'kindergarten', 'data_source'):
        op.execute(f"DROP TABLE {table}")
    # Shared extensions remain installed.
