ALTER TABLE knowledge_chunk DROP CONSTRAINT knowledge_chunk_source_record_id_fkey,
 ADD CONSTRAINT knowledge_chunk_source_record_id_fkey
 FOREIGN KEY (source_record_id) REFERENCES source_record(id) ON DELETE CASCADE;
-- statement
ALTER TABLE enrolment DROP CONSTRAINT enrolment_source_record_id_fkey,
 ADD CONSTRAINT enrolment_source_record_id_fkey
 FOREIGN KEY (source_record_id) REFERENCES source_record(id) ON DELETE CASCADE;
-- statement
ALTER TABLE enrolment_refusal DROP CONSTRAINT enrolment_refusal_source_record_id_fkey,
 ADD CONSTRAINT enrolment_refusal_source_record_id_fkey
 FOREIGN KEY (source_record_id) REFERENCES source_record(id) ON DELETE CASCADE;
-- statement
ALTER TABLE enrolment_refusal DROP CONSTRAINT enrolment_refusal_enrolment_id_fkey,
 ADD CONSTRAINT enrolment_refusal_enrolment_id_fkey
 FOREIGN KEY (enrolment_id) REFERENCES enrolment(id) ON DELETE CASCADE;
-- statement
ALTER TABLE document_scope DROP CONSTRAINT document_scope_source_record_id_fkey,
 ADD CONSTRAINT document_scope_source_record_id_fkey
 FOREIGN KEY (source_record_id) REFERENCES source_record(id) ON DELETE CASCADE;
