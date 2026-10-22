// @vitest-environment node
import {readFileSync}from'node:fs'
import {execFileSync}from'node:child_process'
import {beforeAll,afterAll,describe,test,expect}from'vitest'
import {openRuntime,jsonArg}from'./f04/runtime.mjs'
// OW-09 (owner D17-16): sort and filter apply to every matching row before the page is cut; count, sums and pages agree.
// The readers are the frozen base (scripts/cp7-src and the CP6 accessory reader) patched by the stage's own counted
// substitutions (scripts/cp7_ow09_lists/native_delta.py) on their installed pg_get_functiondef text, exactly as the
// Native stage does. Old calls are read on the original and the patched definitions side by side and must be equal.
// Deliberate raw reader stubs only (ow09/stubs.sql); actual Native business proof is the stage's qualification cases.
type Json=Record<string,any>
let db:Awaited<ReturnType<typeof openRuntime>>
const sources=['finance/analysis.sql','sales/payments.sql','sales/returns.sql','payroll/note-read.sql','fg/adjustment-read.sql','fg/corrected-ledger.sql','materials/count-read.sql']
const signatures=['cp7_finance.analysis(jsonb)','cp7_sales.cash_workspace(jsonb)','cp7_sales.return_workspace(jsonb)','cp7_payroll.note_workspace(text,jsonb)',
 'cp7_fg.adjust_workspace(jsonb)','cp7_fg.corrected_ledger(jsonb)','cp7_material.count_workspace(jsonb)','erp.get_accessory_issue_workspace_v1(jsonb)']
let originals:Record<string,string>={},patched:Record<string,string>={}
// The last CP6 definition of the accessory note reader (cp6-t3 20bc) and its public wrapper (20ap), as installed.
function accessorySource(){
 const release=readFileSync('supabase/release/cp6-t3/20260925030000_erp_v2_6_20bc_cp6_accessory_service_returns.sql','utf8')
 const start=release.indexOf('create or replace function erp.get_accessory_issue_workspace_v1('),open=release.indexOf('$function$',start),end=release.indexOf('$function$',open+10)+10
 const wrapper=readFileSync('supabase/migrations/20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql','utf8').split('\n').find(l=>l.startsWith('create or replace function public.erp_get_accessory_issue_workspace_v1('))
 if(start<0||!wrapper)throw new Error('accessory reader source not found')
 return release.slice(start,end)+';\n'+wrapper
}
// The stage's own patched() on the captured definitions; no copy of the substitutions lives in this test.
const stagePatch=(input:Record<string,string>)=>JSON.parse(execFileSync('python3',['-B','-c','import json,sys\nfrom cp7_ow09_lists import native_delta as d\nprint(json.dumps(d.patched(json.load(sys.stdin))))'],
 {input:JSON.stringify(input),encoding:'utf8',env:{...process.env,PYTHONPATH:'scripts',PYTHONDONTWRITEBYTECODE:'1'}})) as Record<string,string>
