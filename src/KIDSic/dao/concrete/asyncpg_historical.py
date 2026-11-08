"""AsyncpgHistoricalRepository attaches history without creating current objects."""
import re

from KIDSic.dao.concrete.source_state import SourceStateWriter
from KIDSic.dao.interfaces.historical import HistoricalRepository
from KIDSic.dto.historical import HistoricalSnapshot
from KIDSic.dto.source import name_key
from KIDSic.exceptions import SourceImportError


def address_key(value: str) -> str:
    return ' '.join(re.sub(r'\b(?:ulica|ul)\b', '', name_key(value)).split())


class AsyncpgHistoricalRepository(HistoricalRepository):
    def __init__(self, connection):
        self._connection = connection

    async def import_snapshot(self, snapshot: HistoricalSnapshot) -> dict:
        SourceStateWriter.validate(row.source_key for row in snapshot.rows)
        async with self._connection.transaction():
            await self._connection.execute('SELECT pg_advisory_xact_lock(194733, 1)')
            return await self._import_snapshot(snapshot)

    async def _import_snapshot(self, snapshot):
        stored = await self._connection.fetchrow(
            'SELECT id,uvoz_dopusten  AS import_allowed FROM izvori_podataka WHERE kljuc_skupa_podataka=$1 FOR UPDATE',
            snapshot.source.definition.key)
        if stored is None or not stored['import_allowed']:
            raise SourceImportError('Historical source must be registered and approved.')
        if not snapshot.rows:
            raise SourceImportError('Historical snapshot must not be empty.')

        places = await self._connection.fetch("""
          WITH active AS (
            SELECT r.id_vrtica,r.id_objekta FROM izvorni_zapisi r
            JOIN izvori_podataka s ON s.id=r.id_izvora
            WHERE s.uvoz_dopusten AND r.status_povezivanja='accepted'
          )
          SELECT k.id,k.naziv AS name,k.vrsta_pruzatelja AS provider_kind,l.id AS location_id,l.adresa
           AS address FROM vrtici k LEFT JOIN objekti l ON l.id_vrtica=k.id
            AND EXISTS(SELECT 1 FROM active a WHERE a.id_objekta=l.id AND a.id_vrtica=k.id)
          LEFT JOIN jedinice_lokalne_samouprave lm ON lm.id=l.id_jedinice_lokalne_samouprave
          LEFT JOIN sjedista_vrtica ks ON ks.id_vrtica=k.id
          LEFT JOIN jedinice_lokalne_samouprave km ON km.id=ks.id_jedinice_lokalne_samouprave
          WHERE EXISTS(SELECT 1 FROM active a WHERE a.id_vrtica=k.id)
            AND (lm.kljuc='zagreb' OR (l.id IS NULL AND km.kljuc='zagreb'))
        """)
        accepted = 0
        for row in snapshot.rows:
            matches = [p for p in places if name_key(p['name']) == name_key(row.name)
                and (row.provider_kind == 'unknown' or p['provider_kind'] == row.provider_kind)
                and (row.scope == 'institution' or (p['location_id'] is not None
                    and address_key(p['address'] or '') == address_key(row.address or '')))]
            identities = {(p['id'], p['location_id'] if row.scope == 'facility' else None) for p in matches}
            owner, location = next(iter(identities)) if len(identities) == 1 else (None, None)
            status = 'accepted' if owner is not None else 'candidate'
            accepted += status == 'accepted'
            await self._connection.execute("""INSERT INTO povijesni_zapisi
                (id_izvora,kljuc_izvornog_zapisa,izvorni_podaci,id_vrtica,id_objekta,obuhvat,
                 status_povezivanja,referentni_datum,vrsta_datuma,dohvaceno_u,programi,slobodna_mjesta)
                VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                ON CONFLICT (id_izvora,kljuc_izvornog_zapisa) DO UPDATE SET
                  izvorni_podaci=EXCLUDED.izvorni_podaci,id_vrtica=EXCLUDED.id_vrtica,
                  id_objekta=EXCLUDED.id_objekta,obuhvat=EXCLUDED.obuhvat,
                  status_povezivanja=EXCLUDED.status_povezivanja,referentni_datum=EXCLUDED.referentni_datum,
                  vrsta_datuma=EXCLUDED.vrsta_datuma,dohvaceno_u=EXCLUDED.dohvaceno_u,
                  programi=EXCLUDED.programi,slobodna_mjesta=EXCLUDED.slobodna_mjesta""",
                stored['id'], row.source_key, row.raw_data, owner, location, row.scope,
                status, snapshot.reference_date, snapshot.date_kind, snapshot.fetched_at,
                list(row.programs), [v.model_dump(mode='json') for v in row.vacancies])
        if not accepted:
            raise SourceImportError('No historical records could be linked; retain the previous state.')
        await self._connection.execute("""DELETE FROM povijesni_zapisi
            WHERE id_izvora=$1 AND NOT(kljuc_izvornog_zapisa=ANY($2::text[]))""",
            stored['id'], [row.source_key for row in snapshot.rows])
        await SourceStateWriter.activate(self._connection, stored['id'], snapshot.fetched_at,
            snapshot.reference_date if snapshot.date_kind == 'observed' else None)
        return {'source': snapshot.source.definition.key, 'records': len(snapshot.rows),
                'accepted': accepted, 'needs_review': len(snapshot.rows) - accepted,
                'reference_date': snapshot.reference_date.isoformat()}
