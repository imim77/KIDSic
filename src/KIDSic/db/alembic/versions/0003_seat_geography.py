"""Add source-grounded seat geography without treating seats as service facilities."""
from pathlib import Path
from alembic import op

revision = '0003_seat_geography'
down_revision = '0002_settlement_seat'
branch_labels = None
depends_on = None


def upgrade():
    for statement in Path(__file__).with_suffix('.sql').read_text().split('\n-- statement\n'):
        if statement.strip():
            op.execute(statement)


def downgrade():
    op.execute('DROP VIEW kindergarten_seat_geography')
    op.execute('ALTER TABLE kindergarten DROP COLUMN seat_longitude, DROP COLUMN seat_latitude, DROP COLUMN seat_attributes')
