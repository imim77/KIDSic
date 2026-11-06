"""Separate legal seats from institutions and derive counties from municipalities."""
from pathlib import Path
from alembic import op

revision = '0013_kindergarten_seat'
down_revision = '0012_remove_programs'
branch_labels = None
depends_on = None


def upgrade():
    for statement in Path(__file__).with_suffix('.sql').read_text().split('\n-- statement\n'):
        if statement.strip():
            op.execute(statement)


def downgrade():
    op.execute('DROP VIEW document_applicability')
    op.execute('DROP VIEW kindergarten_seat_geography')
    op.execute("ALTER TABLE kindergarten\n ADD COLUMN seat_address text, ADD COLUMN seat_postal_code text, ADD COLUMN seat_settlement text,\n ADD COLUMN seat_settlement_key text, ADD COLUMN seat_county text,\n ADD COLUMN seat_municipality_id uuid REFERENCES municipality(id),\n ADD COLUMN seat_longitude double precision CHECK(seat_longitude BETWEEN -180 AND 180),\n ADD COLUMN seat_latitude double precision CHECK(seat_latitude BETWEEN -90 AND 90),\n ADD COLUMN seat_attributes jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(seat_attributes)='object'),\n ADD CONSTRAINT kindergarten_seat_settlement_check CHECK((seat_settlement IS NULL)=(seat_settlement_key IS NULL)),\n ADD CHECK((seat_longitude IS NULL)=(seat_latitude IS NULL))")
    op.execute("UPDATE kindergarten k SET seat_address=ks.address,seat_postal_code=ks.postal_code,\n seat_settlement=ks.settlement,seat_settlement_key=ks.settlement_key,seat_county=m.county,\n seat_municipality_id=ks.municipality_id,seat_longitude=ks.longitude,seat_latitude=ks.latitude,\n seat_attributes=ks.attributes,provenance=k.provenance || CASE WHEN ks.geography_source_record_id IS NOT NULL\n THEN jsonb_build_object('seat_geography',jsonb_build_object('source_record_id',ks.geography_source_record_id::text))\n ELSE '{}'::jsonb END\n FROM kindergarten_seat ks LEFT JOIN municipality m ON m.id=ks.municipality_id WHERE k.id=ks.kindergarten_id")
    op.execute('CREATE INDEX ix_kindergarten_seat ON kindergarten(seat_settlement_key)')
    op.execute('CREATE INDEX ix_kindergarten_seat_municipality ON kindergarten(seat_municipality_id)')
    op.execute('ALTER TABLE location ADD COLUMN county text')
    op.execute('UPDATE location l SET county=m.county FROM municipality m WHERE m.id=l.municipality_id')
    op.execute('DROP TABLE kindergarten_seat')
    op.execute("-- Geography is usable only while its evidence and the geocoded seat address still agree.\nCREATE VIEW kindergarten_seat_geography AS\n SELECT k.id AS kindergarten_id,k.seat_longitude AS longitude,k.seat_latitude AS latitude,\n        k.seat_attributes->>'quarter' AS quarter,k.seat_attributes->>'suburb' AS suburb,\n        k.seat_attributes->>'neighbourhood' AS neighbourhood,\n        k.seat_attributes->>'settlement' AS geo_settlement,r.id AS source_record_id\n FROM kindergarten k\n JOIN source_record r ON r.id::text=k.provenance->'seat_geography'->>'source_record_id'\n   AND r.kindergarten_id=k.id AND r.location_id IS NULL AND r.match_status='accepted'\n JOIN data_source s ON s.id=r.source_id AND s.import_allowed AND s.active_batch_id=r.batch_id\n WHERE k.seat_address=k.seat_attributes->>'address';\n")
    op.execute("CREATE VIEW document_applicability AS\n WITH active AS (\n   SELECT r.* FROM source_record r JOIN data_source s ON s.id=r.source_id\n   WHERE s.import_allowed AND s.active_batch_id=r.batch_id AND r.match_status='accepted'\n     AND s.metadata->>'kind' IS DISTINCT FROM 'enrolment_document'\n )\n SELECT r.id AS source_record_id,r.kindergarten_id FROM source_record r\n WHERE r.kindergarten_id IS NOT NULL\n UNION\n SELECT d.source_record_id,d.kindergarten_id FROM document_scope d\n WHERE d.kindergarten_id IS NOT NULL\n UNION\n SELECT d.source_record_id,k.id FROM document_scope d JOIN kindergarten k\n   ON k.provider_kind=ANY(d.provider_kinds)\n WHERE d.municipality_id IS NOT NULL\n   AND EXISTS(SELECT 1 FROM active a WHERE a.kindergarten_id=k.id)\n   AND (k.seat_municipality_id=d.municipality_id OR EXISTS (\n     SELECT 1 FROM location l JOIN active a ON a.location_id=l.id AND a.kindergarten_id=k.id\n     WHERE l.kindergarten_id=k.id AND l.municipality_id=d.municipality_id));\n")
