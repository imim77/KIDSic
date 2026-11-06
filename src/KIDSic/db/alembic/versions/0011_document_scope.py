"""Store document text once and apply explicit provider scopes."""
from pathlib import Path
from alembic import op

revision = '0011_document_scope'
down_revision = '0010_current_source_state'
branch_labels = None
depends_on = None


def upgrade():
    for statement in Path(__file__).with_suffix('.sql').read_text().split('\n-- statement\n'):
        if statement.strip():
            op.execute(statement)


def downgrade():
    for statement in (
        'DROP TRIGGER source_record_scope_check ON source_record',
        'DROP TRIGGER chunk_document_scope_check ON knowledge_chunk',
        'DROP TRIGGER document_scope_required ON document_scope',
        'DROP FUNCTION check_document_scope()',
        'DROP VIEW document_applicability',
        'DROP TABLE enrolment_refusal',
        'DROP TABLE document_scope',
        "DELETE FROM knowledge_chunk WHERE source_record_id IN (SELECT r.id FROM source_record r JOIN data_source s ON s.id=r.source_id WHERE s.metadata->>'kind'='enrolment_document')",
        "DELETE FROM enrolment WHERE source_record_id IN (SELECT r.id FROM source_record r JOIN data_source s ON s.id=r.source_id WHERE s.metadata->>'kind'='enrolment_document')",
        "DELETE FROM source_record r USING data_source s WHERE r.source_id=s.id AND s.metadata->>'kind'='enrolment_document'",
        'ALTER TABLE knowledge_chunk ALTER COLUMN kindergarten_id SET NOT NULL, DROP CONSTRAINT IF EXISTS chunk_document_location_owner',
        'ALTER TABLE enrolment ADD COLUMN municipality_id uuid REFERENCES municipality(id), ADD COLUMN accepting boolean NOT NULL DEFAULT true, ADD CONSTRAINT enrolment_scope_check CHECK(num_nonnulls(kindergarten_id,municipality_id)=1)',
        'CREATE INDEX ix_enrolment_municipality ON enrolment(municipality_id)',
    ):
        op.execute(statement)
