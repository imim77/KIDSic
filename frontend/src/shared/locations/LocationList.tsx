import { useEffect, useRef } from 'react'
import { Building2 } from 'lucide-react'
import { providerLabels, type LocationCollection } from './types'
import { SuitabilityBadge } from './ProgramDetails'
import { formatDistance } from './distance'
import { useEntrance } from '../motion/useEntrance'

interface LocationListProps {
  collection: LocationCollection
  selectedId: string | null
  onSelect: (id: string) => void
}

function results(count: number) {
  return new Intl.PluralRules('hr').select(count) === 'one' ? `${count} rezultat` : `${count} rezultata`
}

// LocationList shows every result as a scrollable column in the expanded
// explorer, where the horizontal card deck would hide most of them.
export function LocationList({ collection, selectedId, onSelect }: LocationListProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  // Items, not rows: rows keep CSS transform transitions for hover and press.
  useEntrance(scrollRef, [collection], { selector: 'li', limit: 14 })
  const city = collection.features[0]?.properties.city
  useEffect(() => {
    const scroller = scrollRef.current
    const row = Array.from(scroller?.querySelectorAll<HTMLElement>('[data-location-row]') ?? [])
      .find((element) => element.dataset.locationRow === selectedId)
    if (!scroller || !row) return
    // Scroll only this column; scrollIntoView could also move the host page.
    if (row.offsetTop < scroller.scrollTop || row.offsetTop + row.offsetHeight > scroller.scrollTop + scroller.clientHeight) {
      scroller.scrollTop = row.offsetTop - 16
    }
  }, [selectedId])

  return <section className="location-list" aria-label="Popis vrtića">
    <header className="location-list-header">
      <h2>{city ? `Vrtići · ${city}` : 'Vrtići'}</h2>
      <p>{results(collection.metadata.total)} · {collection.metadata.mapped} na karti</p>
    </header>
    <div ref={scrollRef} className="location-list-scroll">
      <ul aria-label="Svi vrtići">
        {collection.features.map((feature) => {
          const location = feature.properties
          const selected = feature.id === selectedId
          return <li key={feature.id}>
            <button type="button" className="location-row" data-location-row={feature.id} aria-pressed={selected} onClick={() => onSelect(feature.id)}>
              <span className="location-thumbnail" aria-hidden="true"><Building2 /></span>
              <span className="location-row-text">
                <span className="location-row-kind">{providerLabels[location.provider_kind]}</span>
                <SuitabilityBadge status={location.suitability_status} />
                <span className="location-row-name">{location.location_name}</span>
                <span className="location-row-address">{location.address ?? 'Adresa nije poznata'}</span>
                {location.distance_m != null && <span className="location-row-distance">{formatDistance(location.distance_m)} zračno</span>}
                {location.district && <span className="location-row-district">{location.district}</span>}
              </span>
            </button>
          </li>
        })}
      </ul>
    </div>
  </section>
}
