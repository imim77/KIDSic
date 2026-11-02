import { KindergartenMap } from '../../shared/map/KindergartenMap'
import { useLocations } from '../../shared/locations/useLocations'
import { providerLabels } from '../../shared/locations/types'
import './welcome.css'

function App() {
  const { status, data, retry } = useLocations({ city: 'Zagreb', q: '', provider_kind: '' })
  return (
    <main className="directory">
      <header className="directory-header">
        <a className="brand" href="/" aria-label="KIDSic početna">
          <span className="brand-mark" aria-hidden="true">k.</span>KIDSic
        </a>
        <span className="city-label">Grad Zagreb</span>
      </header>
      <div className="directory-layout">
        <section className="directory-panel" aria-labelledby="directory-title">
          <p className="eyebrow">Imenik vrtićkih objekata</p>
          <h1 id="directory-title">Vrtići u<br />vašem susjedstvu.</h1>
          <p className="directory-intro">Istražite lokacije i podatke o vrtićima u Zagrebu.</p>
          <section className="location-results" aria-label="Popis objekata" aria-busy={status === 'loading'}>
            {status === 'loading' && <p role="status">Učitavanje objekata…</p>}
            {status === 'error' && <div role="alert"><p>Podatke nije moguće učitati. Provjerite vezu i pokušajte ponovno.</p><button className="text-button" onClick={retry}>Pokušaj ponovno</button></div>}
            {data && <>
              <p className="result-count">{data.metadata.total} rezultata · {data.metadata.mapped} na karti · {data.metadata.unmapped} bez koordinata</p>
              {data.features.length === 0 && <p>Za odabrani grad nema dostupnih objekata.</p>}
              <ul className="location-list">
                {data.features.map((feature) => <li key={feature.id} className="location-item">
                  <span className="provider-label">{providerLabels[feature.properties.provider_kind]}</span>
                  <h2>{feature.properties.location_name}</h2>
                  <p>{feature.properties.address ?? 'Adresa nije poznata'}</p>
                  {!feature.geometry && <small>{feature.properties.location_role === 'seat' ? 'Sjedište ustanove — lokacija pružanja usluge nije potvrđena' : 'Koordinate nisu poznate — nema prikaza na karti'}</small>}
                </li>)}
              </ul>
            </>}
          </section>
          <div className="directory-note">
            <h2>Lokacija je početak.</h2>
            <p>Broj objekata ne predstavlja broj slobodnih mjesta. Podatke o upisu provjerite izravno s vrtićem.</p>
          </div>
        </section>
        <section className="map-panel" aria-label="Karta vrtića u Zagrebu">
          <KindergartenMap />
        </section>
      </div>
    </main>
  )
}

export default App
