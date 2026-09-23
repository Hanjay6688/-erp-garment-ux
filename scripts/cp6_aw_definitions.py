"""AW: one per-date close readiness engine (AUD-S06 + AUD-B04), written in exact pg_get_functiondef form.

One engine, read by the close command, its preview and the official report:
- erp.period_blockers_v1(through, window_from) lists every blocker with family, code, severity, scope, the earliest
  impact date, a reference and an owner-readable reason. erp.period_readiness_v1 folds it into READY /
  RECALC_PENDING / BLOCKED.
- close_accounting_through recomputes readiness after its FOR UPDATE on the period control row and refuses unless
  READY, then files an insert-only snapshot (readiness + GL balance per account as of the date).
- get_owner_financial_snapshot_v2 takes data_confidence from the same engine for p_as_of (the old global queue
  count and current-only integrity are replaced); the report-scoped sales bridge check stays.

Owner policy (handoff §14 no. 3 and §16.4): recost pending/failed for the period, stock/journal mismatch, empty
attendance cell on a working day (existing rule: holidays are recorded OFF), payroll due and not approved (labour
recognised at payroll period_end; a payroll ending after the date does not block), paid attendance or eligible work
not taken by any payroll, laundry price unknown until the owner enters an estimate. GRNI may close with an estimate
(INFO only). Open items use every fact dated on or before the date; attendance completeness uses the window after
the current closed_through. Current-state integrity checks cannot be dated and block every date (conservative).

Atomicity: producers that read closed_through take FOR SHARE on the control row and wait for close; producers that
never read it do not depend on close, so a fact they commit during close is ordered after it (a late change).
Unknown laundry price is resolved by erp.set_laundry_rate_owner_estimate_v1, which records the estimate in an
insert-only table and sets the delivery rate through the existing rate trigger (accrual + HPP at the delivery date).
"""
from pathlib import Path
import re
import cp6_av_definitions as av

ROOT=Path(__file__).resolve().parents[1]
AC='supabase/migrations/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql'
CLOSE='erp.close_accounting_through(date,text)'
SNAPSHOT='erp.get_owner_financial_snapshot_v2(date,date,date)'
BLOCKERS='erp.period_blockers_v1(date,date)'
READINESS='erp.period_readiness_v1(date,date)'
PREFLIGHT='erp.accounting_close_preflight_v1(date)'
FILING_GUARD='erp.guard_accounting_close_filing_immutable_v1()'
ESTIMATE='erp.set_laundry_rate_owner_estimate_v1(uuid,numeric,text)'
ESTIMATE_GUARD='erp.guard_laundry_rate_owner_estimate_immutable_v1()'
FACADE_PREFLIGHT='public.erp_accounting_close_preflight_v1(date)'
FACADE_CLOSE='public.erp_close_accounting_through_v1(date,text)'
FACADE_ESTIMATE='public.erp_set_laundry_rate_owner_estimate_v1(uuid,numeric,text)'
FILINGS='accounting_close_filings_v1'
ESTIMATES='laundry_rate_owner_estimates_v1'
PRIVATE_ACL=['postgres=X/postgres']
PUBLIC_ACL=['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']

OLD={CLOSE:av.canonical_from_migration(AC,'close_accounting_through'),
     SNAPSHOT:av.canonical_from_migration(AC,'get_owner_financial_snapshot_v2')}
replace_once=av.replace_once
ENGINE_SQL=(ROOT/'scripts/cp6_aw_engine.sql').read_text()


def _function(text,name):
    start=text.index('CREATE OR REPLACE FUNCTION '+name+'(')
    end=text.index('$function$',text.index('AS $function$',start)+len('AS $function$'))+len('$function$')
    return text[start:end]+'\n'


