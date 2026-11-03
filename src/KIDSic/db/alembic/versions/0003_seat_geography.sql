ALTER TABLE kindergarten
 ADD COLUMN seat_longitude double precision CHECK (seat_longitude BETWEEN -180 AND 180),
 ADD COLUMN seat_latitude double precision CHECK (seat_latitude BETWEEN -90 AND 90),
 ADD COLUMN seat_attributes jsonb NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(seat_attributes)='object'),
 ADD CHECK ((seat_longitude IS NULL)=(seat_latitude IS NULL));
-- statement
-- Geography is usable only while its evidence and the geocoded seat address still agree.
CREATE VIEW kindergarten_seat_geography AS
 SELECT k.id AS kindergarten_id,k.seat_longitude AS longitude,k.seat_latitude AS latitude,
        k.seat_attributes->>'quarter' AS quarter,k.seat_attributes->>'suburb' AS suburb,
        k.seat_attributes->>'neighbourhood' AS neighbourhood,
        k.seat_attributes->>'settlement' AS geo_settlement,r.id AS source_record_id
 FROM kindergarten k
 JOIN source_record r ON r.id::text=k.provenance->'seat_geography'->>'source_record_id'
   AND r.kindergarten_id=k.id AND r.location_id IS NULL AND r.match_status='accepted'
 JOIN data_source s ON s.id=r.source_id AND s.import_allowed AND s.active_batch_id=r.batch_id
 WHERE k.seat_address=k.seat_attributes->>'address';
