import { Building } from 'lucide-react'

interface DistrictControlProps {
  options: string[]
  value: string
  unknown: number
  onChange: (value: string) => void
}




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
