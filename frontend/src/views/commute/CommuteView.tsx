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
  result: CommuteResult; onSelect?: (id: string | null) => void; hostFullscreen?: HostFullscreen
  openLink?: (url: string) => void
}) {
  // Each choice is a new object, so picking any option, even the shown one,
  // gives the map a new route and draws it again.
  const [pick, setPick] = useState<{ id: string | null }>({ id: result.results[0]?.facility_id ?? null })
  const selection = pick.id
  const [tab, setTab] = useState<CommuteTab>('route')
  const option = result.results.find(r => r.facility_id === selection) ?? result.results[0]
  const feature = result.locations.features.find(item => item.id === option?.facility_id)
  const route = useMemo<MapRoute | null>(() => {
    const chosen = result.results.find(r => r.facility_id === pick.id) ?? result.results[0]
    return chosen ? {
      home: [result.home.lon, result.home.lat], work: [result.work.lon, result.work.lat],
      legs: chosen.journeys.flatMap(journey => journey.legs),
    } : null
  }, [result, pick])
  const select = (id: string | null) => {
    setPick({ id })
    onSelect?.(id)
  }
  return <KindergartenExplorer data={result.locations} status="ready" selectedId={selection}
    onSelect={select} retry={() => {}} route={route} hostFullscreen={hostFullscreen} openLink={openLink}
    emptyNotice="Nema dostupnog puta za zadane kriterije. Promijeni lokacije, datum ili način putovanja u razgovoru."
    summary={feature => {
      const index = result.results.findIndex(item => item.facility_id === feature.id)
      const item = result.results[index]
      return `${index === 0 ? 'Najbolja opcija' : `Alternativa ${index}`} · ${Math.ceil(item.elapsed_seconds / 60)} min · dolazak ${time(item.arrival)}`
    }}
    mapNotice={option && <RouteSummary result={result} option={option} onSelect={select} />}
    details={option && feature && <CommuteDetails result={result} option={option} feature={feature}
      tab={tab} onTab={setTab} onClose={() => select(null)} openLink={openLink} />} />
}
