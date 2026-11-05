import { useRef, useState, type ReactNode } from 'react'
import { FullscreenFrame, type HostFullscreen } from './FullscreenFrame'
import { useFrameControls } from './frameControls'
import { useMediaQuery } from './useMediaQuery'
import type { MapRoute } from '../map/RouteLayer'
import { KindergartenMap } from '../map/KindergartenMap'
import { LocationCarousel } from '../locations/LocationCarousel'
import { LocationDetails } from '../locations/LocationDetails'
import { LocationList } from '../locations/LocationList'
import { NearbyControl } from '../locations/NearbyControl'
import { DistrictControl } from '../locations/DistrictControl'
import { CompareTray } from '../locations/CompareTray'
import { ComparisonView } from '../locations/ComparisonView'
import { comparisonLimit } from '../locations/comparison'
import type { CompareChoice } from '../locations/CompareToggle'
import { formatDistance } from '../locations/distance'
import { describeCriteria } from '../locations/criteria'
import type { LocationCollection, LocationFeature, Nearby, SearchCriteria } from '../locations/types'

interface KindergartenExplorerProps {
  route?: MapRoute | null
  summary?: (feature: LocationFeature) => string
  details?: ReactNode
  mapNotice?: ReactNode
  data: LocationCollection | null
  status: 'loading' | 'ready' | 'error'
  selectedId: string | null
  onSelect: (id: string | null) => void
  retry: () => void
  hostFullscreen?: HostFullscreen
  notice?: string
  emptyNotice?: string
  openLink?: (url: string) => void
  // nearby enables the point-and-radius control; hosts without a directory omit it.
  nearby?: { value: Nearby | null; onChange: (value: Nearby | null) => void }
  // district enables the city-district picker; hosts without a directory omit it.
  district?: { options: string[]; value: string; unknown: number; onChange: (value: string) => void }
  // criteria describes the search behind data, so the results explain themselves.
  criteria?: SearchCriteria
}

// KindergartenExplorer keeps every map overlay in the same fullscreen frame.
// Choosing a card expands it into list, details and map columns; narrow
// screens keep the card deck and show details over the map instead.
export function KindergartenExplorer({ hostFullscreen, ...props }: KindergartenExplorerProps) {
  return <FullscreenFrame className="kindergarten-explorer" hostFullscreen={hostFullscreen}>
    <ExplorerLayout {...props} />
  </FullscreenFrame>
}

