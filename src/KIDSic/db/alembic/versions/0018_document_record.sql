SELECT pg_advisory_xact_lock(194733, 1);
-- statement
ALTER TABLE data_source ADD COLUMN kind text NOT NULL DEFAULT 'general'
 CHECK(kind IN ('general','enrolment_document'));
-- statement
UPDATE data_source SET kind=COALESCE(metadata->>'kind','general');
-- statement
-- Stop rather than discard conflicting application metadata.
DO $$ BEGIN
 IF EXISTS (
   SELECT 1 FROM source_record r JOIN data_source s ON s.id=r.source_id
   WHERE s.kind='enrolment_document' AND (
     r.raw_data->>'kind' IS DISTINCT FROM s.kind
     OR r.raw_data->>'document_url' IS DISTINCT FROM s.url
     OR r.raw_data->>'snapshot_key' IS DISTINCT FROM s.metadata->>'snapshot_key'
     OR r.observed_on IS DISTINCT FROM CASE WHEN r.raw_data->>'date_kind'='observed'
       THEN (r.raw_data->>'reference_date')::date END
     OR NOT EXISTS(SELECT 1 FROM document_scope ds WHERE ds.source_record_id=r.id)
     OR r.raw_data->>'scope' IS DISTINCT FROM CASE WHEN EXISTS (
       SELECT 1 FROM document_scope ds WHERE ds.source_record_id=r.id
         AND ds.municipality_id IS NOT NULL) THEN 'municipality' ELSE 'institution' END
   )
 ) THEN
   RAISE EXCEPTION 'Review conflicting document metadata before migration';
 END IF;
END $$;
-- statement
CREATE TABLE document_record (
 source_record_id uuid PRIMARY KEY REFERENCES source_record(id) ON DELETE CASCADE,
 reference_date date NOT NULL,
 date_kind text NOT NULL CHECK(date_kind IN ('published','observed')),
 valid_until date CHECK(valid_until>=reference_date)
);
-- statement
INSERT INTO document_record(source_record_id,reference_date,date_kind,valid_until)
 SELECT r.id,(r.raw_data->>'reference_date')::date,r.raw_data->>'date_kind',
        (r.raw_data->>'valid_until')::date
 FROM source_record r JOIN data_source s ON s.id=r.source_id
 WHERE s.kind='enrolment_document';
-- statement
DROP VIEW valid_knowledge_chunk;
-- statement
DROP VIEW document_applicability;
-- statement
CREATE VIEW document_applicability AS
 WITH active AS (
   SELECT r.* FROM source_record r JOIN data_source s ON s.id=r.source_id
   WHERE s.import_allowed AND r.match_status='accepted'
     AND s.kind<>'enrolment_document'
 )
 SELECT r.id AS source_record_id,r.kindergarten_id FROM source_record r
 WHERE r.kindergarten_id IS NOT NULL
 UNION
 SELECT d.source_record_id,d.kindergarten_id FROM document_scope d
 WHERE d.kindergarten_id IS NOT NULL
 UNION
 SELECT d.source_record_id,k.id FROM document_scope d JOIN kindergarten k
   ON k.provider_kind=ANY(d.provider_kinds)
 LEFT JOIN kindergarten_seat ks ON ks.kindergarten_id=k.id
 WHERE d.municipality_id IS NOT NULL
   AND EXISTS(SELECT 1 FROM active a WHERE a.kindergarten_id=k.id)
   AND (ks.municipality_id=d.municipality_id OR EXISTS (
     SELECT 1 FROM location l JOIN active a ON a.location_id=l.id AND a.kindergarten_id=k.id
     WHERE l.kindergarten_id=k.id AND l.municipality_id=d.municipality_id));

-- statement
-- ValidKnowledgeChunk keeps evidence checks independent of request selection.
CREATE VIEW valid_knowledge_chunk AS
 SELECT c.id,a.kindergarten_id,c.location_id,c.content,c.source_url,c.source_record_id,
        CASE WHEN s.kind='enrolment_document' THEN
          CASE WHEN d.date_kind='observed' THEN d.reference_date END
          ELSE r.observed_on END AS observed_on,
        r.fetched_at,s.title AS source_title,s.license,
        CASE WHEN s.kind='enrolment_document' THEN
          CASE WHEN EXISTS(SELECT 1 FROM document_scope ds
            WHERE ds.source_record_id=r.id AND ds.municipality_id IS NOT NULL)
            THEN 'municipality' ELSE 'institution' END END AS document_scope,
        CASE WHEN s.kind='enrolment_document' AND d.date_kind='published'
          THEN d.reference_date END AS published_on,
        CASE WHEN s.kind='enrolment_document'
          THEN d.valid_until>=current_date END AS in_effect
 FROM knowledge_chunk c
 JOIN source_record r ON r.id=c.source_record_id
 JOIN document_applicability a ON a.source_record_id=r.id
 JOIN data_source s ON s.id=r.source_id
 LEFT JOIN document_record d ON d.source_record_id=r.id
 WHERE r.match_status='accepted' AND s.import_allowed
   AND (s.kind<>'enrolment_document' OR d.source_record_id IS NOT NULL)
   AND r.kindergarten_id IS NOT DISTINCT FROM c.kindergarten_id
   AND (r.raw_data->>'evidence_scope' IS DISTINCT FROM 'registered_seat_geography'
     OR EXISTS (SELECT 1 FROM kindergarten_seat_geography sg
       WHERE sg.kindergarten_id=a.kindergarten_id AND sg.source_record_id=r.id))
   AND (r.location_id IS NULL OR r.location_id IS NOT DISTINCT FROM c.location_id);

-- statement
UPDATE source_record r
 SET raw_data=r.raw_data-ARRAY['kind','scope','reference_date','date_kind',
                              'valid_until','document_url','snapshot_key']
 FROM data_source s WHERE s.id=r.source_id AND s.kind='enrolment_document';
-- statement
UPDATE data_source SET metadata=metadata-'kind';
