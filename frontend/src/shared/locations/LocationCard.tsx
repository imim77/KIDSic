import { Building2 } from 'lucide-react'
import { Button } from '../ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import type { LocationFeature } from './types'

interface LocationCardProps {
  feature: LocationFeature
  selected: boolean
  onSelect: (id: string) => void
}

// LocationCard selects a map result from its compact name and address summary.
export function LocationCard({ feature, selected, onSelect }: LocationCardProps) {
  const location = feature.properties
  const address = location.address ?? 'Adresa nije poznata'

  return <Card className="location-card flex-row items-center gap-3 rounded-2xl p-3" data-selected={selected} role="article">
    <div className="location-thumbnail bg-muted text-muted-foreground" aria-hidden="true">
      <Building2 />
    </div>
    <div className="flex min-w-0 flex-1 flex-col justify-center gap-2 self-stretch">
      <CardHeader className="gap-0 p-0">
        <CardTitle className="min-w-0">
          <Button type="button" variant="ghost" size="sm" className="h-6 w-full min-w-0 justify-start px-0" aria-label={`${location.location_name} ${address}`} aria-pressed={selected} onClick={() => onSelect(feature.id)}>
            <span className="truncate" title={location.location_name}>{location.location_name}</span>
          </Button>
        </CardTitle>
        <CardDescription className="truncate" title={address}>{address}</CardDescription>
      </CardHeader>
      {location.district && <CardContent className="min-w-0 p-0">
        <p className="truncate text-xs text-muted-foreground" title={location.district}>{location.district}</p>
      </CardContent>}
    </div>
  </Card>
}
