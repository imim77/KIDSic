import { isProviderKind, type LocationCollection, type ProviderKind } from '../locations/types'

function record(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}

// LocationToolResult validates host data before it reaches map and card components.
export class LocationToolResult {
  static async fromResult(result: { structuredContent?: unknown; _meta?: Record<string, unknown> }) {
    const summary = result.structuredContent
    if (!record(summary)) throw new Error('Missing summary')
    let locations = result._meta?.locations
    if (record(locations) && locations.encoding === 'gzip+base64') {
      if (typeof locations.data !== 'string') throw new Error('Missing compressed locations')
      const bytes = Uint8Array.from(atob(locations.data), (character) => character.charCodeAt(0))
      const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))
      locations = await new Response(stream).json()
    }
    const parsed = this.parse({ city: summary.city, name: summary.name, provider_kind: summary.provider_kind, locations })
    const metadata = summary.metadata
    if (!record(metadata) || metadata.total !== parsed.locations.metadata.total
      || metadata.mapped !== parsed.locations.metadata.mapped || metadata.unmapped !== parsed.locations.metadata.unmapped
      || metadata.scope !== 'city' || metadata.complete !== true) throw new Error('Mismatched summary')
    return parsed
  }

  static parse(value: unknown): { city: string; name?: string; provider_kind?: ProviderKind | null; locations: LocationCollection } {
    if (!record(value) || typeof value.city !== 'string' || !value.city.trim()) throw new Error('Missing city')
    if (value.name !== undefined && (typeof value.name !== 'string' || value.name.trim().length > 200)) throw new Error('Invalid search name')
    if (value.provider_kind !== undefined && value.provider_kind !== null && !isProviderKind(value.provider_kind)) throw new Error('Invalid provider kind')
    const data = value.locations
    if (!record(data) || data.type !== 'FeatureCollection' || !Array.isArray(data.features)
      || !record(data.metadata) || data.metadata.complete !== true || data.metadata.scope !== 'city'
      || data.metadata.total !== data.features.length) throw new Error('Invalid locations')
    const ids = new Set<string>()
    let mapped = 0
    for (const feature of data.features) {
      if (!record(feature) || feature.type !== 'Feature' || typeof feature.id !== 'string' || ids.has(feature.id)
        || !record(feature.properties)) throw new Error('Invalid feature')
      ids.add(feature.id)
      const p = feature.properties
      if (typeof p.name !== 'string' || typeof p.location_name !== 'string' || typeof p.city !== 'string'
        || typeof p.kindergarten_id !== 'string' || !['facility', 'seat'].includes(String(p.location_role))
        || !isProviderKind(p.provider_kind)
        || !Array.isArray(p.sources)) throw new Error('Invalid properties')
      if (value.provider_kind != null && p.provider_kind !== value.provider_kind) throw new Error('Mismatched provider kind')
      if (['website_url', 'email', 'phone'].some((field) =>
        p[field] != null && typeof p[field] !== 'string')) throw new Error('Invalid contact')
      if (feature.geometry !== null) {
        const g = feature.geometry
        if (!record(g) || g.type !== 'Point' || !Array.isArray(g.coordinates) || g.coordinates.length !== 2
          || !g.coordinates.every((n) => typeof n === 'number' && Number.isFinite(n))
          || Math.abs(g.coordinates[0]) > 180 || Math.abs(g.coordinates[1]) > 90) throw new Error('Invalid coordinates')
        mapped++
      }
    }
    if (data.metadata.mapped !== mapped || data.metadata.unmapped !== data.features.length - mapped) throw new Error('Invalid counts')
    return { city: value.city.trim(), ...(value.name !== undefined ? { name: (value.name as string).trim() } : {}),
      ...(value.provider_kind !== undefined ? { provider_kind: value.provider_kind as ProviderKind | null } : {}),
      locations: data as unknown as LocationCollection }
  }
}