close=OLD[CLOSE]
close=replace_once(close,"declare v_old date; v_material uuid;","declare v_old date; v_material uuid; v_readiness jsonb;")
close=replace_once(close,"""    raise exception 'Untuk membuka kembali periode gunakan reopen_accounting_through(); periode saat ini sudah ditutup sampai %',v_old;
  end if;
""","""    raise exception 'Untuk membuka kembali periode gunakan reopen_accounting_through(); periode saat ini sudah ditutup sampai %',v_old;
  end if;
  -- One engine, evaluated after the control row lock so posting paths that read closed_through wait for this close.
  v_readiness:=erp.period_readiness_v1(p_closed_through,v_old+1);
  if v_readiness->>'status'<>'READY' then
    raise exception using message=format('CLOSE_BLOCKED: tutup buku sampai %s ditolak, %s penghalang (%s).',p_closed_through,
      v_readiness->>'blocker_count',(select string_agg(distinct b->>'code',', ') from jsonb_array_elements(v_readiness->'blockers') b)),
      detail=v_readiness::text,hint='Lihat erp_accounting_close_preflight_v1 untuk daftar lengkap.';
  end if;
""")
close=replace_once(close,"""  values('accounting_period_control',null,'UPDATE',jsonb_build_object('closed_through',v_old),jsonb_build_object('closed_through',p_closed_through,'material_cost_checkpoints_refreshed',true),erp.current_app_user_id(),p_reason);
end;""","""  values('accounting_period_control',null,'UPDATE',jsonb_build_object('closed_through',v_old),jsonb_build_object('closed_through',p_closed_through,'material_cost_checkpoints_refreshed',true),erp.current_app_user_id(),p_reason);

  -- Filed snapshot: never overwritten; later corrections are read from the engine as current-corrected values.
  insert into erp.accounting_close_filings_v1(closed_through,previous_closed_through,filed_by,reason,readiness,gl_balances)
  values(p_closed_through,v_old,erp.current_app_user_id(),p_reason,v_readiness,
    (select coalesce(jsonb_object_agg(ca.account_code,round(b.balance,2) order by ca.account_code),'{}'::jsonb)
     from (select a.account_id,sum(a.debit_total-a.credit_total) balance from erp.account_daily_balances a
           where a.balance_date<=p_closed_through group by a.account_id) b
     join erp.chart_accounts ca on ca.id=b.account_id));
end;""")

snapshot=OLD[SNAPSHOT]
snapshot=replace_once(snapshot,"  v_critical bigint:=0;v_warning bigint:=0;v_pending bigint:=0;",
  "  v_critical bigint:=0;v_warning bigint:=0;v_pending bigint:=0;\n  v_closed date;v_readiness jsonb;v_warnings jsonb:='[]'::jsonb;")
snapshot=replace_once(snapshot,"""  select coalesce(sum(issue_count) filter(where severity='CRITICAL'),0)::bigint,
         coalesce(sum(issue_count) filter(where severity='WARNING'),0)::bigint
  into v_critical,v_warning from erp.run_v268_financial_report_checks();
  select coalesce(jsonb_agg(jsonb_build_object(
    'check_name',c.check_name,'severity',c.severity,'issue_count',c.issue_count,
    'details',c.details) order by c.severity,c.check_name),'[]'::jsonb)
  into v_failed_checks from erp.run_v268_financial_report_checks() c
  where c.issue_count>0;
""","""  -- Confidence for the requested date comes from the close engine (AUD-S06/B04): open items dated on or before
  -- p_as_of, attendance completeness after closed_through, current-state integrity for every date.
  select closed_through into v_closed from erp.accounting_period_control where singleton_id=1;
  v_readiness:=erp.period_readiness_v1(p_as_of,case when v_closed is null then null when p_as_of>v_closed then v_closed+1 else p_as_of+1 end);
  v_critical:=(v_readiness->>'critical_count')::bigint+(v_readiness->>'policy_count')::bigint;
  v_pending:=(v_readiness->>'recalc_count')::bigint;
  select coalesce(jsonb_agg(jsonb_build_object(
    'check_name',b->>'code','severity',case when b->>'severity'='RECALC' then 'WARNING' else 'CRITICAL' end,
    'issue_count',1,'details',b->>'reason','family',b->>'family','scope',b->>'scope',
    'impact_date',b->>'impact_date','reference',b->'reference') order by b->>'family',b->>'code'),'[]'::jsonb)
  into v_failed_checks from jsonb_array_elements(v_readiness->'blockers') b;
  select coalesce(sum(c.issue_count),0)::bigint,
         coalesce(jsonb_agg(jsonb_build_object('check_name',c.check_name,'severity',c.severity,'issue_count',c.issue_count,
           'details',c.details) order by c.check_name),'[]'::jsonb)
  into v_warning,v_warnings from erp.run_v268_financial_report_checks() c
  where c.issue_count>0 and c.severity='WARNING' and c.check_name<>'V268_COST_RECALC_PENDING';
  v_failed_checks:=v_failed_checks||v_warnings;
""")
snapshot=replace_once(snapshot,"""  select count(*)::bigint into v_pending from erp.cost_recalc_queue
  where status in('PENDING','RUNNING') or(status='FAILED' and attempt_count<3);
""","")
snapshot=replace_once(snapshot,"""      'pending_cost_recalc_count',v_pending,'failed_checks',v_failed_checks
    ),""","""      'pending_cost_recalc_count',v_pending,'failed_checks',v_failed_checks,
      'engine',v_readiness->>'engine','as_of',p_as_of,'window_from',v_readiness->'window_from',
      'closed_through',v_closed,'blockers',v_readiness->'blockers','info',v_readiness->'info'
    ),""")

