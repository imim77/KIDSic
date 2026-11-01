"""SQL persistence for CKAN registration and atomic, repeatable snapshots."""
from dataclasses import asdict
from uuid import uuid4

from KIDSic.dao.interfaces.source import SourceRepository
from KIDSic.dto.source import PlannedSource, SourceSnapshot, name_key
from KIDSic.dto.text import normalize
from KIDSic.exceptions import SourceImportError


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
        previous = {r['source_key']: r for r in await self._connection.fetch('''
            SELECT DISTINCT ON (source_key) source_key,kindergarten_id,location_id
            FROM source_record WHERE source_id=$1 AND match_status='accepted'
            ORDER BY source_key,fetched_at DESC,id
        ''', source_id)}
        locations = [dict(r) for r in await self._connection.fetch('''
            SELECT l.id,l.kindergarten_id,l.city_key,l.address,k.name,k.provider_kind
            FROM location l JOIN kindergarten k ON k.id=l.kindergarten_id
        ''')]
        counts = {'records': len(snapshot.rows), 'accepted': 0, 'needs_review': 0,
                  'kindergartens_added': 0, 'locations_added': 0}
        for row in snapshot.rows:
            # Resolve by prior source identity first, then exact normalized address
            # and institution name. Multiple owners remain review candidates.
            city = normalize(row.city)
            compatible = [l for l in locations if l['city_key'] == city
                          and name_key(l['name']) == name_key(row.name)
                          and (l['provider_kind'] in {'unknown', row.provider_kind}
                               or row.provider_kind == 'unknown')]
            exact = [l for l in compatible if name_key(l['address'] or '') == name_key(row.address)]
            prior = previous.get(row.source_key)
            owner_ids = {l['kindergarten_id'] for l in compatible}
            if prior is not None:
                owner, location = prior['kindergarten_id'], prior['location_id']
            elif len(exact) == 1:
                owner, location = exact[0]['kindergarten_id'], exact[0]['id']
            elif len(exact) > 1 or len(owner_ids) > 1:
                await self._record(source_id, batch, row, snapshot.fetched_at,
                                   note='Ambiguous normalized name/address; manual review required.')
                counts['needs_review'] += 1
                continue
            else:
                owner, location = next(iter(owner_ids), None), None
            record_id = uuid4()
            evidence = {'dataset_key': source.definition.key, 'source_record_id': str(record_id)}
            if owner is None:
                owner = await self._connection.fetchval('''
                    INSERT INTO kindergarten(name,provider_kind,provenance)
                    VALUES ($1,$2,$3) RETURNING id
                ''', row.name, row.provider_kind, {'name': evidence, 'provider_kind': evidence})
                counts['kindergartens_added'] += 1
            owner_provenance = {key: evidence for key in ('email', 'phone', 'website_url')
                                if getattr(row, key) is not None}
            if row.provider_kind != 'unknown':
                owner_provenance['provider_kind'] = evidence
            owner_values = await self._connection.fetchrow('''
                UPDATE kindergarten SET email=COALESCE($2,email),phone=COALESCE($3,phone),
                    website_url=COALESCE($4,website_url),
                    provider_kind=CASE WHEN $5='unknown' THEN provider_kind ELSE $5 END,
                    name=CASE WHEN provenance->'name'->>'dataset_key'=$7 THEN $8 ELSE name END,
                    provenance=provenance || $6 || CASE
                        WHEN provenance->'name'->>'dataset_key'=$7
                        THEN jsonb_build_object('name',$9::jsonb) ELSE '{}'::jsonb END
                WHERE id=$1 RETURNING name,provider_kind
            ''', owner, row.email, row.phone, row.website_url, row.provider_kind,
                owner_provenance, source.definition.key, row.name, evidence)
            data = asdict(row)
            location_provenance = {key: evidence for key in ('location_name', 'city', 'address',
                'postal_code', 'county', 'district', 'longitude', 'latitude') if data[key] is not None}
            if row.kind != 'unknown':
                location_provenance['kind'] = evidence
            aliases = {'zagreb': ['zagreba', 'zagrebu'], 'varazdin': ['varazdina', 'varazdinu'],
                       'rijeka': ['rijeke', 'rijeci'], 'split': ['splita', 'splitu'],
                       'osijek': ['osijeka', 'osijeku']}.get(city, [])
            if location is None:
                location = await self._connection.fetchval('''
                    INSERT INTO location(kindergarten_id,name,city,city_key,address)
                    VALUES ($1,$2,$3,$4,$5) RETURNING id
                ''', owner, row.location_name, row.city, city, row.address)
                counts['locations_added'] += 1
                locations.append({'id': location, 'kindergarten_id': owner, 'city_key': city,
                                  'address': row.address, 'name': row.name,
                                  'provider_kind': row.provider_kind})
            await self._connection.execute('''
                UPDATE location SET name=$2,city=$3,city_key=$4,address=$5,
                    kind=CASE WHEN $6='unknown' THEN kind ELSE $6 END,
                    postal_code=COALESCE($7,postal_code),county=COALESCE($8,county),
                    district=COALESCE($9,district),longitude=COALESCE($10,longitude),
                    latitude=COALESCE($11,latitude),city_aliases=$12,
                    provenance=provenance || $13 WHERE id=$1 AND kindergarten_id=$14
            ''', location, row.location_name, row.city, city, row.address, row.kind,
                row.postal_code, row.county, row.district, row.longitude, row.latitude,
                aliases, location_provenance, owner)
            # Keep the in-memory index current for subsequent rows in this batch.
            for item in locations:
                if item['kindergarten_id'] == owner:
                    item.update(name=owner_values['name'], provider_kind=owner_values['provider_kind'])
                if item['id'] == location:
                    item.update(city_key=city, address=row.address)
            await self._record(source_id, batch, row, snapshot.fetched_at,
                               owner=owner, location=location, record_id=record_id)
            counts['accepted'] += 1
        if not counts['accepted']:
            raise SourceImportError('No accepted records; refusing to activate the snapshot.')
        await self._connection.execute('''
            UPDATE data_source SET active_batch_id=$2,fetched_at=$3,observed_on=NULL WHERE id=$1
        ''', source_id, batch, snapshot.fetched_at)
        # Fetch time and resource modification are not the observed date of the data.
        return {'source': source.definition.key, 'registration': registered,
                'batch_id': str(batch), **counts}

    async def _record(self, source_id, batch, row, fetched_at, *, owner=None, location=None,
                      record_id=None, note=None):
        await self._connection.execute('''
            INSERT INTO source_record(id,source_id,batch_id,source_key,raw_data,fetched_at,
                                      kindergarten_id,location_id,match_status,match_note)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
        ''', record_id or uuid4(), source_id, batch, row.source_key, row.raw_data,
            fetched_at, owner, location, 'accepted' if owner else 'candidate', note)
