/** Focused SQL execution: actual D quote and retained collectors/kernel, structural/factual doubles elsewhere. */
import {readFile} from 'node:fs/promises'
import {execFileSync} from 'node:child_process'
import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE||'@electric-sql/pglite')
const here=new URL('./',import.meta.url),db=new PGlite(),id=n=>`00000000-0000-4000-8000-${String(n).padStart(12,'0')}`
const [sale,ret,customer,ar,cohort,family,allocation,location,part,component,plan,consumer,target]=Array.from({length:13},(_,i)=>id(i+1))
const statement=async(file,name)=>{const text=await readFile(new URL(file,here),'utf8'),start=text.indexOf('create function '+name+'(');assert(start>=0);const tail=text.slice(start),end=tail.indexOf('$$;',tail.indexOf('$$')+2);return tail.slice(0,end+3)}
try{
 await db.exec(execFileSync('python3',[new URL('local_compile_fixture.py',here).pathname,process.argv[2]],{encoding:'utf8',maxBuffer:15e6}))
 for(const file of ['../cp7_customer_credit/kernel/kernel.sql','../cp7_customer_credit/ordinal-wrapper/wrapper.sql','review.sql','facts.sql','owning.sql','proof.sql','posting.sql','materialize.sql','closure.sql'])await db.exec(await readFile(new URL(file,here),'utf8'))
 await db.exec(`create schema cp7_note;create table cp7_note.revisions(root_sale_id uuid,previous_sale_id uuid,replacement_sale_id uuid);create schema cp7_credit_incoming;
 create or replace function auth.uid()returns uuid language sql stable as $$select '${customer}'::uuid$$;
 create function cp7_sales_return_correction.access_now()returns jsonb language sql volatile as $$select '{"declared_authority_double":true}'::jsonb$$;
 create function cp7_sales_return_correction.validate(jsonb)returns void language plpgsql as $$begin null;end$$;
 create function cp7_credit.assert_current_materialized_profile(uuid,uuid,uuid)returns void language plpgsql stable as $$begin null;end$$;
 create function cp7_credit.inspect_current_materialized_profile(uuid,uuid,uuid)returns jsonb language sql stable as $$select '{"I":"200.00","actual_objects":[]}'::jsonb$$;
 create function cp7_credit.source_native_snapshot_v1(uuid)returns jsonb language sql stable as $$select '{"declared_source_double":true}'::jsonb$$;
 create function cp7_credit.source_hpp_lot_ids_v1(uuid)returns uuid[]language sql stable as $$select '{}'::uuid[]$$;
 create function cp7_credit.consumer_event_data_v1(uuid)returns jsonb language sql stable as $$select '{"declared_consumer_provenance_double":true}'::jsonb$$;
 create or replace function ow04_source_proposal.sha(jsonb)returns text language sql immutable as $$select encode(sha256(convert_to($1::text,'UTF8')),'hex')$$;
 create function cp7_credit_incoming.incoming_applied_v1(uuid)returns numeric language sql stable as $$select 0::numeric$$;
 create function erp.resolve_accounting_transaction_date(date)returns date language sql stable as $$select $1$$;
 create or replace function cp7_credit.account_by_mapping_v1(text)returns uuid language sql stable as $$select '${ar}'::uuid$$;
 `)
 if(!(await db.query("select to_regclass('erp.be_conversion_sources_v1')x")).rows[0].x)await db.exec('create table erp.be_conversion_sources_v1(source_lot_id uuid)')
 await db.exec(await statement('../cp7_customer_credit/ledger/01_immutable_facts.proposal.sql','cp7_credit.pg_jsonb_sha256'))
 await db.exec(await statement('../cp7_customer_credit/coordinator/01_coordinator_facts.sql','cp7_credit.initial_base_events_v1'))
 await db.exec(await statement('../cp7_customer_credit/coordinator/05_factual_profile.sql','cp7_credit.initial_ordinal_input_v1'))
 const active=await statement('../cp7_customer_credit/consumer/05_consumer_data.sql','cp7_credit.consumer_active_events_v1').catch(async()=>{
  const files=execFileSync('rg',['--files',new URL('../cp7_customer_credit/consumer/',here).pathname],{encoding:'utf8'}).trim().split('\n');
  for(const file of files)if(file.endsWith('.sql')&&(await readFile(file,'utf8')).includes('create function cp7_credit.consumer_active_events_v1('))return statement(file,'cp7_credit.consumer_active_events_v1');throw Error('active reader missing')
 })
 await db.exec(active.replace('create function ','create or replace function '))
 await db.query('insert into erp.sales_headers(id,customer_id,status)values($1,$2,\'PAID\')',[sale,customer])
 await db.query('insert into erp.sales_returns(id,sale_id,customer_id,status,physical_at)values($1,$2,$3,\'POSTED\',\'2026-10-02T05:00:00Z\')',[ret,sale,customer])
 await db.query('insert into erp.sales_return_items(id,return_id,sale_stock_allocation_id,location_id,qty_pcs,quality_grade,refund_amount)values($1,$2,$3,$4,2,\'GRADE_A\',200)',[id(41),ret,allocation,location])
 await db.query('insert into erp.accounting_account_mappings(mapping_key,account_id)values(\'AR_CUSTOMER\',$1)',[ar])
 for(const [n,type,source,debit,credit,date]of [[21,'SALE',sale,1000,0,'2026-10-01'],[22,'SALES_PAYMENT',id(43),0,1000,'2026-10-01'],[23,'SALES_RETURN',ret,0,200,'2026-10-02']]){
  await db.query('insert into erp.journal_entries(id,source_type,source_id,status,economic_date,transaction_date)values($1,$2,$3,\'POSTED\',$4,$4)',[id(n),type,source,date])
  await db.query('insert into erp.journal_lines(id,journal_entry_id,account_id,debit,credit)values($1,$2,$3,$4,$5)',[id(n+100),id(n),ar,debit,credit])
 }
 await db.query('insert into erp.sales_payments(id,sale_id,status,amount)values($1,$2,\'POSTED\',1000)',[id(43),sale])
 await db.query("insert into cp7_credit.return_families(id,family_root_sale_id,family_ordinal,first_return_id,source_sha256)values($1,$2,1,$3,repeat('a',64))",[family,sale,ret])
 await db.query('insert into cp7_credit.return_family_members(family_id,return_id)values($1,$2)',[family,ret])
 await db.query('insert into cp7_credit.cohorts(id,family_id,source_sale_id,source_return_id)values($1,$2,$3,$4)',[cohort,family,sale,ret])
 await db.query('insert into cp7_credit.recognition_plans(id,cohort_id)values($1,$2)',[plan,cohort])
 await db.query('insert into cp7_credit.recognition_components(id,plan_id)values($1,$2)',[component,plan])
 await db.query('insert into cp7_credit.component_parts(id,component_id,amount)values($1,$2,200)',[part,component])
 await db.query("insert into cp7_credit.component_journals(part_id,journal_id,economic_date,transaction_date)values($1,$2,'2026-10-02','2026-10-02')",[part,id(44)])
 const p={sale_id:sale,return_id:ret,review_token:'a'.repeat(32),return_review_token:'b'.repeat(32),change_reason:'Nilai kredit ditinjau',replacement:{physical_at:'2026-10-02T05:00:00Z',notes:null,items:[{allocation_id:allocation,location_id:location,qty_pcs:'2',quality_grade:'GRADE_A',refund_amount:'250.00',notes:null}]}}
 const quote=async(payload)=>(await db.query('select cp7_credit_correction_de.quote_v1($1::jsonb)q',[payload])).rows[0].q

 // All rows below are declared LOCAL structural/source doubles. They are not
 // posted Native documents. The unchanged Native normalizer is executed only
 // for its per-item cap; stock, cost, journal and full transaction proof are absent.
 await db.query('insert into erp.sales_items(id,sale_id,product_id,qty_pcs,unit_price_snapshot,discount_amount,line_total)values($1,$2,$3,5,200,0,1000)',[id(80),sale,id(82)])
 await db.query('insert into erp.sale_stock_allocations(id,sale_item_id,qty_pcs,lot_id,unit_hpp_snapshot)values($1,$2,5,$3,10)',[allocation,id(80),id(81)])
 await db.query("insert into erp.locations(id,is_active,location_type)values($1,true,'FG_WAREHOUSE')",[location])
 await db.exec(`create table cap_source_override(snapshot jsonb);
 create or replace function cp7_credit.source_native_snapshot_v1(p_sale uuid)returns jsonb language sql stable as $$
 select coalesce((select snapshot from public.cap_source_override),jsonb_build_object('declared_cap_source_double',true,
 'sale',(select to_jsonb(h)from erp.sales_headers h where h.id=p_sale),
 'items',(select coalesce(jsonb_agg(to_jsonb(i)order by i.id),'[]')from erp.sales_items i where i.sale_id=p_sale),
 'allocations',(select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]')from erp.sale_stock_allocations a)))$$;
 create view erp.v_current_hpp as select '${id(81)}'::uuid lot_id,10::numeric hpp_per_pcs;`)
 const dump=await readFile(process.argv[2],'utf8'),marker='CREATE FUNCTION erp.normalize_sales_return_item_from_allocation()';assert.equal(dump.split(marker).length,2)
 const tail=dump.slice(dump.indexOf(marker)),normalizer=tail.slice(0,tail.indexOf('$$;')+3)
 const normalizerSHA=createHash('sha256').update(normalizer).digest('hex');assert.equal(normalizerSHA,'1ca83d0e1728833c1fff2d3a285b142f8b1064e85afd3560573f885fedfd92bc')
 await db.exec(normalizer)
 await db.exec('create trigger local_cap_only before insert on erp.sales_return_items for each row execute function erp.normalize_sales_return_item_from_allocation()')
 let inserted=1000;const checks=[]
 async function nativeCap(amount,qty){
  await db.exec('begin;savepoint cap_only');let allowed=true,message=''
  try{await db.query("insert into erp.sales_return_items(id,return_id,sale_stock_allocation_id,location_id,qty_pcs,quality_grade,refund_amount)values($1,$2,$3,$4,$5,'GRADE_A',$6)",[id(inserted++),ret,allocation,location,qty,amount])}
  catch(error){allowed=false;message=error.message}
  finally{await db.exec('rollback to savepoint cap_only;release savepoint cap_only;rollback')}
  if(!allowed)assert.match(message,/exceeds original net sales value/)
  return allowed
 }
 async function checkCap(name,{qty,net,saleQty=5,allocQty=saleQty,price='200.00',discount='0.00',amount,over}){
  await db.query('update erp.sales_items set qty_pcs=$1,line_total=$2,unit_price_snapshot=$3,discount_amount=$4 where id=$5',[saleQty,net,price,discount,id(80)])
  await db.query('update erp.sale_stock_allocations set qty_pcs=$1 where id=$2',[allocQty,allocation])
  await db.query('update erp.sales_return_items set qty_pcs=$1 where id=$2',[qty,id(41)])
  const next=structuredClone(p);Object.assign(next.replacement.items[0],{qty_pcs:String(qty),refund_amount:amount})
  const q=await quote(next);assert.equal(q.issues.includes('REFUND_EXCEEDS_ORIGINAL_NET_SALES_CAP'),over,name)
  assert(!q.issues.includes('REFUND_CAP_SOURCE_UNAVAILABLE'),name)
  assert.equal(await nativeCap(amount,qty),!over,name+' must match exact unchanged Native normalizer')
  if(over)assert.equal(q.state,'REFUSE',name+' never READY')
  else if(Number(amount)>200)assert.equal(q.state,'READY',name)
  checks.push({name,cap_exceeded:over,unchanged_Native_cap_allowed:!over})
 }
 for(const [qty,max]of [[1,200],[2,400]]){
  await checkCap(qty+'pcs exact limit',{qty,net:'1000.00',amount:max+'.00',over:false})
  await checkCap(qty+'pcs tolerance .01',{qty,net:'1000.00',amount:max+'.01',over:false})
  await checkCap(qty+'pcs above tolerance .02',{qty,net:'1000.00',amount:max+'.02',over:true})
 }
 await checkCap('discount uses net not gross .01',{qty:2,net:'900.00',discount:'100.00',amount:'360.01',over:false})
 await checkCap('discount uses net not gross .02',{qty:2,net:'900.00',discount:'100.00',amount:'360.02',over:true})
 await checkCap('discount prevents gross price over-refund',{qty:2,net:'900.00',discount:'100.00',amount:'400.00',over:true})
 await checkCap('proportional third .34',{qty:1,saleQty:3,net:'1000.00',amount:'333.34',over:false})
 await checkCap('proportional third .35',{qty:1,saleQty:3,net:'1000.00',amount:'333.35',over:true})
 await checkCap('never round half cent to whole cent before tolerance',{qty:1,saleQty:2,net:'1000.01',amount:'500.02',over:true})
 await checkCap('same half-cent .01 lawful',{qty:1,saleQty:2,net:'1000.01',amount:'500.01',over:false})
 await checkCap('numeric24_6 assignment rounds before tolerance',{qty:5000,saleQty:100000000,net:'9999999.99',amount:'500.01',over:false})
 await checkCap('numeric24_6 next cent refused',{qty:5000,saleQty:100000000,net:'9999999.99',amount:'500.02',over:true})
 await checkCap('reset ordinary lawful basis',{qty:2,net:'1000.00',amount:'250.00',over:false})
 const fresh=await quote(p)
 await db.query('update erp.sales_items set line_total=900,discount_amount=100 where id=$1',[id(80)])
 const changed=await quote(p);assert.equal(changed.state,'READY');assert.notEqual(changed.review_token,fresh.review_token,'local current cap/source change retires token');checks.push({name:'current source refresh changes token; local double mutation only'})
 const snapshot=(await db.query('select cp7_credit.source_native_snapshot_v1($1)s',[sale])).rows[0].s
 async function unavailable(name,s){await db.query('insert into cap_source_override values($1::jsonb)',[s]);const q=await quote(p);assert.equal(q.state,'REFUSE',name);assert(q.issues.includes('REFUND_CAP_SOURCE_UNAVAILABLE'),name);await db.exec('delete from cap_source_override');checks.push({name,source_unavailable:true})}
 const missing=structuredClone(snapshot);missing.allocations=[];await unavailable('missing allocation cannot vanish',missing)
 const duplicate=structuredClone(snapshot);duplicate.allocations.push(structuredClone(duplicate.allocations[0]));await unavailable('duplicate allocation cannot vanish',duplicate)
 const missingItem=structuredClone(snapshot);missingItem.items=[];await unavailable('missing source item cannot vanish',missingItem)
 const duplicateItem=structuredClone(snapshot);duplicateItem.items.push(structuredClone(duplicateItem.items[0]));await unavailable('duplicate source item cannot vanish',duplicateItem)
 const foreign=structuredClone(snapshot);foreign.items[0].sale_id=target;await unavailable('foreign source item refuses',foreign)
 const foreignCustomer=structuredClone(snapshot);foreignCustomer.sale.customer_id=target;await unavailable('foreign customer refuses',foreignCustomer)
 const foreignSale=structuredClone(snapshot);foreignSale.sale.id=target;await unavailable('foreign sale refuses',foreignSale)
 const shortQty=structuredClone(snapshot);shortQty.allocations[0].qty_pcs=1;await unavailable('allocation quantity below return refuses',shortQty)
 const noBasis=structuredClone(snapshot);delete noBasis.items[0].line_total;await unavailable('missing net basis refuses',noBasis)
 const empty=structuredClone(snapshot);empty.items[0].qty_pcs=0;await unavailable('zero sale qty cannot fabricate cap',empty)
 await unavailable('missing source structure refuses',{declared_source_double:true})
 // A second valid line cannot contribute unused capacity to an over-cap first.
 await db.query('update erp.sales_items set line_total=1000,discount_amount=0 where id=$1',[id(80)])
 await db.query('insert into erp.sales_items(id,sale_id,product_id,qty_pcs,line_total)values($1,$2,$3,5,1000)',[id(90),sale,id(82)])
 await db.query('insert into erp.sale_stock_allocations(id,sale_item_id,qty_pcs,lot_id,unit_hpp_snapshot)values($1,$2,5,$3,10)',[id(91),id(90),id(81)])
 await db.query("insert into erp.sales_return_items(id,return_id,sale_stock_allocation_id,location_id,qty_pcs,quality_grade,refund_amount)values($1,$2,$3,$4,2,'GRADE_A',0)",[id(92),ret,id(91),location])
 const multi=structuredClone(p);multi.replacement.items[0].refund_amount='400.02';multi.replacement.items.push({...multi.replacement.items[0],allocation_id:id(91),refund_amount:'0.00'})
 const perLine=await quote(multi);assert.equal(perLine.state,'REFUSE');assert(perLine.issues.includes('REFUND_EXCEEDS_ORIGINAL_NET_SALES_CAP'));checks.push({name:'per-line limit never pooled across allocations'})
 const faultSQL=execFileSync('python3',['-c',`import ast,pathlib
p=pathlib.Path('scripts/cp7_credit_correction_de/cases.py');t=ast.parse(p.read_text());s=[n.value for n in ast.walk(t)if isinstance(n,ast.Constant)and isinstance(n.value,str)and 'create function cp7_credit_correction_de.test_part_failure()'in n.value];assert len(s)==1;print(s[0])`],{encoding:'utf8'})
 await db.exec(faultSQL);checks.push({name:'private AFTER INSERT failure hook declarations compile; not executed'})
 console.log(JSON.stringify({status:'PASS',tests:checks.length,checks,actual_quote_SQL:true,unchanged_Native_cap_trigger_SQL:true,normalizer_sha256:normalizerSHA,Native_financial_execution:false,actual_Native_case_credit:0,standins:'structural schema, authority/validation/source/profile/account/HPP/input journals; mutation controls are local doubles, never posted Native edits; no money writer/Auth/full restore claim'},null,2))
}catch(error){console.error(JSON.stringify({status:'FAIL',message:error.message,sqlstate:error.code,where:error.where,Native_financial_execution:false},null,2));process.exitCode=1}finally{await db.close()}
