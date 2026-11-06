"""Keep evidence validity rules in one view, separate from request selection."""
from pathlib import Path
from alembic import op

revision = '0015_valid_knowledge_chunk'
down_revision = '0014_remove_unread_storage'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(Path(__file__).with_suffix('.sql').read_text())


def downgrade():
    op.execute('DROP VIEW valid_knowledge_chunk')
