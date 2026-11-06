import { CommuteView } from '../../../Commute/components/CommuteView'
import { KindergartenExplorer } from '../../components/KindergartenExplorer'
import type { McpLocationsViewModel } from '../../hooks/use-mcp-locations'
import './mcp.css'

// McpLocationView renders whichever result the host sent last: a ranked
// commute, its progress notice, or the city search.
export function McpLocationView({ expanded, fullscreen, openLink, commute, search }: McpLocationsViewModel) {
  const mode = expanded ? 'fullscreen' : 'inline'
  if (commute) return <main className="mcp-location-app w-full overflow-hidden" data-display-mode={mode} aria-label="Vrtići na putu do posla">
    {commute.result
      ? <CommuteView key={commute.revision} result={commute.result} hostFullscreen={fullscreen} openLink={openLink} onSelect={commute.selectRoute} />
      : <KindergartenExplorer data={null} status="loading" selectedId={null} onSelect={() => {}} notice={commute.notice} hostFullscreen={fullscreen} />}
  </main>

  const { label, select, ...explorer } = search
  return <main className="mcp-location-app w-full overflow-hidden" data-display-mode={mode} aria-label={label}>
    <KindergartenExplorer {...explorer} onSelect={select} openLink={openLink} hostFullscreen={fullscreen} />
  </main>
}
