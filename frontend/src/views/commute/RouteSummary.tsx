import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { CommuteOption, CommuteResult } from './types'
import './commute.css'

// RouteSummary names the option whose route the map draws and steps through
// the ranked options right beside it, in every layout. The route itself is
// told in the details column, so this card stays a one-line label.
export function RouteSummary({ result, option, onSelect }: {
  result: CommuteResult; option: CommuteOption; onSelect: (id: string) => void
}) {
  const rank = result.results.indexOf(option)
  const count = result.results.length
  // Wrapping around means the arrows are never disabled under the pointer.
  const step = (by: number) => onSelect(result.results[(rank + by + count) % count].facility_id)
  return <div className="route-summary" role="region" aria-label={`Ruta: ${option.name}`}>
    <p className="route-summary-title">
      <span className="route-summary-rank">{rank === 0 ? 'Najbolja opcija' : `Alternativa ${rank}`}</span>
      <span className="route-summary-name" title={option.name}>{option.name}</span>
    </p>
    {count > 1 && <div className="route-option-nav" role="group" aria-label="Rangirane opcije">
      <button type="button" aria-label="Prethodna opcija" onClick={() => step(-1)}><ChevronLeft aria-hidden="true" /></button>
      <span aria-live="polite">{rank + 1} / {count}</span>
      <button type="button" aria-label="Sljedeća opcija" onClick={() => step(1)}><ChevronRight aria-hidden="true" /></button>
    </div>}
  </div>
}
