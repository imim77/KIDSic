"""AsyncpgLocationRepository reads active locations and source evidence together."""
from KIDSic.dao.interfaces.location import LocationRepository
from KIDSic.dto.location import LocationQuery
from KIDSic.dto.municipality import supported_city_key
from KIDSic.dto.text import normalize


class AsyncpgLocationRepository(LocationRepository):
    def __init__(self, connection):
        self._connection = connection

    async def list_locations(self, query: LocationQuery):
        return await self._connection.fetch("""
          WITH active_record AS (
            SELECT r.id::text AS record_id,r.id_izvora,r.id_vrtica,r.id_objekta,r.izvorni_podaci,r.dohvaceno_u,
              jsonb_build_object('name',s.naslov,'url',s.poveznica,'license',s.licenca,
                'reference_date',r.datum_opazanja,'retrieved_at',r.dohvaceno_u) AS evidence
            FROM izvorni_zapisi r JOIN izvori_podataka s ON s.id=r.id_izvora
            WHERE r.status_povezivanja='accepted' AND s.uvoz_dopusten
          ), place AS (
            SELECT l.id AS id_objekta,l.id_vrtica,l.naziv AS location_name,
              l.adresa,l.naselje,l.kljuc_naselja,l.id_jedinice_lokalne_samouprave,l.gradska_cetvrt,
              l.geografska_duzina,l.geografska_sirina,'facility' AS location_role,l.podrijetlo AS field_provenance,
              l.obiljezja->>'phone' AS facility_phone,
              jsonb_build_object('district',l.gradska_cetvrt,'quarter',l.obiljezja->>'quarter',
                'suburb',l.obiljezja->>'suburb','neighbourhood',l.obiljezja->>'neighbourhood',
                'settlement',l.naselje) AS area_values,
              (SELECT jsonb_agg(DISTINCT r.evidence ORDER BY r.evidence)
               FROM active_record r WHERE r.id_objekta=l.id) AS izvori
            FROM objekti l
            WHERE EXISTS (SELECT 1 FROM active_record r WHERE r.id_objekta=l.id)
            UNION ALL
            SELECT NULL,k.id,k.naziv,ks.adresa,ks.naselje,
              ks.kljuc_naselja,ks.id_jedinice_lokalne_samouprave,NULL,sg.geografska_duzina,sg.geografska_sirina,'seat',
              jsonb_build_object('location_name',k.podrijetlo->'name',
                'address',k.podrijetlo->'seat_address',
                'longitude',jsonb_build_object('source_record_id',sg.id_izvornog_zapisa),'latitude',jsonb_build_object('source_record_id',sg.id_izvornog_zapisa),
                'quarter',jsonb_build_object('source_record_id',sg.id_izvornog_zapisa),'suburb',jsonb_build_object('source_record_id',sg.id_izvornog_zapisa),
                'neighbourhood',jsonb_build_object('source_record_id',sg.id_izvornog_zapisa),'settlement',jsonb_build_object('source_record_id',sg.id_izvornog_zapisa)),NULL,
              jsonb_build_object('quarter',sg.gradska_cetvrt_geografije,'suburb',sg.predio,
                'neighbourhood',sg.susjedstvo,'settlement',sg.geografsko_naselje),
              (SELECT jsonb_agg(DISTINCT r.evidence ORDER BY r.evidence)
               FROM active_record r WHERE r.id_vrtica=k.id)
            FROM vrtici k LEFT JOIN sjedista_vrtica ks ON ks.id_vrtica=k.id
            LEFT JOIN kindergarten_seat_geography sg ON sg.id_vrtica=k.id
            WHERE ks.kljuc_naselja IS NOT NULL
              AND EXISTS (SELECT 1 FROM active_record r WHERE r.id_vrtica=k.id)
              -- A facility outside the requested bounds still rules out a seat.
              AND NOT EXISTS (SELECT 1 FROM objekti l JOIN active_record r
                ON r.id_objekta=l.id WHERE l.id_vrtica=k.id)
          ), candidate AS (
          SELECT pl.id_objekta,pl.id_vrtica,k.naziv,pl.location_name,
            pl.adresa,pl.naselje AS city,k.vrsta_pruzatelja,pl.gradska_cetvrt,
            COALESCE(areas.names,'[]'::jsonb) AS areas,
            COALESCE(history.records,'[]'::jsonb) AS historical_data,
            COALESCE(rounds.items,'[]'::jsonb) AS enrolment,
            COALESCE(NULLIF(btrim(contact.izvorni_podaci->>'Web'),''),NULLIF(btrim(k.mrezna_stranica),'')) AS mrezna_stranica,
            COALESCE(NULLIF(btrim(contact.izvorni_podaci->>'Email'),''),NULLIF(btrim(k.e_posta),'')) AS e_posta,
            COALESCE(NULLIF(btrim(contact.izvorni_podaci->>'Telefon'),''),NULLIF(btrim(pl.facility_phone),''),
                     NULLIF(btrim(k.telefon),'')) AS telefon,
            pl.geografska_duzina,pl.geografska_sirina,pl.location_role,pl.izvori,
            COALESCE(fields.field_sources,'{}') AS field_sources,
            jsonb_build_object(
              'website_url',CASE WHEN NULLIF(btrim(contact.izvorni_podaci->>'Web'),'') IS NOT NULL
                THEN contact.evidence || '{"scope":"facility"}'::jsonb ELSE owner_contacts.evidence->'website_url' END,
              'email',CASE WHEN NULLIF(btrim(contact.izvorni_podaci->>'Email'),'') IS NOT NULL
                THEN contact.evidence || '{"scope":"facility"}'::jsonb ELSE owner_contacts.evidence->'email' END,
              'phone',CASE WHEN NULLIF(btrim(contact.izvorni_podaci->>'Telefon'),'') IS NOT NULL
                THEN contact.evidence || '{"scope":"facility"}'::jsonb
                WHEN NULLIF(btrim(pl.facility_phone),'') IS NULL THEN owner_contacts.evidence->'phone' END
            ) AS contact_sources,
            COALESCE((SELECT jsonb_agg(jsonb_build_object('id',p.id,'policy_key',p.kljuc_pravila,'municipality_id',p.id_jedinice_lokalne_samouprave,'provider_kinds',p.vrste_pruzatelja,'title',p.naslov,'summary',p.sazetak,'verification_status',p.status_provjere,'verified_on',p.datum_provjere,'valid_from',p.vrijedi_od,'valid_until',p.vrijedi_do,'rules',p.pravila,'sources',p.izvori) ORDER BY p.vrijedi_od DESC,p.kljuc_pravila)
              FROM pravila_sufinanciranja p
              WHERE p.id_jedinice_lokalne_samouprave=pl.id_jedinice_lokalne_samouprave
                AND k.vrsta_pruzatelja=ANY(p.vrste_pruzatelja)
                AND p.datum_provjere<=CURRENT_DATE
                AND (p.vrijedi_od IS NULL OR p.vrijedi_od<=CURRENT_DATE)
                AND (p.vrijedi_do IS NULL OR p.vrijedi_do>=CURRENT_DATE)), '[]'::jsonb)
              AS subsidy_policies,
            NOT ((pl.field_provenance ? 'longitude' AND NOT
                  COALESCE(fields.field_sources ? 'longitude',false)) OR
                 (pl.field_provenance ? 'latitude' AND NOT
                  COALESCE(fields.field_sources ? 'latitude',false))) AS geometry_valid
          FROM place pl JOIN vrtici k ON k.id=pl.id_vrtica
          LEFT JOIN jedinice_lokalne_samouprave m ON m.id=pl.id_jedinice_lokalne_samouprave
          LEFT JOIN LATERAL (
            SELECT jsonb_agg(jsonb_build_object('reference_date',h.referentni_datum,
              'date_kind',h.vrsta_datuma,'scope',h.obuhvat,'programs',h.programi,'vacancies',h.slobodna_mjesta,
              'source_title',s.naslov,'source_url',COALESCE(s.metapodaci->>'resource_url',s.poveznica),
              'license',s.licenca) ORDER BY h.referentni_datum DESC,s.kljuc_skupa_podataka,h.kljuc_izvornog_zapisa) AS records
            FROM povijesni_zapisi h JOIN izvori_podataka s ON s.id=h.id_izvora
            WHERE s.uvoz_dopusten AND h.status_povezivanja='accepted'
              AND h.id_vrtica=pl.id_vrtica
              AND ((h.obuhvat='institution' AND h.id_objekta IS NULL)
                OR (h.obuhvat='facility' AND h.id_objekta=pl.id_objekta))
              AND (cardinality(h.programi)>0 OR jsonb_array_length(h.slobodna_mjesta)>0)
          ) history ON true
          -- Shared applicability enforces named owners and municipality/provider rules.
          LEFT JOIN LATERAL (
            SELECT jsonb_agg(jsonb_build_object('round',e.upisni_krug,'academic_year',e.pedagoska_godina,
              'channel',e.kanal_prijave,'application_url',e.poveznica_za_prijavu,'accepting',NOT EXISTS (
                SELECT 1 FROM neprihvacanja_upisa f JOIN active_record fr
                  ON fr.record_id=f.id_izvornog_zapisa::text
                JOIN document_applicability fa ON fa.id_izvornog_zapisa=f.id_izvornog_zapisa
                  AND fa.id_vrtica=pl.id_vrtica
                WHERE f.id_upisnog_kruga=e.id AND f.id_vrtica=pl.id_vrtica),
              'opens_at',e.pocetak_prijava,'closes_at',e.zavrsetak_prijava,
              'source_title',s.naslov,'source_url',s.poveznica,'license',s.licenca,
              'reference_date',COALESCE(d.referentni_datum::text,r.evidence->>'reference_date'),
              'date_kind',COALESCE(d.vrsta_datuma,CASE WHEN r.evidence->>'reference_date' IS NOT NULL
                THEN 'observed' ELSE 'unknown' END))
              ORDER BY e.pedagoska_godina DESC,e.upisni_krug,s.kljuc_skupa_podataka) AS items
            FROM upisni_krugovi e JOIN active_record r ON r.record_id=e.id_izvornog_zapisa::text
            LEFT JOIN zapisi_dokumenata d ON d.id_izvornog_zapisa=e.id_izvornog_zapisa
            JOIN izvori_podataka s ON s.id=r.id_izvora
            JOIN document_applicability a ON a.id_izvornog_zapisa=e.id_izvornog_zapisa
            WHERE a.id_vrtica=pl.id_vrtica
              AND (s.vrsta<>'enrolment_document' OR d.id_izvornog_zapisa IS NOT NULL)
          ) rounds ON true
          -- Area filters use current attestation; historical labels stay in district only.
          LEFT JOIN LATERAL (
            SELECT jsonb_agg(DISTINCT btrim(area.value) ORDER BY btrim(area.value)) AS names
            FROM jsonb_each_text(pl.area_values) area
            WHERE NULLIF(btrim(area.value),'') IS NOT NULL
              AND (area.key<>'settlement' OR (
                translate(lower(btrim(area.value)),'čćžšđ','cczsd')<>$1
                AND lower(btrim(area.value)) IS DISTINCT FROM lower(m.naziv)))
              AND (NOT (pl.field_provenance ? area.key) OR EXISTS (
                SELECT 1 FROM active_record r
                WHERE r.record_id=pl.field_provenance->area.key->>'source_record_id'
                  AND r.id_vrtica=pl.id_vrtica
                  AND r.id_objekta IS NOT DISTINCT FROM pl.id_objekta))
          ) areas ON true
          -- Published branch contacts take precedence over the institution fallback.
          LEFT JOIN LATERAL (
            SELECT r.izvorni_podaci,r.evidence FROM active_record r
            WHERE r.id_objekta=pl.id_objekta AND r.id_vrtica=pl.id_vrtica
              AND r.izvorni_podaci ?| ARRAY['Web','Email','Telefon']
            ORDER BY r.dohvaceno_u DESC,r.record_id LIMIT 1
          ) contact ON true
          LEFT JOIN LATERAL (
            SELECT jsonb_object_agg(field.key,r.evidence || jsonb_build_object('scope',
              CASE WHEN r.id_objekta IS NULL THEN 'institution' ELSE 'facility' END)) AS evidence
            FROM jsonb_each(k.podrijetlo) field JOIN active_record r
              ON r.record_id=field.value->>'source_record_id' AND r.id_vrtica=k.id
                AND (r.id_objekta IS NULL OR r.id_objekta=pl.id_objekta)
            WHERE field.key IN ('website_url','email','phone')
          ) owner_contacts ON true
          LEFT JOIN LATERAL (
            SELECT jsonb_object_agg(field.key,r.evidence) AS field_sources
            FROM jsonb_each(pl.field_provenance || jsonb_build_object(
              'name',k.podrijetlo->'name','provider_kind',k.podrijetlo->'provider_kind')) field
            JOIN active_record r ON r.record_id=field.value->>'source_record_id'
              AND r.id_vrtica=pl.id_vrtica
              AND (field.key IN ('name','provider_kind')
                OR (field.key='location_name' AND pl.location_role='seat')
                OR r.id_objekta IS NOT DISTINCT FROM pl.id_objekta)
            WHERE field.key IN ('name','provider_kind','location_name','address',
                                'district','quarter','suburb','neighbourhood','settlement',
                                'longitude','latitude')
          ) fields ON true
          WHERE (pl.kljuc_naselja=$1 OR m.kljuc=$1 OR $1=ANY(m.alternativni_nazivi))
            AND ($2='' OR strpos(translate(lower(k.naziv),'čćžšđ','cczsd'),$2)>0
                       OR strpos(translate(lower(pl.location_name),'čćžšđ','cczsd'),$2)>0)
            AND ($3::text IS NULL OR k.vrsta_pruzatelja=$3)
          )
          SELECT id_objekta AS location_id,id_vrtica AS kindergarten_id,naziv AS name,location_name,adresa AS address,city,
            vrsta_pruzatelja AS provider_kind,gradska_cetvrt AS district,areas,historical_data,enrolment,
            mrezna_stranica AS website_url,e_posta AS email,telefon AS phone,contact_sources,location_role,izvori AS sources,field_sources,subsidy_policies,
            CASE WHEN geometry_valid THEN geografska_duzina END AS longitude,
            CASE WHEN geometry_valid THEN geografska_sirina END AS latitude,
            CASE WHEN $6::float8[] IS NOT NULL AND geometry_valid THEN round(ST_Distance(
              ST_MakePoint(geografska_duzina,geografska_sirina)::geography,
              ST_MakePoint($6[1],$6[2])::geography))::int END AS distance_m
          FROM candidate
          WHERE ($4::float8[] IS NULL OR (
              geometry_valid AND geografska_duzina BETWEEN $4[1] AND $4[3]
              AND geografska_sirina BETWEEN $4[2] AND $4[4]))
            -- Geography measures metres on the spheroid; NULL points never match.
            AND ($6::float8[] IS NULL OR (geometry_valid AND ST_DWithin(
              ST_MakePoint(geografska_duzina,geografska_sirina)::geography,
              ST_MakePoint($6[1],$6[2])::geography,$7::float8)))
            AND ($5='' OR EXISTS (SELECT 1 FROM jsonb_array_elements_text(areas) area(naziv)
              WHERE regexp_replace(translate(lower(btrim(area.naziv)),'čćžšđ','cczsd'),
                '^mjesni odbor ','')=$5))
            -- Only the newest snapshot that publishes vacancies counts; an
            -- older positive count must not outlive a newer published zero.
            AND (NOT $8::boolean OR COALESCE((
              SELECT bool_or((v.item->>'free_places')::int>0)
              FROM (SELECT r.item FROM jsonb_array_elements(historical_data) r(item)
                    WHERE jsonb_array_length(r.item->'vacancies')>0
                    ORDER BY r.item->>'reference_date' DESC LIMIT 1) latest,
                jsonb_array_elements(latest.item->'vacancies') v(item)),false))
          -- Distance is NULL without a radius search.
          ORDER BY distance_m NULLS LAST,
            naziv,location_name,id_vrtica,id_objekta
        """, supported_city_key(query.city), normalize(query.q), query.provider_kind,
            list(query.bbox) if query.bbox is not None else None,
            normalize(query.area).removeprefix('mjesni odbor '),
            list(query.near) if query.near is not None else None, query.radius_m,
            query.has_vacancies)
