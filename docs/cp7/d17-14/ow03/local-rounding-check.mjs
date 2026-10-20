// Real profile writer and rounding SQL in PGlite, with synthetic identity and
// product tables. Development checks only: not Native/Supabase acceptance.
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {execFileSync} from 'node:child_process'
import {randomUUID} from 'node:crypto'
const {PGlite}=await import(process.env.PGLITE_MODULE)
const db=new PGlite(),old=process.argv.includes('--old')
const read=p=>old?execFileSync('git',['show','333005edbc052cfba0d0dcdff26f72854849a4fb:'+p],{encoding:'utf8',maxBuffer:4e6}):readFileSync(p,'utf8')
const functionSql=(path,name)=>{const sql=read(path),start=sql.indexOf('create function '+name+'(');assert.ok(start>=0,name);const end=sql.indexOf('$$;',start);assert.ok(end>start,name);return sql.slice(start,end+3)}
let checks=0
const check=(got,want)=>{assert.deepEqual(got,want);checks++}
const actor='11111111-1111-4111-8111-111111111111',root='22222222-2222-4222-8222-222222222222',pid='33333333-3333-4333-8333-333333333333',size='44444444-4444-4444-8444-444444444444'
await db.exec(`create role cp7_policy;create role cp7_capture;create role anon;create role authenticated;create role service_role;
 create schema cp7_identity;create schema auth;create schema cp7_wip;create schema cp7_demand;create schema erp;create schema cp7_analysis_native;
 create function auth.uid()returns uuid language sql stable as $$select '${actor}'::uuid$$;
 create function cp7_identity.access_now(boolean)returns jsonb language sql stable as $$select '{"actor":"${actor}","synthetic_access":true}'::jsonb$$;
 create function cp7_identity.immutable_row()returns trigger language plpgsql as $$begin raise exception 'SYNTHETIC_IMMUTABLE';end$$;
 create table erp.products(id uuid,identity_root_id uuid,size_id uuid,sku text,product_name text,effective_from timestamptz,effective_to timestamptz);
 insert into erp.products values('${pid}','${root}','${size}','LOCAL-PCS','Synthetic product',now()-interval'1 day',null);
 grant usage on schema cp7_identity,auth,erp to cp7_policy,cp7_capture;
 grant select on erp.products to cp7_policy,cp7_capture;
 grant execute on all functions in schema cp7_identity,auth to cp7_policy,cp7_capture;`)
await db.exec(functionSql('scripts/cp7-src/wip/bootstrap.sql','cp7_wip.fields'))
await db.exec(functionSql('scripts/cp7-src/wip/bootstrap.sql','cp7_wip.pcs'))
await db.exec(functionSql('scripts/cp7-src/demand/bootstrap.sql','cp7_demand.decimal'))
await db.exec(read('scripts/cp7-src/planning/profile.sql'))
const config={mean_mode:'OWN_AVAILABLE_HISTORY',daily_pcs:null,minimum_available_days:'1',lead_days:'3',review_days:'7',buffer_days:null}
const payload=(revision,cfg)=>({root_id:root,product_version_id:pid,expected_revision:String(revision),config:cfg,reason:'Synthetic explicit review'})
const apply=async(p,id=randomUUID())=>(await db.query('select public.erp_cp7_save_planning_profile_v1($1::jsonb,$2::uuid) out',[JSON.stringify(p),id])).rows[0].out
const key=randomUUID(),legacy=payload(0,config),first=await apply(legacy,key)
check((await apply(legacy,key)),first)
check((await db.query('select payload from cp7_profile.commands where request_id=$1',[key])).rows[0].payload,legacy)
await assert.rejects(()=>apply({...legacy,config:{...config,rounding_multiple:null}},key),/CP7_PROFILE_REQUEST_CHANGED/);checks++
const selected=payload(1,{...config,rounding_multiple:'12'}),saved=await apply(selected)
check(saved.revision,'2')
check((await db.query('select config from cp7_profile.profiles where revision=2')).rows[0].config,selected.config)
for(const multiple of ['0','-1','1.5','12.0','01','',12,true]){
 await assert.rejects(()=>apply(payload(2,{...config,rounding_multiple:multiple})),/CP7_PROFILE_ROUNDING_MULTIPLE/);checks++
 check((await db.query('select count(*)::int n from cp7_profile.profiles')).rows[0].n,2)
}
check((await apply(payload(2,{...config,rounding_multiple:null}))).revision,'3')
await assert.rejects(()=>apply(payload(3,{...config,rounding_multiple:'12',extra_key:'1'})),/CP7_WIP_FIELDS/);checks++
await db.exec(functionSql('scripts/cp7-src/planning/analysis.sql','cp7_analysis_native.rounded_suggestion'))
const row=(gap,multiple,quality='SELECTED_ASSUMPTION',state='ACTIVE')=>({production_policy:{policy:{state}},profile:{quality,config:multiple===undefined?{}:{rounding_multiple:multiple}},conditional_gap_pcs:gap})
const rounded=async r=>(await db.query('select cp7_analysis_native.rounded_suggestion($1::jsonb) out',[JSON.stringify(r)])).rows[0].out
const oracle=(n,m)=>{const need=BigInt(n),batch=BigInt(m),value=((need+batch-1n)/batch)*batch;return{suggested_pcs:String(value),extra_pcs:String(value-need),applied:true}}
for(const [n,m]of[['13','12'],['12','12'],['0','12'],['13','1'],['13','5'],['9007199254740993','12'],['100000000000000000000000000001','100000000000000000000000000000']])check(await rounded(row(n,m)),oracle(n,m))
let seed=7n
for(let i=0;i<120;i++){seed=(seed*48271n)%2147483647n;const n=String(seed);seed=(seed*48271n)%2147483647n;const m=String(seed%10000n+1n);check(await rounded(row(n,m)),oracle(n,m))}
const unknown={suggested_pcs:null,extra_pcs:null,applied:false}
for(const r of[row('13',undefined),row('13',null),row(null,'12'),row('13','12','UNREVIEWED'),row('13','12','PHYSICAL_VERSION_CHANGED')])check(await rounded(r),unknown)
for(const state of['PAUSED','STOPPED'])check(await rounded(row('13','12','SELECTED_ASSUMPTION',state)),{suggested_pcs:'0',extra_pcs:null,applied:false})
for(const m of['0','-1','1.5','01',12,true]){await assert.rejects(()=>rounded(row('13',m)),/CP7_PROFILE_ROUNDING_MULTIPLE/);checks++}
check(await rounded(row('13','12')),oracle('13','12'));check(await rounded(row('13','5')),oracle('13','5'))
console.log(JSON.stringify({status:'PASS',checks,real_profile_and_rounding_sql:true,runtime:'LOCAL_PGLITE18_DEV',synthetic_identity_and_products:true,native_acceptance:false,full_compiler_parity:false}))
await db.close()
