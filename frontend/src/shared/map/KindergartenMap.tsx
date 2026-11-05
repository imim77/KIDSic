import { useEffect, useRef, useState, type ReactNode } from 'react'
import type { Map } from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { LocationLayer } from './LocationLayer'
import { NearbyLayer } from './NearbyLayer'
import type { LocationCollection, Nearby } from '../locations/types'
import { providerColors } from '../locations/types'
import './map.css'

const accessToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN?.trim()

interface KindergartenMapProps {
  collection?: LocationCollection | null
  onSelect?: (id: string) => void
  selectedId?: string | null
  nearby?: Nearby | null
  // While picking, the next map click becomes the nearby point, not a selection.
  picking?: boolean
  onPick?: (near: [number, number]) => void
  // overlay renders map-level controls; mapReady tells whether clicks can work.
  overlay?: (mapReady: boolean) => ReactNode
}

export function KindergartenMap({ collection = null, onSelect, selectedId = null, nearby = null, picking = false, onPick, overlay }: KindergartenMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<Map | null>(null)
  const layerRef = useRef<LocationLayer | null>(null)
  const collectionRef = useRef(collection)
  const onSelectRef = useRef(onSelect)
  const selectedIdRef = useRef(selectedId)
  const nearbyLayerRef = useRef<NearbyLayer | null>(null)
  const nearbyRef = useRef(nearby)
  const pickingRef = useRef(picking)
  const onPickRef = useRef(onPick)
  const [status, setStatus] = useState('Karta se učitava…')

  useEffect(() => {
    if (!accessToken || !containerRef.current) return
    let map: Map | undefined
    let layer: LocationLayer | undefined
    let nearbyLayer: NearbyLayer | undefined
    let observer: ResizeObserver | undefined
    let disposed = false
    // Loading Mapbox separately keeps the directory usable while it initializes.
    void import('mapbox-gl').then(({ default: mapboxgl }) => {
      if (disposed || !containerRef.current) return
      if (!mapboxgl.supported()) throw new Error('WebGL nije dostupan')
      map = new mapboxgl.Map({
        container: containerRef.current,
        accessToken,
        style: 'mapbox://styles/mapbox/light-v11',
        center: [15.9819, 45.815],
        zoom: 11,
        attributionControl: true,
      })
      mapRef.current = map
      nearbyLayer = new NearbyLayer(map, (near) => onPickRef.current?.(near))
      nearbyLayerRef.current = nearbyLayer
      nearbyLayer.show(nearbyRef.current)
      nearbyLayer.setPicking(pickingRef.current)
      layer = new LocationLayer(map, (id) => { if (!pickingRef.current) onSelectRef.current?.(id) })
      layerRef.current = layer
      layer.update(collectionRef.current)
      layer.select(selectedIdRef.current)
      map.addControl(new mapboxgl.NavigationControl(), 'top-right')
      map.on('load', () => { if (!disposed) setStatus('') })
      map.on('style.load', () => { if (!disposed) setStatus('') })
      map.on('error', () => {
        if (!disposed) setStatus('Kartu nije moguće učitati. Provjerite internetsku vezu ili pregledajte objekte na popisu.')
      })
      observer = new ResizeObserver(() => { map?.resize(); layer?.resize() })
      observer.observe(containerRef.current)
    }).catch(() => {
      observer?.disconnect()
      layer?.dispose()
      nearbyLayer?.dispose()
      if (layerRef.current === layer) layerRef.current = null
      if (nearbyLayerRef.current === nearbyLayer) nearbyLayerRef.current = null
      map?.remove()
      if (mapRef.current === map) mapRef.current = null
      map = undefined
      if (!disposed) setStatus('Kartu nije moguće pokrenuti u ovom pregledniku. Objekte možete pregledati na popisu.')
    })
    return () => {
      disposed = true
      observer?.disconnect()
      layer?.dispose()
      nearbyLayer?.dispose()
      if (layerRef.current === layer) layerRef.current = null
      if (nearbyLayerRef.current === nearbyLayer) nearbyLayerRef.current = null
      map?.remove()
      if (mapRef.current === map) mapRef.current = null
    }
  }, [])

  useEffect(() => {
    collectionRef.current = collection
    layerRef.current?.update(collection)
  }, [collection])

  useEffect(() => { onSelectRef.current = onSelect }, [onSelect])
  useEffect(() => { onPickRef.current = onPick }, [onPick])
  useEffect(() => {
    nearbyRef.current = nearby
    nearbyLayerRef.current?.show(nearby)
  }, [nearby])
  useEffect(() => {
    pickingRef.current = picking
    nearbyLayerRef.current?.setPicking(picking)
  }, [picking])
  useEffect(() => {
    selectedIdRef.current = selectedId
    layerRef.current?.select(selectedId)
  }, [selectedId])

  return (
    <div className="kindergarten-map">
      <div className="map-canvas" ref={containerRef} />
      <div className="map-overlay">
        {accessToken && !status && !!collection?.metadata.mapped && <ul className="map-provider-legend" aria-label="Vrste pružatelja na karti">
          {([
            ['municipal', 'Javni i ostali'], ['private', 'Privatni'],
            ['religious', 'Vjerski'], ['childminder', 'Dadilje'],
          ] as const).map(([kind, label]) => <li key={kind}>
            <span aria-hidden="true" style={{ backgroundColor: providerColors[kind] }} />{label}
          </li>)}
        </ul>}
        {overlay?.(!!accessToken && !status)}
        {accessToken && !status && collection?.metadata.mapped === 0 && <p className="map-data-message" role="status">Rezultati nemaju potvrđene koordinate. Pregledajte ih na popisu.</p>}
      </div>
      {(!accessToken || status) && (
        <div className="map-message" role="status">
          <span className="map-message-marker" aria-hidden="true">↗</span>
          <h2>{accessToken ? 'Karta lokacija' : 'Karta još nije dostupna'}</h2>
          <p>{accessToken ? status : 'Karta trenutačno nije dostupna. Objekte možete pregledati na popisu.'}</p>
        </div>
      )}
    </div>
  )
}
