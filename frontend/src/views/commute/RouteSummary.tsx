import { Bus, ChevronDown, Footprints } from 'lucide-react'
import { Disclosure } from '../../shared/motion/Disclosure'
import type { CommuteOption, CommuteResult } from './types'
import { time } from './time'
import './commute.css'

const minutes = (seconds: number) => Math.ceil(seconds / 60)

// RouteSummary condenses the selected route into a map overlay that opens on
// demand, so the details column stays free for the kindergarten itself.
export function RouteSummary({ result, option }: { result: CommuteResult; option: CommuteOption }) {
  const rank = result.results.indexOf(option)
  const extra = option.extra_seconds == null ? null
    : `${option.extra_seconds >= 0 ? '+' : ''}${minutes(option.extra_seconds)} min uz put`
  return <div className="route-summary" role="region" aria-label={`Ruta: ${option.name}`}>
    <Disclosure summary={<>
      <span className="route-summary-title">
        <span className="route-summary-rank">{rank === 0 ? 'Najbolja opcija' : `Alternativa ${rank}`}</span>
        <span className="route-summary-name">{option.name}</span>
        <span>Dolazak {time(option.arrival)} · {minutes(option.elapsed_seconds)} min · predaja {result.dropoff_minutes} min</span>
      </span>
      <ChevronDown className="route-summary-chevron" aria-hidden="true" size={18} />
    </>}>
      <p className="route-summary-facts">
        Polazak {time(result.departure)} · {result.mode === 'TRANSIT' ? 'bus + pješice' : 'pješice'} · {option.transfers} presjedanja{extra && ` · ${extra}`}
      </p>
      {option.journeys.map((journey, index) => <section key={index}>
        <h3>{index === 0 ? 'Dom → vrtić' : 'Vrtić → posao'} · {time(journey.departure)}–{time(journey.arrival)}</h3>
        <ol>{journey.legs.map((leg, i) => <li key={i}>
          {leg.mode === 'WALK' ? <Footprints aria-hidden="true" size={14} /> : <Bus aria-hidden="true" size={14} />}
          <span>{time(leg.departure)} {leg.mode === 'WALK' ? 'pješice' : `linija ${leg.line ?? leg.mode}`} do{' '}
            {leg.to_name === 'Destination' ? (index === 0 ? 'vrtića' : 'posla') : leg.to_name}</span>
        </li>)}</ol>
      </section>)}
      {option.journeys.some(journey => journey.legs.some(leg => !leg.geometry)) && <p>Dio puta nema geometriju pa nije na karti.</p>}
      <p className="route-summary-note">
        Uspoređeno {result.searched}, s rutom {result.reachable}. Vozni red do {result.sources.service_end}, bez kašnjenja uživo; radno vrijeme i mjesta nisu potvrđeni.
      </p>
      <p className="route-summary-note">GTFS vekejsn, CC-BY-4.0 · © OpenStreetMap contributors</p>
    </Disclosure>
  </div>
}
