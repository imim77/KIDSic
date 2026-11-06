DROP TABLE availability;
-- statement
ALTER TABLE knowledge_chunk DROP COLUMN embedding, DROP COLUMN embedding_model;
-- statement
ALTER TABLE enrolment DROP COLUMN steps, DROP COLUMN documents;
