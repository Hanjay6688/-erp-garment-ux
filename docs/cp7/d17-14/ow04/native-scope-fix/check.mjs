// Actual scope assertion and role/RLS controls; not ERP Native posting proof.
import fs from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {createHash} from 'node:crypto';
const {PGlite}=await import(process.env.PGLITE_MODULE||'@electric-sql/pglite');
const repo=process.env.ERP_REPO||process.cwd(), here=path.dirname(fileURLToPath(import.meta.url));
const prefix='scripts/cp7_customer_credit/', read=n=>fs.readFile(repo+'/'+prefix+n,'utf8');
const files=['admission/02_owning_wrapper.proposal.sql','coordinator/07_capabilities_and_quote.sql','coordinator/08_outer_wrapper.sql'];
const sources=Object.fromEntries(await Promise.all(files.map(async n=>[n,await read(n)])));
const sig='cp7_credit.assert_return_native_scope_cleared_v1()';
const start=sources[files[1]].indexOf('create function '+sig), end=sources[files[1]].indexOf('end $$;',start);
assert(start>=0&&end>start); const helper=sources[files[1]].slice(start,end+7);
const old=execFileSync('git',['show','a96079dc0f0ee5aadb8bcd07f4fce7a434a12227:'+prefix+files[2]],{cwd:repo,encoding:'utf8'});
const oldStart=old.indexOf(' if exists(select 1 from cp7_credit.return_native_scope'), oldEnd=old.indexOf('end if;',oldStart);
assert(oldStart>=0&&oldEnd>oldStart); const oldCheck=old.slice(oldStart,oldEnd+7);
for(const n of [files[0],files[2]]){assert(sources[n].includes('perform '+sig+';'));assert(!sources[n].includes('from cp7_credit.return_native_scope'));}
assert(sources[files[1]].includes("'assert_return_native_scope_cleared_v1()']loop"));
assert(sources[files[1]].includes(sig+',cp7_credit.seal_return_settlement'));
const cases=[], db=new PGlite();
async function control(name,sql,expected){
 await db.exec('begin');let error;
 try{await db.exec(sql);}catch(e){error=e;}
 await db.exec('rollback');
 if(expected){assert(error,name);assert(error.code===expected||error.message.includes(expected),JSON.stringify({name,message:error.message,code:error.code}));}
 else if(error)throw error;
 cases.push({name,status:'PASS',expected_refusal:expected||null,observed_error:error?.message||null});
}
try{
 await fs.writeFile(here+'/DECLARATION.json',JSON.stringify({classification:'ISOLATED_ACTUAL_SQL_ROLE_RLS_CONTROLS',candidate_base:'a96079dc0f0ee5aadb8bcd07f4fce7a434a12227',expected:'Old query denied42501; helper observes every own pid/tx leak despite RLS; other pid/tx ignored; no table rights or outsider execution; no authority/posting/commit claim.'},null,2)+'\n');
 await db.exec(`create role cp7_credit_write nologin noinherit nosuperuser nobypassrls;
 create role authenticated nologin;create role anon nologin;create role service_role nologin;create role cp7_sales_write nologin;
 create schema cp7_credit;create table cp7_credit.return_native_scope(backend_pid int,transaction_id bigint,actor uuid,completed boolean);
 alter table cp7_credit.return_native_scope enable row level security;
 create policy ow04_deny_direct on cp7_credit.return_native_scope for all to public using(false)with check(false);
 grant usage on schema cp7_credit to cp7_credit_write,authenticated,anon,service_role,cp7_sales_write;
 ${helper}
 alter function ${sig} owner to postgres;
 revoke all on function ${sig} from public,authenticated,anon,service_role,cp7_sales_write;
 grant execute on function ${sig} to cp7_credit_write;`);
 const own='insert into cp7_credit.return_native_scope values(pg_backend_pid(),txid_current(),null,false);';
 await control('FIRST_RED_OUTER_DIRECT_EMPTY_TABLE',`set local role cp7_credit_write;do $$begin ${oldCheck}end $$;`,'42501');
 await control('FIXED_EMPTY_SCOPE_ALLOWS',`set local role cp7_credit_write;select ${sig};`);
 await control('OWN_SCOPE_LEAK_REFUSED',own+`set local role cp7_credit_write;select ${sig};`,'CP7_CREDIT_NATIVE_SCOPE_NOT_CLEARED');
 await control('COMPLETED_SCOPE_STILL_REFUSED',own+`update cp7_credit.return_native_scope set completed=true;set local role cp7_credit_write;select ${sig};`,'CP7_CREDIT_NATIVE_SCOPE_NOT_CLEARED');
 await control('OTHER_ACTOR_SAME_PID_TX_STILL_REFUSED',own+`update cp7_credit.return_native_scope set actor='00000000-0000-0000-0000-000000000002';set local role cp7_credit_write;select ${sig};`,'CP7_CREDIT_NATIVE_SCOPE_NOT_CLEARED');
 await control('OTHER_BACKEND_IGNORED',`insert into cp7_credit.return_native_scope values(pg_backend_pid()+1,txid_current(),null,false);set local role cp7_credit_write;select ${sig};`);
 await control('OTHER_TRANSACTION_IGNORED',`insert into cp7_credit.return_native_scope values(pg_backend_pid(),txid_current()+1,null,false);set local role cp7_credit_write;select ${sig};`);
 for(const role of ['authenticated','anon','service_role','cp7_sales_write'])await control('NO_HELPER_EXEC_'+role,`set local role ${role};select ${sig};`,'42501');
 for(const sql of ['select * from cp7_credit.return_native_scope','delete from cp7_credit.return_native_scope','insert into cp7_credit.return_native_scope values(1,1,null,false)','update cp7_credit.return_native_scope set completed=true'])await control('NO_TABLE_CAPABILITY_'+sql.split(' ')[0],`set local role cp7_credit_write;${sql};`,'42501');
 await control('HYPOTHETICAL_SELECT_GRANT_HIDES_LEAK_VIA_RLS',own+`grant select on cp7_credit.return_native_scope to cp7_credit_write;set local role cp7_credit_write;do $$begin ${oldCheck}if (select count(*)from cp7_credit.return_native_scope)<>0 then raise exception 'unexpected visibility';end if;end $$;`);
 await control('DEFINER_STILL_SEES_LEAK_UNDER_FALSE_RLS',own+`grant select on cp7_credit.return_native_scope to cp7_credit_write;set local role cp7_credit_write;select ${sig};`,'CP7_CREDIT_NATIVE_SCOPE_NOT_CLEARED');
 const meta=await db.query(`select pg_get_userbyid(proowner) owner,prosecdef,proconfig,has_table_privilege('cp7_credit_write','cp7_credit.return_native_scope','SELECT') may_read,has_table_privilege('cp7_credit_write','cp7_credit.return_native_scope','UPDATE') may_update from pg_proc where oid='${sig}'::regprocedure`);
 assert.deepEqual(meta.rows,[{owner:'postgres',prosecdef:true,proconfig:['search_path=""','TimeZone=UTC'],may_read:false,may_update:false}]);
 cases.push({name:'EXACT_OWNER_CONFIG_NO_TABLE_GRANTS',status:'PASS'});
 await fs.writeFile(here+'/SOURCE_PINS.json',JSON.stringify(Object.fromEntries(Object.entries(sources).map(([n,s])=>[prefix+n,createHash('sha256').update(s).digest('hex')])),null,2)+'\n');
 await fs.writeFile(here+'/RESULT.json',JSON.stringify({classification:'ISOLATED_SQL_NOT_ERP_NATIVE',status:'PASS',count:cases.length,cases},null,2)+'\n');
 console.log(JSON.stringify({status:'PASS',count:cases.length}));
}catch(e){await fs.writeFile(here+'/FIRST_FAILURE.json',JSON.stringify({message:e.message,code:e.code,cases},null,2)+'\n');console.error(e);process.exitCode=1;}finally{await db.close();}
