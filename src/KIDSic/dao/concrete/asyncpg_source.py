"""SQL persistence for CKAN registration and atomic, repeatable snapshots."""
from dataclasses import asdict
from KIDSic.dao.concrete.columns import database_column, domain_projection
from uuid import uuid4

from KIDSic.dao.interfaces.source import SourceRepository
from KIDSic.dao.concrete.source_state import SourceStateWriter
from KIDSic.dto.municipality import MUNICIPALITIES
from KIDSic.dto.source import PlannedSource, SourceSnapshot, name_key
from KIDSic.dto.text import normalize
from KIDSic.exceptions import SourceImportError


def _same_area(first: tuple, second: tuple) -> bool:
    # Areas are (settlement_key, municipality_key). Compare confirmed municipalities when both
    # are known, so "Sesvete" matches Zagreb; otherwise require the same settlement.
    if first[1] and second[1]:
        return first[1] == second[1]
    return first[0] == second[0]


class AsyncpgSourceRepository(SourceRepository):
    def __init__(self, connection):
        self._connection = connection

    async def register(self, source: PlannedSource) -> str:
        collision = await self._connection.fetchval("""
            SELECT kljuc_skupa_podataka  AS dataset_key FROM izvori_podataka WHERE kljuc_skupa_podataka<>$1 AND (
                metapodaci->>'resource_url'=$3 OR
                (metapodaci->>'ckan_base_url'=$2 AND metapodaci->>'ckan_resource_id'=$4)) LIMIT 1
        """, source.definition.key, source.definition.base_url.rstrip('/'),
            str(source.resource.url), source.resource.id)
        if collision is not None:
            raise SourceImportError(f'This CKAN resource is already registered as {collision}.')
        old = await self._connection.fetchrow(
            'SELECT id,kljuc_skupa_podataka AS dataset_key,naslov AS title,izdavac AS publisher,poveznica AS url,licenca AS license,uvoz_dopusten AS import_allowed,dohvaceno_u AS fetched_at,datum_opazanja AS observed_on,metapodaci AS metadata,vrsta AS kind FROM izvori_podataka WHERE kljuc_skupa_podataka=$1 FOR UPDATE', source.definition.key)
        values = (source.package.title, source.publisher, source.catalogue_url,
                  source.package.license_title or source.package.license_id)
        if old is None:
            await self._connection.execute("""
                INSERT INTO izvori_podataka(kljuc_skupa_podataka,naslov,izdavac,poveznica,licenca,uvoz_dopusten,metapodaci)
                VALUES ($1,$2,$3,$4,$5,true,$6)
            """, source.definition.key, *values, source.metadata)
            return 'added'
        unchanged = tuple(old[field] for field in ('title', 'publisher', 'url', 'license')) == values
        unchanged = unchanged and all(old['metadata'].get(k) == v for k, v in source.metadata.items())
        if unchanged:
            return 'unchanged'
        await self._connection.execute("""
            UPDATE izvori_podataka SET naslov=$2,izdavac=$3,poveznica=$4,licenca=$5,metapodaci=metapodaci || $6
            WHERE kljuc_skupa_podataka=$1
        """, source.definition.key, *values, source.metadata)
        return 'updated'

    async def import_snapshot(self, snapshot: SourceSnapshot, *, allow_removals: bool = False) -> dict:
        SourceStateWriter.validate(row.source_key for row in snapshot.rows)
        async with self._connection.transaction():
            await self._connection.execute('SELECT pg_advisory_xact_lock(194733, 1)')
            if not allow_removals:
                # A valid file can still be partial; compare identities rather
                # than counts, before touching metadata or canonical fields.
                missing = await self._connection.fetch("""
                    SELECT r.kljuc_izvornog_zapisa  AS source_key FROM izvorni_zapisi r
                    JOIN izvori_podataka s ON s.id=r.id_izvora
                    WHERE s.kljuc_skupa_podataka=$1 AND NOT(r.kljuc_izvornog_zapisa=ANY($2::text[]))
                    ORDER BY r.kljuc_izvornog_zapisa
                """, snapshot.source.definition.key, [row.source_key for row in snapshot.rows])
                if missing:
                    sample = ', '.join(repr(row['source_key']) for row in missing[:10])
                    raise SourceImportError(
                        f'{snapshot.source.definition.key}: {len(missing)} previous source keys are missing '
                        f'({sample}). Verify the complete resource before retrying with '
                        '--allow-removals (allow_removals=True).')
            return await self._import_snapshot(snapshot)

    async def _import_snapshot(self, snapshot):
        if any(row.municipality not in MUNICIPALITIES for row in snapshot.rows):
            raise SourceImportError('Import supports only Zagreb, Varaždin, Rijeka and Šibenik.')
        source = snapshot.source
        registered = await self.register(source)
        stored = await self._connection.fetchrow(
            'SELECT id,uvoz_dopusten  AS import_allowed FROM izvori_podataka WHERE kljuc_skupa_podataka=$1', source.definition.key)
        if not stored['import_allowed']:
            raise SourceImportError(f'Import is disabled for {source.definition.key}.')
        source_id = stored['id']
        self._state = SourceStateWriter(self._connection, source_id, snapshot.fetched_at)
        self._municipalities = {}
        previous = {r['source_key']: r for r in await self._connection.fetch("""
            SELECT id,id_izvora AS source_id,kljuc_izvornog_zapisa AS source_key,izvorni_podaci AS raw_data,dohvaceno_u AS fetched_at,datum_opazanja AS observed_on,id_vrtica AS kindergarten_id,id_objekta AS location_id,status_povezivanja AS match_status,napomena_povezivanja AS match_note,metoda_povezivanja AS match_method FROM izvorni_zapisi WHERE id_izvora=$1
        """, source_id)}
        owners = {r['id']: {**dict(r), 'name_key': name_key(r['name']), 'areas': set()}
                  for r in await self._connection.fetch("""
            SELECT k.id,k.naziv AS name,k.vrsta_pruzatelja AS provider_kind,k.oib,ks.kljuc_naselja AS seat_settlement_key,m.kljuc AS municipality
            FROM vrtici k LEFT JOIN sjedista_vrtica ks ON ks.id_vrtica=k.id
            LEFT JOIN jedinice_lokalne_samouprave m ON m.id=ks.id_jedinice_lokalne_samouprave
        """)}
        for item in owners.values():
            if item['seat_settlement_key']:
                item['areas'].add((item['seat_settlement_key'], item['municipality']))
        locations = [dict(r) for r in await self._connection.fetch("""
            SELECT l.id,l.id_vrtica AS kindergarten_id,l.kljuc_naselja AS settlement_key,l.adresa AS address,m.kljuc AS municipality
            FROM objekti l LEFT JOIN jedinice_lokalne_samouprave m ON m.id=l.id_jedinice_lokalne_samouprave
            WHERE l.id_vrtica IS NOT NULL
        """)]
        for item in locations:
            item['area'] = (item['settlement_key'], item['municipality'])
            item['address_key'] = name_key(item['address'] or '')
            owners[item['kindergarten_id']]['areas'].add(item['area'])
        claimed = set()  # owners whose seat this snapshot already supplied
        counts = {'records': len(snapshot.rows), 'accepted': 0, 'needs_review': 0,
                  'kindergartens_added': 0, 'locations_added': 0}
        for row in snapshot.rows:
            # Resolve by prior source identity, then OIB, then exact normalized name within the
            # same municipality/settlement (plus address for objects). Multiple owners remain
            # review candidates; an institution row never creates an object.
            institution = row.scope == 'institution'
            settlement_key = normalize(row.settlement)
            area = (settlement_key, row.municipality)
            row_name, row_address = name_key(row.name), name_key(row.address)
            by_oib = [o['id'] for o in owners.values() if row.oib and o['oib'] == row.oib]
            compatible = [o['id'] for o in owners.values() if o['name_key'] == row_name
                          and any(_same_area(area, other) for other in o['areas'])
                          and (o['oib'] is None or row.oib is None or o['oib'] == row.oib)
                          and (o['provider_kind'] in {'unknown', row.provider_kind}
                               or row.provider_kind == 'unknown')]
            same_address = [l for l in locations
                            if l['address_key'] == row_address and _same_area(l['area'], area)]
            exact = [l for l in same_address if l['kindergarten_id'] in compatible]
            prior = previous.get(row.source_key)
            location = None
            if prior is not None and prior['match_status'] == 'rejected':
                await self._record(row)
                counts['needs_review'] += 1
                continue
            if prior is not None and prior['match_status'] == 'accepted':
                owner, method = prior['kindergarten_id'], 'source_identity'
                location = None if institution else prior['location_id']
            elif by_oib:
                owner, method = by_oib[0], 'oib'
                matches = [l['id'] for l in same_address if l['kindergarten_id'] == owner]
                location = matches[0] if not institution and len(matches) == 1 else None
            elif not institution and len(exact) == 1:
                owner, location, method = exact[0]['kindergarten_id'], exact[0]['id'], 'name_address'
            elif ((not institution and len(exact) > 1) or len(compatible) > 1
                  or (institution and set(compatible) & claimed)):
                await self._record(row,
                                   note='Ambiguous normalized name/address; manual review required.')
                counts['needs_review'] += 1
                continue
            else:
                owner = next(iter(compatible), None)
                method = 'name' if owner else 'new'
            record_id = prior['id'] if prior is not None else uuid4()
            evidence = {'dataset_key': source.definition.key, 'source_record_id': str(record_id)}
            if owner is None:
                owner = await self._connection.fetchval("""
                    INSERT INTO vrtici(naziv,vrsta_pruzatelja,podrijetlo)
                    VALUES ($1,$2,$3) RETURNING id
                """, row.name, row.provider_kind, {'name': evidence, 'provider_kind': evidence})
                owners[owner] = {'id': owner, 'oib': None, 'areas': set()}
                counts['kindergartens_added'] += 1
            owner_provenance = {key: evidence for key in ('email', 'phone', 'website_url', 'oib')
                                if getattr(row, key) is not None}
            if row.provider_kind != 'unknown':
                owner_provenance['provider_kind'] = evidence
                if row.provider_kind_source_url:
                    owner_provenance['provider_kind'] = {
                        **evidence, 'source_url': row.provider_kind_source_url}
            existing = await self._connection.fetchrow('SELECT id,naziv AS name,vrsta_pruzatelja AS provider_kind,e_posta AS email,telefon AS phone,mrezna_stranica AS website_url,podrijetlo AS provenance,oib FROM vrtici WHERE id=$1', owner)
            proof = existing['provenance'].get('provider_kind', {})
            # A stable ID cannot preserve a classification after its source
            # stops attesting it; only another active source can do that.
            if (row.provider_kind == 'unknown' and existing['provider_kind'] != 'unknown'
                    and not await self._active_proof(proof, owner, source_id)):
                raise SourceImportError(f'Review provider_kind before replacing evidence: {existing["name"]}.')
            values = {key: getattr(row, key) for key in ('email', 'phone', 'website_url', 'oib')}
            if row.provider_kind != 'unknown':
                values['provider_kind'] = row.provider_kind
            name_proof = existing['provenance'].get('name', {})
            replace_name = not await self._active_proof(name_proof, owner, source_id)
            if replace_name:
                values['name'] = row.name
                owner_provenance['name'] = evidence
            await self._write_fields('vrtici', owner, values, owner_provenance,
                                     source.definition.key, replace_fields=('name',) if replace_name else ())
            owner_values = await self._connection.fetchrow(
                'SELECT naziv AS name,vrsta_pruzatelja AS provider_kind,oib FROM vrtici WHERE id=$1', owner)
            owners[owner].update(owner_values, name_key=name_key(owner_values['name']))
            municipality_id = await self._municipality_id(row.municipality)
            data = asdict(row)
            if institution:
                await self._connection.execute("""INSERT INTO sjedista_vrtica(id_vrtica)
                    VALUES ($1) ON CONFLICT(id_vrtica) DO NOTHING""", owner)
                seat_values = {key: data[key] for key in ('address', 'postal_code', 'settlement')}
                seat_values.update(settlement_key=settlement_key, municipality_id=municipality_id)
                await self._write_fields('sjedista_vrtica', owner, seat_values,
                    {f'seat_{key}': evidence for key, value in seat_values.items() if value is not None},
                    source.definition.key)
                owners[owner]['areas'].add(area)
                claimed.add(owner)
            else:
                location_provenance = {key: evidence for key in ('location_name', 'settlement',
                    'address', 'postal_code', 'district', 'longitude', 'latitude')
                    if data[key] is not None}
                if row.kind != 'unknown':
                    location_provenance['kind'] = evidence
                if location is None:
                    location = await self._connection.fetchval("""
                        INSERT INTO objekti(id_vrtica,naziv,naselje,kljuc_naselja,adresa)
                        VALUES ($1,$2,$3,$4,$5) RETURNING id
                    """, owner, row.location_name, row.settlement, settlement_key, row.address)
                    counts['locations_added'] += 1
                    locations.append({'id': location, 'kindergarten_id': owner})
                # Reviewed address geography cannot follow a moved facility.
                # Demotion also removes its area/RAG evidence from active reads.
                await self._connection.execute("""
                    UPDATE izvorni_zapisi SET status_povezivanja='candidate',
                        napomena_povezivanja='Address changed; geography requires another review.'
                    WHERE id_objekta=$1 AND status_povezivanja='accepted'
                      AND izvorni_podaci ? 'reviewed_address'
                      AND izvorni_podaci->>'reviewed_address' IS DISTINCT FROM $2
                """, location, row.address)
                location_values = {key: data[key] for key in
                                   ('settlement', 'address', 'postal_code', 'district', 'longitude', 'latitude')}
                location_values.update(name=row.location_name, settlement_key=settlement_key,
                                       municipality_id=municipality_id, kind=row.kind)
                await self._write_fields('objekti', location, location_values,
                    {**location_provenance, 'name': evidence}, source.definition.key)
                # Keep the in-memory index current for subsequent rows in this import.
                for item in locations:
                    if item['id'] == location:
                        item.update(area=area, address_key=row_address)
                owners[owner]['areas'].add(area)
            await self._record(row, owner=owner,
                               location=location, record_id=record_id, method=method)
            counts['accepted'] += 1
        if not counts['accepted']:
            raise SourceImportError('No accepted records; refusing to activate the snapshot.')
        await self._state.finish()
        # Fetch time and resource modification are not the observed date of the data.
        return {'source': source.definition.key, 'registration': registered, **counts}

    async def _municipality_id(self, key):
        if key is None:
            return None
        if key not in self._municipalities:
            item = MUNICIPALITIES[key]
            self._municipalities[key] = await self._connection.fetchval("""
                INSERT INTO jedinice_lokalne_samouprave(kljuc,naziv,zupanija,alternativni_nazivi) VALUES ($1,$2,$3,$4)
                ON CONFLICT (kljuc) DO UPDATE SET naziv=EXCLUDED.naziv,zupanija=EXCLUDED.zupanija,
                    alternativni_nazivi=EXCLUDED.alternativni_nazivi RETURNING id
            """, item.key, item.name, item.county, list(item.aliases))
        return self._municipalities[key]

    async def _record(self, row, *, owner=None, location=None,
                      record_id=None, method=None, note=None):
        return await self._state.record(row.source_key, row.raw_data, owner=owner,
            location=location, status='accepted' if owner else 'candidate', method=method,
            note=note, record_id=record_id)

    async def _active_proof(self, proof, owner, excluding_source):
        return await self._connection.fetchval("""SELECT EXISTS (
            SELECT 1 FROM izvorni_zapisi r JOIN izvori_podataka s ON s.id=r.id_izvora
            WHERE r.id::text=$1 AND r.id_vrtica=$2 AND r.id_izvora<>$3
              AND r.status_povezivanja='accepted' AND s.uvoz_dopusten)
        """, proof.get('source_record_id'), owner, excluding_source)

    async def _write_fields(self, table, identity, values, evidence, dataset, *, replace_fields=()):
        seat = table == 'sjedista_vrtica'
        identity_column = 'id_vrtica' if seat else 'id'
        stored = await self._connection.fetchrow(
            f'SELECT {domain_projection(table, qualifier=table)},k.podrijetlo AS provenance '
            'FROM sjedista_vrtica JOIN vrtici k ON k.id=sjedista_vrtica.id_vrtica '
            'WHERE k.id=$1' if seat else
            f'SELECT {domain_projection(table)} FROM {table} WHERE id=$1', identity)
        provenance = dict(stored['provenance'])
        updates = {}
        for field, value in values.items():
            proof_key = (f'seat_{field}' if seat else
                         'location_name' if table == 'objekti' and field == 'name' else field)
            old = provenance.get(proof_key, {})
            owned = old.get('dataset_key') == dataset or await self._connection.fetchval(
                'SELECT EXISTS(SELECT 1 FROM izvorni_zapisi r JOIN izvori_podataka s ON s.id=r.id_izvora WHERE r.id::text=$1 AND s.kljuc_skupa_podataka=$2)', old.get('source_record_id'), dataset)
            if (old and not owned and field not in replace_fields
                    and not (field == 'provider_kind' and stored[field] == 'unknown')):
                continue
            if value is not None:
                updates[field] = value
                if proof_key in evidence:
                    provenance[proof_key] = evidence[proof_key]
            elif owned:
                updates[field] = None
                provenance.pop(proof_key, None)
        if seat:
            await self._connection.execute('UPDATE vrtici SET podrijetlo=$2 WHERE id=$1', identity, provenance)
        else:
            updates['provenance'] = provenance
        if not updates:
            return
        columns = ','.join(f'{database_column(field)}=${index}' for index, field in enumerate(updates, 2))
        await self._connection.execute(f'UPDATE {table} SET {columns} WHERE {identity_column}=$1', identity, *updates.values())
