"""RagEvidenceBuilder turns accepted structured facts into dated, scoped excerpts."""
from hashlib import sha256
from KIDSic.dto.rag import RagEvidence, RagSource
from KIDSic.services.interfaces.presenters import SubsidyPresenter
from KIDSic.services.interfaces.rag import EvidenceBuilder


class RagEvidenceBuilder(EvidenceBuilder):
    def __init__(self, subsidies: SubsidyPresenter):
        self._subsidies = subsidies

    @staticmethod
    def feature_id(row):
        return str(row['location_id']) if row['location_id'] else f"seat:{row['kindergarten_id']}"

    @staticmethod
    def context_scope(rows):
        return dict(location_ids=[r['location_id'] for r in rows if r['location_id']],
            kindergarten_ids=[r['kindergarten_id'] for r in rows if not r['location_id']])

    def collect(self, rows, chunks):
        evidence = {}

        def add(item):
            if item.citation_id in evidence:
                evidence[item.citation_id].applies_to.extend(item.applies_to)
            else:
                evidence[item.citation_id] = item

        for row in rows:
            for item in self._build(row):
                add(item)
        for chunk in chunks:
            for row in rows:
                if self._covers(chunk, row):
                    add(self._document(row, chunk))
        return list(evidence.values())

    @staticmethod
    def _covers(chunk, row) -> bool:
        """_covers is true when a document chunk is about the row's
        kindergarten and, if it names a facility, about that facility."""
        return chunk['kindergarten_id'] == row['kindergarten_id'] and (
            chunk['location_id'] is None or chunk['location_id'] == row['location_id'])

    def _document(self, row, chunk):
        reference = chunk['observed_on'] or chunk.get('published_on')
        return self._evidence(row, topic='document', content=chunk['content'],
            scope='facility' if chunk['location_id'] else (
                'municipality' if chunk.get('document_scope') == 'municipality' else 'institution'),
            sources=[RagSource(title=chunk['source_title'], url=chunk['source_url'], license=chunk.get('license'))],
            reference_date=reference, date_kind='observed' if chunk['observed_on'] else (
                'published' if reference else 'unknown'),
            # Current only while the governed period lasts; deadlines inside it stay dated.
            temporal_status='current' if chunk.get('in_effect') else (
                'historical' if reference else 'undated'))

    def _evidence(self, row, *, topic, content, sources, reference_date=None,
                 date_kind='unknown', temporal_status='undated', scope='facility'):
        location = str(row['location_id']) if scope == 'facility' and row['location_id'] else None
        identity = f"{row['kindergarten_id']}|{location}|{topic}|{reference_date}|{content}|{sources}"
        return RagEvidence(citation_id='E' + sha256(identity.encode()).hexdigest()[:16],
            kindergarten_id=str(row['kindergarten_id']), location_id=location,
            applies_to=[self.feature_id(row)], scope=scope, topic=topic, content=content,
            sources=sources, reference_date=reference_date, date_kind=date_kind, temporal_status=temporal_status)

    def _build(self, row):
        result = []
        for key, label in (('website_url', 'Službena web-stranica'), ('email', 'E-mail'), ('phone', 'Telefon')):
            source = row.get('contact_sources', {}).get(key)
            if row.get(key) and source:
                result.append(self._evidence(row, topic='contacts', content=f'{label}: {row[key]}',
                    scope=source['scope'], sources=[RagSource(title=source['name'], url=source['url'],
                    license=source['license'])], reference_date=source['reference_date'],
                    date_kind='observed' if source['reference_date'] else 'unknown',
                    temporal_status='historical' if source['reference_date'] else 'undated'))
        for record in row.get('historical_data', []):
            source = [RagSource(title=record['source_title'], url=record['source_url'], license=record['license'])]
            common = dict(sources=source, reference_date=record['reference_date'], date_kind=record['date_kind'],
                          temporal_status='historical', scope=record['scope'])
            if record['programs']:
                result.append(self._evidence(row, topic='programs',
                    content='Povijesno objavljeni programi: ' + '; '.join(record['programs']) +
                    '. Provedba danas i dobni uvjeti nisu potvrđeni ovom snimkom.', **common))
            if record['vacancies']:
                scope_note = ('Podatak za cijelu ustanovu/obrt; nije raspoređen po objektima. '
                    'Ne zbrajati isti broj po podružnicama.' if record['scope'] == 'institution'
                    else 'Podatak za ovaj objekt.')
                groups = [f"{v['age_label'] or 'dob nije navedena'} / {v['program'] or 'program nije naveden'}: "
                          f"{v['free_places'] if v['free_places'] is not None else 'nije objavljeno'}"
                          for v in record['vacancies']]
                result.append(self._evidence(row, topic='vacancies',
                    content='Povijesno objavljena slobodna mjesta:\n' + '\n'.join(groups) +
                    f'\n{scope_note} Ovo nije današnja raspoloživost ni jamstvo upisa.', **common))
        for raw in row.get('subsidy_policies', []):
            policy = self._subsidies.present(raw)
            rates = [rate.model_dump_json() for rate in policy.rates]
            result.append(self._evidence(row, topic='subsidies', scope='municipality',
                content=f'{policy.title}: {policy.summary}\nVrsta iznosa: {policy.amount_kind}. '
                    f'Status provjere: {policy.verification_status}. Iznosi u tarifama su eurocenti.\n' +
                    '\n'.join(rates + policy.conditions + policy.reliefs + policy.notes) +
                    f'\nRazdoblje: {policy.valid_from} – {policy.valid_until}. '
                    'Pravo pojedine obitelji i ugovor vrtića s Gradom nisu potvrđeni samom vrstom objekta.',
                sources=[RagSource(title=s.title, url=s.url) for s in policy.sources],
                reference_date=policy.verified_on, date_kind='verified', temporal_status='current'))
        return result
