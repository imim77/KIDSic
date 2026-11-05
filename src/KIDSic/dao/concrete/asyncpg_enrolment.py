"""AsyncpgEnrolmentDocumentRepository stores reviewed excerpts as RAG document chunks."""
from collections import defaultdict
from hashlib import sha256
from uuid import uuid4

from KIDSic.dao.interfaces.enrolment import EnrolmentDocumentRepository
from KIDSic.dto.enrolment import EnrolmentDocument
from KIDSic.dto.source import name_key
from KIDSic.exceptions import SourceImportError

KIND = 'enrolment_document'  # Marks these sources; they never prove an object is active.


class AsyncpgEnrolmentDocumentRepository(EnrolmentDocumentRepository):
    def __init__(self, connection):
        self._connection = connection

    async def import_document(self, document: EnrolmentDocument, snapshot_key: str, fetched_at) -> dict:
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
        default_scope = 'institution' if document.institutions else 'municipality'
        records = defaultdict(list)
        for ordinal, excerpt in enumerate(document.excerpts):
            if excerpt.institutions:
                for owner in (resolve(n) for n in excerpt.institutions):
                    records[owner, 'institution'].append((ordinal, excerpt.content))
            else:
                for owner in covered:
                    records[owner, default_scope].append((ordinal, excerpt.content))
        if document.calls:
            for owner in covered:  # A call needs a record even without shared excerpts.
                records.setdefault((owner, default_scope), [])
        batch, record_ids = uuid4(), {}
        dates = {'reference_date': document.reference_date.isoformat(), 'date_kind': document.date_kind,
                 'valid_until': document.valid_until.isoformat() if document.valid_until else None}
        observed_on = document.reference_date if document.date_kind == 'observed' else None
        for (owner, scope), chunks in records.items():
            record = record_ids[owner, scope] = await self._connection.fetchval('''
                INSERT INTO source_record(source_id,batch_id,source_key,raw_data,fetched_at,observed_on,
                                          kindergarten_id,match_status,match_method,match_note)
                VALUES ($1,$2,$3,$4,$5,$6,$7,'accepted',$8,$9) RETURNING id
            ''', stored['id'], batch, f'{owner}:{scope}',
                {'kind': KIND, 'snapshot_key': snapshot_key, 'document_url': str(document.url),
                 'scope': scope, **dates}, fetched_at, observed_on, owner,
                'name' if scope == 'institution' else 'manual',
                'Reviewed snapshot: named institution.' if scope == 'institution'
                else 'Reviewed snapshot: every active provider of the listed kinds in the municipality.')
            await self._connection.executemany('''
                INSERT INTO knowledge_chunk(kindergarten_id,source_record_id,ordinal,content,source_url,content_sha256)
                VALUES ($1,$2,$3,$4,$5,$6)
            ''', [(owner, record, ordinal, content, str(document.url), sha256(content.encode()).hexdigest())
                  for ordinal, content in chunks])
        for call in document.calls:
            refused = {resolve(name) for name in call.not_accepting}
            await self._connection.executemany('''
                INSERT INTO enrolment(kindergarten_id,source_record_id,academic_year,application_url,
                                      opens_at,closes_at,channel,round,accepting)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            ''', [(owner, record_ids[owner, default_scope], call.academic_year, str(call.application_url),
                   call.opens_at, call.closes_at, call.channel, call.round, owner not in refused)
                  for owner in covered])
        await self._connection.execute('''
            UPDATE data_source SET active_batch_id=$2,fetched_at=$3,observed_on=$4 WHERE id=$1
        ''', stored['id'], batch, fetched_at, observed_on)
        return {'source': document.dataset_key, 'institutions': len({owner for owner, _ in records}),
                'records': len(records), 'chunks': sum(len(c) for c in records.values()),
                'enrolment_rounds': len(document.calls) * len(covered),
                'reference_date': document.reference_date.isoformat(), 'date_kind': document.date_kind}
