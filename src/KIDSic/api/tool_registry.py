"""ToolRegistry installs one MCP dispatch handler for independent tool contracts."""
from KIDSic.api.tool_results import text_error


class ToolRegistry:
    def __init__(self, handlers):
        self._handlers = tuple(handlers)
        self._routes = {}

    def register(self, server):
        server.list_tools()(self.list_tools)
        server.call_tool(validate_input=False)(self.call_tool)

    async def list_tools(self):
        result, routes = [], {}
        for handler in self._handlers:
            for tool in await handler.list_tools():
                if tool.name in routes:
                    raise ValueError(f'Duplicate MCP tool: {tool.name}')
                routes[tool.name] = handler
                result.append(tool)
        self._routes = routes
        return result

    async def call_tool(self, name, arguments):
        if not self._routes:
            await self.list_tools()
        if name not in self._routes:
            return text_error('Nepoznat alat. Dohvati tools/list i odaberi objavljeni naziv alata.')
        return await self._routes[name].call_tool(name, arguments)
