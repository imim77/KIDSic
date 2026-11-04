"""Municipal subsidies stores shared funding rules without duplicating facilities."""
from pathlib import Path

from alembic import op

revision = '0006_municipal_subsidies'
down_revision = '0005_supported_cities'
branch_labels = None
depends_on = None


def upgrade():
    for statement in Path(__file__).with_suffix('.sql').read_text().split('\n-- statement\n'):
        if statement.strip():
            op.execute(statement)


def downgrade():
    op.execute('DROP TABLE municipality_subsidy_policy')
