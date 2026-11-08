DROP INDEX ix_kindergarten_name;
-- statement
DROP EXTENSION pg_trgm;
-- statement
ALTER TABLE location DROP COLUMN position;
-- statement
ALTER TABLE knowledge_chunk DROP COLUMN content_sha256;
-- statement
DELETE FROM kindergarten_seat
WHERE address IS NULL AND postal_code IS NULL AND settlement IS NULL
  AND municipality_id IS NULL AND longitude IS NULL AND attributes='{}'
  AND geography_source_record_id IS NULL;
