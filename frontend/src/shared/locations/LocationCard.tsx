import { providerLabels } from './types'
import type { LocationFeature } from './types'

interface LocationCardProps {
  feature: LocationFeature
  selected: boolean
  detailsOpen: boolean
  onSelect: (id: string) => void
  onDetails: (feature: LocationFeature, trigger: HTMLButtonElement) => void
}

// LocationCard keeps selection and source details as separate actions.
export function LocationCard({ feature, selected, detailsOpen, onSelect, onDetails }: LocationCardProps) {
  const location = feature.properties
  return <article className="location-card" data-selected={selected}>
    <div className="location-thumbnail" aria-hidden="true">
      <svg viewBox="0 0 80 80" fill="none"><path d="M15 65V30L40 14l25 16v35H15Z" /><path d="M33 65V47h14v18M25 33h8v8h-8zm22 0h8v8h-8zM9 65h62" /></svg>
    </div>
    <div className="location-card-copy">
      <button type="button" className="location-select" aria-pressed={selected} onClick={() => onSelect(feature.id)}>
        <span className="location-name">{location.location_name}</span>{' '}
        <span className="location-address">{location.address ?? 'Adresa nije poznata'}</span>
      </button>
      <p className="location-context">{providerLabels[location.provider_kind]}{location.district ? ` · ${location.district}` : ''}</p>
      {!feature.geometry && <small className="location-coordinate-note">{location.location_role === 'seat' ? 'Sjedište ustanove — lokacija pružanja usluge nije potvrđena' : 'Koordinate nisu poznate — nema prikaza na karti'}</small>}
      <button type="button" className="location-details-button" aria-label={`Detalji i izvori: ${location.location_name}`} aria-expanded={detailsOpen} aria-controls={detailsOpen ? `details-${feature.id}` : undefined} onClick={(event) => onDetails(feature, event.currentTarget)}>Detalji i izvori <span aria-hidden="true">↗</span></button>
    </div>
  </article>
}
