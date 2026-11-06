import { useRef, type ReactNode } from 'react'
import { Baby, BriefcaseBusiness, Bus, Footprints, House, MapPin } from 'lucide-react'
import { useEntrance } from '@/mvvm/hooks/use-entrance'
import { formatTime as time } from '@/mvvm/utils/format'
import { rankLabel } from '../utils/rank'
import type { CommuteLeg, CommuteOption, CommuteResult } from '../types'

const minutes = (from: string, to: string) => Math.max(0, Math.ceil((Date.parse(to) - Date.parse(from)) / 60_000))

// Step is one timetable row: a time, a marker on the rail and what happens.
function Step({ at, kind, icon, title, children }: {
  at: string; kind: string; icon: ReactNode; title: ReactNode; children?: ReactNode
}) {
  return <li className="route-step" data-kind={kind}>
    <time className="route-step-time" dateTime={at}>{time(at)}</time>
    <span className="route-step-marker" aria-hidden="true">{icon}</span>
    <div className="route-step-text"><p className="route-step-title">{title}</p>{children}</div>
  </li>
}

// RouteDetails lays the selected journey out as a timetable, with the
// figures a parent decides on (arrival, total time, transfers) up front.
export function RouteDetails({ result, option, rank }: { result: CommuteResult; option: CommuteOption; rank: number }) {
  const body = useRef<HTMLDivElement>(null)
  // Replays per option; the panel stays mounted while the map arrows step.
  useEntrance(body, [option.facility_id], { selector: '.route-details > *, .route-step', limit: 18 })
  const [toKindergarten, toWork] = option.journeys
  // OTP names the journey ends Origin and Destination; name them for people.
  // The kindergarten is the heading already, so steps just call it Vrtić.
  const place = (name: string, leg: number) => name === 'Origin' ? (leg === 0 ? 'Dom' : 'Vrtić')
    : name === 'Destination' ? (leg === 0 ? 'Vrtić' : 'Posao') : name
  const legs = (legs: CommuteLeg[], journey: number) => legs.map((leg, i) => {
    const walk = leg.mode === 'WALK'
    return <Step key={`${journey}-${i}`} at={leg.departure} kind={walk ? 'walk' : 'transit'}
      icon={walk ? <Footprints /> : <Bus />}
      title={<>{walk ? 'Pješice' : <span className="route-line">Linija {leg.line ?? leg.mode}</span>}
        <span className="route-step-duration">{minutes(leg.departure, leg.arrival)} min</span></>}>
      <p className="route-step-path">{place(leg.from_name, journey)} → {place(leg.to_name, journey)}</p>
    </Step>
  })
  const extra = option.extra_seconds
  return <div className="location-details-scroll"><div ref={body} className="location-details-body route-details">
    <span className="route-rank" data-best={rank === 0 ? '' : undefined}>{rankLabel(rank)}</span>
    <h2>{option.name}</h2>
    <p className="location-details-address"><MapPin aria-hidden="true" /><span>{option.address}</span></p>

    <dl className="route-stats">
      <div><dt>Na poslu</dt><dd>{time(option.arrival)}</dd></div>
      <div><dt>Ukupno</dt><dd>{Math.ceil(option.elapsed_seconds / 60)} min</dd></div>
      <div><dt>Presjedanja</dt><dd>{option.transfers}</dd></div>
    </dl>
    <p className="route-facts">
      <span>Polazak {time(result.departure)}</span>
      <span>{result.mode === 'TRANSIT' ? 'Javni prijevoz i hodanje' : 'Pješice'}</span>
      <span>{extra == null ? 'Izravan put nije dostupan'
        : `${extra >= 0 ? '+' : '−'}${Math.ceil(Math.abs(extra) / 60)} min prema izravnom putu`}</span>
    </p>

    <h3>Plan puta</h3>
    <ol className="route-timeline">
      <Step at={toKindergarten.departure} kind="stop" icon={<House />} title="Polazak od kuće" />
      {legs(toKindergarten.legs, 0)}
      <Step at={toKindergarten.arrival} kind="dropoff" icon={<Baby />} title="Predaja u vrtiću">
        <p className="route-step-path">Do {time(toWork.departure)} · predaja {result.dropoff_minutes} min uračunata</p>
      </Step>
      {legs(toWork.legs, 1)}
      <Step at={toWork.arrival} kind="finish" icon={<BriefcaseBusiness />} title="Dolazak na posao" />
    </ol>

    <p className="location-details-note">Vozni red: {result.sources.publisher} · {result.sources.license}.
      {' '}Preuzeto {result.sources.retrieved_on}; razdoblje {result.sources.service_start} – {result.sources.service_end}.
      {' '}Planirani polasci, bez podataka o kašnjenjima.</p>

    {result.city === 'Šibenik' && <p className="location-details-note">Popis šibenskih objekata nije potpun; uspoređuju se samo dostupni mapirani objekti. Autobusna geometrija povezuje stajališta.</p>}

    {option.journeys.some(journey => journey.legs.some(leg => !leg.geometry))
      && <p className="location-details-note">Dio puta nema geometriju pa nije ucrtan na karti.</p>}
  </div></div>
}
