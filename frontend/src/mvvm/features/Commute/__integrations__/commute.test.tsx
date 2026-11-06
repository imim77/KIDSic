import type { ReactNode } from 'react'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { CommuteView } from '@/mvvm/features/Commute/components/CommuteView'
import { McpLocationApp } from '@/mvvm/features/Locations/screens/McpLocation/McpLocationApp'
import { decodePolyline } from '@/mvvm/features/Locations/components/map/polyline'
import type { MapRoute } from '@/mvvm/features/Locations/components/map/RouteLayer'
import type { LocationCollection } from '@/mvvm/features/Locations/types'
import { parseCommuteResult } from '@/mvvm/features/Commute/utils/commute-result'
import { commuteResult } from '@test-support/commute-fixtures'
import { collection, facility } from '@test-support/fixtures'

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
const drawn = vi.hoisted(() => new Set<unknown>())
vi.mock('@/mvvm/features/Locations/components/map/KindergartenMap', () => ({KindergartenMap:({route,collection,onSelect,overlay}: {
  route?:MapRoute;collection?:LocationCollection;onSelect?:(id:string)=>void;overlay?:(ready:boolean)=>ReactNode
}) => { if (route) drawn.add(route); return <div aria-label="Zajednička karta">
  <output aria-label="Odabrana geometrija">{route?.legs.map(leg=>leg.geometry).join(',')}</output>
  <output aria-label="Broj oznaka">{collection?.features.length ?? 0}</output>
  {collection?.features.map(feature=><button key={feature.id} onClick={()=>onSelect?.(feature.id)}>Oznaka {feature.id}</button>)}
  {overlay?.(true)}
</div> }}))

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
  // Choosing the shown option again hands the map a new route, so it redraws.
  const routes=drawn.size
  fireEvent.click(screen.getByRole('button',{name:'Oznaka id2'}))
  expect(drawn.size).toBe(routes+1)
  fireEvent.click(screen.getByRole('button',{name:'Vrtić 2 Test 2'}))
  // Details open on the route tab; the other tab shows the city-search details.
  expect(screen.getByRole('tab',{name:'Put'})).toHaveAttribute('aria-selected','true')
  expect(screen.getByRole('tabpanel')).toHaveTextContent('Predaja u vrtiću')
  expect(screen.getByRole('tabpanel')).not.toHaveTextContent('Uspoređeno')
  // Arrows step through the ranked options and wrap around, keeping focus.
  const next=screen.getByRole('button',{name:'Sljedeća opcija'})
  next.focus()
  fireEvent.click(next)
  expect(screen.getByRole('heading',{name:'Vrtić 3'})).toBeInTheDocument()
  expect(screen.getByText('4 / 4')).toBeInTheDocument()
  expect(screen.getByLabelText('Odabrana geometrija')).toHaveTextContent('shape3')
  expect(next).toHaveFocus()
  fireEvent.click(next)
  expect(screen.getByText('Najbolja opcija',{selector:'.route-rank'})).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Prethodna opcija'}))
  fireEvent.click(screen.getByRole('button',{name:'Prethodna opcija'}))
  expect(screen.getByText('Alternativa 2',{selector:'.route-rank'})).toBeInTheDocument()
  expect(select).toHaveBeenLastCalledWith('id2')
  fireEvent.keyDown(screen.getByRole('tab',{name:'Put'}),{key:'ArrowRight'})
  expect(screen.getByRole('tab',{name:'Vrtić'})).toHaveAttribute('aria-selected','true')
  expect(screen.getByRole('tab',{name:'Vrtić'})).toHaveFocus()
  expect(screen.getByRole('region',{name:'Detalji: Vrtić 2'})).toBeVisible()
  // The chosen tab stays when another kindergarten is selected.
  fireEvent.click(screen.getByRole('button',{name:'Oznaka id1'}))
  expect(screen.getByRole('region',{name:'Detalji: Vrtić 1'})).toBeVisible()
  fireEvent.click(screen.getByRole('button',{name:'Oznaka id2'}))
  const route=screen.getByRole('region',{name:'Ruta: Vrtić 2'})
  // The map card only labels the drawn option; the route lives in the details.
  expect(route.querySelector('details')).toBeNull()
  expect(route).toHaveTextContent('Alternativa 2Vrtić 23 / 4')
  fireEvent.click(screen.getByRole('button',{name:'Zatvori detalje'}))
  expect(select).toHaveBeenLastCalledWith(null)
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
  expect(bridge.updateModelContext).toHaveBeenLastCalledWith({content:[{type:'text',text:expect.stringContaining(
    '"feature_id":"id1","kindergarten_id":"institution-id1","city":"Rijeka","name":"Synthetic institution id1","location_name":"Vrtić 1","address":"Test 1","location_role":"facility"'
  )}]})
  fireEvent.click(screen.getByRole('button',{name:/^Vrtić 1 Test 1/}))
  await screen.findByRole('button',{name:'Zatvori detalje'})
  fireEvent.click(screen.getByRole('button',{name:'Sljedeća opcija'}))
  expect(bridge.updateModelContext).toHaveBeenLastCalledWith({content:[{type:'text',text:expect.stringContaining('"feature_id":"id2"')}]})
  fireEvent.click(screen.getByRole('button',{name:'Zatvori detalje'}))
  expect(bridge.updateModelContext).toHaveBeenLastCalledWith({content:[{type:'text',text:expect.stringContaining('Odabir vrtića je uklonjen')}]})
  await act(async()=>call('ontoolinput',{arguments:{city:'Rijeka',home:'Zametska 6',work:'Korzo 16',top_k:4}}))
  expect(screen.getByLabelText('Broj oznaka')).toHaveTextContent('0')
  expect(screen.getByText('Uspoređujem putove kroz vrtiće…')).toBeInTheDocument()
  await act(async()=>call('ontoolresult',{isError:true}))
  expect(screen.getByText(/Izračun nije dostupan/)).toBeInTheDocument()
  await act(async()=>call('ontoolresult',{_meta:{commute:{status:'clarification_required'}}}))
  expect(screen.getByText(/Adresa nije jednoznačna/)).toBeInTheDocument()
  expect(screen.getByLabelText('Odabrana geometrija')).toBeEmptyDOMElement()
  await act(async()=>call('ontoolresult',{_meta:{commute:commuteResult()}}))
  await act(async()=>call('ontoolinput',{arguments:{city:'Rijeka'}}))
  const locations=collection(facility('city'))
  await act(async()=>call('ontoolresult',{structuredContent:{city:'Rijeka',metadata:locations.metadata},_meta:{locations}}))
  expect(screen.getByRole('button',{name:/Synthetic facility city/})).toBeVisible()
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


