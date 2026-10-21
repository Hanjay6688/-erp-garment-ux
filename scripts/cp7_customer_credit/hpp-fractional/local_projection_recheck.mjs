// Financial arithmetic and source-seal regression on an isolated PGlite DB.
// Rows below are deliberately synthetic: this is NOT Native writer, auth,
// concurrency, browser, deployment or production acceptance.
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash,randomUUID} from 'node:crypto'
import {execFileSync} from 'node:child_process'
const {PGlite}=await import(process.env.PGLITE_MODULE)
const root=new URL('../../../',import.meta.url)
const read=path=>readFileSync(new URL(path,root),'utf8')
const sha=value=>createHash('sha256').update(value).digest('hex')
const expectations=read('docs/cp7/d17-14/ow04/hpp-fractional/EXPECTED_LITERAL.json')
const declared=JSON.parse(expectations)
const projectionSource=read('scripts/cp7_customer_credit/coordinator/02_initial_projection.sql')
const bookSource=read('scripts/cp7_customer_credit/coordinator/02_hpp_book.sql')
const nativeSource=read('supabase/release/cp6-t3/20260926050000_erp_v2_6_20be_cp6_conversion_redye_pocket.sql')
const extract=(text,name,delimiter)=>{
 const start=text.search(new RegExp('create (?:or replace )?function '+name.replaceAll('.','\\.')+'\\s*\\(','i'))
 assert.ok(start>=0,name)
 const first=text.indexOf(delimiter,start),end=text.indexOf(delimiter+';',first+delimiter.length)
 assert.ok(first>=0&&end>first,name)
 return text.slice(start,end+delimiter.length+1)
}
const db=new PGlite(),results=[]
await db.exec(`create schema erp;create schema cp7_credit;
create table erp.fg_lots(id uuid,product_id uuid,po_id uuid,lot_origin text,initial_qty_pcs integer);
create table erp.hpp_versions(id uuid,lot_id uuid,is_current boolean,total_cost numeric,qty_basis_pcs integer,hpp_per_pcs numeric);
create table erp.fg_stock_movements(id uuid,lot_id uuid,qty_signed integer,movement_type text,reversal_of_id uuid);
create table erp.sales_headers(id uuid,status text);
create table erp.sales_items(id uuid,sale_id uuid,product_id uuid);
create table erp.sale_stock_allocations(id uuid,sale_item_id uuid,lot_id uuid,qty_pcs integer,unit_hpp_snapshot numeric);
create table erp.sales_returns(id uuid,status text);
create table erp.sales_return_items(id uuid,return_id uuid,lot_id uuid,qty_pcs integer,sale_stock_allocation_id uuid);
create table erp.product_conversions(id uuid,status text);
create table erp.product_conversion_allocations(id uuid,conversion_id uuid,source_lot_id uuid,destination_lot_id uuid,qty_pcs integer);
create table erp.be_conversion_sources_v1(conversion_id uuid,source_lot_id uuid);
create table erp.be_conversion_cost_sources_v1(document_id uuid,conversion_id uuid);
create table erp.be_conversion_cost_events_v1(id uuid,document_id uuid,target_amount numeric,previous_amount numeric);
create table erp.journal_entries(id uuid,source_type text,source_id uuid,status text,reversal_of_id uuid);
create table erp.journal_lines(id uuid,journal_entry_id uuid,account_id uuid,product_id uuid,po_id uuid,debit numeric,credit numeric);
create table erp.po_wip_close_events(po_id uuid,journal_entry_id uuid,residual_amount numeric);
create table erp.po_hpp_gl_state(po_id uuid,base_output_qty integer,hpp_total_cost numeric,fg_value numeric,cogs_value numeric,other_out_value numeric);
create table erp.locations(id uuid,is_active boolean,location_type text);
create table erp.fg_inventory_balances(product_id uuid,location_id uuid,quality_grade text);
create table erp.accounting_account_mappings(mapping_key text,account_id uuid);
create table erp.chart_accounts(id uuid,is_active boolean,is_postable boolean);
create function cp7_credit.pg_jsonb_sha256(p jsonb)returns text language sql immutable as $$select encode(sha256(convert_to(p::text,'UTF8')),'hex')$$;
create function cp7_credit.cent_text(p numeric)returns text language sql immutable as $$select to_char(p,'FM999999999999990.00')$$;
create function erp.be_po_extra_v1(p uuid)returns numeric language sql stable as $$select coalesce(sum(e.target_amount-e.previous_amount),0)
from erp.be_conversion_cost_events_v1 e join erp.be_conversion_cost_sources_v1 c on c.document_id=e.document_id
join erp.be_conversion_sources_v1 s on s.conversion_id=c.conversion_id join erp.fg_lots l on l.id=s.source_lot_id
where l.po_id=p$$;
create function erp.be_nonpo_admitted_v1(p uuid)returns boolean language sql stable as $$select exists(select 1 from erp.product_conversions c where c.id=p and c.status='POSTED')$$;`)
for(const name of ['initial_po_hpp_lifecycle_amount_v1','initial_po_hpp_book_v1','initial_hpp_account_facts_v1','initial_hpp_support_v1'])
 await db.exec(extract(bookSource,'cp7_credit.'+name,'$function$'))
