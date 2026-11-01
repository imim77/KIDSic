# Rječnik podataka — KIDSic

Generirano iz migrirane baze naredbom `uv run python scripts/export_database_model.py`.
Revizija: `0001_simple_rag`. PK = primarni ključ, FK = strani ključ, UQ = jedinstveno ograničenje.
Kod složenih ključeva oznaka u retku označava sudjelovanje u ključu; puni sastav naveden je pod ograničenjima.
`NULL` znači nepoznatu/neprimjenjivu vrijednost prema pravilima u [ERA.md](ERA.md).

## Izvori

### `data_source`

| Stupac | PostgreSQL tip | NULL | Ključ | Zadano / generirano |
|---|---|---|---|---|
| `id` | `uuid` | ne | PK | gen_random_uuid() |
| `dataset_key` | `text` | ne | UQ | — |
| `title` | `text` | ne | — | — |
| `publisher` | `text` | ne | — | — |
| `url` | `text` | ne | — | — |
| `license` | `text` | da | — | — |
| `import_allowed` | `boolean` | ne | — | false |
| `active_batch_id` | `uuid` | da | — | — |
| `fetched_at` | `timestamp with time zone` | da | — | — |
| `observed_on` | `date` | da | — | — |
| `stale_after_days` | `integer` | da | — | — |
| `metadata` | `jsonb` | ne | — | '{}'::jsonb |

Ograničenja:

- `data_source_metadata_check`: `CHECK ((jsonb_typeof(metadata) = 'object'::text))`
- `data_source_stale_after_days_check`: `CHECK ((stale_after_days > 0))`
- `data_source_pkey`: `PRIMARY KEY (id)`
- `data_source_dataset_key_key`: `UNIQUE (dataset_key)`

Indeksi:

- `data_source_dataset_key_key`: `CREATE UNIQUE INDEX data_source_dataset_key_key ON public.data_source USING btree (dataset_key)`
- `data_source_pkey`: `CREATE UNIQUE INDEX data_source_pkey ON public.data_source USING btree (id)`

### `source_record`

| Stupac | PostgreSQL tip | NULL | Ključ | Zadano / generirano |
|---|---|---|---|---|
| `id` | `uuid` | ne | PK | gen_random_uuid() |
| `source_id` | `uuid` | ne | FK | — |
| `batch_id` | `uuid` | ne | — | — |
| `source_key` | `text` | da | — | — |
| `raw_data` | `jsonb` | ne | — | — |
| `fetched_at` | `timestamp with time zone` | ne | — | now() |
| `observed_on` | `date` | da | — | — |
| `kindergarten_id` | `uuid` | da | FK | — |
| `location_id` | `uuid` | da | FK | — |
| `match_status` | `text` | ne | — | 'candidate'::text |
| `match_note` | `text` | da | — | — |

Ograničenja:

- `source_record_check`: `CHECK (((location_id IS NULL) OR (kindergarten_id IS NOT NULL)))`
- `source_record_match_status_check`: `CHECK ((match_status = ANY (ARRAY['candidate'::text, 'accepted'::text, 'rejected'::text])))`
- `source_record_raw_data_check`: `CHECK ((jsonb_typeof(raw_data) = 'object'::text))`
- `source_record_kindergarten_id_fkey`: `FOREIGN KEY (kindergarten_id) REFERENCES kindergarten(id)`
- `source_record_location_id_kindergarten_id_fkey`: `FOREIGN KEY (location_id, kindergarten_id) REFERENCES location(id, kindergarten_id)`
- `source_record_source_id_fkey`: `FOREIGN KEY (source_id) REFERENCES data_source(id)`
- `source_record_pkey`: `PRIMARY KEY (id)`

Indeksi:

- `ix_record_batch`: `CREATE INDEX ix_record_batch ON public.source_record USING btree (source_id, batch_id)`
- `ix_record_owner`: `CREATE INDEX ix_record_owner ON public.source_record USING btree (kindergarten_id, location_id)`
- `source_record_pkey`: `CREATE UNIQUE INDEX source_record_pkey ON public.source_record USING btree (id)`

## Vrtići i pretraga

### `kindergarten`

