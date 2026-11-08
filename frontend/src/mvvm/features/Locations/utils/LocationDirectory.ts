import type { LocationCollection, LocationFilters } from '../types'



export class LocationDirectory {
  async find(filters: LocationFilters, signal: AbortSignal): Promise<LocationCollection> {
    const query = new URLSearchParams({ city: filters.city })
    if (filters.q) query.set('q', filters.q)
    if (filters.provider_kind) query.set('provider_kind', filters.provider_kind)
    if (filters.area) query.set('area', filters.area)
    if (filters.has_vacancies) query.set('has_vacancies', 'true')
    if (filters.nearby) {

      query.set('near', filters.nearby.near.map((value) => Number(value.toFixed(5))).join(','))
      query.set('radius_m', String(filters.nearby.radius_m))
    }
    const response = await fetch(`/api/locations?${query}`, { signal })
    if (!response.ok) throw new Error(`Locations unavailable (${response.status})`)
    const data = await response.json() as LocationCollection
    if (data.type !== 'FeatureCollection' || !Array.isArray(data.features)
      || data.metadata?.complete !== true || data.metadata.scope !== (filters.nearby ? 'radius' : 'city')
      || data.metadata.total !== data.features.length
      || data.metadata.mapped + data.metadata.unmapped !== data.metadata.total) {
      throw new Error('Incomplete location response')
    }
    return data
  }
}
