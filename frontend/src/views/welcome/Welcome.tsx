import { useState } from 'react'
import { KindergartenExplorer } from '../../shared/explorer/KindergartenExplorer'
import { useLocations } from '../../shared/locations/useLocations'
import { initialLocationFilters, type Nearby } from '../../shared/locations/types'
import './welcome.css'

function App() {
  const [selection, setSelection] = useState<string | null>(null)
  const [nearby, setNearby] = useState<Nearby | null>(null)
  const filters = { ...initialLocationFilters, nearby }
  const { status, data, retry } = useLocations(filters)
  const selectedId = data?.features.some((feature) => feature.id === selection) ? selection : null
  return (
    <main className="w-full h-dvh overflow-hidden p-2" aria-label="Karta vrtićkih objekata">
      <KindergartenExplorer data={data} status={status} selectedId={selectedId} onSelect={setSelection} retry={() => { setSelection(null); retry() }}
        nearby={{ value: nearby, onChange: setNearby }} criteria={{ city: filters.city, nearby }} />
    </main>
  )
}

export default App
