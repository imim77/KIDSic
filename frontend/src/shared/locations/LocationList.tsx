import { useEffect, useRef } from 'react'
import { Building2 } from 'lucide-react'
import { providerLabels, type LocationFeature, type LocationCollection } from './types'
import { formatDistance } from './distance'
import { useEntrance } from '../motion/useEntrance'

interface LocationListProps {
  collection: LocationCollection
  summary?: (feature: LocationFeature) => string
  selectedId: string | null
  onSelect: (id: string) => void
  criteria?: string[]
}

// LocationList shows every result as a scrollable column in the expanded
// explorer, where the horizontal card deck would hide most of them.
export function LocationList({ collection, selectedId, onSelect, criteria, summary }: LocationListProps) {
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
      {!!criteria?.length && <p className="location-list-criteria" title="Aktivni kriteriji i redoslijed">{criteria.join(' · ')}</p>}
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
                <span className="location-row-name">{location.location_name}</span>
                {summary && <span className="location-row-distance">{summary(feature)}</span>}
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
