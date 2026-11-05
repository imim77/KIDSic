import { App } from '@modelcontextprotocol/ext-apps'
import { useEffect, useRef, useState } from 'react'
import { KindergartenExplorer } from '../../shared/explorer/KindergartenExplorer'
import { LocationToolResult } from '../../shared/mcp/LocationToolResult'
import { isAgeMonths, isProviderKind, providerLabels, type LocationCollection, type Nearby, type SearchCriteria } from '../../shared/locations/types'
import { formatDistance } from '../../shared/locations/distance'
import './mcp.css'

type Snapshot = Omit<SearchCriteria, 'city'> & { city: string | null; data: LocationCollection | null; status: 'loading' | 'ready' | 'error'; notice?: string }
const initial: Snapshot = { city: null, data: null, status: 'loading', notice: 'U kojem gradu želiš prikaz vrtića?' }

// toolArguments sends every retained criterion, since each call is a full search.
function toolArguments({ city, name, provider_kind, area, age_months, program, include_unknown, nearby }: SearchCriteria) {
  return { city, ...(name ? { name } : {}), ...(provider_kind ? { provider_kind } : {}), ...(area ? { area } : {}),
    ...(age_months != null ? { age_months } : {}), ...(program ? { program } : {}),
    ...(age_months != null || program || include_unknown === false ? { include_unknown } : {}),
    ...(nearby ? { near: nearby.near, radius_m: nearby.radius_m } : {}) }
}

function toolNearby(near: unknown, radius: unknown): Nearby | null {
  return Array.isArray(near) && near.length === 2 && near.every((n) => typeof n === 'number' && Number.isFinite(n))
    && typeof radius === 'number' && Number.isInteger(radius) ? { near: [near[0], near[1]], radius_m: radius } : null
}

