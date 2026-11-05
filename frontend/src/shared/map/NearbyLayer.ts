import type { GeoJSONSource, Map, MapMouseEvent } from 'mapbox-gl'
import type { FeatureCollection, Point, Polygon } from 'geojson'
import type { Nearby } from '../locations/types'

const areaSourceId = 'nearby-area'
const centreSourceId = 'nearby-centre'
const earthRadiusM = 6_371_008.8
// Mirrors theme.css tokens; Mapbox paint properties cannot read CSS variables.
const palette = { ink: '#03594d', lemon: '#ffff94' }

type Coordinates = [number, number]

// circle approximates the searched radius; the API measures on the spheroid,
// so the drawn edge can differ from the result boundary by a few metres.
function circle([longitude, latitude]: Coordinates, radiusM: number, steps = 64): Polygon {
  const lat = latitude * Math.PI / 180
  const lon = longitude * Math.PI / 180
  const angular = radiusM / earthRadiusM
  const ring: Coordinates[] = []
  for (let step = 0; step <= steps; step += 1) {
    const bearing = 2 * Math.PI * step / steps
    const pointLat = Math.asin(Math.sin(lat) * Math.cos(angular) + Math.cos(lat) * Math.sin(angular) * Math.cos(bearing))
    const pointLon = lon + Math.atan2(Math.sin(bearing) * Math.sin(angular) * Math.cos(lat),
      Math.cos(angular) - Math.sin(lat) * Math.sin(pointLat))
    ring.push([pointLon * 180 / Math.PI, pointLat * 180 / Math.PI])
  }
  return { type: 'Polygon', coordinates: [ring] }
}

// NearbyLayer draws the chosen point and radius, and turns the next map click
// into a new point while picking. Create it before LocationLayer so the area
// stays below kindergarten pins.
export class NearbyLayer {
  private map: Map
  private onPick: (near: Coordinates) => void
  private nearby: Nearby | null = null
  private picking = false

  constructor(map: Map, onPick: (near: Coordinates) => void) {
    this.map = map
    this.onPick = onPick
    map.on('style.load', this.mount)
    map.on('click', this.pick)
    if (map.isStyleLoaded()) this.mount()
  }

  show(nearby: Nearby | null) {
    this.nearby = nearby
    ;(this.map.getSource(areaSourceId) as GeoJSONSource | undefined)?.setData(this.area())
    ;(this.map.getSource(centreSourceId) as GeoJSONSource | undefined)?.setData(this.centre())
  }

  setPicking(picking: boolean) {
    this.picking = picking
    this.map.getCanvas().style.cursor = picking ? 'crosshair' : ''
  }

  dispose() {
    this.map.off('style.load', this.mount)
    this.map.off('click', this.pick)
  }

  private area(): FeatureCollection<Polygon> {
    return { type: 'FeatureCollection', features: this.nearby ? [{
      type: 'Feature', properties: {}, geometry: circle(this.nearby.near, this.nearby.radius_m),
    }] : [] }
  }

  private centre(): FeatureCollection<Point> {
    return { type: 'FeatureCollection', features: this.nearby ? [{
      type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: this.nearby.near },
    }] : [] }
  }

  private pick = (event: MapMouseEvent) => {
    if (this.picking) this.onPick([event.lngLat.lng, event.lngLat.lat])
  }

  private mount = () => {
    if (this.map.getSource(areaSourceId)) return
    this.map.addSource(areaSourceId, { type: 'geojson', data: this.area() })
    this.map.addSource(centreSourceId, { type: 'geojson', data: this.centre() })
    this.map.addLayer({
      id: 'nearby-area-fill', type: 'fill', source: areaSourceId,
      paint: { 'fill-color': palette.lemon, 'fill-opacity': 0.18 },
    })
    this.map.addLayer({
      id: 'nearby-area-line', type: 'line', source: areaSourceId,
      paint: { 'line-color': palette.ink, 'line-width': 2, 'line-dasharray': [2, 2] },
    })
    this.map.addLayer({
      id: 'nearby-centre', type: 'circle', source: centreSourceId,
      paint: { 'circle-color': palette.lemon, 'circle-radius': 8, 'circle-stroke-color': palette.ink, 'circle-stroke-width': 3 },
    })
  }
}
