"""Supported cities removes data outside Zagreb, Varaždin and Rijeka."""
from pathlib import Path
from alembic import op

revision = '0005_supported_cities'
down_revision = '0004_provider_kinds'
branch_labels = None
depends_on = None


def upgrade():
    for statement in Path(__file__).with_suffix('.sql').read_text().split('\n-- statement\n'):
        if statement.strip():
            op.execute(statement)


def downgrade():
    raise RuntimeError('City cleanup cannot restore deleted data; restore the pre-migration backup.')
