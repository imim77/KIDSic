import type { LocationProperties } from '../types'
import { hostLink, websiteHref, type OpenLink } from '@/mvvm/utils/links'
import { formatDay } from '@/mvvm/utils/format'
import { officialVacancyOverview, publishedVacancies, vacancyLabel } from '../utils/vacancies'

// VacancyDetails shows the newest published free-place count with its date and
// scope. It keeps a published zero, a blank count and an unpublished count
// apart and never presents a count as a place the family will get.
export function VacancyDetails({ location, openLink }: { location: LocationProperties; openLink?: OpenLink }) {
  const open = hostLink(openLink)
  const vacancies = publishedVacancies(location)
  if (vacancies.state === 'unpublished') {
    const overview = officialVacancyOverview(location)
    return <section className="vacancy-details" aria-label="Objavljena slobodna mjesta">
      <h3>Objavljena slobodna mjesta</h3>
      <p className="location-details-note">Za ovaj vrtić slobodna mjesta nisu objavljena u uvezenim izvorima. To ne znači da mjesta nema; provjerite izravno s vrtićem.</p>
      {overview && <a href={overview} target="_blank" rel="noreferrer" onClick={open}>Službeni pregled slobodnih mjesta ↗</a>}
    </section>
  }
  const { total, record, stale } = vacancies
  const href = websiteHref(record.source_url)
  return <section className="vacancy-details" aria-label="Objavljena slobodna mjesta">
    <h3>Objavljena slobodna mjesta</h3>
    <article className="vacancy-card" data-state={total === null ? 'partial' : total > 0 ? 'free' : 'zero'}>
      <p className="vacancy-total">{total === null ? 'Broj nije potpuno objavljen' : vacancyLabel(total)}</p>
      <p className="vacancy-meta">
        <span className="enrolment-status" data-status={stale ? 'closed' : 'open'}>{record.date_kind === 'observed' ? 'Stanje' : 'Objavljeno'} {formatDay(record.reference_date)}</span>
        {stale && <span className="vacancy-stale">Snimka je starija od godinu dana</span>}
      </p>
      <p>{record.scope === 'institution' ? 'Broj vrijedi za cijelu ustanovu ili obrt; nije raspoređen po objektima.' : 'Broj vrijedi za ovaj objekt.'}</p>
      <ul className="vacancy-groups" aria-label="Mjesta prema dobi i programu">
        {record.vacancies.map((group, index) => <li key={index}>
          <span>{[group.age_label, group.program?.toLocaleLowerCase('hr')].filter(Boolean).join(' · ') || 'Sve skupine'}</span>
          <strong>{group.free_places ?? 'nije objavljeno'}</strong>
        </li>)}
      </ul>
      {href && <a href={href} target="_blank" rel="noreferrer" onClick={open}>{record.source_title} ↗</a>}
      <p className="location-details-note">Licenca: {record.license}. Objavljeno slobodno mjesto nije jamstvo upisa; trenutačno stanje provjerite s vrtićem.</p>
    </article>
  </section>
}
