import { useEffect, useRef, type MouseEvent } from 'react'
import { Building2, MapPin, X } from 'lucide-react'
import { providerLabels, type LocationFeature } from './types'
import { websiteHref } from './links'
import { SubsidyDetails } from './SubsidyDetails'
import { ProgramDetails } from './ProgramDetails'
import { HistoricalDetails } from './HistoricalDetails'
import { EnrolmentDetails } from './EnrolmentDetails'
import { useEntrance } from '../motion/useEntrance'
import { CompareToggle, type CompareChoice } from './CompareToggle'

interface LocationDetailsProps {
  feature: LocationFeature
  onClose: () => void
  openLink?: (url: string) => void
  compare?: CompareChoice
}


function phoneHref(value: string) {
  const digits = value.replace(/\D/g, '')
  // Multiple published numbers remain readable; do not dial a concatenation.
  return /^\+?[\d\s()./-]+$/.test(value) && digits.length >= 3 && digits.length <= 15
    ? `tel:${value.startsWith('+') ? '+' : ''}${digits}` : undefined
}

// LocationDetails presents published contacts and leaves missing facts unfilled.
export function LocationDetails({ feature, onClose, openLink, compare }: LocationDetailsProps) {
  const location = feature.properties
  const sectionRef = useRef<HTMLElement>(null)
  // Remounted per feature (keyed by id), so each selection replays the entrance.
  useEntrance(sectionRef, [], { selector: '.location-details-hero, .location-details-body > *', limit: 16, container: true })
  useEffect(() => {
    // A card that expanded the frame may have unmounted with keyboard focus.
    if (!document.activeElement || document.activeElement === document.body) sectionRef.current?.focus({ preventScroll: true })
  }, [])
  const website = websiteHref(location.website_url)
  const email = location.email?.trim()
  const phone = location.phone?.trim()
  const emailUrl = email && /^[^\s@,;<>]+@[^\s@,;<>]+\.[^\s@,;<>]+$/.test(email)
    ? `mailto:${encodeURIComponent(email).replace('%40', '@')}` : undefined
  const phoneUrl = phone ? phoneHref(phone) : undefined
  // Sandboxed MCP hosts block plain navigation, so links go through the host.
  const open = (event: MouseEvent<HTMLAnchorElement>) => {
    if (!openLink) return
    event.preventDefault()
    openLink(event.currentTarget.href)
  }
  const place = [location.district, location.city].filter(Boolean).join(', ')

  return <section ref={sectionRef} tabIndex={-1} className="location-details" aria-label={`Detalji: ${location.location_name}`}
    onKeyDown={(event) => { if (event.key === 'Escape' && !event.defaultPrevented) { event.preventDefault(); onClose() } }}>
    <div className="location-details-scroll">
      <div className="location-details-hero">
        <Building2 aria-hidden="true" />
        <button type="button" className="location-details-close" aria-label="Zatvori detalje" onClick={onClose}><X aria-hidden="true" /></button>
      </div>
      <div className="location-details-body">
        <div className="location-details-top">
          <span className="location-details-kind">{providerLabels[location.provider_kind]}</span>
          {compare && <CompareToggle {...compare} name={location.location_name} />}
        </div>
        <h2>{location.location_name}</h2>
        {location.name !== location.location_name && <p className="location-details-institution">Ustanova: {location.name}</p>}
        <p className="location-details-address">
          <MapPin aria-hidden="true" />
          <span>{location.address ?? 'Adresa nije poznata'}{place && `, ${place}`}</span>
        </p>
        {location.location_role === 'seat' && <p className="location-details-note">Ovo je adresa sjedišta ustanove; lokacija objekta nije potvrđena.</p>}
        {!feature.geometry && location.location_role !== 'seat' && <p className="location-details-note">Koordinate nisu poznate, pa objekt nije na karti.</p>}

        {(website || email || phone) && <>
          <h3>Kontakt</h3>
          <dl className="location-details-contacts">
            {website && <><dt>Web</dt><dd><a href={website} target="_blank" rel="noreferrer" onClick={open}>Web stranica vrtića</a></dd></>}
            {email && <><dt>E-mail</dt><dd>{emailUrl ? <a href={emailUrl} onClick={open}>{email}</a> : email}</dd></>}
            {phone && <><dt>Telefon</dt><dd>{phoneUrl ? <a href={phoneUrl} onClick={open}>{phone}</a> : phone}</dd></>}
          </dl>
        </>}

        <EnrolmentDetails rounds={location.enrolment ?? []} openLink={openLink} />
        <ProgramDetails location={location} openLink={openLink} />
        <HistoricalDetails records={location.historical_data ?? []} openLink={openLink} />
        <SubsidyDetails policies={location.subsidy_policies ?? []} openLink={openLink} />

        <h3>O ovom objektu</h3>
        <dl>
          <dt>Vrsta</dt><dd>{providerLabels[location.provider_kind]}</dd>
          <dt>Četvrt</dt><dd>{location.district ?? 'Nije navedena'}</dd>
          <dt>Grad</dt><dd>{location.city}</dd>
        </dl>
        <p className="location-details-note">Dobne skupine, slobodna mjesta i konačnu cijenu za svoju obitelj provjerite izravno kod vrtića.</p>

      </div>
    </div>
  </section>
}
