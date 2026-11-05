"""Enrolment rounds separate the main call from enrolment during the pedagogical year."""
from pathlib import Path
from alembic import op

revision = '0008_enrolment_rounds'
down_revision = '0007_historical_records'
branch_labels = None
depends_on = None


def upgrade():
    for statement in Path(__file__).with_suffix('.sql').read_text().split('\n-- statement\n'):
        if statement.strip():
            op.execute(statement)


def downgrade():
    op.execute('ALTER TABLE enrolment DROP COLUMN accepting, DROP COLUMN round')
