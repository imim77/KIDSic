import type { ReactNode } from 'react'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { CommuteView } from '../src/views/commute/CommuteView'
import { McpLocationApp } from '../src/views/mcp/McpLocationApp'
import { decodePolyline } from '../src/shared/map/polyline'
import type { MapRoute } from '../src/shared/map/RouteLayer'
import type { LocationCollection } from '../src/shared/locations/types'
import { parseCommuteResult } from '../src/views/commute/types'
import { commuteResult } from './commuteFixtures'
import { collection, facility } from './fixtures'

const bridge = vi.hoisted(() => ({ current: null as Record<string, unknown> | null,
  updateModelContext: vi.fn().mockResolvedValue({}), connect:vi.fn().mockResolvedValue({}), close:vi.fn(),
  requestDisplayMode:vi.fn(async({mode})=>({mode})) }))
vi.mock('@modelcontextprotocol/ext-apps', () => ({App: class {
  constructor() {bridge.current=this as unknown as Record<string, unknown>}
  connect=bridge.connect
  close=bridge.close
  updateModelContext=bridge.updateModelContext
  requestDisplayMode=bridge.requestDisplayMode
  getHostContext=()=>({displayMode:'inline',availableDisplayModes:['inline','fullscreen']})
}}))
vi.mock('../src/shared/map/KindergartenMap', () => ({KindergartenMap:({route,collection,onSelect,overlay}: {
  route?:MapRoute;collection?:LocationCollection;onSelect?:(id:string)=>void;overlay?:(ready:boolean)=>ReactNode
}) => <div aria-label="Zajednička karta">
  <output aria-label="Odabrana geometrija">{route?.legs.map(leg=>leg.geometry).join(',')}</output>
  <output aria-label="Broj oznaka">{collection?.features.length ?? 0}</output>
  {collection?.features.map(feature=><button key={feature.id} onClick={()=>onSelect?.(feature.id)}>Oznaka {feature.id}</button>)}
  {overlay?.(true)}
</div>}))

beforeEach(()=> {Element.prototype.scrollTo=vi.fn()})
afterEach(()=> {Reflect.deleteProperty(Element.prototype,'scrollTo')})

