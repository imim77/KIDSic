import L from 'leaflet'
import type { Nearby } from '../locations/types'

type Coordinates = [number, number]

// NearbyLayer draws the search radius below pins and handles point picking.
export class NearbyLayer {
  private map: L.Map
  private layer: L.LayerGroup
  private onPick: (near: Coordinates) => void
  private picking = false

  constructor(map: L.Map, onPick: (near: Coordinates) => void) {
    this.map = map
    this.onPick = onPick
    this.layer = L.layerGroup().addTo(map)
    map.on('click', this.pick)
  }

  show(nearby: Nearby | null) {
    this.layer.clearLayers()
    if (!nearby) return
    const [lng, lat] = nearby.near
    // Leaflet measures metres on a sphere; the API uses the spheroid.
    L.circle([lat, lng], {
      radius: nearby.radius_m, color: '#03594d', weight: 2, dashArray: '4 4',
      fillColor: '#ffff94', fillOpacity: .18, interactive: false,
    }).addTo(this.layer)
    L.circleMarker([lat, lng], {
      radius: 8, color: '#03594d', weight: 3,
      fillColor: '#ffff94', fillOpacity: 1, interactive: false,
    }).addTo(this.layer)
  }

  setPicking(picking: boolean) {
    this.picking = picking
    this.map.getContainer().style.cursor = picking ? 'crosshair' : ''
  }

  dispose() {
    this.map.off('click', this.pick)
    this.layer.remove()
  }

  private pick = (event: L.LeafletMouseEvent) => {
    if (this.picking) this.onPick([event.latlng.lng, event.latlng.lat])
  }
}
