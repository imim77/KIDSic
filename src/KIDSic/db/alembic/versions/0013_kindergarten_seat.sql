DO $$
DECLARE differences text;
BEGIN
 SELECT string_agg(t.name || ': ' || t.county || ' / ' || COALESCE(m.county,'missing municipality county'), '; ')
 INTO differences FROM (
   SELECT name,seat_county AS county,seat_municipality_id AS municipality_id FROM kindergarten
   UNION ALL SELECT name,county,municipality_id FROM location
 ) t LEFT JOIN municipality m ON m.id=t.municipality_id
 WHERE t.county IS NOT NULL AND btrim(t.county) IS DISTINCT FROM btrim(m.county);
 IF differences IS NOT NULL THEN RAISE EXCEPTION 'Review county differences: %',differences; END IF;
END $$;
-- statement
CREATE TABLE kindergarten_seat (
 kindergarten_id uuid PRIMARY KEY REFERENCES kindergarten(id),
 address text, postal_code text, settlement text, settlement_key text,
 municipality_id uuid REFERENCES municipality(id),
 longitude double precision CHECK(longitude BETWEEN -180 AND 180),
 latitude double precision CHECK(latitude BETWEEN -90 AND 90),
 attributes jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(attributes)='object'),
 geography_source_record_id uuid REFERENCES source_record(id),
 CHECK((settlement IS NULL)=(settlement_key IS NULL)),
 CHECK((longitude IS NULL)=(latitude IS NULL))
);
-- statement
CREATE INDEX ix_seat_settlement ON kindergarten_seat(settlement_key);
-- statement
CREATE INDEX ix_seat_municipality ON kindergarten_seat(municipality_id);
-- statement
CREATE INDEX ix_seat_geography_source ON kindergarten_seat(geography_source_record_id);
-- statement
INSERT INTO kindergarten_seat(kindergarten_id,address,postal_code,settlement,settlement_key,
 municipality_id,longitude,latitude,attributes,geography_source_record_id)
 SELECT id,seat_address,seat_postal_code,seat_settlement,seat_settlement_key,
 seat_municipality_id,seat_longitude,seat_latitude,seat_attributes,
 (provenance->'seat_geography'->>'source_record_id')::uuid FROM kindergarten;
-- statement
DROP VIEW kindergarten_seat_geography;
-- statement
DROP VIEW document_applicability;
-- statement
ALTER TABLE kindergarten DROP COLUMN seat_address, DROP COLUMN seat_postal_code,
 DROP COLUMN seat_settlement, DROP COLUMN seat_settlement_key, DROP COLUMN seat_county,
 DROP COLUMN seat_municipality_id, DROP COLUMN seat_longitude, DROP COLUMN seat_latitude,
 DROP COLUMN seat_attributes;
-- statement
ALTER TABLE location DROP COLUMN county;
-- statement
UPDATE kindergarten SET provenance=provenance - 'seat_geography' - 'seat_county';
-- statement
UPDATE location SET provenance=provenance - 'county';
-- statement
CREATE VIEW kindergarten_seat_geography AS
 SELECT ks.kindergarten_id,ks.longitude,ks.latitude,
        ks.attributes->>'quarter' AS quarter,ks.attributes->>'suburb' AS suburb,
        ks.attributes->>'neighbourhood' AS neighbourhood,
        ks.attributes->>'settlement' AS geo_settlement,r.id AS source_record_id
 FROM kindergarten_seat ks JOIN source_record r ON r.id=ks.geography_source_record_id
   AND r.kindergarten_id=ks.kindergarten_id AND r.location_id IS NULL AND r.match_status='accepted'
 JOIN data_source s ON s.id=r.source_id AND s.import_allowed AND s.active_batch_id=r.batch_id
 WHERE ks.address=ks.attributes->>'address';
-- statement
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
 LEFT JOIN kindergarten_seat ks ON ks.kindergarten_id=k.id
 WHERE d.municipality_id IS NOT NULL
   AND EXISTS(SELECT 1 FROM active a WHERE a.kindergarten_id=k.id)
   AND (ks.municipality_id=d.municipality_id OR EXISTS (
     SELECT 1 FROM location l JOIN active a ON a.location_id=l.id AND a.kindergarten_id=k.id
     WHERE l.kindergarten_id=k.id AND l.municipality_id=d.municipality_id));
