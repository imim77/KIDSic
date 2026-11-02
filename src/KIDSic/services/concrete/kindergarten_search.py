"""Coordinate filtering and RAG inside one caller-owned snapshot."""
from KIDSic.dto.search import Recommendation
from KIDSic.services.interfaces.kindergarten_search import KindergartenSearchServiceInterface
from KIDSic.services.concrete.request_parser import parse_request


class KindergartenSearchService(KindergartenSearchServiceInterface):
    def __init__(self, uow_factory):
        self._uow_factory = uow_factory

    async def recommend(self, question: str, *, embedding=None, embedding_model=None, as_of=None) -> Recommendation:
        """Return retrieval evidence, not an unconstrained generated answer or enrolment promise."""
        async with self._uow_factory() as uow:
            criteria = await parse_request(uow.search, question)
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
