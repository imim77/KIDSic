import { useState } from 'react'
import { KindergartenExplorer } from '../../shared/explorer/KindergartenExplorer'
import { useLocations } from '../../shared/locations/useLocations'
import { initialLocationFilters, type LocationCollection, type Nearby } from '../../shared/locations/types'
import './welcome.css'

// districtsOf reads the picker options from a whole-city result, so the list
// only offers districts that the sources actually record.
function districtsOf(data: LocationCollection) {
  const names = new Set(data.features.flatMap((feature) => feature.properties.district ?? []))
  return { options: [...names].sort((a, b) => a.localeCompare(b, 'hr')),
    unknown: data.features.filter((feature) => !feature.properties.district).length }
}

function App() {
  const [selection, setSelection] = useState<string | null>(null)
  const [nearby, setNearby] = useState<Nearby | null>(null)
  const [area, setArea] = useState('')
  const filters = { ...initialLocationFilters, area, nearby }
  const { status, data, retry } = useLocations(filters)
  // Filtered results would shrink the picker, so options come from the last
  // whole-city result.
  const [city, setCity] = useState<{ data: LocationCollection; options: string[]; unknown: number } | null>(null)
  if (data && !area && !nearby && city?.data !== data) setCity({ data, ...districtsOf(data) })
  const selectedId = data?.features.some((feature) => feature.id === selection) ? selection : null
  return (
    <main className="w-full h-dvh overflow-hidden p-2" aria-label="Karta vrtićkih objekata">
      <KindergartenExplorer data={data} status={status} selectedId={selectedId} onSelect={setSelection} retry={() => { setSelection(null); retry() }}
        nearby={{ value: nearby, onChange: setNearby }}
        district={city ? { options: city.options, unknown: city.unknown, value: area, onChange: setArea } : undefined}
        criteria={{ city: filters.city, area, nearby }} />
    </main>
  )
}

export default App
