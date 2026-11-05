"""EnrolmentDocumentService imports reviewed official enrolment excerpts in one transaction."""
from datetime import datetime, timezone

from KIDSic.db.uow.source import SourceUnitOfWorkFactory
from KIDSic.dto.enrolment import EnrolmentSnapshot


class EnrolmentDocumentService:
    # The snapshot is reviewed by hand: PDF layouts and licences differ per
    # publisher, so excerpts are transcribed whole instead of cut automatically.
    def __init__(self, snapshot: EnrolmentSnapshot, uow_factory: SourceUnitOfWorkFactory | None = None):
        self._snapshot, self._uow_factory = snapshot, uow_factory

    def preview_import(self):
        return {'dry_run': True, 'snapshot': self._snapshot.snapshot_key, 'sources': [
            {'source': d.dataset_key, 'url': str(d.url), 'license': d.license, 'excerpts': len(d.excerpts),
             'reference_date': d.reference_date.isoformat(), 'date_kind': d.date_kind}
            for d in self._snapshot.documents]}

    async def import_data(self):
        if self._uow_factory is None:
            raise RuntimeError('Enrolment import requires a Unit of Work factory.')
        fetched_at = datetime.now(timezone.utc)
        async with self._uow_factory() as work:
            results = [await work.enrolment.import_document(d, self._snapshot.snapshot_key, fetched_at)
                       for d in self._snapshot.documents]
        return {'snapshot': self._snapshot.snapshot_key, 'sources': results,
                'chunks': sum(r['chunks'] for r in results)}
