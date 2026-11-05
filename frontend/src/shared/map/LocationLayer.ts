import L from 'leaflet'
import 'leaflet.markercluster'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import type { Point } from 'geojson'
import type { LocationCollection, LocationFeature } from '../locations/types'
import { providerColors } from '../locations/types'

// LocationLayer keeps clustered markers and list selection in sync.
export class LocationLayer {
  private map: L.Map
  private points: L.MarkerClusterGroup
  private selection: L.LayerGroup
  private features: (LocationFeature & { geometry: Point })[] = []
  private selectedId: string | null = null

  constructor(map: L.Map, onSelect: (id: string) => void) {
    this.map = map
    this.points = L.markerClusterGroup({
      maxClusterRadius: 42, disableClusteringAtZoom: 15,
      showCoverageOnHover: false,
      iconCreateFunction: (cluster) => L.divIcon({
        className: 'location-cluster', html: String(cluster.getChildCount()),
        iconSize: [38, 38],
      }),
    }).addTo(map)
    this.points.on('click', (event: L.LeafletEvent & { layer: L.Marker }) => {
      const id = event.layer.options.alt
      if (id) onSelect(id)
    })
    this.selection = L.layerGroup().addTo(map)
  }

  update(collection: LocationCollection | null) {
    this.features = (collection?.features ?? []).filter(
      (feature): feature is LocationFeature & { geometry: Point } => feature.geometry !== null,
    )
    this.points.clearLayers()
    this.points.addLayers(this.features.map((feature) => {
      const [lng, lat] = feature.geometry.coordinates
      return L.marker([lat, lng], {
        icon: this.icon(feature), alt: feature.properties.location_id || feature.id,
        title: feature.properties.location_name, bubblingMouseEvents: true,
      })
    }))
    this.select(this.selectedId, false)
    this.fit()
  }

  fit(routePoints: L.LatLngTuple[] = []) {
    const points: L.LatLngTuple[] = [...routePoints, ...this.features.map((feature) => {
      const [lng, lat] = feature.geometry.coordinates
      return [lat, lng] as L.LatLngTuple
    })]
    if (points.length) this.map.fitBounds(L.latLngBounds(points), {
      ...this.cameraPadding(), maxZoom: 14, animate: false,
    })
  }

  select(id: string | null, focus = true) {
    this.selectedId = id
    this.selection.clearLayers()
    const feature = this.features.find((item) => item.id === id)
    if (!feature) return
    const [lng, lat] = feature.geometry.coordinates
    // A separate marker keeps selection visible even inside a cluster.
    L.marker([lat, lng], {
      icon: this.icon(feature, true), interactive: false, keyboard: false,
      zIndexOffset: 1000,
    }).addTo(this.selection)
    if (focus) this.map.fitBounds([[lat, lng], [lat, lng]], {
      ...this.cameraPadding(), maxZoom: Math.max(this.map.getZoom(), 15), animate: false,
    })
  }

  resize() {
    // Recenter an active selection above the card deck after rotation.
    if (this.selectedId) this.select(this.selectedId)
  }

  dispose() {
    this.points.off()
    this.points.clearLayers()
    this.points.remove()
    this.selection.remove()
  }

  private icon(feature: LocationFeature, selected = false) {
    const dot = document.createElement('span')
    dot.style.backgroundColor = providerColors[feature.properties.provider_kind] ?? providerColors.municipal
    const size = selected ? 26 : 18
    return L.divIcon({
      className: selected ? 'location-pin location-pin-selected' : 'location-pin',
      html: dot, iconSize: [size, size], iconAnchor: [size / 2, size / 2],
    })
  }

  private cameraPadding(): L.FitBoundsOptions {
    const frame = this.map.getContainer().closest('.kindergarten-explorer')
    if (!frame) return { paddingTopLeft: [50, 50], paddingBottomRight: [50, 50] }
    const height = frame.clientHeight
    const deck = frame.querySelector('.location-carousel')?.getBoundingClientRect().height ?? 0
    // Center selected pins in the map area above the cards, also in landscape.
    return {
      paddingTopLeft: [45, Math.min(90, height * .2)],
      paddingBottomRight: [45, Math.min(deck + 45, height * .6)],
    }
  }
}
