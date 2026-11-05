import { useState } from 'react'
import { KindergartenExplorer } from '../../shared/explorer/KindergartenExplorer'
import { useLocations } from '../../shared/locations/useLocations'
import { initialLocationFilters, type LocationCollection, type Nearby } from '../../shared/locations/types'
import './welcome.css'

// districtsOf reads the picker options from a whole-city result, so the list
// only offers districts that the sources actually record.
function districtsOf(data: LocationCollection) {
  const names = new Set(data.features.flatMap((feature) => feature.properties.district ?? []))
  const dates = data.features.flatMap((feature) => (feature.properties.historical_data ?? [])
    .filter((record) => record.vacancies.length).map((record) => record.reference_date))
  return { options: [...names].sort((a, b) => a.localeCompare(b, 'hr')),
    unknown: data.features.filter((feature) => !feature.properties.district).length,
    vacancyDate: dates.sort().at(-1) ?? null }
}

function App() {
  const [selection, setSelection] = useState<string | null>(null)
  const [nearby, setNearby] = useState<Nearby | null>(null)
  const [area, setArea] = useState('')
  const [hasVacancies, setHasVacancies] = useState(false)
  const filters = { ...initialLocationFilters, area, has_vacancies: hasVacancies, nearby }
  const { status, data, retry } = useLocations(filters)
  // Filtered results would shrink the picker, so options come from the last
  // whole-city result.
  const [city, setCity] = useState<{ data: LocationCollection } & ReturnType<typeof districtsOf> | null>(null)
  if (data && !area && !nearby && !hasVacancies && city?.data !== data) setCity({ data, ...districtsOf(data) })
  const selectedId = data?.features.some((feature) => feature.id === selection) ? selection : null
  return (
    <main className="w-full h-dvh overflow-hidden p-2" aria-label="Karta vrtićkih objekata">
      <KindergartenExplorer data={data} status={status} selectedId={selectedId} onSelect={setSelection} retry={() => { setSelection(null); retry() }}
        nearby={{ value: nearby, onChange: setNearby }}
        district={city ? { options: city.options, unknown: city.unknown, value: area, onChange: setArea } : undefined}
        vacancies={{ value: hasVacancies, date: city?.vacancyDate ?? null, onChange: setHasVacancies }}
        criteria={{ city: filters.city, area, has_vacancies: hasVacancies, nearby }} />
    </main>
  )
}

export default App
