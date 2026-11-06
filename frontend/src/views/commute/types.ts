import type { LocationCollection } from '../../shared/locations/types'
import { LocationToolResult } from '../../shared/mcp/LocationToolResult'

export type Point = { lat: number; lon: number }

export type CommuteLeg = { mode: string; departure: string; arrival: string; from_name: string; to_name: string; line: string | null; geometry: string | null }
export type CommuteOption = { facility_id: string; name: string; address: string; point: Point;
  status: 'ok'; arrival: string; elapsed_seconds: number; extra_seconds: number | null; transfers: number;
  journeys: { departure: string; arrival: string; legs: CommuteLeg[] }[] }
export type CommuteResult = { status: 'ok' | 'no_route'; city: 'Rijeka' | 'Zagreb' | 'Šibenik'; home: Point; work: Point;
  departure: string; dropoff_minutes: number; mode: 'WALK' | 'TRANSIT'; results: CommuteOption[];
  top_k: number; locations: LocationCollection;
  searched: number; reachable: number; excluded: number; without_route: number; notice: string;
  sources: { service_start: string; service_end: string; gtfs_url: string; publisher: string; license: string; retrieved_on: string } }

const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v)
const instant = (v: unknown) => typeof v === 'string' && /^\d{4}-\d\d-\d\dT/.test(v) && Number.isFinite(Date.parse(v))
const count = (v: unknown): v is number => typeof v === 'number' && Number.isInteger(v) && v >= 0
const point = (v: unknown, city: unknown) => record(v) && typeof v.lat === 'number' && typeof v.lon === 'number'
  && (city === 'Zagreb'
    ? v.lat >= 45.60 && v.lat <= 46.00 && v.lon >= 15.70 && v.lon <= 16.30
    : city === 'Šibenik'
      ? v.lat >= 43.60 && v.lat <= 43.85 && v.lon >= 15.70 && v.lon <= 16.05
      : city === 'Rijeka' && v.lat >= 45.20 && v.lat <= 45.45 && v.lon >= 14.20 && v.lon <= 14.65)

// parseCommuteResult prevents malformed host data from becoming a ranked map.
export function parseCommuteResult(value: unknown): CommuteResult {
  if (!record(value) || !['ok', 'no_route'].includes(String(value.status)) || !['Rijeka', 'Zagreb', 'Šibenik'].includes(String(value.city))
    || !point(value.home, value.city) || !point(value.work, value.city) || !instant(value.departure)
    || !count(value.dropoff_minutes) || value.dropoff_minutes > 60
    || !['WALK', 'TRANSIT'].includes(String(value.mode)) || typeof value.notice !== 'string'
    || ![value.searched, value.reachable, value.excluded, value.without_route].every(count)
    || !record(value.sources) || !['service_start', 'service_end', 'gtfs_url', 'publisher', 'license', 'retrieved_on'].every(k => typeof value.sources === 'object' && value.sources !== null && typeof (value.sources as Record<string, unknown>)[k] === 'string')
    || !Array.isArray(value.results) || !count(value.top_k) || value.top_k < 1 || value.results.length > value.top_k) throw new Error('Invalid commute result')
  const ids = new Set<string>()
  let previous = -1
  for (const r of value.results) {
    if (!record(r) || r.status !== 'ok' || typeof r.facility_id !== 'string' || ids.has(r.facility_id)
      || typeof r.name !== 'string' || typeof r.address !== 'string' || !point(r.point, value.city)
      || !instant(r.arrival) || !count(r.elapsed_seconds) || r.elapsed_seconds < previous
      || !count(r.transfers) || !(r.extra_seconds === null || typeof r.extra_seconds === 'number' && Number.isFinite(r.extra_seconds))
      || !Array.isArray(r.journeys) || r.journeys.length !== 2) throw new Error('Invalid commute option')
    ids.add(r.facility_id); previous = r.elapsed_seconds
    for (const journey of r.journeys) {
      if (!record(journey) || !instant(journey.departure) || !instant(journey.arrival)
        || !Array.isArray(journey.legs) || !journey.legs.length) throw new Error('Invalid journey')
      for (const l of journey.legs) {
        if (!record(l) || !instant(l.departure) || !instant(l.arrival)
          || !['mode', 'from_name', 'to_name'].every(k => typeof l[k] === 'string')
          || !(l.line === null || typeof l.line === 'string')
          || !(l.geometry === null || typeof l.geometry === 'string' && l.geometry.length < 1_000_000)) throw new Error('Invalid leg')
      }
    }
  }
  if ((value.status === 'ok') !== (value.results.length > 0)
    || value.results.length !== Math.min(value.top_k as number, value.reachable as number)
    || value.searched !== (value.reachable as number) + (value.without_route as number)) throw new Error('Invalid counts')
  const options = value.results as CommuteOption[]
  const locations = LocationToolResult.parse({ city: value.city, locations: value.locations }).locations
  if (locations.features.length !== value.results.length || locations.features.some((feature, index) => {
    const option = options[index]
    return feature.id !== option.facility_id || feature.properties.city !== value.city
      || feature.properties.location_role !== 'facility' || feature.properties.location_name !== option.name
      || feature.properties.address !== option.address || !feature.geometry
      || feature.geometry.coordinates[0] !== option.point.lon || feature.geometry.coordinates[1] !== option.point.lat
  })) throw new Error('Mismatched route locations')
  return value as CommuteResult
}
