import { useEffect, useRef, useState } from 'react'
import type { Map } from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import './map.css'

const accessToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN?.trim()

export function KindergartenMap() {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<Map | null>(null)
  const [status, setStatus] = useState('Karta se učitava…')

  useEffect(() => {
    if (!accessToken || !containerRef.current) return
    let map: Map | undefined
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
      map?.remove()
      map = undefined
      mapRef.current = null
      if (!disposed) setStatus('Kartu nije moguće pokrenuti u ovom pregledniku. Objekte možete pregledati na popisu.')
    })
    return () => {
      disposed = true
      observer?.disconnect()
      map?.remove()
      mapRef.current = null
    }
  }, [])

  return (
    <div className="kindergarten-map">
      <div className="map-canvas" ref={containerRef} />
      {(!accessToken || status) && (
        <div className="map-message" role="status">
          <span className="map-message-marker" aria-hidden="true">↗</span>
          <h2>{accessToken ? 'Karta Zagreba' : 'Karta još nije dostupna'}</h2>
          <p>{accessToken ? status : 'Karta trenutačno nije dostupna. Objekte možete pregledati na popisu.'}</p>
        </div>
      )}
    </div>
  )
}