| Stupac | PostgreSQL tip | NULL | Ključ | Zadano / generirano |
|---|---|---|---|---|
| `id` | `uuid` | ne | PK | gen_random_uuid() |
| `name` | `text` | ne | — | — |
| `provider_kind` | `text` | ne | — | 'unknown'::text |
| `email` | `text` | da | — | — |
| `phone` | `text` | da | — | — |
| `website_url` | `text` | da | — | — |
| `provenance` | `jsonb` | ne | — | '{}'::jsonb |

Ograničenja:

- `kindergarten_name_check`: `CHECK ((btrim(name) <> ''::text))`
- `kindergarten_provenance_check`: `CHECK ((jsonb_typeof(provenance) = 'object'::text))`
- `kindergarten_provider_kind_check`: `CHECK ((provider_kind = ANY (ARRAY['municipal'::text, 'private'::text, 'religious'::text, 'childminder'::text, 'other'::text, 'unknown'::text])))`
- `kindergarten_pkey`: `PRIMARY KEY (id)`

Indeksi:

- `ix_kindergarten_name`: `CREATE INDEX ix_kindergarten_name ON public.kindergarten USING gin (name gin_trgm_ops)`
- `kindergarten_pkey`: `CREATE UNIQUE INDEX kindergarten_pkey ON public.kindergarten USING btree (id)`

### `location`

| Stupac | PostgreSQL tip | NULL | Ključ | Zadano / generirano |
|---|---|---|---|---|
| `id` | `uuid` | ne | PK, UQ | gen_random_uuid() |
| `kindergarten_id` | `uuid` | da | FK, UQ | — |
| `name` | `text` | ne | — | — |
| `kind` | `text` | ne | — | 'unknown'::text |
| `address` | `text` | da | — | — |
| `postal_code` | `text` | da | — | — |
| `city` | `text` | ne | — | — |
| `city_key` | `text` | ne | — | — |
| `city_aliases` | `text[]` | ne | — | '{}'::text[] |
| `county` | `text` | da | — | — |
| `district` | `text` | da | — | — |
| `longitude` | `double precision` | da | — | — |
| `latitude` | `double precision` | da | — | — |
| `position` | `geography(Point,4326)` | da | — | GENERATED: (st_setsrid(st_makepoint(longitude, latitude), 4326))::geography |
| `attributes` | `jsonb` | ne | — | '{}'::jsonb |
| `provenance` | `jsonb` | ne | — | '{}'::jsonb |

Ograničenja:

- `location_attributes_check`: `CHECK ((jsonb_typeof(attributes) = 'object'::text))`
- `location_check`: `CHECK (((longitude IS NULL) = (latitude IS NULL)))`
- `location_kind_check`: `CHECK ((kind = ANY (ARRAY['main'::text, 'branch'::text, 'unknown'::text])))`
- `location_latitude_check`: `CHECK (((latitude >= ('-90'::integer)::double precision) AND (latitude <= (90)::double precision)))`
- `location_longitude_check`: `CHECK (((longitude >= ('-180'::integer)::double precision) AND (longitude <= (180)::double precision)))`
- `location_provenance_check`: `CHECK ((jsonb_typeof(provenance) = 'object'::text))`
- `location_kindergarten_id_fkey`: `FOREIGN KEY (kindergarten_id) REFERENCES kindergarten(id)`
- `location_pkey`: `PRIMARY KEY (id)`
- `location_id_kindergarten_id_key`: `UNIQUE (id, kindergarten_id)`

Indeksi:

- `ix_location_city`: `CREATE INDEX ix_location_city ON public.location USING btree (city_key)`
- `ix_location_owner`: `CREATE INDEX ix_location_owner ON public.location USING btree (kindergarten_id)`
- `ix_location_position`: `CREATE INDEX ix_location_position ON public.location USING gist ("position")`
- `location_id_kindergarten_id_key`: `CREATE UNIQUE INDEX location_id_kindergarten_id_key ON public.location USING btree (id, kindergarten_id)`
- `location_pkey`: `CREATE UNIQUE INDEX location_pkey ON public.location USING btree (id)`

### `program`

