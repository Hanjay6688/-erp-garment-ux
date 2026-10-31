// Isolated PostgreSQL controls. No ERP, Supabase, Auth or production connection.
import assert from 'node:assert/strict'
import {readFileSync,writeFileSync} from 'node:fs'
import {fileURLToPath,pathToFileURL} from 'node:url'
import {dirname,resolve} from 'node:path'
import {createHash} from 'node:crypto'

const here=dirname(fileURLToPath(import.meta.url)),modulePath=process.env.PGLITE_MODULE
assert(modulePath,'PGLITE_MODULE must identify the separately pinned local control engine')
const {PGlite}=await import(pathToFileURL(resolve(modulePath)).href)
const db=new PGlite(),original=readFileSync(resolve(here,'ORIGINAL.sql'),'utf8'),fixed=readFileSync(resolve(here,'PREPARED.sql'),'utf8')
const hash=text=>createHash('sha256').update(text).digest('hex')
const reference=JSON.parse(readFileSync(resolve(here,'ACTUAL_REFERENCE.json'),'utf8'))
assert.equal(hash(original),reference.original_sha256)
const category='00000000-0000-4000-8000-000000000101',other='00000000-0000-4000-8000-000000000102'
const material='00000000-0000-4000-8000-000000000201',unlisted='00000000-0000-4000-8000-000000000202',fabric='00000000-0000-4000-8000-000000000203'
const special='00000000-0000-4000-8000-000000000301',normal='00000000-0000-4000-8000-000000000302',open='00000000-0000-4000-8000-000000000303'
const q=async(sql,args=[])=>await db.query(sql,args)
const value=async(m,c,at)=>(await q('select erp.bc_free_basis_v1($1::uuid,$2::uuid,$3::timestamptz) result',[m,c,at])).rows[0].result
const expected={category_id:category,policy_version:'17'}
const dates=[['2026-09-30T16:59:59.999999Z',false],['2026-09-30T17:00:00Z',true],
 ['2026-10-01T00:00:00Z',true],['2026-10-30T17:00:00Z',true],
 ['2026-10-31T16:59:59.999999Z',true],['2026-10-31T17:00:00Z',false],['2026-11-01T00:00:00Z',false],[null,false]]
const zones=['UTC','Asia/Jakarta','America/New_York','Pacific/Kiritimati']
const metadata=async()=>(await q("select pg_get_userbyid(proowner) owner,prosecdef,provolatile,proisstrict,proleakproof,proretset,proparallel,prokind,procost,prorows,pronargdefaults,provariadic::text,proargmodes,proallargtypes::text,proconfig,proacl::text,proargnames,pg_get_function_identity_arguments(oid) args,pg_get_function_result(oid) result from pg_proc where oid='erp.bc_free_basis_v1(uuid,uuid,timestamptz)'::regprocedure")).rows[0]
const data=async()=>(await q("select (select jsonb_agg(to_jsonb(m)order by id)from erp.materials m) materials,(select jsonb_agg(to_jsonb(v)order by contractor_id)from erp.contractor_hpp_policy_versions v) policies,(select to_jsonb(p)from erp.control_policy p) setting")).rows[0]
try{
 await db.exec(`create schema erp;
 create table erp.materials(id uuid primary key,material_type text,accessory_category_id uuid);
 create table erp.contractor_hpp_policy_versions(contractor_id uuid,is_special boolean,effective_from date,effective_to date);
 create table erp.control_policy(version bigint,value jsonb);
 create function erp.bc_policy_v1(text)returns jsonb language sql stable set search_path='' as $$select value from erp.control_policy$$;
 create function erp.bc_policy_version_v1(text)returns bigint language sql stable set search_path='' as $$select version from erp.control_policy$$;`)
 await q('insert into erp.materials values($1,\'ACCESSORY\',$2),($3,\'ACCESSORY\',$4),($5,\'FABRIC\',$2)',[material,category,unlisted,other,fabric])
 await q("insert into erp.contractor_hpp_policy_versions values($1,true,'2026-10-01','2026-10-31'),($2,false,'2026-10-01','2026-10-31'),($3,true,'2026-10-01',null)",[special,normal,open])
 await q('insert into erp.control_policy values(17,$1::jsonb)',[JSON.stringify({special_free_category_ids:[category]})])
 await db.exec(original+';');await db.exec('revoke all on function erp.bc_free_basis_v1(uuid,uuid,timestamptz) from public')
 const beforeMetadata=await metadata(),beforeData=await data(),old=[]
 for(const zone of zones){await q("select set_config('TimeZone',$1,false)",[zone]);for(const [at,eligible]of dates){const result=await value(material,special,at);old.push({zone,at,expected:eligible?expected:null,actual:result})}}
 assert(old.some(row=>JSON.stringify(row.expected)!==JSON.stringify(row.actual)),'THE_ORIGINAL_DATE_BUG_MUST_ACTUALLY_REPRODUCE')
 await db.exec(fixed+';');assert.deepEqual(await metadata(),beforeMetadata,'ACL_OWNER_SECURITY_AND_SIGNATURE_UNCHANGED')
 const actual=[]
 for(const zone of zones){await q("select set_config('TimeZone',$1,false)",[zone]);for(const [at,eligible]of dates){const result=await value(material,special,at);assert.deepEqual(result,eligible?expected:null);actual.push({zone,at,result})}}
 for(const [m,c,at]of[[unlisted,special,dates[2][0]],[fabric,special,dates[2][0]],[material,normal,dates[2][0]],[other,special,dates[2][0]],[material,other,dates[2][0]]])assert.equal(await value(m,c,at),null)
 assert.deepEqual(await value(material,open,'2030-12-31T23:59:59Z'),expected)
 await db.exec('begin;update erp.control_policy set value=null');assert.equal(await value(material,special,dates[2][0]),null);await db.exec('rollback')
 assert.deepEqual(await data(),beforeData,'READS_AND_FUNCTION_REPLACEMENT_DID_NOT_CHANGE_FIXTURE_ROWS')
 const result={status:'ISOLATED_POSTGRES_WIB_INCLUSIVE_DATE_CONTROLS_PASS',engine:(await q('select version() version')).rows[0].version,
  original_sha256:hash(original),prepared_sha256:hash(fixed),business_timezones:zones,temporal_checks:actual.length,
  original_mismatches:old.filter(row=>JSON.stringify(row.expected)!==JSON.stringify(row.actual)),
  ineligible_pending_and_open_end_checks:7,exact_function_metadata_unchanged:true,fixture_rows_unchanged:true,
  actual_ERP_Native_cases:0,actual_Auth_cases:0,actual_browser_cases:0,installed_on_candidate:false,
  Afui_GOOD_nonpayable_path_complete:false,production_go:false,independent_acceptance:false}
 if(process.argv[2])writeFileSync(resolve(process.argv[2]),JSON.stringify(result,null,2)+'\n')
 console.log(JSON.stringify({...result,original_mismatches:result.original_mismatches.length}))
}finally{await db.close()}