FUNCTIONS={CLOSE:close,SNAPSHOT:snapshot}

NEW_FUNCTIONS={
BLOCKERS:_function(ENGINE_SQL,'erp.period_blockers_v1'),
READINESS:_function(ENGINE_SQL,'erp.period_readiness_v1'),
PREFLIGHT:"""CREATE OR REPLACE FUNCTION erp.accounting_close_preflight_v1(p_through date)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v_closed date;
begin
  perform erp.require_owner_admin();
  if p_through is null then raise exception 'Tanggal tutup buku wajib diisi'; end if;
  select closed_through into v_closed from erp.accounting_period_control where singleton_id=1;
  -- Same engine and window as close_accounting_through; close repeats it after its lock.
  return erp.period_readiness_v1(p_through,v_closed+1)||jsonb_build_object(
    'closed_through',v_closed,
    'date_allowed',p_through<erp._cp3_business_date(statement_timestamp()) and (v_closed is null or p_through>=v_closed));
end
$function$
""",
FILING_GUARD:"""CREATE OR REPLACE FUNCTION erp.guard_accounting_close_filing_immutable_v1()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
begin
  raise exception 'CLOSE_FILING_IMMUTABLE: snapshot tutup buku tidak boleh diubah atau dihapus';
end
$function$
""",
ESTIMATE_GUARD:"""CREATE OR REPLACE FUNCTION erp.guard_laundry_rate_owner_estimate_immutable_v1()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
begin
  raise exception 'LAUNDRY_ESTIMATE_IMMUTABLE: estimasi harga laundry owner tidak boleh diubah atau dihapus';
end
$function$
""",
ESTIMATE:"""CREATE OR REPLACE FUNCTION erp.set_laundry_rate_owner_estimate_v1(p_delivery_line_id uuid, p_rate numeric, p_reason text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  v_line erp.laundry_delivery_lines%rowtype;
  v_delivery erp.laundry_deliveries%rowtype;
  v_date date;
begin
  perform erp.require_owner_admin();
  if nullif(btrim(p_reason),'') is null then raise exception 'LAUNDRY_ESTIMATE_REASON_REQUIRED'; end if;
  if p_rate is null or p_rate<0 or p_rate<>round(p_rate,2) then raise exception 'LAUNDRY_ESTIMATE_RATE_INVALID'; end if;
  select * into v_line from erp.laundry_delivery_lines where id=p_delivery_line_id for update;
  if v_line.id is null then raise exception 'LAUNDRY_ESTIMATE_LINE_NOT_FOUND'; end if;
  select * into v_delivery from erp.laundry_deliveries where id=v_line.delivery_id for update;
  if v_delivery.status in('DRAFT','REVERSED') then raise exception 'LAUNDRY_ESTIMATE_DELIVERY_NOT_POSTED'; end if;
  -- Only an unknown price is estimated here; a known rate is never overwritten.
  if v_line.estimated_rate_snapshot is not null then raise exception 'LAUNDRY_ESTIMATE_RATE_ALREADY_KNOWN'; end if;
  perform set_config('app.change_reason',p_reason,true);
  insert into erp.laundry_rate_owner_estimates_v1(delivery_line_id,rate_per_pcs,reason,estimated_by)
  values(v_line.id,p_rate,btrim(p_reason),erp.current_app_user_id());
  -- The existing rate trigger posts the accrual and rebuilds PO HPP at the delivery date (shifted by post_journal
  -- into the open period when that date is closed).
  update erp.laundry_delivery_lines set estimated_rate_snapshot=p_rate,estimated_cost_status='ESTIMATED' where id=v_line.id;
  v_date:=erp._cp3_business_date(v_delivery.physical_at);
  -- The trigger does not settle a FINISHED PO's residual WIP; the other cost paths do.
  if (select po.status from erp.production_orders po where po.id=v_delivery.po_id)='FINISHED' then
    perform erp.sync_finished_po_wip_residual(v_delivery.po_id,v_date,'Owner laundry rate estimate: '||btrim(p_reason));
  end if;
  return jsonb_build_object('delivery_line_id',v_line.id,'delivery_id',v_delivery.id,'po_id',v_delivery.po_id,
    'rate_per_pcs',p_rate,'economic_date',v_date);
end
$function$
""",
}

