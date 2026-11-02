"""SQL persistence for CKAN registration and atomic, repeatable snapshots."""
from dataclasses import asdict
from uuid import uuid4

from KIDSic.dao.interfaces.source import SourceRepository
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
        collision = await self._connection.fetchval('''
            SELECT dataset_key FROM data_source WHERE dataset_key<>$1 AND (
                metadata->>'resource_url'=$3 OR
                (metadata->>'ckan_base_url'=$2 AND metadata->>'ckan_resource_id'=$4)) LIMIT 1
        ''', source.definition.key, source.definition.base_url.rstrip('/'),
            str(source.resource.url), source.resource.id)
        if collision is not None:
            raise SourceImportError(f'This CKAN resource is already registered as {collision}.')
        old = await self._connection.fetchrow(
            'SELECT * FROM data_source WHERE dataset_key=$1 FOR UPDATE', source.definition.key)
        values = (source.package.title, source.publisher, source.catalogue_url,
                  source.package.license_title or source.package.license_id)
        if old is None:
            await self._connection.execute('''
                INSERT INTO data_source(dataset_key,title,publisher,url,license,import_allowed,metadata)
                VALUES ($1,$2,$3,$4,$5,true,$6)
            ''', source.definition.key, *values, source.metadata)
            return 'added'
        unchanged = tuple(old[field] for field in ('title', 'publisher', 'url', 'license')) == values
        unchanged = unchanged and all(old['metadata'].get(k) == v for k, v in source.metadata.items())
        if unchanged:
            return 'unchanged'
        await self._connection.execute('''
            UPDATE data_source SET title=$2,publisher=$3,url=$4,license=$5,metadata=metadata || $6
            WHERE dataset_key=$1
        ''', source.definition.key, *values, source.metadata)
        return 'updated'

    async def import_snapshot(self, snapshot: SourceSnapshot) -> dict:
        source = snapshot.source
        registered = await self.register(source)
        stored = await self._connection.fetchrow(
            'SELECT id,import_allowed FROM data_source WHERE dataset_key=$1', source.definition.key)
        if not stored['import_allowed']:
            raise SourceImportError(f'Import is disabled for {source.definition.key}.')
        source_id, batch = stored['id'], uuid4()
        self._municipalities = {}
        previous = {r['source_key']: r for r in await self._connection.fetch('''
            SELECT DISTINCT ON (source_key) source_key,kindergarten_id,location_id
            FROM source_record WHERE source_id=$1 AND match_status='accepted'
            ORDER BY source_key,fetched_at DESC,id
        ''', source_id)}
        owners = {r['id']: {**dict(r), 'name_key': name_key(r['name']), 'areas': set()}
                  for r in await self._connection.fetch('''
            SELECT k.id,k.name,k.provider_kind,k.oib,k.seat_settlement_key,m.key AS municipality
            FROM kindergarten k LEFT JOIN municipality m ON m.id=k.seat_municipality_id
        ''')}
        for item in owners.values():
            if item['seat_settlement_key']:
                item['areas'].add((item['seat_settlement_key'], item['municipality']))
        locations = [dict(r) for r in await self._connection.fetch('''
            SELECT l.id,l.kindergarten_id,l.settlement_key,l.address,m.key AS municipality
            FROM location l LEFT JOIN municipality m ON m.id=l.municipality_id
            WHERE l.kindergarten_id IS NOT NULL
        ''')]
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
            if prior is not None:
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
                await self._record(source_id, batch, row, snapshot.fetched_at,
                                   note='Ambiguous normalized name/address; manual review required.')
                counts['needs_review'] += 1
                continue
            else:
                owner = next(iter(compatible), None)
                method = 'name' if owner else 'new'
            record_id = uuid4()
            evidence = {'dataset_key': source.definition.key, 'source_record_id': str(record_id)}
            if owner is None:
                owner = await self._connection.fetchval('''
                    INSERT INTO kindergarten(name,provider_kind,provenance)
                    VALUES ($1,$2,$3) RETURNING id
                ''', row.name, row.provider_kind, {'name': evidence, 'provider_kind': evidence})
                owners[owner] = {'id': owner, 'oib': None, 'areas': set()}
                counts['kindergartens_added'] += 1
            owner_provenance = {key: evidence for key in ('email', 'phone', 'website_url', 'oib')
                                if getattr(row, key) is not None}
            if row.provider_kind != 'unknown':
                owner_provenance['provider_kind'] = evidence
            owner_values = await self._connection.fetchrow('''
                UPDATE kindergarten SET email=COALESCE($2,email),phone=COALESCE($3,phone),
                    website_url=COALESCE($4,website_url),oib=COALESCE($10,oib),
                    provider_kind=CASE WHEN $5='unknown' THEN provider_kind ELSE $5 END,
                    name=CASE WHEN provenance->'name'->>'dataset_key'=$7 THEN $8 ELSE name END,
                    provenance=provenance || $6 || CASE
                        WHEN provenance->'name'->>'dataset_key'=$7
                        THEN jsonb_build_object('name',$9::jsonb) ELSE '{}'::jsonb END
                WHERE id=$1 RETURNING name,provider_kind,oib
            ''', owner, row.email, row.phone, row.website_url, row.provider_kind,
                owner_provenance, source.definition.key, row.name, evidence, row.oib)
            owners[owner].update(owner_values, name_key=name_key(owner_values['name']))
            municipality_id = await self._municipality_id(row.municipality)
            data = asdict(row)
            if institution:
                seat_provenance = {f'seat_{key}': evidence for key in
                                   ('address', 'postal_code', 'settlement', 'county')
                                   if data[key] is not None}
                await self._connection.execute('''
                    UPDATE kindergarten SET seat_address=$2,seat_postal_code=$3,seat_settlement=$4,
                        seat_settlement_key=$5,seat_county=$6,seat_municipality_id=$7,
                        provenance=provenance || $8 WHERE id=$1
                ''', owner, row.address, row.postal_code, row.settlement, settlement_key,
                    row.county, municipality_id, seat_provenance)
                owners[owner]['areas'].add(area)
                claimed.add(owner)
            else:
                location_provenance = {key: evidence for key in ('location_name', 'settlement',
                    'address', 'postal_code', 'county', 'district', 'longitude', 'latitude')
                    if data[key] is not None}
                if row.kind != 'unknown':
                    location_provenance['kind'] = evidence
                if location is None:
                    location = await self._connection.fetchval('''
                        INSERT INTO location(kindergarten_id,name,settlement,settlement_key,address)
                        VALUES ($1,$2,$3,$4,$5) RETURNING id
                    ''', owner, row.location_name, row.settlement, settlement_key, row.address)
                    counts['locations_added'] += 1
                    locations.append({'id': location, 'kindergarten_id': owner})
                await self._connection.execute('''
                    UPDATE location SET name=$2,settlement=$3,settlement_key=$4,address=$5,
                        kind=CASE WHEN $6='unknown' THEN kind ELSE $6 END,
                        postal_code=COALESCE($7,postal_code),county=COALESCE($8,county),
                        district=COALESCE($9,district),longitude=COALESCE($10,longitude),
                        latitude=COALESCE($11,latitude),municipality_id=$12,
                        provenance=provenance || $13 WHERE id=$1 AND kindergarten_id=$14
                ''', location, row.location_name, row.settlement, settlement_key, row.address,
                    row.kind, row.postal_code, row.county, row.district, row.longitude,
                    row.latitude, municipality_id, location_provenance, owner)
                # Keep the in-memory index current for subsequent rows in this batch.
                for item in locations:
                    if item['id'] == location:
                        item.update(area=area, address_key=row_address)
                owners[owner]['areas'].add(area)
            await self._record(source_id, batch, row, snapshot.fetched_at, owner=owner,
                               location=location, record_id=record_id, method=method)
            counts['accepted'] += 1
        if not counts['accepted']:
            raise SourceImportError('No accepted records; refusing to activate the snapshot.')
        await self._connection.execute('''
            UPDATE data_source SET active_batch_id=$2,fetched_at=$3,observed_on=NULL WHERE id=$1
        ''', source_id, batch, snapshot.fetched_at)
        # Fetch time and resource modification are not the observed date of the data.
        return {'source': source.definition.key, 'registration': registered,
                'batch_id': str(batch), **counts}

    async def _municipality_id(self, key):
        if key is None:
            return None
        if key not in self._municipalities:
            item = MUNICIPALITIES[key]
            self._municipalities[key] = await self._connection.fetchval('''
                INSERT INTO municipality(key,name,county,aliases) VALUES ($1,$2,$3,$4)
                ON CONFLICT (key) DO UPDATE SET name=EXCLUDED.name,county=EXCLUDED.county,
                    aliases=EXCLUDED.aliases RETURNING id
            ''', item.key, item.name, item.county, list(item.aliases))
        return self._municipalities[key]

    async def _record(self, source_id, batch, row, fetched_at, *, owner=None, location=None,
                      record_id=None, method=None, note=None):
        await self._connection.execute('''
            INSERT INTO source_record(id,source_id,batch_id,source_key,raw_data,fetched_at,
                                      kindergarten_id,location_id,match_status,match_method,match_note)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        ''', record_id or uuid4(), source_id, batch, row.source_key, row.raw_data,
            fetched_at, owner, location, 'accepted' if owner else 'candidate', method, note)
