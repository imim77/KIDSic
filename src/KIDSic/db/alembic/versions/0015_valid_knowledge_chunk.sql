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
 WHERE r.match_status='accepted' AND s.import_allowed AND s.active_batch_id=r.batch_id
   AND r.kindergarten_id IS NOT DISTINCT FROM c.kindergarten_id
   AND (r.raw_data->>'evidence_scope' IS DISTINCT FROM 'registered_seat_geography'
     OR EXISTS (SELECT 1 FROM kindergarten_seat_geography sg
       WHERE sg.kindergarten_id=a.kindergarten_id AND sg.source_record_id=r.id))
   AND (r.location_id IS NULL OR r.location_id IS NOT DISTINCT FROM c.location_id);
