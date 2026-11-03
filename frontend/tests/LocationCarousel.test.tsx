import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { LocationCarousel } from '../src/shared/locations/LocationCarousel'
import { facility } from './fixtures'

const features = [facility('first'), facility('second'), facility('third')]
const onSelect = vi.fn()
const scrollTo = vi.fn(function (this: HTMLElement, options: ScrollToOptions) {
  this.scrollLeft = Math.max(0, Math.min(this.scrollWidth - this.clientWidth, options.left ?? 0))
  fireEvent.scroll(this)
})
beforeEach(() => {
  vi.clearAllMocks()
  vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(300)
  vi.spyOn(HTMLElement.prototype, 'scrollWidth', 'get').mockReturnValue(900)
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
    const left = this.tagName === 'LI' ? Array.from(this.parentElement!.children).indexOf(this) * 300 - this.parentElement!.scrollLeft : 0
    return { left, right: left + 300, top: 0, bottom: 200, width: 300, height: 200, x: left, y: 0, toJSON: () => ({}) }
  })
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: true })))
  Object.defineProperty(HTMLElement.prototype, 'scrollTo', { configurable: true, value: scrollTo })
})
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); Reflect.deleteProperty(HTMLElement.prototype, 'scrollTo') })
function props() { return { features, selectedId: null, reveal: null, onSelect } }

describe('location carousel', () => {
  it('moves both directions to bounded edges without selecting a card', async () => {
    const user = userEvent.setup()
    render(<LocationCarousel {...props()} />)
    const previous = screen.getByRole('button', { name: 'Prethodni vrtić' })
    const next = screen.getByRole('button', { name: 'Sljedeći vrtić' })
    expect(previous).toBeDisabled()
    await user.click(next)
    expect(scrollTo).toHaveBeenLastCalledWith({ left: 300, behavior: 'auto' })
    expect(previous).toBeEnabled()
    await user.click(next)
    expect(next).toBeDisabled()
    await user.click(previous)
    await user.click(previous)
    expect(previous).toBeDisabled()
    expect(onSelect).not.toHaveBeenCalled()
  })
  it('reveals marker selection by scrolling only its own viewport and leaves manual browsing unselected', () => {
    const pageScroll = vi.fn()
    vi.stubGlobal('scrollTo', pageScroll)
    const { rerender } = render(<LocationCarousel {...props()} />)
    const track = screen.getByRole('list', { name: 'Vrtićki objekti' })
    track.scrollLeft = 200
    fireEvent.scroll(track)
    expect(onSelect).not.toHaveBeenCalled()
    rerender(<LocationCarousel {...props()} selectedId="third" reveal={{ id: 'third', revision: 1 }} />)
    expect(scrollTo).toHaveBeenLastCalledWith({ left: 600, behavior: 'auto' })
    expect(scrollTo.mock.instances.at(-1)).toBe(track)
    expect(pageScroll).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: /Synthetic facility third.*Synthetic address/ })).toHaveAttribute('aria-pressed', 'true')
  })
  it('keeps keyboard selection and unknown address fallback without details actions', async () => {
    const first = facility('first')
    first.properties.address = null
    const user = userEvent.setup()
    render(<LocationCarousel {...props()} features={[first]} />)
    const select = screen.getByRole('button', { name: /Synthetic facility first.*Adresa nije poznata/ })
    select.focus()
    await user.keyboard('{Enter}')
    expect(onSelect).toHaveBeenCalledExactlyOnceWith('first')
    expect(screen.queryByRole('button', { name: /Detalji i izvori/ })).toBeNull()
  })
})
