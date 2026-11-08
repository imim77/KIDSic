"""MCP session support exercises the real ASGI transport and SDK handshake."""

from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from KIDSic.api.mcp_server import create_app


@asynccontextmanager
async def connected(service, rag_service=None, commute_service=None):
    with TemporaryDirectory() as directory:
        asset = Path(directory) / "mcp.html"
        asset.write_text("<html><body>KIDSic map</body></html>")
        app = create_app(
            service,
            ui_path=asset,
            rag_service=rag_service,
            commute_service=commute_service,
        )
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url="http://localhost"
            ) as http,
            streamable_http_client("http://localhost/mcp", http_client=http) as (
                read,
                write,
                _,
            ),
            ClientSession(read, write) as session,
        ):
            initialized = await session.initialize()
            yield session, initialized
