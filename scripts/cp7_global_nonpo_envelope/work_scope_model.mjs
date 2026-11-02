// New private scope lifecycle only. Native owner phases, Auth/current rights,
// inspector, barrier and base constraints are EXPLICIT MODELS. No ERP execution.
import assert from 'node:assert/strict';
import {readFile,writeFile}from'node:fs/promises';
import{fileURLToPath,pathToFileURL}from'node:url';
import{createHash}from'node:crypto';
const[runtime,output]=process.argv.slice(2);assert(runtime&&output);
const{PGlite}=await import(pathToFileURL(runtime).href),db=new PGlite();
const here=fileURLToPath(new URL('.',import.meta.url)),results=[];
const id=n=>'40000000-0000-4000-8000-'+String(n).padStart(12,'0');
const actor=id(1),root=id(2),profile='a'.repeat(64),basis='b'.repeat(64);
const scalar=async(sql,args=[])=>Object.values((await db.query(sql,args)).rows[0])[0];
let sequence=10;
const modelTable=op=>op==='D1'?'cp7_credit_correction_de.work_v1':op==='E'?'cp7_credit_note_carry_de.work_v1':'cp7_credit.source_operation_work_v1';
const baseOutside={facts:{BE_context_rows:[],inventory_balances:[{id:id(3),qty:'7',value:'140.00'}]},identity_domain:{product_ids:[id(3)]},sha256:'d'.repeat(64),keyset:{inventory_balances:1}};
async function transaction(fn,commit=false){await db.exec('BEGIN');try{const v=await fn();await db.exec(commit?'COMMIT':'ROLLBACK');return v;}catch(e){await db.exec('ROLLBACK');throw e;}}
async function refused(label,fn,message,code='P0001'){
 let error;try{await transaction(fn);}catch(e){error=e;}
 assert(error,label+': refusal required');assert.equal(error.code,code,label+': SQLSTATE');assert(error.message.includes(message),label+': '+error.message);
 results.push({label,result:'REFUSED_AS_REQUIRED',SQLSTATE:error.code,error:message});
}
const counts=()=>scalar("select jsonb_build_object('open',(select count(*)from cp7_global_nonpo_envelope.work_scopes_v1),'closed',(select count(*)from cp7_global_nonpo_envelope.scope_completions_v1))");
const bind=(op,n,review=op==='SOURCE'?null:basis)=>scalar('select cp7_global_nonpo_envelope.bind_v1($1,$2,$3,$4)',[op,n,profile,review]);
const finish=(op,n)=>scalar('select cp7_global_nonpo_envelope.finish_v1($1,$2)',[op,n]);
async function owner(op='D1'){
 const n=id(++sequence),request=id(++sequence),table=modelTable(op),rootColumn=op==='E'?'source_sale_id':'sale_id',authorityColumn=op==='SOURCE'?'authority_snapshot':'authority';
 const cols=['operation_id','backend_pid','transaction_id','actor','request_id',rootColumn,'payload','expected_version','phase',authorityColumn];
 const values=['$1','pg_backend_pid()','txid_current()','$2','$3','$4',"'{\"sale_id\":\""+root+"\",\"change_reason\":\"MODEL OWNED INTENT\"}'::jsonb","'5'","'PREPARED'","jsonb_build_object('actor',auth.uid(),'epoch','1')"];
 if(op==='SOURCE'){cols.push('action');values.push("'RETURN_REVERSE'");}
 await db.query('insert into '+table+'('+cols.join(',')+')values('+values.join(',')+')',[n,actor,request,root]);
 return{op,n,request,table};
}
const completeOwner=async x=>db.query('update '+x.table+' set phase=$1 where operation_id=$2',[x.op==='SOURCE'?'NATIVE_COMPLETE':'MATERIALIZED',x.n]);
try{
 await db.exec(`create role anon;create role authenticated;create role service_role;
  create schema auth;create schema cp7_model;create schema cp7_credit_correction_de;
  create schema cp7_credit_note_carry_de;create schema cp7_credit;
  create schema cp7_sales_return_correction;create schema cp7_note;create schema cp7_sales;
  create schema cp7_global_nonpo_native_graph;
  create function auth.uid()returns uuid language sql stable as $$select nullif(current_setting('model.actor',true),'')::uuid$$;
  create function auth.jwt()returns jsonb language sql stable as $$select jsonb_build_object('role',coalesce(nullif(current_setting('model.jwt',true),''),'authenticated'))$$;
  create function cp7_model.access_now()returns jsonb language plpgsql volatile as $$begin
   if coalesce(nullif(current_setting('model.denied',true),''),'no')='yes'then raise exception using errcode='42501',message='MODEL_CURRENT_NATIVE_ACCESS_DENIED';end if;
   return jsonb_build_object('actor',auth.uid(),'epoch','1');end$$;
  create function cp7_sales_return_correction.access_now()returns jsonb language sql volatile as $$select cp7_model.access_now()$$;
  create function cp7_note.access_now()returns jsonb language sql volatile as $$select cp7_model.access_now()$$;
  create function cp7_sales.command_access(text)returns jsonb language sql volatile as $$select cp7_model.access_now()$$;
  create table cp7_model.graph(value jsonb);
  create function cp7_global_nonpo_native_graph.inspect_v1(uuid[])returns jsonb language sql stable as $$select value from cp7_model.graph$$;`);
 await db.query("select set_config('model.actor',$1,false)",[actor]);
 const reference=JSON.parse(await readFile(here+'NATIVE_SCOPE_WORK_REFERENCE.json'));
 for(const[table,declared]of Object.entries(reference.columns)){
  const cols=Object.values(declared).sort((a,b)=>a[1]-b[1]);
  await db.exec('create table '+table+'('+cols.map(row=>'"'+row[0]+'" '+row[2]).join(',')+')');
  const actual=await scalar('select jsonb_object_agg(attname,format_type(atttypid,atttypmod))from pg_attribute where attrelid=$1::regclass and attnum>0 and not attisdropped',[table]);
  assert.deepEqual(actual,Object.fromEntries(cols.map(row=>[row[0],row[2]])));
 }
 await db.exec((await readFile(here+'schema.sql')).toString());
 await db.exec(`create function cp7_global_nonpo_envelope.lock_v1(text)returns jsonb language plpgsql volatile as $$begin
  if coalesce(nullif(current_setting('model.lock_revokes',true),''),'no')='yes'then perform set_config('model.denied','yes',true);end if;
  if not exists(select 1 from cp7_global_nonpo_envelope.profiles where id=$1)then raise exception 'MODEL_SEALED_PROFILE_REQUIRED';end if;
  return jsonb_build_object('contract','cp7.global-nonpo-envelope-lock.v1','profile',$1,'all_acquisition_NOWAIT',true);end$$;`);
 await db.query(`insert into cp7_global_nonpo_envelope.profiles(id,parent_head,parent_tree,actual_parent_root_receipt,expected_catalogs,expected_relations,native_authority_sha256)
  values($1,$2,$2,'{"model_only":true}','[["model_catalog"]]',to_jsonb(array_fill('model_relation'::text,array[42])),$1)`,[profile,'c'.repeat(40)]);
 const graph={contract:'cp7.global-nonpo-native-graph.readonly-inspector.v1',status:'OBSERVED_QUIESCENT_SOURCE_ONLY',issues:[],basis_sha256:basis,outside_source:baseOutside};
 await db.query('insert into cp7_model.graph values($1::jsonb)',[JSON.stringify(graph)]);
 await db.exec((await readFile(here+'work_scope.sql')).toString());
 results.push({label:'Four new private scope functions and two tables compile against exact73 Native work-column types; all base constraints and providers remain modeled',result:'PASS'});
 await refused('No caller-supplied operation ID can replace missing actual Native owner work',()=>bind('D1',id(999)),'CP7_GLOBAL_EXACT_NATIVE_WORK_REQUIRED');
 await refused('An unrelated operation UUID cannot use a real Native work row',async()=>{await owner();await bind('D1',id(999));},'CP7_GLOBAL_EXACT_NATIVE_WORK_REQUIRED');
 await refused('D1 requires its exact reviewed global basis before any scope is created',async()=>{const x=await owner();await bind(x.op,x.n,'f'.repeat(64));},'CP7_GLOBAL_REVIEWED_BASIS_CHANGED');
 await refused('A newly dirty global visit refuses before effects',async()=>{const x=await owner('E');await db.query("update cp7_model.graph set value=jsonb_set(value,'{issues}','[\"DIRTY_GLOBAL\"]')");await bind(x.op,x.n);},'CP7_GLOBAL_CURRENT_NOOP_PROOF_REQUIRED');
 await refused('Live Native rights are checked again after the barrier acquisition',async()=>{const x=await owner();await db.query("select set_config('model.lock_revokes','yes',true)");await bind(x.op,x.n);},'MODEL_CURRENT_NATIVE_ACCESS_DENIED','42501');
 await refused('A second scope in the same backend and transaction is refused',async()=>{const x=await owner();await bind(x.op,x.n);await bind(x.op,x.n);},'CP7_GLOBAL_NESTED_SCOPE_REFUSED');
 await refused('Finish requires the actual Native completion phase',async()=>{const x=await owner();await bind(x.op,x.n);await finish(x.op,x.n);},'CP7_GLOBAL_SAME_NATIVE_COMPLETION_REQUIRED');
 await refused('Changed actual Native payload cannot complete an earlier scope',async()=>{const x=await owner();await bind(x.op,x.n);await completeOwner(x);await db.query('update '+x.table+" set payload=payload||'{\"changed\":true}'where operation_id=$1",[x.n]);await finish(x.op,x.n);},'CP7_GLOBAL_SAME_NATIVE_COMPLETION_REQUIRED');
 await refused('Changing the active actor cannot borrow another actor scope',async()=>{const x=await owner();await bind(x.op,x.n);await completeOwner(x);await db.query("select set_config('model.actor',$1,true)",[id(999)]);await finish(x.op,x.n);},'CP7_GLOBAL_OWN_SCOPE_REQUIRED');
 await refused('Revoked Native authority refuses completion',async()=>{const x=await owner();await bind(x.op,x.n);await completeOwner(x);await db.query("select set_config('model.denied','yes',true)");await finish(x.op,x.n);},'MODEL_CURRENT_NATIVE_ACCESS_DENIED','42501');
 await refused('One changed outside fact refuses instead of excluding or repairing it',async()=>{const x=await owner();await bind(x.op,x.n);await completeOwner(x);await db.query("update cp7_model.graph set value=jsonb_set(value,'{outside_source,facts,inventory_balances,0,value}','\"140.01\"')");await finish(x.op,x.n);},'CP7_GLOBAL_OUTSIDE_CHANGED_OR_NOT_QUIESCENT');
 await refused('A generic source operation cannot pretend to have a new UI review token',async()=>{const x=await owner('SOURCE');await bind(x.op,x.n,basis);},'CP7_GLOBAL_SOURCE_HAS_NO_NEW_UI_REVIEW_TOKEN');
 const operations=[];
 for(const op of['D1','E','SOURCE'])await transaction(async()=>{
  const x=await owner(op);await bind(x.op,x.n);const opened=await scalar('select to_jsonb(w)from cp7_global_nonpo_envelope.work_scopes_v1 w');
  assert.equal(opened.request_id,x.request);assert.deepEqual(opened.root_sales,[root]);assert.equal(opened.native_binding.payload.sale_id,root);
  await completeOwner(x);await finish(x.op,x.n);operations.push(x);
  const closed=await scalar('select to_jsonb(c)from cp7_global_nonpo_envelope.scope_completions_v1 c where operation_id=$1',[x.n]);
  assert.equal(closed.actor,actor);assert.equal(closed.request_id,x.request);assert.deepEqual(closed.outside_before,baseOutside);assert.deepEqual(closed.outside_after,baseOutside);
  await db.query('delete from '+x.table+' where operation_id=$1',[x.n]);
  results.push({label:op+' binds the actual Native request/root and closes with exact outside identity/fact equality; only the Native owner model advances its phase',result:'PASS'});
 },true);
 assert.deepEqual(await counts(),{open:0,closed:3});
 await refused('A completed operation cannot manufacture another finish or duplicate proof',()=>finish('D1',operations[0].n),'CP7_GLOBAL_OWN_SCOPE_REQUIRED');
 for(const[verb,sql]of[['UPDATE',"update cp7_global_nonpo_envelope.scope_completions_v1 set operation='OTHER'"],['DELETE','delete from cp7_global_nonpo_envelope.scope_completions_v1'],['TRUNCATE','truncate cp7_global_nonpo_envelope.scope_completions_v1']])
  await refused('Completion history is immutable under '+verb,()=>db.exec(sql),'CP7_GLOBAL_COMPLETION_HISTORY_IMMUTABLE');
 for(const role of['anon','authenticated','service_role']){
  for(const table of['work_scopes_v1','scope_completions_v1'])assert.equal(await scalar("select has_table_privilege($1,$2,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",[role,'cp7_global_nonpo_envelope.'+table]),false);
  for(const signature of['native_work_v1(text,uuid)','bind_v1(text,uuid,text,text)','finish_v1(text,uuid)','immutable_completion_v1()'])assert.equal(await scalar("select has_function_privilege($1,$2,'EXECUTE')",[role,'cp7_global_nonpo_envelope.'+signature]),false);
 }
 results.push({label:'All three browser/service roles lack table and scope-function access; no public entrypoint exists',result:'PASS'});
 const source_files={};for(const name of['schema.sql','work_scope.sql','work_scope_model.mjs','NATIVE_SCOPE_WORK_REFERENCE.json']){const raw=await readFile(here+name);source_files[name]={bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')};}
 const report={status:'GLOBAL_NATIVE_WORK_SCOPE_BINDING_AND_OUTSIDE_MODEL_CONTROLS_PASS_NOT_ERP',results,source_files,
  runtime:await scalar("select current_setting('server_version')"),actual_Native_work_column_maps:3,actual_Native_work_columns:73,
  actual_Native_owner_lifecycles_and_barrier_and_inspector_and_current_rights_are_models:true,
  source_schema_and_lock_sql_unchanged:true,old_actual_lock_primitives_and_old_census_NOT_rerun:true,
  Native_owning_hooks_written:0,complete_installer_provided:false,parent_gate_opened:false,
  actual_Native_cases:0,actual_Auth_HTTP_cases:0,actual_two_session_races:0,actual_browser_cases:0,production_go:false,independent_acceptance:false};
 await writeFile(output,JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:report.status,new_controls:results.length,actual_Native_cases:0}));
}catch(error){process.stderr.write(JSON.stringify({status:'GLOBAL_SCOPE_MODEL_FIRST_FAILURE',completed_controls:results,error:String(error),SQLSTATE:error.code,actual_Native_cases:0})+'\n');throw error;}
finally{await db.close();}
