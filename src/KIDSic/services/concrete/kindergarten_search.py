"""Coordinate filtering and RAG inside one caller-owned snapshot."""
from KIDSic.db.uow.base import UnitOfWorkFactory
from KIDSic.dto.search import Recommendation
from KIDSic.services.interfaces.kindergarten_search import KindergartenSearchServiceInterface
from KIDSic.services.concrete.request_parser import RequestParser


class KindergartenSearchService(KindergartenSearchServiceInterface):
    def __init__(self, uow_factory: UnitOfWorkFactory, request_parser: RequestParser | None = None):
        self._uow_factory = uow_factory
        self._request_parser = request_parser or RequestParser()

    async def recommend(self, question: str, *, embedding=None, embedding_model=None, as_of=None) -> Recommendation:
        """Return retrieval evidence, not an unconstrained generated answer or enrolment promise."""
        async with self._uow_factory() as uow:
            criteria = self._request_parser.parse_city_age(question, await uow.search.list_cities())
            area = self._request_parser.parse_area(question, await uow.search.list_areas(city=criteria['city']))
            if area:
                criteria['area'] = area
            options = await uow.search.find_options(**criteria, as_of=as_of, include_unknown=True)
            confirmed = [dict(row) for row in options if row['age_status'] == 'confirmed']
            unknown = [dict(row) for row in options if row['age_status'] == 'unknown']
            context = await uow.search.retrieve_context(
                location_ids=[row['location_id'] for row in confirmed if row['location_id']],
                kindergarten_ids=[row['kindergarten_id'] for row in confirmed if not row['location_id']],
                text=question, embedding=embedding, embedding_model=embedding_model,
                program_ids=[e["program_id"] for row in confirmed for e in row["age_evidence"]],
            ) if confirmed else []
            return {'criteria': criteria, 'confirmed': confirmed, 'age_unknown': unknown,
                    'context': [dict(row) for row in context],
                    'notice': 'Dobna prikladnost nije potvrda slobodnog mjesta ni upisa.'}
