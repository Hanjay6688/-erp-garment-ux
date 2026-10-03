// @vitest-environment node
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
import {beforeAll,afterAll,test,expect} from 'vitest'
import {openRuntime,jsonArg,textArg} from './f04/runtime.mjs'

// Actual isolated PostgreSQL authority controls. They do not grant Native40,
// Native284, financial correctness or measured HTTP performance credit.
let db:Awaited<ReturnType<typeof openRuntime>>
const actor='22000000-0000-4000-8000-000000000001'
const actions=['CREATE','EDIT','POST','CANCEL','PAYMENT','PAYMENT_REVERSE','RETURN','RETURN_REVERSE','SALE_REVERSE']
const all=['sales.invoice.view','finance.ar.view','sales.invoice.create','sales.invoice.edit_draft','sales.invoice.post','sales.invoice.reverse','sales.payment.view','sales.payment.create','sales.payment.post','sales.payment.reverse','sales.return.view','sales.return.create','sales.return.post','sales.return.reverse']
const source=readFileSync('scripts/cp7-src/sales/commands.sql','utf8')
const candidate=source.slice(source.indexOf('create function cp7_sales.command_access('),source.indexOf('\n\ncreate function cp7_sales.apply_command'))
const read=readFileSync('scripts/cp7-src/sales/read.sql','utf8')
const accessNow=read.slice(read.indexOf('create function cp7_sales.access_now()'),read.indexOf('\n\ncreate function cp7_sales.review_token'))
const reference=readFileSync('tests/cp7/fixtures/sales-command-access-6127.sql','utf8')
const claims=(role='authenticated',id:string|null=actor)=>`select set_config('request.jwt.claims',${textArg(JSON.stringify({role,sub:id}))},false);`
const subject=(role:string,permissions:string[]=all,active=true,roleActive=true,protectedOwner=false)=>`update public.sales_guard_subject set role_code=${textArg(role)},permissions=array(select jsonb_array_elements_text(${jsonArg(permissions)})),active=${active},role_active=${roleActive},protected_owner=${protectedOwner};`

beforeAll(async()=>{
 db=await openRuntime()
 await db.execute(`do $$begin if not exists(select 1 from pg_roles where rolname='postgres')then create role postgres nologin;end if;end$$;
 create role authenticator nologin nosuperuser nobypassrls;
 create schema erp;create schema auth;create schema cp7_sales;
 create table public.sales_guard_subject(actor uuid,role_code text,permissions text[],active boolean,role_active boolean,protected_owner boolean,row_version bigint);
 insert into public.sales_guard_subject values('${actor}','ADMIN',array[]::text[],true,true,false,1);
 create sequence public.sales_access_reads;
 create function auth.jwt()returns jsonb language sql stable as $$select current_setting('request.jwt.claims')::jsonb$$;
 create function auth.uid()returns uuid language sql stable as $$select(auth.jwt()->>'sub')::uuid$$;
 create function erp.has_permission(k text)returns boolean language sql stable security definer set search_path='' as $$
  select coalesce((select active and role_active and(protected_owner and role_code='OWNER' or k=any(permissions))from public.sales_guard_subject where actor=auth.uid()),false)$$;
 create function erp.get_my_access_v1()returns jsonb language plpgsql stable security definer set search_path='' as $$
 declare s public.sales_guard_subject;
 begin
  perform nextval('public.sales_access_reads');
  select * into s from public.sales_guard_subject where actor=auth.uid();
  if s.actor is null or not s.active or not s.role_active then return '{"allowed":false}'::jsonb;end if;
  return jsonb_build_object('allowed',true,'profile',jsonb_build_object('role_code',s.role_code,'row_version',s.row_version::text),'permissions',to_jsonb(s.permissions));
 end$$;
 ${accessNow};${reference};${candidate};
 create function public.sales_guard_outcome(action text,original boolean)returns jsonb language plpgsql security definer set search_path='' as $$
 declare a jsonb;
 begin
  if original then a:=cp7_sales.reference_command_access(action);else a:=cp7_sales.command_access(action);end if;
  return jsonb_build_object('allowed',true,'access',a);
 exception when others then return jsonb_build_object('allowed',false,'sqlstate',SQLSTATE,'message',SQLERRM);
 end$$;
 alter function public.sales_guard_outcome(text,boolean)owner to postgres;
 alter function erp.get_my_access_v1()owner to postgres;alter function erp.has_permission(text)owner to postgres;
 alter function cp7_sales.reference_command_access(text)owner to postgres;alter function cp7_sales.command_access(text)owner to postgres;
 grant usage on schema erp,auth,cp7_sales to postgres;grant select on public.sales_guard_subject to postgres;
 grant usage,select on sequence public.sales_access_reads to postgres;
 create function public.sales_guard_compare(jwt jsonb,action text,read_original boolean)returns table(original jsonb,candidate jsonb)language plpgsql as $$
 begin
  perform set_config('request.jwt.claims',jwt::text,true);
  return query select case when read_original then public.sales_guard_outcome(action,true)else null::jsonb end,public.sales_guard_outcome(action,false);
 end$$;`)
})
afterAll(async()=>{await db?.close()})

