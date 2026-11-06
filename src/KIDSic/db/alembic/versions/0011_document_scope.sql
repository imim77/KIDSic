-- Reviewed enrolment seeds are reimported after this destructive conversion.
CREATE TEMP TABLE replaced_document ON COMMIT DROP AS
 SELECT r.id FROM source_record r JOIN data_source s ON s.id=r.source_id
 WHERE s.metadata->>'kind'='enrolment_document';
-- statement
DELETE FROM knowledge_chunk WHERE source_record_id IN (SELECT id FROM replaced_document);
-- statement
DELETE FROM enrolment WHERE source_record_id IN (SELECT id FROM replaced_document);
-- statement
DELETE FROM program WHERE source_record_id IN (SELECT id FROM replaced_document);
-- statement
DELETE FROM source_record WHERE id IN (SELECT id FROM replaced_document);
-- statement
CREATE TABLE document_scope (
 source_record_id uuid NOT NULL REFERENCES source_record(id),
 municipality_id uuid REFERENCES municipality(id),
 provider_kinds text[],
 kindergarten_id uuid REFERENCES kindergarten(id),
 CHECK ((municipality_id IS NOT NULL AND provider_kinds IS NOT NULL AND kindergarten_id IS NULL
         AND cardinality(provider_kinds)>0 AND array_position(provider_kinds,NULL) IS NULL
         AND provider_kinds <@ ARRAY['municipal','private','religious','childminder','other','unknown']::text[])
     OR (municipality_id IS NULL AND provider_kinds IS NULL AND kindergarten_id IS NOT NULL))
);
-- statement
CREATE UNIQUE INDEX ix_document_scope_rule ON document_scope(source_record_id,municipality_id)
 WHERE municipality_id IS NOT NULL;
-- statement
CREATE UNIQUE INDEX ix_document_scope_owner ON document_scope(source_record_id,kindergarten_id)
 WHERE kindergarten_id IS NOT NULL;
-- statement
CREATE TABLE enrolment_refusal (
 enrolment_id uuid NOT NULL REFERENCES enrolment(id),
 kindergarten_id uuid NOT NULL REFERENCES kindergarten(id),
 source_record_id uuid NOT NULL REFERENCES source_record(id),
 PRIMARY KEY(enrolment_id,kindergarten_id)
);
-- statement
ALTER TABLE knowledge_chunk ALTER COLUMN kindergarten_id DROP NOT NULL,
 ADD CONSTRAINT chunk_document_location_owner CHECK (location_id IS NULL OR kindergarten_id IS NOT NULL);
-- statement
ALTER TABLE enrolment DROP CONSTRAINT enrolment_scope_check,
 DROP COLUMN municipality_id, DROP COLUMN accepting;
-- statement
-- Document applicability is shared by cards and RAG. Only directory evidence
-- anchors a municipality rule, so documents cannot keep removed owners alive.
CREATE VIEW document_applicability AS
 WITH active AS (
   SELECT r.* FROM source_record r JOIN data_source s ON s.id=r.source_id
   WHERE s.import_allowed AND s.active_batch_id=r.batch_id AND r.match_status='accepted'
     AND s.metadata->>'kind' IS DISTINCT FROM 'enrolment_document'
 )
 SELECT r.id AS source_record_id,r.kindergarten_id FROM source_record r
 WHERE r.kindergarten_id IS NOT NULL
 UNION
 SELECT d.source_record_id,d.kindergarten_id FROM document_scope d
 WHERE d.kindergarten_id IS NOT NULL
 UNION
 SELECT d.source_record_id,k.id FROM document_scope d JOIN kindergarten k
   ON k.provider_kind=ANY(d.provider_kinds)
 WHERE d.municipality_id IS NOT NULL
   AND EXISTS(SELECT 1 FROM active a WHERE a.kindergarten_id=k.id)
   AND (k.seat_municipality_id=d.municipality_id OR EXISTS (
     SELECT 1 FROM location l JOIN active a ON a.location_id=l.id AND a.kindergarten_id=k.id
     WHERE l.kindergarten_id=k.id AND l.municipality_id=d.municipality_id));
-- statement
-- Deferred checks allow the source, scope and chunks to be inserted in any order
-- within one import, but reject accepted ownerless evidence at commit.
CREATE FUNCTION check_document_scope() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE record_id uuid; record_ids uuid[];
BEGIN
 IF TG_TABLE_NAME='source_record' THEN record_ids=ARRAY[NEW.id];
 ELSIF TG_OP='DELETE' THEN record_ids=ARRAY[OLD.source_record_id];
 ELSIF TG_OP='UPDATE' THEN record_ids=ARRAY[OLD.source_record_id,NEW.source_record_id];
 ELSE record_ids=ARRAY[NEW.source_record_id]; END IF;
 FOREACH record_id IN ARRAY record_ids LOOP
 IF EXISTS(SELECT 1 FROM source_record r WHERE r.id=record_id
      AND r.kindergarten_id IS NULL AND r.match_status='accepted'
      AND NOT EXISTS(SELECT 1 FROM document_scope d WHERE d.source_record_id=r.id))
    OR EXISTS(SELECT 1 FROM knowledge_chunk c WHERE c.source_record_id=record_id
      AND c.kindergarten_id IS NULL AND NOT EXISTS(
        SELECT 1 FROM document_scope d WHERE d.source_record_id=record_id)) THEN
   RAISE EXCEPTION 'Ownerless document % requires document_scope',record_id USING ERRCODE='23514';
 END IF;
 END LOOP;
 RETURN NULL;
END $$;
-- statement
CREATE CONSTRAINT TRIGGER source_record_scope_check AFTER INSERT OR UPDATE ON source_record
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_document_scope();
-- statement
CREATE CONSTRAINT TRIGGER chunk_document_scope_check AFTER INSERT OR UPDATE ON knowledge_chunk
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_document_scope();
-- statement
CREATE CONSTRAINT TRIGGER document_scope_required AFTER DELETE OR UPDATE ON document_scope
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_document_scope();
