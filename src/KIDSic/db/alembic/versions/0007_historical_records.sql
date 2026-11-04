CREATE TABLE historical_record (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 source_id uuid NOT NULL REFERENCES data_source(id),
 batch_id uuid NOT NULL,
 source_key text NOT NULL,
 raw_data jsonb NOT NULL CHECK(jsonb_typeof(raw_data)='object'),
 kindergarten_id uuid REFERENCES kindergarten(id),
 location_id uuid,
 scope text NOT NULL CHECK(scope IN ('facility','institution')),
 match_status text NOT NULL CHECK(match_status IN ('accepted','candidate')),
 reference_date date NOT NULL,
 date_kind text NOT NULL CHECK(date_kind IN ('published','observed')),
 fetched_at timestamptz NOT NULL,
 programs text[] NOT NULL DEFAULT '{}',
 vacancies jsonb NOT NULL DEFAULT '[]' CHECK(jsonb_typeof(vacancies)='array'),
 FOREIGN KEY(location_id,kindergarten_id) REFERENCES location(id,kindergarten_id),
 UNIQUE(source_id,batch_id,source_key),
 CHECK(match_status<>'accepted' OR kindergarten_id IS NOT NULL),
 CHECK(location_id IS NULL OR kindergarten_id IS NOT NULL),
 CHECK(match_status<>'accepted' OR (scope='facility')=(location_id IS NOT NULL))
);
-- statement
CREATE INDEX ix_historical_record_scope ON historical_record(kindergarten_id,location_id);
-- statement
CREATE INDEX ix_historical_record_batch ON historical_record(source_id,batch_id);
