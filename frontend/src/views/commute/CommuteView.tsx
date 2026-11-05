import { useState } from 'react'
import { Bus, Footprints } from 'lucide-react'
import { Button } from '@/shared/ui/button'
import CommuteMap from './CommuteMap'
import type { CommuteResult } from './types'
import './commute.css'

const time = (s: string) => new Intl.DateTimeFormat('hr-HR', { timeZone: 'Europe/Zagreb', hour:'2-digit', minute:'2-digit' }).format(new Date(s))

export function CommuteView({ result, onSelect }: { result: CommuteResult; onSelect?: (id: string) => void }) {
  const [selection, setSelection] = useState(result.results[0]?.facility_id ?? null)
  const option = result.results.find(r => r.facility_id === selection) ?? result.results[0]
  const geometries = option?.journeys.flatMap(j => j.legs.flatMap(l => l.geometry ? [l.geometry] : [])) ?? []
  return <section className="commute-view" aria-label="Vrtići na putu do posla">
    <header><span className="day-eyebrow">RIJEKA · TVOJE JUTRO</span><h1>Vrtić koji se uklapa u tvoj dan</h1>
      <p>Polazak {time(result.departure)} · {result.mode === 'TRANSIT' ? 'javni prijevoz + hodanje' : 'pješice'} · predaja {result.dropoff_minutes} min</p></header>
    <p className="commute-notice">{result.notice}</p>
    <CommuteMap home={result.home} work={result.work} facilities={result.results.map(r => ({id:r.facility_id,name:r.name,point:r.point}))} geometries={geometries} />
    {option && <p className="commute-map-caption">Na karti: <strong>{option.name}</strong> · dolazak {time(option.arrival)}</p>}
    <p className="day-note">Uspoređeno {result.searched} objekata · dostupna ruta za {result.reachable} · bez rute {result.without_route} · izvan mapirane pokrivenosti {result.excluded}.</p>
    {!option && <h2>Nema dostupnog puta za zadane kriterije. Promijeni lokacije, datum ili način putovanja u razgovoru.</h2>}
    <div className="commute-options">{result.results.map((r, index) => <article key={r.facility_id} className="day-result" data-selected={r.facility_id === option?.facility_id}>
      <div className="day-result-head"><div><span className="day-eyebrow">{index === 0 ? 'NAJBOLJA OPCIJA' : `ALTERNATIVA ${index}`}</span><h2>{r.name}</h2></div><strong>{Math.ceil(r.elapsed_seconds / 60)} min</strong></div>
      <p>{r.address}</p><div className="day-metrics"><span>Dolazak <b>{time(r.arrival)}</b></span><span>{r.transfers} presjedanja</span><span>{r.extra_seconds == null ? 'Izravan put nije dostupan' : `${r.extra_seconds >= 0 ? '+' : ''}${Math.ceil(r.extra_seconds / 60)} min prema izravnom putu`}</span></div>
      <Button type="button" aria-pressed={r.facility_id === option?.facility_id} aria-label={`Prikaži rutu: ${r.name}`} onClick={() => {setSelection(r.facility_id); onSelect?.(r.facility_id)}}>{r.facility_id === option?.facility_id ? 'Ruta prikazana na karti' : 'Prikaži ovu rutu'}</Button>
      {r.facility_id === option?.facility_id && r.journeys.map((j, i) => <div className="day-journey" key={i}><h3>{i === 0 ? 'Dom → vrtić' : 'Vrtić → posao'} <small>{time(j.departure)}–{time(j.arrival)}</small></h3>{j.legs.map((l,n) => <p key={n}>{l.mode === 'WALK' ? <Footprints size={15}/> : <Bus size={15}/>}<span>{time(l.departure)} {l.mode === 'WALK' ? 'Pješice' : `Linija ${l.line ?? l.mode}`} · {l.from_name === 'Origin' ? (i === 0 ? 'Dom' : r.name) : l.from_name} → {l.to_name === 'Destination' ? (i === 0 ? r.name : 'Posao') : l.to_name}</span></p>)}</div>)}
    </article>)}</div><footer className="day-footer">Rang prema dolasku na posao. Vozni red {result.sources.service_start} – {result.sources.service_end}, bez kašnjenja uživo. Radno vrijeme, dobna prikladnost i mjesta nisu potvrđeni.<br />GTFS: vekejsn, CC-BY-4.0 · karta i adrese © OpenStreetMap contributors, ODbL.</footer>
  </section>
}
