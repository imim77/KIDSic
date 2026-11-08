SELECT pg_advisory_xact_lock(194733, 1);
-- statement
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM source_record r JOIN data_source s ON s.id=r.source_id
   WHERE r.batch_id IS DISTINCT FROM s.active_batch_id) THEN
   RAISE EXCEPTION 'Review non-current source records before removing batches';
 END IF;
END $$;
-- statement
DELETE FROM historical_record h USING data_source s
 WHERE h.source_id=s.id AND h.batch_id IS DISTINCT FROM s.active_batch_id;
-- statement
DROP VIEW valid_knowledge_chunk;
-- statement
DROP VIEW document_applicability;
-- statement
DROP VIEW kindergarten_seat_geography;
-- statement
ALTER TABLE historical_record
 DROP CONSTRAINT historical_record_source_id_batch_id_source_key_key,
 ADD CONSTRAINT historical_record_source_id_source_key_key UNIQUE(source_id,source_key);
-- statement
DROP INDEX ix_record_batch;
-- statement
DROP INDEX ix_historical_record_batch;
-- statement
ALTER TABLE source_record DROP COLUMN batch_id;
-- statement
ALTER TABLE historical_record DROP COLUMN batch_id;
-- statement
ALTER TABLE data_source DROP COLUMN active_batch_id;
-- statement
CREATE VIEW kindergarten_seat_geography AS
 SELECT ks.kindergarten_id,ks.longitude,ks.latitude,
        ks.attributes->>'quarter' AS quarter,ks.attributes->>'suburb' AS suburb,
        ks.attributes->>'neighbourhood' AS neighbourhood,
        ks.attributes->>'settlement' AS geo_settlement,r.id AS source_record_id
 FROM kindergarten_seat ks JOIN source_record r ON r.id=ks.geography_source_record_id
   AND r.kindergarten_id=ks.kindergarten_id AND r.location_id IS NULL AND r.match_status='accepted'
 JOIN data_source s ON s.id=r.source_id AND s.import_allowed
 WHERE ks.address=ks.attributes->>'address';
-- statement
CREATE VIEW document_applicability AS
 WITH active AS (
   SELECT r.* FROM source_record r JOIN data_source s ON s.id=r.source_id
   WHERE s.import_allowed AND r.match_status='accepted'
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
 LEFT JOIN kindergarten_seat ks ON ks.kindergarten_id=k.id
 WHERE d.municipality_id IS NOT NULL
   AND EXISTS(SELECT 1 FROM active a WHERE a.kindergarten_id=k.id)
   AND (ks.municipality_id=d.municipality_id OR EXISTS (
     SELECT 1 FROM location l JOIN active a ON a.location_id=l.id AND a.kindergarten_id=k.id
     WHERE l.kindergarten_id=k.id AND l.municipality_id=d.municipality_id));

-- statement
CREATE VIEW valid_knowledge_chunk AS
 SELECT c.id,a.kindergarten_id,c.location_id,c.content,c.source_url,c.source_record_id,
        r.observed_on,r.fetched_at,s.title AS source_title,s.license,
        CASE WHEN r.raw_data->>'kind'='enrolment_document'
          THEN r.raw_data->>'scope' END AS document_scope,
        CASE WHEN r.raw_data->>'kind'='enrolment_document'
          AND r.raw_data->>'date_kind'='published'
          THEN (r.raw_data->>'reference_date')::date END AS published_on,
        CASE WHEN r.raw_data->>'kind'='enrolment_document'
          THEN (r.raw_data->>'valid_until')::date>=current_date END AS in_effect
 FROM knowledge_chunk c
 JOIN source_record r ON r.id=c.source_record_id
 JOIN document_applicability a ON a.source_record_id=r.id
 JOIN data_source s ON s.id=r.source_id
 WHERE r.match_status='accepted' AND s.import_allowed
   AND r.kindergarten_id IS NOT DISTINCT FROM c.kindergarten_id
   AND (r.raw_data->>'evidence_scope' IS DISTINCT FROM 'registered_seat_geography'
     OR EXISTS (SELECT 1 FROM kindergarten_seat_geography sg
       WHERE sg.kindergarten_id=a.kindergarten_id AND sg.source_record_id=r.id))
   AND (r.location_id IS NULL OR r.location_id IS NOT DISTINCT FROM c.location_id);
