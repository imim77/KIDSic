import { useState } from 'react'
import { formatDistance } from '@/mvvm/utils/format'
import type { CompareChoice } from '../components/CompareToggle'
import { comparisonLimit } from '../utils/comparison'
import { describeCriteria } from '../utils/criteria'
import type { LocationCollection, LocationFeature, Nearby, SearchCriteria } from '../types'

// NearbySearch is a screen's point-and-radius search; screens without one omit it.
export interface NearbySearch {
  value: Nearby | null
  onChange: (value: Nearby | null) => void
}

// DistrictFilter is a screen's city-district picker; screens without one omit it.
export interface DistrictFilter {
  options: string[]
  value: string
  unknown: number // Results without a recorded district, which never match.
  onChange: (value: string) => void
}

export interface ExplorerInput {
  data: LocationCollection | null
  selectedId: string | null
  onSelect: (id: string | null) => void
  retry?: () => void
  nearby?: NearbySearch
  district?: DistrictFilter
  criteria?: SearchCriteria
  emptyNotice?: string
  // A ranked route compares journeys, not kindergartens, so it hides comparison.
  comparable?: boolean
}

const defaultRadius = 1000

// useKindergartenExplorer owns the explorer's own interaction state: the
// nearby point being picked, the comparison and which map pick the card deck
// should scroll to. Results and selection stay with the screen.
export function useKindergartenExplorer({ data, selectedId, onSelect, retry, nearby, district, criteria, emptyNotice, comparable = true }: ExplorerInput) {
  const [picking, setPicking] = useState(false)
  const [chosenRadius, setChosenRadius] = useState(defaultRadius)
  // An active search, also one the host's model made, owns the shown radius.
  const radius = nearby?.value?.radius_m ?? chosenRadius
  // Each map pick is a new revision, so picking the same pin scrolls again.
  const [reveal, setReveal] = useState<{ id: string; revision: number } | null>(null)

  // Compared options are kept as snapshots so they survive a new search; a
  // result that is still listed replaces its snapshot, e.g. to show distance.
  const [compared, setCompared] = useState<LocationFeature[]>([])
  const [comparing, setComparing] = useState(false)
  const comparedNow = compared.map((feature) => data?.features.find((current) => current.id === feature.id) ?? feature)

  const compareChoice = (feature: LocationFeature): CompareChoice | undefined => {
    if (!comparable) return undefined
    const selected = compared.some((item) => item.id === feature.id)
    return { selected, full: compared.length >= comparisonLimit, onToggle: () => setCompared((items) => selected
      ? items.filter((item) => item.id !== feature.id)
      : items.length < comparisonLimit ? [...items, feature] : items) }
  }

  const describedEmpty = emptyNotice ?? (nearby?.value
    ? `Nema objekata s potvrđenim koordinatama unutar ${formatDistance(nearby.value.radius_m)}${district?.value ? ` u četvrti ${district.value}` : ''}. Povećajte radijus ili uklonite točku.`
    : district?.value ? `Nema objekata s potvrđenom četvrti ${district.value}.`
    : 'Nema dostupnih vrtićkih objekata.')

  return {
    selected: data?.features.find((feature) => feature.id === selectedId) ?? null,
    criteria: criteria ? describeCriteria(criteria) : undefined,
    emptyNotice: data?.features.length === 0 ? describedEmpty : undefined,
    reveal,
    selectFromMap: (id: string) => {
      onSelect(id)
      setReveal((previous) => ({ id, revision: (previous?.revision ?? 0) + 1 }))
    },
    retry: () => {
      setReveal(null)
      retry?.()
    },
    nearby: nearby && {
      value: nearby.value,
      radius,
      picking,
      setPicking,
      place: (near: [number, number]) => {
        setPicking(false)
        nearby.onChange({ near, radius_m: radius })
      },
      changeRadius: (value: number) => {
        setChosenRadius(value)
        if (nearby.value) nearby.onChange({ ...nearby.value, radius_m: value })
      },
      clear: () => {
        setPicking(false)
        nearby.onChange(null)
      },
    },
    comparison: {
      count: compared.length,
      features: comparedNow,
      // The comparison covers the explorer once it holds two options to set side by side.
      open: comparing && comparedNow.length > 1,
      choice: compareChoice,
      show: () => setComparing(true),
      hide: () => setComparing(false),
      remove: (id: string) => {
        const remaining = compared.filter((item) => item.id !== id)
        setCompared(remaining)
        if (remaining.length < 2) setComparing(false)
      },
      clear: () => {
        setCompared([])
        setComparing(false)
      },
    },
  }
}

export type ExplorerViewModel = ReturnType<typeof useKindergartenExplorer>
