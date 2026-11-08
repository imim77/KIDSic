"""Rename application columns in Croatian without replacing stored data."""
from pathlib import Path
from alembic import op

revision = '0020_croatian_columns'
down_revision = '0019_croatian_tables'
branch_labels = None
depends_on = None


def _execute(path):
    for statement in path.read_text().split('\n-- statement\n'):
        if statement.strip():
            op.execute(statement)


def upgrade():
    _execute(Path(__file__).with_suffix('.sql'))


def downgrade():
    op.execute('SELECT pg_advisory_xact_lock(194733, 1)')
    _execute(Path(__file__).with_name('0020_croatian_columns_downgrade.sql'))
