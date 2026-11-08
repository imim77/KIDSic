"""SourceStateWriter replaces source contents while preserving record identity."""
from uuid import uuid4
from KIDSic.dao.concrete.columns import database_column, domain_projection

from KIDSic.exceptions import SourceImportError


class SourceStateWriter:


    def __init__(self, connection, source_id, fetched_at):
        self._connection = connection
        self._source_id = source_id
        self._fetched_at = fetched_at
        self._keys = set()

    @staticmethod
    def validate(keys):
        keys = list(keys)
        if not keys or any(not key for key in keys) or len(set(keys)) != len(keys):
            raise SourceImportError('Source state must be nonempty with unique source_key values.')

    async def record(self, key, raw, *, owner=None, location=None, status='accepted',
                     method='manual', note=None, observed_on=None, record_id=None):
        if key in self._keys or not key:
            raise SourceImportError(f'Duplicate or empty source_key: {key!r}.')
        self._keys.add(key)
        return await self._connection.fetchval("""
            INSERT INTO izvorni_zapisi(id,id_izvora,kljuc_izvornog_zapisa,izvorni_podaci,dohvaceno_u,
                datum_opazanja,id_vrtica,id_objekta,status_povezivanja,metoda_povezivanja,napomena_povezivanja)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            ON CONFLICT (id_izvora,kljuc_izvornog_zapisa) DO UPDATE SET
                izvorni_podaci=EXCLUDED.izvorni_podaci,
                dohvaceno_u=EXCLUDED.dohvaceno_u,datum_opazanja=EXCLUDED.datum_opazanja,
                id_vrtica=CASE WHEN izvorni_zapisi.status_povezivanja='candidate'
                    THEN EXCLUDED.id_vrtica ELSE izvorni_zapisi.id_vrtica END,
                id_objekta=CASE WHEN izvorni_zapisi.status_povezivanja='candidate'
                    THEN EXCLUDED.id_objekta ELSE izvorni_zapisi.id_objekta END,
                status_povezivanja=CASE WHEN izvorni_zapisi.status_povezivanja='candidate'
                    THEN EXCLUDED.status_povezivanja ELSE izvorni_zapisi.status_povezivanja END,
                metoda_povezivanja=CASE WHEN izvorni_zapisi.status_povezivanja='candidate'
                    THEN EXCLUDED.metoda_povezivanja ELSE izvorni_zapisi.metoda_povezivanja END,
                napomena_povezivanja=CASE WHEN izvorni_zapisi.status_povezivanja='candidate'
                    THEN EXCLUDED.napomena_povezivanja ELSE izvorni_zapisi.napomena_povezivanja END
            RETURNING id
        """, record_id or uuid4(), self._source_id, key, raw, self._fetched_at,
            observed_on, owner, location, status, method, note)

    async def clear_derived(self, record_ids):

        await self._connection.execute("""DELETE FROM neprihvacanja_upisa
            WHERE id_izvornog_zapisa=ANY($1::uuid[])""", list(record_ids))
        for table in ('odlomci_znanja', 'upisni_krugovi'):
            await self._connection.execute(
                f'DELETE FROM {table} WHERE id_izvornog_zapisa=ANY($1::uuid[])', list(record_ids))

    async def finish(self, *, observed_on=None):
        self.validate(self._keys)
        missing = await self._connection.fetch("""
            SELECT id FROM izvorni_zapisi WHERE id_izvora=$1 AND NOT(kljuc_izvornog_zapisa=ANY($2::text[]))
        """, self._source_id, list(self._keys))
        ids = [r['id'] for r in missing]
        if ids:
            await self._forget_fields(ids)
            await self._connection.execute('DELETE FROM izvorni_zapisi WHERE id=ANY($1::uuid[])', ids)
        await self.activate(self._connection, self._source_id, self._fetched_at, observed_on)

    @staticmethod
    async def activate(connection, source, fetched_at, observed_on=None):
        await connection.execute("""UPDATE izvori_podataka
            SET dohvaceno_u=$2,datum_opazanja=$3 WHERE id=$1""",
            source, fetched_at, observed_on)

    async def _forget_fields(self, ids):
        await self._connection.execute("""UPDATE sjedista_vrtica SET id_zapisa_geografskog_izvora=NULL,
            geografska_duzina=NULL,geografska_sirina=NULL,obiljezja='{}' WHERE id_zapisa_geografskog_izvora=ANY($1::uuid[])""", ids)
        texts = {str(value) for value in ids}
        for table in ('vrtici', 'objekti'):
            rows = await self._connection.fetch(f'''SELECT {domain_projection(table, qualifier='t')} FROM {table} t WHERE EXISTS (
                SELECT 1 FROM jsonb_each(t.podrijetlo) f
                WHERE f.value->>'source_record_id'=ANY($1::text[]))''', list(texts))
            for row in rows:
                provenance = dict(row['provenance'])
                removed = [key for key, value in provenance.items()
                           if value.get('source_record_id') in texts]
                if table == 'vrtici' and set(removed) & {'name', 'provider_kind'}:
                    active = await self._connection.fetchval("""SELECT EXISTS (
                        SELECT 1 FROM izvorni_zapisi r JOIN izvori_podataka s ON s.id=r.id_izvora
                        WHERE r.id_vrtica=$1 AND r.id<>ALL($2::uuid[])
                          AND r.status_povezivanja='accepted' AND s.uvoz_dopusten)""", row['id'], ids)
                    if active and ('name' in removed or row['provider_kind'] != 'unknown'):
                        raise SourceImportError(f'Review classification before removing evidence: {row["name"]}.')
                values = {}
                seat_values = {}
                attributes = dict(row.get('attributes') or {})
                for key in removed:
                    provenance.pop(key)
                    if table == 'vrtici' and key in {
                            'seat_address', 'seat_postal_code', 'seat_settlement',
                            'seat_settlement_key', 'seat_municipality_id'}:
                        seat_values[key.removeprefix('seat_')] = None
                    if key in ('name', 'provider_kind', 'location_name', 'settlement'):
                        continue
                    if table == 'objekti' and key == 'kind':
                        values[key] = 'unknown'
                    elif key in row and key not in ('id', 'kindergarten_id'):
                        values[key] = None
                    elif key in attributes:
                        attributes.pop(key)
                if seat_values:
                    if 'settlement' in seat_values:
                        seat_values['settlement_key'] = None
                    columns = ','.join(f'{database_column(key)}=${index}' for index,key in enumerate(seat_values,2))
                    await self._connection.execute(f'UPDATE sjedista_vrtica SET {columns} WHERE id_vrtica=$1',
                                                   row['id'], *seat_values.values())
                if table == 'objekti':
                    values['attributes'] = attributes
                values['provenance'] = provenance
                columns = ','.join(f'{database_column(key)}=${index}' for index, key in enumerate(values, 2))
                await self._connection.execute(f'UPDATE {table} SET {columns} WHERE id=$1',
                                                row['id'], *values.values())
