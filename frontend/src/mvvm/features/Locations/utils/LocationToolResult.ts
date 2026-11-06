import { isRecord as record } from '@/mvvm/utils/guards'
import { isProviderKind, type LocationCollection, type Nearby, type ProviderKind, type SearchCriteria } from '../types'

function textKey(value: string): string {
  return value.trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replaceAll('đ', 'd')
}

const areaKey = (value: string) => textKey(value).replace(/^mjesni odbor /, '')

// nearby reads the tool's near/radius_m pair; null or absent means a city search.
function nearby(near: unknown, radius: unknown): Nearby | null {
  if (near == null && radius == null) return null
  if (!Array.isArray(near) || near.length !== 2 || !near.every((n) => typeof n === 'number' && Number.isFinite(n))
    || Math.abs(near[0]) > 180 || Math.abs(near[1]) > 90
    || typeof radius !== 'number' || !Number.isInteger(radius) || radius < 1 || radius > 50_000) throw new Error('Invalid nearby')
  return { near: [near[0], near[1]], radius_m: radius }
}

function date(value: unknown): value is string {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  const parsed = new Date(`${value}T00:00:00Z`)
  return Number.isFinite(parsed.valueOf()) && parsed.toISOString().slice(0, 10) === value
}

function validHistory(value: unknown): boolean {
  if (!record(value)) return false
  return date(value.reference_date) && ['published', 'observed'].includes(String(value.date_kind))
    && ['institution', 'facility'].includes(String(value.scope))
    && ['source_title', 'source_url', 'license'].every((key) => typeof value[key] === 'string' && !!value[key].trim())
    && Array.isArray(value.programs) && value.programs.every((p) => typeof p === 'string' && !!p.trim())
    && Array.isArray(value.vacancies) && value.vacancies.every((v) => record(v)
      && (v.age_label === null || typeof v.age_label === 'string')
      && (v.program === null || typeof v.program === 'string')
      && (v.free_places === null || typeof v.free_places === 'number' && Number.isInteger(v.free_places) && v.free_places >= 0))
}

function instant(value: unknown): boolean {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T[\d:.]+(Z|[+-]\d{2}:\d{2})$/.test(value)
    && Number.isFinite(Date.parse(value))
}

function validEnrolment(value: unknown): boolean {
  if (!record(value)) return false
  const opens = value.opens_at, closes = value.closes_at
  return ['main', 'rolling'].includes(String(value.round))
    && typeof value.academic_year === 'string' && /^\d{4}\.\/\d{4}\.$/.test(value.academic_year)
    && ['e_upisi', 'city_system', 'kindergarten'].includes(String(value.channel))
    && typeof value.application_url === 'string' && /^https:\/\//.test(value.application_url)
    && typeof value.accepting === 'boolean'
    && ['open', 'upcoming', 'closed', 'not_accepting', 'dates_unknown'].includes(String(value.status))
    && (value.status === 'not_accepting') === !value.accepting
    && (opens === null || instant(opens)) && (closes === null || instant(closes))
    && (opens == null || closes == null || Date.parse(closes as string) >= Date.parse(opens as string))
    && ['source_title', 'source_url'].every((key) => typeof value[key] === 'string' && !!(value[key] as string).trim())
    && (value.license === null || typeof value.license === 'string')
    && (value.reference_date === null || date(value.reference_date))
    && ['published', 'observed', 'unknown'].includes(String(value.date_kind))
}

