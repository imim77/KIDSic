"""Use Croatian plural names for application tables without changing their data."""
from pathlib import Path
from alembic import op

revision = '0019_croatian_tables'
down_revision = '0018_document_record'
branch_labels = None
depends_on = None


def upgrade():
    for statement in Path(__file__).with_suffix('.sql').read_text().split('\n-- statement\n'):
        if statement.strip():
            op.execute(statement)


def downgrade():
    op.execute('SELECT pg_advisory_xact_lock(194733, 1)')
    for old, new in (
        ('historical_record', 'povijesni_zapisi'),
        ('knowledge_chunk', 'odlomci_znanja'),
        ('document_record', 'zapisi_dokumenata'),
        ('document_scope', 'obuhvati_dokumenata'),
        ('enrolment_refusal', 'neprihvacanja_upisa'),
        ('enrolment', 'upisni_krugovi'),
        ('municipality_subsidy_policy', 'pravila_sufinanciranja'),
        ('municipality', 'jedinice_lokalne_samouprave'),
        ('location', 'objekti'),
        ('kindergarten_seat', 'sjedista_vrtica'),
        ('kindergarten', 'vrtici'),
        ('source_record', 'izvorni_zapisi'),
        ('data_source', 'izvori_podataka'),
    ):
        op.execute(f'ALTER TABLE {new} RENAME TO {old}')
    for statement in Path(__file__).with_name('0011_document_scope.sql').read_text().split('\n-- statement\n'):
        if 'CREATE FUNCTION check_document_scope()' in statement:
            op.execute(statement.replace('CREATE FUNCTION', 'CREATE OR REPLACE FUNCTION'))
