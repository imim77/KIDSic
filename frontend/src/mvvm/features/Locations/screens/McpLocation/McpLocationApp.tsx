import { useMcpLocations } from '../../hooks/use-mcp-locations'
import { McpLocationView } from './McpLocationView'



export function McpLocationApp() {
  return <McpLocationView {...useMcpLocations()} />
}