it('accepts Zagreb routes and rejects mixed-city points and facilities', () => {
  const result = commuteResult('Zagreb')
  expect(parseCommuteResult(result).city).toBe('Zagreb')
  render(<CommuteView result={parseCommuteResult(result)} />)
  expect(screen.getByLabelText('Broj oznaka')).toHaveTextContent('4')
  expect(screen.getByLabelText('Odabrana geometrija')).toHaveTextContent('shape0')
  expect(() => parseCommuteResult({...result, city: 'Rijeka'})).toThrow()
  expect(() => parseCommuteResult({...result, home: {lat: 45.33, lon: 14.42}})).toThrow()
  result.locations.features[0].properties.city = 'Rijeka'
  expect(() => parseCommuteResult(result)).toThrow()
})


it('accepts Šibenik routes and rejects points from the other routing cities', () => {
  const result = commuteResult('Šibenik')
  expect(parseCommuteResult(result).city).toBe('Šibenik')
  render(<CommuteView result={parseCommuteResult(result)} />)
  expect(screen.getByLabelText('Broj oznaka')).toHaveTextContent('4')
  expect(() => parseCommuteResult({...result, city: 'Zagreb'})).toThrow()
  expect(() => parseCommuteResult({...result, work: {lat: 45.33, lon: 14.42}})).toThrow()
  result.locations.features[0].properties.city = 'Rijeka'
  expect(() => parseCommuteResult(result)).toThrow()
})
