import { Check, Plus } from 'lucide-react'

export interface CompareChoice {
  selected: boolean
  full: boolean // The comparison already holds its limit of other options.
  onToggle: () => void
}

// CompareToggle adds an option to the comparison or takes it out again.
export function CompareToggle({ selected, full, onToggle, name, compact = false }: CompareChoice & { name: string; compact?: boolean }) {
  const label = selected ? 'U usporedbi' : full ? 'Usporedba je puna' : 'Usporedi'
  return <button type="button" className="compare-toggle" data-compact={compact} aria-pressed={selected}
    disabled={full && !selected} title={full && !selected ? 'Uklonite jedan vrtić iz usporedbe' : undefined}
    aria-label={compact ? `${selected ? 'Ukloni iz usporedbe' : 'Dodaj u usporedbu'}: ${name}` : undefined} onClick={onToggle}>
    {selected ? <Check aria-hidden="true" /> : <Plus aria-hidden="true" />}
    {!compact && label}
  </button>
}
