export function decodePolyline(encoded: string): [number, number][] {
  const points: [number, number][] = []
  let index = 0, lat = 0, lon = 0
  function number() {
    let result = 0, shift = 0, byte: number
    do {
      if (index >= encoded.length || shift > 30) throw new Error('Invalid geometry')
      byte = encoded.charCodeAt(index++) - 63
      result |= (byte & 31) << shift
      shift += 5
    } while (byte >= 32)
    return result & 1 ? ~(result >> 1) : result >> 1
  }
  while (index < encoded.length) {
    lat += number(); lon += number()
    points.push([lat / 1e5, lon / 1e5])
  }
  return points
}
