import { useRef, type ReactNode } from 'react'
import { FullscreenFrame, type HostFullscreen } from '@/mvvm/components/FullscreenFrame'
import { useFrameControls } from '@/mvvm/hooks/use-frame-controls'
import { useMediaQuery } from '@/mvvm/hooks/use-media-query'
import type { OpenLink } from '@/mvvm/utils/links'
import { useKindergartenExplorer, type ExplorerInput } from '../hooks/use-kindergarten-explorer'
import type { LocationFeature } from '../types'
import type { MapRoute } from './map/RouteLayer'
import { KindergartenMap } from './map/KindergartenMap'
import { LocationCarousel } from './LocationCarousel'
import { LocationDetails } from './LocationDetails'
import { LocationList } from './LocationList'
import { NearbyControl } from './NearbyControl'
import { DistrictControl } from './DistrictControl'
import { CompareTray } from './CompareTray'
import { ComparisonView } from './ComparisonView'
import './explorer.css'

interface KindergartenExplorerProps extends Omit<ExplorerInput, 'comparable'> {
  status: 'loading' | 'ready' | 'error'
  route?: MapRoute | null
  summary?: (feature: LocationFeature) => string
  // details replaces the kindergarten details, e.g. with a route.
  details?: ReactNode
  mapNotice?: ReactNode
  hostFullscreen?: HostFullscreen
  notice?: string
  openLink?: OpenLink
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
function ExplorerLayout({ status, route, summary, details, mapNotice, notice, openLink, ...input }: Omit<KindergartenExplorerProps, 'hostFullscreen'>) {
  const { data, selectedId, onSelect, district } = input
  const explorer = useKindergartenExplorer({ ...input, comparable: !route })
  const { selected, nearby, comparison } = explorer
  const { expanded, expand } = useFrameControls()
  const layoutRef = useRef<HTMLDivElement>(null)
  const roomy = useMediaQuery('(min-width: 700px)', true)
  const closeDetails = () => {
    // Return focus to the result that opened the details before they unmount.
    const origin = Array.from(layoutRef.current?.querySelectorAll<HTMLElement>('[data-location-row], [data-location-card]') ?? [])
      .find((element) => (element.dataset.locationRow ?? element.dataset.locationCard) === selectedId)
    origin?.focus({ preventScroll: true })
    onSelect(null)
  }

  const panels = expanded && roomy && !!data?.features.length
  // The comparison covers the explorer; what lies beneath must not take focus.
  const covered = comparison.open
  return <div ref={layoutRef} className="explorer-layout" data-layout={panels ? 'panels' : 'map'} data-details={expanded && selected ? '' : undefined} data-comparing={covered ? '' : undefined}>
    {/* display: contents keeps list and details as grid items of the layout. */}
    <div className="contents" inert={covered}>
    {panels && <LocationList collection={data!} selectedId={selectedId} onSelect={onSelect} criteria={explorer.criteria} summary={summary} />}
    {expanded && selected && (details ?? <LocationDetails key={selected.id} feature={selected} onClose={closeDetails} openLink={openLink} compare={comparison.choice(selected)} />)}
    </div>
    {covered && <ComparisonView features={comparison.features} onRemove={comparison.remove}
      onClose={comparison.hide} openLink={openLink} />}
    <div className="explorer-map" inert={covered}>
      <KindergartenMap route={route} collection={data} selectedId={selectedId} nearby={nearby?.value} picking={nearby?.picking} onPick={nearby?.place}
        onSelect={explorer.selectFromMap}
        overlay={(mapReady) => <>
          {mapNotice}
          {nearby && <NearbyControl value={nearby.value} radius={nearby.radius} picking={nearby.picking && mapReady} canPick={mapReady}
            onLocate={nearby.place} onPicking={nearby.setPicking} onClear={nearby.clear} onRadius={nearby.changeRadius} />}
          {!!district?.options.length && <DistrictControl {...district} />}
          {comparison.count > 0 && <CompareTray count={comparison.count} onOpen={comparison.show} onClear={comparison.clear} />}
          {status === 'loading' && <p className="explorer-notice" role="status">{notice ?? 'Učitavanje objekata…'}</p>}
          {status === 'error' && <div className="explorer-notice" role="alert"><p>Podatke nije moguće učitati. Provjerite vezu i pokušajte ponovno.</p><button className="text-button" onClick={explorer.retry}>Pokušaj ponovno</button></div>}
          {explorer.emptyNotice && <p className="explorer-notice" role="status">{explorer.emptyNotice}</p>}
        </>} />
      {data && <p className="sr-only" role="status">{data.metadata.total} rezultata · {data.metadata.mapped} na karti · {data.metadata.unmapped} bez koordinata</p>}
      {!!data?.features.length && !panels && <LocationCarousel features={data.features} selectedId={selectedId} reveal={explorer.reveal} onSelect={(id) => { onSelect(id); expand() }}
        compare={comparison.choice} summary={summary}
        caption={explorer.criteria?.join(' · ')} />}
    </div>
  </div>
}
