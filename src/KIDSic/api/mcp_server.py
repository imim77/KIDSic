"""McpServer owns transport lifetime; tools and resources own protocol presentation."""
from contextlib import asynccontextmanager
import httpx
from pathlib import Path
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Route
from KIDSic.api.apps.map_resource import MapResource, SERVER_INSTRUCTIONS, UI_URI, UI_MIME  # noqa: F401 - re-exported
from KIDSic.api.commute_tools import CommuteTools
from KIDSic.factories.commute import CommuteServiceFactory
from KIDSic.api.location_tools import LocationTools
from KIDSic.api.rag_tools import RagTools
from KIDSic.api.tool_registry import ToolRegistry
from KIDSic.config.settings import Settings
from KIDSic.config.routing import ROUTING_CITIES
from KIDSic.services.interfaces.commute import CommuteServiceInterface
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
                 commute_service: CommuteServiceInterface | None = None):
        self._provided_commute, self._commute = commute_service, None
        self._provided_service = service
        self._locations = None
        self._provided_rag, self._rag = rag_service, None
        asset = Path(ui_path) if ui_path is not None else Path('frontend/dist/mcp.html')
        self._resource = MapResource(asset)
        self._server = Server('KIDSic', version='0.1.0', instructions=SERVER_INSTRUCTIONS)
        self._resource.register(self._server)
        ToolRegistry([LocationTools(self._location_service), RagTools(self._rag_service), CommuteTools(self._commute_service)]).register(self._server)
        self._manager = StreamableHTTPSessionManager(self._server, stateless=True, json_response=True)
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
            # A caller-supplied service answers for every city.
            self._commute = ({city: self._provided_commute for city in ROUTING_CITIES}
                             if self._provided_commute is not None
                             else CommuteServiceFactory().create(self._locations, http))
            yield


def create_app(service: LocationServiceInterface | None = None,
               ui_path: Path | str | None = None, rag_service: RagServiceInterface | None = None,
               commute_service: CommuteServiceInterface | None = None) -> Starlette:
    return McpServer(service, ui_path, rag_service, commute_service).app