| Stupac | PostgreSQL tip | NULL | Ključ | Zadano / generirano |
|---|---|---|---|---|
| `id` | `uuid` | ne | PK, UQ | gen_random_uuid() |
| `kindergarten_id` | `uuid` | ne | FK, UQ | — |
| `location_id` | `uuid` | da | FK | — |
| `source_record_id` | `uuid` | ne | FK | — |
| `name` | `text` | ne | — | — |
| `min_age_months` | `smallint` | da | — | — |
| `max_age_months_exclusive` | `smallint` | da | — | — |
| `verified_on` | `date` | ne | — | — |
| `valid_until` | `date` | da | — | — |
| `languages` | `text[]` | ne | — | '{}'::text[] |

Ograničenja:

- `program_check`: `CHECK (((max_age_months_exclusive IS NULL) OR (min_age_months IS NULL) OR (max_age_months_exclusive > min_age_months)))`
- `program_check1`: `CHECK (((valid_until IS NULL) OR (valid_until >= verified_on)))`
- `program_max_age_months_exclusive_check`: `CHECK ((max_age_months_exclusive > 0))`
- `program_min_age_months_check`: `CHECK ((min_age_months >= 0))`
- `program_kindergarten_id_fkey`: `FOREIGN KEY (kindergarten_id) REFERENCES kindergarten(id)`
- `program_location_id_kindergarten_id_fkey`: `FOREIGN KEY (location_id, kindergarten_id) REFERENCES location(id, kindergarten_id)`
- `program_source_record_id_fkey`: `FOREIGN KEY (source_record_id) REFERENCES source_record(id)`
- `program_pkey`: `PRIMARY KEY (id)`
- `program_id_kindergarten_id_key`: `UNIQUE (id, kindergarten_id)`

Indeksi:

- `ix_program_owner`: `CREATE INDEX ix_program_owner ON public.program USING btree (kindergarten_id, location_id)`
- `ix_program_source`: `CREATE INDEX ix_program_source ON public.program USING btree (source_record_id)`
- `program_id_kindergarten_id_key`: `CREATE UNIQUE INDEX program_id_kindergarten_id_key ON public.program USING btree (id, kindergarten_id)`
- `program_pkey`: `CREATE UNIQUE INDEX program_pkey ON public.program USING btree (id)`

## Mjesta i upisi

### `availability`

| Stupac | PostgreSQL tip | NULL | Ključ | Zadano / generirano |
|---|---|---|---|---|
| `id` | `uuid` | ne | PK | gen_random_uuid() |
| `kindergarten_id` | `uuid` | ne | FK | — |
| `location_id` | `uuid` | da | FK | — |
| `source_record_id` | `uuid` | ne | FK | — |
| `age_label` | `text` | da | — | — |
| `program_label` | `text` | da | — | — |
| `free_places` | `integer` | da | — | — |
| `observed_on` | `date` | da | — | — |

Ograničenja:

- `availability_free_places_check`: `CHECK ((free_places >= 0))`
- `availability_kindergarten_id_fkey`: `FOREIGN KEY (kindergarten_id) REFERENCES kindergarten(id)`
- `availability_location_id_kindergarten_id_fkey`: `FOREIGN KEY (location_id, kindergarten_id) REFERENCES location(id, kindergarten_id)`
- `availability_source_record_id_fkey`: `FOREIGN KEY (source_record_id) REFERENCES source_record(id)`
- `availability_pkey`: `PRIMARY KEY (id)`

Indeksi:

- `availability_pkey`: `CREATE UNIQUE INDEX availability_pkey ON public.availability USING btree (id)`
- `ix_availability_owner`: `CREATE INDEX ix_availability_owner ON public.availability USING btree (kindergarten_id, location_id)`
- `ix_availability_source`: `CREATE INDEX ix_availability_source ON public.availability USING btree (source_record_id)`

### `enrolment`

| Stupac | PostgreSQL tip | NULL | Ključ | Zadano / generirano |
|---|---|---|---|---|
| `id` | `uuid` | ne | PK | gen_random_uuid() |
| `kindergarten_id` | `uuid` | ne | FK | — |
| `source_record_id` | `uuid` | ne | FK | — |
| `academic_year` | `text` | ne | — | — |
| `application_url` | `text` | ne | — | — |
| `opens_at` | `timestamp with time zone` | da | — | — |
| `closes_at` | `timestamp with time zone` | da | — | — |
| `steps` | `jsonb` | ne | — | '[]'::jsonb |
| `documents` | `jsonb` | ne | — | '[]'::jsonb |

