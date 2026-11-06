"""Store document dates and source kind outside untyped JSON."""
from pathlib import Path
from alembic import op

revision = '0018_document_record'
down_revision = '0017_remove_batches'
branch_labels = None
depends_on = None


def upgrade():
    for statement in Path(__file__).with_suffix('.sql').read_text().split('\n-- statement\n'):
        if statement.strip():
            op.execute(statement)


def downgrade():
    op.execute('DROP VIEW valid_knowledge_chunk')
    op.execute('DROP VIEW document_applicability')
    op.execute("""UPDATE source_record r SET raw_data=r.raw_data || jsonb_build_object(
        'kind',s.kind,'snapshot_key',s.metadata->>'snapshot_key','document_url',s.url,
        'scope',CASE WHEN EXISTS(SELECT 1 FROM document_scope ds
          WHERE ds.source_record_id=r.id AND ds.municipality_id IS NOT NULL)
          THEN 'municipality' ELSE 'institution' END,
        'reference_date',d.reference_date,'date_kind',d.date_kind,'valid_until',d.valid_until)
        FROM document_record d,data_source s
        WHERE r.id=d.source_record_id AND s.id=r.source_id AND s.kind='enrolment_document'""")
    op.execute("""UPDATE data_source SET metadata=metadata || jsonb_build_object('kind',kind)
        WHERE kind='enrolment_document'""")
    op.execute('SET CONSTRAINTS ALL IMMEDIATE')
    op.execute('DROP TABLE document_record')
    op.execute('ALTER TABLE data_source DROP COLUMN kind')
    for statement in Path(__file__).with_name('0017_remove_batches.sql').read_text().split('\n-- statement\n'):
        if ('CREATE VIEW document_applicability' in statement
                or 'CREATE VIEW valid_knowledge_chunk' in statement):
            op.execute(statement)
