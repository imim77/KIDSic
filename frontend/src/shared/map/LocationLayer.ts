import type { GeoJSONSource, Map, MapLayerMouseEvent } from 'mapbox-gl'
import type { FeatureCollection, Point } from 'geojson'
import type { LocationCollection, LocationFeature, LocationProperties } from '../locations/types'

const sourceId = 'kindergarten-locations'
const clustersId = 'kindergarten-clusters'
const pointsId = 'kindergarten-points'
const selectionSourceId = 'kindergarten-selection'
// Mirrors theme.css tokens; Mapbox paint properties cannot read CSS variables.
const palette = { ink: '#03594d', violet: '#c88cfd', orange: '#ff9124' }

// LocationLayer keeps one clustered source alive as directory results change.
export class LocationLayer {
  private map: Map
  private data: FeatureCollection<Point, LocationProperties> = { type: 'FeatureCollection', features: [] }
  private onSelect: (id: string) => void
  private disposed = false
  private cameraRevision = 0
  private selectedId: string | null = null
  private selection: FeatureCollection<Point, LocationProperties> = { type: 'FeatureCollection', features: [] }

  constructor(map: Map, onSelect: (id: string) => void) {
    this.map = map
    this.onSelect = onSelect
    map.on('style.load', this.mount)
    map.on('click', clustersId, this.expandCluster)
    map.on('click', pointsId, this.selectPoint)
    map.on('mouseenter', clustersId, this.showPointer)
    map.on('mouseleave', clustersId, this.hidePointer)
    map.on('mouseenter', pointsId, this.showPointer)
    map.on('mouseleave', pointsId, this.hidePointer)
    if (map.isStyleLoaded()) this.mount()
  }

  update(collection: LocationCollection | null) {
    this.cameraRevision += 1
    this.data = {
      type: 'FeatureCollection',
      features: (collection?.features ?? []).filter(
        (feature): feature is LocationFeature & { geometry: Point } => feature.geometry !== null,
      ),
    }
    this.source()?.setData(this.data)
    this.select(this.selectedId, false)
    const coordinates = this.data.features.map((feature) => feature.geometry.coordinates)
    if (!coordinates.length) return
    const longitudes = coordinates.map(([longitude]) => longitude)
    const latitudes = coordinates.map(([, latitude]) => latitude)
    this.map.fitBounds([
      [Math.min(...longitudes), Math.min(...latitudes)],
      [Math.max(...longitudes), Math.max(...latitudes)],
    ], { padding: this.cameraPadding(), maxZoom: 14, duration: 0 })
  }

  select(id: string | null, focus = true) {
    if (focus) this.cameraRevision += 1
    this.selectedId = id
    const feature = this.data.features.find((item) => item.id === id)
    this.selection = { type: 'FeatureCollection', features: feature ? [feature] : [] }
    ;(this.map.getSource(selectionSourceId) as GeoJSONSource | undefined)?.setData(this.selection)
    if (feature && focus) this.map.jumpTo({
      center: feature.geometry.coordinates as [number, number],
      zoom: Math.max(this.map.getZoom(), 15),
      padding: this.cameraPadding(),
    })
  }

  resize() {
    // Padding follows the card deck while the logical center and zoom stay put.
    this.map.setPadding(this.cameraPadding())
  }

  dispose() {
    this.disposed = true
    this.map.off('style.load', this.mount)
    this.map.off('click', clustersId, this.expandCluster)
    this.map.off('click', pointsId, this.selectPoint)
    this.map.off('mouseenter', clustersId, this.showPointer)
    this.map.off('mouseleave', clustersId, this.hidePointer)
    this.map.off('mouseenter', pointsId, this.showPointer)
    this.map.off('mouseleave', pointsId, this.hidePointer)
  }

  private source() { return this.map.getSource(sourceId) as GeoJSONSource | undefined }
  private cameraPadding() {
    const frame = this.map.getContainer?.().closest('.kindergarten-explorer')
    if (!frame) return { top: 50, bottom: 50, left: 50, right: 50 }
    const height = frame.clientHeight
    const deck = frame.querySelector('.location-carousel')?.getBoundingClientRect().height ?? 0
    // Center selected pins in the map area above the cards, also in landscape.
    const bottom = Math.min(deck + 45, height * .6)
    return { top: Math.min(90, height * .2), bottom, left: 45, right: 45 }
  }
  private showPointer = () => { this.map.getCanvas().style.cursor = 'pointer' }
  private hidePointer = () => { this.map.getCanvas().style.cursor = '' }
  private selectPoint = (event: MapLayerMouseEvent) => {
    const feature = event.features?.[0]
    // Vector tiling can discard UUID feature IDs; retain the canonical property.
    const locationId = feature?.properties?.location_id
    const id = typeof locationId === 'string' && locationId.trim() ? locationId : feature?.id
    if (id !== undefined) this.onSelect(String(id))
  }
  private expandCluster = (event: MapLayerMouseEvent) => {
    const feature = event.features?.[0]
    if (feature?.geometry.type !== 'Point') return
    const center = feature.geometry.coordinates as [number, number]
    const clusterId = Number(feature.properties?.cluster_id)
    const revision = ++this.cameraRevision
    this.source()?.getClusterExpansionZoom(clusterId, (error, zoom) => {
      if (!error && zoom != null && !this.disposed && revision === this.cameraRevision) this.map.easeTo({ center, zoom })
    })
  }
  private mount = () => {
    if (this.map.getSource(sourceId)) return
    this.map.addSource(sourceId, { type: 'geojson', data: this.data, cluster: true, clusterMaxZoom: 14, clusterRadius: 42 })
    this.map.addLayer({
      id: clustersId, type: 'circle', source: sourceId, filter: ['has', 'point_count'],
      paint: { 'circle-color': palette.orange, 'circle-radius': ['step', ['get', 'point_count'], 18, 20, 23, 60, 28], 'circle-stroke-color': palette.ink, 'circle-stroke-width': 2 },
    })
    this.map.addLayer({
      id: 'kindergarten-cluster-count', type: 'symbol', source: sourceId, filter: ['has', 'point_count'],
      layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-size': 12 },
      paint: { 'text-color': palette.ink },
    })
    this.map.addLayer({
      id: pointsId, type: 'circle', source: sourceId, filter: ['!', ['has', 'point_count']],
      paint: { 'circle-color': palette.violet, 'circle-radius': 7, 'circle-stroke-color': palette.ink, 'circle-stroke-width': 2 },
    })
    this.map.addSource(selectionSourceId, { type: 'geojson', data: this.selection })
    this.map.addLayer({
      id: 'kindergarten-selected-point', type: 'circle', source: selectionSourceId,
      paint: { 'circle-color': palette.violet, 'circle-radius': 11, 'circle-stroke-color': palette.ink, 'circle-stroke-width': 4 },
    })
  }
}
