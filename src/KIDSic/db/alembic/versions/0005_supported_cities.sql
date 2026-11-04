-- Coordinate cleanup with ordinary imports; all deletions share one transaction.
SELECT pg_advisory_xact_lock(194733, 1);
-- statement
CREATE TEMP TABLE removed_city_location ON COMMIT DROP AS
SELECT l.id FROM location l LEFT JOIN municipality m ON m.id=l.municipality_id
WHERE COALESCE(m.key,l.settlement_key,'') NOT IN ('zagreb','varazdin','rijeka');
-- statement
-- An institution outside the cities can still operate a supported facility.
CREATE TEMP TABLE removed_city_kindergarten ON COMMIT DROP AS
SELECT k.id FROM kindergarten k LEFT JOIN municipality m ON m.id=k.seat_municipality_id
WHERE COALESCE(m.key,k.seat_settlement_key,'') NOT IN ('zagreb','varazdin','rijeka')
  AND NOT EXISTS (SELECT 1 FROM location l WHERE l.kindergarten_id=k.id
                  AND l.id NOT IN (SELECT id FROM removed_city_location));
-- statement
CREATE TEMP TABLE removed_city_record ON COMMIT DROP AS
SELECT r.id FROM source_record r JOIN data_source s ON s.id=r.source_id
WHERE r.kindergarten_id IN (SELECT id FROM removed_city_kindergarten)
   OR r.location_id IN (SELECT id FROM removed_city_location)
   OR (r.kindergarten_id IS NULL AND r.location_id IS NULL AND s.dataset_key='national'
       AND NOT (COALESCE(lower(btrim(r.raw_data->>'Zupanija')),'')='grad zagreb'
         OR (COALESCE(translate(lower(btrim(r.raw_data->>'Mjesto')),'čćđšž','ccdsz'),'')='varazdin'
             AND COALESCE(translate(lower(btrim(r.raw_data->>'Zupanija')),'čćđšž','ccdsz'),'')='varazdinska zupanija')
         OR (COALESCE(lower(btrim(r.raw_data->>'Mjesto')),'')='rijeka'
             AND COALESCE(translate(lower(btrim(r.raw_data->>'Zupanija')),'čćđšž','ccdsz'),'')='primorsko-goranska zupanija')));
-- statement
CREATE TEMP TABLE removed_city_program ON COMMIT DROP AS
SELECT id FROM program
WHERE kindergarten_id IN (SELECT id FROM removed_city_kindergarten)
   OR location_id IN (SELECT id FROM removed_city_location)
   OR source_record_id IN (SELECT id FROM removed_city_record);
-- statement
DELETE FROM knowledge_chunk
WHERE kindergarten_id IN (SELECT id FROM removed_city_kindergarten)
   OR location_id IN (SELECT id FROM removed_city_location)
   OR program_id IN (SELECT id FROM removed_city_program)
   OR source_record_id IN (SELECT id FROM removed_city_record);
-- statement
DELETE FROM availability
WHERE kindergarten_id IN (SELECT id FROM removed_city_kindergarten)
   OR location_id IN (SELECT id FROM removed_city_location)
   OR program_id IN (SELECT id FROM removed_city_program)
   OR source_record_id IN (SELECT id FROM removed_city_record);
-- statement
DELETE FROM enrolment
WHERE kindergarten_id IN (SELECT id FROM removed_city_kindergarten)
   OR municipality_id IN (SELECT id FROM municipality WHERE key NOT IN ('zagreb','varazdin','rijeka'))
   OR source_record_id IN (SELECT id FROM removed_city_record);
-- statement
DELETE FROM program WHERE id IN (SELECT id FROM removed_city_program);
-- statement
DELETE FROM source_record WHERE id IN (SELECT id FROM removed_city_record);
-- statement
DELETE FROM location WHERE id IN (SELECT id FROM removed_city_location);
-- statement
DELETE FROM kindergarten WHERE id IN (SELECT id FROM removed_city_kindergarten);
-- statement
-- A retained provider's legal seat can reference an outside municipality.
DELETE FROM municipality m WHERE m.key NOT IN ('zagreb','varazdin','rijeka')
  AND NOT EXISTS (SELECT 1 FROM kindergarten k WHERE k.seat_municipality_id=m.id)
  AND NOT EXISTS (SELECT 1 FROM location l WHERE l.municipality_id=m.id);
-- statement
DROP TABLE removed_city_program,removed_city_record,removed_city_kindergarten,removed_city_location;
