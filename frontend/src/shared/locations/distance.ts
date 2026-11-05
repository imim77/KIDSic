// formatDistance renders whole metres below a kilometre and one decimal above.
export function formatDistance(metres: number) {
  if (metres < 1000) return `${metres} m`
  return `${(metres / 1000).toLocaleString('hr', { maximumFractionDigits: 1 })} km`
}
