import { useMemo, useState } from 'react'
import { KindergartenExplorer } from '../../shared/explorer/KindergartenExplorer'
import type { HostFullscreen } from '../../shared/explorer/FullscreenFrame'
import type { MapRoute } from '../../shared/map/RouteLayer'
import { CommuteDetails } from './CommuteDetails'
import { time } from './time'
import type { CommuteResult } from './types'
import '../welcome/welcome.css'

// CommuteView adds ranked journeys to the same explorer used by city searches.
export function CommuteView({ result, onSelect, hostFullscreen }: {
  result: CommuteResult; onSelect?: (id: string) => void; hostFullscreen?: HostFullscreen
}) {
  const [selection, setSelection] = useState<string | null>(result.results[0]?.facility_id ?? null)
  const option = result.results.find(r => r.facility_id === selection) ?? result.results[0]
  const route = useMemo<MapRoute | null>(() => option ? {
    home: [result.home.lon, result.home.lat], work: [result.work.lon, result.work.lat],
    legs: option.journeys.flatMap(journey => journey.legs),
  } : null, [result, option])
  const select = (id: string | null) => {
    setSelection(id)
    if (id) onSelect?.(id)
  }
  return <KindergartenExplorer data={result.locations} status="ready" selectedId={selection}
    onSelect={select} retry={() => {}} route={route} hostFullscreen={hostFullscreen}
    emptyNotice="Nema dostupnog puta za zadane kriterije. Promijeni lokacije, datum ili način putovanja u razgovoru."
    summary={feature => {
      const index = result.results.findIndex(item => item.facility_id === feature.id)
      const item = result.results[index]
      return `${index === 0 ? 'Najbolja opcija' : `Alternativa ${index}`} · ${Math.ceil(item.elapsed_seconds / 60)} min · dolazak ${time(item.arrival)}`
    }}
    mapNotice={option && <p className="map-data-message" role="status">
      {option.name} · dolazak {time(option.arrival)} · predaja {result.dropoff_minutes} min
    </p>}
    details={option && <CommuteDetails key={option.facility_id} result={result}
      option={option} onClose={() => select(null)} />} />
}
