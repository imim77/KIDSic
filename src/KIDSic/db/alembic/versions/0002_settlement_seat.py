"""Settlement/municipality split, institution seat, identifiers and scoped places/enrolment.

The adjacent SQL is an immutable part of this revision, not an application model.
"""

from pathlib import Path

from alembic import op

revision = "0002_settlement_seat"
down_revision = "0001_simple_rag"
branch_labels = None
depends_on = None


def upgrade():
    ddl = Path(__file__).with_suffix(".sql").read_text(encoding="utf-8")
    for statement in ddl.split("\n-- statement\n"):
        if statement.strip():
            op.execute(statement)


def downgrade():


    for statement in (
        "DROP INDEX ix_enrolment_municipality",
        "ALTER TABLE enrolment DROP CONSTRAINT enrolment_scope_check, DROP COLUMN channel,"
        " DROP COLUMN municipality_id, ALTER COLUMN kindergarten_id SET NOT NULL",
        "DROP INDEX ix_availability_program",
        "ALTER TABLE availability ALTER COLUMN observed_on DROP NOT NULL, DROP COLUMN program_id,"
        " DROP COLUMN min_age_months, DROP COLUMN max_age_months_exclusive",
        "ALTER TABLE source_record DROP COLUMN match_method",
        "DROP INDEX ix_kindergarten_seat_municipality",
        "DROP INDEX ix_kindergarten_seat",
        "ALTER TABLE kindergarten DROP COLUMN oib, DROP COLUMN seat_address, DROP COLUMN seat_postal_code,"
        " DROP COLUMN seat_settlement, DROP COLUMN seat_settlement_key, DROP COLUMN seat_county,"
        " DROP COLUMN seat_municipality_id",
        "DROP INDEX ix_location_municipality",
        "ALTER INDEX ix_location_settlement RENAME TO ix_location_city",
        "ALTER TABLE location ADD COLUMN city_aliases text[] NOT NULL DEFAULT '{}'",
        "UPDATE location l SET city_aliases=m.aliases FROM municipality m WHERE m.id=l.municipality_id",
        "ALTER TABLE location DROP COLUMN municipality_id",
        "ALTER TABLE location RENAME COLUMN settlement_key TO city_key",
        "ALTER TABLE location RENAME COLUMN settlement TO city",
        "DROP TABLE municipality",
    ):
        op.execute(statement)
