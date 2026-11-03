import { ArrowUpRight, Building2 } from 'lucide-react'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../ui/card'
import { providerLabels } from './types'
import type { LocationFeature } from './types'

interface LocationCardProps {
  feature: LocationFeature
  selected: boolean
  detailsOpen: boolean
  onSelect: (id: string) => void
  onDetails: (feature: LocationFeature, trigger: HTMLButtonElement) => void
}

// LocationCard keeps selection and source details as separate actions.
export function LocationCard({ feature, selected, detailsOpen, onSelect, onDetails }: LocationCardProps) {
  const location = feature.properties
  const address = location.address ?? 'Adresa nije poznata'
  const coordinateNote = location.location_role === 'seat'
    ? 'Sjedište ustanove — lokacija pružanja usluge nije potvrđena'
    : 'Koordinate nisu poznate — nema prikaza na karti'

  return <Card className="location-card flex-row items-center gap-3 rounded-2xl p-3" data-selected={selected} role="article">
    <div className="location-thumbnail bg-muted text-muted-foreground" aria-hidden="true">
      <Building2 />
    </div>
    <div className="flex min-w-0 flex-1 flex-col justify-between self-stretch">
      <CardHeader className="gap-0 p-0">
        <CardTitle className="min-w-0">
          <Button type="button" variant="ghost" size="sm" className="h-6 w-full min-w-0 justify-start px-0" aria-label={`${location.location_name} ${address}`} aria-pressed={selected} onClick={() => onSelect(feature.id)}>
            <span className="truncate" title={location.location_name}>{location.location_name}</span>
          </Button>
        </CardTitle>
        <CardDescription className="truncate" title={address}>{address}</CardDescription>
      </CardHeader>
      <CardContent className="min-w-0 p-0">
        <div className="flex min-w-0 items-center gap-2">
          <Badge variant="secondary" className="max-w-full"><span className="truncate">{providerLabels[location.provider_kind]}</span></Badge>
          {location.district && <span className="truncate text-xs text-muted-foreground" title={location.district}>{location.district}</span>}
        </div>
        {!feature.geometry && <small className="block truncate text-xs text-muted-foreground" title={coordinateNote}>{coordinateNote}</small>}
      </CardContent>
      <CardFooter className="p-0">
        <Button type="button" variant="link" size="xs" className="justify-start px-0" aria-label={`Detalji i izvori: ${location.location_name}`} aria-expanded={detailsOpen} aria-controls={detailsOpen ? `details-${feature.id}` : undefined} onClick={(event) => onDetails(feature, event.currentTarget)}>
          Detalji i izvori <ArrowUpRight data-icon="inline-end" />
        </Button>
      </CardFooter>
    </div>
  </Card>
}
