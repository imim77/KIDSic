import gsap from 'gsap'
import { vi } from 'vitest'

export function finishAnimations() {
  gsap.globalTimeline.getChildren().forEach(animation => animation.progress(1))
}

export function preferReducedMotion(reduce: boolean) {
  vi.stubGlobal('matchMedia', vi.fn((query: string) => ({ matches: query.includes('reduce') && reduce })))
}
