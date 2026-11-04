"""Historical records enrich existing identities without activating old facilities."""
from pathlib import Path
from alembic import op

revision = '0007_historical_records'
down_revision = '0006_municipal_subsidies'
branch_labels = None
depends_on = None


def upgrade():
    for statement in Path(__file__).with_suffix('.sql').read_text().split('\n-- statement\n'):
        if statement.strip():
            op.execute(statement)


def downgrade():
    op.execute('DROP TABLE historical_record')
