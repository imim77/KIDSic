"""Deterministic RAG checks cover topic filters, attribution, identity and empty evidence."""
from contextlib import asynccontextmanager
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock
import unittest
from uuid import uuid4

from pydantic import ValidationError
from KIDSic.dto.rag import RagQuery
from KIDSic.factories.rag import RagServiceFactory


def row(*, owner=None, location=None):
    return dict(kindergarten_id=owner or uuid4(), location_id=location or uuid4(), name='Synthetic Primjer',
        location_name='Synthetic object', address='Synthetic 1', city='Zagreb', programs=[],
        historical_data=[dict(reference_date='2019-10-09',date_kind='published',scope='facility',
            programs=['Montessori', 'engleski jezik'], vacancies=[], source_title='Synthetic open data',
            source_url='https://example.invalid/programs',license='OD'),
            dict(reference_date='2025-01-01',date_kind='observed',scope='institution',programs=[],
            vacancies=[dict(age_label='od 1 do 2 godine',program='REDOVITI PROGRAM',free_places=0),
                       dict(age_label='od 3 godine do OŠ',program='POSEBNI PROGRAM',free_places=None)],
            source_title='Synthetic vacancies',source_url='https://example.invalid/vacancies',license='OD')])


class RagServiceTests(unittest.IsolatedAsyncioTestCase):
    def service(self, rows, chunks=None):
        self.locations = SimpleNamespace(list_locations=AsyncMock(return_value=rows))
        self.search = SimpleNamespace(retrieve_context=AsyncMock(return_value=chunks or []))
        self.events = []
        @asynccontextmanager
        async def work():
            self.events.append('enter')
            yield SimpleNamespace(locations=self.locations, search=self.search)
            self.events.append('exit')
        return RagServiceFactory().create(work)

    async def test_historical_programs_are_retrievable_without_confirmed_age(self):
        item = row(); service = self.service([item])
        result = await service.retrieve(RagQuery(city='Zagreb',name='Primjer',topics=['programs']))
        self.assertEqual(result.status, 'ok')
        self.assertEqual({e.topic for e in result.evidence}, {'programs'})
        evidence, = result.evidence
        self.assertEqual(evidence.temporal_status, 'historical')
        self.assertEqual(evidence.reference_date.isoformat(), '2019-10-09')
        self.assertEqual(evidence.date_kind, 'published')
        self.assertEqual(evidence.sources[0].url, 'https://example.invalid/programs')
        self.assertIn('nisu potvrđeni', evidence.content)
        self.assertEqual(self.events, ['enter','exit'])
        self.assertIsNone(self.locations.list_locations.await_args.args[0].age_months)

    async def test_institution_vacancies_are_deduplicated_and_zero_is_not_unknown(self):
        first = row(); second = deepcopy(first); second['location_id'] = uuid4()
        service = self.service([first,second])
        result = await service.retrieve(RagQuery(city='Zagreb',name='Primjer',topics=['vacancies']))
        evidence, = result.evidence
        self.assertEqual(evidence.topic, 'vacancies')
        self.assertEqual(evidence.scope, 'institution')
        self.assertIsNone(evidence.location_id)
        self.assertEqual(len(evidence.applies_to), 2)
        self.assertIn('REDOVITI PROGRAM: 0', evidence.content)
        self.assertIn('POSEBNI PROGRAM: nije objavljeno', evidence.content)
        self.assertIn('nije današnja', evidence.content)
        self.assertEqual(evidence.reference_date.isoformat(), '2025-01-01')

    async def test_ambiguous_institutions_require_selection_before_retrieving_any_context(self):
        first, second = row(), row()
        service = self.service([first,second])
        result = await service.retrieve(RagQuery(city='Zagreb',name='Primjer',topics=['programs']))
        self.assertEqual(result.status, 'clarification_required')
        self.assertFalse(result.evidence)
        self.search.retrieve_context.assert_not_awaited()
        result = await service.retrieve(RagQuery(city='Zagreb',name='Primjer',topics=['programs'],
            feature_id=str(first['location_id'])))
        self.assertEqual(result.status, 'ok')
        self.assertEqual({e.kindergarten_id for e in result.evidence}, {str(first['kindergarten_id'])})
        result = await service.retrieve(RagQuery(city='Zagreb',name='Primjer',topics=['programs'],feature_id=str(uuid4())))
        self.assertEqual(result.status, 'not_found')

    async def test_missing_topic_does_not_fall_back_to_unrelated_programs_or_vacancies(self):
        service = self.service([row()])
        result = await service.retrieve(RagQuery(city='Zagreb',name='Primjer',topics=['document']))
        self.assertEqual(result.status, 'no_evidence')
        self.assertFalse(result.evidence)
        self.search.retrieve_context.assert_awaited_once()

    async def test_documents_are_read_only_when_requested(self):
        service = self.service([row()])
        await service.retrieve(RagQuery(city='Zagreb',name='Primjer',topics=['programs','vacancies']))
        self.search.retrieve_context.assert_not_awaited()
        await service.retrieve(RagQuery(city='Zagreb',name='Primjer'))
        call = self.search.retrieve_context.await_args.kwargs
        self.assertTrue(call['all_documents'])
        self.assertNotIn('text', call)  # Documents are filtered by scope, never by question terms.

    async def test_chunks_stay_within_selected_owner_and_exact_facility(self):
        first = row(); sibling = deepcopy(first); sibling['location_id'] = uuid4()
        program = uuid4()
        first['programs'] = [dict(program_id=str(program),name='Montessori',min_age_months=12,
            max_age_months_exclusive=36,verified_on='2026-11-04',valid_until=None,
            scope='facility',source_title='Current',source_url='https://example.invalid/current')]
        base = dict(kindergarten_id=first['kindergarten_id'],location_id=first['location_id'],
            content='Dokumenti za upis: potvrda.',source_url='https://example.invalid/instructions',
            source_title='Synthetic instructions',observed_on=None)
        chunks = [base,dict(base,kindergarten_id=uuid4()),dict(base,location_id=uuid4()),
                  dict(base,location_id=None,content='Upis: upute ustanove.')]
        service = self.service([first,sibling], chunks)
        result = await service.retrieve(RagQuery(city='Zagreb',name='Primjer',topics=['document'],feature_id=str(first['location_id'])))
        self.assertEqual(len(result.evidence),2)
        self.assertEqual({e.topic for e in result.evidence},{'document'})
        self.assertTrue(all(e.temporal_status == 'undated' for e in result.evidence))
        call = self.search.retrieve_context.await_args.kwargs
        self.assertEqual(call['location_ids'],[first['location_id']])
        self.assertEqual(call['program_ids'],[str(program)])
        self.assertEqual(call['kindergarten_ids'],[])

    async def test_contacts_require_field_specific_source_evidence(self):
        item = row()
        item.update(email='office@example.invalid',phone='01 123',website_url='https://example.invalid')
        item['contact_sources'] = dict(email=dict(name='Synthetic directory',url='https://example.invalid/directory',
            license='OD',reference_date=None,scope='institution'))
        result = await self.service([item]).retrieve(RagQuery(city='Zagreb',name='Primjer',topics=['contacts']))
        evidence, = result.evidence
        self.assertEqual(evidence.content,'E-mail: office@example.invalid')
        self.assertEqual(evidence.scope,'institution')
        self.assertEqual(evidence.temporal_status,'undated')

    async def test_response_budget_never_slices_a_source_or_silently_drops_matches(self):
        item = row()
        item['historical_data'] *= 40
        result = await self.service([item]).retrieve(RagQuery(city='Zagreb',name='Primjer',topics=['programs']))
        self.assertEqual(len(result.evidence),1)  # Duplicates do not consume the response budget.
        self.assertFalse(result.truncated)
        rows = [dict(item,location_id=uuid4()) for _ in range(21)]
        result = await self.service(rows).retrieve(RagQuery(city='Zagreb',name='Primjer',topics=['programs']))
        self.assertEqual(result.status,'clarification_required')
        self.assertEqual(result.total_matches,21)
        self.assertTrue(result.truncated)

    async def test_bounded_context_preserves_complete_excerpts_and_reports_omissions(self):
        item = row()
        template = item['historical_data'][0]
        item['historical_data'] = [dict(template,programs=[f'Montessori program {i}']) for i in range(20)]
        result = await self.service([item]).retrieve(RagQuery(city='Zagreb',name='Primjer',topics=['programs']))
        self.assertEqual(len(result.evidence),20)  # Many short excerpts fit; only characters are bounded.
        self.assertFalse(result.truncated)
        item['historical_data'] = [dict(template,programs=[f'Montessori {i} ' + 'x'*2000]) for i in range(20)]
        result = await self.service([item]).retrieve(RagQuery(city='Zagreb',name='Primjer',topics=['programs']))
        self.assertLess(len(result.evidence),20)
        self.assertLessEqual(sum(len(e.content) for e in result.evidence),24_000)
        self.assertTrue(result.truncated)
        self.assertTrue(all(e.content.endswith('nisu potvrđeni ovom snimkom.') for e in result.evidence))
        item['historical_data'] = [dict(template,programs=['Montessori ' + 'x'*25000])]
        result = await self.service([item]).retrieve(RagQuery(city='Zagreb',name='Primjer',topics=['programs']))
        self.assertEqual(result.status,'no_evidence')
        self.assertTrue(result.truncated)

    def test_query_rejects_missing_city_name_unknown_topics_fields_and_invented_ids(self):
        valid = dict(city='Zagreb',name='Primjer',topics=['programs'])
        for change in (dict(city='Split'),dict(city=' '),dict(name=''),dict(topics=[]),dict(topics=['jelovnik']),
                       dict(topics='programs'),dict(feature_id='invented'),dict(extra='ignored'),
                       dict(question='Koji su programi?')):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                RagQuery.model_validate(valid | change)
        self.assertIsNone(RagQuery(city='Zagreb',name='Primjer').topics)
        self.assertEqual(RagQuery(city='Zagreb',name='Primjer',topics=['contacts','programs','contacts']).topics,
                         ['contacts','programs'])

    async def test_topics_select_evidence_with_dates_citations_and_scope(self):
        item = row()
        item.update(email='synthetic@example.invalid',phone='01 000',website_url='https://example.invalid')
        item['contact_sources'] = {key:dict(name='Synthetic directory',url='https://example.invalid/directory',
            license='OD',reference_date=None,scope='institution') for key in ('email','phone','website_url')}
        item['subsidy_policies'] = [dict(policy_key='synthetic',title='Synthetic municipal policy',
            summary='Gradsko sufinanciranje iznosi 10 €.',verification_status='partial',verified_on='2026-11-04',
            valid_from='2026-01-01',valid_until='2026-12-31',
            rules=dict(funding_model='city_subsidy', rates=[dict(city_subsidy_cents=1000)],
                       eligibility=['Pravo treba provjeriti kod Grada.']),
            sources=[dict(title='Synthetic policy',url='https://example.invalid/subsidy')])]
        chunk = dict(kindergarten_id=item['kindergarten_id'],location_id=item['location_id'],
            content='Upis: prijave do 15. svibnja.',source_url='https://example.invalid/enrolment',
            source_title='Synthetic enrolment',observed_on=None)
        service = self.service([item], [chunk])
        everything = ['programs','vacancies','subsidies','contacts','document']
        cases = [[topic] for topic in everything] + [['subsidies','contacts'],['document','programs'],None]
        for topics in cases:
            with self.subTest(topics=topics):
                result = await service.retrieve(RagQuery(city='Zagreb',name='Primjer',topics=topics))
                self.assertEqual(result.status,'ok')
                self.assertEqual({e.topic for e in result.evidence},set(topics or everything))
                order = [everything.index(e.topic) for e in result.evidence]
                self.assertEqual(order,sorted(order))  # Stable topic order regardless of request order.
                for e in result.evidence:
                    self.assertEqual(e.kindergarten_id,str(item['kindergarten_id']))
                    self.assertEqual(e.applies_to,[str(item['location_id'])])
                    self.assertTrue(e.citation_id.startswith('E'))
                    self.assertTrue(e.sources)
                    self.assertTrue(all(s.url.startswith('https://example.invalid/') for s in e.sources))
                    if e.topic in ('programs','vacancies'):
                        self.assertEqual(e.temporal_status,'historical')
                        self.assertEqual(e.reference_date.isoformat(),'2019-10-09' if e.topic=='programs' else '2025-01-01')
                        self.assertEqual(e.scope,'facility' if e.topic=='programs' else 'institution')
