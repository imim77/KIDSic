import type { LocationCollection, LocationFilters } from './types'

// LocationDirectory reads the complete city so list counts never depend on map view.
export class LocationDirectory {
  async find(filters: LocationFilters, signal: AbortSignal): Promise<LocationCollection> {
    const query = new URLSearchParams({ city: filters.city })
    if (filters.q) query.set('q', filters.q)
    if (filters.provider_kind) query.set('provider_kind', filters.provider_kind)
    const response = await fetch(`/api/locations?${query}`, { signal })
    if (!response.ok) throw new Error(`Locations unavailable (${response.status})`)
    const data = await response.json() as LocationCollection
    if (data.type !== 'FeatureCollection' || !Array.isArray(data.features)
      || data.metadata?.complete !== true || data.metadata.scope !== 'city'
      || data.metadata.total !== data.features.length
      || data.metadata.mapped + data.metadata.unmapped !== data.metadata.total) {
      throw new Error('Incomplete location response')
    }
    return data
  }
}
