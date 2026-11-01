// Real isolated PostgreSQL model; no ERP runtime, Auth, hosted DB or UI claim.
import assert from 'node:assert/strict'
import {readFileSync, writeFileSync} from 'node:fs'
import {dirname, resolve} from 'node:path'
import {fileURLToPath, pathToFileURL} from 'node:url'
import {createHash, randomUUID} from 'node:crypto'

const here = dirname(fileURLToPath(import.meta.url))
assert(process.env.PGLITE_MODULE, 'PGLITE_MODULE must point to the separately pinned local control engine')
const {PGlite} = await import(pathToFileURL(resolve(process.env.PGLITE_MODULE)).href)
const db = new PGlite(), sql = readFileSync(resolve(here, 'policy.sql'), 'utf8')
const ids = Object.fromEntries(['owner','special','ordinary','categoryA','categoryB','eventA','eventB','eventEmpty','eventPending','eventOther','specialPolicy','ordinaryPolicy']
  .map((name,index) => [name, `00000000-0000-4000-8000-${String(index+1).padStart(12,'0')}`]))
const q = (text,args=[]) => db.query(text,args)
const scalar = async(text,args=[]) => Object.values((await q(text,args)).rows[0])[0]
const token = () => scalar('select cp7_accessory_nonpayable.timeline_token_v1()')
const record = async(day,event,request,seen,reason='SYNTHETIC EXPLICIT EFFECTIVE DATE') => scalar(
  'select cp7_accessory_nonpayable.record_version_v1($1::date,$2::uuid,$3::uuid,$4,$5)', [day,event,request,seen,reason])
const basis = (contractor,category,at) => scalar(
  'select cp7_accessory_nonpayable.good_basis_v1($1::uuid,$2::uuid,$3::timestamptz)', [contractor,category,at])
const rows = () => scalar("select coalesce(jsonb_agg(to_jsonb(v) order by v.effective_from),'[]'::jsonb) from cp7_accessory_nonpayable.category_versions_v1 v")
const checks = []
async function test(name, callback) { await callback(); checks.push({name,status:'PASS'}) }
async function refused(name, callback, expected) {
  await test(name, async () => { const before=await rows(); await assert.rejects(callback, expected); assert.deepEqual(await rows(),before) })
}