for(const name of ['account_by_mapping_v1','initial_hpp_targets_v1','initial_hpp_projection_v1'])
 await db.exec(extract(projectionSource,'cp7_credit.'+name,'$$'))
for(const name of ['compute_po_hpp_gl_targets_v2620d','compute_non_po_product_hpp_targets_v2620f'])
 await db.exec(extract(nativeSource,'erp.'+name,'$function$'))
const account={}
for(const key of ['FG_INVENTORY','COGS','OTHER_EXPENSE','OTHER_INCOME']){
 account[key]=randomUUID()
 await db.query('insert into erp.accounting_account_mappings values($1,$2)',[key,account[key]])
 await db.query('insert into erp.chart_accounts values($1,true,true)',[account[key]])
}
const tables=(await db.query("select tablename from pg_tables where schemaname='erp' and tablename not in('chart_accounts','accounting_account_mappings')")).rows.map(r=>r.tablename)
const targetKeys=['hpp_total_cost','fg_value','cogs_value','other_out_value']
const money=value=>Number(value).toFixed(2)
const vector=target=>targetKeys.map(key=>money(target[key]))
const one=async(sql,args=[])=>(await db.query(sql,args)).rows[0]
const check=async(gold,mode,sourceLots=gold.lots)=>{
 for(const table of tables)await db.exec('truncate erp.'+table)
 const product=randomUUID(),po=mode==='PO'?randomUUID():null,sale=randomUUID(),location=randomUUID(),entry=randomUUID()
 await db.query("insert into erp.locations values($1,true,'FG_WAREHOUSE')",[location])
 await db.query("insert into erp.fg_inventory_balances values($1,$2,'GOOD')",[product,location])
 await db.query("insert into erp.sales_headers values($1,'POSTED')",[sale])
 const items=[]
 for(const [label,cost,basis,raw,owned,sold,qty]of sourceLots){
  const lot=randomUUID(),version=randomUUID(),line=randomUUID()
  await db.query('insert into erp.fg_lots values($1,$2,$3,$4,$5)',[lot,product,po,po?'PRODUCTION':'OPENING',basis])
  await db.query('insert into erp.hpp_versions values($1,$2,true,$3::numeric,$4::integer,round($3::numeric/$4::integer,6))',[version,lot,cost,basis])
  await db.query("insert into erp.fg_stock_movements values($1,$2,$3,'SYNTHETIC_OWNED',null)",[randomUUID(),lot,owned])
  await db.query('insert into erp.sales_items values($1,$2,$3)',[line,sale,product])
  const split=gold.allocation_returns?.filter(a=>a[1]===label).map(a=>a[2])??(qty?[qty]:[])
  let remaining=sold
  for(const amount of split){
   const allocation=randomUUID(),allocated=split.length>1?amount:sold
   await db.query('insert into erp.sale_stock_allocations values($1,$2,$3,$4,round($5::numeric/$6,6))',[allocation,line,lot,allocated,cost,basis])
   items.push({allocation_id:allocation,lot_id:lot,qty_pcs:String(amount),refund_amount:gold.return_amount??'1.00',location_id:location,quality_grade:'GOOD'})
   remaining-=allocated
  }
  if(remaining>0)await db.query('insert into erp.sale_stock_allocations values($1,$2,$3,$4,round($5::numeric/$6,6))',[randomUUID(),line,lot,remaining,cost,basis])
  if(raw==='2/3'){
   const conversion=randomUUID()
   await db.query("insert into erp.product_conversions values($1,'POSTED')",[conversion])
   await db.query('insert into erp.product_conversion_allocations values($1,$2,$3,$4,1)',[randomUUID(),conversion,lot,randomUUID()])
  }else assert.equal(raw,cost,'Unexpected fixture precision; do not infer a new expectation')
 }
 const queryNative=po?'select *from erp.compute_po_hpp_gl_targets_v2620d($1)':'select *from erp.compute_non_po_product_hpp_targets_v2620f($1)'
 const nativeBefore=await one(queryNative,[po??product])
 assert.deepEqual(vector(nativeBefore),gold.before_target,gold.id+' Native-source formula before')
 await db.query("insert into erp.journal_entries values($1,'SYNTHETIC_OPENING',null,'POSTED',null)",[entry])
 for(const [key,field]of[['FG_INVENTORY','fg_value'],['COGS','cogs_value'],['OTHER_EXPENSE','other_out_value']]){
  const amount=Number(nativeBefore[field]),actualKey=amount<0&&key==='OTHER_EXPENSE'?'OTHER_INCOME':key
  if(amount)await db.query('insert into erp.journal_lines values($1,$2,$3,$4,$5,$6,$7)',[randomUUID(),entry,account[actualKey],po?null:product,po,Math.max(amount,0),Math.max(-amount,0)])
 }
 if(po)await db.query('insert into erp.po_hpp_gl_state values($1,$2,$3,$4,$5,$6)',[po,nativeBefore.base_output_qty,...targetKeys.map(k=>nativeBefore[k])])
 const after=(await one('select cp7_credit.initial_hpp_targets_v1($1,$2,$3,true)p',[product,po,JSON.stringify(items)])).p
 assert.deepEqual(vector(after.target),gold.after_target,gold.id+' candidate after')
 const payload={sale_id:sale,items:items.map(({lot_id,...item})=>item)}
 if(gold.id.startsWith('HPP13_')){
  payload.items=payload.items.map(i=>({...i,refund_amount:'0.00'}))
  await assert.rejects(()=>db.query('select cp7_credit.initial_hpp_projection_v1($1)p',[JSON.stringify(payload)]),/CP7_CREDIT_POSITIVE_HPP_ZERO_VECTOR_UNPROVEN/)
 }else{
  const projected=(await one('select cp7_credit.initial_hpp_projection_v1($1)p',[JSON.stringify(payload)])).p
  assert.equal(projected.hpp_amount,gold.hpp_amount,gold.id+' debit magnitude')
  assert.deepEqual(['fg_value','cogs_value','other_out_value'].map(k=>money(projected.groups[0].delta[k])),gold.delta,gold.id+' vector')
  const actualLines=projected.lines.map(l=>[l.mapping_key,money(l.debit),money(l.credit)]).sort()
  assert.deepEqual(actualLines,[...gold.hpp_lines].sort(),gold.id+' complete lines')
  const beforeSupport=(await one('select cp7_credit.initial_hpp_support_v1($1,$2)p',[product,po])).p
  const ownDraft=randomUUID(),selected=items[0]
  await db.query("insert into erp.sales_returns values($1,'DRAFT')",[ownDraft])
  await db.query('insert into erp.sales_return_items values($1,$2,$3,1,$4)',[randomUUID(),ownDraft,selected.lot_id,selected.allocation_id])
  assert.deepEqual((await one('select cp7_credit.initial_hpp_support_v1($1,$2)p',[product,po])).p,beforeSupport,'Own draft must not change before support')
  const lot=(await one('select id from erp.fg_lots order by id limit 1')).id
  const adjustment=randomUUID()
  await db.query("insert into erp.fg_stock_movements values($1,$2,1,'ADJUSTMENT',null)",[adjustment,lot])
  await db.query("insert into erp.fg_stock_movements values($1,$2,-1,'REVERSAL',$3)",[randomUUID(),lot,adjustment])
  assert.deepEqual(vector(await one(queryNative,[po??product])),gold.before_target,'Source control must be numerically unchanged')
  assert.notEqual((await one('select cp7_credit.initial_hpp_support_v1($1,$2)p',[product,po])).p.sha256,beforeSupport.sha256,'Same-valued changed history must change source seal')
  if(po&&gold.id==='HPP07_TWO_LOTS_SAME_PO_POOL'){
   await db.query('update erp.po_hpp_gl_state set fg_value=fg_value+.01,cogs_value=cogs_value-.01 where po_id=$1',[po])
   await assert.rejects(()=>db.query('select cp7_credit.initial_hpp_projection_v1($1)p',[JSON.stringify(payload)]),/CP7_CREDIT_HPP_TARGET_BOOK_NOT_RECONCILED/)
  }
 }
 results.push({case_id:gold.id,grouping:mode,status:'PASS',before:gold.before_target,after:gold.after_target})
}
let failure
try{
 for(const gold of declared.cases.filter(c=>c.lots)){
  if(gold.grouping==='SEPARATE_PO_P_AND_Q'){
   for(let index=0;index<gold.groups.length;index++)await check({...gold.groups[index],id:gold.id+':'+index,lots:[gold.lots[index]],hpp_lines:[['FG_INVENTORY','0.33','0.00'],['COGS','0.00','0.33']]},'PO')
  }else for(const mode of gold.grouping.startsWith('ONE_')?['PO','NONPO']:[gold.grouping.startsWith('NONPO')?'NONPO':'PO'])await check(gold,mode)
 }
 assert.equal(results.length,22,'The predeclared arithmetic scopes must all execute')
}catch(error){failure=String(error);results.push({status:'FIRST_FAILURE',error:failure,stack:error.stack})}
await db.close()
console.log(JSON.stringify({classification:'LOCAL_PGLITE_SYNTHETIC_HPP_ARITHMETIC_AND_SEAL_NOT_NATIVE',Native:false,
 expected_sha256:sha(expectations),projection_source_sha256:sha(projectionSource),book_source_sha256:sha(bookSource),
 source_head:execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),results,status:failure?'FAIL':'PASS'}))
if(failure)process.exitCode=1