PUBLIC_FUNCTIONS={
FACADE_PREFLIGHT:"""CREATE OR REPLACE FUNCTION public.erp_accounting_close_preflight_v1(p_through date)
 RETURNS jsonb
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
 select erp.accounting_close_preflight_v1(p_through);
$function$
""",
FACADE_CLOSE:"""CREATE OR REPLACE FUNCTION public.erp_close_accounting_through_v1(p_closed_through date, p_reason text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v_filing jsonb;
begin
  perform erp.close_accounting_through(p_closed_through,p_reason);
  select jsonb_build_object('filing_id',f.id,'closed_through',f.closed_through,'previous_closed_through',f.previous_closed_through,
    'filed_at',f.filed_at,'readiness',f.readiness)
  into v_filing from erp.accounting_close_filings_v1 f
  where f.closed_through=p_closed_through order by f.filed_at desc,f.id desc limit 1;
  return v_filing;
end
$function$
""",
FACADE_ESTIMATE:"""CREATE OR REPLACE FUNCTION public.erp_set_laundry_rate_owner_estimate_v1(p_delivery_line_id uuid, p_rate numeric, p_reason text)
 RETURNS jsonb
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
 select erp.set_laundry_rate_owner_estimate_v1(p_delivery_line_id,p_rate,p_reason);
$function$
""",
}

SCHEMA=f"""create table erp.{FILINGS} (
  id uuid primary key default gen_random_uuid(),
  closed_through date not null,
  previous_closed_through date,
  filed_at timestamptz not null default statement_timestamp(),
  filed_by uuid,
  reason text not null check (length(btrim(reason))>0),
  readiness jsonb not null check (readiness->>'status'='READY'),
  gl_balances jsonb not null
);
alter table erp.{FILINGS} enable row level security;
revoke all on erp.{FILINGS} from public,anon,authenticated,service_role;
create table erp.{ESTIMATES} (
  delivery_line_id uuid primary key references erp.laundry_delivery_lines(id),
  rate_per_pcs numeric(18,2) not null check (rate_per_pcs>=0),
  reason text not null check (length(btrim(reason))>0),
  estimated_by uuid,
  estimated_at timestamptz not null default statement_timestamp()
);
alter table erp.{ESTIMATES} enable row level security;
revoke all on erp.{ESTIMATES} from public,anon,authenticated,service_role;
"""

TRIGGERS=f"""create trigger trg_guard_accounting_close_filing_immutable before update or delete on erp.{FILINGS}
  for each row execute function erp.guard_accounting_close_filing_immutable_v1();
create trigger trg_guard_accounting_close_filing_truncate before truncate on erp.{FILINGS}
  for each statement execute function erp.guard_accounting_close_filing_immutable_v1();
create trigger trg_guard_laundry_rate_owner_estimate_immutable before update or delete on erp.{ESTIMATES}
  for each row execute function erp.guard_laundry_rate_owner_estimate_immutable_v1();
create trigger trg_guard_laundry_rate_owner_estimate_truncate before truncate on erp.{ESTIMATES}
  for each statement execute function erp.guard_laundry_rate_owner_estimate_immutable_v1();
"""

assert set(FUNCTIONS)==set(OLD) and all(FUNCTIONS[k]!=OLD[k] for k in OLD)
assert all(re.match(r'CREATE OR REPLACE FUNCTION ',t) for t in list(NEW_FUNCTIONS.values())+list(PUBLIC_FUNCTIONS.values()))
