import type { LocationCollection } from '../Locations/types'

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
