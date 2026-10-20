// Exact source helper + isolated synthetic table/roles. No ERP Native/schema,
// capture function, authorization stub, actual product data, or installer.
import{readFile,writeFile}from'node:fs/promises';
import{createHash}from'node:crypto';
import{dirname,resolve}from'node:path';
import{fileURLToPath}from'node:url';
import assert from'node:assert/strict';
const directory=dirname(fileURLToPath(import.meta.url));
const repo=resolve(process.env.OW01_REPO??process.cwd());
const planFile=resolve(repo,'scripts/cp7-src/plan-native/staged.sql');
const accessoryFile=resolve(repo,'scripts/cp7-src/reminders/accessory-source.sql');
const bundleFile=resolve(repo,'scripts/cp7_reminder_v2_bundle.py');
const[plan,accessory,bundle,expectedText]=await Promise.all([planFile,accessoryFile,bundleFile,resolve(directory,'EXPECTED.json')].map(p=>readFile(p,'utf8')));
const expected=JSON.parse(expectedText);const sha=x=>createHash('sha256').update(x).digest('hex');
const match=plan.match(/create function cp7_plan_native\.after_snapshot\([^]*?\n\$\$;/g);
assert.equal(match?.length,1);const exactHelper=match[0];
assert(accessory.includes('cp7_plan_native.after_snapshot(i.xmin,i.recorded_at,j.captured_at,mark.source_snapshot)'));
const{PGlite}=await import(process.env.OW01_PGLITE_MODULE??'@electric-sql/pglite');
const db=new PGlite();
const result={scope:expected.scope,native_execution_proven:false,expected_sha256:sha(expectedText),
 source_sha256:{[planFile]:sha(plan),[accessoryFile]:sha(accessory),[bundleFile]:sha(bundle)},helper_sha256:sha(exactHelper),observations:[]};
let step='setup';
const query=`select count(*)::text as value from cp7_plan_native.intents i where i.target_key='synthetic-target'
 and cp7_plan_native.after_snapshot(i.xmin,i.recorded_at,'2026-10-19T00:00:00Z'::timestamptz,pg_current_snapshot())`;
const scalar=async(sql,args=[])=>(await db.query(sql,args)).rows[0].value;
async function refused(name,want){
 let caught;try{await scalar(query);}catch(error){caught=error;}
 const observed=caught?{sqlstate:caught.code,message:caught.message}:null;
 result.observations.push({name,observed});assert.deepEqual(observed,want);
}
try{
 await db.exec(`create role anon;create role authenticated;create role service_role;
 create role cp7_capture nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
 create role cp7_plan_writer nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
 create schema cp7_plan_native authorization cp7_plan_writer;
 revoke all on schema cp7_plan_native from public,anon,authenticated,service_role;
 grant usage on schema cp7_plan_native to cp7_capture;
 create table cp7_plan_native.intents(id uuid primary key,target_key text,cutting_group_id uuid,recorded_at timestamptz);
 alter table cp7_plan_native.intents owner to cp7_plan_writer;
 alter table cp7_plan_native.intents enable row level security;
 create policy private_intents on cp7_plan_native.intents for all to public using(false)with check(false);
 grant select(id,target_key,cutting_group_id,recorded_at,xmin)on cp7_plan_native.intents to cp7_capture;`);
 await db.exec(exactHelper);
 await db.exec(`alter function cp7_plan_native.after_snapshot(xid,timestamptz,timestamptz,pg_snapshot)owner to cp7_plan_writer;
 revoke all on function cp7_plan_native.after_snapshot(xid,timestamptz,timestamptz,pg_snapshot)from public,anon,authenticated,service_role;
 set role cp7_capture;`);
 step='initial_privileges';
 const privileges={schema_usage:await scalar("select has_schema_privilege(current_user,'cp7_plan_native','USAGE')as value"),
  intents_columns_select:await scalar("select has_column_privilege(current_user,'cp7_plan_native.intents','xmin','SELECT')and has_column_privilege(current_user,'cp7_plan_native.intents','recorded_at','SELECT')as value"),
  helper_execute:await scalar("select has_function_privilege(current_user,'cp7_plan_native.after_snapshot(xid,timestamptz,timestamptz,pg_snapshot)','EXECUTE')as value")};
 assert.deepEqual(privileges,{schema_usage:expected.before.schema_usage,intents_columns_select:expected.before.intents_columns_select,helper_execute:expected.before.helper_execute});
 result.observations.push({name:step,observed:privileges});
 step='empty_query_without_execute';await refused(step,expected.before.empty_query);
 await db.exec('reset role');
 await db.exec(`insert into cp7_plan_native.intents values('00000000-0000-0000-0000-000000000001','synthetic-target',null,'2026-10-20T00:00:00Z');set role cp7_capture;`);
 step='one_row_query_without_execute';await refused(step,expected.before.one_row_query);
 await db.exec('reset role');
 await db.exec(`grant execute on function cp7_plan_native.after_snapshot(xid,timestamptz,timestamptz,pg_snapshot)to cp7_capture;set role cp7_capture;`);
 step='one_row_narrow_execute_control';const one=await scalar(query);assert.equal(one,expected.narrow_execute_control.one_row_query_count);result.observations.push({name:step,observed:one});
 step='control_did_not_add_writes_or_role_membership';
 const control={capture_table_write:await scalar("select has_table_privilege(current_user,'cp7_plan_native.intents','INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')as value"),
 capture_writer_membership:await scalar("select pg_has_role(current_user,'cp7_plan_writer','MEMBER')as value")};
 assert.deepEqual(control,{capture_table_write:false,capture_writer_membership:false});result.observations.push({name:step,observed:control});
 await db.exec('reset role');await db.exec('delete from cp7_plan_native.intents');await db.exec('set role cp7_capture');
 step='empty_narrow_execute_control';const empty=await scalar(query);assert.equal(empty,expected.narrow_execute_control.empty_query_count);result.observations.push({name:step,observed:empty});
 result.status='PASS';await writeFile(resolve(directory,'RESULT.json'),JSON.stringify(result,null,2)+'\n');
 process.stdout.write(JSON.stringify({scope:result.scope,status:result.status,native_execution_proven:false,observations:result.observations})+'\n');
}catch(error){
 const failure={...result,status:'FAIL',step,message:error.message,code:error.code};
 try{await writeFile(resolve(directory,'FIRST_FAILURE.json'),JSON.stringify(failure,null,2)+'\n',{flag:'wx'});}catch(e){if(e.code!=='EEXIST')throw e;}
 process.stderr.write(JSON.stringify({step,message:error.message,code:error.code})+'\n');process.exitCode=1;
}finally{await db.close();}
