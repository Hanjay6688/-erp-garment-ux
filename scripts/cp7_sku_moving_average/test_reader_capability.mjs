// Isolated PG17 role/reader controls. Pool and actor permission are explicit
// stand-ins; this proves no Native financial or real Auth acceptance.
import assert from 'node:assert/strict'
import {readFile,writeFile} from 'node:fs/promises'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE)
const db=new PGlite(),checks=[],values={}
const signature='cp7_sku_conversion.position_value_v2(uuid,uuid,text,numeric)'
const invocation="select cp7_sku_conversion.position_value_v2('11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222','GRADE_A',2) value"
const source=await readFile(new URL('./valuation.sql',import.meta.url),'utf8')
const start=source.indexOf('create function cp7_sku_conversion.position_value_v2(')
const end=source.indexOf('\ncreate function ',start+1)
assert.ok(start>=0&&end>start)
const ddl=source.slice(start,end)
async function refused(label,sql,code,message){
 try{await db.exec(sql);assert.fail('Expected refusal: '+label)}
 catch(error){assert.equal(error.code,code,label+': '+error.message);assert.ok(error.message.includes(message),error.message);checks.push({label,code,message:error.message})}
}
try{
 const engine=(await db.query('select version() v')).rows[0].v;assert.match(engine,/^PostgreSQL 17\./)
 await db.exec(`create schema erp;create schema cp7_sku_conversion;
 create role cp7_fg_read;create role authenticated;create role anon;create role service_role;
 create function erp.require_permission(k text)returns void language plpgsql as $$begin
  if k<>'finance.hpp.view'or current_setting('test.allowed',true)is distinct from 'yes'then
   raise exception using errcode='42501',message='TEST_ACTUAL_PERMISSION_REQUIRED';end if;end$$;
 create function cp7_sku_conversion.pool_quote_v2(uuid,uuid,text)returns jsonb language plpgsql as $$begin
  if current_setting('test.pool')='unknown'then raise exception 'CP7_SKU_POOL_HPP_UNKNOWN: seluruh komponen ekonomi termasuk reservasi harus diketahui';end if;
  if current_setting('test.pool')='invalid'then raise exception 'CP7_SKU_POOL_ATTRIBUTION_MISMATCH';end if;
  if current_setting('test.pool')='permission'then raise exception using errcode='42501',message='TEST_NESTED_PERMISSION';end if;
  return current_setting('test.pool')::jsonb;end$$;
 revoke all on function cp7_sku_conversion.pool_quote_v2(uuid,uuid,text)from public;
 create table cp7_sku_conversion.private_data(id uuid primary key);
 ${ddl}
 revoke all on function ${signature}from public,anon,authenticated,service_role;
 set test.allowed='yes';
 set test.pool='{"state":"KNOWN","average":"23.7500000000000000","revision":"0123456789abcdef0123456789abcdef"}';
 set role cp7_fg_read;`)
 await refused('missing_schema_capability',invocation,'42501','permission denied for schema')
 await db.exec('reset role;grant usage on schema cp7_sku_conversion to cp7_fg_read;set role cp7_fg_read;')
 await refused('missing_function_capability',invocation,'42501','permission denied for function')
 await db.exec(`reset role;grant execute on function ${signature}to cp7_fg_read;set role cp7_fg_read;`)
 values.known=(await db.query(invocation)).rows[0].value
 assert.deepEqual(values.known,{state:'KNOWN',hpp_version_id:null,hpp_version:null,cost_state:null,calculated_at:null,
  unit_cost:'23.750000',value:'47.500000',basis:'SKU_LOCATION_GRADE_MOVING_AVERAGE_V2',pool_revision:'0123456789abcdef0123456789abcdef',reserved_included:true})
 checks.push({label:'known_pool_exact_six_decimal_output',status:'PASS'})
 await db.exec("set test.pool='unknown';")
 values.unknown=(await db.query(invocation)).rows[0].value
 assert.equal(values.unknown.state,'UNKNOWN');assert.equal(values.unknown.value,null);assert.equal(values.unknown.unit_cost,null)
 checks.push({label:'unknown_does_not_become_zero_or_error',status:'PASS'})
 await db.exec("set test.pool='{\"state\":\"EMPTY\",\"revision\":\"0123456789abcdef0123456789abcdef\"}';")
 values.empty=(await db.query(invocation)).rows[0].value
 assert.equal(values.empty.state,'UNKNOWN');assert.equal(values.empty.value,null);assert.equal(values.empty.unit_cost,null)
 checks.push({label:'depleted_pool_keeps_card_available_without_inventing_cost',status:'PASS'})
 await db.exec("set test.pool='invalid';")
 await refused('unrelated_financial_refusal_preserved',invocation,'P0001','CP7_SKU_POOL_ATTRIBUTION_MISMATCH')
 await db.exec("set test.pool='permission';")
 await refused('nested_permission_refusal_preserved',invocation,'42501','TEST_NESTED_PERMISSION')
 await db.exec("set test.allowed='no';set test.pool='invalid';")
 await refused('current_permission_before_pool_read',invocation,'42501','TEST_ACTUAL_PERMISSION_REQUIRED')
 await db.exec("set test.allowed='yes';")
 for(const quantity of["null","-1","'NaN'::numeric","'Infinity'::numeric","'-Infinity'::numeric"])
  await refused('invalid_quantity_'+quantity,invocation.replace(',2) value',','+quantity+') value'),'P0001','CP7_SKU_POSITION_QTY_INVALID')
 await refused('read_role_cannot_read_other_private_function',"select cp7_sku_conversion.pool_quote_v2(null,null,null)",'42501','permission denied for function')
 await refused('read_role_cannot_read_private_tables','select *from cp7_sku_conversion.private_data','42501','permission denied for table')
 await refused('read_role_cannot_write_private_tables',"insert into cp7_sku_conversion.private_data values('33333333-3333-4333-8333-333333333333')",'42501','permission denied for table')
 for(const role of['authenticated','anon','service_role']){
  await db.exec('reset role;set role '+role)
  await refused(role+'_no_direct_private_access',invocation,'42501','permission denied for schema')
 }
 await db.exec('reset role;revoke usage on schema cp7_sku_conversion from cp7_fg_read;')
 assert.equal((await db.query("select has_schema_privilege('cp7_fg_read','cp7_sku_conversion','USAGE') allowed")).rows[0].allowed,false)
 checks.push({label:'unused_inverse_removes_exact_schema_lease',status:'PASS'})
 const report={status:'ISOLATED_POSTGRES17_READER_CAPABILITY_AND_CONTRACT_PASS',engine,checks,values,
  explicit_modeled_dependencies:['erp.require_permission(text)','cp7_sku_conversion.pool_quote_v2(uuid,uuid,text)'],
  actual_Native_cases:0,actual_Auth_cases:0,production_go:false,independent_acceptance:false}
 if(process.env.CP7_READER_REPORT)await writeFile(process.env.CP7_READER_REPORT,JSON.stringify(report,null,2)+'\n')
 console.log(JSON.stringify({status:report.status,checks:checks.length,actual_Native_cases:0}))
}finally{await db.close()}
