import { isAgeMonths, isProviderKind, type LocationCollection, type LocationProgram, type Nearby, type ProviderKind, type SearchCriteria } from '../locations/types'

function record(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}

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

function validProgram(value: unknown): value is LocationProgram {
  if (!record(value)) return false
  const min = value.min_age_months, max = value.max_age_months_exclusive
  return ['program_id', 'name', 'source_record_id', 'source_url', 'source_title'].every((key) => typeof value[key] === 'string' && !!value[key].trim())
    && ['institution', 'facility'].includes(String(value.scope))
    && date(value.verified_on)
    && (value.valid_until === null || date(value.valid_until) && value.valid_until >= value.verified_on)
    && (min === null || typeof min === 'number' && Number.isInteger(min) && min >= 0)
    && (max === null || typeof max === 'number' && Number.isInteger(max) && max > 0)
    && (min == null || max == null || (max as number) > (min as number))
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
    let locations = result._meta?.locations
    if (record(locations) && locations.encoding === 'gzip+base64') {
      if (typeof locations.data !== 'string') throw new Error('Missing compressed locations')
      const bytes = Uint8Array.from(atob(locations.data), (character) => character.charCodeAt(0))
      const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))
      locations = await new Response(stream).json()
    }
    const parsed = this.parse({ city: summary.city, name: summary.name, provider_kind: summary.provider_kind, area: summary.area,
      age_months: summary.age_months, program: summary.program, include_unknown: summary.include_unknown,
      near: summary.near, radius_m: summary.radius_m, locations })
    const metadata = summary.metadata
    if (!record(metadata) || metadata.total !== parsed.locations.metadata.total
      || metadata.mapped !== parsed.locations.metadata.mapped || metadata.unmapped !== parsed.locations.metadata.unmapped
      || metadata.confirmed !== parsed.locations.metadata.confirmed || metadata.unknown !== parsed.locations.metadata.unknown
      || metadata.scope !== parsed.locations.metadata.scope || metadata.complete !== true) throw new Error('Mismatched summary')
    return parsed
  }

  static parse(value: unknown): SearchCriteria & { locations: LocationCollection } {
    if (!record(value) || typeof value.city !== 'string' || !value.city.trim()) throw new Error('Missing city')
    if (value.name !== undefined && (typeof value.name !== 'string' || value.name.trim().length > 200)) throw new Error('Invalid search name')
    if (value.provider_kind !== undefined && value.provider_kind !== null && !isProviderKind(value.provider_kind)) throw new Error('Invalid provider kind')
    if (value.area !== undefined && (typeof value.area !== 'string' || value.area.trim().length > 200)) throw new Error('Invalid search area')
    if (value.age_months != null && !isAgeMonths(value.age_months)) throw new Error('Invalid child age')
    if (value.program !== undefined && (typeof value.program !== 'string' || value.program.trim().length > 200)) throw new Error('Invalid search program')
    if (value.include_unknown !== undefined && typeof value.include_unknown !== 'boolean') throw new Error('Invalid unknown filter')
    const area = typeof value.area === 'string' ? value.area.trim() : ''
    const program = typeof value.program === 'string' ? value.program.trim() : ''
    const evaluated = value.age_months != null || !!program
    const around = nearby(value.near, value.radius_m)
    const data = value.locations
    if (!record(data) || data.type !== 'FeatureCollection' || !Array.isArray(data.features)
      || !record(data.metadata) || data.metadata.complete !== true || data.metadata.scope !== (around ? 'radius' : 'city')
      || data.metadata.total !== data.features.length) throw new Error('Invalid locations')
    const ids = new Set<string>()
    let mapped = 0
    let confirmed = 0, unknown = 0
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
      if (p.programs !== undefined && (!Array.isArray(p.programs) || !p.programs.every(validProgram))) throw new Error('Invalid programs')
      const programs = Array.isArray(p.programs) ? p.programs : []
      if (p.location_role === 'seat' && programs.some((item) => item.scope !== 'institution')) throw new Error('Invalid seat program scope')
      if (p.suitability_status !== undefined && !['not_evaluated', 'confirmed', 'unknown'].includes(String(p.suitability_status))) throw new Error('Invalid suitability')
      if (evaluated && !['confirmed', 'unknown'].includes(String(p.suitability_status))) throw new Error('Missing suitability')
      if (!evaluated && p.suitability_status != null && p.suitability_status !== 'not_evaluated') throw new Error('Unexpected suitability')
      if (p.suitability_status === 'unknown') {
        if (value.include_unknown === false) throw new Error('Unexpected unknown result')
        unknown++
      }
      if (p.suitability_status === 'confirmed') {
        const matches = programs.some((item) => textKey(item.name).includes(textKey(program))
          && (value.age_months == null || typeof item.min_age_months === 'number' && typeof item.max_age_months_exclusive === 'number'
            && item.min_age_months <= (value.age_months as number) && (value.age_months as number) < item.max_age_months_exclusive))
        if (!matches) throw new Error('Missing matching program evidence')
        confirmed++
      }
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
    if ((evaluated || data.metadata.confirmed !== undefined || data.metadata.unknown !== undefined)
      && (data.metadata.confirmed !== confirmed || data.metadata.unknown !== unknown)) throw new Error('Invalid suitability counts')
    return { city: value.city.trim(), ...(value.name !== undefined ? { name: (value.name as string).trim() } : {}),
      ...(value.provider_kind !== undefined ? { provider_kind: value.provider_kind as ProviderKind | null } : {}),
      ...(value.area !== undefined ? { area } : {}),
      ...(value.age_months !== undefined ? { age_months: value.age_months as number | null } : {}),
      ...(value.program !== undefined ? { program } : {}),
      ...(value.include_unknown !== undefined ? { include_unknown: value.include_unknown as boolean } : {}),
      ...(value.near !== undefined || value.radius_m !== undefined ? { nearby: around } : {}),
      locations: data as unknown as LocationCollection }
  }
}
