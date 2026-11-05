import { useEffect, useRef } from 'react'
import { Bus, Footprints, X } from 'lucide-react'
import { Button } from '../../shared/ui/button'
import type { CommuteOption, CommuteResult } from './types'

import { time } from './time'

// CommuteDetails explains the selected route in the explorer's details column.
export function CommuteDetails({ result, option, onClose }: {
  result: CommuteResult; option: CommuteOption; onClose: () => void
}) {
  const panel = useRef<HTMLElement>(null)
  useEffect(() => { panel.current?.focus({ preventScroll: true }) }, [])
  const rank = result.results.indexOf(option)
  return <section ref={panel} tabIndex={-1} className="location-details" role="region" aria-label={`Ruta: ${option.name}`}>
    <div className="location-details-scroll"><div className="location-details-body">
      <Button variant="outline" size="icon" aria-label="Zatvori detalje rute" onClick={() => {
        const rows = panel.current?.closest('.kindergarten-explorer')?.querySelectorAll<HTMLElement>('[data-location-row], [data-location-card]')
        Array.from(rows ?? []).find(row => (row.dataset.locationRow ?? row.dataset.locationCard) === option.facility_id)?.focus({ preventScroll: true })
        onClose()
      }}><X /></Button>
      <p>{rank === 0 ? 'Najbolja opcija' : `Alternativa ${rank}`}</p>
      <h2>{option.name}</h2><p>{option.address}</p>
      <p>Polazak {time(result.departure)} · {result.mode === 'TRANSIT' ? 'javni prijevoz + hodanje' : 'pješice'} · predaja {result.dropoff_minutes} min</p>
      <p>Dolazak {time(option.arrival)} · {Math.ceil(option.elapsed_seconds / 60)} min · {option.transfers} presjedanja</p>
      <p>{option.extra_seconds == null ? 'Izravan put nije dostupan.' : `${option.extra_seconds >= 0 ? '+' : ''}${Math.ceil(option.extra_seconds / 60)} min prema izravnom putu.`}</p>
      {option.journeys.map((journey, index) => <section key={index}>
        <h3>{index === 0 ? 'Dom → vrtić' : 'Vrtić → posao'} · {time(journey.departure)}–{time(journey.arrival)}</h3>
        {journey.legs.map((leg, i) => <p key={i}>
          {leg.mode === 'WALK' ? <Footprints aria-hidden="true" size={15} /> : <Bus aria-hidden="true" size={15} />}{' '}
          {time(leg.departure)} {leg.mode === 'WALK' ? 'Pješice' : `Linija ${leg.line ?? leg.mode}`} ·{' '}
          {leg.from_name === 'Origin' ? (index === 0 ? 'Dom' : option.name) : leg.from_name} →{' '}
          {leg.to_name === 'Destination' ? (index === 0 ? option.name : 'Posao') : leg.to_name}
        </p>)}
      </section>)}
      {option.journeys.some(journey => journey.legs.some(leg => !leg.geometry)) && <p>Geometrija dijela puta nije dostupna; karta prikazuje samo dostupne dionice.</p>}
      <p>{result.notice}</p>
      <p>Uspoređeno {result.searched} objekata · dostupna ruta za {result.reachable} · bez rute {result.without_route} · izvan mapirane pokrivenosti {result.excluded}.</p>
      <p>Vozni red {result.sources.service_start} – {result.sources.service_end}, bez kašnjenja uživo. Radno vrijeme, dobna prikladnost i mjesta nisu potvrđeni.</p>
      <p>GTFS: vekejsn, CC-BY-4.0 · karta i adrese © OpenStreetMap contributors, ODbL.</p>
    </div></div>
  </section>
}
