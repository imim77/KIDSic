import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import gsap from 'gsap'
import { afterEach, expect, it, vi } from 'vitest'
import { Disclosure } from '@/mvvm/components/Disclosure'

afterEach(() => vi.unstubAllGlobals())

const finish = () => gsap.globalTimeline.getChildren().forEach((animation) => animation.progress(1))

function preferReducedMotion(reduce: boolean) {
  vi.stubGlobal('matchMedia', vi.fn((query: string) => ({ matches: query.includes('reduce') && reduce })))
}

it('slides the body open, keeps it visible until closing ends and leaves no inline styles', async () => {
  preferReducedMotion(false)
  const { container } = render(<Disclosure summary="Tarife"><p>Cjelodnevne jaslice</p></Disclosure>)
  const details = container.querySelector('details')!
  const body = container.querySelector<HTMLElement>('.disclosure-body')!
  await userEvent.click(screen.getByText('Tarife'))
  expect(details.open).toBe(true)
  expect(body.style.overflow).toBe('hidden')
  finish()
  expect(body.getAttribute('style') ?? '').toBe('')
  await userEvent.click(screen.getByText('Tarife'))
  expect(details.open).toBe(true)  // still animating closed
  finish()
  expect(details.open).toBe(false)
  expect(body.getAttribute('style') ?? '').toBe('')
})

it('reopens a body that is still closing instead of losing the click', async () => {
  preferReducedMotion(false)
  const { container } = render(<Disclosure summary="Tarife"><p>Sadržaj</p></Disclosure>)
  const details = container.querySelector('details')!
  await userEvent.click(screen.getByText('Tarife')); finish()
  await userEvent.click(screen.getByText('Tarife'))
  await userEvent.click(screen.getByText('Tarife'))
  finish()
  expect(details.open).toBe(true)
})

it('leaves toggling to the browser when the user prefers reduced motion', async () => {
  preferReducedMotion(true)
  const { container } = render(<Disclosure summary="Tarife"><p>Sadržaj</p></Disclosure>)
  await userEvent.click(screen.getByText('Tarife'))
  expect(container.querySelector('details')!.open).toBe(true)
  expect(container.querySelector('.disclosure-body')!.getAttribute('style') ?? '').toBe('')
})
