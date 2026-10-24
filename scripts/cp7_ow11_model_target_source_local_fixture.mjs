// Shared controlled source/access fixture; no historical Native/Auth credit.
import {randomUUID} from 'node:crypto'
import {execFileSync} from 'node:child_process'
import assert from 'node:assert/strict'
import {modelRegistryFixture} from './cp7_ow11_model_registry_local_fixture.mjs'
export async function modelTargetSourceFixture({extraFacts={}}={}){
execFileSync('python',['-B','-c','import cp7_model_target_source as s;s.verify_sources()'],{env:{...process.env,PYTHONPATH:'scripts'}})
const base=await modelRegistryFixture({currentDay:true});const {db,read,cases,sql,actor,key,history,q,seed,test,rejects}=base
await db.exec(`alter table cp7_planning.history_runs add column request_id uuid default gen_random_uuid();
alter table cp7_planning.history_runs owner to cp7_capture;grant usage on schema extensions to cp7_capture;
create schema auth;create schema cp7_stock_formula;
create function auth.uid()returns uuid language sql stable as $$select current_setting('model_target_test.actor')::uuid$$;
create function cp7_stock_formula.access_now(boolean)returns jsonb language plpgsql volatile as $$begin
 if current_setting('model_target_test.active',true)is distinct from'true'or current_setting('model_target_test.warehouse_access',true)is distinct from'true'then raise exception using errcode='42501',message='CONTROLLED_WAREHOUSE_ACCESS_DENIED';end if;
 return jsonb_build_object('actor',auth.uid(),'epoch',current_setting('model_target_test.access_epoch'),'model_access',current_setting('model_target_test.model_access'));
end$$;
create or replace function erp.has_permission(text)returns boolean language sql stable as $$select current_setting('model_target_test.model_access',true)='true'$$;
create function cp7_private.access_now()returns jsonb language plpgsql volatile as $$begin
 if current_setting('model_target_test.active',true)is distinct from'true'or current_setting('model_target_test.model_access',true)is distinct from'true'then raise exception using errcode='42501',message='CONTROLLED_ACCESS_DENIED';end if;
 return jsonb_build_object('actor',current_setting('model_target_test.actor'),'profile',jsonb_build_object('revision',current_setting('model_target_test.access_epoch')));
end$$;
create function cp7_planning.history_source()returns jsonb language plpgsql volatile as $$declare n integer;facts jsonb;begin
 n:=coalesce(nullif(current_setting('model_target_test.history_calls',true),''),'0')::integer+1;
 perform set_config('model_target_test.history_calls',n::text,true);
 facts:=jsonb_build_object('sentinel',current_setting('model_target_test.facts'))||current_setting('model_target_test.facts_extra')::jsonb;
 if current_setting('model_target_test.change_second',true)='true'and n>=2 then facts:=jsonb_build_object('sentinel','changed during capture');end if;
 if current_setting('model_target_test.revoke_second',true)='true'and n>=2 then perform set_config('model_target_test.active','false',true);end if;
 return jsonb_build_object('status',current_setting('model_target_test.history_state'),'facts',facts);
end$$;`)
await sql("select set_config('model_target_test.actor',$1,false)v",[actor])
for(const[k,v]of Object.entries({facts_extra:JSON.stringify(extraFacts),active:'true',model_access:'true',warehouse_access:'true',access_epoch:'1',facts:'original',history_state:'COMPLETE',history_calls:'0',change_second:'false',revoke_second:'false'}))await sql('select set_config($1,$2,false)v',['model_target_test.'+k,v])
await db.exec("update cp7_planning.history_runs set dependency_hash=encode(pg_catalog.sha256(convert_to((jsonb_build_object('sentinel','original')||current_setting('model_target_test.facts_extra')::jsonb)::text,'UTF8')),'hex')")
const historySql=await read('scripts/cp7-src/planning/history.sql'),i=historySql.indexOf('create function cp7_planning.serve_history(')
assert.ok(i>=0);await db.exec(historySql.slice(i,historySql.indexOf('$$;',i)+3))
await db.exec(await read('scripts/cp7_model_evaluation_v2_stage/runtime.sql'))
await db.exec(await read('scripts/cp7_model_target_source/source.sql'))
const capture=(p=q)=>sql('select public.erp_cp7_capture_model_evaluation_v2($1::jsonb,$2::uuid)v',[JSON.stringify(p),randomUUID()])
const current=(keys=[key],at=null)=>sql('select cp7_model_target_source.capture($1::text[],coalesce($2::timestamptz,clock_timestamp()))v',[keys,at])
const reset=()=>sql("select set_config('model_target_test.history_calls','0',true)v")
const setting=(k,v)=>sql('select set_config($1,$2,true)v',['model_target_test.'+k,v])
const stored=id=>sql('select to_jsonb(r)v from cp7_model_registry_adapter.runs r where id=$1::uuid',[id])
const ready=async()=>{await seed();const r=await capture();assert.equal(r.current_guard.state,'ELIGIBLE');await reset();return r}
return{...base,capture,current,reset,setting,stored,ready}
}
