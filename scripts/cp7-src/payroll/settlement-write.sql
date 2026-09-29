-- P12 controlled preparation and native full settlement. This capability owns
-- only request/context metadata; no ERP business table DML is granted to it.
create role cp7_payroll_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
grant usage on schema cp7_payroll,auth,erp to cp7_payroll_write;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text) to cp7_payroll_write;
create table cp7_payroll.settlement_requests(actor uuid not null,request_id uuid not null,action text not null,payload jsonb not null,expected_version text not null,response jsonb,primary key(actor,request_id));
create table cp7_payroll.settlement_context(backend_pid integer not null,transaction_id bigint not null,actor uuid not null,payroll_id uuid not null,action text not null check(action in('PREPARE','APPROVE','PAY','CANCEL','REVERSE')),primary key(backend_pid,transaction_id));
alter table cp7_payroll.settlement_requests owner to cp7_payroll_write;
alter table cp7_payroll.settlement_context owner to cp7_payroll_write;
alter table cp7_payroll.settlement_requests enable row level security;
alter table cp7_payroll.settlement_context enable row level security;
revoke all on cp7_payroll.settlement_requests,cp7_payroll.settlement_context from public,anon,authenticated,service_role,cp7_capture,cp7_payroll_read,cp7_nota_write,cp7_payroll_header;

create function cp7_payroll.settlement_access(p_action text) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare a jsonb;
begin
 a:=cp7_payroll.access_now('PAYROLL');
 if p_action not in('PREPARE','APPROVE','PAY','CANCEL','REVERSE') or p_action is null
  or(p_action in('PREPARE','APPROVE','CANCEL','REVERSE') and not erp.has_permission('finance.payroll.approve'))
  or(p_action in('PAY','REVERSE') and not erp.has_permission('finance.payroll.pay')) then
  raise exception using errcode='42501',message='CP7_PAYROLL_WRITE_DENIED';end if;
 return a;
end $$;

create function cp7_payroll.require_settlement_context(p_id uuid) returns void
language plpgsql stable security definer set search_path='' as $$
declare c cp7_payroll.settlement_context;
begin
 select * into c from cp7_payroll.settlement_context where backend_pid=pg_backend_pid() and transaction_id=txid_current() and actor=auth.uid() and payroll_id=p_id;
 if c.actor is null then raise exception using errcode='42501',message='CP7_PAYROLL_PRIVATE_CONTEXT_REQUIRED';end if;
 perform cp7_payroll.settlement_access(c.action);
end $$;

-- Compare actual economic content, excluding generated child IDs. PREPARE keeps
-- selected work untouched; rebuilding source snapshots may generate new row IDs.
create function cp7_payroll.settlement_meaning(p_id uuid) returns jsonb
language sql stable security definer set search_path='' as $$
 select jsonb_build_object('contractor_id',p.contractor_id,'period_start',p.period_start,'period_end',p.period_end,
  'attendance_required',c.attendance_required,'labor_total',p.labor_total,'attendance_total',p.attendance_total,
  'reimburse_total',p.reimburse_total,'deduction_total',p.deduction_total,'manual_adjustment',p.manual_adjustment,'net_payable',p.net_payable,
  'work',(select coalesce(jsonb_agg(to_jsonb(i) order by i.id),'[]') from erp.payroll_work_items i where i.payroll_id=p.id),
  'attendance',(select coalesce(jsonb_agg(to_jsonb(i)-'id' order by i.attendance_record_id,i.worker_id),'[]') from erp.payroll_attendance_items i where i.payroll_id=p.id),
  'reimbursements',(select coalesce(jsonb_agg(to_jsonb(i)-'id' order by (to_jsonb(i)-'id')::text),'[]') from erp.payroll_reimbursements i where i.payroll_id=p.id),
  'deductions',(select coalesce(jsonb_agg(to_jsonb(i)-'id' order by (to_jsonb(i)-'id')::text),'[]') from erp.payroll_deductions i where i.payroll_id=p.id))
 from erp.payroll_settlements p join erp.contractors c on c.id=p.contractor_id where p.id=p_id
$$;

