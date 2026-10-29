import assert from 'node:assert/strict'

export const IDS=['SKU29_BROWSER_DESKTOP_REAL_AUTH_PAIR_FIFO_RECOVERY_INVERSE','SKU29_BROWSER_MOBILE390_REAL_AUTH_PAIR_FIFO_GUARDS_INVERSE']
export function cents(value){
 const match=/^(-?)(\d+)(?:\.(\d+))?$/.exec(String(value));assert.ok(match,'INVALID_EXACT_MONEY')
 const[,sign,whole,fraction='']=match;assert.match(fraction.slice(2),/^0*$/,'FRACTIONAL_CENT_NOT_ALLOWED')
 return(BigInt(whole)*100n+BigInt(fraction.slice(0,2).padEnd(2,'0')))*(sign? -1n:1n)
}
export function equalCensus(before,after){
 assert.equal(before.catalog_groups,22);assert.equal(after.catalog_groups,22)
 assert.equal(after.catalog_sha256,before.catalog_sha256,'CURRENT_ALL22_CATALOG_CHANGED')
 assert.deepEqual(after.data_and_sequences,before.data_and_sequences,'CURRENT_ROWS_OR_SEQUENCES_CHANGED')
 assert.deepEqual(before.dropped_catalog_fields,[]);assert.deepEqual(after.dropped_catalog_fields,[])
 assert.deepEqual(before.dropped_data_or_sequence_keys,[]);assert.deepEqual(after.dropped_data_or_sequence_keys,[])
}
export function pairOnly(before,after,source,target,eventDelta){
 assert.equal(after.census.catalog_sha256,before.census.catalog_sha256,'PAIR_CHANGED_CURRENT_CATALOG')
 for(const state of[before,after]){assert.equal(state.census.catalog_groups,22);assert.deepEqual(state.census.dropped_catalog_fields,[]);assert.deepEqual(state.census.dropped_data_or_sequence_keys,[])}
 const a=before.census.data_and_sequences,b=after.census.data_and_sequences
 assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),'PAIR_CHANGED_CENSUS_MEMBERS')
 const allowed=['cp7_sku_conversion.pairs_v1','cp7_sku_conversion.pair_events_v1']
 const changed=Object.keys(a).filter(key=>JSON.stringify(a[key])!==JSON.stringify(b[key]))
 assert.ok(changed.every(key=>allowed.includes(key)),'PAIR_CHANGED_STOCK_MONEY_OR_SEQUENCE:'+changed.join(','))
 assert.deepEqual(after.ledgers,before.ledgers);assert.deepEqual(after.accounts,before.accounts)
 assert.equal(after.pair_event_count-before.pair_event_count,eventDelta)
 assert.deepEqual(after.pairs,target?[[source,target].sort()]:[])
 return changed
}
export function previewOracle(value,fixture){
 assert.equal(value.source_product_id,fixture.source);assert.equal(value.target_product_id,fixture.target);assert.equal(value.location_id,fixture.location)
 assert.equal(value.qty_pcs,4)
 assert.deepEqual(value.source_stock,{physical:10,reserved:1,available:9})
 assert.deepEqual(value.source_after,{physical:6,reserved:1,available:5})
 assert.deepEqual(value.target_stock,{physical:4,reserved:0,available:4})
 assert.deepEqual(value.target_after,{physical:8,reserved:0,available:8})
 assert.deepEqual(value.allocations.map(a=>[a.source_lot_id,a.qty_pcs]),fixture.lots.map(id=>[id,2]))
 assert.deepEqual(value.allocations.map(a=>cents(a.source_value)),[2002n,4004n])
 assert.equal(cents(value.cost.source_value),6006n)
 assert.equal(new Date(value.physical_at).getTime(),new Date(fixture.physical_iso).getTime())
}
export function postedOracle(state,fixture,result){
 assert.deepEqual(state.source,{physical:6,reserved:1,available:5});assert.deepEqual(state.target,{physical:8,reserved:0,available:8})
 assert.deepEqual(state.accounts,fixture.baseline_accounts)
 assert.equal(state.groups.length,1);assert.equal(state.groups[0].id,result.conversion_id);assert.equal(state.members.length,2)
 assert.deepEqual(state.members.map(m=>[m.source_lot_id,m.qty_pcs,cents(m.unit_hpp),cents(m.destination_value)]),
  [[fixture.lots[0],2,1001n,2002n],[fixture.lots[1],2,2002n,4004n]])
 assert.ok(state.members.every(m=>m.status==='POSTED'&&m.group_id===result.conversion_id))
 assert.equal(state.members.reduce((value,row)=>value+cents(row.destination_value),0n),6006n)
 assert.equal(result.conversion_ids.length,2);assert.equal(new Set(result.conversion_ids).size,2)
 assert.deepEqual(new Set(state.members.map(m=>m.conversion_id)),new Set(result.conversion_ids))
}
export function observeConsole(page){
 const errors=[],pageErrors=[]
 const consoleListener=message=>{if(message.type()==='error')errors.push({text:message.text(),location:message.location()})}
 const errorListener=error=>pageErrors.push(String(error.message||error))
 page.on('console',consoleListener);page.on('pageerror',errorListener)
 return{errors,pageErrors,stop(){page.off('console',consoleListener);page.off('pageerror',errorListener)}}
}
export function requireConsoleEvidence(capture,expectedNetwork){
 const unused=expectedNetwork.map(x=>({...x})),expected=[],unexpected=[]
 for(const error of capture.errors){
  const i=unused.findIndex(item=>item.url===error.location.url&&item.text===error.text)
  if(i<0)unexpected.push(error);else expected.push({...error,reason:unused.splice(i,1)[0].reason})
 }
 assert.deepEqual(capture.pageErrors,[],'UNEXPECTED_BROWSER_PAGE_ERROR');assert.deepEqual(unexpected,[],'UNEXPECTED_BROWSER_CONSOLE_ERROR')
 return{observed:structuredClone(capture.errors),expected_network_errors:expected,unexpected_errors:unexpected,page_errors:structuredClone(capture.pageErrors)}
}

