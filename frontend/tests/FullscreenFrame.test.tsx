import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FullscreenFrame } from '@/mvvm/components/FullscreenFrame'
import { deferred } from '@test-support/fixtures'

const enterLabel = 'Prikaži preko cijelog ekrana'
const exitLabel = 'Vrati prikaz'
function nativeState(element: Element | null) {
  Object.defineProperty(document, 'fullscreenElement', { configurable: true, value: element })
  document.dispatchEvent(new Event('fullscreenchange'))
}
afterEach(() => {
  vi.restoreAllMocks()
  Reflect.deleteProperty(HTMLElement.prototype, 'requestFullscreen')
  Reflect.deleteProperty(document, 'exitFullscreen')
  Reflect.deleteProperty(document, 'fullscreenElement')
  Reflect.deleteProperty(document, 'fullscreenEnabled')
  document.body.style.overflow = ''
})

describe('fullscreen explorer', () => {
  it('uses actual native state, survives external Escape, and keeps the same children', async () => {
    const user = userEvent.setup()
    const request = vi.fn(function (this: HTMLElement) { nativeState(this); return Promise.resolve() })
    Object.defineProperty(HTMLElement.prototype, 'requestFullscreen', { configurable: true, value: request })
    const exit = vi.fn(async () => nativeState(null))
    Object.defineProperty(document, 'exitFullscreen', { configurable: true, value: exit })
    render(<FullscreenFrame><input aria-label="Preserved filter" defaultValue="Zagreb" /></FullscreenFrame>)
    const child = screen.getByLabelText('Preserved filter')
    const toggle = screen.getByRole('button', { name: enterLabel })
    await user.click(toggle)
    expect(request).toHaveBeenCalledOnce()
    expect(document.fullscreenElement).toBe(child.parentElement)
    expect(toggle).toHaveAccessibleName(exitLabel)
    expect(screen.queryByRole('dialog')).toBeNull()
    fireEvent.keyDown(toggle, { key: 'Escape' })
    await waitFor(() => expect(toggle).toHaveAccessibleName(enterLabel))
    expect(exit).toHaveBeenCalledOnce()
    expect(toggle).toHaveFocus()
    expect(screen.getByLabelText('Preserved filter')).toBe(child)
    await user.click(toggle)
    act(() => nativeState(null))
    expect(toggle).toHaveAccessibleName(enterLabel)
    expect(toggle).toHaveFocus()
  })

  it('restores toggle focus when native exit emits fullscreenchange before its promise resolves', async () => {
    const user = userEvent.setup()
    const pending = deferred<void>()
    Object.defineProperty(HTMLElement.prototype, 'requestFullscreen', { configurable: true, value: vi.fn(function (this: HTMLElement) { nativeState(this); return Promise.resolve() }) })
    Object.defineProperty(document, 'exitFullscreen', { configurable: true, value: vi.fn(() => pending.promise) })
    render(<FullscreenFrame><button>Map control</button></FullscreenFrame>)
    const toggle = screen.getByRole('button', { name: enterLabel })
    await user.click(toggle)
    await user.click(toggle)
    expect(toggle).toBeEnabled()
    act(() => nativeState(null))
    expect(toggle).toHaveFocus()
    await act(async () => { pending.resolve(); await pending.promise })
    expect(toggle).toHaveFocus()
  })

  it('falls back after rejection, traps focus, and restores body scroll and focus on Escape', async () => {
    const user = userEvent.setup()
    Object.defineProperty(HTMLElement.prototype, 'requestFullscreen', { configurable: true, value: vi.fn().mockRejectedValue(new Error('denied')) })
    document.body.style.overflow = 'scroll'
    render(<><button>Outside</button><FullscreenFrame><button>Inside</button></FullscreenFrame></>)
    const toggle = screen.getByRole('button', { name: enterLabel })
    const outside = screen.getByRole('button', { name: 'Outside' })
    await user.click(toggle)
    expect(await screen.findByRole('dialog')).toHaveAttribute('aria-modal', 'true')
    expect(toggle).toHaveAttribute('aria-pressed', 'true')
    expect(document.fullscreenElement).toBeFalsy()
    expect(document.body.style.overflow).toBe('hidden')
    expect(outside).toHaveAttribute('inert')
    await user.tab()
    expect(screen.getByRole('button', { name: 'Inside' })).toHaveFocus()
    await user.tab({ shift: true })
    expect(toggle).toHaveFocus()
    outside.focus()
    expect(toggle).toHaveFocus()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(document.body.style.overflow).toBe('scroll')
    expect(outside).not.toHaveAttribute('inert')
    expect(toggle).toHaveFocus()
    outside.focus()
    expect(outside).toHaveFocus()
  })

  it('cleans fallback listeners and inert state when unmounted', async () => {
    const user = userEvent.setup()
    const outside = document.createElement('button')
    outside.textContent = 'Persistent outside'
    outside.setAttribute('inert', '')
    document.body.append(outside)
    const { unmount } = render(<FullscreenFrame><button>Inside</button></FullscreenFrame>)
    await user.click(screen.getByRole('button', { name: enterLabel }))
    expect(document.body.style.overflow).toBe('hidden')
    unmount()
    expect(document.body.style.overflow).toBe('')
    expect(outside).toHaveAttribute('inert')
    outside.removeAttribute('inert')
    outside.focus()
    expect(outside).toHaveFocus()
    outside.remove()
  })

  it('does not expand early and exits a native request that resolves after unmount', async () => {
    const user = userEvent.setup()
    const pending = deferred<void>()
    Object.defineProperty(HTMLElement.prototype, 'requestFullscreen', { configurable: true, value: vi.fn(() => pending.promise) })
    const exit = vi.fn(async () => nativeState(null))
    Object.defineProperty(document, 'exitFullscreen', { configurable: true, value: exit })
    const { unmount } = render(<FullscreenFrame><span>Map</span></FullscreenFrame>)
    const toggle = screen.getByRole('button', { name: enterLabel })
    const frame = toggle.parentElement!
    await user.click(toggle)
    expect(toggle).toHaveAttribute('aria-disabled', 'true')
    await user.click(toggle)
    expect(HTMLElement.prototype.requestFullscreen).toHaveBeenCalledOnce()
    expect(toggle).toHaveAttribute('aria-pressed', 'false')
    unmount()
    await act(async () => { nativeState(frame); pending.resolve(); await pending.promise })
    expect(exit).toHaveBeenCalledOnce()
  })
})