-- The only trusted business adapter. All source accounting still runs through
-- accepted native functions; payment edits are limited to date and cash account.
create function cp7_payroll.apply_settlement(p_action text,p_payload jsonb,p_expected text) returns jsonb
language plpgsql volatile security definer set search_path='' as $$
declare p erp.payroll_settlements;a jsonb;before_meaning jsonb;after_meaning jsonb;prior_work jsonb;reason text:=btrim(p_payload->>'change_reason');
begin
 a:=cp7_payroll.settlement_access(p_action);
 select * into p from erp.payroll_settlements where id=(p_payload->>'id')::uuid for update;
 if p.id is null then raise exception 'CP7_PAYROLL_MISSING';end if;
 perform cp7_payroll.require_settlement_context(p.id);
 perform pg_advisory_xact_lock(hashtextextended(p.contractor_id::text,0));
 -- Native child writers use the payroll lock. These locks also fence edits to
 -- already selected rows while the review token is checked.
 perform 1 from erp.payroll_work_items where payroll_id=p.id order by id for update;
 perform 1 from erp.payroll_attendance_items where payroll_id=p.id order by id for update;
 perform 1 from erp.payroll_reimbursements where payroll_id=p.id order by id for update;
 perform 1 from erp.payroll_deductions where payroll_id=p.id order by id for update;
 if cp7_payroll.settlement_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_PAYROLL_ACCESS_CHANGED';end if;
 if p.row_version::text is distinct from p_expected or cp7_payroll.settlement_token(p.id) is distinct from p_payload->>'review_token' then raise exception 'CP7_PAYROLL_REVIEW_CHANGED';end if;
 perform set_config('app.change_reason',reason,true);
 if p_action in('PREPARE','APPROVE') then
  if p.status not in('DRAFT','CALCULATED','REVIEW') then raise exception 'CP7_PAYROLL_DRAFT_ONLY';end if;
  -- Freeze existing source rows in native lock order. A new source visible
  -- before this rebuild is included and forces another review at APPROVE.
  perform 1 from erp.contractors where id=p.contractor_id for share;
  perform 1 from erp.attendance_periods where contractor_id=p.contractor_id and period_start<=p.period_end and period_end>=p.period_start order by id for share;
  perform 1 from erp.contractor_workers where contractor_id=p.contractor_id order by id for share;
  perform 1 from erp.attendance_records where contractor_id=p.contractor_id and attendance_date between p.period_start and p.period_end order by id for share;
  perform 1 from erp.contractor_accessory_reimbursement_entitlements where contractor_id=p.contractor_id order by id for update;
  perform 1 from erp.contractor_material_issues where contractor_id=p.contractor_id order by id for share;
  perform 1 from erp.contractor_material_issue_items i where exists(select 1 from erp.contractor_material_issues h where h.id=i.issue_id and h.contractor_id=p.contractor_id) order by i.id for update;
  before_meaning:=cp7_payroll.settlement_meaning(p.id);prior_work:=before_meaning->'work';
  -- Derived from the accepted populate function, with only automatic work
  -- removal/insertion removed. All non-work eligibility/formulas are identical.
  perform cp7_payroll.rebuild_nonwork(p.id);
  after_meaning:=cp7_payroll.settlement_meaning(p.id);
  if after_meaning->'work' is distinct from prior_work then raise exception 'CP7_PAYROLL_SELECTED_WORK_CHANGED';end if;
  if p_action='APPROVE' then
   if before_meaning is distinct from after_meaning then raise exception 'CP7_PAYROLL_PREPARE_REQUIRED: sumber atau jumlah berubah; hitung dan periksa ulang';end if;
   perform erp.approve_payroll(p.id);
  end if;
 elsif p_action='PAY' then
  if p.status<>'APPROVED' then raise exception 'CP7_PAYROLL_APPROVED_ONLY';end if;
  update erp.payroll_settlements set payment_date=(p_payload->>'payment_date')::date,payment_cash_account_id=(p_payload->>'cash_account_id')::uuid where id=p.id;
  perform erp.post_payroll_payment(p.id);
 elsif p_action='CANCEL' then
  if p.status not in('DRAFT','CALCULATED','REVIEW','APPROVED') then raise exception 'CP7_PAYROLL_UNPAID_ONLY';end if;
  perform erp.cancel_unpaid_payroll(p.id,reason);
 elsif p_action='REVERSE' then
  if p.status<>'PAID' then raise exception 'CP7_PAYROLL_PAID_ONLY';end if;
  perform erp.reverse_paid_payroll(p.id,reason);
 else raise exception 'CP7_PAYROLL_ACTION';end if;
 if cp7_payroll.settlement_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_PAYROLL_ACCESS_CHANGED';end if;
 return cp7_payroll.settlement_document(p.id);
