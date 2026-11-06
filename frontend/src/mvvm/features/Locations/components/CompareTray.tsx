import { Scale, X } from 'lucide-react'
import { comparisonLimit } from '../utils/comparison'

interface CompareTrayProps {
  count: number
  onOpen: () => void
  onClear: () => void
}

// CompareTray keeps the chosen options visible while parents keep browsing.
export function CompareTray({ count, onOpen, onClear }: CompareTrayProps) {
  return <section className="compare-tray" aria-label="Usporedba">
    <Scale aria-hidden="true" />
    <span>Usporedba {count}/{comparisonLimit}</span>
    <button type="button" className="compare-tray-open" onClick={onOpen} disabled={count < 2}
      title={count < 2 ? 'Dodajte još barem jedan vrtić' : undefined}>Usporedi</button>
    <button type="button" className="compare-tray-clear" onClick={onClear} aria-label="Očisti usporedbu"><X aria-hidden="true" /></button>
  </section>
}
