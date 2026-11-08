ALTER TABLE enrolment
 ADD COLUMN round text NOT NULL DEFAULT 'main' CHECK (round IN ('main','rolling')),
 ADD COLUMN accepting boolean NOT NULL DEFAULT true
