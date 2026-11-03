import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { LocationDetails } from '../src/shared/locations/LocationDetails'
import { facility } from './fixtures'

describe('source evidence', () => {
  it('keeps historical field evidence separate from current records and labels unknown reference dates', () => {
    const feature = facility('provenance')
    feature.properties.field_sources = {
      longitude: {
        name: 'Historical coordinate source', url: 'https://example.invalid/older',
        license: null, reference_date: '2021-01-01', retrieved_at: '2021-02-01T10:00:00Z', active_snapshot: false,
      },
    }
    render(<LocationDetails feature={feature} onClose={vi.fn()} />)
    expect(screen.getByRole('heading', { name: 'Izvori aktualnih zapisa' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Podrijetlo pojedinih podataka' })).toBeVisible()
    const historical = screen.getByText('Zemljopisna dužina').closest('li')!
    expect(within(historical).getByText('Posljednji poznati podatak (starija snimka)')).toBeVisible()
    expect(within(historical).getByRole('link', { name: /Historical coordinate source/ })).toHaveAttribute('href', 'https://example.invalid/older')
    expect(historical).toHaveTextContent('2021.')
    expect(within(historical).getByText('Nije navedena')).toBeVisible()
    expect(screen.getByText('Nije poznato')).toBeVisible()
    expect(screen.getByRole('link', { name: /Synthetic source/ })).toHaveAttribute('href', 'https://example.invalid/source')
  })

  it('renders data as text and does not make an executable source URL clickable', () => {
    const feature = facility('unsafe')
    const literal = '<img src=x onerror=alert(1)>'
    feature.properties.name = literal
    feature.properties.sources[0].name = '<script>malicious()</script>'
    feature.properties.sources[0].url = 'javascript:alert(1)'
    const { container } = render(<LocationDetails feature={feature} onClose={vi.fn()} />)
    expect(screen.getByText(literal)).toBeVisible()
    expect(screen.getByText('<script>malicious()</script>')).toBeVisible()
    expect(screen.queryByRole('link')).toBeNull()
    expect(container.querySelector('script,img')).toBeNull()
  })
})
