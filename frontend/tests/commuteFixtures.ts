import type { CommuteResult } from '../src/views/commute/types'
import { collection, facility } from './fixtures'

export function commuteResult(): CommuteResult {
  const departure='2026-11-05T07:00:00+01:00'
  const leg={mode:'BUS',departure,arrival:'2026-11-05T07:20:00+01:00',from_name:'Origin',to_name:'Destination',line:'23',geometry:'shape'}
  return {status:'ok',city:'Rijeka',home:{lat:45.33,lon:14.41},work:{lat:45.33,lon:14.44},departure,
    mode:'TRANSIT',dropoff_minutes:10,top_k:4,
    locations:collection(...[0,1,2,3].map(i => {
      const item=facility(`id${i}`)
      item.geometry={type:'Point',coordinates:[14.42,45.33]}
      Object.assign(item.properties,{city:'Rijeka',location_name:`Vrtić ${i}`,address:`Test ${i}`})
      return item
    })),searched:10,reachable:8,without_route:2,excluded:3,
    notice:'Rang prema dolasku, bez potvrde mjesta.',sources:{service_start:'2026-10-09',service_end:'2026-11-08',gtfs_url:'https://example.invalid/gtfs'},
    results:[0,1,2,3].map(i => ({facility_id:`id${i}`,name:`Vrtić ${i}`,address:`Test ${i}`,point:{lat:45.33,lon:14.42},
      status:'ok',arrival:'2026-11-05T07:35:00+01:00',elapsed_seconds:2100+i*60,extra_seconds:600+i*60,transfers:0,
      journeys:[{departure,arrival:leg.arrival,legs:[{...leg,geometry:`shape${i}`}]},
        {departure:'2026-11-05T07:30:00+01:00',arrival:'2026-11-05T07:35:00+01:00',legs:[{...leg,geometry:null}]}]}))}
}
