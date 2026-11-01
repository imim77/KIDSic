CREATE EXTENSION IF NOT EXISTS postgis;
-- statement
CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- statement
CREATE TABLE data_source (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 dataset_key text NOT NULL UNIQUE,
 title text NOT NULL,
 publisher text NOT NULL,
 url text NOT NULL,
 license text,
 import_allowed boolean NOT NULL DEFAULT false,
 active_batch_id uuid,
 fetched_at timestamptz,
 observed_on date,
 stale_after_days integer CHECK (stale_after_days > 0),
 metadata jsonb NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(metadata)='object')
);
-- statement
CREATE TABLE kindergarten (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 name text NOT NULL CHECK (btrim(name)<>''),
 provider_kind text NOT NULL DEFAULT 'unknown' CHECK (provider_kind IN ('municipal','private','religious','childminder','other','unknown')),
 email text, phone text, website_url text,
 provenance jsonb NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(provenance)='object')
);
-- statement
CREATE TABLE location (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 kindergarten_id uuid REFERENCES kindergarten(id),
 name text NOT NULL,
 kind text NOT NULL DEFAULT 'unknown' CHECK (kind IN ('main','branch','unknown')),
 address text, postal_code text,
 city text NOT NULL,
 city_key text NOT NULL,
 city_aliases text[] NOT NULL DEFAULT '{}',
 county text, district text,
 longitude double precision CHECK (longitude BETWEEN -180 AND 180),
 latitude double precision CHECK (latitude BETWEEN -90 AND 90),
 position geography(Point,4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude,latitude),4326)::geography) STORED,
 attributes jsonb NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(attributes)='object'),
 provenance jsonb NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(provenance)='object'),
 UNIQUE(id,kindergarten_id),
 CHECK ((longitude IS NULL)=(latitude IS NULL))
);
-- statement
CREATE INDEX ix_location_city ON location(city_key);
-- statement
CREATE INDEX ix_location_owner ON location(kindergarten_id);
-- statement
CREATE INDEX ix_location_position ON location USING gist(position);
-- statement
CREATE INDEX ix_kindergarten_name ON kindergarten USING gin(name gin_trgm_ops);
-- statement
CREATE TABLE source_record (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 source_id uuid NOT NULL REFERENCES data_source(id),
 batch_id uuid NOT NULL,
 source_key text,
 raw_data jsonb NOT NULL CHECK (jsonb_typeof(raw_data)='object'),
 fetched_at timestamptz NOT NULL DEFAULT now(),
 observed_on date,
 kindergarten_id uuid REFERENCES kindergarten(id),
 location_id uuid,
 match_status text NOT NULL DEFAULT 'candidate' CHECK (match_status IN ('candidate','accepted','rejected')),
 match_note text,
 FOREIGN KEY(location_id,kindergarten_id) REFERENCES location(id,kindergarten_id),
 CHECK (location_id IS NULL OR kindergarten_id IS NOT NULL)
);
-- statement
CREATE INDEX ix_record_batch ON source_record(source_id,batch_id);
-- statement
CREATE INDEX ix_record_owner ON source_record(kindergarten_id,location_id);
-- statement
CREATE TABLE program (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 kindergarten_id uuid NOT NULL REFERENCES kindergarten(id),
 location_id uuid,
 source_record_id uuid NOT NULL REFERENCES source_record(id),
 name text NOT NULL,
 min_age_months smallint CHECK (min_age_months>=0),
 max_age_months_exclusive smallint CHECK (max_age_months_exclusive>0),
 verified_on date NOT NULL,
 valid_until date,
 languages text[] NOT NULL DEFAULT '{}',
 FOREIGN KEY(location_id,kindergarten_id) REFERENCES location(id,kindergarten_id),
 UNIQUE(id,kindergarten_id),
 CHECK (max_age_months_exclusive IS NULL OR min_age_months IS NULL OR max_age_months_exclusive>min_age_months),
 CHECK (valid_until IS NULL OR valid_until>=verified_on)
);
-- statement
CREATE INDEX ix_program_owner ON program(kindergarten_id,location_id);
-- statement
CREATE INDEX ix_program_source ON program(source_record_id);
-- statement
CREATE TABLE availability (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 kindergarten_id uuid NOT NULL REFERENCES kindergarten(id),
 location_id uuid,
 source_record_id uuid NOT NULL REFERENCES source_record(id),
 age_label text, program_label text,
 free_places integer CHECK(free_places>=0),
 observed_on date,
 FOREIGN KEY(location_id,kindergarten_id) REFERENCES location(id,kindergarten_id)
);
-- statement
CREATE INDEX ix_availability_owner ON availability(kindergarten_id,location_id);
-- statement
CREATE INDEX ix_availability_source ON availability(source_record_id);
-- statement
CREATE TABLE enrolment (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 kindergarten_id uuid NOT NULL REFERENCES kindergarten(id),
 source_record_id uuid NOT NULL REFERENCES source_record(id),
 academic_year text NOT NULL,
 application_url text NOT NULL,
 opens_at timestamptz, closes_at timestamptz,
 steps jsonb NOT NULL DEFAULT '[]' CHECK(jsonb_typeof(steps)='array'),
 documents jsonb NOT NULL DEFAULT '[]' CHECK(jsonb_typeof(documents)='array'),
 CHECK (closes_at IS NULL OR opens_at IS NULL OR closes_at>=opens_at)
);
-- statement
CREATE INDEX ix_enrolment_owner ON enrolment(kindergarten_id);
-- statement
CREATE INDEX ix_enrolment_source ON enrolment(source_record_id);
