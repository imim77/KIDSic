"""Provider kinds backfills reviewed ownership without changing source snapshots."""
from pathlib import Path
from alembic import op

revision = '0004_provider_kinds'
down_revision = '0003_seat_geography'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(Path(__file__).with_suffix('.sql').read_text())


def downgrade():

    op.execute("""
        UPDATE kindergarten SET
            provider_kind=provenance->'provider_kind'->>'previous_kind',
            provenance=(provenance-'provider_kind') || CASE
                WHEN provenance->'provider_kind'->'previous_provenance'<>'null'::jsonb
                THEN jsonb_build_object('provider_kind',
                    provenance->'provider_kind'->'previous_provenance')
                ELSE '{}'::jsonb END
        WHERE provenance->'provider_kind'->>'migration'='0004_provider_kinds'
    """)
