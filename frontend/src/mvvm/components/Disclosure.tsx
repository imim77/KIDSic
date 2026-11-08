import type { MouseEvent, ReactNode } from 'react'
import gsap from 'gsap'
import { reducedMotion } from '../utils/motion'



function toggle(event: MouseEvent<HTMLElement>) {
  const details = event.currentTarget.parentElement
  const body = event.currentTarget.nextElementSibling
  if (!(details instanceof HTMLDetailsElement) || !(body instanceof HTMLElement) || reducedMotion()) return
  event.preventDefault()
  gsap.killTweensOf(body)

  if (!details.open || details.dataset.closing) {
    delete details.dataset.closing
    details.open = true
    gsap.fromTo(body, { height: 0, opacity: 0, overflow: 'hidden' },
      { height: 'auto', opacity: 1, duration: 0.32, ease: 'power2.out', clearProps: 'height,opacity,overflow' })
  } else {
    details.dataset.closing = 'true'
    gsap.to(body, { height: 0, opacity: 0, overflow: 'hidden', duration: 0.22, ease: 'power2.in',
      onComplete: () => {
        delete details.dataset.closing
        details.open = false
        gsap.set(body, { clearProps: 'height,opacity,overflow' })
      } })
  }
}





export function Disclosure({ summary, children }: { summary: ReactNode; children: ReactNode }) {
  return <details className="disclosure">
    <summary onClick={toggle}>{summary}</summary>
    <div className="disclosure-body">{children}</div>
  </details>
}
