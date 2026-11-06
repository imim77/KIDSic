SELECT pg_advisory_xact_lock(194733, 1);
-- statement
ALTER TABLE data_source RENAME TO izvori_podataka;
-- statement
ALTER TABLE source_record RENAME TO izvorni_zapisi;
-- statement
ALTER TABLE kindergarten RENAME TO vrtici;
-- statement
ALTER TABLE kindergarten_seat RENAME TO sjedista_vrtica;
-- statement
ALTER TABLE location RENAME TO objekti;
-- statement
ALTER TABLE municipality RENAME TO jedinice_lokalne_samouprave;
-- statement
ALTER TABLE municipality_subsidy_policy RENAME TO pravila_sufinanciranja;
-- statement
ALTER TABLE enrolment RENAME TO upisni_krugovi;
-- statement
ALTER TABLE enrolment_refusal RENAME TO neprihvacanja_upisa;
-- statement
ALTER TABLE document_scope RENAME TO obuhvati_dokumenata;
-- statement
ALTER TABLE document_record RENAME TO zapisi_dokumenata;
-- statement
ALTER TABLE knowledge_chunk RENAME TO odlomci_znanja;
-- statement
ALTER TABLE historical_record RENAME TO povijesni_zapisi;
-- statement
-- Deferred checks allow the source, scope and chunks to be inserted in any order
-- within one import, but reject accepted ownerless evidence at commit.
CREATE OR REPLACE FUNCTION check_document_scope() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE record_id uuid; record_ids uuid[];
BEGIN
 IF TG_TABLE_NAME='izvorni_zapisi' THEN record_ids=ARRAY[NEW.id];
 ELSIF TG_OP='DELETE' THEN record_ids=ARRAY[OLD.source_record_id];
 ELSIF TG_OP='UPDATE' THEN record_ids=ARRAY[OLD.source_record_id,NEW.source_record_id];
 ELSE record_ids=ARRAY[NEW.source_record_id]; END IF;
 FOREACH record_id IN ARRAY record_ids LOOP
 IF EXISTS(SELECT 1 FROM izvorni_zapisi r WHERE r.id=record_id
      AND r.kindergarten_id IS NULL AND r.match_status='accepted'
      AND NOT EXISTS(SELECT 1 FROM obuhvati_dokumenata d WHERE d.source_record_id=r.id))
    OR EXISTS(SELECT 1 FROM odlomci_znanja c WHERE c.source_record_id=record_id
      AND c.kindergarten_id IS NULL AND NOT EXISTS(
        SELECT 1 FROM obuhvati_dokumenata d WHERE d.source_record_id=record_id)) THEN
   RAISE EXCEPTION 'Ownerless document % requires obuhvati_dokumenata',record_id USING ERRCODE='23514';
 END IF;
 END LOOP;
 RETURN NULL;
END $$;