// Measure normal text on actual opaque feature panels. Disabled controls are
// retained as an explicit WCAG exemption; no gradient/opacity is guessed.
export async function readable(panel){
 const observed=await panel.evaluate(root=>{
  const rgb=value=>value.match(/[\d.]+/g).map(Number),lum=color=>color.slice(0,3).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((sum,x,i)=>sum+x*[.2126,.7152,.0722][i],0),rows=[],exempt=[]
  for(const el of[root,...root.querySelectorAll('*')]){
   const style=getComputedStyle(el),text=[...el.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent).join(' ').trim()
   const label=text||((el instanceof HTMLInputElement||el instanceof HTMLTextAreaElement)?el.value:'')
   if(!label||!el.getClientRects().length||style.visibility!=='visible'||el.tagName==='OPTION')continue
   if(el.closest(':disabled,[aria-disabled="true"]')){exempt.push({label:label.slice(0,100),reason:'INACTIVE_CONTROL_WCAG_CONTRAST_EXEMPTION'});continue}
   const layers=[];let bg=null
   for(let p=el;p;p=p.parentElement){const s=getComputedStyle(p),c=rgb(s.backgroundColor)
    if(s.backgroundImage!=='none'||s.opacity!=='1')throw Error('UNMEASURED_SKU_TEXT_SURFACE:'+JSON.stringify({label:label.slice(0,100),tag:p.tagName,classes:p.className,backgroundImage:s.backgroundImage,opacity:s.opacity}))
    if(c.length===3||c[3]===1){bg=c.slice(0,3);break}layers.push(c)
   }
   if(!bg)throw Error('MISSING_SKU_TEXT_SURFACE')
   for(const color of layers.reverse())bg=bg.map((x,i)=>color[i]*(color[3]??1)+x*(1-(color[3]??1)))
   const fg=rgb(style.color),visible=bg.map((x,i)=>fg[i]*(fg[3]??1)+x*(1-(fg[3]??1))),a=lum(visible),b=lum(bg)
   rows.push({label:label.slice(0,100),ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05),foreground:style.color,background:bg})
  }return{rows,exempt}
 })
 assert.ok(observed.rows.length>0,'NO_VISIBLE_SKU_TEXT_MEASURED')
 assert.deepEqual(observed.rows.filter(row=>row.ratio<4.5),[],'SKU_TEXT_CONTRAST_BELOW_4_5')
 return observed
}
