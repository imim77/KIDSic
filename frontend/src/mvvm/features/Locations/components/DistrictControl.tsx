import { Building } from 'lucide-react'

interface DistrictControlProps {
  options: string[]
  value: string
  unknown: number
  onChange: (value: string) => void
}

// DistrictControl filters by the city district recorded in the sources. Objects
// without a recorded district never match, so the count of those is stated
// rather than letting a short list read as the district's full supply.
export function DistrictControl({ options, value, unknown, onChange }: DistrictControlProps) {
  return <section className="district-control" aria-label="Gradska četvrt" data-active={!!value}>
    <label>
      <Building aria-hidden="true" />
      <span>Četvrt</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Sve četvrti</option>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
    {value && unknown > 0 && <p className="district-note">Nisu uključeni objekti bez potvrđene četvrti ({unknown}).</p>}
  </section>
}
