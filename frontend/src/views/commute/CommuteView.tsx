import { useMemo, useState } from 'react'
import { KindergartenExplorer } from '../../shared/explorer/KindergartenExplorer'
import type { HostFullscreen } from '../../shared/explorer/FullscreenFrame'
import type { MapRoute } from '../../shared/map/RouteLayer'
import { CommuteDetails, type CommuteTab } from './CommuteDetails'
import { RouteSummary } from './RouteSummary'
import { time } from './time'
import type { CommuteResult } from './types'
import '../welcome/welcome.css'

// CommuteView adds ranked journeys to the same explorer used by city searches:
// the details column tabs between the route and the kindergarten, and the
// map card keeps a short route summary for the inline view.
export function CommuteView({ result, onSelect, hostFullscreen, openLink }: {
  result: CommuteResult; onSelect?: (id: string) => void; hostFullscreen?: HostFullscreen
  openLink?: (url: string) => void
}) {
  const [selection, setSelection] = useState<string | null>(result.results[0]?.facility_id ?? null)
  const [tab, setTab] = useState<CommuteTab>('route')
  const option = result.results.find(r => r.facility_id === selection) ?? result.results[0]
  const feature = result.locations.features.find(item => item.id === option?.facility_id)
  const route = useMemo<MapRoute | null>(() => option ? {
    home: [result.home.lon, result.home.lat], work: [result.work.lon, result.work.lat],
    legs: option.journeys.flatMap(journey => journey.legs),
  } : null, [result, option])
  const select = (id: string | null) => {
    setSelection(id)
    if (id) onSelect?.(id)
  }
  return <KindergartenExplorer data={result.locations} status="ready" selectedId={selection}
    onSelect={select} retry={() => {}} route={route} hostFullscreen={hostFullscreen} openLink={openLink}
    emptyNotice="Nema dostupnog puta za zadane kriterije. Promijeni lokacije, datum ili način putovanja u razgovoru."
    summary={feature => {
      const index = result.results.findIndex(item => item.facility_id === feature.id)
      const item = result.results[index]
      return `${index === 0 ? 'Najbolja opcija' : `Alternativa ${index}`} · ${Math.ceil(item.elapsed_seconds / 60)} min · dolazak ${time(item.arrival)}`
    }}
    mapNotice={option && <RouteSummary key={option.facility_id} result={result} option={option} />}
    details={option && feature && <CommuteDetails result={result} option={option} feature={feature}
      tab={tab} onTab={setTab} onClose={() => select(null)} openLink={openLink} />} />
}