async function compare(role:string,permissions:string[]=all,active=true,roleActive=true,protectedOwner=false,action:string|null='POST',jwtRole='authenticated',id:string|null=actor){
 await db.execute(subject(role,permissions,active,roleActive,protectedOwner))
 const rows=await db.query(`select * from public.sales_guard_compare(${jsonArg({role:jwtRole,sub:id})},${action===null?'null':textArg(action)},true)`)
 expect(rows[0].candidate).toEqual(rows[0].original)
 return rows[0].candidate
}

test('accepted authority outcomes stay exact for every action, role and missing fine permission',async()=>{
 for(const role of ['OWNER','ADMIN','STAFF','CUSTOM'])for(const action of actions){
  await compare(role,all,true,true,role==='OWNER',action)
  for(const missing of all)await compare(role,all.filter(p=>p!==missing),true,true,false,action)
 }
},60000)

test('null action, bad JWT, missing identity, inactive user and inactive role retain exact refusals',async()=>{
 for(const action of [null,'TYPO'])await compare('ADMIN',all,true,true,false,action)
 for(const jwt of ['anon','service_role',''])await compare('OWNER',all,true,true,true,'POST',jwt)
 await compare('ADMIN',all,true,true,false,'POST','authenticated',null)
 await compare('ADMIN',all,false)
 await compare('ADMIN',all,true,false)
})

test('revocation and role demotion remain live on the next guard invocation',async()=>{
 const allowed=await compare('ADMIN',all,true,true,false,'SALE_REVERSE');expect(allowed.allowed).toBe(true)
 const revoked=await compare('ADMIN',all.filter(p=>p!=='sales.invoice.reverse'),true,true,false,'SALE_REVERSE');expect(revoked.allowed).toBe(false);expect(revoked.message).toBe('CP7_SALES_WRITE_DENIED')
 const demoted=await compare('STAFF',all,true,true,false,'SALE_REVERSE');expect(demoted.allowed).toBe(false);expect(demoted.message).toBe('CP7_SALES_OWNER_ADMIN_REQUIRED')
})

test('complete access is read once per invocation and a new invocation returns a fresh profile',async()=>{
 await db.execute(claims()+subject('ADMIN')+"select setval('public.sales_access_reads',1,false);")
 const invoke=async()=>{
  const rows=await db.query(`select * from public.sales_guard_compare(${jsonArg({role:'authenticated',sub:actor})},'POST',false)`)
  return rows[0].candidate
 }
 const first=await invoke();expect(first.allowed).toBe(true)
 const initial=await db.query('select last_value,is_called from public.sales_access_reads');expect(initial).toEqual([{last_value:1,is_called:true}])
 await db.execute("update public.sales_guard_subject set row_version=2;")
 const second=await invoke();expect(second.access.profile.row_version).toBe('2')
 const updated=await db.query('select last_value from public.sales_access_reads');expect(updated).toEqual([{last_value:2}])
})

test('reference authority oracle is pinned to the accepted source',()=>{
 expect(createHash('sha256').update(reference).digest('hex')).toBe('6953889f355f03d916d06c58290cefff81f4dc7558621d5a03996cc49240a7a3')
})
