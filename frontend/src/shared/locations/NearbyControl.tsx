import { useState } from 'react'
import { LocateFixed, MapPin, X } from 'lucide-react'
import { formatDistance } from './distance'
import type { Nearby } from './types'

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

// NearbyControl lets parents choose a point by device location or map click and
// a radius. Device location stays in the browser and is sent only as the query.
export function NearbyControl({ value, radius, picking, canPick, onLocate, onRadius, onPicking, onClear }: NearbyControlProps) {
  const [locating, setLocating] = useState(false)
  const [error, setError] = useState('')
  const locate = () => {
    if (!('geolocation' in navigator)) {
      setError('Preglednik ne podržava lokaciju. Odaberite točku na karti.')
      return
    }
    setError('')
    setLocating(true)
    onPicking(false)
    navigator.geolocation.getCurrentPosition((position) => {
      setLocating(false)
      onLocate([position.coords.longitude, position.coords.latitude])
    }, (failure) => {
      setLocating(false)
      setError(failure.code === failure.PERMISSION_DENIED
        ? 'Pristup lokaciji nije dopušten. Odaberite točku na karti.'
        : 'Lokaciju nije moguće odrediti. Odaberite točku na karti.')
    }, { enableHighAccuracy: false, timeout: 10_000, maximumAge: 60_000 })
  }

  return <section className="nearby-control" aria-label="Vrtići u blizini" onKeyDown={(event) => {
    if (event.key === 'Escape' && picking) onPicking(false)
  }}>
    <div className="nearby-actions">
      <button type="button" onClick={locate} disabled={locating} aria-busy={locating}>
        <LocateFixed aria-hidden="true" />{locating ? 'Tražim lokaciju…' : 'Moja lokacija'}
      </button>
      <button type="button" onClick={() => { setError(''); onPicking(!picking) }} disabled={!canPick} aria-pressed={picking}>
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
  </section>
}
