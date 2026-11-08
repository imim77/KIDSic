"""Tool result builders give every MCP tool the same error and payload shapes."""
import json

from mcp import types


def text_error(message: str, meta: dict | None = None) -> types.CallToolResult:
    """text_error returns plain guidance the host model can relay to the user."""
    return types.CallToolResult(isError=True, _meta=meta,
                                content=[types.TextContent(type='text', text=message)])


def coded_error(code: str, message: str, meta: dict | None = None) -> types.CallToolResult:
    """coded_error returns a machine-readable code beside the guidance."""
    return text_error(json.dumps({'code': code, 'message': message}, ensure_ascii=False), meta)


def json_result(payload: dict, meta: dict | None = None) -> types.CallToolResult:
    """json_result mirrors structured content as text for hosts without it."""
    return types.CallToolResult(structuredContent=payload, _meta=meta,
        content=[types.TextContent(type='text', text=json.dumps(payload, ensure_ascii=False))])
