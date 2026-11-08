import type { LocationEnrolment } from '../types'
import { hostLink, websiteHref, type OpenLink } from '@/mvvm/utils/links'
import { formatDay as day, formatInstant as instant } from '@/mvvm/utils/format'
import { enrolmentStatusLabels as statusLabels } from '../utils/enrolment'

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


export function EnrolmentDetails({ rounds, openLink }: { rounds: LocationEnrolment[]; openLink?: OpenLink }) {
  const open = hostLink(openLink)
  return <section className="enrolment-details" aria-label="Upis">
    <h3>Upis</h3>
    {rounds.length === 0
      ? <p className="location-details-note">Službeni kanal upisa za ovaj vrtić nije potvrđen. Rokove i postupak provjerite izravno kod vrtića.</p>
      : <>{rounds.map((round, index) => {
        const application = round.status === 'open' || round.status === 'upcoming' ? websiteHref(round.application_url) : undefined
        const source = websiteHref(round.source_url)
        return <article className="subsidy-policy enrolment-round" key={`${round.source_url}-${round.round}-${index}`}>

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
