// Actual source/selector/assessment/guard SQL; synthetic rows and controlled
// access/physical recapture. These fixtures do not establish Native history.
import assert from 'node:assert/strict'
import {randomUUID} from 'node:crypto'
import {modelTargetSourceFixture} from './cp7_ow11_model_target_source_local_fixture.mjs'
export async function modelTargetSourceV2Fixture(){
const f=await modelTargetSourceFixture(),{db,read,sql,actor,root,size,key}=f
await db.exec(`create table erp.products(id uuid primary key,identity_root_id uuid,size_id uuid);
create table erp.fg_stock_movements(id uuid primary key,product_id uuid,lot_id uuid,location_id uuid,quality_grade text,qty_signed numeric,physical_at timestamptz,system_created_at timestamptz,movement_type text,source_type text,source_id uuid,reversal_of_id uuid,book_order bigint);
create schema cp7_model_history_scope;create schema cp7_model_history_runtime;create schema cp7_model_scoped_evaluation;create schema cp7_reorder_inputs;
create table cp7_model_history_runtime.runs(id uuid primary key,actor uuid,query jsonb,captured_at timestamptz,source jsonb,result jsonb,dependency_hash text,engine_hash text);
create table cp7_model_scoped_evaluation.runs(id uuid primary key,actor uuid,request_id uuid,payload jsonb,query jsonb,history_run_id uuid,captured_at timestamptz,registry_id text,input jsonb,result jsonb,dependency_hash text);
create function cp7_model_history_runtime.engine()returns text language sql stable as $$select repeat('7',64)$$;
create function cp7_model_scoped_evaluation.engine()returns text language sql stable as $$select repeat('8',32)$$;
create function cp7_reorder_inputs.capture_history(integer)returns jsonb language plpgsql volatile as $$declare c jsonb;begin
 c:=current_setting('model_source_v2_test.capture')::jsonb;
 c:=jsonb_set(c,'{captured_at}',to_jsonb(cp7_planning.utc(clock_timestamp())));
 if current_setting('model_source_v2_test.mode',true)='CHANGE_PHYSICAL'then c:=jsonb_set(c,'{facts,products,0,label}',to_jsonb('changed'::text));end if;
 if current_setting('model_source_v2_test.mode',true)='REVOKE'then perform set_config('model_target_test.active','false',true);end if;
 if current_setting('model_source_v2_test.mode',true)='NEW_MODEL'then
  insert into cp7_model_scoped_evaluation.runs select gen_random_uuid(),actor,gen_random_uuid(),payload,query,history_run_id,clock_timestamp(),registry_id,input,result,dependency_hash from cp7_model_scoped_evaluation.runs limit 1;
 end if;
 return c;
end$$;`)
await db.query('insert into erp.products values($1,null,$2)',[root,size])
for(const path of['scripts/cp7_history_reference/digest.sql','scripts/cp7_model_history_scope/identity.sql','scripts/cp7_model_target_binding/binding.sql',
 'scripts/cp7_model_evaluation_selection/selection.sql','scripts/cp7_model_target_source_v2/stock.sql',
 'scripts/cp7_model_target_source_v2/non-stock.sql','scripts/cp7_model_target_source_v2/physical.sql',
 'scripts/cp7_model_target_source_v2/source.sql','scripts/cp7_model_target_source_v2/reorder.sql'])await db.exec(await read(path))
const now=()=>sql('select cp7_planning.utc(clock_timestamp())v')
const captureFacts=async()=>({contract_version:'cp7.native-demand-facts.v1',scope:'GLOBAL_CURRENT_PHYSICAL_ROOTS',captured_at:await now(),status:'COMPLETE',stock_raw_omitted:false,stock_rows_at_least:0,
 facts:{products:[{id:root,root_id:root,size_id:size,commercial:[]}],stock:[],sales:[],sale_journals:[],returns:[],return_journals:[]}})
const sourceSetting=(k,v)=>sql('select set_config($1,$2,true)v',['model_source_v2_test.'+k,v])
const current=async(c)=>{c??=await captureFacts();await sourceSetting('capture',JSON.stringify(c));return sql('select cp7_model_target_source_v2.capture($1::jsonb,5000)v',[JSON.stringify(c)])}
const seedScoped=async({eligible=false}={})=>{
 if(eligible)await f.seed()
 const global=await f.capture(),original=await f.stored(global.run_id),c=await captureFacts(),hid=randomUUID(),id=randomUUID()
 const stock=await sql('select cp7_model_target_source_v2.stock_digests($1::jsonb,$2::timestamptz)v',[JSON.stringify(c.facts.products),c.captured_at])
 const source={...c,contract_version:'cp7.model-history-facts.v1',scope:'SINGLE_CURRENT_PHYSICAL_ROOT',target_key:key,
  producer_hash:await sql('select cp7_model_target_source_v2.producer()v'),stock_reference:stock[0].stock_reference}
 const hash=await sql('select cp7_model_history_scope.identity($1::jsonb)v',[JSON.stringify(source)])
 const hq={from_date:original.input.from_date,through_date:original.input.through_date,group_mode:'AS_SOLD',target_key:key}
 const historySource={query:{from_date:hq.from_date,through_date:hq.through_date,group_mode:hq.group_mode},target_key:key,source_hash:hash,captured_at:c.captured_at,source}
 await db.query('insert into cp7_model_history_runtime.runs values($1,$2,$3::jsonb,$4,$5::jsonb,$6::jsonb,$7,$8)',[hid,actor,JSON.stringify(hq),c.captured_at,JSON.stringify(historySource),JSON.stringify({source_hash:hash,target_key:key,captured_at:c.captured_at,scope:'SINGLE_CURRENT_PHYSICAL_ROOT'}),hash,'7'.repeat(64)])
 let input={...original.input,history_run_id:hid,query:{...original.query,history_run_id:hid},history_source_hash:hash,engine_hash:'8'.repeat(32)};delete input.source_hash
 input={...input,source_hash:await sql("select encode(sha256(convert_to($1::jsonb::text,'UTF8')),'hex')v",[JSON.stringify(input)])}
 const assessment=await f.assess(input)
 await db.query('insert into cp7_model_scoped_evaluation.runs values($1,$2,$3,$4::jsonb,$4::jsonb,$5,$6,$7,$8::jsonb,$9::jsonb,$10)',[id,actor,randomUUID(),JSON.stringify(input.query),hid,await now(),input.registry_id,JSON.stringify(input),JSON.stringify(assessment),input.source_hash])
 await f.reset();return{id,hid,input,assessment,original,global,hash}
}
return{...f,now,captureFacts,sourceSetting,currentV2:current,seedScoped}
}
