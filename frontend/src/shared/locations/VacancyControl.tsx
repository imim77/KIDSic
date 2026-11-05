import { Users } from 'lucide-react'
import { vacancyDate } from './vacancies'

interface VacancyControlProps {
  value: boolean
  date: string | null // Newest published snapshot in the city, shown so the filter never looks live.
  onChange: (value: boolean) => void
}

// VacancyControl keeps only kindergartens whose newest published snapshot lists
// a free place. The snapshot date sits on the control itself.
export function VacancyControl({ value, date, onChange }: VacancyControlProps) {
  return <button type="button" className="vacancy-control" aria-pressed={value} onClick={() => onChange(!value)}>
    <Users aria-hidden="true" />
    Slobodna mjesta
    {date && <>{' '}<span className="vacancy-control-date">stanje {vacancyDate(date)}</span></>}
  </button>
}
