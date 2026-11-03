import type { Feature, FeatureCollection, Point } from 'geojson'

export type ProviderKind = 'municipal' | 'private' | 'religious' | 'childminder' | 'other' | 'unknown'

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
  district: string | null
  location_role: 'facility' | 'seat'
  sources: LocationSource[]
  field_sources?: Record<string, LocationSource & { active_snapshot: boolean }>
  age_groups: null
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

export const providerLabels: Record<ProviderKind, string> = {
  municipal: 'Gradski',
  private: 'Privatni',
  religious: 'Vjerski',
  childminder: 'Dadilje',
  other: 'Ostali',
  unknown: 'Nepoznat pružatelj',
}

export const initialLocationFilters: LocationFilters = { city: 'Zagreb', q: '', provider_kind: '' }
