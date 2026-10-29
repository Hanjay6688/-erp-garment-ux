/** Focused SQL execution: actual D quote and retained collectors/kernel, structural/factual doubles elsewhere. */
import {readFile} from 'node:fs/promises'
import {execFileSync} from 'node:child_process'
import assert from 'node:assert/strict'
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
 const q=await quote(p);assert.equal(q.state,'READY');assert.equal(q.credit_delta,'50.00');assert.equal(q.after_available,'250.00')
 const p2=structuredClone(p);p2.replacement.items[0].refund_amount='251.00';assert.notEqual((await quote(p2)).review_token,q.review_token)
 await db.query("insert into cp7_credit.consumption_events(id,cohort_id,event_kind,amount,economic_date,transaction_date,target_sale_id,journal_id,source_sha256)values($1,$2,'APPLY',180,'2026-10-03','2026-10-03',$3,$4,repeat('a',64))",[consumer,cohort,target,id(45)])
 const used=await quote(p);assert.equal(used.state,'READY');assert.equal(used.after_available,'70.00');assert.equal(used.active_consumers[0].target_sale_id,target)
 const p3=structuredClone(p);p3.replacement.items[0].refund_amount='100.00';const blocked=await quote(p3);assert.equal(blocked.state,'REFUSE');assert(blocked.issues.includes('UNDO_ACTIVE_CONSUMERS_FIRST'));assert.equal(blocked.active_consumers[0].undo_action,'Batalkan penggunaan kredit di invoice tujuan')
 await db.query("insert into cp7_credit.consumption_events(id,cohort_id,event_kind,amount,economic_date,transaction_date,target_sale_id,journal_id,restores_event_id,source_sha256)values($1,$2,'APPLY',-180,'2026-10-04','2026-10-04',$3,$4,$5,repeat('a',64))",[id(46),cohort,target,id(47),consumer])
 const undone=await quote(p);assert.equal(undone.state,'READY');assert.deepEqual(undone.active_consumers,[]);assert.equal(undone.after_available,'250.00')
 const historical=await quote(p3);assert(historical.issues.includes('HISTORICAL_CAPACITY_ADAPTER_REQUIRED'));assert(!historical.issues.includes('UNDO_ACTIVE_CONSUMERS_FIRST'));assert.deepEqual(historical.active_consumers,[])
 const physical=structuredClone(p);physical.replacement.items[0].qty_pcs='3';assert((await quote(physical)).issues.includes('PHYSICAL_OR_QUANTITY_CHANGE_ADAPTER_REQUIRED'))

 // Execute reconciliation SQL bindings with a pending owning structural row.
 // Authority/source/profile/account proofs are still explicit stand-ins. No J
 // is posted, and deferred completion is rolled back, never asserted passed.
 await db.exec((await readFile(new URL('../cp7_customer_credit/ledger/01_immutable_facts.proposal.sql',here),'utf8')).match(/create domain cp7_credit\.cent_amount as numeric[\s\S]*?;/)[0])
 await db.exec(await statement('../cp7_customer_credit/reconciliation/02_reconciliation_inputs.sql','cp7_credit.source_adjustment_components_v1'))
 await db.exec(await statement('../cp7_customer_credit/reconciliation/02_reconciliation_inputs.sql','cp7_credit.source_adjustment_kernel_v1'))
 await db.exec(await statement('../cp7_customer_credit/ledger/01_immutable_facts.proposal.sql','cp7_credit.native_journal_cent_max'))
 await db.exec("create function cp7_credit.credit_account_facts_v1(uuid)returns jsonb language sql stable as $$select '{\"account\":{}}'::jsonb$$;")
 await db.exec('begin')
 try{
  const operation=id(51),request=id(52),newPlan=id(53),newComponent=id(54),newPart=id(55),creditAccount=id(56)
  await db.query('insert into erp.accounting_period_control(singleton_id)values(1)')
  await db.query('insert into erp.chart_accounts(id)values($1),($2)',[ar,creditAccount])
  await db.query("update cp7_credit.cohorts set ar_account_id=$1,credit_account_id=$2,source_ar_snapshot=(select to_jsonb(a)from erp.chart_accounts a where a.id=$1),credit_account_snapshot='{\"account\":{}}'::jsonb where id=$3",[ar,creditAccount,cohort])
  const before=(await db.query('select cp7_credit.initial_ordinal_input_v1($1)q',[sale])).rows[0].q
  await db.query('update erp.journal_lines set credit=250 where journal_entry_id=$1',[id(23)])
  await db.query('update erp.sales_return_items set refund_amount=250 where return_id=$1',[ret])
  const inp=(await db.query('select cp7_credit.initial_ordinal_input_v1($1)q',[sale])).rows[0].q
  const result=(await db.query('select ow04_ordinal_wrapper.reconcile_v1($1::jsonb)q',[inp])).rows[0].q
  const kernel=(await db.query('select cp7_credit.source_adjustment_kernel_v1($1::jsonb)q',[result.families[0]])).rows[0].q
  assert.equal(kernel.net_current_k,'50.00');assert.equal(kernel.components.length,1)
  const c=kernel.components[0],parts=[{id:newPart,component_id:newComponent,ordinal:1,amount:'50.00'}]
  const manifest=[{plan_id:newPlan,family_id:family,cohort_id:cohort,request_ordinal:1,components:[{id:newComponent,ordinal:1,component:c}],parts}]
  const payload={...p,credit_review_token:undone.review_token}
  await db.query('insert into cp7_sales_return_correction.requests(actor,request_id,payload,expected_version)values($1,$2,$3,\'1\')',[customer,request,payload])
  await db.query("insert into cp7_sales.command_context(backend_pid,transaction_id,actor,sale_id,action)values(pg_backend_pid(),txid_current(),$1,$2,'RETURN')",[customer,sale])
  await db.query(`insert into cp7_credit_correction_de.work_v1(operation_id,operation_ordinal,backend_pid,transaction_id,actor,request_id,sale_id,return_id,expected_version,payload,authority,period,before_source,before_input,before_profile,review,phase,actual_source,actual_input,actual_result,manifest)
   values($1,1,pg_backend_pid(),txid_current(),$2,$3,$4,$5,'1',$6,cp7_sales_return_correction.access_now(),(select to_jsonb(x)from erp.accounting_period_control x where singleton_id=1),cp7_credit.source_native_snapshot_v1($4),$7,'{"actual_objects":[]}'::jsonb,$8,'RECONCILING',cp7_credit.source_native_snapshot_v1($4),$9,$10,$11)`,[operation,customer,request,sale,ret,payload,before,undone,inp,result,manifest])
  await db.query(`insert into cp7_credit.recognition_plans(id,cohort_id,plan_kind,owning_action,actor,request_id,request_ordinal,payload_sha256,review_sha256,family_root_sale_id,before_events,added_events,kernel_result,kernel_version,before_source_sha256,after_source_sha256,support_sha256_pg,components_sha256_pg,parts_sha256_pg,net_amount,has_recognition_effect,expected_component_count,expected_part_count)
   values($1,$2,'ADJUSTMENT','RETURN_CORRECT',$3,$4,1,cp7_credit.pg_jsonb_sha256($5),$6,$7,$8,$9,$10,$11,$12,$13,cp7_credit.pg_jsonb_sha256($14),cp7_credit.pg_jsonb_sha256($15),cp7_credit.pg_jsonb_sha256($16),50,true,1,1)`,[newPlan,cohort,customer,request,payload,undone.review_token,sale,kernel.before_events,kernel.added_events,kernel,kernel.kernel_version,kernel.before_source_sha256,kernel.after_source_sha256,kernel.support,kernel.components,parts])
  await db.query('insert into cp7_credit_correction_de.plans_v1 values($1,$2,$3,$4,1)',[newPlan,operation,family,kernel])
  await db.query('insert into cp7_credit.recognition_components(id,plan_id,ordinal,economic_date,transaction_date,amount,previous_economic_date,previous_transaction_date,corners,kernel_component,component_sha256_pg)values($1,$2,1,$3,$4,$5,$6,$7,$8,$9,cp7_credit.pg_jsonb_sha256($9))',[newComponent,newPlan,c.economic_date,c.transaction_date,c.amount,c.previous_economic_date,c.previous_transaction_date,c.corners,c])
  await db.query('insert into cp7_credit.component_parts(id,component_id,ordinal,amount)values($1,$2,1,50)',[newPart,newComponent])
  for(const phase of ['BEFORE','ADDED'])for(const event of phase==='BEFORE'?kernel.before_events:kernel.added_events){
   await db.query('insert into cp7_credit.plan_support_events(plan_id,event_id,phase,kind,amount,economic_date,transaction_date,source_sha256,journal_id,source_fact_snapshot)values($1,$2,$3,$4,$5,$6,$7,$8,$9,\'{}\'::jsonb)',[newPlan,event.id,phase,event.kind,event.amount,event.economic_date,event.transaction_date,event.source_sha256,event.id.slice(8)])
  }
  await db.query('select cp7_credit_correction_de.assert_plan_set_v1($1)',[operation])
  await db.exec('savepoint injected')
  await db.query('update cp7_credit.plan_support_events set amount=amount+0.01 where plan_id=$1',[newPlan])
  await assert.rejects(()=>db.query('select cp7_credit_correction_de.assert_plan_set_v1($1)',[operation]),/CP7_CREDIT_DE_SUPPORT_SET_CHANGED/)
  await db.exec('rollback to savepoint injected;release savepoint injected')
  await db.query('insert into cp7_credit.recognition_plans(id,actor,request_id,request_ordinal)values($1,$2,$3,2)',[id(57),customer,request])
  await assert.rejects(()=>db.query('select cp7_credit_correction_de.assert_plan_set_v1($1)',[operation]),/CP7_CREDIT_DE_PLAN_SET_CHANGED/)
 }finally{await db.exec('rollback')}
 console.log(JSON.stringify({status:'PASS',tests:10,actual_D_quote_and_plan_set_SQL_and_retained_collectors_kernel:true,Native_execution:false,financial_writer_tested:false,standins:'authority, validation, source/profile/account provenance, Native journal rows, HPP eligibility, consumer-event provenance; owning work rolls back without deferred completion; no Native accounting or Auth claim'},null,2))
}catch(error){console.error(JSON.stringify({status:'FAIL',message:error.message,sqlstate:error.code,where:error.where,Native_execution:false},null,2));process.exitCode=1}finally{await db.close()}
