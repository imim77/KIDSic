"""AsyncpgEnrolmentDocumentRepository stores reviewed excerpts as RAG document chunks."""
from collections import defaultdict
from hashlib import sha256

from KIDSic.dao.concrete.source_state import SourceStateWriter
from KIDSic.dao.interfaces.enrolment import EnrolmentDocumentRepository
from KIDSic.dto.enrolment import EnrolmentDocument
from KIDSic.dto.source import name_key
from KIDSic.exceptions import SourceImportError

KIND = 'enrolment_document'  # Marks these sources; they never prove an object is active.


class AsyncpgEnrolmentDocumentRepository(EnrolmentDocumentRepository):
    def __init__(self, connection):
        self._connection = connection

    async def import_document(self, document: EnrolmentDocument, snapshot_key: str, fetched_at) -> dict:
        async with self._connection.transaction():
            await self._connection.execute('SELECT pg_advisory_xact_lock(194733, 1)')
            return await self._import_document(document, snapshot_key, fetched_at)

    async def _import_document(self, document, snapshot_key, fetched_at):
        stored = await self._connection.fetchrow('''
            INSERT INTO data_source(dataset_key,title,publisher,url,license,import_allowed,metadata)
            VALUES ($1,$2,$3,$4,$5,true,$6)
            ON CONFLICT(dataset_key) DO UPDATE SET title=EXCLUDED.title,publisher=EXCLUDED.publisher,
                url=EXCLUDED.url,license=EXCLUDED.license,metadata=data_source.metadata || EXCLUDED.metadata
            RETURNING id,import_allowed
        ''', document.dataset_key, document.title, document.publisher, str(document.url), document.license,
            {'kind': KIND, 'license_url': str(document.license_url), 'document_sha256': document.sha256,
             'snapshot_key': snapshot_key})
        if not stored['import_allowed']:
            raise SourceImportError(f'Import is disabled for {document.dataset_key}.')
        # Only directory records anchor the targets; enrolment chunks cannot keep
        # a kindergarten alive after the directory drops it.
        owners = await self._connection.fetch('''
            WITH active AS (
              SELECT r.kindergarten_id,r.location_id FROM source_record r
              JOIN data_source s ON s.id=r.source_id AND s.active_batch_id=r.batch_id
              WHERE s.import_allowed AND r.match_status='accepted'
                AND s.metadata->>'kind' IS DISTINCT FROM $3
            )
            SELECT k.id,k.name FROM kindergarten k
            WHERE k.provider_kind=ANY($2::text[]) AND EXISTS(SELECT 1 FROM active a WHERE a.kindergarten_id=k.id)
              AND (EXISTS(SELECT 1 FROM municipality m WHERE m.id=k.seat_municipality_id AND m.key=$1)
                OR EXISTS(SELECT 1 FROM location l JOIN municipality m ON m.id=l.municipality_id
                  JOIN active a ON a.location_id=l.id WHERE l.kindergarten_id=k.id AND m.key=$1))
        ''', document.municipality, list(document.provider_kinds), KIND)
        if not owners:
            raise SourceImportError(f'No active institutions for {document.dataset_key}; retain the previous batch.')

        def resolve(name):
            # A reviewed snapshot names institutions exactly; guessing would attach
            # another kindergarten's rules.
            found = [o['id'] for o in owners if name_key(o['name']) == name_key(name)]
            if len(found) != 1:
                raise SourceImportError(f'{document.dataset_key}: {len(found)} active institutions match {name!r}.')
            return found[0]

        covered = [resolve(n) for n in document.institutions] or [o['id'] for o in owners]
        records = defaultdict(list)
        targets = {}

        def group(names=()):
            named = tuple(sorted((resolve(n) for n in names), key=str))
            key = ':'.join(map(str, named)) if named else 'municipality'
            targets[key] = named
            return key

        default_key = group(document.institutions)
        for ordinal, excerpt in enumerate(document.excerpts):
            key = group(excerpt.institutions) if excerpt.institutions else default_key
            records[key].append((ordinal, excerpt.content))
        if document.calls:
            records.setdefault(default_key, [])
        SourceStateWriter.validate(records)
        state = SourceStateWriter(self._connection, stored['id'], fetched_at)
        record_ids = {}
        dates = {'reference_date': document.reference_date.isoformat(), 'date_kind': document.date_kind,
                 'valid_until': document.valid_until.isoformat() if document.valid_until else None}
        observed_on = document.reference_date if document.date_kind == 'observed' else None
        municipality = await self._connection.fetchval('SELECT id FROM municipality WHERE key=$1', document.municipality)
        for key, chunks in records.items():
            named = targets[key]
            owner = named[0] if len(named) == 1 else None
            scope = 'institution' if named else 'municipality'
            record = record_ids[key] = await state.record(key,
                {'kind': KIND, 'snapshot_key': snapshot_key, 'document_url': str(document.url),
                 'scope': scope, **dates}, owner=owner, observed_on=observed_on,
                method='name' if named else 'manual', note='Reviewed document scope.')
            await state.clear_derived([record])
            await self._connection.execute('DELETE FROM document_scope WHERE source_record_id=$1', record)
            if named:
                await self._connection.executemany(
                    'INSERT INTO document_scope(source_record_id,kindergarten_id) VALUES($1,$2)',
                    [(record, target) for target in named])
            else:
                await self._connection.execute('''INSERT INTO document_scope
                    (source_record_id,municipality_id,provider_kinds) VALUES($1,$2,$3)''',
                    record, municipality, list(document.provider_kinds))
            await self._connection.executemany('''
                INSERT INTO knowledge_chunk(kindergarten_id,source_record_id,ordinal,content,source_url,content_sha256)
                VALUES ($1,$2,$3,$4,$5,$6)
            ''', [(owner, record, ordinal, content, str(document.url), sha256(content.encode()).hexdigest())
                  for ordinal, content in chunks])
        for call in document.calls:
            refused = {resolve(name) for name in call.not_accepting}
            record = record_ids[default_key]
            named = targets[default_key]
            enrolment = await self._connection.fetchval('''
                INSERT INTO enrolment(kindergarten_id,source_record_id,academic_year,application_url,
                                      opens_at,closes_at,channel,round)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8) RETURNING id
            ''', named[0] if len(named) == 1 else None, record, call.academic_year,
                str(call.application_url), call.opens_at, call.closes_at, call.channel, call.round)
            await self._connection.executemany('''INSERT INTO enrolment_refusal
                (enrolment_id,kindergarten_id,source_record_id) VALUES ($1,$2,$3)''',
                [(enrolment, owner, record) for owner in refused])
        await state.finish(observed_on=observed_on)
        return {'source': document.dataset_key, 'institutions': len(set(covered) | {o for key in records for o in targets[key]}),
                'records': len(records), 'chunks': sum(len(c) for c in records.values()),
                'enrolment_rounds': len(document.calls),
                'reference_date': document.reference_date.isoformat(), 'date_kind': document.date_kind}
