CREATE TABLE municipality (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 key text NOT NULL UNIQUE CHECK (btrim(key)<>''),
 name text NOT NULL CHECK (btrim(name)<>''),
 county text,
 aliases text[] NOT NULL DEFAULT '{}'
);
-- statement
INSERT INTO municipality(key,name,aliases)
SELECT DISTINCT ON (city_key) city_key,city,city_aliases FROM location
WHERE cardinality(city_aliases)>0 ORDER BY city_key,city;
-- statement
ALTER TABLE location RENAME COLUMN city TO settlement;
-- statement
ALTER TABLE location RENAME COLUMN city_key TO settlement_key;
-- statement
ALTER TABLE location ADD COLUMN municipality_id uuid REFERENCES municipality(id);
-- statement
UPDATE location l SET municipality_id=m.id FROM municipality m WHERE m.key=l.settlement_key;
-- statement
ALTER TABLE location DROP COLUMN city_aliases;
-- statement
ALTER INDEX ix_location_city RENAME TO ix_location_settlement;
-- statement
CREATE INDEX ix_location_municipality ON location(municipality_id);
-- statement
ALTER TABLE kindergarten
 ADD COLUMN oib text UNIQUE CHECK (oib ~ '^[0-9]{11}$'),
 ADD COLUMN seat_address text,
 ADD COLUMN seat_postal_code text,
 ADD COLUMN seat_settlement text,
 ADD COLUMN seat_settlement_key text,
 ADD COLUMN seat_county text,
 ADD COLUMN seat_municipality_id uuid REFERENCES municipality(id),
 ADD CONSTRAINT kindergarten_seat_settlement_check
  CHECK ((seat_settlement IS NULL)=(seat_settlement_key IS NULL));
-- statement
CREATE INDEX ix_kindergarten_seat ON kindergarten(seat_settlement_key);
-- statement
CREATE INDEX ix_kindergarten_seat_municipality ON kindergarten(seat_municipality_id);
-- statement
ALTER TABLE source_record ADD COLUMN match_method text
 CHECK (match_method IN ('source_identity','oib','name_address','name','new','manual','unrecorded'));
-- statement
UPDATE source_record SET match_method='unrecorded' WHERE match_status<>'candidate';
-- statement
ALTER TABLE source_record ADD CONSTRAINT source_record_decided_method_check
 CHECK (match_status='candidate' OR match_method IS NOT NULL);
-- statement
ALTER TABLE availability
 ADD COLUMN program_id uuid,
 ADD COLUMN min_age_months smallint CHECK (min_age_months>=0),
 ADD COLUMN max_age_months_exclusive smallint CHECK (max_age_months_exclusive>0),
 ADD FOREIGN KEY(program_id,kindergarten_id) REFERENCES program(id,kindergarten_id),
 ADD CHECK (max_age_months_exclusive IS NULL OR min_age_months IS NULL OR max_age_months_exclusive>min_age_months);
-- statement
ALTER TABLE availability ALTER COLUMN observed_on SET NOT NULL;
-- statement
CREATE INDEX ix_availability_program ON availability(program_id);
-- statement
ALTER TABLE enrolment
 ADD COLUMN channel text CHECK (channel IN ('e_upisi','city_system','kindergarten')),
 ADD COLUMN municipality_id uuid REFERENCES municipality(id),
 ALTER COLUMN kindergarten_id DROP NOT NULL,
 ADD CONSTRAINT enrolment_scope_check CHECK (num_nonnulls(kindergarten_id,municipality_id)=1);
-- statement
ALTER TABLE enrolment ALTER COLUMN channel SET NOT NULL;
-- statement
CREATE INDEX ix_enrolment_municipality ON enrolment(municipality_id);
