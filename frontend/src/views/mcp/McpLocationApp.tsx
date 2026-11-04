import { App } from '@modelcontextprotocol/ext-apps'
import { useEffect, useRef, useState } from 'react'
import { KindergartenExplorer } from '../../shared/explorer/KindergartenExplorer'
import { LocationToolResult } from '../../shared/mcp/LocationToolResult'
import type { LocationCollection } from '../../shared/locations/types'
import './mcp.css'

type Snapshot = { city: string | null; name?: string; data: LocationCollection | null; status: 'loading' | 'ready' | 'error'; notice?: string }
const initial: Snapshot = { city: null, data: null, status: 'loading', notice: 'U kojem gradu želiš prikaz vrtića?' }

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
      setSelection(null)
      setSnapshot(city ? { city, name, data: null, status: 'loading' } : initial)
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
        setSnapshot({ city: parsed.city, name: parsed.name ?? '', data: parsed.locations, status: 'ready' })
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

  const retry = async () => {
    const app = bridge.current
    const city = snapshot.city
    const name = snapshot.name ?? ''
    if (!app || !city) { setSnapshot(initial); return }
    const request = ++revision.current
    setSelection(null)
    setSnapshot({ city, name, data: null, status: 'loading' })
    try {
      const result = await app.callServerTool({ name: 'prikazi_vrtice', arguments: { city, ...(name ? { name } : {}) } })
      if (request !== revision.current) return
      if (result.isError) throw new Error('Tool failed')
      const parsed = await LocationToolResult.fromResult(result)
      if (request !== revision.current) return
      setSnapshot({ city: parsed.city, name: parsed.name ?? '', data: parsed.locations, status: 'ready' })
    } catch {
      if (request === revision.current) setSnapshot({ city, name, data: null, status: 'error' })
    }
  }

  return <main className="mcp-location-app w-full overflow-hidden" data-display-mode={display.expanded ? 'fullscreen' : 'inline'} aria-label={snapshot.city ? `Vrtići: ${snapshot.city}` : 'Karta vrtićkih objekata'}>
    <KindergartenExplorer data={snapshot.data} status={snapshot.status} selectedId={selection} onSelect={setSelection}
      criteria={snapshot.city ? { city: snapshot.city, name: snapshot.name } : undefined}
      notice={snapshot.notice}
      emptyNotice={snapshot.name ? `Za naziv „${snapshot.name}” u gradu ${snapshot.city} nema rezultata. Provjerite ili skratite naziv u razgovoru.` : undefined}
      retry={() => { void retry() }}
      openLink={(url) => { void bridge.current?.openLink({ url }) }}
      hostFullscreen={display.available ? { expanded: display.expanded, request: async (mode) => {
        const result = await bridge.current!.requestDisplayMode({ mode })
        setDisplay((previous) => ({ ...previous, expanded: result.mode === 'fullscreen' }))
      } } : undefined} />
  </main>
}
