import { useState } from 'react'
import { KindergartenMap } from '../../shared/map/KindergartenMap'
import { useLocations } from '../../shared/locations/useLocations'
import { LocationFilters } from '../../shared/locations/LocationFilters'
import { LocationResults } from '../../shared/locations/LocationResults'
import { initialLocationFilters } from '../../shared/locations/types'
import './welcome.css'

function App() {
  const [filters, setFilters] = useState(initialLocationFilters)
  const [selection, setSelection] = useState<string | null>(null)
  const { status, data, retry } = useLocations(filters)
  const selectedId = data?.features.some((feature) => feature.id === selection) ? selection : null
  return (
    <main className="directory">
      <header className="directory-header">
        <a className="brand" href="/" aria-label="KIDSic početna">
          <span className="brand-mark" aria-hidden="true">k.</span>KIDSic
        </a>
        <span className="city-label">{filters.city}</span>
      </header>
      <div className="directory-layout">
        <section className="directory-panel" aria-labelledby="directory-title">
          <p className="eyebrow">Imenik vrtićkih objekata</p>
          <h1 id="directory-title">Vrtići u susjedstvu.</h1>
          <p className="directory-intro">Lokacije vrtića i izvori podataka.</p>
          <LocationFilters onChange={(next) => { setFilters(next); setSelection(null) }} />
          <LocationResults data={data} status={status} filters={filters} selectedId={selectedId} onSelect={setSelection} retry={() => { setSelection(null); retry() }} />
          <div className="directory-note">
            <p>Broj objekata ne predstavlja broj slobodnih mjesta. Podatke o upisu provjerite s vrtićem.</p>
          </div>
        </section>
        <section className="map-panel" aria-label="Karta vrtića">
          <KindergartenMap collection={data} selectedId={selectedId} onSelect={setSelection} />
        </section>
      </div>
    </main>
  )
}

export default App