end $$;

create function cp7_payroll.settlement_command(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;old cp7_payroll.settlement_requests;d jsonb;r jsonb;keys text[];
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_payroll.settlement_access(p_action);
 keys:=array['id','review_token','change_reason']||case when p_action='PAY' then array['payment_date','cash_account_id'] else '{}'::text[] end;
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'
  or jsonb_typeof(p_payload) is distinct from 'object' or not p_payload ?& keys
  or exists(select 1 from jsonb_each(p_payload) e where e.key<>all(keys) or (jsonb_typeof(e.value)<>'string' and not(e.key='cash_account_id' and e.value='null'::jsonb)))
  or coalesce(p_payload->>'id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or coalesce(p_payload->>'review_token','')!~'^[a-f0-9]{32}$'
  or length(btrim(p_payload->>'change_reason')) not between 5 and 1000
  or (p_action='PAY' and coalesce(p_payload->>'payment_date','')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$') then raise exception 'CP7_PAYROLL_FIELDS';end if;
 insert into cp7_payroll.settlement_requests values(auth.uid(),p_request,p_action,p_payload,p_expected,null) on conflict do nothing;
 select * into old from cp7_payroll.settlement_requests where actor=auth.uid() and request_id=p_request for update;
 if old.action<>p_action or old.payload is distinct from p_payload or old.expected_version is distinct from p_expected then raise exception 'CP7_PAYROLL_REQUEST_CHANGED';end if;
 if cp7_payroll.settlement_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_PAYROLL_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 insert into cp7_payroll.settlement_context values(pg_backend_pid(),txid_current(),auth.uid(),(p_payload->>'id')::uuid,p_action);
 d:=cp7_payroll.apply_settlement(p_action,p_payload,p_expected);
 delete from cp7_payroll.settlement_context where backend_pid=pg_backend_pid() and transaction_id=txid_current();
 if cp7_payroll.settlement_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_PAYROLL_ACCESS_CHANGED';end if;
 r:=jsonb_build_object('contract_version','cp7.payroll-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request,'payroll_id',d->'id','status',d->'status','row_version',d->'row_version','review_token',d->'review_token');
 update cp7_payroll.settlement_requests set response=r where actor=auth.uid() and request_id=p_request;
 return r;
end $$;
create function public.erp_cp7_save_payroll_v1(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_payroll.settlement_command(p_action,p_payload,p_request,p_expected)$$;

alter function cp7_payroll.settlement_access(text) owner to cp7_payroll_read;
alter function cp7_payroll.settlement_command(text,jsonb,uuid,text) owner to cp7_payroll_write;
grant create on schema public to cp7_payroll_write;
alter function public.erp_cp7_save_payroll_v1(text,jsonb,uuid,text) owner to cp7_payroll_write;
revoke create on schema public from cp7_payroll_write;
-- Trusted helpers are explicitly postgres-owned and never publicly executable.
alter function cp7_payroll.require_settlement_context(uuid) owner to postgres;
alter function cp7_payroll.settlement_meaning(uuid) owner to postgres;
alter function cp7_payroll.apply_settlement(text,jsonb,text) owner to postgres;
revoke all on function cp7_payroll.settlement_access(text),cp7_payroll.require_settlement_context(uuid),cp7_payroll.settlement_meaning(uuid),cp7_payroll.apply_settlement(text,jsonb,text),cp7_payroll.settlement_command(text,jsonb,uuid,text) from public,anon,authenticated,service_role,cp7_capture,cp7_nota_write,cp7_payroll_header;
grant execute on function cp7_payroll.settlement_access(text),cp7_payroll.apply_settlement(text,jsonb,text) to cp7_payroll_write;
-- Supabase's postgres role is not necessarily a superuser. Give the native
-- adapter only its private read/execute dependencies, never a client capability.
grant usage on schema cp7_payroll to postgres;
grant select on cp7_payroll.settlement_context,cp7_payroll.notes to postgres;
grant execute on function cp7_payroll.settlement_access(text),cp7_payroll.settlement_token(uuid),cp7_payroll.settlement_document(uuid) to postgres;
revoke all on function public.erp_cp7_save_payroll_v1(text,jsonb,uuid,text) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_save_payroll_v1(text,jsonb,uuid,text) to authenticated;
