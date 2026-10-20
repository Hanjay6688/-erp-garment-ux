// Actual outside proposal SQL; selected Native DDL and explicitly synthetic
// fact fixtures only. NO Native writer/permission/poster success stub.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import {execFileSync}from'node:child_process';
const dir=path.dirname(new URL(import.meta.url).pathname),repo=process.env.ERP_REPO||process.cwd(),base=path.join(repo,'scripts/cp7_customer_credit');
const {PGlite}=await import(process.env.PGLITE_MODULE||'@electric-sql/pglite');
const sha=x=>crypto.createHash('sha256').update(x).digest('hex'),read=p=>fs.readFileSync(p==='source/ISOLATED_TABLES.sql'?path.join(dir,'ISOLATED_TABLES.sql'):path.join(base,p),'utf8');
const strip=s=>s.replace(/do \$not_an_installer\$[\s\S]*?end \$not_an_installer\$;/,'-- ONLY removed in isolated exercise');
const db=new PGlite(),sources={},results=[];let stage='setup';
const ex=s=>db.exec(s),q=(s,p=[])=>db.query(s,p),one=async(s,p=[])=>Object.values((await q(s,p)).rows[0])[0];
const id=n=>`00000000-0000-0000-0000-${String(n).padStart(12,'0')}`;
const load=async p=>{stage=p;const s=read(p);sources[p]=sha(s);await ex(strip(s));};
const result={classification:'ACTUAL_PROPOSAL_SQL_SELECTED_NATIVE_DDL_SYNTHETIC_NOT_NATIVE',native_execution_proven:false,
 authority_proven:false,poster_execution_proven:false,expected_sha256:sha(fs.readFileSync(path.join(base,'native-empty/EXPECTED.json'))),sources,results};
const test=async(name,fn,expected)=>{try{const actual=await fn();results.push({id:name,pass:JSON.stringify(actual)===JSON.stringify(expected),expected,actual});}
 catch(e){results.push({id:name,pass:false,error:e.message,detail:e.detail,where:e.where});}};
const refuses=async(name,sql,params,pattern)=>{try{await q(sql,params);results.push({id:name,pass:false,expected_refusal:pattern,actual:'ACCEPTED'});}
 catch(e){results.push({id:name,pass:e.message.includes(pattern),expected_refusal:pattern,error:e.message,detail:e.detail});}};
