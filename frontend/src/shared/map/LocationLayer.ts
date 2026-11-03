import type { GeoJSONSource, Map, MapLayerMouseEvent } from 'mapbox-gl'
import type { FeatureCollection, Point } from 'geojson'
import type { LocationCollection, LocationFeature, LocationProperties } from '../locations/types'

const sourceId = 'kindergarten-locations'
const clustersId = 'kindergarten-clusters'
const pointsId = 'kindergarten-points'

// LocationLayer keeps one clustered source alive as directory results change.
export class LocationLayer {
  private map: Map
  private data: FeatureCollection<Point, LocationProperties> = { type: 'FeatureCollection', features: [] }
  private onSelect: (id: string) => void
  private disposed = false

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
    this.data = {
      type: 'FeatureCollection',
      features: (collection?.features ?? []).filter(
        (feature): feature is LocationFeature & { geometry: Point } => feature.geometry !== null,
      ),
    }
    this.source()?.setData(this.data)
    const coordinates = this.data.features.map((feature) => feature.geometry.coordinates)
    if (!coordinates.length) return
    const longitudes = coordinates.map(([longitude]) => longitude)
    const latitudes = coordinates.map(([, latitude]) => latitude)
    this.map.fitBounds([
      [Math.min(...longitudes), Math.min(...latitudes)],
      [Math.max(...longitudes), Math.max(...latitudes)],
    ], { padding: 50, maxZoom: 14, duration: 0 })
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
  private showPointer = () => { this.map.getCanvas().style.cursor = 'pointer' }
  private hidePointer = () => { this.map.getCanvas().style.cursor = '' }
  private selectPoint = (event: MapLayerMouseEvent) => {
    const id = event.features?.[0]?.id
    if (id !== undefined) this.onSelect(String(id))
  }
  private expandCluster = (event: MapLayerMouseEvent) => {
    const feature = event.features?.[0]
    if (feature?.geometry.type !== 'Point') return
    const center = feature.geometry.coordinates as [number, number]
    const clusterId = Number(feature.properties?.cluster_id)
    this.source()?.getClusterExpansionZoom(clusterId, (error, zoom) => {
      if (!error && zoom != null && !this.disposed) this.map.easeTo({ center, zoom })
    })
  }
  private mount = () => {
    if (this.map.getSource(sourceId)) return
    this.map.addSource(sourceId, { type: 'geojson', data: this.data, cluster: true, clusterMaxZoom: 14, clusterRadius: 42 })
    this.map.addLayer({
      id: clustersId, type: 'circle', source: sourceId, filter: ['has', 'point_count'],
      paint: { 'circle-color': '#2055c7', 'circle-radius': ['step', ['get', 'point_count'], 18, 20, 23, 60, 28], 'circle-stroke-color': '#fff', 'circle-stroke-width': 2 },
    })
    this.map.addLayer({
      id: 'kindergarten-cluster-count', type: 'symbol', source: sourceId, filter: ['has', 'point_count'],
      layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-size': 12 },
      paint: { 'text-color': '#fff' },
    })
    this.map.addLayer({
      id: pointsId, type: 'circle', source: sourceId, filter: ['!', ['has', 'point_count']],
      paint: { 'circle-color': '#2055c7', 'circle-radius': 7, 'circle-stroke-color': '#fff', 'circle-stroke-width': 2 },
    })
  }
}