it('uses the city explorer and ranked cards, with only the requested options and selected route', () => {
  const select=vi.fn()
  const {container}=render(<CommuteView result={commuteResult()} onSelect={select}/>)
  expect(container.querySelector('.kindergarten-explorer')).toBeInTheDocument()
  expect(screen.getByLabelText('Broj oznaka')).toHaveTextContent('4')
  expect(screen.getByText(/^Najbolja opcija ·/)).toBeInTheDocument()
  expect(screen.getByText(/^Alternativa 3 ·/)).toBeInTheDocument()
  expect(screen.getByLabelText('Odabrana geometrija')).toHaveTextContent('shape0')
  fireEvent.click(screen.getByRole('button',{name:'Oznaka id2'}))
  expect(screen.getByLabelText('Odabrana geometrija')).toHaveTextContent('shape2')
  expect(select).toHaveBeenCalledWith('id2')
  fireEvent.click(screen.getByRole('button',{name:'Vrtić 2 Test 2'}))
  // Details open on the route tab; the other tab shows the city-search details.
  expect(screen.getByRole('tab',{name:'Put'})).toHaveAttribute('aria-selected','true')
  expect(screen.getByRole('tabpanel')).toHaveTextContent('Predaja u vrtiću')
  expect(screen.getByRole('tabpanel')).not.toHaveTextContent('Uspoređeno')
  fireEvent.keyDown(screen.getByRole('tab',{name:'Put'}),{key:'ArrowRight'})
  expect(screen.getByRole('tab',{name:'Vrtić'})).toHaveAttribute('aria-selected','true')
  expect(screen.getByRole('tab',{name:'Vrtić'})).toHaveFocus()
  expect(screen.getByRole('region',{name:'Detalji: Vrtić 2'})).toBeVisible()
  // The chosen tab stays when another kindergarten is selected.
  fireEvent.click(screen.getByRole('button',{name:'Oznaka id1'}))
  expect(screen.getByRole('region',{name:'Detalji: Vrtić 1'})).toBeVisible()
  fireEvent.click(screen.getByRole('button',{name:'Oznaka id2'}))
  const route=screen.getByRole('region',{name:'Ruta: Vrtić 2'})
  expect(route.querySelector('details')).not.toHaveAttribute('open')
  fireEvent.click(screen.getByText('Vrtić 2',{selector:'.route-summary-name'}))
  expect(route.querySelector('details')).toHaveAttribute('open')
  expect(screen.getByText(/^Uspoređeno 10, s rutom 8\./)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Zatvori detalje'}))
  expect(screen.queryByRole('region',{name:'Vrtić na putu: Vrtić 2'})).not.toBeInTheDocument()
})

it('validates variable top_k and rejects extra, unsorted, or mismatched map results', () => {
  expect(parseCommuteResult(commuteResult()).results).toHaveLength(4)
  const two=commuteResult()
  two.top_k=2;two.results=two.results.slice(0,2);two.locations.features=two.locations.features.slice(0,2)
  two.locations.metadata.total=2;two.locations.metadata.mapped=2
  expect(parseCommuteResult(two).results).toHaveLength(2)
  expect(()=>parseCommuteResult({...commuteResult(),top_k:2})).toThrow()
  expect(()=>parseCommuteResult({...two,locations:commuteResult().locations})).toThrow()
  const invalid=commuteResult(); invalid.results[0].point.lat=Infinity
  expect(()=>parseCommuteResult(invalid)).toThrow()
  const unsorted=commuteResult(); unsorted.results.reverse()
  expect(()=>parseCommuteResult(unsorted)).toThrow()
  expect(()=>parseCommuteResult({...commuteResult(),reachable:3})).toThrow()
})

it('receives both tools through one bridge and clears old routes on new input, errors and clarification', async () => {
  render(<McpLocationApp/>)
  const call=(name:string,payload:unknown) => (bridge.current?.[name] as (p:unknown)=>void)(payload)
  await act(async()=>call('ontoolresult',{_meta:{commute:commuteResult()}}))
  fireEvent.click(screen.getByRole('button',{name:'Oznaka id1'}))
  expect(bridge.updateModelContext).toHaveBeenCalled()
  await act(async()=>call('ontoolinput',{arguments:{city:'Rijeka',home:'Zametska 6',work:'Korzo 16',top_k:4}}))
  expect(screen.getByLabelText('Broj oznaka')).toHaveTextContent('0')
  expect(screen.getByText('Uspoređujem putove kroz riječke vrtiće…')).toBeInTheDocument()
  await act(async()=>call('ontoolresult',{isError:true}))
  expect(screen.getByText(/Izračun nije dostupan/)).toBeInTheDocument()
  await act(async()=>call('ontoolresult',{_meta:{commute:{status:'clarification_required'}}}))
  expect(screen.getByText(/Adresa nije jednoznačna/)).toBeInTheDocument()
  expect(screen.getByLabelText('Odabrana geometrija')).toBeEmptyDOMElement()
  await act(async()=>call('ontoolresult',{_meta:{commute:commuteResult()}}))
  await act(async()=>call('ontoolinput',{arguments:{city:'Rijeka'}}))
  const locations=collection(facility('city'))
  await act(async()=>call('ontoolresult',{structuredContent:{city:'Rijeka',metadata:locations.metadata},_meta:{locations}}))
  expect(screen.getByRole('button',{name:/^Synthetic facility city/})).toBeVisible()
  expect(screen.getByLabelText('Odabrana geometrija')).toBeEmptyDOMElement()
})

it('shows an empty map without inventing options when there is no route', () => {
  const empty=commuteResult()
  empty.status='no_route';empty.results=[];empty.reachable=0;empty.without_route=empty.searched;empty.locations=collection()
  render(<CommuteView result={parseCommuteResult(empty)}/>)
  expect(screen.getByLabelText('Broj oznaka')).toHaveTextContent('0')
  expect(screen.getByText(/Nema dostupnog puta/)).toBeVisible()
  expect(screen.getByLabelText('Odabrana geometrija')).toBeEmptyDOMElement()
})

it('decodes route geometry and rejects truncated polylines', () => {
  expect(decodePolyline('_p~iF~ps|U_ulLnnqC_mqNvxq`@')).toEqual([[38.5,-120.2],[40.7,-120.95],[43.252,-126.453]])
  expect(() => decodePolyline('_')).toThrow('Invalid geometry')
})
