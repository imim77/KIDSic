import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { McpLocationApp } from '../src/views/mcp/McpLocationApp'
import { collection, facility } from './fixtures'

vi.mock('../src/shared/map/KindergartenMap', () => ({ KindergartenMap: () => <div aria-label="Test map" /> }))
afterEach(() => { vi.unstubAllGlobals(); Reflect.deleteProperty(Element.prototype, 'scrollTo') })

it('negotiates the real SDK postMessage bridge, receives results, and requests host fullscreen', async () => {
  vi.spyOn(console, 'debug').mockImplementation(() => {})
  vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} })
  Element.prototype.scrollTo = vi.fn()
  const methods: string[] = []
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
    if (result) queueMicrotask(() => window.dispatchEvent(new MessageEvent('message', {
      source: window.parent, data: { jsonrpc: '2.0', id: request.id, result },
    })))
    if (request.method === 'ui/notifications/initialized') queueMicrotask(() => {
      notify('ui/notifications/tool-input', { arguments: { city: 'Zagreb', name: 'Bajka' } })
      const locations = collection(facility('bridge'))
      notify('ui/notifications/tool-result', { content: [], structuredContent: { city: 'Zagreb', name: 'Bajka', metadata: locations.metadata }, _meta: { locations } })
    })
  })
  const { unmount } = render(<McpLocationApp />)
  expect(await screen.findByRole('button', { name: /Synthetic facility bridge.*Synthetic address/ })).toBeVisible()
  expect(methods).toContain('ui/initialize')
  await userEvent.click(screen.getByRole('button', { name: 'Prikaži preko cijelog ekrana' }))
  expect(await screen.findByRole('button', { name: 'Vrati prikaz' })).toBeVisible()
  expect(methods).toContain('ui/request-display-mode')
  expect(screen.getByText('Grad: Zagreb')).toBeVisible()
  expect(screen.getByText('Naziv: „Bajka”')).toBeVisible()
  await act(async () => notify('ui/notifications/tool-input', { arguments: {} }))
  expect(screen.getByText('U kojem gradu želiš prikaz vrtića?')).toBeVisible()
  expect(screen.queryByText('Synthetic facility bridge')).toBeNull()
  expect(screen.queryByText('Naziv: „Bajka”')).toBeNull()
  unmount()
})
