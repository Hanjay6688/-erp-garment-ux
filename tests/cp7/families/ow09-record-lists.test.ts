// @vitest-environment node
import {readFileSync}from'node:fs'
import {beforeAll,afterAll,describe,test,expect}from'vitest'
import {openRuntime,jsonArg}from'./f04/runtime.mjs'
// OW-09 (owner D17-16): sort and filter apply to every matching row before the page is cut; count, sums and pages agree.
// Deliberate raw reader stubs only (ow09/stubs.sql); actual Native business proof is the qualification cases.
type Json=Record<string,any>
let db:Awaited<ReturnType<typeof openRuntime>>
const sources=['finance/analysis.sql','sales/payments.sql','sales/returns.sql','payroll/note-read.sql','fg/adjustment-read.sql','fg/corrected-ledger.sql','materials/count-read.sql']
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
})
