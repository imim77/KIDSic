import { useId, useLayoutEffect, useRef, useState } from 'react'
import gsap from 'gsap'
import { ChevronDown, LocateFixed, MapPin, X } from 'lucide-react'
import { reducedMotion } from '@/mvvm/utils/motion'
import { formatDistance } from '@/mvvm/utils/format'
import type { Nearby } from '../types'
import { useDeviceLocation } from '../hooks/use-device-location'

const nearbyRadii = [500, 1000, 2000, 3000, 5000] as const

interface NearbyControlProps {
  value: Nearby | null
  radius: number
  picking: boolean
  canPick: boolean
  onLocate: (near: [number, number]) => void
  onRadius: (radius: number) => void
  onPicking: (picking: boolean) => void
  onClear: () => void
}




export function NearbyControl({ value, radius, picking, canPick, onLocate, onRadius, onPicking, onClear }: NearbyControlProps) {
  const [open, setOpen] = useState(false)
  const [mounted, setMounted] = useState(false)
  const bodyRef = useRef<HTMLDivElement>(null)
  const bodyId = useId()
  useLayoutEffect(() => {
    const body = bodyRef.current
    if (!body || reducedMotion()) return
    gsap.killTweensOf(body)

    if (open) {
      gsap.fromTo(body, { height: 0, opacity: 0, overflow: 'hidden' },
        { height: 'auto', opacity: 1, duration: 0.32, ease: 'power2.out', clearProps: 'height,opacity,overflow' })
    } else {
      gsap.to(body, { height: 0, opacity: 0, overflow: 'hidden', duration: 0.22, ease: 'power2.in', onComplete: () => setMounted(false) })
    }
  }, [open])
  const toggle = (next: boolean) => {
    if (next || reducedMotion()) setMounted(next)
    if (!next) onPicking(false)
    setOpen(next)
  }
  const { locating, error, locate: findDevice, clearError } = useDeviceLocation(onLocate)
  const locate = () => {
    onPicking(false)
    findDevice()
  }

  return <section className="nearby-control" aria-label="Vrtići u blizini" data-open={open} onKeyDown={(event) => {
    if (event.key !== 'Escape') return
    if (picking) onPicking(false)
    else if (open) toggle(false)
  }}>
    <button type="button" className="nearby-toggle" aria-expanded={open} aria-controls={bodyId} onClick={() => toggle(!open)}>
      <MapPin aria-hidden="true" />U blizini
      {value && <>{' '}<span className="nearby-toggle-radius">{formatDistance(value.radius_m)}</span></>}
      <ChevronDown aria-hidden="true" className="nearby-toggle-chevron" />
    </button>
    {mounted && <div ref={bodyRef} id={bodyId} className="nearby-body">

    <div className="nearby-body-inner">
    <div className="nearby-actions">
      <button type="button" onClick={locate} disabled={locating} aria-busy={locating}>
        <LocateFixed aria-hidden="true" />{locating ? 'Tražim lokaciju…' : 'Moja lokacija'}
      </button>
      <button type="button" onClick={() => { clearError(); onPicking(!picking) }} disabled={!canPick} aria-pressed={picking}>
        <MapPin aria-hidden="true" />{picking ? 'Kliknite na kartu' : 'Odaberi na karti'}
      </button>
      <label>
        <span>Radijus</span>
        <select value={radius} onChange={(event) => onRadius(Number(event.target.value))}>
          {[...new Set([...nearbyRadii, radius])].sort((a, b) => a - b).map((option) => <option key={option} value={option}>{formatDistance(option)}</option>)}
        </select>
      </label>
    </div>
    {value && <p className="nearby-summary">
      <span>Zračna udaljenost do {formatDistance(value.radius_m)}; samo objekti s potvrđenim koordinatama.</span>
      <button type="button" onClick={onClear}><X aria-hidden="true" />Ukloni</button>
    </p>}
    {picking && <p className="nearby-hint" role="status">Kliknite mjesto na karti. Esc odustaje.</p>}
    {error && <p className="nearby-error" role="alert">{error}</p>}
    </div>
    </div>}
  </section>
}
