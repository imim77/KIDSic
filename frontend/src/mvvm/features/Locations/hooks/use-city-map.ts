import { useState } from 'react'
import type { LocationCollection, LocationFilters, Nearby } from '../types'
import { useLocations } from './use-locations'

const city = 'Zagreb'

// districtsOf reads the picker options from a whole-city result, so the list
// only offers districts that the sources actually record.
function districtsOf(data: LocationCollection) {
  const names = new Set(data.features.flatMap((feature) => feature.properties.district ?? []))
  return { options: [...names].sort((a, b) => a.localeCompare(b, 'hr')),
    unknown: data.features.filter((feature) => !feature.properties.district).length }
}

// useCityMap drives the standalone city map from the location API: the
// district and nearby filters, and a selection that a new result can drop.
export function useCityMap() {
  const [selection, setSelection] = useState<string | null>(null)
  const [nearby, setNearby] = useState<Nearby | null>(null)
  const [area, setArea] = useState('')
  const filters: LocationFilters = { city, q: '', provider_kind: '', area, nearby }
  const { status, data, retry } = useLocations(filters)
  // Filtered results would shrink the picker, so options come from the last
  // whole-city result.
  const [whole, setWhole] = useState<{ data: LocationCollection } & ReturnType<typeof districtsOf> | null>(null)
  if (data && !area && !nearby && whole?.data !== data) setWhole({ data, ...districtsOf(data) })
  return {
    data,
    status,
    selectedId: data?.features.some((feature) => feature.id === selection) ? selection : null,
    select: setSelection,
    retry: () => {
      setSelection(null)
      retry()
    },
    nearby: { value: nearby, onChange: setNearby },
    district: whole ? { options: whole.options, unknown: whole.unknown, value: area, onChange: setArea } : undefined,
    criteria: { city, area, nearby },
  }
}
