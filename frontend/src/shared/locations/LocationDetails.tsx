import { useEffect, useRef, type MouseEvent } from 'react'
import { Building2, MapPin, X } from 'lucide-react'
import { providerLabels, type LocationFeature, type LocationSource } from './types'

interface LocationDetailsProps {
  feature: LocationFeature
  onClose: () => void
  openLink?: (url: string) => void
}

function formatDate(value: string | null) {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.valueOf()) ? null : new Intl.DateTimeFormat('hr-HR', { dateStyle: 'medium', timeZone: 'UTC' }).format(date)
}

function safeHref(value: string) {
  try {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol) ? url.href : undefined
  } catch { return undefined }
}

// Coordinates are exact; the address search is the fallback for seats.
function directionsHref(feature: LocationFeature) {
  const { address, city } = feature.properties
  const query = feature.geometry
    ? `${feature.geometry.coordinates[1]},${feature.geometry.coordinates[0]}`
    : [address, city].filter(Boolean).join(', ')
  return query ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}` : undefined
}

function Source({ source, open }: { source: LocationSource; open: (event: MouseEvent<HTMLAnchorElement>) => void }) {
  const href = safeHref(source.url)
  const retrieved = formatDate(source.retrieved_at)
  const reference = formatDate(source.reference_date)
  return <li>
    {href ? <a href={href} target="_blank" rel="noreferrer" onClick={open}>{source.name}</a> : <span>{source.name}</span>}
    <span className="source-meta">
      {[source.license ?? 'Licenca nije navedena', reference && `stanje ${reference}`, retrieved && `dohvaćeno ${retrieved}`].filter(Boolean).join(' · ')}
    </span>
  </li>
}

// LocationDetails shows everything the open data says about one location,
// and states what it cannot say instead of filling gaps.
export function LocationDetails({ feature, onClose, openLink }: LocationDetailsProps) {
  const location = feature.properties
  const sectionRef = useRef<HTMLElement>(null)
  useEffect(() => {
    // A card that expanded the frame may have unmounted with keyboard focus.
    if (!document.activeElement || document.activeElement === document.body) sectionRef.current?.focus({ preventScroll: true })
  }, [])
  const directions = directionsHref(feature)
  // Sandboxed MCP hosts block plain navigation, so links go through the host.
  const open = (event: MouseEvent<HTMLAnchorElement>) => {
    if (!openLink) return
    event.preventDefault()
    openLink(event.currentTarget.href)
  }
  const place = [location.district, location.city].filter(Boolean).join(', ')

  return <section ref={sectionRef} tabIndex={-1} className="location-details" aria-label={`Detalji: ${location.location_name}`}
    onKeyDown={(event) => { if (event.key === 'Escape' && !event.defaultPrevented) { event.preventDefault(); onClose() } }}>
    <div className="location-details-scroll">
      <div className="location-details-hero">
        <Building2 aria-hidden="true" />
        <button type="button" className="location-details-close" aria-label="Zatvori detalje" onClick={onClose}><X aria-hidden="true" /></button>
      </div>
      <div className="location-details-body">
        <span className="location-details-kind">{providerLabels[location.provider_kind]}</span>
        <h2>{location.location_name}</h2>
        {location.name !== location.location_name && <p className="location-details-institution">Ustanova: {location.name}</p>}
        <p className="location-details-address">
          <MapPin aria-hidden="true" />
          <span>{location.address ?? 'Adresa nije poznata'}{place && `, ${place}`}</span>
        </p>
        {location.location_role === 'seat' && <p className="location-details-note">Ovo je adresa sjedišta ustanove; lokacija objekta nije potvrđena.</p>}
        {!feature.geometry && location.location_role !== 'seat' && <p className="location-details-note">Koordinate nisu poznate, pa objekt nije na karti.</p>}
        {directions && <a className="location-details-action" href={directions} target="_blank" rel="noreferrer" onClick={open}>Otvori u Google kartama</a>}

        <h3>O ovom objektu</h3>
        <dl>
          <dt>Vrsta</dt><dd>{providerLabels[location.provider_kind]}</dd>
          <dt>Četvrt</dt><dd>{location.district ?? 'Nije navedena'}</dd>
          <dt>Grad</dt><dd>{location.city}</dd>
        </dl>
        <p className="location-details-note">Dobne skupine, slobodna mjesta i cijene nisu dio otvorenih podataka. Provjerite ih izravno kod vrtića.</p>

        <h3>Izvori podataka</h3>
        {location.sources.length
          ? <ul className="location-details-sources">{location.sources.map((source, index) => <Source key={`${source.url}-${index}`} source={source} open={open} />)}</ul>
          : <p>Podrijetlo podatka nije dostupno.</p>}
      </div>
    </div>
  </section>
}
