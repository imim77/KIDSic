import type { RefObject } from 'react'
import gsap from 'gsap'
import { useGSAP } from '@gsap/react'
import { reducedMotion } from '../utils/motion'

gsap.registerPlugin(useGSAP)

interface EntranceOptions {

  selector: string
  limit?: number

  container?: boolean
}





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
