-- A city call has a fixed main round and, separately, enrolment during the
-- pedagogical year; one row per round keeps their deadlines apart.
ALTER TABLE enrolment
 ADD COLUMN round text NOT NULL DEFAULT 'main' CHECK (round IN ('main','rolling')),
 -- false records a published refusal (e.g. construction), not a missing call.
 ADD COLUMN accepting boolean NOT NULL DEFAULT true
