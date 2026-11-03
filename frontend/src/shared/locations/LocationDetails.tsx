import type { LocationFeature, LocationSource } from './types'

function formatDate(value: string | null) {
  if (!value) return 'Nije poznato'
  const date = new Date(value)
  return Number.isNaN(date.valueOf()) ? 'Nije poznato' : new Intl.DateTimeFormat('hr-HR', { dateStyle: 'medium', timeZone: 'UTC' }).format(date)
}

function sourceHref(value: string) {
  try {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol) ? url.href : undefined
  } catch { return undefined }
}

const fieldLabels: Record<string, string> = {
  name: 'Naziv ustanove', provider_kind: 'Pružatelj', location_name: 'Naziv objekta',
  address: 'Adresa', district: 'Četvrt', longitude: 'Zemljopisna dužina', latitude: 'Zemljopisna širina',
}

function SourceEvidence({ source }: { source: LocationSource }) {
  const href = sourceHref(source.url)
  return <>
    {href ? <a href={href} target="_blank" rel="noreferrer">{source.name} ↗</a> : <span>{source.name}</span>}
    <dl>
      <dt>Referentni datum</dt><dd>{formatDate(source.reference_date)}</dd>
      <dt>Dohvaćeno</dt><dd>{formatDate(source.retrieved_at)}</dd>
      <dt>Licenca</dt><dd>{source.license ?? 'Nije navedena'}</dd>
    </dl>
  </>
}

export function LocationDetails({ feature, onClose }: { feature: LocationFeature; onClose: () => void }) {
  const { properties } = feature
  return <section className="location-details" id={`details-${feature.id}`} aria-label={`Detalji: ${properties.location_name}`}>
    <dl>
      <dt>Ustanova</dt><dd>{properties.name}</dd>
      <dt>Grad / općina</dt><dd>{properties.city}</dd>
      <dt>Četvrt</dt><dd>{properties.district ?? 'Nije poznata'}</dd>
    </dl>
    <p className="age-note">Dobna prikladnost nije provjerena u ovom prikazu.</p>
    <h3>Izvori aktualnih zapisa</h3>
    {properties.sources.length === 0 && <p>Podrijetlo podatka nije dostupno.</p>}
    <ul className="source-list">
      {properties.sources.map((source, index) => <li key={`${source.url}-${index}`}><SourceEvidence source={source} /></li>)}
    </ul>
    <h3>Podrijetlo pojedinih podataka</h3>
    {!Object.keys(properties.field_sources ?? {}).length && <p>Za pojedine podatke nije zabilježen izvor.</p>}
    <ul className="source-list">
      {Object.entries(properties.field_sources ?? {}).map(([field, source]) => <li key={field}>
        <strong>{fieldLabels[field] ?? field}</strong>
        {!source.active_snapshot && <p className="historical-note">Posljednji poznati podatak (starija snimka)</p>}
        <SourceEvidence source={source} />
      </li>)}
    </ul>
    <button className="text-button" type="button" onClick={onClose}>Zatvori detalje</button>
  </section>
}