const event=(id,kind,amount,e,b=e)=>({id,kind,amount,economic_date:e,transaction_date:b,source_sha256:'a'.repeat(64)});
try{
 await ex("set TimeZone='UTC'");await load('source/ISOLATED_TABLES.sql');
 for(const t of['customers','chart_accounts','sales_headers','sales_returns','journal_entries','cash_accounts']){
  if(!await one("select exists(select 1 from pg_constraint where conrelid=$1::regclass and contype='p')",[`erp.${t}`]))await ex(`alter table erp.${t}add primary key(id)`);
 }
 await ex('create schema cp7_sales;create schema auth;');
 const command=fs.readFileSync('/workspace/scratch/9442228ed2dc/erp-d1714/scripts/cp7-src/sales/commands.sql','utf8');
 for(const name of['requests','command_context']){const m=command.match(new RegExp(`create table cp7_sales\\.${name}\\([^;]+;`));if(!m)throw Error('actual context DDL missing');await ex(m[0]);}
 await load('kernel/kernel.sql');await load('ordinal-wrapper/wrapper.sql');
 await load('ledger/01_immutable_facts.proposal.sql');await load('ledger/02_uuid_poster.proposal.sql');await load('source/NO_JOURNAL_SCHEMA_DIFF.proposal.sql');
 await load('source/source.sql');await load('source/member-proof.sql');await load('source/absence-proof.sql');
 const reader=read('readers/01_current_reader_capability.proposal.sql');sources['readers/01_current_reader_capability.proposal.sql']=sha(reader);
 await ex(strip(reader.slice(0,reader.indexOf('-- Narrow capability'))));await load('readers/02_materialized_profile.proposal.sql');
 await load('admission/01_typed_context_and_preclaim.proposal.sql');await load('admission/02_owning_wrapper.proposal.sql');await load('refund/01_initial_refund.proposal.sql');
 for(const name of['01_coordinator_facts.sql','02_initial_projection.sql','03_native_initial_callbacks.sql','04_register_and_materialize.sql','05_factual_profile.sql','06_finish_and_closed_routes.sql'])await load(`coordinator/${name}`);
 const caps=read('coordinator/07_capabilities_and_quote.sql');sources['coordinator/07_capabilities_and_quote.sql']=sha(caps);
 await ex(strip(caps.slice(0,caps.indexOf('-- Explicit private owners'))));await ex(caps.slice(caps.indexOf('do $private_functions$')));
 await ex(caps.match(/do \$role\$[\s\S]*?end \$role\$;/)[0]);
 await load('coordinator/08_outer_wrapper.sql');await load('coordinator/09_public_facades.sql');
 await ex("alter table cp7_payment_correction.links owner to cp7_sales_write;grant usage on schema cp7_payment_correction to cp7_sales_write;");
 const actualLock=execFileSync('python',['-B','-c',"import sys;sys.path.insert(0,'scripts');from cp7_customer_credit.integration.owning_bundle import PAYMENT_LINK_LOCK_SQL;print(PAYMENT_LINK_LOCK_SQL)"],{cwd:repo,encoding:'utf8'});await ex(actualLock);
 await load('native-empty/01_native_empty_facts.sql');await load('native-empty/02_native_empty_callbacks.sql');await load('native-empty/04_exact_overlays.sql');
 results.push({id:'ACTUAL_DDL_AND_14_EXACT_OVERLAYS',pass:true,limit:'Native/Auth/context-capability grants/copy poster not executed or stubbed'});
 await test('ACTUAL_NULL_HUMAN_DATABASE_PRINCIPAL',async()=>{const p=await one('select cp7_credit.native_empty_principal_v1()');await q('select cp7_credit.assert_native_empty_principal_v1($1)',[p]);
  return{kind:p.kind,uid:p.auth_uid,session_user:p.session_user,auth_uid_function_present:p.auth_uid_function_present};},
  {kind:'DATABASE_SESSION',uid:null,session_user:'postgres',auth_uid_function_present:false});
 const p=await one('select cp7_credit.native_empty_principal_v1()');
 await refuses('FAKE_HUMAN_KIND','select cp7_credit.assert_native_empty_principal_v1($1)',[{...p,kind:'AUTHENTICATED_SUBJECT'}],'CP7_NATIVE_EMPTY_PRINCIPAL_BINDING');
 await refuses('FABRICATED_UID_WITHOUT_AUTH','select cp7_credit.assert_native_empty_principal_v1($1)',[{...p,kind:'OTHER_NATIVE_PRINCIPAL',auth_uid:id(99)}],'CP7_NATIVE_EMPTY_PRINCIPAL_BINDING');
 const S=event('S','NET','1000.00','2026-10-18'),R=event('R','NET','-200.00','2026-10-19');
 await test('ALL_CUT_EMPTY_TARGET',async()=>{const k=await one('select ow04_pure_kernel.recognition_plan_v1($1,$2)',[[S,event('P','FUNDING','500.00','2026-10-18')],[R]]);return{k:k.net_current_k,effect:k.has_recognition_effect};},{k:'0.00',effect:false});
 await test('ZERO_CURRENT_K_NONEMPTY_TEMPORAL',async()=>{const k=await one('select ow04_pure_kernel.recognition_plan_v1($1,$2)',[[S,event('P1','FUNDING','500.00','2026-10-18'),event('P2','FUNDING','400.00','2026-10-19'),event('P1I','FUNDING','-500.00','2026-10-20')],[R]]);return{k:k.net_current_k,effect:k.has_recognition_effect,amounts:k.components.map(x=>x.amount)};},
  {k:'0.00',effect:true,amounts:['100.00','-100.00']});
 await test('NO_UNREGISTERED_NATIVE_NOOP',()=>one('select cp7_credit.is_unchanged_native_return_v1($1)',[id(300)]),false);
 await test('NEW_PRIVATE_METADATA',async()=> (await q("select bool_and(p.proowner='postgres'::regrole and p.prosecdef and p.proconfig@>array['TimeZone=UTC'] and not has_function_privilege('authenticated',p.oid,'EXECUTE')and not has_function_privilege('anon',p.oid,'EXECUTE')and not has_function_privilege('service_role',p.oid,'EXECUTE'))ok from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_credit'and p.proname in('native_empty_enter_v1','native_empty_guard_v1','native_empty_complete_v1','native_empty_leave_v1','verify_native_empty_member_v1','assert_native_empty_closed_v1')")).rows[0].ok,true);
 await refuses('NO_NATIVE_AUTHORITY_CAPABILITY_STUB','select cp7_credit.native_empty_enter_v1($1)',[id(300)],'function erp.require_internal() does not exist');
 stage='explicitly synthetic Native-shaped source/registration facts';
 // These inserts are NOT calls to Native writers or registration callbacks.
 // They exercise the actual pure factual/member/current-profile/closure SQL.
 // No context or authority function is replaced by a passing implementation.
 await ex('begin');
 await q("insert into erp.customers(id,customer_code,customer_name)values($1,'SYNTHETIC-NATIVE-EMPTY','Synthetic source only')",[id(10)]);
 for(const[n,name,type,normal]of[[1,'AR','ASSET','DEBIT'],[2,'REVENUE','REVENUE','CREDIT'],[3,'BANK','ASSET','DEBIT'],[4,'FG','ASSET','DEBIT'],[5,'COGS','EXPENSE','DEBIT']])await q(
  'insert into erp.chart_accounts(id,account_code,account_name,account_type,report_group,normal_balance)values($1,$2,$2,$3,$2,$4)',[id(n),name,type,normal]);
 await q("insert into erp.accounting_account_mappings(mapping_key,account_id)values('AR_CUSTOMER',$1)",[id(1)]);
 await q("insert into erp.cash_accounts(id,cash_account_code,cash_account_name,coa_account_id,account_kind)values($1,'BANK','Synthetic bank',$2,'BANK')",[id(50),id(3)]);
 let seq=10000;
 const journal=async(src,type,e,b)=>{const j=id(seq++);await q("insert into erp.journal_entries(id,journal_number,economic_date,transaction_date,posting_at,source_type,source_id,description,status)values($1,$2,$3,$4,$3::date+time'12:00',$5,$6,'Synthetic only','POSTED')",[j,`SYN-${seq}`,e,b,type,src]);return j;};
 const line=async(j,a,d,c,product=null)=>q('insert into erp.journal_lines(id,journal_entry_id,account_id,debit,credit,customer_id,product_id)values($1,$2,$3,$4,$5,$6,$7)',[id(seq++),j,id(a),d,c,id(10),product]);
 const movement=async(item,lot,product,loc,qty,cost,at,type,kind)=>q('insert into erp.fg_stock_movements(id,product_id,lot_id,location_id,movement_type,qty_signed,unit_hpp_snapshot,customer_id,source_type,source_id,physical_at)values($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)',[id(seq++),product,lot,loc,kind,qty,cost,id(10),type,item,at]);
 const hash=p=>one('select ow04_source_proposal.sha($1)',[p]);
 const registerSynthetic=async({root,ret,refund,cost,gross,payment,saleBook='2026-10-18',returnBook='2026-10-19',existing=false})=>{
  const sale=id(root),returnId=id(ret),saleItem=id(root+1),allocation=id(root+2),product=id(root+3),lot=id(root+4),loc=id(root+5),ri=id(ret+1);
  if(!existing){
   await q("insert into erp.sales_headers(id,sale_number,customer_id,sale_date,status)values($1,$2,$3,'2026-10-18 01:00Z',$4)",[sale,`S-${root}`,id(10),payment?'PARTIAL_PAID':'POSTED']);
   await q('insert into erp.sales_items(id,sale_id,product_id,qty_pcs,unit_price_snapshot)values($1,$2,$3,4,$4)',[saleItem,sale,product,gross/4]);
   await q('insert into erp.sale_stock_allocations(id,sale_item_id,lot_id,location_id,qty_pcs,unit_hpp_snapshot)values($1,$2,$3,$4,4,$5)',[allocation,saleItem,lot,loc,cost]);
   await movement(saleItem,lot,product,loc,-4,cost,'2026-10-18 01:00Z','SALE_ITEM','SALE');
   if(gross||cost){const j=await journal(sale,'SALE','2026-10-18',saleBook);if(gross){await line(j,1,gross,0);await line(j,2,0,gross);}if(cost){await line(j,5,4*cost,0,product);await line(j,4,0,4*cost,product);}}
   if(payment){const pay=id(root+6);await q("insert into erp.sales_payments(id,sale_id,payment_number,payment_date,amount,cash_account_id,payment_method,status)values($1,$2,$3,'2026-10-18 02:00Z',$4,$5,'TRANSFER','POSTED')",[pay,sale,`P-${root}`,payment,id(50)]);
    const j=await journal(pay,'SALES_PAYMENT','2026-10-18','2026-10-18');await line(j,3,payment,0);await line(j,1,0,payment);
    await q(`insert into erp.sales_payment_posting_facts(payment_id,sale_id,customer_id,payment_number,payment_date,amount,cash_account_id,original_journal_entry_id,journal_economic_date,journal_transaction_date,journal_posting_at,payment_snapshot,lineage_sha256)
     select p.id,p.sale_id,$2,p.payment_number,p.payment_date,p.amount,p.cash_account_id,j.id,j.economic_date,j.transaction_date,j.posting_at,to_jsonb(p)-'status',
     ow04_source_proposal.native_sha(jsonb_build_array(p.id,p.sale_id,$2::uuid,p.payment_number,p.payment_date,p.amount,p.cash_account_id,j.id,j.economic_date,j.transaction_date,j.posting_at,p.replaces_payment_id,null,to_jsonb(p)-'status'))
     from erp.sales_payments p join erp.journal_entries j on j.source_type='SALES_PAYMENT'and j.source_id=p.id where p.id=$1`,[pay,id(10)]);
   }
  }
  await q("insert into erp.sales_returns(id,return_number,sale_id,customer_id,physical_at,status)values($1,$2,$3,$4,'2026-10-19 01:00Z','DRAFT')",[returnId,`R-${ret}`,sale,id(10)]);
  await q('insert into erp.sales_return_items(id,return_id,product_id,lot_id,location_id,qty_pcs,unit_hpp_snapshot,refund_amount,sale_stock_allocation_id)values($1,$2,$3,$4,$5,1,$6,$7,$8)',[ri,returnId,product,lot,loc,cost,refund,allocation]);
  const source=await one('select ow04_source_proposal.locked_source_family($1)',[sale]);if(source.source_status!=='BASE_COLLECTED')throw Error('synthetic before source blocked '+JSON.stringify(source.blockers));
  const before=await one('select cp7_credit.initial_base_events_v1($1)',[sale]);
  const draft=await one('select cp7_credit.native_empty_draft_v1($1)',[returnId]);
  const prior=await one('select cp7_credit.native_empty_prior_v1($1)',[sale]);
  const preserved=await one('select cp7_credit.initial_preserved_source_v1($1,$2)',[sale,returnId]);
  const projected=refund?[{id:`projected-native-return:${returnId}`,kind:'NET',amount:`-${refund}.00`,economic_date:'2026-10-19',transaction_date:returnBook,source_sha256:await hash(draft)}]:[];
  const projectedK=await one('select ow04_pure_kernel.recognition_plan_v1($1,$2)',[before,projected]);
  await q("update erp.sales_returns set status='POSTED'where id=$1",[returnId]);await movement(ri,lot,product,loc,1,cost,'2026-10-19 01:00Z','SALES_RETURN_ITEM','SALE_RETURN');
  let j=null;if(refund||cost){j=await journal(returnId,'SALES_RETURN','2026-10-19',returnBook);if(refund){await line(j,2,refund,0);await line(j,1,0,refund);}if(cost){await line(j,4,cost,0,product);await line(j,5,0,cost,product);}}
  const fact=await one('select ow04_source_proposal.return_fact_v1($1)',[returnId]);const physical=await one('select cp7_credit.native_empty_physical_v1($1)',[returnId]);
  const events=await one('select cp7_credit.actual_own_return_events_v1($1)',[returnId]);const k=await one('select ow04_pure_kernel.recognition_plan_v1($1,$2)',[before,events]);
  const principal=await one('select cp7_credit.native_empty_principal_v1()');const op=id(seq++),family=id(seq++),marker=id(seq++);
  const ord=Number(await one('select coalesce(max(family_ordinal),0)+1 from cp7_credit.return_families where family_root_sale_id=$1',[sale]));
  const previous=(await q('select id from cp7_credit.return_families where family_root_sale_id=$1 and family_ordinal=$2',[sale,ord-1])).rows[0]?.id??null;
  const assignment={contract_version:'ow04.native-empty-return-family-assignment.v1',origin:'NATIVE_RETURN',operation_id:op,family_id:family,family_root_sale_id:sale,family_ordinal:String(ord),first_return_id:returnId,previous_family_id:previous,principal_sha256:await hash(principal),source_sha256:await hash(source)};
  await q("insert into cp7_credit.return_families(id,family_root_sale_id,family_ordinal,first_return_id,assignment_kind,assignment_proof,source_sha256,actor,request_id)values($1,$2,$3,$4,'NEW_POST',$5,$6,null,null)",[family,sale,ord,returnId,assignment,await hash(assignment)]);
  const member={contract_version:'ow04.actual-return-family-member.v1',family_id:family,family_root_sale_id:sale,return_id:returnId,sale_id:sale,member_kind:'ORIGINAL',predecessor_return_id:null,native_lineage_id:null,return_item_lineage:{},financial_state:fact.financial_state,source_journal_id:fact.source_journal_id,financial_source_sha256:fact.financial_source_sha256,no_journal_proof:fact.no_journal_proof};
  // Actual SQL callback stores fact->'no_journal_proof': JSON null for a real
  // journal. The first driver run incorrectly supplied SQL NULL instead.
  await q("insert into cp7_credit.return_family_members(family_id,return_id,member_kind,source_journal_id,source_sha256,actual_lineage_snapshot,actor,request_id,financial_state,financial_source_proof)values($1,$2,'ORIGINAL',$3,$4,$5,null,null,$6,coalesce($7::jsonb,'null'::jsonb))",[family,returnId,j,await hash(member),member,fact.financial_state,fact.no_journal_proof]);
  const objects=(await q("select cp7_credit.materialized_fact('FAMILY',f.id,to_jsonb(f))x from cp7_credit.return_families f where id=$1 union all select cp7_credit.materialized_fact('MEMBER',m.return_id,to_jsonb(m))from cp7_credit.return_family_members m where return_id=$2",[family,returnId])).rows.map(x=>x.x).sort((a,b)=>a.object_kind.localeCompare(b.object_kind));
  const journalPayload=j?await one('select cp7_credit.materialized_journal_payload($1)',[j]):null;
  await q(`insert into cp7_credit.native_empty_operations(operation_id,source_return_id,source_sale_id,family_id,family_ordinal,backend_pid,transaction_id,principal,principal_sha256,draft_manifest,draft_sha256,source_snapshot,source_sha256,preserved_source,before_events,prior_causal,period_snapshot,projected_events,projected_kernel,actual_fact,actual_physical,actual_events,actual_kernel,actual_original_journal,assignment_proof,materialization_id,actual_objects,actual_objects_sha256)
   values($1,$2,$3,$4,$5,pg_backend_pid(),txid_current(),$6,$7,$8,$9,$10,$11,$12,$13,$14,'{"classification":"SYNTHETIC_NO_NATIVE_PERIOD_CALL"}',$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25)`,
   [op,returnId,sale,family,ord,principal,await hash(principal),draft,await hash(draft),source,await hash(source),preserved,before,prior,projected,projectedK,fact,physical,events,k,journalPayload,assignment,marker,objects,await hash(objects)]);
  await q("insert into cp7_credit.financial_materializations(id,root_sale_id,actor,request_id,request_ordinal,owning_action,payload_sha256,source_plan_sha256,actual_objects,actual_objects_sha256)values($1,$2,null,null,1,'NATIVE_EMPTY_RETURN',$3,$4,$5,$6)",[marker,sale,await hash(draft),await hash(k),objects,await hash(objects)]);
  for(const x of objects)await q('insert into cp7_credit.financial_materialization_objects(object_kind,object_id,materialization_id,fact_sha256)values($1,$2,$3,$4)',[x.object_kind,x.object_id,marker,x.fact_sha256]);
  const net=Number(await one("select (select coalesce(sum(line_total),0)from erp.sales_items where sale_id=$1)-(select coalesce(sum(i.refund_amount),0)from erp.sales_returns r join erp.sales_return_items i on i.return_id=r.id where r.sale_id=$1 and r.status='POSTED')",[sale]));
  const status=payment===net?'PAID':payment?'PARTIAL_PAID':'POSTED';await q('update erp.sales_headers set status=$2 where id=$1',[sale,status]);
  const completed={contract_version:'ow04.native-empty-return-completion.v1',operation_id:op,source_sale_id:sale,source_return_id:returnId,return_status:'POSTED',header_status:status,net_after:`${net}.00`,raw_paid:`${payment}.00`,actual_fact:fact,principal_sha256:await hash(principal),assignment_sha256:await hash(assignment),materialization_id:marker};
  await q('insert into cp7_credit.native_empty_completions(operation_id,final_manifest,final_manifest_sha256)values($1,$2,$3)',[op,completed,await hash(completed)]);
  return{sale,returnId,family,op,marker,j,ri,events,prior,net,payment};
 };
 const first=await registerSynthetic({root:100,ret:300,refund:20,cost:10,gross:80,payment:30});
 await test('SYNTHETIC_NULL_HUMAN_MEMBER_PROOF',async()=>{const v=await one('select ow04_source_proposal.verify_return_member_v1($1)',[first.returnId]);return{kind:v.principal_kind,ordinal:v.family_ordinal,state:v.financial_state};},{kind:'DATABASE_SESSION',ordinal:'1',state:'JOURNAL'});
 await test('SYNTHETIC_SHARED_CURRENT_E',()=>one('select cp7_credit.current_effective_paid($1)::text',[first.sale]),'30.00');
 await test('SYNTHETIC_NO_CP7_ENVELOPE_OR_CREDIT',async()=> (await q('select (select count(*)::int from cp7_sales.requests)requests,(select count(*)::int from cp7_credit.cohorts)cohorts,(select count(*)::int from cp7_credit.recognition_plans)plans,(select count(*)::int from cp7_credit.execution_context)contexts')).rows[0],{requests:0,cohorts:0,plans:0,contexts:0});
 await test('SYNTHETIC_CONTEXT_FREE_CLOSURE_NO_AUTH',async()=>{await q('select cp7_credit.assert_native_empty_closed_v1($1)',[first.op]);return'VALID';},'VALID');
 const second=await registerSynthetic({root:100,ret:310,refund:10,cost:10,gross:80,payment:30,existing:true});
 await test('SYNTHETIC_SECOND_EMPTY_APPEND',async()=>{const a=await one('select ow04_source_proposal.verify_return_member_v1($1)',[first.returnId]);const b=await one('select ow04_source_proposal.verify_return_member_v1($1)',[second.returnId]);return[a.family_ordinal,b.family_ordinal];},['1','2']);
 const noJ=await registerSynthetic({root:1000,ret:1300,refund:0,cost:0,gross:0,payment:0});
 await test('SYNTHETIC_TYPED_ABSENCE_AND_NO_JOURNAL',async()=>{const v=await one('select ow04_source_proposal.verify_return_member_v1($1)',[noJ.returnId]);return{state:v.financial_state,j:v.source_journal_id,floor:v.causal_book_floor,prior:noJ.prior.state,event_count:noJ.events.length};},{state:'NO_JOURNAL',j:null,floor:null,prior:'PROVEN_ABSENT',event_count:0});
 const hpp=await registerSynthetic({root:2000,ret:2300,refund:0,cost:10,gross:0,payment:0,saleBook:'2026-10-20',returnBook:'2026-10-20'});
 await test('SYNTHETIC_HPP_ONLY_REOPENED_CAUSAL_PAIR',async()=>{const v=await one('select ow04_source_proposal.verify_return_member_v1($1)',[hpp.returnId]);return{state:v.financial_state,floor:v.causal_book_floor,event_amount:hpp.events[0].amount,economic:hpp.events[0].economic_date,book:hpp.events[0].transaction_date};},
  {state:'JOURNAL',floor:'2026-10-20',event_amount:'0.00',economic:'2026-10-19',book:'2026-10-20'});
 for(const[name,mutate,sql,params,pattern]of[
  ['ALTERED_ACTUAL_PHYSICAL',()=>q('update erp.fg_stock_movements set qty_signed=2 where source_type=\'SALES_RETURN_ITEM\'and source_id=$1',[first.ri]),'select cp7_credit.verify_native_empty_member_v1($1)',[first.returnId],'CP7_NATIVE_EMPTY_ACTUAL_PHYSICAL_PROOF'],
  ['RETURN_JOURNAL_PRECEDES_ECONOMIC',()=>q("update erp.journal_entries set transaction_date='2026-10-18'where id=$1",[first.j]),'select cp7_credit.verify_native_empty_member_v1($1)',[first.returnId],'OW04_MEMBER_ORIGINAL_JOURNAL_PAIR_OR_STATE_CHANGED'],
  ['WRONG_RETURN_ORIGINAL_JOURNAL_SOURCE',()=>q("update erp.journal_entries set source_type='SYNTHETIC_BROKEN_SOURCE'where id=$1",[first.j]),'select cp7_credit.verify_native_empty_member_v1($1)',[first.returnId],'OW04_MEMBER_ORIGINAL_JOURNAL_MISSING_OR_DUPLICATE'],
  ['NOJ_WITH_EXTRA_FINANCIAL_JOURNAL',()=>journal(noJ.returnId,'SALES_RETURN','2026-10-19','2026-10-19'),'select cp7_credit.verify_native_empty_member_v1($1)',[noJ.returnId],'OW04_MEMBER_ORIGINAL_UNBALANCED']
 ]){await ex('savepoint negative');await mutate();await refuses(name,sql,params,pattern);await ex('rollback to negative');await ex('release negative');}
 await ex('savepoint wrong_status');await q("update erp.sales_headers set status='PAID'where id=$1",[first.sale]);
 await refuses('CURRENT_HEADER_STATUS_MISMATCH','select cp7_credit.assert_native_empty_closed_v1($1)',[first.op],'CP7_NATIVE_EMPTY_FINAL_AR_OR_STATUS');await ex('rollback to wrong_status');await ex('release wrong_status');
 await test('ALL_SYNTHETIC_FACTS_DEFERRED_CLOSURE',async()=>{await ex('set constraints all immediate');return'VALID';},'VALID');
 await ex('rollback');
 stage='complete';result.status=results.every(x=>x.pass)?'PASS':'FAIL';
}catch(e){result.status='FAIL';result.setup_error={stage,message:e.message,detail:e.detail,where:e.where,position:e.position,internalQuery:e.internalQuery};}
result.stage=stage;
const output=JSON.stringify(result,null,2)+'\n';
if(result.status!=='PASS'&&!fs.existsSync(path.join(dir,'FIRST_FAILURE.json')))fs.writeFileSync(path.join(dir,'FIRST_FAILURE.json'),output);
fs.writeFileSync(path.join(dir,'RESULT.json'),output);
console.log(JSON.stringify({status:result.status,stage,checks:results.length,failures:results.filter(x=>!x.pass).map(x=>x.id),setup_error:result.setup_error??null,native_execution_proven:false}));
await db.close();if(result.status!=='PASS')process.exitCode=1;
