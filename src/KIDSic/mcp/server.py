"""Compatibility entry point; MCP presentation now lives with the other API adapters."""
from KIDSic.api.mcp_server import create_app, UI_URI, UI_MIME

__all__ = ['create_app', 'UI_URI', 'UI_MIME']
