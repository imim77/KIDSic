import { useState } from 'react'
import { KindergartenExplorer } from '../../shared/explorer/KindergartenExplorer'
import { useLocations } from '../../shared/locations/useLocations'
import { initialLocationFilters } from '../../shared/locations/types'
import './welcome.css'

function App() {
  const [selection, setSelection] = useState<string | null>(null)
  const { status, data, retry } = useLocations(initialLocationFilters)
  const selectedId = data?.features.some((feature) => feature.id === selection) ? selection : null
  return (
    <main className="directory" aria-label="Karta vrtićkih objekata">
      <KindergartenExplorer data={data} status={status} selectedId={selectedId} onSelect={setSelection} retry={() => { setSelection(null); retry() }} />
    </main>
  )
}

export default App
