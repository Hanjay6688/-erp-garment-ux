// Complete decision/refusal comparison using exact frozen Native access helpers.
// Auth identity and small profile tables are explicit kernel fixtures. This is
// not real Auth, a Native financial transaction or browser latency qualification.
import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs'
import {dirname} from 'node:path'
import {execFileSync} from 'node:child_process'
import {openRuntime} from '../tests/cp7/families/f04/runtime.mjs'

const paths=['scripts/cp7-src/sales/commands.sql','supabase/migrations/20260902104937_erp_v2_6_17_access_pattern_wip_control.sql','scripts/cp7_p19_sales_admission_benchmark.mjs']
const hash=b=>createHash('sha256').update(b).digest('hex')
const extract=(source,name)=>{
 const escaped=name.replaceAll('.','\\.')
 const start=source.search(new RegExp('create(?: or replace)? function '+escaped+'\\(','i'))
 assert.ok(start>=0,name)
 const match=/\bas\s+(\$\w*\$)/i.exec(source.slice(start));assert.ok(match,name)
 const body=start+match.index+match[0].length,end=source.indexOf(match[1]+';',body)
 assert.ok(end>=body,name)
 return source.slice(start,end+match[1].length+1)
}
const out=process.argv[2]||'cp7-proof/p19/SALES_ADMISSION_KERNEL.json'
const report={classification:'DISPOSABLE_ADMISSION_KERNEL_EXACT_NATIVE_HELPERS_EXPLICIT_AUTH_PROFILE_FIXTURES',
 git_head:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),
 working_tree_dirty:Boolean(execFileSync('git',['status','--porcelain','--',...paths],{encoding:'utf8'}).trim()),
 files_sha256:Object.fromEntries(paths.map(p=>[p,hash(readFileSync(p))])),Native_case_credit_added:0,
 full_P19_acceptance:false,independent_acceptance:false,production_go:false,authority_cached:false}
