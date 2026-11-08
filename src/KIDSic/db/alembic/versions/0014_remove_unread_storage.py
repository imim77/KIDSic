"""Remove indexes, columns and empty seats that no query reads."""
from pathlib import Path
from alembic import op

revision = '0014_remove_unread_storage'
down_revision = '0013_kindergarten_seat'
branch_labels = None
depends_on = None


def upgrade():
    for statement in Path(__file__).with_suffix('.sql').read_text().split('\n-- statement\n'):
        if statement.strip():
            op.execute(statement)


def downgrade():
    op.execute("INSERT INTO kindergarten_seat(kindergarten_id) SELECT id FROM kindergarten\n"
               " ON CONFLICT(kindergarten_id) DO NOTHING")
    op.execute('ALTER TABLE knowledge_chunk ADD COLUMN content_sha256 text')
    op.execute("UPDATE knowledge_chunk SET content_sha256=encode(sha256(convert_to(content,'UTF8')),'hex')")

    op.execute('SET CONSTRAINTS ALL IMMEDIATE')
    op.execute("ALTER TABLE knowledge_chunk ALTER COLUMN content_sha256 SET NOT NULL,\n"
               " ADD CHECK(content_sha256 ~ '^[0-9a-f]{64}$')")
    op.execute('ALTER TABLE location ADD COLUMN position geography(Point,4326) GENERATED ALWAYS AS\n'
               ' (ST_SetSRID(ST_MakePoint(longitude,latitude),4326)::geography) STORED')
    op.execute('CREATE INDEX ix_location_position ON location USING gist(position)')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    op.execute('CREATE INDEX ix_kindergarten_name ON kindergarten USING gin(name gin_trgm_ops)')
