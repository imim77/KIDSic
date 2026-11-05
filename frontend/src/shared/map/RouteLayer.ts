import L from 'leaflet'
import { decodePolyline } from './polyline'

export interface MapRoute {
  home: [longitude: number, latitude: number]
  work: [longitude: number, latitude: number]
  legs: { geometry: string | null; mode: string }[]
}

// The timetable is CC BY 4.0, which requires crediting it wherever it is used.
const timetableCredit = 'Vozni red: vekejsn GTFS, CC BY 4.0'

// RouteLayer draws sourced route shapes without inventing missing segments.
export class RouteLayer {
  private map: L.Map
  private layer: L.LayerGroup

  constructor(map: L.Map) {
    this.map = map
    this.layer = L.layerGroup().addTo(map)
  }

  show(route: MapRoute | null): L.LatLngTuple[] {
    this.layer.clearLayers()
    // Removing first keeps the credit from repeating when routes change.
    this.map.attributionControl?.removeAttribution(timetableCredit)
    if (!route) return []
    this.map.attributionControl?.addAttribution(timetableCredit)
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

  dispose() {
    this.map.attributionControl?.removeAttribution(timetableCredit)
    this.layer.remove()
  }
}