// LocationToolResult validates host data before it reaches map and card components.
export class LocationToolResult {
  static async fromResult(result: { structuredContent?: unknown; _meta?: Record<string, unknown> }) {
    const summary = result.structuredContent
    if (!record(summary)) throw new Error('Missing summary')
    if (['age_months', 'program', 'include_unknown'].some((key) => key in summary)) throw new Error('Unsupported search criteria')
    let locations = result._meta?.locations
    if (record(locations) && locations.encoding === 'gzip+base64') {
      if (typeof locations.data !== 'string') throw new Error('Missing compressed locations')
      const bytes = Uint8Array.from(atob(locations.data), (character) => character.charCodeAt(0))
      const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))
      locations = await new Response(stream).json()
    }
    const parsed = this.parse({ city: summary.city, name: summary.name, provider_kind: summary.provider_kind, area: summary.area,
      near: summary.near, radius_m: summary.radius_m, locations })
    const metadata = summary.metadata
    if (!record(metadata) || metadata.total !== parsed.locations.metadata.total
      || metadata.mapped !== parsed.locations.metadata.mapped || metadata.unmapped !== parsed.locations.metadata.unmapped
      || metadata.scope !== parsed.locations.metadata.scope || metadata.complete !== true) throw new Error('Mismatched summary')
    return parsed
  }

  static parse(value: unknown): SearchCriteria & { locations: LocationCollection } {
    if (!record(value) || typeof value.city !== 'string' || !value.city.trim()) throw new Error('Missing city')
    if (['age_months', 'program', 'include_unknown'].some((key) => key in value)) throw new Error('Unsupported search criteria')
    if (value.name !== undefined && (typeof value.name !== 'string' || value.name.trim().length > 200)) throw new Error('Invalid search name')
    if (value.provider_kind !== undefined && value.provider_kind !== null && !isProviderKind(value.provider_kind)) throw new Error('Invalid provider kind')
    if (value.area !== undefined && (typeof value.area !== 'string' || value.area.trim().length > 200)) throw new Error('Invalid search area')
    const area = typeof value.area === 'string' ? value.area.trim() : ''
    const around = nearby(value.near, value.radius_m)
    const data = value.locations
    if (!record(data) || data.type !== 'FeatureCollection' || !Array.isArray(data.features)
      || !record(data.metadata) || data.metadata.complete !== true || data.metadata.scope !== (around ? 'radius' : 'city')
      || data.metadata.total !== data.features.length) throw new Error('Invalid locations')
    const ids = new Set<string>()
    let mapped = 0
    for (const feature of data.features) {
      if (!record(feature) || feature.type !== 'Feature' || typeof feature.id !== 'string' || ids.has(feature.id)
        || !record(feature.properties)) throw new Error('Invalid feature')
      ids.add(feature.id)
      const p = feature.properties
      if (p.historical_data !== undefined && (!Array.isArray(p.historical_data) || !p.historical_data.every(validHistory))) throw new Error('Invalid historical data')
      if (p.enrolment !== undefined && (!Array.isArray(p.enrolment) || !p.enrolment.every(validEnrolment))) throw new Error('Invalid enrolment')
      if (p.location_role === 'seat' && Array.isArray(p.historical_data) && p.historical_data.some((item) => record(item) && item.scope !== 'institution')) throw new Error('Invalid seat historical scope')
      if (typeof p.name !== 'string' || typeof p.location_name !== 'string' || typeof p.city !== 'string'
        || typeof p.kindergarten_id !== 'string' || !['facility', 'seat'].includes(String(p.location_role))
        || !isProviderKind(p.provider_kind)
        || !Array.isArray(p.sources)) throw new Error('Invalid properties')
      if (value.provider_kind != null && p.provider_kind !== value.provider_kind) throw new Error('Mismatched provider kind')
      if (p.areas !== undefined && (!Array.isArray(p.areas) || !p.areas.every((name) => typeof name === 'string' && name.trim()))) throw new Error('Invalid areas')
      if (area && (!Array.isArray(p.areas) || !p.areas.some((name: string) => areaKey(name) === areaKey(area)))) throw new Error('Mismatched area')
      if (['website_url', 'email', 'phone'].some((field) =>
        p[field] != null && typeof p[field] !== 'string')) throw new Error('Invalid contact')
      // A radius result asserts a verified point no further than the radius.
      if (around && (feature.geometry === null || typeof p.distance_m !== 'number' || !Number.isInteger(p.distance_m)
        || p.distance_m < 0 || p.distance_m > around.radius_m)) throw new Error('Invalid distance')
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
      ...(value.area !== undefined ? { area } : {}),
      ...(value.near !== undefined || value.radius_m !== undefined ? { nearby: around } : {}),
      locations: data as unknown as LocationCollection }
  }
}
