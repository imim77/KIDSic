import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { decodePolyline } from './polyline'

export type Point = { lat: number; lon: number }
export type MapFacility = { id: string; name: string; point: Point }


export default function CommuteMap({ home, work, facilities, geometries }: {
  home: Point; work: Point; facilities: MapFacility[]; geometries: string[]
}) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  useEffect(() => {
    const instance = L.map(container.current!).setView([45.331, 14.431], 13)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(instance)
    map.current = instance
    return () => { instance.remove(); map.current = null }
  }, [])
  useEffect(() => {
    if (!map.current) return
    const layer = L.layerGroup().addTo(map.current)
    const marker = (point: Point, label: string, color: string) => {
      const content = document.createElement('span'); content.textContent = label
      L.circleMarker([point.lat, point.lon], { radius: 9, color: '#03594d', weight: 2,
        fillColor: color, fillOpacity: 1 }).bindTooltip(content).addTo(layer)
    }
    marker(home, 'Dom', '#82eda6'); marker(work, 'Posao', '#f6bbfd')
    facilities.forEach(f => marker(f.point, f.name, '#ffff94'))
    const routePoints: L.LatLngTuple[] = []
    geometries.forEach(encoded => {
      try {
        const points = decodePolyline(encoded)
        routePoints.push(...points)
        L.polyline(points, { color: '#03594d', weight: 5 }).addTo(layer)
      }
      catch { /* A malformed optional shape must not hide the itinerary. */ }
    })
    const points: L.LatLngTuple[] = [...routePoints, [home.lat,home.lon],[work.lat,work.lon], ...facilities.map(f => [f.point.lat,f.point.lon] as L.LatLngTuple)]
    map.current.fitBounds(L.latLngBounds(points),{padding:[25,25],maxZoom:15})
    return () => { layer.remove() }
  }, [home, work, facilities, geometries])
  return <div ref={container} className="day-map" role="region" aria-label="Karta najboljih putova kroz riječke vrtiće" />
}
