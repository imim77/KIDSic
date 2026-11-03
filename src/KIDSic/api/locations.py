"""create_app exposes location reads while lifespan owns the database pool."""
from contextlib import asynccontextmanager
import logging

import asyncpg
from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from KIDSic.config.settings import Settings
from KIDSic.dto.location import LocationQuery
from KIDSic.services.dependency import DependencyService
from KIDSic.services.interfaces.location import LocationServiceInterface

logger = logging.getLogger(__name__)


async def list_locations(request):
    params = dict(request.query_params)
    try:
        if len(params) != len(request.query_params.multi_items()):
            raise ValueError('Repeated query parameters are unsupported.')
        if 'bbox' in params:
            params['bbox'] = params['bbox'].split(',')
        query = LocationQuery.model_validate(params)
    except (ValidationError, ValueError):
        return JSONResponse({'error': 'invalid_query'}, status_code=422)

    try:
        result = await request.app.state.locations.list_locations(query)
    except (asyncpg.PostgresError, asyncpg.InterfaceError, OSError, TimeoutError):
        logger.exception('Location database read failed.')
        return JSONResponse({'error': 'locations_unavailable'}, status_code=503)
    return JSONResponse(result.model_dump(mode='json'), media_type='application/geo+json')


def create_app(service: LocationServiceInterface | None = None):
    @asynccontextmanager
    async def lifespan(app):
        if service is not None:
            app.state.locations = service
            yield
        else:
            dependencies = DependencyService(Settings.from_env())
            async with dependencies.location_service() as locations:
                app.state.locations = locations
                yield
        del app.state.locations

    return Starlette(routes=[Route('/api/locations', list_locations, methods=['GET'])],
                     lifespan=lifespan)
