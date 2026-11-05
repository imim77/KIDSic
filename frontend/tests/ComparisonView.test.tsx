import { render, screen, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { ComparisonView } from '../src/shared/locations/ComparisonView'
import { facility } from './fixtures'

afterEach(() => vi.unstubAllGlobals())

it('stacks one section per criterion on phones instead of a wide table', () => {
  vi.stubGlobal('matchMedia', (query: string) => ({ matches: query === '(max-width: 650px)', addEventListener: () => {}, removeEventListener: () => {} }))
  const first = facility('a')
  first.properties.district = 'Trnje'
  render(<ComparisonView features={[first, facility('b')]} onRemove={() => {}} onClose={() => {}} />)
  expect(screen.queryByRole('table')).toBeNull()
  expect(within(screen.getByRole('list', { name: 'Vrtići u usporedbi' })).getAllByRole('listitem')).toHaveLength(2)
  const address = screen.getByRole('region', { name: 'Adresa' })
  expect(within(address).getByText('Synthetic facility a')).toBeVisible()
  expect(within(address).getByText('Trnje')).toHaveClass('comparison-sticker')
  expect(within(screen.getByRole('region', { name: 'Programi i dob' })).getAllByText('Nije potvrđeno')).toHaveLength(2)
})
