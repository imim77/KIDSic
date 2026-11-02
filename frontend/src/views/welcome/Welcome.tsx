import { KindergartenMap } from '../../shared/map/KindergartenMap'
import './welcome.css'

function App() {
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
