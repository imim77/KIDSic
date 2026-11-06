import { render, screen } from '@testing-library/react'
import gsap from 'gsap'
import { afterEach, expect, it, vi } from 'vitest'
import { LocationDetails } from '@/mvvm/features/Locations/components/LocationDetails'
import { facility } from '@test-support/fixtures'

afterEach(() => vi.unstubAllGlobals())

function preferReducedMotion(reduce: boolean) {
  vi.stubGlobal('matchMedia', vi.fn((query: string) => ({ matches: query.includes('reduce') && reduce })))
}

it('fades details in and leaves no inline styles that would block hover or focus', () => {
  preferReducedMotion(false)
  render(<LocationDetails feature={facility('motion')} onClose={() => {}} />)
  const panel = screen.getByRole('region', { name: /Detalji/ })
  expect(panel.style.opacity).toBe('0')
  expect(panel).toHaveFocus()  // opacity, not visibility, keeps the panel focusable
  gsap.globalTimeline.getChildren().forEach((animation) => animation.progress(1))
  expect(panel.getAttribute('style') ?? '').toBe('')
  expect(screen.getByRole('heading', { level: 2 }).getAttribute('style') ?? '').toBe('')
})

it('shows the final state at once when the user prefers reduced motion', () => {
  preferReducedMotion(true)
  render(<LocationDetails feature={facility('still')} onClose={() => {}} />)
  expect(screen.getByRole('region', { name: /Detalji/ }).getAttribute('style') ?? '').toBe('')
  expect(screen.getByRole('heading', { level: 2 })).toBeVisible()
})
