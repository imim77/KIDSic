import { Building2 } from 'lucide-react'
import { Button } from '../ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import type { LocationFeature } from './types'
import { formatDistance } from './distance'
import { CompareToggle, type CompareChoice } from './CompareToggle'

interface LocationCardProps {
  feature: LocationFeature
  summary?: string
  selected: boolean
  onSelect: (id: string) => void
  compare?: CompareChoice
}

// LocationCard selects a map result from its compact name and address summary.
export function LocationCard({ feature, selected, onSelect, compare, summary }: LocationCardProps) {
  const location = feature.properties
  const rawAddress = location.address ?? 'Adresa nije poznata'
  const address = location.location_role === 'seat' ? `Sjedište: ${rawAddress}` : rawAddress
  const distance = location.distance_m == null ? '' : `${formatDistance(location.distance_m)} zračno`

  return <Card className="location-card relative flex-row items-center gap-2.5 rounded-[18px] p-2.5" data-selected={selected} role="article">
    <Button type="button" variant="ghost" className="absolute inset-0 h-full w-full rounded-[16px] p-0" aria-label={[location.location_name, address, distance].filter(Boolean).join(' ')} title={`${location.location_name}\n${address}`} aria-pressed={selected} data-location-card={feature.id} onClick={() => onSelect(feature.id)} />
    <div className="location-thumbnail pointer-events-none relative" aria-hidden="true">
      <Building2 />
    </div>
    <div className="location-card-text pointer-events-none relative flex min-w-0 flex-1 flex-col justify-center gap-1 self-stretch">
      <CardHeader className="gap-0 p-0">
        <CardTitle className="min-w-0">
          <span className="block truncate font-display text-[15px] leading-tight font-normal tracking-[.01em]" title={location.location_name}>{location.location_name}</span>
        </CardTitle>
        <CardDescription className="truncate text-xs" title={address}>{address}</CardDescription>
      </CardHeader>
      {summary && <p className="truncate text-[11px] font-semibold">{summary}</p>}
      {(distance || location.district) && <CardContent className="min-w-0 p-0">
        {/* One meta line keeps the card short; distance leads when searching nearby. */}
        <p className="truncate text-[11px] text-muted-foreground" title={location.district ?? undefined}>
          {distance && <span className="font-semibold text-foreground">{distance}</span>}
          {distance && location.district && ' · '}
          {location.district}
        </p>
      </CardContent>}
    </div>
    {/* Sits above the card-wide select button, so it toggles without opening details. */}
    {compare && <div className="location-card-compare"><CompareToggle {...compare} name={location.location_name} compact /></div>}
  </Card>
}
