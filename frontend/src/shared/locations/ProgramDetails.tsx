import type { MouseEvent } from 'react'
import { Badge } from '../ui/badge'
import { type LocationProperties, type SuitabilityStatus } from './types'
import { websiteHref } from './links'

export function SuitabilityBadge({ status }: { status?: SuitabilityStatus }) {
  if (status !== 'confirmed') return null
  return <Badge className="suitability-badge max-w-full" variant="default">
    <span className="truncate">Potvrđeno podudaranje</span>
  </Badge>
}

// ProgramDetails keeps published program evidence distinct from enrolment availability.
export function ProgramDetails({ location, openLink }: { location: LocationProperties; openLink?: (url: string) => void }) {
  const programs = location.programs ?? []
  const open = (event: MouseEvent<HTMLAnchorElement>) => {
    if (!openLink) return
    event.preventDefault()
    openLink(event.currentTarget.href)
  }
  return <section className="program-details" aria-label="Programi i dobni uvjeti">
    <h3>Programi i dobni uvjeti</h3>
    <SuitabilityBadge status={location.suitability_status} />
    {location.suitability_status === 'unknown' && <p className="location-details-note">Nema dovoljno potvrđenih podataka za zadanu dob ili program. Provjerite uvjete izravno s vrtićem.</p>}
    {programs.length === 0 && <p className="location-details-note">Programi i dobni uvjeti nisu potvrđeni u dostupnim podacima. To ne znači da program nije dostupan.</p>}
    {programs.map((program) => {
      const href = websiteHref(program.source_url)
      return <article key={program.program_id}>
        <h4>{program.name}</h4>
        <p>Dob: {program.min_age_months == null ? 'donja granica nije potvrđena' : `od ${program.min_age_months} mjeseci`}; {program.max_age_months_exclusive == null ? 'gornja granica nije potvrđena' : `manje od ${program.max_age_months_exclusive} mjeseci`}.</p>
        <p>{program.scope === 'institution' ? 'Podatak za ustanovu; provedbu u ovom objektu treba provjeriti.' : 'Podatak za ovaj objekt.'}</p>
        <p>Provjereno {new Intl.DateTimeFormat('hr-HR').format(new Date(`${program.verified_on}T00:00:00`))}
          {program.valid_until && ` · vrijedi do ${new Intl.DateTimeFormat('hr-HR').format(new Date(`${program.valid_until}T00:00:00`))}`}</p>
        {href && <a href={href} target="_blank" rel="noreferrer" onClick={open}>{program.source_title} ↗</a>}
      </article>
    })}
    <p className="location-details-note">Potvrđeno podudaranje dobi i programa nije potvrda slobodnog mjesta ni jamstvo upisa.</p>
  </section>
}
