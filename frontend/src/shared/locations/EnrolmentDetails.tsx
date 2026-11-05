import type { MouseEvent } from 'react'
import type { EnrolmentStatus, LocationEnrolment } from './types'
import { websiteHref } from './links'

// Deadlines are Zagreb times whatever the viewer's zone.
const instant = (value: string) => new Intl.DateTimeFormat('hr-HR', { day: '2-digit', month: '2-digit',
  year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Zagreb' }).format(new Date(value))
const day = (value: string) => new Intl.DateTimeFormat('hr-HR').format(new Date(`${value}T00:00:00`))

const statusLabels: Record<EnrolmentStatus, string> = {
  open: 'Otvoreno', upcoming: 'Uskoro', closed: 'Rok završen', not_accepting: 'Upisi se ne provode',
  dates_unknown: 'Rok nije objavljen',
}
const channelLabels: Record<LocationEnrolment['channel'], string> = {
  city_system: 'Gradski sustav e-upisa', e_upisi: 'Nacionalni e-Upisi', kindergarten: 'Prema uputama vrtića',
}

function period(round: LocationEnrolment) {
  const { opens_at: opens, closes_at: closes } = round
  if (round.status === 'not_accepting') return `Prema službenom izvoru upisi u ovaj vrtić za ${round.academic_year} ne provode se.`
  if (round.status === 'closed') return `Rok je završio ${instant(closes!)}.`
  if (round.status === 'upcoming') return `Prijave od ${instant(opens!)}${closes ? ` do ${instant(closes)}` : ''}.`
  if (round.status === 'open') return opens ? `Prijave traju od ${instant(opens)}${closes ? ` do ${instant(closes)}` : ''}.`
    : `Zahtjev se može podnijeti do ${instant(closes!)}.`
  return 'Izvor ne navodi rok prijave.'
}

// EnrolmentDetails links the official channel and dates each round without promising a place.
export function EnrolmentDetails({ rounds, openLink }: { rounds: LocationEnrolment[]; openLink?: (url: string) => void }) {
  const open = (event: MouseEvent<HTMLAnchorElement>) => {
    if (!openLink) return
    event.preventDefault()
    openLink(event.currentTarget.href)
  }
  return <section className="enrolment-details" aria-label="Upis">
    <h3>Upis</h3>
    {rounds.length === 0
      ? <p className="location-details-note">Službeni kanal upisa za ovaj vrtić nije potvrđen. Rokove i postupak provjerite izravno kod vrtića.</p>
      : <>{rounds.map((round, index) => {
        const application = round.status === 'open' || round.status === 'upcoming' ? websiteHref(round.application_url) : undefined
        const source = websiteHref(round.source_url)
        return <article className="subsidy-policy enrolment-round" key={`${round.source_url}-${round.round}-${index}`}>
          {/* Status leads the round: parents scan whether they can apply before the year. */}
          <div className="subsidy-policy-heading enrolment-heading">
            <span className="enrolment-status" data-status={round.status}>{statusLabels[round.status]}</span>
            <h4>{round.round === 'main' ? `Upisi za ${round.academic_year}` : `Upis tijekom pedagoške godine ${round.academic_year}`}</h4>
          </div>
          <p>{period(round)}</p>
          {round.accepting && <p className="subsidy-caption">Kanal: {channelLabels[round.channel]}</p>}
          {application && <>
            <a className="enrolment-action" href={application} target="_blank" rel="noreferrer" onClick={open}>Otvori službeni upis ↗</a>
            <p className="subsidy-caption">Otvara vanjsku uslugu {new URL(application).host}. KIDSic ne predaje zahtjev i ne jamči mjesto.</p>
          </>}
          <p className="subsidy-dates">{round.reference_date
            ? `${round.date_kind === 'observed' ? 'Stanje izvora' : 'Objavljeno'} ${day(round.reference_date)}` : 'Datum izvora nije poznat'}</p>
          {source && <div className="subsidy-links"><a href={source} target="_blank" rel="noreferrer" onClick={open}>{round.source_title} ↗</a></div>}
          {round.license && <p className="subsidy-caption">Licenca: {round.license}</p>}
        </article>
      })}
      <p className="location-details-note">Korake i popis potrebnih dokumenata pročitajte u službenom izvoru. Upis ovisi o slobodnim mjestima i listi prednosti.</p>
      </>}
  </section>
}
