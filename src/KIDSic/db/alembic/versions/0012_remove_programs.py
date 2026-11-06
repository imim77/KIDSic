"""Remove current program features without changing historical source labels."""
from pathlib import Path
from alembic import op

revision = '0012_remove_programs'
down_revision = '0011_document_scope'
branch_labels = None
depends_on = None


def upgrade():
    for statement in Path(__file__).with_suffix('.sql').read_text().split('\n-- statement\n'):
        if statement.strip():
            op.execute(statement)


def downgrade():
    op.execute("CREATE TABLE program (\n id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n kindergarten_id uuid NOT NULL REFERENCES kindergarten(id),\n location_id uuid,\n source_record_id uuid NOT NULL REFERENCES source_record(id),\n name text NOT NULL,\n min_age_months smallint CHECK (min_age_months>=0),\n max_age_months_exclusive smallint CHECK (max_age_months_exclusive>0),\n verified_on date NOT NULL,\n valid_until date,\n languages text[] NOT NULL DEFAULT '{}',\n FOREIGN KEY(location_id,kindergarten_id) REFERENCES location(id,kindergarten_id),\n UNIQUE(id,kindergarten_id),\n CHECK (max_age_months_exclusive IS NULL OR min_age_months IS NULL OR max_age_months_exclusive>min_age_months),\n CHECK (valid_until IS NULL OR valid_until>=verified_on)\n);")
    op.execute('CREATE INDEX ix_program_owner ON program(kindergarten_id,location_id);')
    op.execute('CREATE INDEX ix_program_source ON program(source_record_id);')
    op.execute('ALTER TABLE knowledge_chunk ADD COLUMN program_id uuid, ADD FOREIGN KEY(program_id,kindergarten_id) REFERENCES program(id,kindergarten_id)')
    op.execute('ALTER TABLE data_source ADD COLUMN stale_after_days integer CHECK(stale_after_days>0)')
    op.execute("ALTER TABLE knowledge_chunk ADD COLUMN search_text tsvector GENERATED ALWAYS AS (to_tsvector('simple',content)) STORED")
    op.execute('CREATE INDEX ix_chunk_lexical ON knowledge_chunk USING gin(search_text)')
