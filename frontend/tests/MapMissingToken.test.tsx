import { render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'

const mapbox = vi.hoisted(() => ({ supported: vi.fn(), Map: vi.fn() }))
vi.mock('mapbox-gl', () => ({ default: mapbox }))

afterEach(() => vi.unstubAllEnvs())

it('keeps a usable directory fallback without allocating Mapbox when the token is absent', async () => {
  vi.stubEnv('VITE_MAPBOX_ACCESS_TOKEN', '')
  const { KindergartenMap } = await import('../src/shared/map/KindergartenMap')
  render(<KindergartenMap />)
  expect(screen.getByRole('status')).toHaveTextContent('Objekte možete pregledati na popisu')
  await Promise.resolve()
  expect(mapbox.supported).not.toHaveBeenCalled()
  expect(mapbox.Map).not.toHaveBeenCalled()
})
