// Execute the exact parent/current coordinator and exact unchanged BE reverse
// and dispatcher. Auth, stock inverse and ledger tables below are explicit
// local doubles: this proves guard placement, not actual Native money/Auth.
import {readFileSync, writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {resolve, dirname} from 'node:path';
const modulePath=process.env.F04_PGLITE_MODULE;
if(!modulePath)throw new Error('F04_PGLITE_MODULE must name an explicit local PGlite runtime; no green skip');
const {PGlite}=await import(modulePath);

const here=dirname(fileURLToPath(import.meta.url)),root=resolve(here,'../..');
const sha=s=>createHash('sha256').update(s).digest('hex');
const current=readFileSync(resolve(root,'scripts/cp7_sku_pair_conversion/conversion.sql'),'utf8');
const before=readFileSync(resolve(here,'evidence/BEFORE_conversion.sql'),'utf8');
function native(path,name){
 const text=readFileSync(resolve(root,path),'utf8');
 const start=text.indexOf(`CREATE OR REPLACE FUNCTION ${name}(`);
 assert(start>=0,`missing Native ${name}`);
 const end=text.indexOf('$function$;',start);assert(end>start);
 return text.slice(start,end+'$function$;'.length);
}
function coordinator(text){
 const start=text.indexOf('create function cp7_sku_conversion.action_v1(');
 const end=text.indexOf('end $$;',start);assert(start>=0&&end>start);
 return text.slice(start,end+'end $$;'.length).replace('create function','create or replace function');
}
const be=native('scripts/cp6_be_objects_rework.sql','erp.be_reverse_conversion_v1');
const dispatcher=native('scripts/cp6_be_objects_conversion.sql','erp.save_product_conversion_action_v1');
const groupGuard=current.slice(current.indexOf('create function cp7_sku_conversion.assert_group_reverse_v1('),current.indexOf('create function cp7_sku_conversion.stock_v1('));
const validatorFile=readFileSync(resolve(root,'supabase/migrations/20260901023000_erp_v2_6_14_attendance_hpp_sewing_terminal_foundation.sql'),'utf8');
const vi=validatorFile.indexOf('create or replace function erp._cp3_assert_closed_json_object(');
const validator=validatorFile.slice(vi,validatorFile.indexOf('$function$;',vi)+'$function$;'.length);
assert(vi>=0&&validator.endsWith('$function$;'));
const db=new PGlite();
const u=n=>`10000000-0000-4000-8000-${String(n).padStart(12,'0')}`;
const g=u(1),c1=u(11),c2=u(12),d1=u(21),d2=u(22),doc=u(31),outstanding=u(41);
const j=x=>`'${JSON.stringify(x).replaceAll("'","''")}'::jsonb`;
const one=async sql=>(await db.query(sql)).rows[0];
const value=async sql=>Object.values(await one(`select ${sql}`))[0];
const results=[];
const record=(id,detail)=>results.push({id,status:'PASS',...detail});
const call=(request=u(71))=>value(`cp7_sku_conversion.action_v1('REVERSE',${j({conversion_id:c1,reason:'Seluruh grup dibatalkan'})},'${request}')`);
const census=async()=>value(`jsonb_build_object(
 'tables',(select jsonb_object_agg(n,v order by n)from(
  select 'conversions' n,(select jsonb_agg(to_jsonb(x)order by id)from erp.product_conversions x)v union all
  select 'allocations',(select jsonb_agg(to_jsonb(x)order by conversion_id)from erp.product_conversion_allocations x)union all
  select 'sources',(select jsonb_agg(to_jsonb(x)order by conversion_id)from erp.be_conversion_sources_v1 x)union all
  select 'cost_sources',(select jsonb_agg(to_jsonb(x)order by conversion_id)from erp.be_conversion_cost_sources_v1 x)union all
  select 'documents',(select jsonb_agg(to_jsonb(x)order by id)from erp.bc_documents_v1 x)union all
  select 'returns',(select jsonb_agg(to_jsonb(x)order by conversion_id)from erp.be_conversion_returns_v1 x)union all
  select 'return_lots',(select jsonb_agg(to_jsonb(x)order by outstanding_id)from erp.bc_return_lots_v1 x)union all
  select 'outstanding',(select jsonb_agg(to_jsonb(x)order by id)from erp.bc_outstanding_returns_v1 x)union all
  select 'downstream',(select jsonb_agg(to_jsonb(x)order by lot_id)from erp.test_downstream x)union all
  select 'groups',(select jsonb_agg(to_jsonb(x)order by request_id)from cp7_sku_conversion.groups_v1 x)union all
  select 'members',(select jsonb_agg(to_jsonb(x)order by conversion_id)from cp7_sku_conversion.members_v1 x)union all
  select 'execution',(select jsonb_agg(to_jsonb(x))from cp7_sku_conversion.execution_v1 x)union all
  select 'native_context',(select jsonb_agg(to_jsonb(x))from erp.be_execution_context_v1 x)union all
  select 'requests',(select jsonb_agg(to_jsonb(x)order by namespace,id)from erp.test_requests x)union all
  select 'movements',(select jsonb_agg(to_jsonb(x)order by order_seq)from erp.fg_stock_movements x)union all
  select 'audit',(select jsonb_agg(to_jsonb(x)order by id)from erp.audit_logs x)
  union all select 'journals',(select jsonb_agg(to_jsonb(x)order by source_id)from erp.journal_entries x)
 )s),
 'sequences',jsonb_build_object('audit',(select jsonb_build_object('last_value',last_value,'is_called',is_called)from erp.audit_logs_id_seq),'stock',(select jsonb_build_object('last_value',last_value,'is_called',is_called)from erp.fg_stock_book_order_seq)),
 'session',jsonb_build_object('role',current_role,'search_path',current_setting('search_path'),'timezone',current_setting('TimeZone'),'reason',current_setting('app.change_reason',true)))`);
async function refusal(id,expected){
 const a=await census();let err;
 try{await call();}catch(e){err=e;}
 assert(err,`${id}: expected refusal`);assert.match(err.message,expected);
 const b=await census();assert.deepEqual(b,a,`${id}: local all-row, all-sequence and session no-effect`);
 record(id,{message:err.message,complete_local_census_equal:true,before_sha256:sha(JSON.stringify(a)),after_sha256:sha(JSON.stringify(b))});
}
try{
 await db.exec(`create schema erp;create schema cp7_sku_conversion;
 create table erp.test_actor(id uuid,role_name text,permissions text[]);insert into erp.test_actor values('${u(90)}','OWNER',array['warehouse.brand_conversion.view','warehouse.brand_conversion.reverse']);
 create function erp.current_app_user_id()returns uuid language sql stable as $$select id from erp.test_actor$$;
 create function erp.require_permission(p text)returns void language plpgsql as $$begin if not coalesce((select p=any(permissions)from erp.test_actor),false)then raise exception '42501 ACCESS_DENIED';end if;end$$;
 create function erp.require_owner_admin()returns void language plpgsql as $$begin if(select role_name from erp.test_actor)not in('OWNER','ADMIN')then raise exception 'OWNER_ADMIN_REQUIRED';end if;end$$;
 create function erp.require_internal()returns void language plpgsql as $$begin if erp.current_app_user_id()is null then raise exception 'AUTH_REQUIRED';end if;end$$;
 create function erp.pocket_period_lock_v1()returns void language sql as $$select$$;
 create function erp.bc_text_v1(p jsonb,k text,required boolean,max_length int)returns text language plpgsql as $$begin if(required and nullif(btrim(p->>k),'')is null)or length(p->>k)>max_length then raise exception 'TEXT_REQUIRED';end if;return p->>k;end$$;
 create function erp.bd_uuid_v1(p jsonb,k text,required boolean)returns uuid language plpgsql as $$begin if required and p->>k is null then raise exception 'UUID_REQUIRED';end if;return(p->>k)::uuid;end$$;
 create table erp.product_conversions(id uuid primary key,status text not null);
 create table erp.product_conversion_allocations(conversion_id uuid primary key,destination_lot_id uuid not null,qty_pcs int,original_hpp_per_pcs numeric(24,6));
 create table erp.journal_entries(source_type text,source_id uuid,status text);
 create table erp.be_conversion_sources_v1(conversion_id uuid primary key);
 create table erp.be_conversion_cost_sources_v1(conversion_id uuid,document_id uuid);
 create table erp.bc_documents_v1(id uuid primary key,status text);
 create table erp.be_conversion_returns_v1(conversion_id uuid,outstanding_id uuid);
 create table erp.bc_return_lots_v1(outstanding_id uuid,document_id uuid);
 create table erp.bc_outstanding_returns_v1(id uuid primary key,status text);
 create table erp.test_downstream(lot_id uuid primary key);
 create function erp.fg_lot_has_active_downstream(p uuid,a text,b text,c uuid)returns boolean language sql stable as $$select exists(select 1 from erp.test_downstream where lot_id=p)$$;
 create sequence erp.fg_stock_book_order_seq;
 create table erp.fg_stock_movements(order_seq bigint primary key default nextval('erp.fg_stock_book_order_seq'),conversion_id uuid,qty_signed integer,reversal_of_id bigint);
 create table erp.audit_logs(id bigserial primary key,entity_type text,entity_id uuid,action text,new_data jsonb,changed_by uuid,change_reason text);
 create table erp.be_execution_context_v1(backend_pid integer,transaction_id bigint,request_id uuid);
 create table cp7_sku_conversion.groups_v1(request_id uuid primary key,actor uuid,payload jsonb);
 create table cp7_sku_conversion.members_v1(conversion_id uuid primary key,group_id uuid,line_no int);
 create table cp7_sku_conversion.execution_v1(backend_pid int,transaction_id bigint,group_id uuid,mode text,primary key(backend_pid,transaction_id));
 create table erp.test_requests(namespace text,id uuid,hash text,response jsonb,primary key(namespace,id));
 create function erp._request_hash(p jsonb)returns text language sql immutable as $$select md5(p::text)$$;
 create function erp._idempotency_begin(n text,r uuid,h text)returns jsonb language plpgsql as $$declare x erp.test_requests%rowtype;begin
  insert into erp.test_requests values(n,r,h,null)on conflict do nothing;select *into strict x from erp.test_requests where namespace=n and id=r;
  if x.hash<>h then raise exception 'REQUEST_REUSED';end if;return x.response;end$$;
 create function erp._idempotency_complete(n text,r uuid,v jsonb)returns jsonb language plpgsql as $$begin update erp.test_requests set response=v where namespace=n and id=r;return v;end$$;
 create function erp.reverse_product_conversion(p_id uuid,p_reason text)returns void language plpgsql as $$declare c erp.product_conversions%rowtype;x record;begin
  perform cp7_sku_conversion.assert_group_reverse_v1(p_id);select *into strict c from erp.product_conversions where id=p_id for update;
  if c.status='REVERSED'then return;end if;
  if c.status<>'POSTED'then raise exception 'Hanya conversion/rebrand POSTED yang dapat direverse';end if;
  if exists(select 1 from erp.product_conversion_allocations a where a.conversion_id=p_id and erp.fg_lot_has_active_downstream(a.destination_lot_id,'REBRAND_IN','PRODUCT_CONVERSION',p_id))then raise exception 'Hasil conversion/rebrand masih dipakai transaksi downstream aktif. Reverse transaksi downstream terlebih dahulu.';end if;
  for x in select *from erp.fg_stock_movements where conversion_id=p_id and reversal_of_id is null loop
   insert into erp.fg_stock_movements(conversion_id,qty_signed,reversal_of_id)values(p_id,-x.qty_signed,x.order_seq);end loop;
  update erp.product_conversions set status='REVERSED'where id=p_id;
 end$$;
 insert into erp.product_conversions values('${c1}','POSTED'),('${c2}','POSTED');
 insert into erp.product_conversion_allocations values('${c1}','${d1}',3,10.01),('${c2}','${d2}',1,20.02);
 insert into erp.journal_entries values('PRODUCT_CONVERSION','${c1}','POSTED'),('PRODUCT_CONVERSION','${c2}','POSTED');
 insert into erp.be_conversion_sources_v1 values('${c1}'),('${c2}');
 insert into cp7_sku_conversion.groups_v1 values('${g}','${u(90)}','{}');
 insert into cp7_sku_conversion.members_v1 values('${c1}','${g}',1),('${c2}','${g}',2);
 insert into erp.fg_stock_movements(conversion_id,qty_signed)values('${c1}',-3),('${c1}',3),('${c2}',-1),('${c2}',1);
 select set_config('app.change_reason','Local initial reason',false);`);
 await db.exec(validator+groupGuard+be+dispatcher+coordinator(before));
 await db.exec(`insert into erp.bc_documents_v1 values('${doc}','POSTED');insert into erp.be_conversion_cost_sources_v1 values('${c1}','${doc}');`);
 const a=await census();let oldError;
 try{await call();}catch(e){oldError=e;}
 assert.match(oldError?.message||'',/BE_REVERSE_DEPENDANTS/);
 const b=await census();assert.deepEqual(a.tables,b.tables);assert.deepEqual(a.session,b.session);
 assert.notDeepEqual(a.sequences,b.sequences);assert.notDeepEqual(a.sequences.audit,b.sequences.audit);
 assert(b.sequences.stock.last_value>a.sequences.stock.last_value);
 record('BEFORE_FIRST_MEMBER_ACTIVE_COST',{expected_first_failure:true,error:oldError.message,rows_restored:true,session_restored:true,sequences_restored:false,before:a.sequences,after:b.sequences});
 await db.exec(coordinator(current));
 await refusal('ALL_MEMBER_ACTIVE_COST',/BE_REVERSE_DEPENDANTS:.*sumber biaya/);
 await db.exec(`update erp.bc_documents_v1 set status='REVERSED';insert into erp.bc_documents_v1 values('${u(32)}','POSTED');insert into erp.bc_outstanding_returns_v1 values('${outstanding}','OPEN');insert into erp.be_conversion_returns_v1 values('${c1}','${outstanding}');insert into erp.bc_return_lots_v1 values('${outstanding}','${u(32)}');`);
 await refusal('ALL_MEMBER_ACTIVE_RETURN',/BE_REVERSE_DEPENDANTS:.*penerimaan bongkaran/);
 await db.exec(`update erp.bc_documents_v1 set status='REVERSED';insert into erp.test_downstream values('${d1}');`);
 await refusal('ALL_MEMBER_ACTIVE_DOWNSTREAM',/Hasil conversion\/rebrand masih dipakai/);
 await db.exec(`delete from erp.test_downstream;delete from erp.be_conversion_sources_v1 where conversion_id='${c1}';`);
 await refusal('ALL_MEMBER_MISSING_BE_SOURCE',/BE_DOCUMENT_NOT_FOUND/);
 await db.exec(`insert into erp.be_conversion_sources_v1 values('${c1}');update erp.product_conversions set status='DRAFT'where id='${c1}';`);
 await refusal('ALL_MEMBER_INVALID_NATIVE_STATUS',/Hanya conversion\/rebrand POSTED/);
 await db.exec(`update erp.product_conversions set status='POSTED';update erp.journal_entries set status='REVERSED'where source_id='${c1}';`);
 await refusal('ALL_MEMBER_MISSING_NATIVE_JOURNAL',/Jurnal conversion\/rebrand tidak ditemukan/);
 await db.exec(`update erp.journal_entries set status='POSTED';`);
 const positive=await call();assert.equal(positive.status,'REVERSED');assert.deepEqual(positive.conversion_ids,[c2,c1]);
 assert.equal(await value("(select count(*)from erp.product_conversions where status='REVERSED')"),2);
 assert.equal(await value('(select count(*)from erp.fg_stock_movements where reversal_of_id is not null)'),4);
 assert.equal(Number(await value('(select sum(qty_signed)from erp.fg_stock_movements)')),0);
 assert.equal(await value('(select count(*)from cp7_sku_conversion.execution_v1)'),0);
 assert.equal(await value('(select count(*)from erp.be_execution_context_v1)'),0);
 assert.equal(await value('(select count(*)from erp.audit_logs)'),2);
 assert.equal(await value(`(select status from erp.bc_outstanding_returns_v1 where id='${outstanding}')`),'CANCELLED');
 record('RELEASED_DEPENDENCIES_ALLOW_WHOLE_GROUP',{response:positive,real_local_inverse_rows:4,local_pcs_net:0,native_implementation:'UNCHANGED_BE_AND_DISPATCHER_WITH_DECLARED_STOCK_INVERSE_DOUBLE'});
 const replayBefore=await census();assert.deepEqual(await call(),positive);assert.deepEqual(await census(),replayBefore);
 record('EXACT_UUID_REPLAY',{all_local_rows_sequences_session_equal:true});
 const directBefore=await census();let directError;
 try{await value(`erp.be_reverse_conversion_v1('${c1}','Partial inverse outside group')`);}catch(e){directError=e;}
 assert.match(directError?.message||'',/CP7_SKU_GROUP_REVERSE_REQUIRED/);assert.deepEqual(await census(),directBefore);
 record('DIRECT_MEMBER_REVERSE_REMAINS_REFUSED',{all_local_rows_sequences_session_equal:true,error:directError.message});
 const report={status:'PASS',count:results.length,proof_kind:'PGLITE_DECLARED_LOCAL_DOUBLES_NOT_NATIVE_MONEY_AUTH_OR_FULL_RESTORE',source:{before_conversion:sha(before),conversion:sha(current),unchanged_BE_reverse:sha(be),unchanged_BE_dispatcher:sha(dispatcher)},cases:results,production_go:false,independent_acceptance:false};
 writeFileSync(resolve(here,'evidence/LOCAL_GUARD.json'),JSON.stringify(report,null,2)+'\n');
 process.stdout.write(JSON.stringify({status:report.status,count:report.count,proof_kind:report.proof_kind})+'\n');
}finally{await db.close();}
