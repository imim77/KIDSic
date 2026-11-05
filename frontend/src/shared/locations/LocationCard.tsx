import { Building2 } from 'lucide-react'
import { Button } from '../ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import type { LocationFeature } from './types'
import { SuitabilityBadge } from './ProgramDetails'
import { formatDistance } from './distance'

interface LocationCardProps {
  feature: LocationFeature
  selected: boolean
  onSelect: (id: string) => void
}

// LocationCard selects a map result from its compact name and address summary.
export function LocationCard({ feature, selected, onSelect }: LocationCardProps) {
  const location = feature.properties
  const rawAddress = location.address ?? 'Adresa nije poznata'
  const address = location.location_role === 'seat' ? `Sjedište: ${rawAddress}` : rawAddress
  const distance = location.distance_m == null ? '' : `${formatDistance(location.distance_m)} zračno`

  return <Card className="location-card relative flex-row items-center gap-3 rounded-[20px] p-3" data-selected={selected} role="article">
    <Button type="button" variant="ghost" className="absolute inset-0 h-full w-full rounded-[18px] p-0" aria-label={[location.location_name, address, distance].filter(Boolean).join(' ')} title={`${location.location_name}\n${address}`} aria-pressed={selected} data-location-card={feature.id} onClick={() => onSelect(feature.id)} />
    <div className="location-thumbnail pointer-events-none relative" aria-hidden="true">
      <Building2 />
    </div>
    <div className="pointer-events-none relative flex min-w-0 flex-1 flex-col justify-center gap-2 self-stretch">
      <CardHeader className="gap-0 p-0">
        <CardTitle className="min-w-0">
          <span className="block truncate font-display text-lg leading-tight font-normal tracking-[.01em]" title={location.location_name}>{location.location_name}</span>
        </CardTitle>
        <CardDescription className="truncate text-[13px]" title={address}>{address}</CardDescription>
      </CardHeader>
      <SuitabilityBadge status={location.suitability_status} />
      {distance && <p className="truncate text-xs font-semibold text-foreground">{distance}</p>}
      {location.district && <CardContent className="min-w-0 p-0">
        <p className="truncate text-xs text-muted-foreground" title={location.district}>{location.district}</p>
      </CardContent>}
    </div>
  </Card>
}
