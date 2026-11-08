SELECT pg_advisory_xact_lock(194733, 1);
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN dataset_key TO kljuc_skupa_podataka;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN title TO naslov;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN publisher TO izdavac;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN url TO poveznica;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN license TO licenca;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN import_allowed TO uvoz_dopusten;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN fetched_at TO dohvaceno_u;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN observed_on TO datum_opazanja;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN metadata TO metapodaci;
-- statement
ALTER TABLE izvori_podataka RENAME COLUMN kind TO vrsta;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN source_id TO id_izvora;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN source_key TO kljuc_izvornog_zapisa;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN raw_data TO izvorni_podaci;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN fetched_at TO dohvaceno_u;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN observed_on TO datum_opazanja;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN kindergarten_id TO id_vrtica;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN location_id TO id_objekta;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN match_status TO status_povezivanja;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN match_note TO napomena_povezivanja;
-- statement
ALTER TABLE izvorni_zapisi RENAME COLUMN match_method TO metoda_povezivanja;
-- statement
ALTER TABLE jedinice_lokalne_samouprave RENAME COLUMN key TO kljuc;
-- statement
ALTER TABLE jedinice_lokalne_samouprave RENAME COLUMN name TO naziv;
-- statement
ALTER TABLE jedinice_lokalne_samouprave RENAME COLUMN county TO zupanija;
-- statement
ALTER TABLE jedinice_lokalne_samouprave RENAME COLUMN aliases TO alternativni_nazivi;
-- statement
ALTER TABLE vrtici RENAME COLUMN name TO naziv;
-- statement
ALTER TABLE vrtici RENAME COLUMN provider_kind TO vrsta_pruzatelja;
-- statement
ALTER TABLE vrtici RENAME COLUMN email TO e_posta;
-- statement
ALTER TABLE vrtici RENAME COLUMN phone TO telefon;
-- statement
ALTER TABLE vrtici RENAME COLUMN website_url TO mrezna_stranica;
-- statement
ALTER TABLE vrtici RENAME COLUMN provenance TO podrijetlo;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN kindergarten_id TO id_vrtica;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN address TO adresa;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN postal_code TO postanski_broj;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN settlement TO naselje;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN settlement_key TO kljuc_naselja;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN municipality_id TO id_jedinice_lokalne_samouprave;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN longitude TO geografska_duzina;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN latitude TO geografska_sirina;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN attributes TO obiljezja;
-- statement
ALTER TABLE sjedista_vrtica RENAME COLUMN geography_source_record_id TO id_zapisa_geografskog_izvora;
-- statement
ALTER TABLE objekti RENAME COLUMN kindergarten_id TO id_vrtica;
-- statement
ALTER TABLE objekti RENAME COLUMN name TO naziv;
-- statement
ALTER TABLE objekti RENAME COLUMN kind TO vrsta;
-- statement
ALTER TABLE objekti RENAME COLUMN address TO adresa;
-- statement
ALTER TABLE objekti RENAME COLUMN postal_code TO postanski_broj;
-- statement
ALTER TABLE objekti RENAME COLUMN settlement TO naselje;
-- statement
ALTER TABLE objekti RENAME COLUMN settlement_key TO kljuc_naselja;
-- statement
ALTER TABLE objekti RENAME COLUMN district TO gradska_cetvrt;
-- statement
ALTER TABLE objekti RENAME COLUMN longitude TO geografska_duzina;
-- statement
ALTER TABLE objekti RENAME COLUMN latitude TO geografska_sirina;
-- statement
ALTER TABLE objekti RENAME COLUMN attributes TO obiljezja;
-- statement
ALTER TABLE objekti RENAME COLUMN provenance TO podrijetlo;
-- statement
ALTER TABLE objekti RENAME COLUMN municipality_id TO id_jedinice_lokalne_samouprave;
-- statement
ALTER TABLE zapisi_dokumenata RENAME COLUMN source_record_id TO id_izvornog_zapisa;
-- statement
ALTER TABLE zapisi_dokumenata RENAME COLUMN reference_date TO referentni_datum;
-- statement
ALTER TABLE zapisi_dokumenata RENAME COLUMN date_kind TO vrsta_datuma;
-- statement
ALTER TABLE zapisi_dokumenata RENAME COLUMN valid_until TO vrijedi_do;
-- statement
ALTER TABLE obuhvati_dokumenata RENAME COLUMN source_record_id TO id_izvornog_zapisa;
-- statement
ALTER TABLE obuhvati_dokumenata RENAME COLUMN municipality_id TO id_jedinice_lokalne_samouprave;
-- statement
ALTER TABLE obuhvati_dokumenata RENAME COLUMN provider_kinds TO vrste_pruzatelja;
-- statement
ALTER TABLE obuhvati_dokumenata RENAME COLUMN kindergarten_id TO id_vrtica;
-- statement
ALTER TABLE upisni_krugovi RENAME COLUMN kindergarten_id TO id_vrtica;
-- statement
ALTER TABLE upisni_krugovi RENAME COLUMN source_record_id TO id_izvornog_zapisa;
-- statement
ALTER TABLE upisni_krugovi RENAME COLUMN academic_year TO pedagoska_godina;
-- statement
ALTER TABLE upisni_krugovi RENAME COLUMN application_url TO poveznica_za_prijavu;
-- statement
ALTER TABLE upisni_krugovi RENAME COLUMN opens_at TO pocetak_prijava;
-- statement
ALTER TABLE upisni_krugovi RENAME COLUMN closes_at TO zavrsetak_prijava;
-- statement
ALTER TABLE upisni_krugovi RENAME COLUMN channel TO kanal_prijave;
-- statement
ALTER TABLE upisni_krugovi RENAME COLUMN round TO upisni_krug;
-- statement
ALTER TABLE neprihvacanja_upisa RENAME COLUMN enrolment_id TO id_upisnog_kruga;
-- statement
ALTER TABLE neprihvacanja_upisa RENAME COLUMN kindergarten_id TO id_vrtica;
-- statement
ALTER TABLE neprihvacanja_upisa RENAME COLUMN source_record_id TO id_izvornog_zapisa;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN policy_key TO kljuc_pravila;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN municipality_id TO id_jedinice_lokalne_samouprave;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN provider_kinds TO vrste_pruzatelja;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN title TO naslov;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN summary TO sazetak;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN verification_status TO status_provjere;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN verified_on TO datum_provjere;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN valid_from TO vrijedi_od;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN valid_until TO vrijedi_do;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN rules TO pravila;
-- statement
ALTER TABLE pravila_sufinanciranja RENAME COLUMN sources TO izvori;
-- statement
ALTER TABLE odlomci_znanja RENAME COLUMN kindergarten_id TO id_vrtica;
-- statement
ALTER TABLE odlomci_znanja RENAME COLUMN location_id TO id_objekta;
-- statement
ALTER TABLE odlomci_znanja RENAME COLUMN source_record_id TO id_izvornog_zapisa;
-- statement
ALTER TABLE odlomci_znanja RENAME COLUMN ordinal TO redni_broj;
-- statement
ALTER TABLE odlomci_znanja RENAME COLUMN content TO sadrzaj;
-- statement
ALTER TABLE odlomci_znanja RENAME COLUMN source_url TO poveznica_izvora;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN source_id TO id_izvora;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN source_key TO kljuc_izvornog_zapisa;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN raw_data TO izvorni_podaci;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN kindergarten_id TO id_vrtica;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN location_id TO id_objekta;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN scope TO obuhvat;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN match_status TO status_povezivanja;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN reference_date TO referentni_datum;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN date_kind TO vrsta_datuma;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN fetched_at TO dohvaceno_u;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN programs TO programi;
-- statement
ALTER TABLE povijesni_zapisi RENAME COLUMN vacancies TO slobodna_mjesta;
-- statement
ALTER VIEW document_applicability RENAME COLUMN source_record_id TO id_izvornog_zapisa;
-- statement
ALTER VIEW document_applicability RENAME COLUMN kindergarten_id TO id_vrtica;
-- statement
ALTER VIEW kindergarten_seat_geography RENAME COLUMN kindergarten_id TO id_vrtica;
-- statement
ALTER VIEW kindergarten_seat_geography RENAME COLUMN longitude TO geografska_duzina;
-- statement
ALTER VIEW kindergarten_seat_geography RENAME COLUMN latitude TO geografska_sirina;
-- statement
ALTER VIEW kindergarten_seat_geography RENAME COLUMN quarter TO gradska_cetvrt_geografije;
-- statement
ALTER VIEW kindergarten_seat_geography RENAME COLUMN suburb TO predio;
-- statement
ALTER VIEW kindergarten_seat_geography RENAME COLUMN neighbourhood TO susjedstvo;
-- statement
ALTER VIEW kindergarten_seat_geography RENAME COLUMN geo_settlement TO geografsko_naselje;
-- statement
ALTER VIEW kindergarten_seat_geography RENAME COLUMN source_record_id TO id_izvornog_zapisa;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN kindergarten_id TO id_vrtica;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN location_id TO id_objekta;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN content TO sadrzaj;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN source_url TO poveznica_izvora;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN source_record_id TO id_izvornog_zapisa;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN observed_on TO datum_opazanja;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN fetched_at TO dohvaceno_u;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN source_title TO naslov_izvora;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN license TO licenca;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN document_scope TO obuhvat_dokumenta;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN published_on TO datum_objave;
-- statement
ALTER VIEW valid_knowledge_chunk RENAME COLUMN in_effect TO na_snazi;
-- statement
CREATE OR REPLACE FUNCTION check_document_scope() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE record_id uuid; record_ids uuid[];
BEGIN
 IF TG_TABLE_NAME='izvorni_zapisi' THEN record_ids=ARRAY[NEW.id];
 ELSIF TG_OP='DELETE' THEN record_ids=ARRAY[OLD.id_izvornog_zapisa];
 ELSIF TG_OP='UPDATE' THEN record_ids=ARRAY[OLD.id_izvornog_zapisa,NEW.id_izvornog_zapisa];
 ELSE record_ids=ARRAY[NEW.id_izvornog_zapisa]; END IF;
 FOREACH record_id IN ARRAY record_ids LOOP
 IF EXISTS(SELECT 1 FROM izvorni_zapisi r WHERE r.id=record_id
      AND r.id_vrtica IS NULL AND r.status_povezivanja='accepted'
      AND NOT EXISTS(SELECT 1 FROM obuhvati_dokumenata d WHERE d.id_izvornog_zapisa=r.id))
    OR EXISTS(SELECT 1 FROM odlomci_znanja c WHERE c.id_izvornog_zapisa=record_id
      AND c.id_vrtica IS NULL AND NOT EXISTS(
        SELECT 1 FROM obuhvati_dokumenata d WHERE d.id_izvornog_zapisa=record_id)) THEN
   RAISE EXCEPTION 'Ownerless document % requires obuhvati_dokumenata',record_id USING ERRCODE='23514';
 END IF;
 END LOOP;
 RETURN NULL;
END $$;

