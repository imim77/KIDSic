import L from 'leaflet'
import { decodePolyline } from './polyline'

export interface MapRoute {
  home: [longitude: number, latitude: number]
  work: [longitude: number, latitude: number]
  legs: { geometry: string | null; mode: string }[]
}

// RouteLayer draws sourced route shapes without inventing missing segments.
export class RouteLayer {
  private layer: L.LayerGroup

  constructor(map: L.Map) {
    this.layer = L.layerGroup().addTo(map)
  }

  show(route: MapRoute | null): L.LatLngTuple[] {
    this.layer.clearLayers()
    if (!route) return []
    const points: L.LatLngTuple[] = []
    for (const leg of route.legs) {
      if (!leg.geometry) continue
      try {
        const shape = decodePolyline(leg.geometry)
        if (shape.length < 2 || shape.some(([lat, lng]) => !Number.isFinite(lat) || !Number.isFinite(lng)
          || Math.abs(lat) > 90 || Math.abs(lng) > 180)) continue
        points.push(...shape)
        L.polyline(shape, {
          color: leg.mode === 'WALK' ? '#03594d' : '#376fbe', weight: 5,
          dashArray: leg.mode === 'WALK' ? '6 8' : undefined, interactive: false,
        }).addTo(this.layer)
      } catch { /* Keep valid legs visible if one optional shape is malformed. */ }
    }
    for (const [coordinates, label, color] of [
      [route.home, 'Dom', '#82eda6'], [route.work, 'Posao', '#f6bbfd'],
    ] as const) {
      const [lng, lat] = coordinates
      points.push([lat, lng])
      L.circleMarker([lat, lng], {
        radius: 9, color: '#03594d', weight: 2, fillColor: color, fillOpacity: 1,
      }).bindTooltip(label, { permanent: true, direction: 'top' }).addTo(this.layer)
    }
    return points
  }

  dispose() { this.layer.remove() }
}
