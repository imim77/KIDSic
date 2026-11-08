ALTER VIEW valid_knowledge_chunk RENAME COLUMN na_snazi TO in_effect;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN datum_objave TO published_on;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN obuhvat_dokumenta TO document_scope;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN licenca TO license;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN naslov_izvora TO source_title;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN dohvaceno_u TO fetched_at;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN datum_opazanja TO observed_on;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN id_izvornog_zapisa TO source_record_id;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN poveznica_izvora TO source_url;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN sadrzaj TO content;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN id_objekta TO location_id;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN id_vrtica TO kindergarten_id;
-- statement
ALTER VIEW kindergarten_seat_geography RENAME COLUMN id_izvornog_zapisa TO source_record_id;
-- statement
ALTER VIEW kindergarten_seat_geography RENAME COLUMN geografsko_naselje TO geo_settlement;
-- statement
ALTER VIEW kindergarten_seat_geography RENAME COLUMN susjedstvo TO neighbourhood;
-- statement
ALTER VIEW kindergarten_seat_geography RENAME COLUMN predio TO suburb;
-- statement
ALTER VIEW kindergarten_seat_geography RENAME COLUMN gradska_cetvrt_geografije TO quarter;
-- statement
ALTER VIEW kindergarten_seat_geography RENAME COLUMN geografska_sirina TO latitude;
-- statement
ALTER VIEW kindergarten_seat_geography RENAME COLUMN geografska_duzina TO longitude;
-- statement
ALTER VIEW kindergarten_seat_geography RENAME COLUMN id_vrtica TO kindergarten_id;
-- statement
ALTER VIEW document_applicability RENAME COLUMN id_vrtica TO kindergarten_id;
-- statement
ALTER VIEW document_applicability RENAME COLUMN id_izvornog_zapisa TO source_record_id;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN slobodna_mjesta TO vacancies;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN programi TO programs;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN dohvaceno_u TO fetched_at;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN vrsta_datuma TO date_kind;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN referentni_datum TO reference_date;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN status_povezivanja TO match_status;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN obuhvat TO scope;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN id_objekta TO location_id;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN id_vrtica TO kindergarten_id;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN izvorni_podaci TO raw_data;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN kljuc_izvornog_zapisa TO source_key;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN id_izvora TO source_id;
-- statement
ALTER TABLE odlomci_znanja RENAME COLUMN poveznica_izvora TO source_url;
-- statement
ALTER TABLE odlomci_znanja RENAME COLUMN sadrzaj TO content;
-- statement
ALTER TABLE odlomci_znanja RENAME COLUMN redni_broj TO ordinal;
-- statement
ALTER TABLE odlomci_znanja RENAME COLUMN id_izvornog_zapisa TO source_record_id;
-- statement
ALTER TABLE odlomci_znanja RENAME COLUMN id_objekta TO location_id;
-- statement
ALTER TABLE odlomci_znanja RENAME COLUMN id_vrtica TO kindergarten_id;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN izvori TO sources;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN pravila TO rules;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN vrijedi_do TO valid_until;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN vrijedi_od TO valid_from;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN datum_provjere TO verified_on;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN status_provjere TO verification_status;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN sazetak TO summary;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN naslov TO title;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN vrste_pruzatelja TO provider_kinds;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN id_jedinice_lokalne_samouprave TO municipality_id;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN kljuc_pravila TO policy_key;
-- statement
ALTER TABLE neprihvacanja_upisa RENAME COLUMN id_izvornog_zapisa TO source_record_id;
-- statement
ALTER TABLE neprihvacanja_upisa RENAME COLUMN id_vrtica TO kindergarten_id;
-- statement
ALTER TABLE neprihvacanja_upisa RENAME COLUMN id_upisnog_kruga TO enrolment_id;
-- statement
ALTER TABLE upisni_krugovi RENAME COLUMN upisni_krug TO round;
-- statement
ALTER TABLE upisni_krugovi RENAME COLUMN kanal_prijave TO channel;
-- statement
ALTER TABLE upisni_krugovi RENAME COLUMN zavrsetak_prijava TO closes_at;
-- statement
ALTER TABLE upisni_krugovi RENAME COLUMN pocetak_prijava TO opens_at;
-- statement
ALTER TABLE upisni_krugovi RENAME COLUMN poveznica_za_prijavu TO application_url;
-- statement
ALTER TABLE upisni_krugovi RENAME COLUMN pedagoska_godina TO academic_year;
-- statement
ALTER TABLE upisni_krugovi RENAME COLUMN id_izvornog_zapisa TO source_record_id;
-- statement
ALTER TABLE upisni_krugovi RENAME COLUMN id_vrtica TO kindergarten_id;
-- statement
ALTER TABLE obuhvati_dokumenata RENAME COLUMN id_vrtica TO kindergarten_id;
-- statement
ALTER TABLE obuhvati_dokumenata RENAME COLUMN vrste_pruzatelja TO provider_kinds;
-- statement
ALTER TABLE obuhvati_dokumenata RENAME COLUMN id_jedinice_lokalne_samouprave TO municipality_id;
-- statement
ALTER TABLE obuhvati_dokumenata RENAME COLUMN id_izvornog_zapisa TO source_record_id;
-- statement
ALTER TABLE zapisi_dokumenata RENAME COLUMN vrijedi_do TO valid_until;
-- statement
ALTER TABLE zapisi_dokumenata RENAME COLUMN vrsta_datuma TO date_kind;
-- statement
ALTER TABLE zapisi_dokumenata RENAME COLUMN referentni_datum TO reference_date;
-- statement
ALTER TABLE zapisi_dokumenata RENAME COLUMN id_izvornog_zapisa TO source_record_id;
-- statement
ALTER TABLE objekti RENAME COLUMN id_jedinice_lokalne_samouprave TO municipality_id;
-- statement
ALTER TABLE objekti RENAME COLUMN podrijetlo TO provenance;
-- statement
ALTER TABLE objekti RENAME COLUMN obiljezja TO attributes;
-- statement
ALTER TABLE objekti RENAME COLUMN geografska_sirina TO latitude;
-- statement
ALTER TABLE objekti RENAME COLUMN geografska_duzina TO longitude;
-- statement
ALTER TABLE objekti RENAME COLUMN gradska_cetvrt TO district;
-- statement
ALTER TABLE objekti RENAME COLUMN kljuc_naselja TO settlement_key;
-- statement
ALTER TABLE objekti RENAME COLUMN naselje TO settlement;
-- statement
ALTER TABLE objekti RENAME COLUMN postanski_broj TO postal_code;
-- statement
ALTER TABLE objekti RENAME COLUMN adresa TO address;
-- statement
ALTER TABLE objekti RENAME COLUMN vrsta TO kind;
-- statement
ALTER TABLE objekti RENAME COLUMN naziv TO name;
-- statement
ALTER TABLE objekti RENAME COLUMN id_vrtica TO kindergarten_id;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN id_zapisa_geografskog_izvora TO geography_source_record_id;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN obiljezja TO attributes;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN geografska_sirina TO latitude;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN geografska_duzina TO longitude;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN id_jedinice_lokalne_samouprave TO municipality_id;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN kljuc_naselja TO settlement_key;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN naselje TO settlement;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN postanski_broj TO postal_code;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN adresa TO address;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN id_vrtica TO kindergarten_id;
-- statement
ALTER TABLE vrtici RENAME COLUMN podrijetlo TO provenance;
-- statement
ALTER TABLE vrtici RENAME COLUMN mrezna_stranica TO website_url;
-- statement
ALTER TABLE vrtici RENAME COLUMN telefon TO phone;
-- statement
ALTER TABLE vrtici RENAME COLUMN e_posta TO email;
-- statement
ALTER TABLE vrtici RENAME COLUMN vrsta_pruzatelja TO provider_kind;
-- statement
ALTER TABLE vrtici RENAME COLUMN naziv TO name;
-- statement
ALTER TABLE jedinice_lokalne_samouprave RENAME COLUMN alternativni_nazivi TO aliases;
-- statement
ALTER TABLE jedinice_lokalne_samouprave RENAME COLUMN zupanija TO county;
-- statement
ALTER TABLE jedinice_lokalne_samouprave RENAME COLUMN naziv TO name;
-- statement
ALTER TABLE jedinice_lokalne_samouprave RENAME COLUMN kljuc TO key;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN metoda_povezivanja TO match_method;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN napomena_povezivanja TO match_note;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN status_povezivanja TO match_status;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN id_objekta TO location_id;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN id_vrtica TO kindergarten_id;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN datum_opazanja TO observed_on;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN dohvaceno_u TO fetched_at;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN izvorni_podaci TO raw_data;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN kljuc_izvornog_zapisa TO source_key;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN id_izvora TO source_id;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN vrsta TO kind;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN metapodaci TO metadata;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN datum_opazanja TO observed_on;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN dohvaceno_u TO fetched_at;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN uvoz_dopusten TO import_allowed;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN licenca TO license;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN poveznica TO url;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN izdavac TO publisher;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN naslov TO title;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN kljuc_skupa_podataka TO dataset_key;
-- statement
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

