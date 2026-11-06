ALTER TABLE knowledge_chunk DROP COLUMN program_id, DROP COLUMN search_text;
-- statement
DROP TABLE program;
-- statement
ALTER TABLE data_source DROP COLUMN stale_after_days;
