import { useRef, useState } from 'react'
import { FullscreenFrame, type HostFullscreen } from './FullscreenFrame'
import { useFrameControls } from './frameControls'
import { useMediaQuery } from './useMediaQuery'
import { KindergartenMap } from '../map/KindergartenMap'
import { LocationCarousel } from '../locations/LocationCarousel'
import { LocationDetails } from '../locations/LocationDetails'
import { LocationList } from '../locations/LocationList'
import { providerLabels, type LocationCollection, type ProviderKind } from '../locations/types'

interface KindergartenExplorerProps {
  data: LocationCollection | null
  status: 'loading' | 'ready' | 'error'
  selectedId: string | null
  onSelect: (id: string | null) => void
  retry: () => void
  hostFullscreen?: HostFullscreen
  notice?: string
  emptyNotice?: string
  criteria?: { city: string; name?: string; provider_kind?: ProviderKind | null; area?: string }
  openLink?: (url: string) => void
}

// KindergartenExplorer keeps every map overlay in the same fullscreen frame.
// Choosing a card expands it into list, details and map columns; narrow
// screens keep the card deck and show details over the map instead.
export function KindergartenExplorer({ hostFullscreen, criteria, ...props }: KindergartenExplorerProps) {
  return <FullscreenFrame className="kindergarten-explorer" hostFullscreen={hostFullscreen}>
    {criteria && <header className="explorer-search-summary" aria-label="Kriteriji pretrage">
      <strong>Grad: {criteria.city}</strong>
      {criteria.name && <span>Naziv: „{criteria.name}”</span>}
      <span>Vrsta: {criteria.provider_kind ? providerLabels[criteria.provider_kind] : 'Sve vrste'}</span>
      <span>Područje: {criteria.area || 'Sva područja'}</span>
      {criteria.area && <span>Prikaz prema potvrđenim nazivima područja. Pokrivenost je nepotpuna; OSM nazivi nisu službene granice.</span>}
    </header>}
    <ExplorerLayout {...props} />
  </FullscreenFrame>
}

// ExplorerLayout arranges list, details and map for the frame's current state.
function ExplorerLayout({ data, status, selectedId, onSelect, retry, notice, emptyNotice, openLink }: Omit<KindergartenExplorerProps, 'hostFullscreen'>) {
  const { expanded, expand } = useFrameControls()
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

  const panels = expanded && roomy && !!data?.features.length
  return <div ref={layoutRef} className="explorer-layout" data-layout={panels ? 'panels' : 'map'} data-details={expanded && selected ? '' : undefined}>
    {panels && <LocationList collection={data!} selectedId={selectedId} onSelect={onSelect} />}
    {expanded && selected && <LocationDetails key={selected.id} feature={selected} onClose={closeDetails} openLink={openLink} />}
    <div className="explorer-map">
      <KindergartenMap collection={data} selectedId={selectedId} onSelect={(id) => { onSelect(id); setReveal((previous) => ({ id, revision: (previous?.revision ?? 0) + 1 })) }} />
      {status === 'loading' && <p className="explorer-notice" role="status">{notice ?? 'Učitavanje objekata…'}</p>}
      {data && <p className="sr-only" role="status">{data.metadata.total} rezultata · {data.metadata.mapped} na karti · {data.metadata.unmapped} bez koordinata</p>}
      {status === 'error' && <div className="explorer-notice" role="alert"><p>Podatke nije moguće učitati. Provjerite vezu i pokušajte ponovno.</p><button className="text-button" onClick={() => { setReveal(null); retry() }}>Pokušaj ponovno</button></div>}
      {data?.features.length === 0 && <p className="explorer-notice" role="status">{emptyNotice ?? 'Nema dostupnih vrtićkih objekata.'}</p>}
      {!!data?.features.length && !panels && <LocationCarousel features={data.features} selectedId={selectedId} reveal={reveal} onSelect={(id) => { onSelect(id); expand() }} />}
    </div>
  </div>
}
