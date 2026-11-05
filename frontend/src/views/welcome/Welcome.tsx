import { useState } from 'react'
import { KindergartenExplorer } from '../../shared/explorer/KindergartenExplorer'
import { useLocations } from '../../shared/locations/useLocations'
import { initialLocationFilters, type Nearby } from '../../shared/locations/types'
import './welcome.css'

function App() {
  const [selection, setSelection] = useState<string | null>(null)
  const [nearby, setNearby] = useState<Nearby | null>(null)
  const { status, data, retry } = useLocations({ ...initialLocationFilters, nearby })
  const selectedId = data?.features.some((feature) => feature.id === selection) ? selection : null
  return (
    <main className="w-full h-dvh overflow-hidden p-2" aria-label="Karta vrtićkih objekata">
      <KindergartenExplorer data={data} status={status} selectedId={selectedId} onSelect={setSelection} retry={() => { setSelection(null); retry() }}
        nearby={{ value: nearby, onChange: setNearby }} />
    </main>
  )
}

export default App
