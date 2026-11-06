"""Remove unused availability, embeddings and enrolment payloads."""
from pathlib import Path
from alembic import op

revision = '0009_remove_unused'
down_revision = '0008_enrolment_rounds'
branch_labels = None
depends_on = None


def upgrade():
    for statement in Path(__file__).with_suffix('.sql').read_text().split('\n-- statement\n'):
        if statement.strip():
            op.execute(statement)


def downgrade():
    op.execute('CREATE TABLE availability (\n id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n kindergarten_id uuid NOT NULL REFERENCES kindergarten(id),\n location_id uuid,\n source_record_id uuid NOT NULL REFERENCES source_record(id),\n age_label text, program_label text,\n free_places integer CHECK(free_places>=0),\n observed_on date,\n FOREIGN KEY(location_id,kindergarten_id) REFERENCES location(id,kindergarten_id)\n);')
    op.execute('CREATE INDEX ix_availability_owner ON availability(kindergarten_id,location_id);')
    op.execute('CREATE INDEX ix_availability_source ON availability(source_record_id);')
    op.execute('ALTER TABLE availability\n ADD COLUMN program_id uuid,\n ADD COLUMN min_age_months smallint CHECK (min_age_months>=0),\n ADD COLUMN max_age_months_exclusive smallint CHECK (max_age_months_exclusive>0),\n ADD FOREIGN KEY(program_id,kindergarten_id) REFERENCES program(id,kindergarten_id),\n ADD CHECK (max_age_months_exclusive IS NULL OR min_age_months IS NULL OR max_age_months_exclusive>min_age_months);')
    op.execute('-- Published places are meaningless without the date they describe; fails if such rows exist.\nALTER TABLE availability ALTER COLUMN observed_on SET NOT NULL;')
    op.execute('CREATE INDEX ix_availability_program ON availability(program_id);')
    op.execute('ALTER TABLE knowledge_chunk ADD COLUMN embedding vector(384), ADD COLUMN embedding_model text, ADD CHECK ((embedding IS NULL)=(embedding_model IS NULL)), ADD CHECK (embedding IS NULL OR vector_norm(embedding)>0)')
    op.execute("ALTER TABLE enrolment ADD COLUMN steps jsonb NOT NULL DEFAULT '[]' CHECK(jsonb_typeof(steps)='array'), ADD COLUMN documents jsonb NOT NULL DEFAULT '[]' CHECK(jsonb_typeof(documents)='array')")
