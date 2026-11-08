import { useEffect, useState } from 'react'



export function useMediaQuery(query: string, fallback: boolean) {
  const [matches, setMatches] = useState(() => window.matchMedia?.(query).matches ?? fallback)
  useEffect(() => {
    const list = window.matchMedia?.(query)
    if (!list?.addEventListener) return
    const update = () => setMatches(list.matches)
    update()
    list.addEventListener('change', update)
    return () => list.removeEventListener('change', update)
  }, [query])
  return matches
}
