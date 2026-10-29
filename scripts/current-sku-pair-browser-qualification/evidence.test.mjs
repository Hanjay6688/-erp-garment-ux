import assert from 'node:assert/strict'
import {EventEmitter} from 'node:events'
import {test} from 'node:test'
import {cents,equalCensus,pairOnly,previewOracle,postedOracle,observeConsole,requireConsoleEvidence} from './evidence.mjs'

const census=()=>({catalog_groups:22,catalog_sha256:'full22',data_and_sequences:{'erp.fg_stock_movements':[1,'stock'],'sequence:erp.ref':[9,true],
 'cp7_sku_conversion.pairs_v1':[0,'empty'],'cp7_sku_conversion.pair_events_v1':[0,'empty']},dropped_catalog_fields:[],dropped_data_or_sequence_keys:[]})
const pairState=()=>({census:census(),ledgers:{stock:'original'},accounts:{FG:'1.00'},pair_event_count:0,pairs:[]})
test('money remains integer cents and fractional cents cannot be silently rounded',()=>{
 assert.equal(cents('9007199254740993.06'),900719925474099306n);assert.equal(cents('-60.0600'),-6006n)
 assert.throws(()=>cents('60.061'),/FRACTIONAL_CENT/);assert.throws(()=>cents('NaN'),/INVALID_EXACT_MONEY/)
})
test('no-effect evidence rejects omitted data, changed sequence, catalog or partial projection',()=>{
 const original=census();equalCensus(original,structuredClone(original))
 for(const change of[value=>delete value.data_and_sequences['erp.fg_stock_movements'],value=>value.data_and_sequences['sequence:erp.ref'][0]++,
  value=>value.catalog_sha256='changed',value=>value.dropped_catalog_fields=['triggers']]){
  const changed=structuredClone(original);change(changed);assert.throws(()=>equalCensus(original,changed))
 }
})
test('pair mutation may change only the exact pair/event rows while stock and sequence remain exact',()=>{
 const before=pairState(),after=structuredClone(before);after.census.data_and_sequences['cp7_sku_conversion.pairs_v1']=[1,'pair'];after.census.data_and_sequences['cp7_sku_conversion.pair_events_v1']=[1,'event'];after.pair_event_count=1;after.pairs=[['a','b']]
 pairOnly(before,after,'b','a',1)
 for(const change of[value=>value.census.data_and_sequences['erp.fg_stock_movements'][1]='changed',value=>value.census.data_and_sequences['sequence:erp.ref'][0]++,
  value=>value.pairs.push(['a','b']),value=>value.ledgers.stock='changed']){
  const wrong=structuredClone(after);change(wrong);assert.throws(()=>pairOnly(before,wrong,'a','b',1))
 }
})
const fixture={source:'s',target:'t',location:'l',lots:['first','second'],physical_iso:'2026-10-29T08:00:00+07:00',baseline_accounts:{FG:'170.17'}}
const preview=()=>({source_product_id:'s',target_product_id:'t',location_id:'l',qty_pcs:4,physical_at:fixture.physical_iso,
 source_stock:{physical:10,reserved:1,available:9},source_after:{physical:6,reserved:1,available:5},target_stock:{physical:4,reserved:0,available:4},target_after:{physical:8,reserved:0,available:8},
 allocations:[{source_lot_id:'first',qty_pcs:2,source_value:'20.02'},{source_lot_id:'second',qty_pcs:2,source_value:'40.04'}],cost:{source_value:'60.06'}})
test('independent preview gold rejects wrong destination, consumed reservation, averaged value and reversed chronology',()=>{
 previewOracle(preview(),fixture)
 for(const change of[value=>value.target_product_id='hidden',value=>value.source_after.reserved=0,value=>value.allocations.reverse(),
  value=>value.allocations[0].source_value='30.03',value=>value.cost.source_value='60.05']){
  const wrong=preview();change(wrong);assert.throws(()=>previewOracle(wrong,fixture))
 }
})
test('posted proof requires one whole group with the exact two source lineages and values',()=>{
 const state={source:{physical:6,reserved:1,available:5},target:{physical:8,reserved:0,available:8},accounts:fixture.baseline_accounts,groups:[{id:'g'}],members:[
  {conversion_id:'c1',group_id:'g',source_lot_id:'first',qty_pcs:2,unit_hpp:'10.01',destination_value:'20.02',status:'POSTED'},
  {conversion_id:'c2',group_id:'g',source_lot_id:'second',qty_pcs:2,unit_hpp:'20.02',destination_value:'40.04',status:'POSTED'}]}
 const result={conversion_id:'g',conversion_ids:['c1','c2']};postedOracle(state,fixture,result)
 for(const change of[value=>value.groups.push({id:'duplicate'}),value=>value.members[1].source_lot_id='first',
  value=>value.members[0].destination_value='30.03',value=>value.members[0].status='REVERSED']){
  const wrong=structuredClone(state);change(wrong);assert.throws(()=>postedOracle(wrong,fixture,result))
 }
})
test('console evidence retains exact anticipated loss, rejects application errors and extra network events',()=>{
 const page=new EventEmitter(),capture=observeConsole(page),url='http://127.0.0.1:54321/rest/v1/rpc/actual',text='Failed to load resource: net::ERR_FAILED'
 const message=(value=text,at=url)=>({type:()=> 'error',text:()=>value,location:()=>({url:at})})
 page.emit('console',message());const expected=[{url,text,reason:'real successful reply deliberately lost'}]
 assert.equal(requireConsoleEvidence(capture,expected).observed.length,1)
 page.emit('console',message());assert.throws(()=>requireConsoleEvidence(capture,expected),/UNEXPECTED_BROWSER_CONSOLE_ERROR/)
 capture.stop();assert.equal(page.listenerCount('console'),0);assert.equal(page.listenerCount('pageerror'),0)
 assert.throws(()=>requireConsoleEvidence({errors:[],pageErrors:['application exception']},[]),/UNEXPECTED_BROWSER_PAGE_ERROR/)
 assert.throws(()=>requireConsoleEvidence({errors:[{text,location:{url:url+'/other'}}],pageErrors:[]},expected),/UNEXPECTED_BROWSER_CONSOLE_ERROR/)
})
