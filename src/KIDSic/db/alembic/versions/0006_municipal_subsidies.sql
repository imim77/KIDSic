CREATE TABLE municipality_subsidy_policy (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 policy_key text NOT NULL UNIQUE CHECK (btrim(policy_key)<>''),
 municipality_id uuid NOT NULL REFERENCES municipality(id),
 provider_kinds text[] NOT NULL CHECK (
   cardinality(provider_kinds)>0
   AND provider_kinds <@ ARRAY['municipal','private','religious','childminder']::text[]
   AND array_position(provider_kinds,NULL) IS NULL
 ),
 title text NOT NULL CHECK (btrim(title)<>''),
 summary text NOT NULL CHECK (btrim(summary)<>''),
 verification_status text NOT NULL CHECK (verification_status IN ('verified','partial')),
 verified_on date NOT NULL,
 valid_from date,
 valid_until date,
 rules jsonb NOT NULL CHECK (jsonb_typeof(rules)='object'),
 sources jsonb NOT NULL CHECK (jsonb_typeof(sources)='array' AND jsonb_array_length(sources)>0),
 CHECK (valid_until IS NULL OR valid_from IS NULL OR valid_until>=valid_from)
);
-- statement
CREATE INDEX ix_subsidy_municipality_period
 ON municipality_subsidy_policy(municipality_id,valid_from,valid_until);
-- statement
COMMENT ON TABLE municipality_subsidy_policy IS
 'Source-backed municipal funding rules; city and provider type identify candidate policies, not individual eligibility. NULL dates mean unconfirmed boundaries, not unlimited validity.';
-- statement
COMMENT ON COLUMN municipality_subsidy_policy.rules IS
 'Curated descriptive rules, schema_version=1. Monetary *_cents values are integer euro cents per child per month unless stated otherwise. Not an executable eligibility calculator.';
