import { useMcpLocations } from '../../hooks/use-mcp-locations'
import { McpLocationView } from './McpLocationView'

// McpLocationApp receives city and commute results exclusively through the
// MCP host bridge; it never calls the location API.
export function McpLocationApp() {
  return <McpLocationView {...useMcpLocations()} />
}
