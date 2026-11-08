import { useMemo, useState } from 'react'
import { formatTime } from '@/mvvm/utils/format'
import type { MapRoute } from '../../Locations/components/map/RouteLayer'
import type { LocationFeature } from '../../Locations/types'
import type { CommuteResult } from '../types'
import { rankLabel } from '../utils/rank'

export type CommuteTab = 'route' | 'kindergarten'



export function useCommute(result: CommuteResult, onSelect?: (id: string | null) => void) {


  const [pick, setPick] = useState<{ id: string | null }>({ id: result.results[0]?.facility_id ?? null })
  const [tab, setTab] = useState<CommuteTab>('route')
  const option = result.results.find(item => item.facility_id === pick.id) ?? result.results[0]
  const rank = option ? result.results.indexOf(option) : -1
  const count = result.results.length
  const select = (id: string | null) => {
    setPick({ id })
    onSelect?.(id)
  }

  const route = useMemo<MapRoute | null>(() => {
    const chosen = result.results.find(item => item.facility_id === pick.id) ?? result.results[0]
    return chosen ? {
      home: [result.home.lon, result.home.lat], work: [result.work.lon, result.work.lat],
      legs: chosen.journeys.flatMap(journey => journey.legs),
    } : null
  }, [result, pick])
  return {
    selectedId: pick.id,
    option,
    rank,
    count,
    feature: result.locations.features.find(item => item.id === option?.facility_id),
    route,
    tab,
    setTab,
    select,
    close: () => select(null),

    step: (by: number) => { if (count) select(result.results[(rank + by + count) % count].facility_id) },
    summary: (feature: LocationFeature) => {
      const index = result.results.findIndex(item => item.facility_id === feature.id)
      const item = result.results[index]
      return `${rankLabel(index)} · ${Math.ceil(item.elapsed_seconds / 60)} min · dolazak ${formatTime(item.arrival)}`
    },
  }
}
