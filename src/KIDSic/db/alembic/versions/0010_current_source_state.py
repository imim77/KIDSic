"""Keep current source records under stable source identities."""
from pathlib import Path
from alembic import op

revision = '0010_current_source_state'
down_revision = '0009_remove_unused'
branch_labels = None
depends_on = None


def upgrade():
    for statement in Path(__file__).with_suffix('.sql').read_text().split('\n-- statement\n'):
        if statement.strip():
            op.execute(statement)


def downgrade():

    op.execute('ALTER TABLE source_record DROP CONSTRAINT source_record_source_key_unique')
