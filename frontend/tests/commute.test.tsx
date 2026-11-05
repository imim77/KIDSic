import { act, fireEvent, render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { CommuteView } from '../src/views/commute/CommuteView'
import { McpCommuteApp } from '../src/views/commute/McpCommuteApp'
import { decodePolyline } from '../src/views/commute/polyline'
import { parseCommuteResult, type CommuteResult } from '../src/views/commute/types'

const bridge = vi.hoisted(() => ({ current: null as Record<string, unknown> | null,
  updateModelContext: vi.fn().mockResolvedValue({}), connect:vi.fn().mockResolvedValue({}), close:vi.fn() }))
vi.mock('@modelcontextprotocol/ext-apps', () => ({App: class {
  constructor() {bridge.current=this as unknown as Record<string, unknown>}
  connect=bridge.connect
  close=bridge.close
  updateModelContext=bridge.updateModelContext
}}))
vi.mock('../src/views/commute/CommuteMap', () => ({default:({geometries}:{geometries:string[]}) => <div aria-label="Odabrana geometrija">{geometries.join(',')}</div>}))

function result(): CommuteResult {
  const departure='2026-11-05T07:00:00+01:00'
  const leg={mode:'BUS',departure,arrival:'2026-11-05T07:20:00+01:00',from_name:'Origin',to_name:'Destination',line:'23',geometry:'shape'}
  return {status:'ok',city:'Rijeka',home:{lat:45.33,lon:14.41},work:{lat:45.33,lon:14.44},departure,
    mode:'TRANSIT',dropoff_minutes:10,searched:10,reachable:8,without_route:2,excluded:3,
    notice:'Rang prema dolasku, bez potvrde mjesta.',sources:{service_start:'2026-10-09',service_end:'2026-11-08',gtfs_url:'https://example.invalid/gtfs'},
    results:[0,1,2,3].map(i => ({facility_id:`id${i}`,name:`Vrtić ${i}`,address:`Test ${i}`,point:{lat:45.33,lon:14.42},
      status:'ok',arrival:'2026-11-05T07:35:00+01:00',elapsed_seconds:2100+i*60,extra_seconds:600+i*60,transfers:0,
      journeys:[{departure,arrival:leg.arrival,legs:[{...leg,geometry:`shape${i}`}]},
        {departure:'2026-11-05T07:30:00+01:00',arrival:'2026-11-05T07:35:00+01:00',legs:[{...leg,geometry:null}]}]}))}
}

it('shows the best plus three alternatives and changes only the selected map route', () => {
  const select=vi.fn()
  render(<CommuteView result={result()} onSelect={select}/>)
  expect(screen.getByText('NAJBOLJA OPCIJA')).toBeInTheDocument()
  expect(screen.getByText('ALTERNATIVA 3')).toBeInTheDocument()
  expect(screen.getByLabelText('Odabrana geometrija')).toHaveTextContent('shape0')
  fireEvent.click(screen.getByRole('button',{name:'Prikaži rutu: Vrtić 2'}))
  expect(screen.getByLabelText('Odabrana geometrija')).toHaveTextContent('shape2')
  expect(select).toHaveBeenCalledWith('id2')
  expect(screen.getByText('Uspoređeno 10 objekata · dostupna ruta za 8 · bez rute 2 · izvan mapirane pokrivenosti 3.')).toBeInTheDocument()
})

it('rejects malformed or unsorted routes before putting them on the map', () => {
  expect(parseCommuteResult(result()).results).toHaveLength(4)
  const invalid=result(); invalid.results[0].point.lat=Infinity
  expect(()=>parseCommuteResult(invalid)).toThrow()
  const unsorted=result(); unsorted.results.reverse()
  expect(()=>parseCommuteResult(unsorted)).toThrow()
  expect(()=>parseCommuteResult({...result(),reachable:3})).toThrow()
})

it('receives host results, updates selected context and clears old routes on new input', async () => {
  render(<McpCommuteApp/>)
  const call=(name:string,payload:unknown) => (bridge.current?.[name] as (p:unknown)=>void)(payload)
  await act(async()=>call('ontoolresult',{_meta:{commute:result()}}))
  fireEvent.click(screen.getByRole('button',{name:'Prikaži rutu: Vrtić 1'}))
  expect(bridge.updateModelContext).toHaveBeenCalled()
  await act(async()=>call('ontoolinput',{}))
  expect(screen.queryByText('NAJBOLJA OPCIJA')).not.toBeInTheDocument()
  expect(screen.getByText('Uspoređujem putove kroz riječke vrtiće…')).toBeInTheDocument()
  await act(async()=>call('ontoolresult',{_meta:{commute:{status:'clarification_required'}}}))
  expect(screen.getByText(/Adresa nije jednoznačna/)).toBeInTheDocument()
  expect(screen.queryByLabelText('Odabrana geometrija')).not.toBeInTheDocument()
})

it('decodes route geometry and rejects truncated polylines', () => {
  expect(decodePolyline('_p~iF~ps|U_ulLnnqC_mqNvxq`@')).toEqual([[38.5,-120.2],[40.7,-120.95],[43.252,-126.453]])
  expect(() => decodePolyline('_')).toThrow('Invalid geometry')
})
