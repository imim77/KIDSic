import { useEffect, useRef, useState } from 'react'
import type { Map } from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { LocationLayer } from './LocationLayer'
import { providerColors, providerLabels } from '../locations/types'
import type { LocationCollection } from '../locations/types'
import './map.css'

const accessToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN?.trim()

interface KindergartenMapProps {
  collection?: LocationCollection | null
  onSelect?: (id: string) => void
  selectedId?: string | null
}

export function KindergartenMap({ collection = null, onSelect, selectedId = null }: KindergartenMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<Map | null>(null)
  const layerRef = useRef<LocationLayer | null>(null)
  const collectionRef = useRef(collection)
  const onSelectRef = useRef(onSelect)
  const selectedIdRef = useRef(selectedId)
  const [status, setStatus] = useState('Karta se učitava…')

  useEffect(() => {
    if (!accessToken || !containerRef.current) return
    let map: Map | undefined
    let layer: LocationLayer | undefined
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
      layer = new LocationLayer(map, (id) => onSelectRef.current?.(id))
      layerRef.current = layer
      layer.update(collectionRef.current)
      layer.select(selectedIdRef.current)
      map.addControl(new mapboxgl.NavigationControl(), 'top-right')
      map.on('load', () => { if (!disposed) setStatus('') })
      map.on('style.load', () => { if (!disposed) setStatus('') })
      map.on('error', () => {
        if (!disposed) setStatus('Kartu nije moguće učitati. Provjerite internetsku vezu ili pregledajte objekte na popisu.')
      })
      observer = new ResizeObserver(() => map?.resize())
      observer.observe(containerRef.current)
    }).catch(() => {
      observer?.disconnect()
      layer?.dispose()
      if (layerRef.current === layer) layerRef.current = null
      map?.remove()
      if (mapRef.current === map) mapRef.current = null
      map = undefined
      if (!disposed) setStatus('Kartu nije moguće pokrenuti u ovom pregledniku. Objekte možete pregledati na popisu.')
    })
    return () => {
      disposed = true
      observer?.disconnect()
      layer?.dispose()
      if (layerRef.current === layer) layerRef.current = null
      map?.remove()
      if (mapRef.current === map) mapRef.current = null
    }
  }, [])

  useEffect(() => {
    collectionRef.current = collection
    layerRef.current?.update(collection)
  }, [collection])

  useEffect(() => { onSelectRef.current = onSelect }, [onSelect])
  useEffect(() => {
    selectedIdRef.current = selectedId
    layerRef.current?.select(selectedId)
  }, [selectedId])

  return (
    <div className="kindergarten-map">
      <div className="map-canvas" ref={containerRef} />
      {accessToken && !status && <div className="map-legend" aria-label="Legenda karte">
        {Object.entries(providerColors).map(([kind, color]) => <span className="legend-entry" key={kind}><span className="legend-dot" style={{ background: color }} />{providerLabels[kind as keyof typeof providerLabels]}</span>)}
        <span className="legend-entry"><span className="legend-cluster">2</span>Skupina objekata</span>
        <span className="legend-entry"><span className="legend-selected" />Odabrani objekt</span>
      </div>}
      {accessToken && !status && collection?.metadata.mapped === 0 && <p className="map-data-message" role="status">Rezultati nemaju potvrđene koordinate. Pregledajte ih na popisu.</p>}
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
