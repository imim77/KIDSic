import type { Feature, FeatureCollection, Point } from 'geojson'

export type ProviderKind = 'municipal' | 'private' | 'religious' | 'childminder' | 'other' | 'unknown'

export const providerLabels: Record<ProviderKind, string> = {
  municipal: 'Gradski vrtić',
  private: 'Privatni vrtić',
  religious: 'Vjerski vrtić',
  childminder: 'Obrt za čuvanje djece',
  other: 'Drugi pružatelj',
  unknown: 'Vrsta nije navedena',
}

export function isProviderKind(value: unknown): value is ProviderKind {
  return typeof value === 'string' && Object.hasOwn(providerLabels, value)
}

export interface SearchCriteria {
  city: string
  name?: string
  area?: string
  provider_kind?: ProviderKind | null
  has_vacancies?: boolean
  nearby?: Nearby | null
}

export interface HistoricalEvidence {
  programs: string[]
  reference_date: string
  date_kind: 'published' | 'observed'
  scope: 'institution' | 'facility'
  vacancies: { age_label: string | null; program: string | null; free_places: number | null }[]
  source_title: string
  source_url: string
  license: string
}

export type EnrolmentStatus = 'open' | 'upcoming' | 'closed' | 'not_accepting' | 'dates_unknown'

// One published enrolment round; steps and documents are read from the source.
export interface LocationEnrolment {
  round: 'main' | 'rolling'
  academic_year: string
  channel: 'e_upisi' | 'city_system' | 'kindergarten'
  application_url: string
  accepting: boolean
  opens_at: string | null
  closes_at: string | null
  status: EnrolmentStatus
  source_title: string
  source_url: string
  license: string | null
  reference_date: string | null
  date_kind: 'published' | 'observed' | 'unknown'
}

// Shared marker colours mirror the provider tokens in theme.css.
export const providerColors: Record<ProviderKind, string> = {
  municipal: '#82eda6',
  private: '#c88cfd',
  religious: '#fdc068',
  childminder: '#fc5681',
  other: '#82eda6',
  unknown: '#82eda6',
}

export interface LocationSource {
  name: string
  url: string
  license: string | null
  reference_date: string | null
  retrieved_at: string
}

export interface LocationProperties {
  location_id: string | null
  kindergarten_id: string
  name: string
  location_name: string
  address: string | null
  city: string
  provider_kind: ProviderKind
  website_url?: string | null
  email?: string | null
  phone?: string | null
  district: string | null
  areas?: string[]
  historical_data?: HistoricalEvidence[]
  enrolment?: LocationEnrolment[]
  distance_m?: number | null
  location_role: 'facility' | 'seat'
  sources: LocationSource[]
  field_sources?: Record<string, LocationSource>
  subsidy_policies?: SubsidyPolicy[]
}

export interface SubsidyPolicy {
  policy_key: string
  title: string
  summary: string
  verification_status: 'verified' | 'partial'
  verified_on: string
  valid_from: string | null
  valid_until: string | null
  amount_kind: 'city_subsidy' | 'parent_fee'
  rates: { label: string; city_subsidy_cents: number | null; parent_fee_cents: number | null }[]
  conditions: string[]
  reliefs: string[]
  notes: string[]
  sources: { title: string; url: string }[]
}

export type LocationFeature = Feature<Point | null, LocationProperties> & { id: string }

export interface LocationCollection extends FeatureCollection<Point | null, LocationProperties> {
  features: LocationFeature[]
  metadata: {
    total: number
    mapped: number
    unmapped: number
    scope: 'city' | 'bbox' | 'radius'
    complete: true
    confirmed?: number
    unknown?: number
  }
}

// Nearby limits results to a straight-line radius around a WGS84 point.
export interface Nearby {
  near: [longitude: number, latitude: number]
  radius_m: number
}

export interface LocationFilters {
  city: string
  q: string
  provider_kind: ProviderKind | ''
  area?: string
  has_vacancies?: boolean
  nearby?: Nearby | null
}
