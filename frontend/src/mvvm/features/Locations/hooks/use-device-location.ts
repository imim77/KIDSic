import { useState } from 'react'

// useDeviceLocation asks the browser once for an approximate position. The
// position stays in the browser and reaches `onLocate` as [longitude, latitude];
// failures become a message that points parents to picking on the map.
export function useDeviceLocation(onLocate: (near: [number, number]) => void) {
  const [locating, setLocating] = useState(false)
  const [error, setError] = useState('')
  const locate = () => {
    if (!('geolocation' in navigator)) {
      setError('Preglednik ne podržava lokaciju. Odaberite točku na karti.')
      return
    }
    setError('')
    setLocating(true)
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
  return { locating, error, locate, clearError: () => setError('') }
}
