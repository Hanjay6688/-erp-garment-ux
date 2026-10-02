// @vitest-environment node
import {readFileSync} from 'node:fs'
import {beforeEach,afterEach,test} from 'vitest'
import {openRuntime} from './f04/runtime.mjs'

// Isolated guard controls, not full Auth/financial/Native40 qualification.
let db:Awaited<ReturnType<typeof openRuntime>>
const actor='11000000-0000-4000-8000-000000000001'
const foreign='11000000-0000-4000-8000-000000000002'
const base=readFileSync('scripts/cp7-src/procurement/accepted-deltas.sql','utf8').split('create or replace function erp.require_internal()',2)[1].split('$function$;',1)[0]
const sales=readFileSync('scripts/cp7_sales_bundle.py','utf8').split('ADMISSION="""',2)[1].split('"""',1)[0]
const guard=base.replace(' v_app_role:=erp.current_app_role();',sales+' v_app_role:=erp.current_app_role();')
beforeEach(async()=>{
 db=await openRuntime()
 await db.execute(`do $$begin if not exists(select 1 from pg_roles where rolname='postgres')then create role postgres nologin;end if;end$$;
 create role authenticator nologin nosuperuser nobypassrls;
 create schema erp;create schema auth;create schema cp7_procurement;create schema cp7_material;create schema cp7_supplier_return;create schema cp7_sales;
 create table public.guard_subject(actor uuid,role_code text,is_active boolean,role_active boolean,permissions text[]);
 insert into public.guard_subject values('${actor}','CUSTOM',true,true,array['warehouse.procurement.view','warehouse.procurement.post']);
 create function auth.jwt()returns jsonb language sql stable as $$select current_setting('request.jwt.claims')::jsonb$$;
 create function auth.uid()returns uuid language sql stable as $$select(auth.jwt()->>'sub')::uuid$$;
 create function erp.current_app_role()returns text language sql stable security definer set search_path='' as $$select role_code from public.guard_subject where actor=auth.uid()and is_active and role_active$$;
 create function erp._idempotency_actor_key()returns text language sql stable as $$select auth.uid()::text$$;
 create function erp.has_permission(k text)returns boolean language plpgsql stable security definer set search_path='' as $$begin
  if current_setting('guard_test.forbid_scope_permission_read',true)='true'then raise exception 'UNNECESSARY_SCOPE_PERMISSION_READ';end if;
  return exists(select 1 from public.guard_subject where actor=auth.uid()and is_active and role_active and k=any(permissions));end$$;
 create table erp.cutting_bridge_execution_context(backend_pid integer,transaction_id bigint,actor_key text,action text,permission_key text);
 create table erp.bs_resolution_execution_context(like erp.cutting_bridge_execution_context);
 create table erp.cp6_laundry_qc_execution_context(like erp.cutting_bridge_execution_context);
 create table cp7_procurement.execution_context(backend_pid integer,transaction_id bigint,actor uuid,action text,permission_key text);
 create table cp7_material.execution_context(like cp7_procurement.execution_context);
 create table cp7_supplier_return.execution_context(like cp7_procurement.execution_context);
 create table cp7_sales.command_context(backend_pid integer,transaction_id bigint,actor uuid,action text);
 create function cp7_sales.command_access(action text)returns jsonb language plpgsql stable security definer set search_path='' as $$begin
  if not erp.has_permission('sales.invoice.post')then raise exception using errcode='42501',message='CP7_SALES_ACCESS_DENIED';end if;return'{"allowed":true}'::jsonb;end$$;
 create or replace function erp.require_internal()${guard}$function$;
 create function public.guard_allow()returns void language plpgsql security definer set search_path='' as $$begin perform erp.require_internal();end$$;
 create function public.guard_deny()returns void language plpgsql security definer set search_path='' as $$begin
  begin perform erp.require_internal();raise exception 'EXPECTED_DENIAL_NOT_RAISED';exception when others then if SQLERRM<>'Internal ERP access required'then raise;end if;end;end$$;
 create function public.guard_scope_deny()returns void language plpgsql security definer set search_path='' as $$begin
  begin perform erp.require_internal();raise exception 'MATCHED_FINE_DENIAL_SKIPPED';exception when insufficient_privilege then if SQLERRM<>'CP7_SALES_ACCESS_DENIED'then raise;end if;end;end$$;
 alter function erp.require_internal() owner to postgres;alter function public.guard_allow()owner to postgres;alter function public.guard_deny()owner to postgres;
 alter function public.guard_scope_deny()owner to postgres;
 grant select on public.guard_subject to postgres;grant usage on schema erp,auth,cp7_procurement,cp7_material,cp7_supplier_return,cp7_sales to postgres;
 grant select on all tables in schema erp,cp7_procurement,cp7_material,cp7_supplier_return,cp7_sales to postgres;`)
})
afterEach(async()=>{await db?.close()})
const claims=`select set_config('request.jwt.claims','{"role":"authenticated","sub":"${actor}"}',false);`

test('active legacy internal roles do not enter irrelevant scope-permission lookups',async()=>{
 for(const role of ['OWNER','ADMIN','STAFF'])await db.execute(`begin;${claims}
  update public.guard_subject set role_code='${role}';select set_config('guard_test.forbid_scope_permission_read','true',true);
  set session authorization authenticator;select public.guard_allow();reset session authorization;rollback;`)
})
test('fine-only actor requires its exact private context and live permissions',async()=>{
 await db.execute(`begin;${claims}
  insert into cp7_procurement.execution_context values(pg_backend_pid(),txid_current(),'${actor}','POST','warehouse.procurement.post');
  set session authorization authenticator;select public.guard_allow();reset session authorization;
  update public.guard_subject set permissions=array['warehouse.procurement.view'];
  set session authorization authenticator;select public.guard_deny();reset session authorization;rollback;`)
})
test('inactive subject or role is denied despite a previously matching private context',async()=>{
 for(const field of ['is_active','role_active'])await db.execute(`begin;${claims}
  insert into cp7_procurement.execution_context values(pg_backend_pid(),txid_current(),'${actor}','POST','warehouse.procurement.post');
  set session authorization authenticator;select public.guard_allow();reset session authorization;
  update public.guard_subject set ${field}=false;
  set session authorization authenticator;select public.guard_deny();reset session authorization;rollback;`)
})
test('other actor, transaction, action and caller GUC cannot grant a scope',async()=>{
 for(const row of [`pg_backend_pid(),txid_current(),'${foreign}','POST','warehouse.procurement.post'`,`pg_backend_pid(),txid_current()+1,'${actor}','POST','warehouse.procurement.post'`,`pg_backend_pid(),txid_current(),'${actor}','DELETE','warehouse.procurement.post'`])await db.execute(`begin;${claims}
  insert into cp7_procurement.execution_context values(${row});select set_config('app.role','OWNER',true);
  set session authorization authenticator;select public.guard_deny();reset session authorization;rollback;`)
})
test('matching sales scope still checks revoked fine rights before legacy fallback',async()=>{
 await db.execute(`begin;${claims}
  update public.guard_subject set role_code='ADMIN',permissions=array['sales.invoice.post'];
  insert into cp7_sales.command_context values(pg_backend_pid(),txid_current(),'${actor}','POST');
  set session authorization authenticator;select public.guard_allow();reset session authorization;
  update public.guard_subject set permissions=array[]::text[];
  set session authorization authenticator;select public.guard_scope_deny();reset session authorization;rollback;`)
})
