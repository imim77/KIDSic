import type { RefObject } from 'react'
import gsap from 'gsap'
import { useGSAP } from '@gsap/react'
import { reducedMotion } from './reducedMotion'

gsap.registerPlugin(useGSAP)

interface EntranceOptions {
  // Children to reveal in document order; only the first `limit` animate.
  selector: string
  limit?: number
  // Also moves the scope itself in before its children.
  container?: boolean
}

// useEntrance fades a container's children in, staggered, whenever `deps`
// change. It animates opacity and translation only and clears them when done:
// hidden-by-visibility elements could not take focus, and leftover inline
// transforms would override the CSS hover and press states.
export function useEntrance(scope: RefObject<HTMLElement | null>, deps: unknown[],
                            { selector, limit = 12, container = false }: EntranceOptions) {
  useGSAP(() => {
    const root = scope.current
    if (!root || reducedMotion()) return
    const items = gsap.utils.toArray<HTMLElement>(selector, root).slice(0, limit)
    const timeline = gsap.timeline({ defaults: { ease: 'power3.out', clearProps: 'opacity,transform' } })
    if (container) timeline.from(root, { opacity: 0, y: 18, duration: 0.32 })
    if (items.length) timeline.from(items, { opacity: 0, y: 14, duration: 0.42, stagger: 0.045 }, container ? '-=0.18' : 0)
  }, { scope, dependencies: deps, revertOnUpdate: true })
}
