"""McpServer owns transport lifetime; tools and resources own protocol presentation."""
from contextlib import asynccontextmanager
import os
import httpx
from pathlib import Path
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Route
from KIDSic.api.apps.map_resource import MapResource, SERVER_INSTRUCTIONS, UI_URI, UI_MIME  # noqa: F401 - re-exported
from KIDSic.api.commute_tools import CommuteTools
from KIDSic.integrations.concrete.address import LocalAddressLookup
from KIDSic.integrations.concrete.otp import OtpJourneyPlanner
from KIDSic.services.concrete.day_route import DayRouteService
from KIDSic.services.concrete.commute import CommuteService
from KIDSic.api.location_tools import LocationTools
from KIDSic.api.rag_tools import RagTools
from KIDSic.api.tool_registry import ToolRegistry
from KIDSic.config.settings import Settings
from KIDSic.config.routing import ROUTING_CITIES
from KIDSic.services.dependency import DependencyService
from KIDSic.services.interfaces.location import LocationServiceInterface
from KIDSic.services.interfaces.rag import RagServiceInterface


class McpHttpEndpoint:
    def __init__(self, manager):
        self._manager = manager

    async def __call__(self, scope, receive, send):
        await self._manager.handle_request(scope, receive, send)


class McpServer:
    """McpServer shares one caller-supplied or lifetime-owned service across requests."""
    def __init__(self, service: LocationServiceInterface | None = None,
                 ui_path: Path | str | None = None, rag_service: RagServiceInterface | None = None,
                 commute_service=None):
        self._provided_commute, self._commute = commute_service, None
        self._provided_service = service
        self._locations = None
        self._provided_rag, self._rag = rag_service, None
        asset = Path(ui_path) if ui_path is not None else Path(os.environ.get('KIDSIC_UI_PATH', 'frontend/dist/mcp.html'))
        self._resource = MapResource(asset)
        self.server = Server('KIDSic', version='0.1.0', instructions=SERVER_INSTRUCTIONS)
        self._resource.register(self.server)
        ToolRegistry([LocationTools(self._location_service), RagTools(self._rag_service), CommuteTools(self._commute_service)]).register(self.server)
        self._manager = StreamableHTTPSessionManager(self.server, stateless=True, json_response=True)
        self.app = Starlette(routes=[Route('/mcp', McpHttpEndpoint(self._manager),
                                          methods=['GET','POST','DELETE'])], lifespan=self._lifespan)

    @staticmethod
    def _opened(service, name: str):
        if service is None:
            raise RuntimeError(f'{name} service is not open.')
        return service

    def _location_service(self) -> LocationServiceInterface:
        return self._opened(self._locations, 'Location')

    def _rag_service(self) -> RagServiceInterface:
        return self._opened(self._rag, 'RAG')

    def _commute_service(self, city: str):
        return self._opened(self._commute, 'Commute')[city]

    @asynccontextmanager
    async def _lifespan(self, app):
        try:
            self._resource.load()
            async with self._conversation_services() as (self._locations, self._rag), \
                    self._commute_lifetime(), self._manager.run():
                yield
        finally:
            self._locations = None
            self._rag = None
            self._commute = None
            self._resource.close()

    @asynccontextmanager
    async def _conversation_services(self):
        """_conversation_services prefers caller-supplied services, so tests
        and embedders run without opening a database pool."""
        if self._provided_service is not None:
            yield self._provided_service, self._provided_rag
        else:
            async with DependencyService(Settings.from_env()).conversation_services() as services:
                yield services

    @asynccontextmanager
    async def _commute_lifetime(self):
        async with httpx.AsyncClient(timeout=20, trust_env=False) as http:
            self._commute = {city.name: self._provided_commute or CommuteService(
                DayRouteService(self._locations, OtpJourneyPlanner(http, city.otp_url())),
                LocalAddressLookup(city.address_index(), city.name)) for city in ROUTING_CITIES.values()}
            yield


def create_app(service: LocationServiceInterface | None = None,
               ui_path: Path | str | None = None, rag_service: RagServiceInterface | None = None,
               commute_service=None) -> Starlette:
    return McpServer(service, ui_path, rag_service, commute_service).app