// McpLocationApp receives city results exclusively through the MCP host bridge.
export function McpLocationApp() {
  const bridge = useRef<App | null>(null)
  const revision = useRef(0)
  const [snapshot, setSnapshot] = useState<Snapshot>(initial)
  const [selection, setSelection] = useState<string | null>(null)
  const [display, setDisplay] = useState({ available: false, expanded: false })

  useEffect(() => {
    const app = new App({ name: 'KIDSic karta', version: '0.1.0' }, { availableDisplayModes: ['inline', 'fullscreen'] })
    bridge.current = app
    let active = true
    const invalidate = () => { revision.current++ }
    const context = () => {
      if (!active) return
      const host = app.getHostContext()
      setDisplay({ available: host?.availableDisplayModes?.includes('fullscreen') ?? false, expanded: host?.displayMode === 'fullscreen' })
    }
    app.onhostcontextchanged = context
    app.ontoolinput = ({ arguments: args }) => {
      revision.current++
      const city = typeof args?.city === 'string' ? args.city.trim() : ''
      const name = typeof args?.name === 'string' ? args.name.trim() : ''
      const area = typeof args?.area === 'string' ? args.area.trim() : ''
      const age_months = isAgeMonths(args?.age_months) ? args.age_months : null
      const program = typeof args?.program === 'string' ? args.program.trim() : ''
      const include_unknown = typeof args?.include_unknown === 'boolean' ? args.include_unknown : true
      const provider_kind = isProviderKind(args?.provider_kind) ? args.provider_kind : null
      const nearby = toolNearby(args?.near, args?.radius_m)
      setSelection(null)
      setSnapshot(city ? { city, name, area, provider_kind, age_months, program, include_unknown, nearby, data: null, status: 'loading' } : initial)
    }
    app.ontoolresult = async (result) => {
      const request = ++revision.current
      setSelection(null)
      if (result.isError) {
        setSnapshot((previous) => previous.city ? { ...previous, data: null, status: 'error' } : initial)
        return
      }
      try {
        const parsed = await LocationToolResult.fromResult(result)
        if (!active || request !== revision.current) return
        setSnapshot({ city: parsed.city, name: parsed.name ?? '', area: parsed.area ?? '', provider_kind: parsed.provider_kind ?? null, age_months: parsed.age_months ?? null, program: parsed.program ?? '', include_unknown: parsed.include_unknown ?? true, nearby: parsed.nearby ?? null, data: parsed.locations, status: 'ready' })
      } catch {
        if (active && request === revision.current) setSnapshot((previous) => ({ ...previous, data: null, status: 'error' }))
      }
    }
    app.ontoolcancelled = () => {
      revision.current++
      setSnapshot((previous) => ({ ...previous, data: null, status: 'error' }))
    }
    void app.connect().then(context).catch(() => {
      if (active) setSnapshot({ city: null, data: null, status: 'loading', notice: 'Otvori ovaj prikaz kroz MCP alat u AI klijentu i navedi grad.' })
    })
    return () => { active = false; invalidate(); bridge.current = null; void app.close() }
  }, [])

  // search repeats the current criteria through the server tool; nearby
  // replaces only the point and radius chosen in the map.
  const search = async (nearby: Nearby | null | undefined = snapshot.nearby) => {
    const app = bridge.current
    const city = snapshot.city
    const criteria = { name: snapshot.name ?? '', area: snapshot.area ?? '', provider_kind: snapshot.provider_kind ?? null,
      age_months: snapshot.age_months ?? null, program: snapshot.program ?? '', include_unknown: snapshot.include_unknown ?? true,
      nearby: nearby ?? null }
    if (!app || !city) { setSnapshot(initial); return }
    const request = ++revision.current
    const changedPoint = nearby !== snapshot.nearby
    setSelection(null)
    setSnapshot({ city, ...criteria, data: null, status: 'loading' })
    try {
      const result = await app.callServerTool({ name: 'prikazi_vrtice', arguments: toolArguments({ city, ...criteria }) })
      if (request !== revision.current) return
      if (result.isError) throw new Error('Tool failed')
      const parsed = await LocationToolResult.fromResult(result)
      if (request !== revision.current) return
      setSnapshot({ city: parsed.city, name: parsed.name ?? '', area: parsed.area ?? '', provider_kind: parsed.provider_kind ?? null, age_months: parsed.age_months ?? null, program: parsed.program ?? '', include_unknown: parsed.include_unknown ?? true, nearby: parsed.nearby ?? null, data: parsed.locations, status: 'ready' })
      // The model did not make this call; tell it so follow-ups keep the point.
      if (changedPoint) void app.updateModelContext({ content: [{ type: 'text', text: parsed.nearby
        ? `Korisnik je na karti odabrao točku [${parsed.nearby.near.join(', ')}] i zračni radijus ${parsed.nearby.radius_m} m; `
          + `prikazano ${parsed.locations.metadata.total} rezultata. Za nastavak pošalji near i radius_m uz ostale kriterije.`
        : `Korisnik je na karti uklonio točku; prikazan je cijeli grad ${parsed.city}. Ne šalji near ni radius_m.` }] }).catch(() => {})
    } catch {
      if (request === revision.current) setSnapshot({ city, ...criteria, data: null, status: 'error' })
    }
  }

  const emptyNotice = snapshot.name || snapshot.provider_kind || snapshot.area || snapshot.age_months != null || snapshot.program || snapshot.nearby
    ? `Nema rezultata za grad ${snapshot.city}${snapshot.nearby ? `, zračno do ${formatDistance(snapshot.nearby.radius_m)} od odabrane točke` : ''}${snapshot.name ? `, naziv „${snapshot.name}”` : ''}${snapshot.provider_kind ? `, vrstu „${providerLabels[snapshot.provider_kind]}”` : ''}${snapshot.area ? `, područje „${snapshot.area}”` : ''}${snapshot.age_months != null ? `, dob ${snapshot.age_months} mjeseci` : ''}${snapshot.program ? `, program „${snapshot.program}”` : ''}. Provjerite ili promijenite kriterije u razgovoru.${snapshot.area ? ' Nema zapisa s potvrđenim podudaranjem područja; to ne znači da ondje nema vrtića.' : ''}${snapshot.age_months != null || snapshot.program ? ' Nema podataka koji potvrđuju zadane uvjete; to nije dokaz da program nije dostupan.' : ''}`
    : undefined

  return <main className="mcp-location-app w-full overflow-hidden" data-display-mode={display.expanded ? 'fullscreen' : 'inline'} aria-label={snapshot.city ? `Vrtići: ${snapshot.city}` : 'Karta vrtićkih objekata'}>
    <KindergartenExplorer data={snapshot.data} status={snapshot.status} selectedId={selection} onSelect={setSelection}
      notice={snapshot.notice}
      emptyNotice={emptyNotice}
      retry={() => { void search() }}
      nearby={snapshot.city ? { value: snapshot.nearby ?? null, onChange: (value) => { void search(value) } } : undefined}
      criteria={snapshot.city ? { ...snapshot, city: snapshot.city } : undefined}
      openLink={(url) => { void bridge.current?.openLink({ url }) }}
      hostFullscreen={display.available ? { expanded: display.expanded, request: async (mode) => {
        const result = await bridge.current!.requestDisplayMode({ mode })
        setDisplay((previous) => ({ ...previous, expanded: result.mode === 'fullscreen' }))
      } } : undefined} />
  </main>
}
