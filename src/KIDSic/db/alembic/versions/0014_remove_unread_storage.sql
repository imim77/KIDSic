-- Name search uses strpos over a translated name, which a trigram index cannot serve.
DROP INDEX ix_kindergarten_name;
-- statement
DROP EXTENSION pg_trgm;
-- statement
-- Distance queries build points from longitude/latitude; nothing reads this column.
ALTER TABLE location DROP COLUMN position;
-- statement
-- Written by importers but never read or constrained as unique.
ALTER TABLE knowledge_chunk DROP COLUMN content_sha256;
-- statement
-- 0013 copied every institution; importers create a seat only from seat evidence.
DELETE FROM kindergarten_seat
WHERE address IS NULL AND postal_code IS NULL AND settlement IS NULL
  AND municipality_id IS NULL AND longitude IS NULL AND attributes='{}'
  AND geography_source_record_id IS NULL;
