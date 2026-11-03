import { useEffect, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import { FullscreenFrame } from './FullscreenFrame'
import { KindergartenMap } from '../map/KindergartenMap'
import { LocationCarousel } from '../locations/LocationCarousel'
import { LocationDetails } from '../locations/LocationDetails'
import type { LocationCollection, LocationFeature } from '../locations/types'

interface KindergartenExplorerProps {
  data: LocationCollection | null
  status: 'loading' | 'ready' | 'error'
  selectedId: string | null
  onSelect: (id: string | null) => void
  retry: () => void
}

// KindergartenExplorer keeps every map overlay in the same fullscreen frame.
export function KindergartenExplorer({ data, status, selectedId, onSelect, retry }: KindergartenExplorerProps) {
  const [detailsId, setDetailsId] = useState<string | null>(null)
  const [reveal, setReveal] = useState<{ id: string; revision: number } | null>(null)
  const detailsPanel = useRef<HTMLDivElement>(null)
  const detailsTrigger = useRef<HTMLElement | null>(null)
  const details = data?.features.find((feature) => feature.id === detailsId)
  useEffect(() => {
    if (details) detailsPanel.current?.querySelector<HTMLButtonElement>('button')?.focus({ preventScroll: true })
  }, [details])
  function closeDetails() {
    setDetailsId(null)
    if (detailsTrigger.current?.isConnected) detailsTrigger.current.focus({ preventScroll: true })
  }
  function escape(event: KeyboardEvent, close: () => void) {
    if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close() }
  }
  function showDetails(feature: LocationFeature, trigger: HTMLElement) {
    detailsTrigger.current = trigger
    setDetailsId(feature.id)
    onSelect(feature.id)
  }
  function selectCard(id: string) {
    setDetailsId(null)
    onSelect(id)
    const feature = data?.features.find((feature) => feature.id === id)
    if (feature?.properties.location_role === 'seat' && document.activeElement instanceof HTMLElement) showDetails(feature, document.activeElement)
  }
  return <FullscreenFrame className="kindergarten-explorer">
    <KindergartenMap collection={data} selectedId={selectedId} onSelect={(id) => { setDetailsId(null); onSelect(id); setReveal((previous) => ({ id, revision: (previous?.revision ?? 0) + 1 })) }} />
    {status === 'loading' && <p className="explorer-notice" role="status">Učitavanje objekata…</p>}
    {data && <p className="sr-only" role="status">{data.metadata.total} rezultata · {data.metadata.mapped} na karti · {data.metadata.unmapped} bez koordinata</p>}
    {status === 'error' && <div className="explorer-notice" role="alert"><p>Podatke nije moguće učitati. Provjerite vezu i pokušajte ponovno.</p><button className="text-button" onClick={() => { setDetailsId(null); setReveal(null); retry() }}>Pokušaj ponovno</button></div>}
    {data?.features.length === 0 && <p className="explorer-notice" role="status">Nema dostupnih vrtićkih objekata.</p>}
    {!!data?.features.length && <LocationCarousel features={data.features} selectedId={selectedId} detailsId={details?.id ?? null} reveal={reveal} onSelect={selectCard} onDetails={showDetails} />}
    {details && <div ref={detailsPanel} className="explorer-panel details-panel" onKeyDown={(event) => escape(event, closeDetails)}><LocationDetails feature={details} onClose={closeDetails} /></div>}
  </FullscreenFrame>
}
