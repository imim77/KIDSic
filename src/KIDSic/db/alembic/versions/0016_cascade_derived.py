"""Let the database remove evidence rows when their parent is deleted."""
from pathlib import Path
from alembic import op

revision = '0016_cascade_derived'
down_revision = '0015_valid_knowledge_chunk'
branch_labels = None
depends_on = None


def upgrade():
    for statement in Path(__file__).with_suffix('.sql').read_text().split('\n-- statement\n'):
        if statement.strip():
            op.execute(statement)


def downgrade():
    for table, column, parent in (
        ('knowledge_chunk', 'source_record_id', 'source_record'),
        ('enrolment', 'source_record_id', 'source_record'),
        ('enrolment_refusal', 'source_record_id', 'source_record'),
        ('enrolment_refusal', 'enrolment_id', 'enrolment'),
        ('document_scope', 'source_record_id', 'source_record'),
    ):
        constraint = f'{table}_{column}_fkey'
        op.execute(f'ALTER TABLE {table} DROP CONSTRAINT {constraint}, '
                   f'ADD CONSTRAINT {constraint} FOREIGN KEY ({column}) '
                   f'REFERENCES {parent}(id)')