// ExplorerLayout arranges list, details and map for the frame's current state.
function ExplorerLayout({ data, status, selectedId, onSelect, retry, notice, emptyNotice, openLink, nearby, district, criteria, route, summary, details, mapNotice }: Omit<KindergartenExplorerProps, 'hostFullscreen'>) {
  const { expanded, expand } = useFrameControls()
  const [picking, setPicking] = useState(false)
  const [chosenRadius, setRadius] = useState(1000)
  // An active search, also one the host's model made, owns the shown radius.
  const radius = nearby?.value?.radius_m ?? chosenRadius
  const place = (near: [number, number]) => {
    setPicking(false)
    nearby?.onChange({ near, radius_m: radius })
  }
  const [reveal, setReveal] = useState<{ id: string; revision: number } | null>(null)
  const layoutRef = useRef<HTMLDivElement>(null)
  const roomy = useMediaQuery('(min-width: 700px)', true)
  const selected = data?.features.find((feature) => feature.id === selectedId) ?? null
  const closeDetails = () => {
    // Return focus to the result that opened the details before they unmount.
    const origin = Array.from(layoutRef.current?.querySelectorAll<HTMLElement>('[data-location-row], [data-location-card]') ?? [])
      .find((element) => (element.dataset.locationRow ?? element.dataset.locationCard) === selectedId)
    origin?.focus({ preventScroll: true })
    onSelect(null)
  }

  // Compared options are kept as snapshots so they survive a new search; a
  // result that is still listed replaces its snapshot, e.g. to show distance.
  const [compared, setCompared] = useState<LocationFeature[]>([])
  const [comparing, setComparing] = useState(false)
  const comparedNow = compared.map((feature) => data?.features.find((current) => current.id === feature.id) ?? feature)
  const compareChoice = (feature: LocationFeature): CompareChoice => {
    const selected = compared.some((item) => item.id === feature.id)
    return { selected, full: compared.length >= comparisonLimit, onToggle: () => setCompared((items) => selected
      ? items.filter((item) => item.id !== feature.id)
      : items.length < comparisonLimit ? [...items, feature] : items) }
  }
  const removeCompared = (id: string) => {
    const remaining = compared.filter((item) => item.id !== id)
    setCompared(remaining)
    if (remaining.length < 2) setComparing(false)
  }

  const panels = expanded && roomy && !!data?.features.length
  // The comparison covers the explorer; what lies beneath must not take focus.
  const covered = comparing && comparedNow.length > 1
  const described = criteria ? describeCriteria(criteria) : undefined
  return <div ref={layoutRef} className="explorer-layout" data-suitability={data?.features.some((feature) => feature.properties.suitability_status === 'confirmed') ? '' : undefined} data-layout={panels ? 'panels' : 'map'} data-details={expanded && selected ? '' : undefined} data-comparing={covered ? '' : undefined}>
    {/* display: contents keeps list and details as grid items of the layout. */}
    <div className="contents" inert={covered}>
    {panels && <LocationList collection={data!} selectedId={selectedId} onSelect={onSelect} criteria={described} summary={summary} />}
    {expanded && selected && (details ?? <LocationDetails key={selected.id} feature={selected} onClose={closeDetails} openLink={openLink} compare={route ? undefined : compareChoice(selected)} />)}
    </div>
    {covered && <ComparisonView features={comparedNow} onRemove={removeCompared}
      onClose={() => setComparing(false)} openLink={openLink} />}
    <div className="explorer-map" inert={covered}>
      <KindergartenMap route={route} collection={data} selectedId={selectedId} nearby={nearby?.value} picking={picking} onPick={place}
        onSelect={(id) => { onSelect(id); setReveal((previous) => ({ id, revision: (previous?.revision ?? 0) + 1 })) }}
        overlay={(mapReady) => <>
          {mapNotice}
          {nearby && <NearbyControl value={nearby.value} radius={radius} picking={picking && mapReady} canPick={mapReady}
            onLocate={place} onPicking={setPicking} onClear={() => { setPicking(false); nearby.onChange(null) }}
            onRadius={(value) => {
              setRadius(value)
              if (nearby.value) nearby.onChange({ ...nearby.value, radius_m: value })
            }} />}
          {!!district?.options.length && <DistrictControl {...district} />}
          {compared.length > 0 && <CompareTray count={compared.length} onOpen={() => setComparing(true)} onClear={() => { setCompared([]); setComparing(false) }} />}
          {status === 'loading' && <p className="explorer-notice" role="status">{notice ?? 'Učitavanje objekata…'}</p>}
          {status === 'error' && <div className="explorer-notice" role="alert"><p>Podatke nije moguće učitati. Provjerite vezu i pokušajte ponovno.</p><button className="text-button" onClick={() => { setReveal(null); retry() }}>Pokušaj ponovno</button></div>}
          {data?.features.length === 0 && <p className="explorer-notice" role="status">{emptyNotice ?? (nearby?.value
            ? `Nema objekata s potvrđenim koordinatama unutar ${formatDistance(nearby.value.radius_m)}${district?.value ? ` u četvrti ${district.value}` : ''}. Povećajte radijus ili uklonite točku.`
            : district?.value ? `Nema objekata s potvrđenom četvrti ${district.value}.`
            : 'Nema dostupnih vrtićkih objekata.')}</p>}
        </>} />
      {data && <p className="sr-only" role="status">{data.metadata.total} rezultata · {data.metadata.mapped} na karti · {data.metadata.unmapped} bez koordinata</p>}
      {!!data?.features.length && !panels && <LocationCarousel features={data.features} selectedId={selectedId} reveal={reveal} onSelect={(id) => { onSelect(id); expand() }}
        compare={route ? undefined : compareChoice} summary={summary}
        caption={described?.join(' · ')} />}
    </div>
  </div>
}
