import { useState } from 'react'
import type { FormEvent } from 'react'
import { initialLocationFilters, providerLabels } from './types'
import type { LocationFilters as Filters, ProviderKind } from './types'

export function LocationFilters({ onChange }: { onChange: (filters: Filters) => void }) {
  const [draft, setDraft] = useState(initialLocationFilters)
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onChange({ ...draft, city: draft.city.trim(), q: draft.q.trim() })
  }
  return <form className="location-filters" onSubmit={submit} aria-label="Filtri imenika">
    <div className="filter-field">
      <label htmlFor="city">Grad ili općina</label>
      <input id="city" name="city" required pattern=".*\S.*" maxLength={100} value={draft.city} onChange={(event) => setDraft({ ...draft, city: event.target.value })} />
    </div>
    <div className="filter-field">
      <label htmlFor="provider">Pružatelj</label>
      <select id="provider" name="provider_kind" value={draft.provider_kind} onChange={(event) => setDraft({ ...draft, provider_kind: event.target.value as ProviderKind | '' })}>
        <option value="">Svi pružatelji</option>
        {Object.entries(providerLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
      </select>
    </div>
    <div className="filter-field search-field">
      <label htmlFor="search">Naziv vrtića ili objekta</label>
      <input id="search" name="q" maxLength={200} placeholder="Npr. Medveščak" value={draft.q} onChange={(event) => setDraft({ ...draft, q: event.target.value })} />
    </div>
    <div className="filter-actions">
      <button className="primary-button" type="submit">Prikaži rezultate</button>
      <button className="reset-button" type="button" onClick={() => { setDraft(initialLocationFilters); onChange(initialLocationFilters) }}>Poništi</button>
    </div>
  </form>
}
