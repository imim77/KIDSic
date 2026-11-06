import { App } from '@modelcontextprotocol/ext-apps'
import { useEffect, useRef, useState } from 'react'
import type { HostFullscreen } from '../components/FullscreenFrame'

type ToolResult = Parameters<NonNullable<App['ontoolresult']>>[0]

// McpAppEvents are the host notifications a screen ViewModel reacts to.
export interface McpAppEvents {
  onToolInput: (args: Record<string, unknown> | undefined) => void
  onToolResult: (result: ToolResult) => void
  onToolCancelled: () => void
  onConnectFailed: () => void
}

// McpHost is the connected host as ViewModels use it. Calls made before the
// connection exists, or after unmount, resolve to undefined.
export interface McpHost {
  callServerTool: (params: Parameters<App['callServerTool']>[0]) => Promise<ToolResult | undefined>
  updateModelContext: (text: string) => void
  openLink: (url: string) => void
  // Undefined while the host does not offer fullscreen.
  fullscreen: HostFullscreen | undefined
  expanded: boolean
}

// useMcpApp owns one MCP Apps connection for the screen's lifetime: it
// connects, follows the host's display mode and forwards tool notifications
// to the latest `events`, so handlers may close over fresh state.
export function useMcpApp(events: McpAppEvents): McpHost {
  const bridge = useRef<App | null>(null)
  const latest = useRef(events)
  const [display, setDisplay] = useState({ available: false, expanded: false })
  useEffect(() => { latest.current = events })

  useEffect(() => {
    const app = new App({ name: 'KIDSic karta', version: '0.1.0' }, { availableDisplayModes: ['inline', 'fullscreen'] })
    bridge.current = app
    let active = true
    const context = () => {
      if (!active) return
      const host = app.getHostContext()
      setDisplay({ available: host?.availableDisplayModes?.includes('fullscreen') ?? false, expanded: host?.displayMode === 'fullscreen' })
    }
    // Handlers are set before connecting, so no notification can be missed.
    app.onhostcontextchanged = context
    app.ontoolinput = ({ arguments: args }) => { if (active) latest.current.onToolInput(args) }
    app.ontoolresult = (result) => { if (active) latest.current.onToolResult(result) }
    app.ontoolcancelled = () => { if (active) latest.current.onToolCancelled() }
    void app.connect().then(context).catch(() => { if (active) latest.current.onConnectFailed() })
    return () => { active = false; bridge.current = null; void app.close() }
  }, [])

  return {
    callServerTool: async (params) => bridge.current?.callServerTool(params),
    // Context updates are hints for the model; a refused one changes nothing shown.
    updateModelContext: (text) => { void bridge.current?.updateModelContext({ content: [{ type: 'text', text }] }).catch(() => {}) },
    openLink: (url) => { void bridge.current?.openLink({ url }) },
    expanded: display.expanded,
    fullscreen: display.available ? {
      expanded: display.expanded,
      request: async (mode) => {
        const result = await bridge.current?.requestDisplayMode({ mode })
        if (result) setDisplay((previous) => ({ ...previous, expanded: result.mode === 'fullscreen' }))
      },
    } : undefined,
  }
}
