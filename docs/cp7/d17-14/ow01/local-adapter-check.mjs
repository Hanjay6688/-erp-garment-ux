// LOCAL_PGLITE18_DEV only: synthetic reader contracts, no Native business evidence.
const { PGlite } = await import(process.env.PGLITE_MODULE ?? '@electric-sql/pglite');
import { fileURLToPath } from 'node:url';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
const repo=fileURLToPath(new URL('../../../../',import.meta.url));
const old=process.argv.includes('--old');
const db=new PGlite();
const q=async(s,p=[]) => (await db.query(s,p)).rows;
const one=async(s,p=[]) => Object.values((await q(s,p))[0])[0];
let cases=0;
try {
await db.exec(`create role anon;create role authenticated;create role service_role;
create schema auth;
create function auth.uid()returns uuid language sql stable as $$select (nullif(current_setting('request.jwt.claims',true),'')::jsonb->>'sub')::uuid$$;`);
await db.exec(`create schema vault;create table vault.secrets(id uuid default gen_random_uuid(),name text,decrypted_secret text);
create view vault.decrypted_secrets as select *from vault.secrets;
create function vault.create_secret(a text,b text,c text)returns uuid language sql as $$insert into vault.secrets(name,decrypted_secret)values(b,a)returning id$$;
create function vault.update_secret(a uuid,b text)returns void language sql as $$update vault.secrets set decrypted_secret=b where id=a$$;
create schema net;create table net.http_request_queue(id bigint generated always as identity,url text,params jsonb);
create table net._http_response(id bigint,status_code integer,content text,timed_out boolean,error_msg text);
create function net.http_get(url text,params jsonb,timeout_milliseconds integer)returns bigint language plpgsql as $$declare i bigint;begin
 if url<>'http://fake-callmebot:8080/whatsapp.php'then raise exception 'TEST_ONLY_FAKE_TRANSPORT';end if;
 insert into net.http_request_queue(url,params)values(url,params)returning id into i;return i;end$$;`);
await db.exec(await fs.readFile(repo+'/scripts/cp7_wa_smoke_stubs.sql','utf8'));
await db.exec(`create table public.test_obligations(doc jsonb);
create or replace function cp7_reminder_native.other_obligation_source()returns jsonb language sql stable security definer set search_path=''as $$select jsonb_build_object('contract_version','cp7.native-other-obligations.v1','as_of','2026-10-20','rows',coalesce((select jsonb_agg(doc)from public.test_obligations),'[]'))$$;`);
let sql=old?execFileSync('git',['show','5fd5d38ef43618e48f9aa36208f46ad2290404c0:scripts/cp7-src/alerts/alerts.sql'],{cwd:repo,encoding:'utf8'}):await fs.readFile(repo+'/scripts/cp7-src/alerts/alerts.sql','utf8');
await db.exec(sql);
console.log(JSON.stringify({step:'full_alerts_sql_installed',runtime:'LOCAL_PGLITE18_DEV',original_sql:true,old}));
const owner='10000000-0000-4000-8000-000000000001';
const perms=['finance.ar.view','finance.ap.view','finance.payroll.view','warehouse.accessory.view','production.laundry.view','finance.hpp.view','warehouse.dashboard.view','warehouse.material.view','master.fabric.view','warehouse.fg.view'];
await db.query('insert into erp.test_users(sub,role_code,perms)values($1,\'OWNER\',$2)',[owner,perms]);
await one("select set_config('request.jwt.claims',$1,false)",[JSON.stringify({sub:owner,role:'authenticated'})]);
const domains=['OPENING_AR','OPENING_AP','PAYROLL_AP','ACCESSORY_AP','LAUNDRY_AP','LAUNDRY_RECEIPT','LAUNDRY_OPENING_UNINVOICED'];
const defaults=await one('select cp7_alert_native.defaults()');
assert(domains.every(d=>defaults.kinds.includes(d)),'D17-14: all seven obligation domains must be enabled by default');cases++;
const settings={...defaults,expected_revision:0,phone_e164:'+620000000000',enabled:false,quiet_enabled:false,digest_times:[]};delete settings.revision;
await one('select public.erp_cp7_save_wa_settings_v1($1::jsonb,$2::uuid)',[JSON.stringify(settings),'10000000-0000-4000-8000-000000000002']);
const rows=domains.map((domain,i)=>({domain,key:(domain==='OPENING_AR'?'AR_DUE:':'AP_DUE:')+domain+':10000000-0000-4000-8000-'+String(i+100).padStart(12,'0'),source_id:'10000000-0000-4000-8000-'+String(i+100).padStart(12,'0'),label:'Rahasia pihak '+i,state:'DATA_REVIEW',reason:i<5?'MISSING_RECORDED_DUE_DATE':'VALUE_PENDING',economic_state:i<5?'OPEN':'UNKNOWN',source_hash:'a'.repeat(64),financial_source:{remaining:{state:i<5?'KNOWN':'UNKNOWN',...(i<5?{value:'9007199254740993.01'}:{})},recorded_due_date:null}}));
for(const r of rows)await db.query('insert into public.test_obligations values($1)',[JSON.stringify(r)]);
await db.exec("set statement_timeout='8s'");
const collect=await one('select cp7_alert_native.collect_kinds($1::text[])',[domains]);
for(const d of domains){assert.equal(collect[d].opened,1,JSON.stringify(collect[d]));cases++;}
const first=await q('select id,kind,subject_key,detail from cp7_alert_native.alerts order by kind');assert.equal(first.length,7);cases++;
for(const a of first){const src=rows.find(r=>r.domain===a.kind);assert.equal(a.subject_key,src.key);assert.equal(a.detail.remaining,src.financial_source.remaining.value??null);assert.equal(a.detail.due_date,null);assert.equal(a.detail.source_hash,src.source_hash);cases++;}
await one('select cp7_alert_native.collect_kinds($1::text[])',[domains]);assert.equal(await one('select count(*)::integer from cp7_alert_native.outbox'),7);cases++;
const items=first.map(a=>({kind:a.kind,subject_key:a.subject_key,title:a.detail.label,detail:a.detail}));
const body=await one("select cp7_alert_native.render('DIGEST',$1,'{}','SUMMARY',10,now(),'{}')",[JSON.stringify(items)]);
assert(!body.includes('Rahasia'));assert.equal(body.split('1 pengingat').length-1,7);assert(!body.includes('Rp0'));assert(body.endsWith('Buka ERP > Reminder'));assert(body.length<=1000);cases++;
assert.equal(await one("select cp7_alert_native.rp('9007199254740993.01')"),'Rp9.007.199.254.740.993,01');
assert.equal(await one("select cp7_alert_native.rp('0.01')"),'Rp0,01');cases++;
const staff='20000000-0000-4000-8000-000000000001';
await db.query("insert into erp.test_users(sub,role_code,perms)values($1,'STAFF',$2)",[staff,perms]);
await one("select set_config('request.jwt.claims',$1,false)",[JSON.stringify({sub:staff,role:'authenticated'})]);
for(const [remove,hidden]of[['finance.payroll.view',['PAYROLL_AP']],['warehouse.accessory.view',['ACCESSORY_AP']],['production.laundry.view',['LAUNDRY_AP','LAUNDRY_RECEIPT','LAUNDRY_OPENING_UNINVOICED']],['finance.hpp.view',['ACCESSORY_AP','LAUNDRY_AP','LAUNDRY_RECEIPT','LAUNDRY_OPENING_UNINVOICED']]]){
 await db.query('update erp.test_users set perms=$2 where sub=$1',[staff,perms.filter(p=>p!==remove)]);
 const visible=await one("select public.erp_cp7_get_alerts_v1('{}')");assert(!visible.rows.some(r=>hidden.includes(r.kind)));assert(!visible.kinds.some(r=>hidden.includes(r.kind)));cases++;
}
await one("select set_config('request.jwt.claims',$1,false)",[JSON.stringify({sub:owner,role:'authenticated'})]);
await db.exec(`update public.test_obligations set doc=jsonb_set(jsonb_set(doc,'{state}','"RESOLVED"'),'{reason}','"ZERO_NATIVE_REMAINING"')`);
await one('select cp7_alert_native.collect_kinds($1::text[])',[domains]);assert.equal(await one("select count(*)::integer from cp7_alert_native.alerts where state='OPEN'"),0);cases++;
console.log(JSON.stringify({status:'PASS',checks:cases,runtime:'LOCAL_PGLITE18_DEV',scope:'full SQL installs; adapter, exact money, grouping, dedup, resolution and permission checks with synthetic source contracts',not_native_business_evidence:true,no_network_transport:true}));
} catch(e) { console.log(JSON.stringify({status:'FAIL',checks:cases,old,error:e.message,code:e.code??null,position:e.position??null})); process.exitCode=1; }
finally { await db.close(); }
