import { Bus, ChevronDown, ChevronLeft, ChevronRight, Footprints } from 'lucide-react'
import { Disclosure } from '../../shared/motion/Disclosure'
import type { CommuteOption, CommuteResult } from './types'
import { time } from './time'
import './commute.css'

const minutes = (seconds: number) => Math.ceil(seconds / 60)

// RouteSummary condenses the selected route into a map overlay that opens on
// demand. Its arrows step through the ranked options right beside the route
// they redraw, in every layout, also when the details column is closed.
export function RouteSummary({ result, option, onSelect }: {
  result: CommuteResult; option: CommuteOption; onSelect: (id: string) => void
}) {
  const rank = result.results.indexOf(option)
  const count = result.results.length
  // Wrapping around means the arrows are never disabled under the pointer.
  const step = (by: number) => onSelect(result.results[(rank + by + count) % count].facility_id)
  const extra = option.extra_seconds == null ? null
    : `${option.extra_seconds >= 0 ? '+' : ''}${minutes(option.extra_seconds)} min uz put`
  return <div className="route-summary" role="region" aria-label={`Ruta: ${option.name}`} data-stepper={count > 1 ? '' : undefined}>
    {/* Outside the summary: buttons inside it would also toggle the card. */}
    {count > 1 && <div className="route-option-nav" role="group" aria-label="Rangirane opcije">
      <button type="button" aria-label="Prethodna opcija" onClick={() => step(-1)}><ChevronLeft aria-hidden="true" /></button>
      <span aria-live="polite">{rank + 1} / {count}</span>
      <button type="button" aria-label="Sljedeća opcija" onClick={() => step(1)}><ChevronRight aria-hidden="true" /></button>
    </div>}
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
