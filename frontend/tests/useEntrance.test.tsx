import { finishAnimations, preferReducedMotion } from '@test-support/motion'
import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { LocationDetails } from '@/mvvm/features/Locations/components/LocationDetails'
import { facility } from '@test-support/fixtures'



it('fades details in and leaves no inline styles that would block hover or focus', () => {
  preferReducedMotion(false)
  render(<LocationDetails feature={facility('motion')} onClose={() => {}} />)
  const panel = screen.getByRole('region', { name: /Detalji/ })
  expect(panel.style.opacity).toBe('0')
  expect(panel).toHaveFocus()
  finishAnimations()
  expect(panel.getAttribute('style') ?? '').toBe('')
  expect(screen.getByRole('heading', { level: 2 }).getAttribute('style') ?? '').toBe('')
})

it('shows the final state at once when the user prefers reduced motion', () => {
  preferReducedMotion(true)
  render(<LocationDetails feature={facility('still')} onClose={() => {}} />)
  expect(screen.getByRole('region', { name: /Detalji/ }).getAttribute('style') ?? '').toBe('')
  expect(screen.getByRole('heading', { level: 2 })).toBeVisible()
})
