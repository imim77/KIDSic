"""Keep current source contents without snapshot activation state."""
from pathlib import Path
from alembic import op

revision = '0017_remove_batches'
down_revision = '0016_cascade_derived'
branch_labels = None
depends_on = None


def upgrade():
    for statement in Path(__file__).with_suffix('.sql').read_text().split('\n-- statement\n'):
        if statement.strip():
            op.execute(statement)


def downgrade():
    # One synthetic batch restores the old contract, not discarded versions.
    for statement in (
        'DROP VIEW valid_knowledge_chunk',
        'DROP VIEW document_applicability',
        'DROP VIEW kindergarten_seat_geography',
        'ALTER TABLE data_source ADD COLUMN active_batch_id uuid',
        'ALTER TABLE source_record ADD COLUMN batch_id uuid',
        'ALTER TABLE historical_record ADD COLUMN batch_id uuid',
        'UPDATE data_source SET active_batch_id=id',
        'UPDATE source_record SET batch_id=source_id',
        'UPDATE historical_record SET batch_id=source_id',
        'SET CONSTRAINTS ALL IMMEDIATE',
        'ALTER TABLE source_record ALTER COLUMN batch_id SET NOT NULL',
        'ALTER TABLE historical_record ALTER COLUMN batch_id SET NOT NULL, '
        'DROP CONSTRAINT historical_record_source_id_source_key_key, '
        'ADD CONSTRAINT historical_record_source_id_batch_id_source_key_key '
        'UNIQUE(source_id,batch_id,source_key)',
        'CREATE INDEX ix_record_batch ON source_record(source_id,batch_id)',
        'CREATE INDEX ix_historical_record_batch ON historical_record(source_id,batch_id)',
    ):
        op.execute(statement)
    for filename in ('0013_kindergarten_seat.sql', '0015_valid_knowledge_chunk.sql'):
        for statement in Path(__file__).with_name(filename).read_text().split('\n-- statement\n'):
            if 'CREATE VIEW ' in statement:
                op.execute(statement)
