import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

const scrollMethods = ['scrollIntoView', 'scrollTo'] as const
const originalScrollMethods = new Map(scrollMethods.map(name =>
  [name, Object.getOwnPropertyDescriptor(Element.prototype, name)]))

beforeEach(() => {
  // jsdom has no layout engine; suites can override these for scroll behavior.
  for (const name of scrollMethods) {
    Object.defineProperty(Element.prototype, name, { configurable: true, writable: true, value: vi.fn() })
  }
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  for (const name of scrollMethods) {
    const original = originalScrollMethods.get(name)
    if (original) Object.defineProperty(Element.prototype, name, original)
    else Reflect.deleteProperty(Element.prototype, name)
  }
})
