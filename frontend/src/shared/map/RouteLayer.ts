import L from 'leaflet'
import gsap from 'gsap'
import { decodePolyline } from './polyline'
import { reducedMotion } from '../motion/reducedMotion'

export interface MapRoute {
  home: [longitude: number, latitude: number]
  work: [longitude: number, latitude: number]
  legs: { geometry: string | null; mode: string }[]
}

const drawSeconds = 1.6 // whole route, shared by legs in proportion to length

// The timetable is CC BY 4.0, which requires crediting it wherever it is used.
const timetableCredit = 'Vozni red: vekejsn GTFS, CC BY 4.0'

// RouteLayer draws sourced route shapes without inventing missing segments.
export class RouteLayer {
  private map: L.Map
  private layer: L.LayerGroup
  private shown: MapRoute | null = null
  private points: L.LatLngTuple[] = []
  private drawing: gsap.core.Timeline | null = null

  constructor(map: L.Map) {
    this.map = map
    this.layer = L.layerGroup().addTo(map)
  }

  // show is called again on every resize; the same route keeps its layers, so
  // a running drawing is not cut short, and only a new route is drawn again.
  show(route: MapRoute | null): L.LatLngTuple[] {
    if (route === this.shown && (route === null || this.layer.getLayers().length)) return this.points
    this.shown = route
    this.drawing?.kill()
    this.drawing = null
    this.layer.clearLayers()
    // Removing first keeps the credit from repeating when routes change.
    this.map.attributionControl?.removeAttribution(timetableCredit)
    this.points = []
    if (!route) return this.points
    this.map.attributionControl?.addAttribution(timetableCredit)
    const points: L.LatLngTuple[] = []
    const lines: { line: L.Polyline; dash?: string; metres: number }[] = []
    for (const leg of route.legs) {
      if (!leg.geometry) continue
      try {
        const shape = decodePolyline(leg.geometry)
        if (shape.length < 2 || shape.some(([lat, lng]) => !Number.isFinite(lat) || !Number.isFinite(lng)
          || Math.abs(lat) > 90 || Math.abs(lng) > 180)) continue
        points.push(...shape)
        const dash = leg.mode === 'WALK' ? '6 8' : undefined
        const line = L.polyline(shape, {
          color: leg.mode === 'WALK' ? '#03594d' : '#376fbe', weight: 5, dashArray: dash, interactive: false,
        }).addTo(this.layer)
        const metres = shape.slice(1).reduce((sum, point, i) => sum + L.latLng(shape[i]).distanceTo(point), 0)
        lines.push({ line, dash, metres })
      } catch { /* Keep valid legs visible if one optional shape is malformed. */ }
    }
    const ends = ([
      [route.home, 'Dom', '#82eda6'], [route.work, 'Posao', '#f6bbfd'],
    ] as const).map(([coordinates, label, color]) => {
      const [lng, lat] = coordinates
      points.push([lat, lng])
      return L.circleMarker([lat, lng], {
        radius: 9, color: '#03594d', weight: 2, fillColor: color, fillOpacity: 1,
      }).bindTooltip(label, { permanent: true, direction: 'top' }).addTo(this.layer)
    })
    if (!reducedMotion()) this.draw(lines, ends)
    this.points = points
    return points
  }

  // draw pops Dom in, traces each leg from home to work, then pops Posao in.
  // pathLength="1" keeps the trace in step when a zoom reprojects the path.
  private draw(lines: { line: L.Polyline; dash?: string; metres: number }[], [home, work]: L.CircleMarker[]) {
    const pop = (marker: L.CircleMarker) => [marker.getElement(), marker.getTooltip()?.getElement()]
      .filter((element): element is HTMLElement | SVGElement => !!element)
    const total = lines.reduce((sum, { metres }) => sum + metres, 0) || 1
    const timeline = gsap.timeline()
    timeline.from(pop(home), { opacity: 0, duration: 0.3, ease: 'power2.out', clearProps: 'opacity' })
    for (const { line, dash, metres } of lines) {
      const path = line.getElement()
      if (!(path instanceof SVGElement)) continue
      path.setAttribute('pathLength', '1')
      path.setAttribute('stroke-dasharray', '1 1')
      path.setAttribute('stroke-dashoffset', '1')
      timeline.to(path, {
        attr: { 'stroke-dashoffset': 0 }, ease: 'none',
        duration: Math.max(0.2, drawSeconds * metres / total),
        onComplete: () => restore(path, dash),
      })
    }
    timeline.from(pop(work), { opacity: 0, duration: 0.3, ease: 'power2.out', clearProps: 'opacity' })
    this.drawing = timeline
  }

  dispose() {
    this.drawing?.kill()
    this.map.attributionControl?.removeAttribution(timetableCredit)
    this.layer.remove()
  }
}

// restore hands the path back to Leaflet's own dash style.
function restore(path: SVGElement, dash?: string) {
  path.removeAttribute('pathLength')
  path.removeAttribute('stroke-dashoffset')
  if (dash) path.setAttribute('stroke-dasharray', dash)
  else path.removeAttribute('stroke-dasharray')
}