const install=async(definitions:Record<string,string>)=>{for(const sig of signatures)await db.execute(definitions[sig])}
// Reads fn() on the exact original definitions, then puts the patched ones back.
async function original<T>(fn:()=>Promise<T>):Promise<T>{await install(originals);try{return await fn()}finally{await install(patched)}}
// Read times (read_at, captured_at) are the statement time of each call, so they are left out of the comparison.
const timeless=(r:any):any=>Array.isArray(r)?r.map(timeless):r&&typeof r==='object'?Object.fromEntries(Object.entries(r).filter(([k])=>k!=='read_at'&&k!=='captured_at').map(([k,v])=>[k,timeless(v)])):r
// Every page of an old call (through next_offset) on the patched and the original reader: equal apart from read_at.
async function sameOld(read:(offset:number)=>Promise<Json>,page:(r:Json)=>Json){
 const pages=async()=>{const out:Json[]=[];let offset=0;for(;;){const r=await read(offset);out.push(timeless(r));const next=page(r).next_offset;if(next===null||next===undefined)return out;offset=next}}
 const now=await pages(),before=await original(pages);expect(now).toEqual(before);expect(now.length).toBeGreaterThan(1)
 return now.length
}
const id=(prefix:string,i:number)=>`${prefix}000000-0000-4000-8000-${String(i).padStart(12,'0')}`
const lit=(v:string|number|null)=>v===null?'null':typeof v==='number'?String(v):`'${v.replaceAll("'","''")}'`
// Same natural key as the readers: digit runs by value (length-prefixed), text runs lower-cased, compared bytewise (collation C).
const natural=(s:string)=>(s.match(/[0-9]+|[^0-9]+/g)??[]).map(p=>/^[0-9]/.test(p)?(d=>String(d.length).padStart(10,'0')+d)(p.replace(/^0+/,'')):p.toLowerCase()).join('')
const bytewise=(a:string,b:string)=>a<b?-1:a>b?1:0
type Fact={id:string;label:string;status:string;at:number;note:string|null}
// 30 rows plus one row whose label ties row 7 by value (07 = 7); source time (i*7 mod 31) differs from label order.
const facts=(prefix:string,label:string,statuses:string[]):Fact[]=>Array.from({length:31},(_,k)=>{const i=k+1;return{id:id(prefix,i),label:i===31?`${label}-07`:`${label}-${i}`,status:statuses[i%statuses.length],at:(i*7)%31,note:i%5===0?'Needle note':null}})
function expected(rows:Fact[],source:(a:Fact,b:Fact)=>number,order:string,keep:(f:Fact)=>boolean=()=>true){
 const list=rows.filter(keep).sort(source)
 if(order==='SOURCE')return list.map(r=>r.id)
 return list.sort((a,b)=>(order==='LABEL_DESC'?-1:1)*bytewise(natural(a.label),natural(b.label))||source(a,b)).map(r=>r.id)
}
const desc=(a:Fact,b:Fact)=>b.at-a.at||bytewise(a.id,b.id),asc=(a:Fact,b:Fact)=>a.at-b.at||bytewise(a.id,b.id)
// Walks every page through next_offset; each page must report the same total and continue exactly where the last ended.
async function walk(read:(offset:number)=>Promise<Json>,page:(r:Json)=>Json){
 const ids:string[]=[],totals=new Set<string>(),lists:string[]=[];let offset=0,pages=0
 for(;;){const r=await read(offset),p=page(r);pages++;totals.add(p.total);lists.push(JSON.stringify(p.list??null));expect(p.offset).toBe(offset);ids.push(...p.rows.map((x:Json)=>x.id))
  if(p.next_offset===null)break;expect(p.next_offset).toBe(offset+p.rows.length);offset=p.next_offset}
 expect(totals.size).toBe(1);expect(new Set(lists).size).toBe(1)
 return {ids,total:[...totals][0],pages,list:JSON.parse(lists[0])}
}
const call=async(fn:string,query:Json,section?:string)=>(await db.query(`select public.${fn}(${section?`'${section}',`:''}${jsonArg(query)}) r`))[0].r as Json
beforeAll(async()=>{
 db=await openRuntime()
 await db.execute(readFileSync('tests/cp7/families/ow09/stubs.sql','utf8'))
 for(const file of sources)await db.execute(readFileSync(`scripts/cp7-src/${file}`,'utf8'))
 await db.execute(accessorySource())
 for(const sig of signatures)originals[sig]=(await db.query(`select pg_get_functiondef('${sig}'::regprocedure) d`))[0].d as string
 patched=stagePatch(originals)
 expect(Object.keys(patched).sort()).toEqual([...signatures].sort())
 for(const sig of signatures)expect(patched[sig]).not.toBe(originals[sig])
 await install(patched)
 for(const sig of signatures)expect((await db.query(`select pg_get_functiondef('${sig}'::regprocedure) d`))[0].d).toBe(patched[sig])
 expect(()=>stagePatch(patched)).toThrow('OW09_ALREADY_PATCHED')
},120000)
afterAll(async()=>{if(db)await db.close()})

