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

// Mirrors theme.css because Mapbox paint expressions cannot read CSS variables.
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
  location_role: 'facility' | 'seat'
  sources: LocationSource[]
  field_sources?: Record<string, LocationSource & { active_snapshot: boolean }>
  age_groups: null
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
    scope: 'city' | 'bbox'
    complete: true
  }
}

export interface LocationFilters {
  city: string
  q: string
  provider_kind: ProviderKind | ''
}

export const initialLocationFilters: LocationFilters = { city: 'Zagreb', q: '', provider_kind: '' }
