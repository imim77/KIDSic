import { useState } from 'react'
import { FullscreenFrame, type HostFullscreen } from './FullscreenFrame'
import { KindergartenMap } from '../map/KindergartenMap'
import { LocationCarousel } from '../locations/LocationCarousel'
import type { LocationCollection } from '../locations/types'

interface KindergartenExplorerProps {
  data: LocationCollection | null
  status: 'loading' | 'ready' | 'error'
  selectedId: string | null
  onSelect: (id: string | null) => void
  retry: () => void
  hostFullscreen?: HostFullscreen
  notice?: string
}

// KindergartenExplorer keeps every map overlay in the same fullscreen frame.
export function KindergartenExplorer({ data, status, selectedId, onSelect, retry, hostFullscreen, notice }: KindergartenExplorerProps) {
  const [reveal, setReveal] = useState<{ id: string; revision: number } | null>(null)
  return <FullscreenFrame className="kindergarten-explorer" hostFullscreen={hostFullscreen}>
    <KindergartenMap collection={data} selectedId={selectedId} onSelect={(id) => { onSelect(id); setReveal((previous) => ({ id, revision: (previous?.revision ?? 0) + 1 })) }} />
    {status === 'loading' && <p className="explorer-notice" role="status">{notice ?? 'Učitavanje objekata…'}</p>}
    {data && <p className="sr-only" role="status">{data.metadata.total} rezultata · {data.metadata.mapped} na karti · {data.metadata.unmapped} bez koordinata</p>}
    {status === 'error' && <div className="explorer-notice" role="alert"><p>Podatke nije moguće učitati. Provjerite vezu i pokušajte ponovno.</p><button className="text-button" onClick={() => { setReveal(null); retry() }}>Pokušaj ponovno</button></div>}
    {data?.features.length === 0 && <p className="explorer-notice" role="status">Nema dostupnih vrtićkih objekata.</p>}
    {!!data?.features.length && <LocationCarousel features={data.features} selectedId={selectedId} reveal={reveal} onSelect={onSelect} />}
  </FullscreenFrame>
}
