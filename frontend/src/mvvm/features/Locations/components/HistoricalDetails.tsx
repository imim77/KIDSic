import type { HistoricalEvidence } from '../types'
import { formatDay } from '@/mvvm/utils/format'
import { hostLink, websiteHref, type OpenLink } from '@/mvvm/utils/links'



export function HistoricalDetails({ records: all, openLink }: { records: HistoricalEvidence[]; openLink?: OpenLink }) {
  const records = all.filter((record) => record.programs.length)
  if (!records.length) return null
  const open = hostLink(openLink)
  return <section className="historical-details" aria-label="Povijesni otvoreni podaci">
    <h3>Povijesni otvoreni podaci</h3>
    <p className="location-details-note">Objavljene snimke podataka. Današnje programe provjerite izravno s vrtićem.</p>
    {records.map((record, index) => {
      const href = websiteHref(record.source_url)
      return <article key={`${record.source_url}-${index}`}>
        <h4>Objavljeni programi</h4>
        <p className="historical-details-date">{record.date_kind === 'observed' ? 'Stanje na dan' : 'Objavljeno'} {formatDay(record.reference_date)}</p>
        <p>{record.scope === 'institution' ? 'Podatak za cijelu ustanovu/obrt; provedbu u ovom objektu treba provjeriti.' : 'Podatak za ovaj objekt.'}</p>
        {record.programs.length > 0 && <ul>{record.programs.map((program) => <li key={program}>{program}</li>)}</ul>}
        {href && <a href={href} target="_blank" rel="noreferrer" onClick={open}>Grad Zagreb · izvorni otvoreni skup ↗</a>}
        <p className="location-details-note">Licenca: {record.license}</p>
      </article>
    })}
  </section>
}