try {
  await db.exec(`
    create role anon nologin; create role authenticated nologin; create role service_role nologin;
    create schema erp;
    create table erp.bc_policy_settings_v1(policy_key text primary key,status text not null,value jsonb,version bigint not null);
    create table erp.bc_policy_setting_events_v1(id uuid primary key,policy_key text not null,version bigint not null,
      status text not null,value jsonb,set_at timestamptz not null,unique(policy_key,version));
    create table erp.accessory_categories(id uuid primary key,is_active boolean not null);
    create table erp.contractors(id uuid primary key,contractor_type text not null);
    create table erp.contractor_hpp_policy_versions(id uuid primary key,contractor_id uuid not null,
      effective_from date not null,effective_to date,is_special boolean not null,row_version bigint not null);
    create function erp.require_internal() returns void language plpgsql as $$begin
      if current_setting('model.internal',true) is distinct from 'yes' then raise exception 'MODEL_INTERNAL_REQUIRED';end if;
    end;$$;
    create function erp.require_owner_admin() returns void language plpgsql as $$begin
      if current_setting('model.owner',true) is distinct from 'yes' then raise exception 'MODEL_OWNER_REQUIRED';end if;
    end;$$;
    create function erp.current_app_user_id() returns uuid language sql as $$select '${ids.owner}'::uuid$$;
    set model.internal='yes'; set model.owner='yes';
  `)
  await q("insert into erp.contractors values($1,'MANDOR'),($2,'MANDOR')",[ids.special,ids.ordinary])
  await q('insert into erp.accessory_categories values($1,true),($2,true)',[ids.categoryA,ids.categoryB])
  await q("insert into erp.contractor_hpp_policy_versions values($1,$2,'2026-10-01','2026-11-30',true,1),($3,$4,'2026-10-01',null,false,1)",
    [ids.specialPolicy,ids.special,ids.ordinaryPolicy,ids.ordinary])
  await q("insert into erp.bc_policy_settings_v1 values('ERP_DEC02','SET',$1::jsonb,2)",[JSON.stringify({special_free_category_ids:[ids.categoryA]})])
  for(const [id,version,status,value] of [
    [ids.eventA,2,'SET',{special_free_category_ids:[ids.categoryA]}],
    [ids.eventB,3,'SET',{special_free_category_ids:[ids.categoryB]}],
    [ids.eventEmpty,4,'SET',{special_free_category_ids:[]}],
    [ids.eventPending,5,'PENDING_POLICY_VALUE',null],
  ]) await q("insert into erp.bc_policy_setting_events_v1 values($1,'ERP_DEC02',$2,$3,$4::jsonb,'2036-01-01T00:00:00Z')",[id,version,status,JSON.stringify(value)])
  // SQL NULL and JSON null have different source meanings, just as in Native.
  await q('update erp.bc_policy_setting_events_v1 set value=null where id=$1',[ids.eventPending])
  await q("insert into erp.bc_policy_setting_events_v1 values($1,'ACC_DEC01',1,'SET','{}','2036-01-01T00:00:00Z')",[ids.eventOther])
  await db.exec(sql)
  await test('INSTALL_EMPTY_NO_CATEGORY_OR_DATE_INVENTED',async()=>assert.deepEqual(await rows(),[]))
  await refused('SPECIAL_GOOD_REQUIRES_EXPLICIT_DATED_CATEGORY_SOURCE',()=>basis(ids.special,ids.categoryA,'2026-10-15T00:00:00Z'),/CURRENT_POLICY_EFFECTIVE_DATE_REQUIRED/)
  await test('ORDINARY_CONTRACTOR_REMAINS_PAYABLE_WITHOUT_FREE_POLICY',async()=>assert.equal((await basis(ids.ordinary,ids.categoryA,'2026-10-15T00:00:00Z')).nonpayable,false))
  const firstToken=await token(), firstRequest=randomUUID()
  let first
  await test('EXPLICIT_OWNER_DATE_REGISTRATION',async()=>{first=await record('2026-10-01',ids.eventA,firstRequest,firstToken);assert.equal(first.source_event_id,ids.eventA);assert.equal(first.effective_from,'2026-10-01')})
  await test('EXACT_REPLAY_SAME_RESPONSE_NO_NEW_ROW',async()=>{const before=await rows();assert.deepEqual(await record('2026-10-01',ids.eventA,firstRequest,firstToken),first);assert.deepEqual(await rows(),before)})
  await refused('REQUEST_CHANGED_INTENT_REFUSED',()=>record('2026-10-01',ids.eventA,firstRequest,firstToken,'DIFFERENT'),/REQUEST_INTENT_CHANGED/)
  await refused('STALE_TIMELINE_REFUSED',()=>record('2026-11-01',ids.eventB,randomUUID(),firstToken),/TIMELINE_STALE/)
  await refused('DUPLICATE_EFFECTIVE_DATE_REFUSED',async()=>record('2026-10-01',ids.eventB,randomUUID(),await token()),/EFFECTIVE_DATE_ALREADY_RECORDED/)
  await refused('WRONG_POLICY_EVENT_REFUSED',async()=>record('2026-11-01',ids.eventOther,randomUUID(),await token()),/EXACT_ERP_DEC02_EVENT_REQUIRED/)
  await refused('MISSING_EVENT_REFUSED',async()=>record('2026-11-01',randomUUID(),randomUUID(),await token()),/EXACT_ERP_DEC02_EVENT_REQUIRED/)
  await refused('UNCONFIRMED_OLDER_GOOD_REFUSED',()=>basis(ids.special,ids.categoryA,'2026-09-30T16:59:59.999999Z'),/EXACT_DATED_SPECIAL_POLICY_REQUIRED/)
  const old = await basis(ids.special,ids.categoryA,'2026-10-15T00:00:00Z')
  await test('D17_20_SOURCE_EVENT_CLOCK_IS_NOT_EFFECTIVE_DATE',async()=>{assert.equal(old.nonpayable,true);assert.equal(old.good_date,'2026-10-15');assert.equal(old.category_effective_from,'2026-10-01')})
  await q("update erp.bc_policy_settings_v1 set version=3,value=$1::jsonb where policy_key='ERP_DEC02'",[JSON.stringify({special_free_category_ids:[ids.categoryB]})])
  await refused('CHANGED_CURRENT_SETTING_CANNOT_GUESS_EFFECTIVE_DATE',()=>basis(ids.special,ids.categoryA,'2026-10-15T00:00:00Z'),/CURRENT_POLICY_EFFECTIVE_DATE_REQUIRED/)
  await record('2026-11-01',ids.eventB,randomUUID(),await token())
  await test('HISTORICAL_GOOD_KEEPS_ITS_DATED_CATEGORY_VERSION',async()=>assert.deepEqual(await basis(ids.special,ids.categoryA,'2026-10-15T00:00:00Z'),old))
  await test('REPLAY_ANSWER_STAYS_IDENTICAL_AFTER_LATER_POLICY',async()=>assert.deepEqual(await record('2026-10-01',ids.eventA,firstRequest,firstToken),first))
  const zones=['UTC','Asia/Jakarta','America/New_York','Pacific/Kiritimati']
  for(const zone of zones) {
    await q("select set_config('TimeZone',$1,false)",[zone])
    for(const [at,category,nonpayable,date] of [
      ['2026-10-31T16:59:59.999999Z',ids.categoryA,true,'2026-10-31'],
      ['2026-10-31T17:00:00Z',ids.categoryA,false,'2026-11-01'],
      ['2026-10-31T17:00:00Z',ids.categoryB,true,'2026-11-01'],
      ['2026-11-30T16:59:59.999999Z',ids.categoryB,true,'2026-11-30'],
    ]) await test('WIB_GOOD_BOUNDARY:'+zone+':'+at+':'+category,async()=>{const actual=await basis(ids.special,category,at);assert.equal(actual.nonpayable,nonpayable);assert.equal(actual.good_date,date)})
  }
  await q("select set_config('TimeZone','UTC',false)")
  await q("update erp.bc_policy_settings_v1 set version=4,value='{}' where policy_key='ERP_DEC02'")
  await record('2026-11-20',ids.eventEmpty,randomUUID(),await token())
  await test('EXPLICIT_EMPTY_CATEGORY_LIST_MEANS_NO_FREE_COMPONENTS',async()=>assert.equal((await basis(ids.special,ids.categoryB,'2026-11-21T00:00:00Z')).nonpayable,false))
  await q("update erp.bc_policy_settings_v1 set version=5,status='PENDING_POLICY_VALUE',value=null where policy_key='ERP_DEC02'")
  await record('2026-11-25',ids.eventPending,randomUUID(),await token())
  await refused('PENDING_GOOD_DATE_POLICY_REFUSES',()=>basis(ids.special,ids.categoryB,'2026-11-26T00:00:00Z'),/GOOD_DATE_CATEGORY_POLICY_REQUIRED/)
  await refused('INFINITE_GOOD_CLOCK_REFUSED',()=>basis(ids.special,ids.categoryA,'infinity'),/PHYSICAL_TIME_REQUIRED/)
  await refused('NULL_CONTRACTOR_REFUSED',()=>basis(null,ids.categoryA,'2026-11-01T00:00:00Z'),/IDENTITIES/)
  await refused('UNKNOWN_CATEGORY_REFUSED',()=>basis(ids.special,randomUUID(),'2026-11-01T00:00:00Z'),/EXACT_CONTRACTOR_AND_CATEGORY/)
  await refused('POLICY_UPDATE_REFUSED',()=>db.exec("update cp7_accessory_nonpayable.category_versions_v1 set reason='NO'"),/HISTORY_IMMUTABLE/)
  await refused('POLICY_DELETE_REFUSED',()=>db.exec('delete from cp7_accessory_nonpayable.category_versions_v1'),/HISTORY_IMMUTABLE/)
  await refused('POLICY_TRUNCATE_REFUSED',()=>db.exec('truncate cp7_accessory_nonpayable.category_versions_v1'),/HISTORY_IMMUTABLE/)
  for(const role of ['anon','authenticated','service_role']) {
    await db.exec('set role '+role)
    try { await test('PRIVATE_SCHEMA_NOT_EXPOSED:'+role,async()=>await assert.rejects(()=>q('select cp7_accessory_nonpayable.timeline_token_v1()'),/permission denied/)) }
    finally { await db.exec('reset role') }
  }
  await db.exec("set model.owner='no'")
  await refused('OWNER_RECHECK_REQUIRED',async()=>record('2026-12-01',ids.eventA,randomUUID(),await token()),/MODEL_OWNER_REQUIRED/)
  await db.exec("set model.owner='yes';set model.internal='no'")
  await refused('PRIVATE_INTERNAL_CONTEXT_REQUIRED',()=>basis(ids.special,ids.categoryA,'2026-11-01T00:00:00Z'),/MODEL_INTERNAL_REQUIRED/)
  const result={status:'ISOLATED_POSTGRES_GOOD_DATE_POLICY_FOUNDATION_PASS',engine:await scalar('select version()'),
    source_sha256:createHash('sha256').update(sql).digest('hex'),owner_decision:'D17-20',checks,
    actual_ERP_Native_cases:0,actual_Auth_cases:0,actual_browser_cases:0,installed_on_candidate:false,
    initial_GOOD_accrual_qualified:false,recost_qualified:false,reversal_qualified:false,
    production_go:false,independent_acceptance:false}
  if(process.argv[2])writeFileSync(resolve(process.argv[2]),JSON.stringify(result,null,2)+'\n')
  console.log(JSON.stringify({...result,checks:{PASS:checks.length}}))
} finally { await db.close() }
