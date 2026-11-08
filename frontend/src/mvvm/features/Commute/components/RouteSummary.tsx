import { ChevronLeft, ChevronRight } from 'lucide-react'
import { rankLabel } from '../utils/rank'




export function RouteSummary({ name, rank, count, onStep }: {
  name: string; rank: number; count: number; onStep: (by: number) => void
}) {
  return <div className="route-summary" role="region" aria-label={`Ruta: ${name}`}>
    <p className="route-summary-title">
      <span className="route-summary-rank">{rankLabel(rank)}</span>
      <span className="route-summary-name" title={name}>{name}</span>
    </p>
    {count > 1 && <div className="route-option-nav" role="group" aria-label="Rangirane opcije">
      <button type="button" aria-label="Prethodna opcija" onClick={() => onStep(-1)}><ChevronLeft aria-hidden="true" /></button>
      <span aria-live="polite">{rank + 1} / {count}</span>
      <button type="button" aria-label="Sljedeća opcija" onClick={() => onStep(1)}><ChevronRight aria-hidden="true" /></button>
    </div>}
  </div>
}