let db
try{
 db=await openRuntime();report.runtime=db.flavor;report.version=db.version
 const native=readFileSync(paths[1],'utf8'),current=readFileSync(paths[0],'utf8')
 const previous=extract(current,'cp7_sales.command_access'),candidate=extract(current,'cp7_sales.command_allowed')
 const negative=candidate.replace('cp7_sales.command_allowed(','cp7_sales.command_allowed_negative(').replace("'finance.ar.view'","'sales.invoice.view'")
 assert.notEqual(negative,candidate)
 const permissions=['sales.invoice.view','finance.ar.view','sales.invoice.create','sales.invoice.edit_draft','sales.invoice.post','sales.invoice.reverse','sales.payment.view','sales.payment.create','sales.payment.post','sales.payment.reverse','sales.return.view','sales.return.create','sales.return.post','sales.return.reverse']
 const actions=['CREATE','EDIT','POST','CANCEL','PAYMENT','PAYMENT_REVERSE','RETURN','RETURN_REVERSE','SALE_REVERSE',null,'INVALID']
 const literal=s=>s===null?'null':"'"+s.replaceAll("'","''")+"'"
 await db.execute(`create schema erp;create schema auth;create schema cp7_sales;
 create table erp.app_roles(id uuid primary key,role_code text unique,role_name text,is_active boolean,is_protected boolean,row_version bigint);
 create table erp.app_users(id uuid primary key,auth_user_id uuid unique,full_name text,role_id uuid,is_active boolean,row_version bigint);
 create table erp.app_permissions(permission_key text primary key,is_active boolean,sort_order integer);
 create table erp.app_role_permissions(role_id uuid,permission_key text,primary key(role_id,permission_key));
 create function auth.uid()returns uuid language sql stable as $$select nullif(current_setting('kernel.subject',true),'')::uuid$$;
 create function auth.jwt()returns jsonb language sql stable as $$select jsonb_build_object('role',current_setting('kernel.role',true))$$;
 ${['erp.current_app_role','erp.has_permission','erp.role_permission_keys','erp.get_my_access_v1'].map(n=>extract(native,n)).join('\n')}
 ${previous}${candidate}${negative}
 insert into erp.app_roles values('10000000-0000-4000-8000-000000000001','CUSTOM','Fixture custom',true,false,1);
 insert into erp.app_users values('10000000-0000-4000-8000-000000000002','10000000-0000-4000-8000-000000000003','Kernel fixture','10000000-0000-4000-8000-000000000001',true,1);
 insert into erp.app_permissions select x,true,0 from unnest(array[${permissions.map(literal)}])x;
 insert into erp.app_role_permissions select '10000000-0000-4000-8000-000000000001',permission_key from erp.app_permissions;
 select set_config('kernel.subject','10000000-0000-4000-8000-000000000003',false),set_config('kernel.role','authenticated',false);
 create function public.p19_decision(f text,a text)returns text language plpgsql as $$declare r text;begin
  if f not in('command_access','command_allowed','command_allowed_negative')then raise exception 'INVALID_KERNEL_FUNCTION';end if;
  execute format('select cp7_sales.%I($1)::text',f)into r using a;
  if(f='command_access'and(r::jsonb)->'allowed'='true'::jsonb)or(f<>'command_access'and r='true')then return 'ALLOW';end if;
  raise exception 'NON_POSITIVE_RESULT';exception when others then return SQLSTATE||':'||SQLERRM;end$$;
 create table public.p19_comparisons(state text,action text,old_decision text,candidate_decision text,negative_decision text);
 create function public.p19_compare(label text)returns void language plpgsql as $$declare a text;begin
  foreach a in array array[${actions.map(literal)}]loop
   insert into public.p19_comparisons values(label,a,public.p19_decision('command_access',a),public.p19_decision('command_allowed',a),public.p19_decision('command_allowed_negative',a));
  end loop;end$$;
 select public.p19_compare('ALL_PERMISSIONS_CUSTOM_ROLE');
 do $$declare p text;begin
  foreach p in array array[${permissions.map(literal)}]loop
   delete from erp.app_role_permissions where permission_key=p;
   perform public.p19_compare('REVOKED:'||p);
   insert into erp.app_role_permissions values('10000000-0000-4000-8000-000000000001',p);
  end loop;end$$;
 select public.p19_compare('PERMISSIONS_RESTORED');
 update erp.app_users set is_active=false;select public.p19_compare('USER_INACTIVE');update erp.app_users set is_active=true;
 update erp.app_roles set is_active=false;select public.p19_compare('ROLE_INACTIVE');update erp.app_roles set is_active=true;
 select set_config('kernel.role','service_role',false);select public.p19_compare('SERVICE_JWT_REJECTED');
 select set_config('kernel.role','anon',false);select public.p19_compare('ANON_JWT_REJECTED');select set_config('kernel.role','authenticated',false);
 select set_config('kernel.subject','',false);select public.p19_compare('AUTH_SUBJECT_ABSENT');select set_config('kernel.subject','10000000-0000-4000-8000-000000000003',false);
 select set_config('kernel.subject','10000000-0000-4000-8000-000000000009',false);select public.p19_compare('APP_USER_UNMAPPED');select set_config('kernel.subject','10000000-0000-4000-8000-000000000003',false);
 select set_config('kernel.role','OWNER',false);select public.p19_compare('CLAIM_ROLE_OWNER_REJECTED');select set_config('kernel.role','authenticated',false);
 update erp.app_roles set is_protected=true;select public.p19_compare('CUSTOM_ROLE_PROTECTED_HAS_NO_UNIVERSAL_GRANT');update erp.app_roles set is_protected=false;
 update erp.app_permissions set is_active=false where permission_key='finance.ar.view';select public.p19_compare('PERMISSION_CATALOG_INACTIVE');update erp.app_permissions set is_active=true where permission_key='finance.ar.view';
 update erp.app_roles set role_code='OWNER',is_protected=true;select public.p19_compare('NATIVE_ROLE:OWNER');
 delete from erp.app_role_permissions;select public.p19_compare('OWNER_NO_EXPLICIT_PERMISSIONS');
 update erp.app_users set is_active=false;select public.p19_compare('OWNER_USER_INACTIVE');update erp.app_users set is_active=true;
 update erp.app_roles set is_active=false;select public.p19_compare('OWNER_ROLE_INACTIVE');update erp.app_roles set is_active=true,is_protected=false;
 insert into erp.app_role_permissions select '10000000-0000-4000-8000-000000000001',permission_key from erp.app_permissions;select public.p19_compare('OWNER_NOT_PROTECTED_ALL_FINE_RIGHTS');
 delete from erp.app_role_permissions where permission_key='finance.ar.view';select public.p19_compare('OWNER_NOT_PROTECTED_AR_REVOKED');insert into erp.app_role_permissions values('10000000-0000-4000-8000-000000000001','finance.ar.view');
 update erp.app_roles set role_code='ADMIN',is_protected=false;select public.p19_compare('NATIVE_ROLE:ADMIN');
 update erp.app_roles set is_protected=true;select public.p19_compare('ADMIN_PROTECTED_HAS_NO_UNIVERSAL_GRANT');
 delete from erp.app_role_permissions where permission_key='finance.ar.view';select public.p19_compare('ADMIN_PROTECTED_AR_REVOKED');
 delete from erp.app_role_permissions;select public.p19_compare('ADMIN_NO_EXPLICIT_PERMISSIONS');
 update erp.app_roles set role_code='OWNER',is_protected=true;
 create function public.p19_time(f text,n integer,a text)returns numeric language plpgsql as $$declare start timestamptz:=clock_timestamp();i integer;v text;begin
  for i in 1..n loop v:=public.p19_decision(f,a);if v<>'ALLOW'then raise exception 'TIMING_NOT_ALLOWED';end if;end loop;
  return extract(epoch from clock_timestamp()-start)*1000;end$$;`)
 report.decisions=await db.query('select * from public.p19_comparisons')
 assert.equal(report.decisions.length,35*actions.length)
 report.differences=report.decisions.filter(r=>r.old_decision!==r.candidate_decision)
 report.negative_control_differences=report.decisions.filter(r=>r.old_decision!==r.negative_decision).length
 assert.deepEqual(report.differences,[])
 assert.ok(report.negative_control_differences>0,'WEAKENED_PERMISSION_CONTROL_NOT_DETECTED')
 report.samples=[]
 for(const action of ['POST','SALE_REVERSE']){
  const [v]=await db.query(`select public.p19_time('command_access',4000,${literal(action)}) predecessor_ms,public.p19_time('command_allowed',4000,${literal(action)}) candidate_ms`)
  report.samples.push({action,invocations:4000,current_profile:'NATIVE_PROTECTED_OWNER_NO_EXPLICIT_PERMISSIONS',...v})
 }
 report.ledger_canary_unchanged=(await db.query('select amount::text amount from public.f04_ledger_canary'))[0].amount==='12345.67'
 assert.ok(report.ledger_canary_unchanged)
 report.status='PASS'
}catch(e){report.status='INCOMPLETE';report.error=String(e);process.exitCode=1}
finally{if(db)await db.close();mkdirSync(dirname(out),{recursive:true});writeFileSync(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,runtime:report.runtime,comparisons:report.decisions?.length,negative_differences:report.negative_control_differences,samples:report.samples,error:report.error}))}
