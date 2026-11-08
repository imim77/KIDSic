import { useEffect, useRef, useState } from 'react'
import { useMcpApp } from '@/mvvm/hooks/use-mcp-app'
import type { CommuteResult } from '../../Commute/types'
import { readCommuteResult } from '../../Commute/utils/commute-result'
import { isProviderKind, type LocationCollection, type LocationFeature, type Nearby, type SearchCriteria } from '../types'
import { describeEmptySearch } from '../utils/criteria'
import { LocationToolResult } from '../utils/LocationToolResult'
import { nearbyContext, selectionContext } from '../utils/model-context'

type Snapshot = Omit<SearchCriteria, 'city'> & { city: string | null; data: LocationCollection | null; status: 'loading' | 'ready' | 'error'; notice?: string }
type Commute = { revision: number; result: CommuteResult | null; notice: string }

const askForCity: Snapshot = { city: null, data: null, status: 'loading', notice: 'U kojem gradu želiš prikaz vrtića?' }
const commuteArguments = ['home', 'work', 'departure', 'mode', 'top_k']


function toolArguments({ city, name, provider_kind, area, nearby }: SearchCriteria) {
  return { city, ...(name ? { name } : {}), ...(provider_kind ? { provider_kind } : {}), ...(area ? { area } : {}),
    ...(nearby ? { near: nearby.near, radius_m: nearby.radius_m } : {}) }
}

function toolNearby(near: unknown, radius: unknown): Nearby | null {
  return Array.isArray(near) && near.length === 2 && near.every((n) => typeof n === 'number' && Number.isFinite(n))
    && typeof radius === 'number' && Number.isInteger(radius) ? { near: [near[0], near[1]], radius_m: radius } : null
}

function readySnapshot(parsed: Awaited<ReturnType<typeof LocationToolResult.fromResult>>): Snapshot {
  return { city: parsed.city, name: parsed.name ?? '', area: parsed.area ?? '', provider_kind: parsed.provider_kind ?? null,
    nearby: parsed.nearby ?? null, data: parsed.locations, status: 'ready' }
}





export function useMcpLocations() {
  const revision = useRef(0)
  const sharedSelection = useRef<string | null>(null)
  const [snapshot, setSnapshot] = useState<Snapshot>(askForCity)
  const [commute, setCommute] = useState<Commute | null>(null)
  const [selection, setSelection] = useState<string | null>(null)

  const host = useMcpApp({
    onToolInput: (args) => {
      revision.current++
      shareSelection(null)
      setCommute(args && commuteArguments.some(key => key in args)
        ? { revision: revision.current, result: null, notice: 'Uspoređujem putove kroz vrtiće…' } : null)
      const city = typeof args?.city === 'string' ? args.city.trim() : ''
      const name = typeof args?.name === 'string' ? args.name.trim() : ''
      const area = typeof args?.area === 'string' ? args.area.trim() : ''
      const provider_kind = isProviderKind(args?.provider_kind) ? args.provider_kind : null
      setSelection(null)
      setSnapshot(city ? { city, name, area, provider_kind, nearby: toolNearby(args?.near, args?.radius_m), data: null, status: 'loading' } : askForCity)
    },
    onToolResult: async (result) => {
      const request = ++revision.current
      shareSelection(null)
      setSelection(null)
      if (result.isError) {
        setCommute(previous => previous ? { revision: request, result: null, notice: 'Izračun nije dostupan. Provjeri podatke i pokušaj ponovno u razgovoru.' } : null)
        setSnapshot((previous) => previous.city ? { ...previous, data: null, status: 'error' } : askForCity)
        return
      }
      if (result._meta && 'commute' in result._meta) {
        setCommute({ revision: request, ...readCommuteResult(result._meta.commute) })
        return
      }
      setCommute(null)
      try {
        const parsed = await LocationToolResult.fromResult(result)
        if (request === revision.current) setSnapshot(readySnapshot(parsed))
      } catch {
        if (request === revision.current) setSnapshot((previous) => ({ ...previous, data: null, status: 'error' }))
      }
    },
    onToolCancelled: () => {
      revision.current++
      setSelection(null)
      shareSelection(null)
      setCommute(previous => previous ? { revision: revision.current, result: null, notice: 'Izračun je prekinut. Možeš ponoviti upit u razgovoru.' } : null)
      setSnapshot((previous) => ({ ...previous, data: null, status: 'error' }))
    },
    onConnectFailed: () => setSnapshot({ city: null, data: null, status: 'loading', notice: 'Otvori ovaj prikaz kroz MCP alat u AI klijentu i navedi grad.' }),
  })

  useEffect(() => () => { revision.current++ }, [])

  function shareSelection(feature: LocationFeature | null, onRoute = false) {
    if (!feature && sharedSelection.current === null) return
    sharedSelection.current = feature?.id ?? null
    host.updateModelContext(selectionContext(feature, onRoute))
  }



  const search = async (nearby: Nearby | null | undefined = snapshot.nearby) => {
    const city = snapshot.city
    if (!city) { setSnapshot(askForCity); return }
    const criteria = { name: snapshot.name ?? '', area: snapshot.area ?? '', provider_kind: snapshot.provider_kind ?? null,
      nearby: nearby ?? null }
    const request = ++revision.current
    const changedPoint = nearby !== snapshot.nearby
    setSelection(null)
    shareSelection(null)
    setSnapshot({ city, ...criteria, data: null, status: 'loading' })
    try {
      const result = await host.callServerTool({ name: 'prikazi_vrtice', arguments: toolArguments({ city, ...criteria }) })
      if (request !== revision.current) return
      if (!result) { setSnapshot(askForCity); return }
      if (result.isError) throw new Error('Tool failed')
      const parsed = await LocationToolResult.fromResult(result)
      if (request !== revision.current) return
      setSnapshot(readySnapshot(parsed))
      if (changedPoint) host.updateModelContext(nearbyContext(parsed.city, parsed.nearby ?? null, parsed.locations.metadata.total))
    } catch {
      if (request === revision.current) setSnapshot({ city, ...criteria, data: null, status: 'error' })
    }
  }

  const city = snapshot.city
  return {
    expanded: host.expanded,
    fullscreen: host.fullscreen,
    openLink: host.openLink,
    commute: commute && {
      ...commute,
      selectRoute: (id: string | null) => {
        const feature = commute.result?.locations.features.find(item => item.id === id)
        if (id === null || feature) shareSelection(feature ?? null, true)
      },
    },
    search: {
      label: city ? `Vrtići: ${city}` : 'Karta vrtićkih objekata',
      data: snapshot.data,
      status: snapshot.status,
      notice: snapshot.notice,
      emptyNotice: city ? describeEmptySearch({ ...snapshot, city }) : undefined,
      selectedId: selection,
      select: (id: string | null) => {
        const feature = snapshot.data?.features.find(item => item.id === id)
        if (id !== null && !feature) return
        setSelection(id)
        shareSelection(feature ?? null)
      },
      retry: () => { void search() },
      nearby: city ? { value: snapshot.nearby ?? null, onChange: (value: Nearby | null) => { void search(value) } } : undefined,
      criteria: city ? { ...snapshot, city } : undefined,
    },
  }
}

export type McpLocationsViewModel = ReturnType<typeof useMcpLocations>
