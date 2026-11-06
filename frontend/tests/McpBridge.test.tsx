import type { ReactNode } from 'react'
import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { McpLocationApp } from '../src/views/mcp/McpLocationApp'
import { collection, facility } from './fixtures'
import { commuteResult } from './commuteFixtures'

vi.mock('../src/shared/map/KindergartenMap', () => ({
  KindergartenMap: ({ overlay }: { overlay?: (mapReady: boolean) => ReactNode }) => <div aria-label="Test map">{overlay?.(true)}</div>,
}))
afterEach(() => { vi.unstubAllGlobals(); Reflect.deleteProperty(Element.prototype, 'scrollTo') })

it('negotiates the real SDK postMessage bridge, receives results, and requests host fullscreen', async () => {
  vi.spyOn(console, 'debug').mockImplementation(() => {})
  vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} })
  Element.prototype.scrollTo = vi.fn()
  const methods: string[] = []
  const contexts: unknown[] = []
  const notify = (method: string, params: unknown) => window.dispatchEvent(new MessageEvent('message', {
    source: window.parent, data: { jsonrpc: '2.0', method, params },
  }))
  vi.spyOn(window.parent, 'postMessage').mockImplementation((message) => {
    const request = message as { jsonrpc: string; id?: number; method?: string; params?: { protocolVersion?: string; mode?: string } }
    if (!request.method) return
    methods.push(request.method)
    let result: unknown
    if (request.method === 'ui/initialize') result = {
      protocolVersion: request.params?.protocolVersion,
      hostInfo: { name: 'Test MCP host', version: '1.0' }, hostCapabilities: { serverTools: {} },
      hostContext: { displayMode: 'inline', availableDisplayModes: ['inline', 'fullscreen'] },
    }
    if (request.method === 'ui/request-display-mode') result = { mode: request.params?.mode }
    if (request.method === 'ui/update-model-context') {
      contexts.push(request.params)
      result = {}
    }
    if (result) queueMicrotask(() => window.dispatchEvent(new MessageEvent('message', {
      source: window.parent, data: { jsonrpc: '2.0', id: request.id, result },
    })))
    if (request.method === 'ui/notifications/initialized') queueMicrotask(() => {
      notify('ui/notifications/tool-input', { arguments: { city: 'Zagreb', name: 'Bajka', provider_kind: 'municipal', area: 'Črnomerec' } })
      const locations = collection(facility('bridge'))
      locations.features[0].properties.areas = ['Črnomerec']
      notify('ui/notifications/tool-result', { content: [], structuredContent: { city: 'Zagreb', name: 'Bajka', provider_kind: 'municipal', area: 'Črnomerec', metadata: locations.metadata }, _meta: { locations } })
    })
  })
  const { unmount } = render(<McpLocationApp />)
  expect(await screen.findByRole('button', { name: /Synthetic facility bridge.*Synthetic address/ })).toBeVisible()
  expect(methods).toContain('ui/initialize')
  expect(screen.queryByLabelText('Kriteriji pretrage')).toBeNull()
  await userEvent.click(screen.getByRole('button', { name: /Synthetic facility bridge.*Synthetic address/ }))
  expect(contexts).toEqual([{ content: [{ type: 'text', text: expect.stringContaining('"feature_id":"bridge"') }] }])
  expect(await screen.findByRole('button', { name: 'Vrati prikaz' })).toBeVisible()
  expect(methods).toContain('ui/request-display-mode')
  expect(screen.queryByLabelText('Kriteriji pretrage')).toBeNull()
  await act(async () => notify('ui/notifications/tool-input', { arguments: {} }))
  expect(screen.getByText('U kojem gradu želiš prikaz vrtića?')).toBeVisible()
  expect(screen.queryByText('Synthetic facility bridge')).toBeNull()
  await act(async () => notify('ui/notifications/tool-input', { arguments: {
    city: 'Rijeka', home: 'Zametska 6', work: 'Korzo 16', departure: '2026-11-05T07:00', mode: 'TRANSIT', top_k: 4,
  } }))
  await act(async () => notify('ui/notifications/tool-result', { content: [], _meta: { commute: commuteResult() } }))
  expect(screen.getByRole('button', { name: /Vrtić 0.*Najbolja opcija/ })).toBeVisible()
  expect(screen.getByText(/^Alternativa 3 ·/)).toBeVisible()
  unmount()
})
