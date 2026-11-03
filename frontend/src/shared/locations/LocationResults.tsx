import { useEffect, useRef } from 'react'
import { LocationDetails } from './LocationDetails'
import { providerLabels } from './types'
import type { LocationCollection, LocationFilters } from './types'

interface LocationResultsProps {
  data: LocationCollection | null
  status: 'loading' | 'ready' | 'error'
  filters: LocationFilters
  selectedId: string | null
  onSelect: (id: string | null) => void
  retry: () => void
}

export function LocationResults({ data, status, filters, selectedId, onSelect, retry }: LocationResultsProps) {
  const selectedRef = useRef<HTMLLIElement>(null)
  useEffect(() => {
    selectedRef.current?.scrollIntoView({ block: 'nearest', behavior: 'auto' })
  }, [selectedId])

  return <section className="location-results" aria-label="Popis objekata" aria-busy={status === 'loading'}>
    {status === 'loading' && <p role="status">Učitavanje objekata…</p>}
    {status === 'error' && <div role="alert"><p>Podatke nije moguće učitati. Provjerite vezu i pokušajte ponovno.</p><button className="text-button" onClick={retry}>Pokušaj ponovno</button></div>}
    {data && <>
      <p className="result-count" role="status">{filters.city} · {data.metadata.total} rezultata · {data.metadata.mapped} na karti · {data.metadata.unmapped} bez koordinata</p>
      {data.features.length === 0 && <p>Nema rezultata za odabrane filtre. Promijenite naziv ili pružatelja.</p>}
      <p className="applied-filters">Primijenjeno: {filters.q ? `Naziv: ${filters.q}` : 'Svi nazivi'} · {filters.provider_kind ? providerLabels[filters.provider_kind] : 'Svi pružatelji'}</p>
      <ul className="location-list">
        {data.features.map((feature) => {
          const selected = feature.id === selectedId
          const location = feature.properties
          return <li key={feature.id} className="location-item" data-selected={selected} ref={selected ? selectedRef : undefined}>
            <button className="location-select" type="button" aria-expanded={selected} aria-controls={selected ? `details-${feature.id}` : undefined} onClick={() => onSelect(feature.id)}>
              <span className="provider-label">{providerLabels[location.provider_kind]}</span>
              <span className="location-name">{location.location_name}</span>
              <span className="location-address">{location.address ?? 'Adresa nije poznata'}</span>
              {!feature.geometry && <small>{location.location_role === 'seat' ? 'Sjedište ustanove — lokacija pružanja usluge nije potvrđena' : 'Koordinate nisu poznate — nema prikaza na karti'}</small>}
            </button>
            {selected && <LocationDetails feature={feature} onClose={() => onSelect(null)} />}
          </li>
        })}
      </ul>
    </>}
  </section>
}
