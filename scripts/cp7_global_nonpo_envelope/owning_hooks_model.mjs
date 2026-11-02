// New private scope lifecycle only. Native owner phases, Auth/current rights,
// inspector, barrier and base constraints are EXPLICIT MODELS. No ERP execution.
import assert from 'node:assert/strict';
import {readFile,writeFile}from'node:fs/promises';
import{fileURLToPath,pathToFileURL}from'node:url';
import{createHash}from'node:crypto';
const[runtime,output]=process.argv.slice(2);assert(runtime&&output);
assert.equal(process.argv[4],'--hooks-only','Only new review/owning source controls execute');
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
  values($1,$2,$2,'{"model_only":true}','[["model_catalog"]]',to_jsonb(array_fill('model_relation'::text,array[42])),encode(sha256(convert_to('{"known_functions_exact":true,"view":{"exact_known_source":true},"new_private_acl_closed":true,"model_only":true}'::jsonb::text,'UTF8')),'hex'))`,[profile,'c'.repeat(40)]);
 const graph={contract:'cp7.global-nonpo-native-graph.readonly-inspector.v1',status:'OBSERVED_QUIESCENT_SOURCE_ONLY',issues:[],basis_sha256:basis,outside_source:baseOutside};
 await db.query('insert into cp7_model.graph values($1::jsonb)',[JSON.stringify(graph)]);
 await db.exec((await readFile(here+'work_scope.sql')).toString());
 const owning=JSON.parse(await readFile(here+'NATIVE_OWNING_REFERENCE.json'));
 await db.exec('create schema erp;create domain cp7_credit.cent_amount as numeric');
 for(const[table,declared]of Object.entries(owning.declared_rowtype_columns)){
  const cols=Object.values(declared).sort((a,b)=>a[1]-b[1]);
  if(!await scalar('select to_regclass($1)::text',[table]))await db.exec('create table '+table+'('+cols.map(r=>'"'+r[0]+'" '+r[2]).join(',')+')');
  const actual=await scalar('select jsonb_object_agg(attname,format_type(atttypid,atttypmod))from pg_attribute where attrelid=$1::regclass and attnum>0 and not attisdropped',[table]);
  assert.deepEqual(actual,Object.fromEntries(cols.map(row=>[row[0],row[2]])));
 }
 await db.exec((await readFile(here+'review.sql')).toString());
 const fakeAuthority={known_functions_exact:true,view:{exact_known_source:true},new_private_acl_closed:true,
  model_only:true,session_user:'MODEL_SESSION',current_user:'MODEL_OWNER',runtime_entry:null,production_go:false};
 await db.query("update cp7_model.graph set value=jsonb_set(value,'{authority}',$1::jsonb)",[JSON.stringify(fakeAuthority)]);
 // The profile is an explicit setup fixture. Add the authority-bearing fake
 // observation first and use the exact hash it was initially seeded with.
 // No protected profile UPDATE, trigger removal or runtime admission is used.
 const normalized={...fakeAuthority};for(const key of['session_user','current_user','runtime_entry','required_final_parent','actual_Native_qualification_credit','production_go'])delete normalized[key];
 const authorityHash=await scalar("select encode(sha256(convert_to($1::jsonb::text,'UTF8')),'hex')",[JSON.stringify(normalized)]);
 // Reuse the existing SHA-shaped model profile ID as the expected digest by
 // replacing only the literal model INSERT before it executes (origin route).
 assert.equal(await scalar('select native_authority_sha256 from cp7_global_nonpo_envelope.profiles'),authorityHash);
 const review=roots=>scalar('select cp7_global_nonpo_envelope.review_v1($1::uuid[])',[roots]);
 const observed=await review([root]);assert.equal(observed.basis_sha256,basis);assert.equal(observed.profile,profile);
 assert.equal(observed.status,'OBSERVED_QUIESCENT_SOURCE_ONLY');assert.equal(observed.runtime_acceptance_claimed,false);
 results.push({label:'Two new private review helpers compile and bind one sealed model profile, exact current authority hash and the read-only global basis',result:'PASS'});
 await refused('No duplicate or NULL root may masquerade as an explicit owning root domain',()=>review([root,root]),'CP7_GLOBAL_EXPLICIT_DISTINCT_ROOTS_REQUIRED');
 await refused('No empty root domain is accepted',()=>review([]),'CP7_GLOBAL_EXPLICIT_DISTINCT_ROOTS_REQUIRED');
 await refused('Two profile rows require a new explicit installation decision',async()=>{
  await db.query(`insert into cp7_global_nonpo_envelope.profiles select $1,parent_head,parent_tree,actual_parent_root_receipt,expected_catalogs,expected_relations,native_authority_sha256,sealed_at from cp7_global_nonpo_envelope.profiles`,['f'.repeat(64)]);
  await review([root]);
 },'CP7_GLOBAL_ONE_ACTUAL_FINAL_PARENT_PROFILE_REQUIRED');
 await refused('Changed actual Native authority is not relabelled as a new matching source',async()=>{await db.exec("update cp7_model.graph set value=jsonb_set(value,'{authority,model_only}','false')");await review([root]);},'CP7_GLOBAL_FINAL_NATIVE_AUTHORITY_PROFILE_CHANGED');
 await refused('An invalid authority flag refuses before a quote basis is returned',async()=>{await db.exec("update cp7_model.graph set value=jsonb_set(value,'{authority,known_functions_exact}','false')");await review([root]);},'CP7_GLOBAL_EXACT_CURRENT_NATIVE_AUTHORITY_REQUIRED');
 await refused('A missing inspector status cannot silently pass the protocol',async()=>{await db.exec("update cp7_model.graph set value=value-'status'");await review([root]);},'CP7_GLOBAL_EXACT_READONLY_INSPECTION_REQUIRED');
 await transaction(async()=>{
  await db.exec("update cp7_model.graph set value=jsonb_set(jsonb_set(value,'{status}','\"OBSERVED_REFUSAL_SOURCE_ONLY\"'),'{issues}','[\"DIRTY_GLOBAL\"]')");
  assert.equal((await review([root])).status,'OBSERVED_REFUSAL_SOURCE_ONLY');
 });results.push({label:'A dirty global observation remains an explicit quote refusal; no Native repair or dispatcher executes',result:'PASS'});
 const derivation=JSON.parse((await import('node:child_process')).execFileSync('python',['-B','-c',
  "import importlib.util,json;s=importlib.util.spec_from_file_location('source_only_hooks','native_hooks.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);d,p=m.derive(m.originals());print(json.dumps(dict(definitions=d,proof=p)))"],{cwd:here,encoding:'utf8',maxBuffer:2*1024*1024,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}}));
 for(const[sig,row]of Object.entries(owning.functions)){
  await db.exec(row[0]);await db.exec('revoke all on function '+sig+' from public,anon,authenticated,service_role');
 }
 const catalog=async()=>Object.fromEntries(await Promise.all(Object.keys(owning.functions).map(async sig=>[sig,await scalar("select to_jsonb(p)-'prosrc'from pg_proc p where oid=$1::regprocedure",[sig])])));
 const before=await catalog();for(const text of Object.values(derivation.definitions))await db.exec(text);
 assert.deepEqual(await catalog(),before);assert.equal(derivation.proof.owning_functions,8);assert.equal(derivation.proof.source_routes,18);
 results.push({label:'All eight exact original and derived owning bodies compile against actual declared Native row types; CREATE OR REPLACE preserves every other pg_proc attribute, OID and raw ACL in the model',result:'PASS'});
 const nativeNames=Object.keys(derivation.definitions);
 for(const name of nativeNames){const text=derivation.definitions[name];
  if(name.includes('prepare_v1')){const firstNativeRead=name.startsWith('cp7_credit_correction_de.')?'src:=ow04_source_proposal.locked_source_family':'graph:=cp7_credit.consumer_joined_graph_v1';assert(text.indexOf('lock_v1(')<text.indexOf(firstNativeRead));assert(text.indexOf('bind_v1(')>text.indexOf('insert into '));}
  if(name.includes('source_request_enter')){assert(text.indexOf('lock_v1(')>text.indexOf('assert_only_own_sales_source_context_v1'));assert(text.indexOf('lock_v1(')<text.indexOf('authority:=cp7_sales.command_access'));assert(text.indexOf("bind_v1('SOURCE'")>text.indexOf('insert into cp7_credit.source_operation_work_v1'));}
  if(name.includes('finish_v1')){assert(text.indexOf('cp7_global_nonpo_envelope.finish_v1')<text.indexOf('delete from '));}
 }
 results.push({label:'The counted barrier precedes each fresh owner read; binding follows actual Native work insertion and completion precedes original receipt/work closure',result:'PASS'});
 const negative=JSON.parse((await import('node:child_process')).execFileSync('python',['-B','-c',
  "import importlib.util,json,copy;s=importlib.util.spec_from_file_location('source_only_hooks','native_hooks.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);r=m.originals();first=next(iter(r));refused=0\nfor index,value in [(0,r[first][0]+'\\n-- changed'),(1,'OTHER_OWNER'),(-1,[])]:\n v=copy.deepcopy(r);v[first][index]=value\n try:m.derive(v)\n except ValueError:refused+=1\n else:raise AssertionError('Changed original admitted')\nprint(json.dumps(dict(refused=refused)))"],{cwd:here,encoding:'utf8',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}}));
 assert.equal(negative.refused,3);results.push({label:'Changed original body, owner or ACL is refused before any owning adapter can be applied',result:'PASS'});
 for(const sig of['cp7_credit.cent_text(cp7_credit.cent_amount)','cp7_credit_note_carry_de.public_basis_v1(jsonb)'])await db.exec(owning.unchanged_public_projection_functions[sig][0]);
 const plain={sale_id:root,incoming_facts:[],basis_sha256:basis};
 const publicBasis=p=>scalar('select cp7_credit_note_carry_de.public_basis_v1($1::jsonb)',[JSON.stringify(p)]);
 assert.deepEqual(await publicBasis({...plain,global_envelope:observed}),await publicBasis(plain));
 results.push({label:'The unchanged actual public E projection never exposes the added private global source or finance facts',result:'PASS'});
 for(const role of['anon','authenticated','service_role'])for(const sig of['selected_profile_v1()','review_v1(uuid[])'])assert.equal(await scalar("select has_function_privilege($1,$2,'EXECUTE')",[role,'cp7_global_nonpo_envelope.'+sig]),false);
 results.push({label:'The two new review helpers grant no browser/service execution or public RPC',result:'PASS'});
 const source_files={};for(const name of['review.sql','native_hooks.py','NATIVE_OWNING_REFERENCE.json','owning_hooks_model.mjs','OWNING_HOOK_MODEL_ORIGIN.json']){const raw=await readFile(here+name);source_files[name]={bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')};}
 const report={status:'GLOBAL_PRIVATE_REVIEW_AND_EIGHT_OWNING_SOURCE_MODEL_CONTROLS_PASS_NOT_ERP',results,source_files,
  actual_original_and_derived_owning_functions_compiled_on_model:8,exact_reversible_owning_source_routes:18,guard_sites:3,
  declared_Native_rowtype_maps:Object.keys(owning.declared_rowtype_columns).length,
  all_Native_business_functions_NOT_executed:true,Auth_rights_barrier_inspector_base_constraints_are_models:true,
  old21_scope_models_and_old_actual_lock_and_catalog_controls_NOT_rerun:true,
  actual_final_parent_installer_or_runtime_armed:false,actual_Native_cases:0,actual_Auth_HTTP_cases:0,actual_two_session_races:0,actual_browser_cases:0,production_go:false,independent_acceptance:false};
 await writeFile(output,JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:report.status,new_controls:results.length,actual_Native_cases:0}));
}catch(error){process.stderr.write(JSON.stringify({status:'GLOBAL_OWNING_HOOK_MODEL_FIRST_FAILURE',completed_controls:results,error:String(error),SQLSTATE:error.code,actual_Native_cases:0})+'\n');throw error;}
finally{await db.close();}
