import { useEffect, useRef, useState, type ReactNode } from 'react'
import type { Map } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { LocationLayer } from './LocationLayer'
import type { NearbyLayer } from './NearbyLayer'
import type { MapRoute, RouteLayer } from './RouteLayer'
import type { LocationCollection, Nearby } from '../../types'
import { providerColors } from '../../types'
import './map.css'

interface KindergartenMapProps {
  route?: MapRoute | null
  collection?: LocationCollection | null
  onSelect?: (id: string) => void
  selectedId?: string | null
  nearby?: Nearby | null

  picking?: boolean
  onPick?: (near: [number, number]) => void

  overlay?: (mapReady: boolean) => ReactNode
}

export function KindergartenMap({ route = null, collection = null, onSelect, selectedId = null, nearby = null, picking = false, onPick, overlay }: KindergartenMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const routeRef = useRef(route)
  const routeLayerRef = useRef<RouteLayer | null>(null)
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
    if (!containerRef.current) return
    let map: Map | undefined
    let routeLayer: RouteLayer | undefined
    let layer: LocationLayer | undefined
    let nearbyLayer: NearbyLayer | undefined
    let observer: ResizeObserver | undefined
    let disposed = false

    void Promise.all([
      import('leaflet'), import('./LocationLayer'), import('./NearbyLayer'), import('./RouteLayer'),
    ]).then(([{ default: L }, { LocationLayer }, { NearbyLayer }, { RouteLayer }]) => {
      if (disposed || !containerRef.current) return
      map = L.map(containerRef.current, {
        center: [45.815, 15.9819], zoom: 11, maxZoom: 19, zoomControl: false,
      })
      L.control.zoom({ position: 'topright' }).addTo(map)
      const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      })
      tiles.on('tileerror', () => {
        if (!disposed) setStatus('Podlogu karte nije moguće učitati. Provjerite internetsku vezu ili pregledajte objekte na popisu.')
      })
      tiles.on('tileload', () => { if (!disposed) setStatus('') })
      tiles.addTo(map)
      mapRef.current = map
      nearbyLayer = new NearbyLayer(map, (near) => onPickRef.current?.(near))
      nearbyLayerRef.current = nearbyLayer
      nearbyLayer.show(nearbyRef.current)
      nearbyLayer.setPicking(pickingRef.current)
      routeLayer = new RouteLayer(map)
      routeLayerRef.current = routeLayer
      layer = new LocationLayer(map, (id) => { if (!pickingRef.current) onSelectRef.current?.(id) })
      layerRef.current = layer
      layer.update(collectionRef.current)
      layer.select(selectedIdRef.current, !routeRef.current)
      if (routeRef.current) layer.fit(routeLayer.show(routeRef.current))
      setStatus('')
      observer = new ResizeObserver(() => {
        map?.invalidateSize({ pan: false })
        if (routeRef.current) layer?.fit(routeLayer?.show(routeRef.current))
        else layer?.resize()
      })
      observer.observe(containerRef.current)
    }).catch(() => {
      observer?.disconnect()
      layer?.dispose()
      nearbyLayer?.dispose()
      routeLayer?.dispose()
      routeLayerRef.current = null
      if (layerRef.current === layer) layerRef.current = null
      if (nearbyLayerRef.current === nearbyLayer) nearbyLayerRef.current = null
      map?.remove()
      if (mapRef.current === map) mapRef.current = null
      map = undefined
      layer = undefined
      nearbyLayer = undefined
      routeLayer = undefined
      if (!disposed) setStatus('Kartu nije moguće pokrenuti u ovom pregledniku. Objekte možete pregledati na popisu.')
    })
    return () => {
      disposed = true
      observer?.disconnect()
      layer?.dispose()
      nearbyLayer?.dispose()
      routeLayer?.dispose()
      routeLayerRef.current = null
      if (layerRef.current === layer) layerRef.current = null
      if (nearbyLayerRef.current === nearbyLayer) nearbyLayerRef.current = null
      map?.remove()
      if (mapRef.current === map) mapRef.current = null
    }
  }, [])

  useEffect(() => {
    collectionRef.current = collection
    layerRef.current?.update(collection)
    if (routeRef.current) layerRef.current?.fit(routeLayerRef.current?.show(routeRef.current))
  }, [collection])

  useEffect(() => {
    routeRef.current = route
    const points = routeLayerRef.current?.show(route)
    if (route) layerRef.current?.fit(points)
  }, [route])

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
    layerRef.current?.select(selectedId, !routeRef.current)
  }, [selectedId])

  return (
    <div className="kindergarten-map">
      <div className="map-canvas" ref={containerRef} role="region" aria-label="Karta lokacija vrtića" />
      <div className="map-overlay">
        {!status && !!collection?.metadata.mapped && <ul className="map-provider-legend" aria-label="Vrste pružatelja na karti">
          {([
            ['municipal', 'Javni i ostali'], ['private', 'Privatni'],
            ['religious', 'Vjerski'], ['childminder', 'Dadilje'],
          ] as const).map(([kind, label]) => <li key={kind}>
            <span aria-hidden="true" style={{ backgroundColor: providerColors[kind] }} />{label}
          </li>)}
        </ul>}
        {overlay?.(!status)}
        {!status && collection?.metadata.mapped === 0 && <p className="map-data-message" role="status">Rezultati nemaju potvrđene koordinate. Pregledajte ih na popisu.</p>}
      </div>
      {status && (
        <div className="map-message" role="status">
          <span className="map-message-marker" aria-hidden="true">↗</span>
          <h2>Karta lokacija</h2>
          <p>{status}</p>
        </div>
      )}
    </div>
  )
}
