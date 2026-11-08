import { useEffect, useRef, useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/mvvm/components/ui/button'
import { LocationCard } from './LocationCard'
import type { CompareChoice } from './CompareToggle'
import type { LocationFeature } from '../types'
import { useEntrance } from '@/mvvm/hooks/use-entrance'
import { reducedMotion } from '@/mvvm/utils/motion'

interface LocationCarouselProps {
  features: LocationFeature[]
  summary?: (feature: LocationFeature) => string
  selectedId: string | null
  reveal: { id: string; revision: number } | null
  onSelect: (id: string) => void

  caption?: string
  compare?: (feature: LocationFeature) => CompareChoice | undefined
}

function motion(): ScrollBehavior {
  return reducedMotion() ? 'auto' : 'smooth'
}

function anchor(track: HTMLElement, card: HTMLElement) {
  const padding = Number.parseFloat(getComputedStyle(track).scrollPaddingLeft) || 0
  return Math.max(0, Math.min(track.scrollWidth - track.clientWidth, card.getBoundingClientRect().left - track.getBoundingClientRect().left + track.scrollLeft - padding))
}


export function LocationCarousel({ features, selectedId, reveal, onSelect, caption, compare, summary }: LocationCarouselProps) {
  const trackRef = useRef<HTMLUListElement>(null)
  const [edges, setEdges] = useState({ start: true, end: features.length < 2 })

  useEntrance(trackRef, [features], { selector: '.location-slide', limit: 8 })
  useEffect(() => {
    const track = trackRef.current
    if (!track) return
    track.scrollLeft = 0
    const update = () => setEdges({ start: track.scrollLeft <= 2, end: track.scrollLeft + track.clientWidth >= track.scrollWidth - 2 })
    track.addEventListener('scroll', update, { passive: true })
    const observer = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(update) : null
    observer?.observe(track)
    update()
    return () => { track.removeEventListener('scroll', update); observer?.disconnect() }
  }, [features])
  useEffect(() => {
    if (!reveal) return
    const track = trackRef.current
    const index = features.findIndex((feature) => feature.id === reveal.id)
    const card = track?.children[index] as HTMLElement | undefined
    if (!track || !card) return
    const cardRect = card.getBoundingClientRect()
    const trackRect = track.getBoundingClientRect()
    if (cardRect.left < trackRect.left || cardRect.right > trackRect.right) {
      track.scrollTo?.({ left: anchor(track, card), behavior: motion() })
    }
  }, [reveal, features])
  function move(direction: number) {
    const track = trackRef.current
    if (!track) return
    const cards = Array.from(track.children) as HTMLElement[]
    const positions = cards.map((card) => anchor(track, card))
    const left = direction > 0
      ? positions.find((position) => position > track.scrollLeft + 2) ?? track.scrollWidth - track.clientWidth
      : positions.findLast((position) => position < track.scrollLeft - 2) ?? 0
    track.scrollTo?.({ left, behavior: motion() })
  }
  return <section className="location-carousel" aria-label="Popis objekata">
    {caption && <p className="location-carousel-caption" title={caption}>{caption}</p>}
    <div className="carousel-controls">
      <Button type="button" variant="outline" size="icon-lg" className="rounded-full" aria-label="Prethodni vrtić" disabled={edges.start} onClick={() => move(-1)}><ChevronLeft data-icon="inline-start" /></Button>
      <Button type="button" variant="outline" size="icon-lg" className="rounded-full" aria-label="Sljedeći vrtić" disabled={edges.end} onClick={() => move(1)}><ChevronRight data-icon="inline-end" /></Button>
    </div>
    <ul ref={trackRef} className="location-track" aria-label="Vrtićki objekti">
      {features.map((feature) => <li className="location-slide" key={feature.id}><LocationCard feature={feature} summary={summary?.(feature)} selected={feature.id === selectedId} onSelect={onSelect} compare={compare?.(feature)} /></li>)}
    </ul>
  </section>
}