Ograničenja:

- `enrolment_check`: `CHECK (((closes_at IS NULL) OR (opens_at IS NULL) OR (closes_at >= opens_at)))`
- `enrolment_documents_check`: `CHECK ((jsonb_typeof(documents) = 'array'::text))`
- `enrolment_steps_check`: `CHECK ((jsonb_typeof(steps) = 'array'::text))`
- `enrolment_kindergarten_id_fkey`: `FOREIGN KEY (kindergarten_id) REFERENCES kindergarten(id)`
- `enrolment_source_record_id_fkey`: `FOREIGN KEY (source_record_id) REFERENCES source_record(id)`
- `enrolment_pkey`: `PRIMARY KEY (id)`

Indeksi:

- `enrolment_pkey`: `CREATE UNIQUE INDEX enrolment_pkey ON public.enrolment USING btree (id)`
- `ix_enrolment_owner`: `CREATE INDEX ix_enrolment_owner ON public.enrolment USING btree (kindergarten_id)`
- `ix_enrolment_source`: `CREATE INDEX ix_enrolment_source ON public.enrolment USING btree (source_record_id)`

## RAG

### `knowledge_chunk`

| Stupac | PostgreSQL tip | NULL | Ključ | Zadano / generirano |
|---|---|---|---|---|
| `id` | `uuid` | ne | PK | gen_random_uuid() |
| `kindergarten_id` | `uuid` | ne | FK | — |
| `location_id` | `uuid` | da | FK | — |
| `program_id` | `uuid` | da | FK | — |
| `source_record_id` | `uuid` | ne | FK, UQ | — |
| `ordinal` | `integer` | ne | UQ | — |
| `content` | `text` | ne | — | — |
| `source_url` | `text` | ne | — | — |
| `content_sha256` | `text` | ne | — | — |
| `embedding` | `vector(384)` | da | — | — |
| `embedding_model` | `text` | da | — | — |
| `search_text` | `tsvector` | da | — | GENERATED: to_tsvector('simple'::regconfig, content) |

Ograničenja:

- `knowledge_chunk_check`: `CHECK (((embedding IS NULL) = (embedding_model IS NULL)))`
- `knowledge_chunk_content_check`: `CHECK ((btrim(content) <> ''::text))`
- `knowledge_chunk_content_sha256_check`: `CHECK ((content_sha256 ~ '^[0-9a-f]{64}$'::text))`
- `knowledge_chunk_embedding_check`: `CHECK (((embedding IS NULL) OR (vector_norm(embedding) > (0)::double precision)))`
- `knowledge_chunk_ordinal_check`: `CHECK ((ordinal >= 0))`
- `knowledge_chunk_kindergarten_id_fkey`: `FOREIGN KEY (kindergarten_id) REFERENCES kindergarten(id)`
- `knowledge_chunk_location_id_kindergarten_id_fkey`: `FOREIGN KEY (location_id, kindergarten_id) REFERENCES location(id, kindergarten_id)`
- `knowledge_chunk_program_id_kindergarten_id_fkey`: `FOREIGN KEY (program_id, kindergarten_id) REFERENCES program(id, kindergarten_id)`
- `knowledge_chunk_source_record_id_fkey`: `FOREIGN KEY (source_record_id) REFERENCES source_record(id)`
- `knowledge_chunk_pkey`: `PRIMARY KEY (id)`
- `knowledge_chunk_source_record_id_ordinal_key`: `UNIQUE (source_record_id, ordinal)`

Indeksi:

- `ix_chunk_lexical`: `CREATE INDEX ix_chunk_lexical ON public.knowledge_chunk USING gin (search_text)`
- `ix_chunk_scope`: `CREATE INDEX ix_chunk_scope ON public.knowledge_chunk USING btree (kindergarten_id, location_id)`
- `knowledge_chunk_pkey`: `CREATE UNIQUE INDEX knowledge_chunk_pkey ON public.knowledge_chunk USING btree (id)`
- `knowledge_chunk_source_record_id_ordinal_key`: `CREATE UNIQUE INDEX knowledge_chunk_source_record_id_ordinal_key ON public.knowledge_chunk USING btree (source_record_id, ordinal)`

## Pogledi
