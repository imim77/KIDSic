UPDATE source_record r SET source_key=r.kindergarten_id::text || ':' || r.source_key
FROM data_source s WHERE s.id=r.source_id AND s.dataset_key LIKE 'varazdin-other-%'
 AND r.source_key NOT LIKE r.kindergarten_id::text || ':%';
-- statement
UPDATE kindergarten k SET provenance=jsonb_set(k.provenance,'{provider_kind}',
    (k.provenance->'provider_kind') || jsonb_build_object('source_record_id',current.id::text))
FROM source_record old JOIN data_source s ON s.id=old.source_id
JOIN source_record current ON current.source_id=s.id AND current.batch_id=s.active_batch_id
 AND current.source_key=old.source_key AND current.kindergarten_id=old.kindergarten_id
 AND current.match_status='accepted'
WHERE old.id::text=k.provenance->'provider_kind'->>'source_record_id'
 AND old.batch_id IS DISTINCT FROM s.active_batch_id AND k.provider_kind='unknown';
-- statement
DO $$
DECLARE unresolved text;
BEGIN
 SELECT string_agg(DISTINCT t.name || ':' || f.key, ', ') INTO unresolved
 FROM (SELECT name,provenance FROM kindergarten UNION ALL SELECT name,provenance FROM location) t
 CROSS JOIN LATERAL jsonb_each(t.provenance) f
 JOIN source_record r ON r.id::text=f.value->>'source_record_id'
 JOIN data_source s ON s.id=r.source_id
 WHERE r.batch_id IS DISTINCT FROM s.active_batch_id;
 IF unresolved IS NOT NULL THEN
   RAISE EXCEPTION 'Review stale field evidence before current-state migration: %', unresolved;
 END IF;
END $$;
-- statement
CREATE TEMP TABLE obsolete_source_record ON COMMIT DROP AS
 SELECT r.id FROM source_record r JOIN data_source s ON s.id=r.source_id
 WHERE r.batch_id IS DISTINCT FROM s.active_batch_id;
-- statement
DELETE FROM knowledge_chunk WHERE source_record_id IN (SELECT id FROM obsolete_source_record)
 OR program_id IN (SELECT id FROM program WHERE source_record_id IN (SELECT id FROM obsolete_source_record));
-- statement
DELETE FROM enrolment WHERE source_record_id IN (SELECT id FROM obsolete_source_record);
-- statement
DELETE FROM program WHERE source_record_id IN (SELECT id FROM obsolete_source_record);
-- statement
DELETE FROM source_record WHERE id IN (SELECT id FROM obsolete_source_record);
-- statement
ALTER TABLE source_record ADD CONSTRAINT source_record_source_key_unique UNIQUE(source_id,source_key);