describe('OW-09 whole-result list readers',()=>{
 test('cash ledger: status, search and natural order cover the whole period; count and sums follow the same filter',async()=>{
  const rows=facts('a1','JV',['POSTED','REVERSED','POSTED']),cash='0a000000-0000-4000-8000-000000000001'
  for(const [k,r] of rows.entries())await db.execute(`insert into erp.journal_entries values('${r.id}',${lit(r.label)},${lit(r.note?'NEEDLE_SOURCE':'SALE')},null,null,'${r.status}',date '2026-01-01'+${r.at},date '2026-01-01'+${r.at},timestamptz '2026-01-01 01:00Z'+${r.at}*interval '1 day');
   insert into erp.journal_lines(journal_entry_id,account_id,debit,credit)values('${r.id}','${cash}',${k%2?'0':`${k+1}.25`},${k%2?`${k+1}.10`:'0'})`)
  const base={from:'2026-01-01',to:'2026-01-31',as_of:'2026-01-31',compare_from:'2025-12-31',compare_to:'2025-12-31'}
  const source=(a:Fact,b:Fact)=>asc(a,b),cents=(r:Fact)=>{const k=rows.indexOf(r);return k%2?-((k+1)*100+10):(k+1)*100+25}
  const period=(await call('erp_cp7_get_finance_analysis_v1',base)).cash
  const old=await walk(o=>call('erp_cp7_get_finance_analysis_v1',{...base,offset:o,limit:25}),r=>r.cash.entries)
  expect(old.ids).toEqual(expected(rows,source,'SOURCE'));expect(old.total).toBe('31');expect(old.list).toBeNull()
  expect(await sameOld(o=>call('erp_cp7_get_finance_analysis_v1',{...base,offset:o,limit:10}),r=>r.cash.entries)).toBe(4)
  for(const order of ['SOURCE','LABEL_ASC','LABEL_DESC'])for(const status of [null,'POSTED','REVERSED'])for(const q of ['','needle_source']){
   const keep=(r:Fact)=>(!status||r.status===status)&&(!q||r.note!==null),want=expected(rows,source,order,keep)
   const got=await walk(o=>call('erp_cp7_get_finance_analysis_v1',{...base,offset:o,limit:10,entry_q:q,entry_status:status,entry_order:order}),r=>r.cash.entries)
   expect(got.ids).toEqual(want);expect(got.total).toBe(String(want.length));expect(got.list).toEqual({q,status,order})
   const first=(await call('erp_cp7_get_finance_analysis_v1',{...base,offset:0,limit:10,entry_q:q,entry_status:status,entry_order:order})).cash
   const net=rows.filter(keep).reduce((s,r)=>s+cents(r),0);expect(Math.round(Number(first.entries.sums.net)*100)).toBe(net)
   expect(Math.round(Number(first.entries.sums.debit)*100)-Math.round(Number(first.entries.sums.credit)*100)).toBe(net)
   expect([first.debit,first.credit,first.opening,first.closing]).toEqual([period.debit,period.credit,period.opening,period.closing]) // period balances stay unfiltered
  }
  const all=(await call('erp_cp7_get_finance_analysis_v1',{...base,entry_status:null})).cash;expect(all.entries.sums.debit).toBe(all.debit);expect(all.entries.sums.credit).toBe(all.credit)
  for(const bad of [{entry_status:'DRAFT'},{entry_order:'RANDOM'},{entry_q:3},{entry_order:null},{entry_status:''},{entry_q:'x'.repeat(121)}])
   await expect(call('erp_cp7_get_finance_analysis_v1',{...base,...bad})).rejects.toThrow('CP7_FINANCE_ANALYSIS_QUERY')
 },120000)
 test('invoice payment history: filter, search and order before paging; old call keeps its shape',async()=>{
  const sale='b0000000-0000-4000-8000-000000000001',bank='b1000000-0000-4000-8000-000000000001',rows=facts('b2','PAY',['REVERSED','POSTED','DRAFT'])
  await db.execute(`insert into erp.sales_headers values('${sale}',7);insert into erp.cash_accounts(id,coa_account_id,cash_account_code,cash_account_name,account_kind)values('${bank}',gen_random_uuid(),'B1','Bank Jarum','BANK')`)
  for(const r of rows)await db.execute(`insert into erp.sales_payments values('${r.id}','${sale}',${lit(r.label)},timestamptz '2026-01-01 01:00Z'+${r.at}*interval '1 hour',10,${r.at%2?`'${bank}'`:'null'},'CASH',null,${lit(r.note)},'${r.status}',null)`)
  const old=await walk(o=>call('erp_cp7_get_sales_cash_v1',{sale_id:sale,payment_offset:o,payment_limit:25}),r=>r.payments)
  expect(old.ids).toEqual(expected(rows,desc,'SOURCE'));expect(old.list).toBeNull()
  expect(await sameOld(o=>call('erp_cp7_get_sales_cash_v1',{sale_id:sale,payment_offset:o,payment_limit:7}),r=>r.payments)).toBe(5)
  for(const order of ['SOURCE','LABEL_ASC','LABEL_DESC'])for(const status of [null,'POSTED','REVERSED','DRAFT'])for(const q of ['','NEEDLE','jarum']){
   const keep=(r:Fact)=>(!status||r.status===status)&&(!q||(q==='NEEDLE'?r.note!==null:r.at%2===1)),want=expected(rows,desc,order,keep)
   const got=await walk(o=>call('erp_cp7_get_sales_cash_v1',{sale_id:sale,payment_offset:o,payment_limit:7,payment_q:q,payment_status:status,payment_order:order}),r=>r.payments)
   expect(got.ids).toEqual(want);expect(got.total).toBe(String(want.length));expect(got.list).toEqual({q,status,order})
  }
  for(const bad of [{payment_status:'PAID'},{payment_order:'NEWEST'},{payment_q:null},{payment_status:3}])
   await expect(call('erp_cp7_get_sales_cash_v1',{sale_id:sale,...bad})).rejects.toThrow('CP7_SALES_CASH_QUERY')
 },120000)
 test('invoice return history: history keys search lines too and apply before paging; other kinds refuse them',async()=>{
  const sale='c0000000-0000-4000-8000-000000000001',rows=facts('c2','RET',['REVERSED','POSTED','DRAFT']),product='c1000000-0000-4000-8000-000000000001',lot='c1000000-0000-4000-8000-000000000002',needle='c1000000-0000-4000-8000-000000000003',wh='c1000000-0000-4000-8000-000000000004'
  await db.execute(`insert into erp.sales_headers values('${sale}',3);insert into erp.products values('${product}','SKU-RET','Kaos',null);insert into erp.fg_lots values('${lot}','LOT-1'),('${needle}','LOT-JARUM');insert into erp.locations(id,location_name)values('${wh}','Gudang FG')`)
  for(const [k,r] of rows.entries())await db.execute(`insert into erp.sales_returns values('${r.id}','${sale}',${lit(r.label)},timestamptz '2026-01-01 01:00Z'+${r.at}*interval '1 hour','${r.status}',${lit(r.note)});
   insert into erp.sales_return_items values(gen_random_uuid(),'${r.id}',gen_random_uuid(),'${product}','${k%4===3?needle:lot}','${wh}',1,'GRADE_A',5,null)`)
  const old=await walk(o=>call('erp_cp7_get_sales_returns_v1',{sale_id:sale,kind:'RETURNS',offset:o,limit:25}),r=>r.page)
  expect(old.ids).toEqual(expected(rows,desc,'SOURCE'));expect(old.list).toBeNull()
  expect(await sameOld(o=>call('erp_cp7_get_sales_returns_v1',{sale_id:sale,kind:'RETURNS',q:'',offset:o,limit:7}),r=>r.page)).toBe(5)
  for(const order of ['SOURCE','LABEL_ASC','LABEL_DESC'])for(const status of [null,'POSTED','REVERSED'])for(const q of ['','needle','lot-jarum']){
   const keep=(r:Fact)=>(!status||r.status===status)&&(!q||(q==='needle'?r.note!==null:rows.indexOf(r)%4===3)),want=expected(rows,desc,order,keep)
   const got=await walk(o=>call('erp_cp7_get_sales_returns_v1',{sale_id:sale,kind:'RETURNS',offset:o,limit:6,q:'',history_q:q,history_status:status,history_order:order}),r=>r.page)
   expect(got.ids).toEqual(want);expect(got.total).toBe(String(want.length));expect(got.list).toEqual({q,status,order})
  }
  await expect(call('erp_cp7_get_sales_returns_v1',{sale_id:sale,kind:'LOCATIONS',history_order:'SOURCE'})).rejects.toThrow('CP7_SALES_RETURN_QUERY')
  for(const bad of [{history_status:'VOID'},{history_order:'X'},{history_q:1}])await expect(call('erp_cp7_get_sales_returns_v1',{sale_id:sale,kind:'RETURNS',...bad})).rejects.toThrow('CP7_SALES_RETURN_QUERY')
 },120000)
 test('saved Nota list: status and order apply to every matching note; other sections refuse them',async()=>{
  const mandor='d1000000-0000-4000-8000-000000000001',rows=facts('d2','NOTA',['VOID','POSTED','DRAFT'])
  await db.execute(`insert into erp.contractors values('${mandor}','Mandor Jarum')`)
  for(const r of rows)await db.execute(`insert into cp7_payroll.notes(id,note_number,contractor_id,note_date,period_start,period_end,notes,status,row_version,created_at,updated_at,cards)
   values('${r.id}',${lit(r.label)},'${mandor}','2026-01-02','2026-01-01','2026-01-07',${lit(r.note)},'${r.status}',1,timestamptz '2026-01-01 01:00Z'+${r.at}*interval '1 hour',now(),'[]')`)
  const old=await walk(o=>call('erp_cp7_get_nota_workspace_v1',{q:'',offset:o,limit:25},'NOTES'),r=>r.page)
  expect(old.ids).toEqual(expected(rows,desc,'SOURCE'));expect(old.list).toBeNull()
  expect(await sameOld(o=>call('erp_cp7_get_nota_workspace_v1',{q:'',offset:o,limit:8},'NOTES'),r=>r.page)).toBe(4)
  for(const order of ['SOURCE','LABEL_ASC','LABEL_DESC'])for(const status of [null,'DRAFT','POSTED','VOID'])for(const q of ['','needle']){
   const keep=(r:Fact)=>(!status||r.status===status)&&(!q||r.note!==null),want=expected(rows,desc,order,keep)
   const got=await walk(o=>call('erp_cp7_get_nota_workspace_v1',{q,offset:o,limit:8,status,order},'NOTES'),r=>r.page)
   expect(got.ids).toEqual(want);expect(got.total).toBe(String(want.length));expect(got.list).toEqual({q,status,order})
  }
  await expect(call('erp_cp7_get_nota_workspace_v1',{q:'',order:'SOURCE',contractor_id:mandor},'PAYROLLS')).rejects.toThrow('CP7_NOTA_QUERY')
  for(const bad of [{status:'REVERSED'},{order:null},{order:'LABEL'}])await expect(call('erp_cp7_get_nota_workspace_v1',bad,'NOTES')).rejects.toThrow('CP7_NOTA_QUERY')
 },120000)
 test('FG adjustment and material count documents: status and order apply before paging',async()=>{
  const wh='e1000000-0000-4000-8000-000000000001';await db.execute(`insert into erp.locations(id,location_name)values('${wh}','Gudang E')`)
  for(const [fn,table,prefix,error] of [['erp_cp7_get_fg_adjustments_v1','erp.fg_adjustments','e2','CP7_FG_ADJUST_QUERY'],['erp_cp7_get_material_counts_v1','erp.material_adjustments','f2','CP7_COUNT_QUERY']] as const){
   const rows=facts(prefix,'ADJ',['REVERSED','POSTED','DRAFT'])
   for(const r of rows)await db.execute(`insert into ${table}(id,adjustment_number,location_id,physical_at,reason_code,status,row_version,notes)values('${r.id}',${lit(r.label)},'${wh}',timestamptz '2026-01-01 01:00Z'+${r.at}*interval '1 hour','COUNT','${r.status}',1,null)`)
   const old=await walk(o=>call(fn,{q:'',offset:o,limit:25,adjustment_id:null}),r=>r.page)
   expect(old.ids).toEqual(expected(rows,desc,'SOURCE'));expect(old.list).toBeNull()
   expect(await sameOld(o=>call(fn,{q:'adj',offset:o,limit:9,adjustment_id:null}),r=>r.page)).toBe(4)
   for(const order of ['SOURCE','LABEL_ASC','LABEL_DESC'])for(const status of [null,'DRAFT','POSTED','REVERSED'])for(const q of ['','adj-1']){
    const keep=(r:Fact)=>(!status||r.status===status)&&(!q||r.label.toLowerCase().includes(q)),want=expected(rows,desc,order,keep)
    const got=await walk(o=>call(fn,{q,offset:o,limit:9,adjustment_id:null,status,order}),r=>r.page)
    expect(got.ids).toEqual(want);expect(got.total).toBe(String(want.length));expect(got.list).toEqual({q,status,order})
   }
   for(const bad of [{status:'VOID'},{order:null},{order:1}])await expect(call(fn,bad)).rejects.toThrow(error)
  }
 },120000)
 test('FG movement card: movement type and order apply to every searched movement; balances keep the complete prefix',async()=>{
  const product='a7000000-0000-4000-8000-000000000001',lot='a7000000-0000-4000-8000-000000000002',location='a7000000-0000-4000-8000-000000000003',kinds=['QC_GOOD','SALE','REVERSAL'],rows=facts('a8','X',kinds)
  for(const [k,r] of rows.entries())await db.execute(`insert into erp.customers values('${id('a9',k+1)}',${lit(r.label)});
   insert into erp.fg_stock_movements values('${r.id}','${product}','${lot}','${location}','GRADE_A',timestamptz '2025-10-01 01:00Z'+${r.at}*interval '1 hour',timestamptz '2025-10-01 02:00Z'+${r.at}*interval '1 hour','${r.status}','SALE_ITEM','${r.id}',null,'${id('a9',k+1)}',${lit(r.note)},${k+1},${r.status==='SALE'?-1:2})`)
  const position={product_id:product,lot_id:lot,location_id:location,quality_grade:'GRADE_A'},source=asc
  const old=await walk(o=>call('erp_cp7_get_fg_ledger_v2',{...position,offset:o,limit:25}),r=>r.page)
  expect(old.ids).toEqual(expected(rows,source,'SOURCE'));expect(old.list).toBeNull()
  expect(await sameOld(o=>call('erp_cp7_get_fg_ledger_v2',{...position,q:'needle',offset:o,limit:2}),r=>r.page)).toBe(3)
  const card=await call('erp_cp7_get_fg_ledger_v2',{...position,offset:0,limit:5,movement_type:'SALE',order:'LABEL_DESC'})
  const physical=rows.reduce((s,r)=>s+(r.status==='SALE'?-1:2),0);expect(card.balances.physical_qty).toBe(String(physical))
  for(const order of ['SOURCE','LABEL_ASC','LABEL_DESC'])for(const type of [null,...kinds])for(const q of ['','needle']){
   const keep=(r:Fact)=>(!type||r.status===type)&&(!q||r.note!==null),want=expected(rows,source,order,keep)
   const got=await walk(o=>call('erp_cp7_get_fg_ledger_v2',{...position,q,offset:o,limit:7,movement_type:type,order}),r=>r.page)
   expect(got.ids).toEqual(want);expect(got.total).toBe(String(want.length));expect(got.list).toEqual({q,movement_type:type,order,movement_types:[...kinds].sort()})
  }
  for(const bad of [{movement_type:'sale'},{movement_type:'X'.repeat(41)},{order:null},{order:'NEWEST'}])
   await expect(call('erp_cp7_get_fg_ledger_v2',{...position,...bad})).rejects.toThrow('CP7_FG_QUERY')
 },120000)
 test('accessory notes: status, search and natural order cover the whole history; count follows the filter; old calls unchanged',async()=>{
  const [mandor,other,wh,cat,button,fabric]=[1,2,3,4,5,6].map(i=>id('a6',i))
  await db.execute(`insert into erp.contractors(id,contractor_name)values('${mandor}','Mandor Jarum'),('${other}','Mandor Lain');
   insert into erp.locations(id,location_name,location_type)values('${wh}','Gudang Aksesori','RAW_MATERIAL_WAREHOUSE');
   insert into erp.uom_definitions values('PCS','COUNT'),('M','LENGTH');insert into erp.accessory_categories values('${cat}','Kancing','PCS');
   insert into erp.materials values('${button}','KC-1','Kancing','ACCESSORY','PCS','${cat}'),('${fabric}','KN-1','Kain','FABRIC','M',null)`)
  const rows=facts('a5','NA',['REVERSED','DRAFT','POSTED'])
  for(const [k,r] of rows.entries())await db.execute(`insert into erp.contractor_material_issues values('${r.id}',${lit(r.label)},'${r.note?mandor:other}','${wh}',null,timestamptz '2026-01-01 01:00Z'+${r.at}*interval '5 hours','${r.status}',${k+1},null);
   insert into erp.contractor_material_issue_items values(gen_random_uuid(),'${r.id}','${button}',${k+1},null,1,1,'PCS',null,${k+1}.5,'OPEN')`)
  // A fabric note is not an accessory note: never listed or counted, before or after the stage.
  await db.execute(`insert into erp.contractor_material_issues values('${id('a4',1)}','NA-99','${mandor}','${wh}',null,timestamptz '2026-01-02 01:00Z','POSTED',1,null);
   insert into erp.contractor_material_issue_items values(gen_random_uuid(),'${id('a4',1)}','${fabric}',1,null,1,1,'M',null,1,'OPEN')`)
  // Source order: business date (WIB) newest first, then id.
  const day=(r:Fact)=>new Date(Date.UTC(2026,0,1,8)+r.at*5*3600e3).toISOString().slice(0,10),source=(a:Fact,b:Fact)=>bytewise(day(b),day(a))||bytewise(a.id,b.id)
  const read=(f:Json)=>call('erp_get_accessory_issue_workspace_v1',f),plain=async(f:Json)=>{const {physical_local:_,...r}=await read(f);return r}
  const olds=[{},{query:'jarum'},{query:' NA-1 '},{id:rows[4].id},{query:'',material_query:'kanc',contractor_id:mandor,location_id:wh,physical_at:'2026-01-03T10:00:00+07:00',material_ids:[button]}]
  for(const f of olds){const now=await plain(f);expect(now).toEqual(await original(()=>plain(f)));expect(now).not.toHaveProperty('history_page')}
  const old=await read({});expect(old.history.map((h:Json)=>h.id)).toEqual(expected(rows,source,'SOURCE'));expect(old.history_count).toBe(31)
  const page=(r:Json)=>({rows:r.history,total:String(r.history_count),...r.history_page})
  for(const order of ['SOURCE','LABEL_ASC','LABEL_DESC'])for(const status of [null,'DRAFT','POSTED','REVERSED'])for(const q of ['','jarum','na-1']){
   const keep=(r:Fact)=>(!status||r.status===status)&&(!q||(q==='jarum'?r.note!==null:r.label.toLowerCase().includes(q))),want=expected(rows,source,order,keep)
   const got=await walk(o=>read({query:q,history_status:status,history_order:order,history_offset:o,history_limit:4}),page)
   expect(got.ids).toEqual(want);expect(got.total).toBe(String(want.length));expect(got.list).toEqual({q,status,order})
  }
  const listed=await read({history_order:'LABEL_ASC',history_offset:0,history_limit:3})
  expect(listed.history.map((h:Json)=>Object.keys(h).sort())).toEqual(old.history.slice(0,3).map((h:Json)=>Object.keys(h).sort()))
  expect(listed.filters).toEqual({history_order:'LABEL_ASC',history_offset:0,history_limit:3})
  // Beyond the old cap of 50 newest notes: 25 older notes without lines are still accessory notes.
  await db.execute(`insert into erp.contractor_material_issues select ('a3000000-0000-4000-8000-'||lpad(g::text,12,'0'))::uuid,'NB-'||g,'${other}','${wh}',null,timestamptz '2025-12-01 01:00Z'+g*interval '3 hours','POSTED',1,null from generate_series(1,25)g`)
  const older=(await db.query(`select id::text id from erp.contractor_material_issues where issue_number like 'NB-%' order by (physical_at at time zone 'Asia/Jakarta')::date desc,id`)).map(r=>r.id as string)
  const capped=await read({});expect(capped.history).toHaveLength(50);expect(capped.history_count).toBe(56);expect(await plain({})).toEqual(await original(()=>plain({})))
  const whole=await walk(o=>read({history_offset:o,history_limit:50}),page)
  expect(whole.ids).toEqual([...expected(rows,source,'SOURCE'),...older]);expect(whole.pages).toBe(2);expect(whole.total).toBe('56')
  for(const bad of [{history_status:'VOID'},{history_status:3},{history_order:null},{history_order:'NEWEST'},{history_offset:-1},{history_offset:1.5},{history_offset:'0'},
   {history_offset:2000000},{history_limit:0},{history_limit:51},{history_limit:'5'}])await expect(read(bad)).rejects.toThrow('Daftar nota tidak valid')
  for(const bad of [{limit:5},{offset:0},{status:'POSTED'}])await expect(read(bad)).rejects.toThrow('unexpected key')
 },120000)
})
