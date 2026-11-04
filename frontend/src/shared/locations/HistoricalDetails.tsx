import type { MouseEvent } from 'react'
import type { HistoricalEvidence } from './types'
import { websiteHref } from './links'

// HistoricalDetails preserves the date and institution/object scope of open snapshots.
export function HistoricalDetails({ records, openLink }: { records: HistoricalEvidence[]; openLink?: (url: string) => void }) {
  if (!records.length) return null
  const open = (event: MouseEvent<HTMLAnchorElement>) => {
    if (!openLink) return
    event.preventDefault()
    openLink(event.currentTarget.href)
  }
  const format = (date: string) => new Intl.DateTimeFormat('hr-HR').format(new Date(`${date}T00:00:00`))
  return <section className="historical-details" aria-label="Povijesni otvoreni podaci">
    <h3>Povijesni otvoreni podaci</h3>
    <p className="location-details-note">Objavljene snimke podataka. Današnje programe i slobodna mjesta provjerite izravno s vrtićem.</p>
    {records.map((record, index) => {
      const href = websiteHref(record.source_url)
      const total = record.vacancies.some((v) => v.free_places === null) ? null
        : record.vacancies.reduce((sum, v) => sum + (v.free_places ?? 0), 0)
      return <article key={`${record.source_url}-${index}`}>
        <h4>{record.vacancies.length ? total === null ? 'Slobodna mjesta: nepotpuni podaci' : `Slobodna mjesta: ${total}` : 'Objavljeni programi'}</h4>
        <p className="historical-details-date">{record.date_kind === 'observed' ? 'Stanje na dan' : 'Objavljeno'} {format(record.reference_date)}</p>
        <p>{record.scope === 'institution' ? 'Podatak za cijelu ustanovu/obrt; mjesta nisu raspoređena po objektima.' : 'Podatak za ovaj objekt.'}</p>
        {record.programs.length > 0 && <ul>{record.programs.map((program) => <li key={program}>{program}</li>)}</ul>}
        {record.vacancies.length > 0 && <details>
          <summary>Mjesta prema dobi i programu</summary>
          <ul>{record.vacancies.map((vacancy, i) => <li key={i}>
            {[vacancy.age_label, vacancy.program?.toLocaleLowerCase('hr')].filter(Boolean).join(' · ')}: <strong>{vacancy.free_places ?? 'nije objavljeno'}</strong>
          </li>)}</ul>
        </details>}
        {href && <a href={href} target="_blank" rel="noreferrer" onClick={open}>Grad Zagreb · izvorni otvoreni skup ↗</a>}
        <p className="location-details-note">Licenca: {record.license}</p>
      </article>
    })}
  </section>
}
