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
        <span>Dolazak <strong>{time(option.arrival)}</strong> · <strong>{minutes(option.elapsed_seconds)} min</strong> · predaja {result.dropoff_minutes} min</span>
      </span>
      <ChevronDown className="route-summary-chevron" aria-hidden="true" size={18} />
    </>}>
      <p className="route-summary-facts">
        Polazak <strong>{time(result.departure)}</strong> · {result.mode === 'TRANSIT' ? 'bus + pješice' : 'pješice'} · <strong>{option.transfers}</strong> presjedanja{extra && <> · <strong>{extra}</strong></>}
      </p>
      {option.journeys.map((journey, index) => <section key={index}>
        <h3>{index === 0 ? 'Dom → vrtić' : 'Vrtić → posao'} · {time(journey.departure)}–{time(journey.arrival)}</h3>
        <ol>{journey.legs.map((leg, i) => <li key={i}>
          {leg.mode === 'WALK' ? <Footprints aria-hidden="true" size={14} /> : <Bus aria-hidden="true" size={14} />}
          <span><strong>{time(leg.departure)}</strong> {leg.mode === 'WALK' ? 'pješice' : <strong>linija {leg.line ?? leg.mode}</strong>} do{' '}
            {leg.to_name === 'Destination' ? (index === 0 ? 'vrtića' : 'posla') : leg.to_name}</span>
        </li>)}</ol>
      </section>)}
    </Disclosure>
  </div>
}
