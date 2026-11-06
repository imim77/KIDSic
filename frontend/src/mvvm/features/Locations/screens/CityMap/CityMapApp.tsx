import { KindergartenExplorer } from '../../components/KindergartenExplorer'
import { useCityMap } from '../../hooks/use-city-map'

// CityMapApp shows the standalone city map, fed by the location API.
export function CityMapApp() {
  const { select, ...map } = useCityMap()
  return (
    <main className="w-full h-dvh overflow-hidden p-2" aria-label="Karta vrtićkih objekata">
      <KindergartenExplorer {...map} onSelect={select} />
    </main>
  )
}
