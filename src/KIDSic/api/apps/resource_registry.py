"""ResourceRegistry dispatches multiple independently cached MCP UI resources."""


class ResourceRegistry:
    def __init__(self, resources):
        self._resources = resources

    def register(self, server):
        server.list_resources()(self.list_resources)
        server.read_resource()(self.read_resource)

    async def list_resources(self):
        result = []
        for resource in self._resources:
            result.extend(await resource.list_resources())
        return result

    async def read_resource(self, uri):
        for resource in self._resources:
            if str(uri) == resource.uri:
                return await resource.read_resource(uri)
        raise ValueError('Nepoznat UI resurs.')
