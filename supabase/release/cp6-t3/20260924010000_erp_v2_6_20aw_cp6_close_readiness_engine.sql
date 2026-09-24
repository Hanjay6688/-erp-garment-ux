-- CP6 AW: close readiness engine (one engine for preflight, close and the owner report). Release candidate of the T3 combined package; closed, drained maintenance required.
begin;
-- Built by scripts/cp6_t3_awx_release.py from supabase/dev/cp6_aw_t1_family.sql (sha256 db8ee8115b5a53dd9a7b154c96b764b8bee9e4a79c5adfa48050417bb756bd32): the T1 body below is unchanged apart from the
-- ledger description; guards follow AO..AV. Catalog pins are placeholders until the T3 capture (refuse as is).
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';set local search_path='';
set local role postgres;
do $closed_admission$
begin
 if session_user not in('postgres','supabase_admin')
  or (select datallowconn from pg_database where datname=current_database())
  or exists(select 1 from pg_stat_activity where datname=current_database() and pid<>pg_backend_pid()) then
  raise exception 'PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE';
 end if;
end $closed_admission$;
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;
do $lock_business$
declare n text;
begin
 for n in select c.relname from pg_class c join pg_namespace s on s.oid=c.relnamespace where s.nspname='erp' and c.relkind in('r','p') order by 1 loop
  execute format('lock table erp.%I in share row exclusive mode',n);
 end loop;
end $lock_business$;
do $predecessor$
begin
 if not exists(select 1 from erp.schema_migrations where version='v2.6.20av')
  or exists(select 1 from erp.schema_migrations where version='v2.6.20aw')
  or (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20av_cp6_identity_new_stock_cutoff')<>1
  or not exists(select 1 from supabase_migrations.schema_migrations where version='20260923110000' and name='erp_v2_6_20av_cp6_identity_new_stock_cutoff'
   and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')='c63a1fe3bf76dfc396921e07f57eb043e3bb864425b3289a9546bf66e08169a5')
  or exists(select 1 from supabase_migrations.schema_migrations where version>'20260923110000') then raise exception 'AW_EXACT_PREDECESSOR_REQUIRED';end if;
end $predecessor$;
do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule')
), objects as (
 select 'FUNCTION:'||format('%I.%I(%s)',n.nspname,p.proname,replace(oidvectortypes(p.proargtypes),', ',',')) k,
 jsonb_build_array(pg_get_functiondef(p.oid),pg_get_userbyid(p.proowner),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl)a order by a::text) end) v
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p')
 union all
 select 'RELATION:'||format('%I.%I',nspname,relname),jsonb_build_array(relkind,pg_get_userbyid(relowner),
  case when relacl is null then null else array(select a::text from unnest(relacl)a order by a::text) end,
  relrowsecurity,relforcerowsecurity,relreplident,relpersistence,relispartition,reloptions)
 from relations
 union all
 select 'COLUMN:'||format('%I.%I.%I',r.nspname,r.relname,a.attname),
 jsonb_build_array((select count(*) from pg_attribute visible where visible.attrelid=a.attrelid and visible.attnum>0 and not visible.attisdropped and visible.attnum<=a.attnum),format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,
  pg_get_expr(d.adbin,d.adrelid),a.attcollation::regcollation::text,
  case when a.attacl is null then null else array(select x::text from unnest(a.attacl)x order by x::text) end)
 from relations r join pg_attribute a on a.attrelid=r.oid and a.attnum>0 and not a.attisdropped
 left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum
 union all
 select 'CONSTRAINT:'||format('%I.%I.%I',r.nspname,r.relname,c.conname),
 jsonb_build_array(c.contype,pg_get_constraintdef(c.oid),c.condeferrable,c.condeferred,c.convalidated,c.conislocal,c.connoinherit)
 from relations r join pg_constraint c on c.conrelid=r.oid
 union all
 select 'INDEX:'||format('%I.%I',r.nspname,c.relname),
 jsonb_build_array(pg_get_indexdef(i.indexrelid),i.indisunique,i.indisprimary,i.indisexclusion,i.indisvalid,i.indisready,i.indisclustered,i.indisreplident,c.reloptions)
 from relations r join pg_index i on i.indrelid=r.oid join pg_class c on c.oid=i.indexrelid
 union all
 select 'TRIGGER:'||format('%I.%I.%I',r.nspname,r.relname,t.tgname),jsonb_build_array(pg_get_triggerdef(t.oid),t.tgenabled)
 from relations r join pg_trigger t on t.tgrelid=r.oid and not t.tgisinternal
 union all
 select 'POLICY:'||format('%I.%I.%I',r.nspname,r.relname,p.polname),jsonb_build_array(p.polcmd,p.polpermissive,
  array(select case when x=0 then 'PUBLIC' else pg_get_userbyid(x) end from unnest(p.polroles)x order by 1),
  pg_get_expr(p.polqual,p.polrelid),pg_get_expr(p.polwithcheck,p.polrelid))
 from relations r join pg_policy p on p.polrelid=r.oid
 union all
 select 'VIEW:'||format('%I.%I',nspname,relname),to_jsonb(pg_get_viewdef(oid,false)) from relations where relkind in('v','m')
 union all
 select 'SEQUENCE:'||format('%I.%I',r.nspname,r.relname),jsonb_build_array(format_type(s.seqtypid,null),s.seqstart,s.seqincrement,s.seqmax,s.seqmin,s.seqcache,s.seqcycle)
 from relations r join pg_sequence s on s.seqrelid=r.oid
 union all
 select 'SCHEMA:'||nspname,jsonb_build_array(pg_get_userbyid(nspowner),
  case when nspacl is null then null else array(select a::text from unnest(nspacl)a order by a::text) end)
 from pg_namespace where nspname in('erp','public')
 union all
 select 'DEFAULT_ACL:'||pg_get_userbyid(d.defaclrole)||':'||coalesce(n.nspname,'GLOBAL')||':'||d.defaclobjtype::text,
 to_jsonb(array(select a::text from unnest(d.defaclacl)a order by a::text))
 from pg_default_acl d left join pg_namespace n on n.oid=d.defaclnamespace
 where n.nspname in('erp','public') or d.defaclnamespace=0
 union all
 select 'ENUM:'||format('%I.%I',n.nspname,t.typname),jsonb_build_array(pg_get_userbyid(t.typowner),
  (select jsonb_agg(e.enumlabel order by e.enumsortorder) from pg_enum e where e.enumtypid=t.oid))
 from pg_type t join pg_namespace n on n.oid=t.typnamespace where n.nspname in('erp','public') and t.typtype='e'
)
select coalesce(jsonb_object_agg(k,encode(extensions.digest(convert_to(v::text,'UTF8'),'sha256'),'hex')),'{}'::jsonb) from objects
) catalog;
 select count(*),encode(extensions.digest(convert_to(coalesce(string_agg(length(key)::text||':'||key||':'||value,E'\n' order by key collate "C"),''),'UTF8'),'sha256'),'hex') into object_count,fingerprint from jsonb_each_text(actual);
 if object_count<>7159 or fingerprint is distinct from 'f345b9f9cdefd97250814cb29c459cde447c1a26846354c516f058abb23a9fdf' then
  raise exception 'AW_PREDECESSOR_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
set local lock_timeout='10s';set local statement_timeout='240s';set local search_path='';
do $t1_guard$
begin
 if not exists(select 1 from erp.schema_migrations where version='v2.6.20av') then raise exception 'AW_T1_REQUIRES_AV'; end if;
 if exists(select 1 from erp.schema_migrations where version='v2.6.20aw') or to_regclass('erp.accounting_close_filings_v1') is not null
    or to_regclass('erp.laundry_rate_owner_estimates_v1') is not null then raise exception 'AW_T1_ALREADY_INSTALLED'; end if;
 if md5(pg_get_functiondef('erp.close_accounting_through(date,text)'::regprocedure))<>'4096a058070e77cac0f4b96fc6497ef7' then raise exception 'AW_T1_PREDECESSOR_DRIFT: erp.close_accounting_through(date,text)'; end if;
 if md5(pg_get_functiondef('erp.get_owner_financial_snapshot_v2(date,date,date)'::regprocedure))<>'fb82961d59f37d61e50ba70c588bd252' then raise exception 'AW_T1_PREDECESSOR_DRIFT: erp.get_owner_financial_snapshot_v2(date,date,date)'; end if;
end $t1_guard$;
create table erp.accounting_close_filings_v1 (
  id uuid primary key default gen_random_uuid(),
  closed_through date not null,
  previous_closed_through date,
  filed_at timestamptz not null default statement_timestamp(),
  filed_by uuid,
  reason text not null check (length(btrim(reason))>0),
  readiness jsonb not null check (readiness->>'status'='READY'),
  gl_balances jsonb not null
);
alter table erp.accounting_close_filings_v1 enable row level security;
revoke all on erp.accounting_close_filings_v1 from public,anon,authenticated,service_role;
create table erp.laundry_rate_owner_estimates_v1 (
  delivery_line_id uuid primary key references erp.laundry_delivery_lines(id),
  rate_per_pcs numeric(18,2) not null check (rate_per_pcs>=0 and rate_per_pcs<>'NaN'::numeric),
  reason text not null check (length(btrim(reason))>0),
  estimated_by uuid,
  estimated_at timestamptz not null default statement_timestamp()
);
alter table erp.laundry_rate_owner_estimates_v1 enable row level security;
revoke all on erp.laundry_rate_owner_estimates_v1 from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.guard_accounting_close_filing_immutable_v1()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
begin
  raise exception 'CLOSE_FILING_IMMUTABLE: snapshot tutup buku tidak boleh diubah atau dihapus';
end
$function$;
CREATE OR REPLACE FUNCTION erp.guard_laundry_rate_owner_estimate_immutable_v1()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
begin
  raise exception 'LAUNDRY_ESTIMATE_IMMUTABLE: estimasi harga laundry owner tidak boleh diubah atau dihapus';
end
$function$;
CREATE OR REPLACE FUNCTION erp.period_integrity_check_registry_v1()
 RETURNS TABLE(check_name text, check_class text, dated_by text)
 LANGUAGE sql
 IMMUTABLE
 SET search_path TO ''
AS $function$
-- P-03: class of every CRITICAL/ERROR check the three runners can emit (108 names, STATIC classification in
-- docs/evidence/cp6-aw/p03_integrity_check_classification.md). DATED_EQUIVALENT: the engine reports the check as INFO
-- only when every key failing it right now is also found by the named dated detector (confirmed per key at run time);
-- otherwise it blocks every date. DATABLE: the defect has a business date, but the engine does not scope it yet, so it
-- blocks every date until the owner decides (handoff §20). SYSTEMIC and UNCERTAIN: configuration, privileges or
-- current-state totals without a date; block every date. QUEUE_FAMILY: handled per date by the RECOST family. A name
-- missing here is UNCLASSIFIED and blocks every date (fail closed).
select x.check_name,x.check_class,x.dated_by from (values
  ('AP_CASH_ADVANCE_CAPACITY','DATABLE',null),
  ('AP_CASH_ADVANCE_PAYROLL_JOURNAL','DATABLE',null),
  ('AP_CASH_ADVANCE_SOURCE','DATABLE',null),
  ('AP_OPENING_RECEIPT_JOURNAL_DRIFT','DATABLE',null),
  ('AP_OPENING_RECEIPT_SOURCE_DRIFT','DATABLE',null),
  ('AP_PERIOD_POCKET_HPP','DATABLE',null),
  ('AP_PERIOD_POCKET_LEDGER','DATABLE',null),
  ('AP_PERIOD_POCKET_OVERLAP','DATABLE',null),
  ('AP_PERIOD_POCKET_SOURCES','DATABLE',null),
  ('AP_POCKET_EXPENSE_LEDGER','DATABLE',null),
  ('AP_POCKET_NO_CUTTING','DATABLE',null),
  ('AP_POCKET_SOURCE','DATABLE',null),
  ('AP_PREPAYMENT_CAPACITY','DATABLE',null),
  ('AP_PREPAYMENT_EVENT_JOURNAL','DATABLE',null),
  ('AP_PREPAYMENT_GL_SUBLEDGER','UNCERTAIN',null),
  ('AP_PREPAYMENT_OPENING_JOURNAL','DATABLE',null),
  ('AP_PREPAYMENT_PAYMENT_JOURNAL','DATABLE',null),
  ('AP_PREPAYMENT_PAYMENT_SOURCE','DATABLE',null),
  ('BS_RESOLUTION_OVER_QTY','DATABLE',null),
  ('DUPLICATE_CURRENT_HPP','DATABLE',null),
  ('FG_CACHE_MISMATCH','SYSTEMIC',null),
  ('KASBON_PAID_OVERSETTLED','DATABLE',null),
  ('KASBON_STATUS_MISMATCH','DATABLE',null),
  ('LAUNDRY_OVER_RETURN','DATABLE',null),
  ('NEGATIVE_FG_BALANCE','DATED_EQUIVALENT','FG_QTY_NEGATIVE_ASOF'),
  ('NEGATIVE_MATERIAL_LOCATION_BALANCE','DATED_EQUIVALENT','MATERIAL_QTY_NEGATIVE_ASOF'),
  ('PAYROLL_ATTENDANCE_DUPLICATE','DATABLE',null),
  ('PAYROLL_PAID_NEGATIVE_NET','DATABLE',null),
  ('QC_SOURCE_OVER_ALLOCATION','DATABLE',null),
  ('REWORK_COMPLETION_UNRECONCILED','DATABLE',null),
  ('REWORK_FG_QTY_MISMATCH','DATABLE',null),
  ('REWORK_GOOD_WITHOUT_FG','DATABLE',null),
  ('REWORK_PAYROLL_BEFORE_COST_POST','DATABLE',null),
  ('UNBALANCED_POSTED_JOURNALS','DATABLE',null),
  ('V2620AD_OPENING_MATERIAL_TIMELINE_MISMATCH','DATABLE',null),
  ('V2620AE_OPENING_MATERIAL_ROLL_INTEGRITY','DATABLE',null),
  ('V2620AF_OPENING_SOURCE_LINEAGE_MISMATCH','DATABLE',null),
  ('V2620AG_SALE_RESERVATION_LINEAGE_MISMATCH','DATABLE',null),
  ('V2620AH_RETURN_ALLOCATION_LINEAGE_MISMATCH','DATABLE',null),
  ('V2620AI_WORK_SOURCE_LINEAGE_MISMATCH','DATABLE',null),
  ('V2620C_DRAFT_SALE_VALUE_LEAK','DATABLE',null),
  ('V2620C_HPP_COMPONENT_SUM_MISMATCH','DATABLE',null),
  ('V2620C_HPP_STATE_HAS_SUBCENT','DATABLE',null),
  ('V2620C_PO_HPP_BOOK_MISMATCH','DATABLE',null),
  ('V2620C_PO_HPP_TARGET_STATE_MISMATCH','DATABLE',null),
  ('V2620C_SALES_RETURN_REPORT_INPUT_MISMATCH','DATABLE',null),
  ('V2620C_SALE_REVENUE_REPORT_INPUT_MISMATCH','DATABLE',null),
  ('V2620C_VENDOR_PAYMENT_EXACT_STATUS_MISMATCH','DATABLE',null),
  ('V2620C_WIP_SOURCE_CONSERVATION_MISMATCH','DATABLE',null),
  ('V2620D_REDISPATCH_PARTICIPANT_LINEAGE_MISMATCH','DATABLE',null),
  ('V2620D_SALE_LIFECYCLE_HPP_DIMENSION_MISMATCH','DATABLE',null),
  ('V2620E_OPENING_FG_GL_MISMATCH','DATABLE',null),
  ('V2620E_OPENING_HPP_LINEAGE_MISMATCH','DATABLE',null),
  ('V2620E_REDISPATCH_EVENT_MISMATCH','DATABLE',null),
  ('V2620E_SALES_RETURN_VALUE_EXCEEDS_SALE','DATABLE',null),
  ('V2620F_CONVERSION_VALUE_LINEAGE_MISMATCH','DATABLE',null),
  ('V2620F_NON_PO_PRODUCT_HPP_BOOK_MISMATCH','DATABLE',null),
  ('V2620G_LAUNDRY_WIP_CUSTODY_MISMATCH','DATABLE',null),
  ('V2620H_CUSTOMER_AR_BY_CUSTOMER_MISMATCH','DATABLE',null),
  ('V2620H_CUSTOMER_AR_STATUS_MISMATCH','DATABLE',null),
  ('V2620H_FAILED_WASH_RETURN_TIME_MISMATCH','DATABLE',null),
  ('V2620I_SALES_PAYMENT_JOURNAL_LINEAGE_MISMATCH','DATABLE',null),
  ('V2620J_SALES_PAYMENT_IMMUTABLE_FACT_MISMATCH','DATABLE',null),
  ('V2620K_PAYMENT_ALLOCATION_DATE_MISMATCH','DATABLE',null),
  ('V2620L_NEGATIVE_VENDOR_AP','DATABLE',null),
  ('V2620L_NONFINITE_LEDGER_MONEY','DATABLE',null),
  ('V2620M_OPENING_SUBLEDGER_STATE','DATABLE',null),
  ('V2620M_ORPHAN_PAYMENT_JOURNAL','DATABLE',null),
  ('V2620M_PAYMENT_SOURCE_JOURNAL_MISMATCH','DATABLE',null),
  ('V2620M_SUPPLIER_PAYMENT_EXACT_STATUS','DATABLE',null),
  ('V2620N_SUPPLIER_CENT_FACT_LEDGER','DATABLE',null),
  ('V2620O_SUPPLIER_RETURN_ALLOCATION','DATABLE',null),
  ('V2620P_SUPPLIER_RETURN_MATCH_STATE','DATABLE',null),
  ('V2620R_SUPPLIER_INVOICE_SOURCE_STATE','DATABLE',null),
  ('V2620S_SUPPLIER_PAYMENT_BUSINESS_DATE','DATABLE',null),
  ('V2620T_JOURNAL_FUTURE_BUSINESS_DATE','UNCERTAIN',null),
  ('V2620T_MATERIAL_ADJUSTMENT_FACT_LEDGER','DATABLE',null),
  ('V2620T_MATERIAL_ADJUSTMENT_REVALUATION','DATABLE',null),
  ('V2620U_JOURNAL_REVERSAL_BUSINESS_DATE','DATABLE',null),
  ('V2620U_MATERIAL_ADJUSTMENT_BUSINESS_DATE','DATABLE',null),
  ('V2620U_MATERIAL_RECEIPT_BUSINESS_DATE','DATABLE',null),
  ('V2620V_MISC_FINANCE_BUSINESS_DATE','DATABLE',null),
  ('V2620W_SCRAP_BUSINESS_DATE','DATABLE',null),
  ('V2620Y_OPENING_SETTLEMENT_BUSINESS_DATE','DATABLE',null),
  ('V2620Y_SALES_PAYMENT_BUSINESS_DATE','DATABLE',null),
  ('V2620Y_VENDOR_PAYMENT_BUSINESS_DATE','DATABLE',null),
  ('V267_AP_GL_SUBLEDGER_MISMATCH','SYSTEMIC',null),
  ('V267_BROWSER_ROLE_DIRECT_INVOICE_WRITE','SYSTEMIC',null),
  ('V267_ESTIMATED_RECEIPT_MISSING_GRNI_RECLASS','DATABLE',null),
  ('V267_GRNI_GL_SUBLEDGER_MISMATCH','SYSTEMIC',null),
  ('V267_GRNI_MAPPING_INVALID','SYSTEMIC',null),
  ('V267_INVOICE_MATCH_OVER_RECEIPT','DATABLE',null),
  ('V267_LEGACY_CORRECTION_ON_GRNI','DATABLE',null),
  ('V267_MISSING_GRNI_MAPPING','SYSTEMIC',null),
  ('V267_PAYMENT_EXCEEDS_FINAL_AP','DATABLE',null),
  ('V267_POSTED_INVOICE_MISSING_JOURNAL','DATABLE',null),
  ('V267_POSTED_RETURN_MISSING_LIABILITY_SNAPSHOT','DATABLE',null),
  ('V268_ACTIVE_SALE_MISSING_JOURNAL','DATABLE',null),
  ('V268_AR_GL_SUBLEDGER_MISMATCH','SYSTEMIC',null),
  ('V268_BALANCE_SHEET_EQUATION','DATABLE',null),
  ('V268_BROWSER_DIRECT_LEDGER_OR_INVOICE_WRITE','SYSTEMIC',null),
  ('V268_COST_RECALC_EXHAUSTED','QUEUE_FAMILY','RECOST'),
  ('V268_DAILY_BALANCE_LEDGER_MISMATCH','DATABLE',null),
  ('V268_LIABILITY_VIEW_HELPER_PRIVILEGE','SYSTEMIC',null),
  ('V268_POSTED_CUSTOMER_PAYMENT_MISSING_JOURNAL','DATABLE',null),
  ('V268_POSTED_SALES_RETURN_MISSING_JOURNAL','DATABLE',null),
  ('V268_PRODUCTION_FG_WITHOUT_CURRENT_HPP','DATABLE',null),
  ('V268_UNBALANCED_POSTED_JOURNAL','DATABLE',null)
) x(check_name,check_class,dated_by)
$function$;
CREATE OR REPLACE FUNCTION erp.period_blockers_v1(p_through date, p_window_from date)
 RETURNS TABLE(family text, code text, severity text, scope text, impact_date date, reference jsonb, reason text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
-- One engine for close, preview and report confidence (S06/B04).
-- Open items (recost, laundry price, payroll due, dated integrity) use every fact dated on or before p_through.
-- Completeness (attendance cells) uses the window [p_window_from, p_through]; a null start means unbounded. Callers
-- pass erp.period_completeness_from_v1(), the first date this engine was responsible for, so a closed date inside
-- the engine's era is re-checked after a later correction (P-01). Before that start only cells that once had a
-- posted record and lost it (reversed, not replaced) are reported.
-- Stock history follows the posting guards' own order (P-04). A current-state check whose defect is scoped by a
-- dated detector is reported as INFO once the detector confirms it; every other failing current-state check blocks
-- every date and names its class (P-03). Unknown check names block (fail closed).
declare
  v_end timestamptz := ((p_through + 1)::timestamp AT TIME ZONE 'Asia/Jakarta');
  v_fg jsonb;
  v_material jsonb;
  v_fg_confirmed boolean;
  v_material_confirmed boolean;
begin
  if p_through is null then raise exception 'PERIOD_BLOCKERS_DATE_REQUIRED'; end if;

  -- RECOST: open queue rows whose PO has a dated fact on or before the date.
  return query
  select 'RECOST'::text,
    case when q.status='FAILED' and q.attempt_count>=3 then 'RECOST_FAILED_EXHAUSTED' else 'RECOST_PENDING' end,
    case when q.status='FAILED' and q.attempt_count>=3 then 'CRITICAL' else 'RECALC' end,
    'AS_OF'::text, f.first_date,
    jsonb_build_object('queue_id',q.id,'po_id',q.entity_id,'po_number',po.po_number,'status',q.status,
      'attempt_count',q.attempt_count,'recalc_from',q.recalc_from,'facts',f.facts),
    format('Hitung ulang biaya PO %s belum selesai (status %s, percobaan %s); PO ini punya fakta pada atau sebelum %s.',
      coalesce(po.po_number,q.entity_id::text),q.status,q.attempt_count,p_through)
  from erp.cost_recalc_queue q
  left join erp.production_orders po on po.id=q.entity_id
  cross join lateral (
    select min(x.d) first_date, jsonb_agg(distinct x.k) facts from (
      select 'RECALC_FROM' k, erp._cp3_business_date(q.recalc_from) d where q.recalc_from is not null and q.recalc_from<v_end
      union all
      select 'CUTTING_MATERIAL', min(erp._cp3_business_date(m.physical_at))
        from erp.material_stock_movements m join erp.cutting_groups cg on cg.id=m.source_id
        where m.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN') and cg.po_id=q.entity_id and m.physical_at<v_end
        having count(*)>0
      union all
      select 'CONTRACTOR_MATERIAL', min(erp._cp3_business_date(m.physical_at))
        from erp.material_stock_movements m
        join erp.contractor_material_issue_items ii on ii.id=m.source_id
        join erp.contractor_material_issues cmi on cmi.id=ii.issue_id
        where m.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and cmi.po_id=q.entity_id and m.physical_at<v_end
        having count(*)>0
      union all
      select 'FG_LOT', min(erp._cp3_business_date(fl.produced_at))
        from erp.fg_lots fl where fl.po_id=q.entity_id and fl.produced_at<v_end having count(*)>0
      union all
      select 'PO_JOURNAL', min(je.economic_date)
        from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
        where jl.po_id=q.entity_id and je.status in('POSTED','REVERSED') and je.economic_date<=p_through
        having count(*)>0
    ) x
  ) f
  where q.entity_type='PO' and q.status in('PENDING','RUNNING','FAILED') and f.first_date is not null;

  -- A PO queue row whose PO has no dated fact at all cannot be scoped to a date: it applies to every date.
  return query
  select 'RECOST'::text,'RECOST_UNSCOPED_ENTITY'::text,
    case when q.status='FAILED' and q.attempt_count>=3 then 'CRITICAL' else 'RECALC' end,'CURRENT_STATE'::text,null::date,
    jsonb_build_object('queue_id',q.id,'entity_type',q.entity_type,'entity_id',q.entity_id,'status',q.status,'attempt_count',q.attempt_count),
    format('Antrean hitung ulang PO %s belum selesai dan PO ini belum punya fakta bertanggal; berlaku untuk semua tanggal.',q.entity_id)
  from erp.cost_recalc_queue q
  where q.entity_type='PO' and q.status in('PENDING','RUNNING','FAILED') and q.recalc_from is null
    and not exists(select 1 from erp.material_stock_movements m join erp.cutting_groups cg on cg.id=m.source_id
      where m.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN') and cg.po_id=q.entity_id)
    and not exists(select 1 from erp.material_stock_movements m join erp.contractor_material_issue_items ii on ii.id=m.source_id
      join erp.contractor_material_issues cmi on cmi.id=ii.issue_id
      where m.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and cmi.po_id=q.entity_id)
    and not exists(select 1 from erp.fg_lots fl where fl.po_id=q.entity_id)
    and not exists(select 1 from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
      where jl.po_id=q.entity_id and je.status in('POSTED','REVERSED'));

  -- A queue row for another entity type cannot be scoped to a date: conservative, every date.
  return query
  select 'RECOST'::text,'RECOST_UNSCOPED_ENTITY'::text,'CRITICAL'::text,'CURRENT_STATE'::text,null::date,
    jsonb_build_object('queue_id',q.id,'entity_type',q.entity_type,'entity_id',q.entity_id,'status',q.status),
    format('Antrean hitung ulang %s %s belum selesai dan tidak dapat dibatasi ke tanggal.',q.entity_type,q.entity_id)
  from erp.cost_recalc_queue q
  where q.entity_type<>'PO' and q.status in('PENDING','RUNNING','FAILED');

  -- FG history per SKU and per lot, in the order the posting guard uses (physical_at, system_created_at, id): every
  -- prefix, not the net per instant (P-04). Computed over the whole history once; a key blocks the dates from its
  -- first negative instant.
  select coalesce(jsonb_agg(z.k),'[]'::jsonb) into v_fg from (
    select jsonb_build_object('level',s.lvl,'product_id',min(s.product_id::text),'lot_id',s.lot_id,
      'location_id',s.location_id,'quality_grade',s.quality_grade,
      'first_negative_at',min(s.physical_at) filter(where s.balance<0),
      'lowest_qty',min(s.balance)) k
    from (
      select 'SKU'::text lvl,m.product_id,null::uuid lot_id,m.location_id,m.quality_grade,m.physical_at,
        sum(m.qty_signed) over(partition by m.product_id,m.location_id,m.quality_grade
          order by m.physical_at,m.system_created_at,m.id rows unbounded preceding) balance
      from erp.fg_stock_movements m
      union all
      select 'LOT'::text,m.product_id,m.lot_id,m.location_id,m.quality_grade,m.physical_at,
        sum(m.qty_signed) over(partition by m.lot_id,m.location_id,m.quality_grade
          order by m.physical_at,m.system_created_at,m.id rows unbounded preceding)
      from erp.fg_stock_movements m where m.lot_id is not null
    ) s
    group by s.lvl,case when s.lvl='SKU' then s.product_id end,s.lot_id,s.location_id,s.quality_grade
    having bool_or(s.balance<0)
  ) z;

  return query
  select 'INTEGRITY'::text,'FG_QTY_NEGATIVE_ASOF'::text,'CRITICAL'::text,'AS_OF'::text,
    erp._cp3_business_date((k->>'first_negative_at')::timestamptz),k,
    format('Stok barang jadi (%s) negatif sejak %s untuk produk %s di lokasi %s.',
      k->>'level',k->>'first_negative_at',k->>'product_id',k->>'location_id')
  from jsonb_array_elements(v_fg) k
  where (k->>'first_negative_at')::timestamptz<v_end;

  -- Material history on the cost engine's effective history and its exact order (reversed pairs excluded, a
  -- transfer-in ordered right after its transfer-out), per material, location and roll.
  select coalesce(jsonb_agg(z.k),'[]'::jsonb) into v_material from (
    with active as (
      select m.*,row_number() over(partition by m.material_id,m.source_id,m.roll_id,m.physical_at,
          abs(m.qty_signed),m.movement_type order by m.system_created_at,m.id) ordinal
      from erp.material_stock_movements m
      where m.source_type='MATERIAL_TRANSFER' and m.reversal_of_id is null
        and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
    ), pairs as (
      select i.id incoming,o.id outgoing,o.system_created_at out_created
      from active i join active o on o.material_id=i.material_id and o.source_id=i.source_id
        and o.roll_id is not distinct from i.roll_id and o.physical_at=i.physical_at
        and o.qty_signed=-i.qty_signed and o.ordinal=i.ordinal
        and o.movement_type='TRANSFER_OUT' and o.qty_signed<0
      where i.movement_type='TRANSFER_IN' and i.qty_signed>0
        and (o.physical_at,o.system_created_at,o.id)<(i.physical_at,i.system_created_at,i.id)
        and o.location_id<>i.location_id
    ), history as (
      select m.material_id,m.location_id,m.roll_id,m.physical_at,
        sum(m.qty_signed) over(partition by m.material_id,m.location_id,m.roll_id
          order by m.physical_at,coalesce(p.out_created,m.system_created_at),coalesce(p.outgoing,m.id),
            (p.outgoing is not null) rows unbounded preceding) balance
      from erp.material_stock_movements m
      left join pairs p on p.incoming=m.id
      where m.reversal_of_id is null
        and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
    )
    select jsonb_build_object('material_id',h.material_id,'location_id',h.location_id,'roll_id',h.roll_id,
      'first_negative_at',min(h.physical_at) filter(where h.balance<0),'lowest_qty',min(h.balance)) k
    from history h
    group by h.material_id,h.location_id,h.roll_id
    having bool_or(h.balance<0)
  ) z;

  return query
  select 'INTEGRITY'::text,'MATERIAL_QTY_NEGATIVE_ASOF'::text,'CRITICAL'::text,'AS_OF'::text,
    erp._cp3_business_date((k->>'first_negative_at')::timestamptz),k,
    format('Stok bahan negatif sejak %s untuk bahan %s.',k->>'first_negative_at',k->>'material_id')
  from jsonb_array_elements(v_material) k
  where (k->>'first_negative_at')::timestamptz<v_end;

  -- Per-key confirmation (P-03): a current-state check scoped by a detector is INFO only when every key failing it
  -- now is a key the detector found; an empty or partial match blocks every date.
  select count(*)>0 and coalesce(bool_and(exists(select 1 from jsonb_array_elements(v_fg) x where x->>'level'='SKU'
      and x->>'product_id'=k.product_id::text and x->>'location_id' is not distinct from k.location_id::text
      and x->>'quality_grade' is not distinct from k.quality_grade)),false)
  into v_fg_confirmed
  from (select m.product_id,m.location_id,m.quality_grade from erp.fg_stock_movements m
        group by m.product_id,m.location_id,m.quality_grade having sum(m.qty_signed)<0) k;
  select count(*)>0 and coalesce(bool_and(exists(select 1 from jsonb_array_elements(v_material) x
      where x->>'material_id'=k.material_id::text and x->>'location_id' is not distinct from k.location_id::text
      and x->>'roll_id' is not distinct from k.roll_id::text)),false)
  into v_material_confirmed
  from (select m.material_id,m.location_id,m.roll_id from erp.material_stock_movements m
        group by m.material_id,m.location_id,m.roll_id having sum(m.qty_signed)<-0.000001) k;

  -- INTEGRITY (current state), classified (P-03). Queue checks are handled per date by RECOST above.
  return query
  with failing as (
    select distinct on (c.check_name) c.check_name,c.src,c.issue_count,c.details from (
      select 'run_v268_financial_report_checks' src,r.check_name,r.severity,r.issue_count,r.details from erp.run_v268_financial_report_checks() r
      union all
      select 'run_v267_financial_truth_checks',r.check_name,r.severity,r.issue_count,r.details from erp.run_v267_financial_truth_checks() r
      union all
      select 'run_integrity_checks',r.check_name,r.severity,r.issue_count,r.details from erp.run_integrity_checks() r
    ) c
    where c.issue_count>0 and c.severity in('CRITICAL','ERROR')
      and c.check_name not in('V268_COST_RECALC_EXHAUSTED','V268_COST_RECALC_PENDING','STALE_RECOST_QUEUE','FAILED_RECOST_QUEUE')
    order by c.check_name,c.src
  ), registry(check_name,check_class,dated_by) as (
    select * from erp.period_integrity_check_registry_v1()
  ), classified as (
    select f.*,coalesce(r.check_class,'UNCLASSIFIED') check_class,r.dated_by,
      case r.dated_by when 'FG_QTY_NEGATIVE_ASOF' then v_fg_confirmed
                      when 'MATERIAL_QTY_NEGATIVE_ASOF' then v_material_confirmed
                      else false end confirmed
    from failing f left join registry r on r.check_name=f.check_name
  )
  select 'INTEGRITY'::text,c.check_name,
    case when c.check_class='DATED_EQUIVALENT' and c.confirmed then 'INFO' else 'CRITICAL' end,
    'CURRENT_STATE'::text,null::date,
    jsonb_build_object('check_name',c.check_name,'issue_count',c.issue_count,'source',c.src,'class',c.check_class,
      'dated_by',c.dated_by,'dated_detector_confirmed',c.confirmed,
      'date_policy',case when c.check_class='DATED_EQUIVALENT' and c.confirmed then 'SCOPED_BY_DATED_DETECTOR'
                         else 'BLOCKS_EVERY_DATE' end),
    case when c.check_class='DATED_EQUIVALENT' and c.confirmed
      then format('%s: dibatasi per tanggal oleh %s.',coalesce(c.details,c.check_name),c.dated_by)
      else coalesce(c.details,c.check_name) end
  from classified c;

  -- INTEGRITY (dated): GL inventory balance negative at any balance date on or before the date.
  return query
  select 'INTEGRITY'::text,'GL_INVENTORY_NEGATIVE_ASOF'::text,'CRITICAL'::text,'AS_OF'::text,min(g.balance_date),
    jsonb_build_object('account',g.mapping_key,'first_negative_date',min(g.balance_date),'lowest_balance',min(g.balance)),
    format('Saldo buku %s negatif sejak %s (terendah %s).',g.mapping_key,min(g.balance_date),min(g.balance))
  from (
    select k.mapping_key,a.balance_date,
      sum(a.debit_total-a.credit_total) over(partition by a.account_id order by a.balance_date) balance
    from erp.account_daily_balances a
    join (values('MATERIAL_INVENTORY'),('WIP'),('FG_INVENTORY')) k(mapping_key) on a.account_id=erp.account_id(k.mapping_key)
    where a.balance_date<=p_through
  ) g
  where g.balance<-0.005
  group by g.mapping_key;

  -- ATTENDANCE (window): eligible worker-days without a current posted record (owner: existing rule, OFF recorded).
  return query
  select 'ATTENDANCE'::text,'ATTENDANCE_CELL_MISSING'::text,'POLICY'::text,'WINDOW'::text,min(x.work_day),
    jsonb_build_object('contractor_id',x.contractor_id,'contractor_name',x.contractor_name,'worker_id',x.worker_id,
      'worker_name',x.worker_name,'missing_days',count(*),'first_missing',min(x.work_day),'last_missing',max(x.work_day),
      'sample_days',(array_agg(x.work_day order by x.work_day))[1:10],'window_from',p_window_from),
    format('Absensi %s (%s) kosong %s hari antara %s dan %s; hari libur dicatat OFF.',
      x.worker_name,x.contractor_name,count(*),min(x.work_day),max(x.work_day))
  from (
    select w.contractor_id,c.contractor_name,w.id worker_id,w.worker_name,gs.d::date as work_day
    from erp.contractor_workers w
    join erp.contractors c on c.id=w.contractor_id
    join erp.worker_employment_periods e on e.worker_id=w.id
    cross join lateral generate_series(
      greatest(e.started_on,coalesce(p_window_from,e.started_on))::timestamp,
      least(coalesce(e.ended_on,p_through),p_through)::timestamp,interval '1 day') gs(d)
    where c.attendance_required and w.pay_scheme in('DAILY','HYBRID')
      and not exists(select 1 from erp.attendance_records a
        where a.worker_id=w.id and a.attendance_date=gs.d::date and coalesce(a.record_lifecycle,'POSTED')='POSTED')
  ) x
  group by x.contractor_id,x.contractor_name,x.worker_id,x.worker_name;

  -- ATTENDANCE (before the window): an eligible worker-day that had a posted record which was later reversed and
  -- never replaced. The date was complete when it was accepted; a later change removed it (P-01).
  return query
  select 'ATTENDANCE'::text,'ATTENDANCE_CELL_REVERSED_UNREPLACED'::text,'POLICY'::text,'AS_OF'::text,min(x.work_day),
    jsonb_build_object('contractor_id',x.contractor_id,'contractor_name',x.contractor_name,'worker_id',x.worker_id,
      'worker_name',x.worker_name,'missing_days',count(*),'first_missing',min(x.work_day),'last_missing',max(x.work_day),
      'sample_days',(array_agg(x.work_day order by x.work_day))[1:10],'window_from',p_window_from),
    format('Absensi %s (%s) pada %s hari antara %s dan %s sudah dibatalkan dan belum dicatat ulang.',
      x.worker_name,x.contractor_name,count(*),min(x.work_day),max(x.work_day))
  from (
    select distinct w.contractor_id,c.contractor_name,w.id worker_id,w.worker_name,r.attendance_date work_day
    from erp.attendance_records r
    join erp.contractor_workers w on w.id=r.worker_id
    join erp.contractors c on c.id=w.contractor_id
    where p_window_from is not null and r.attendance_date<p_window_from and r.attendance_date<=p_through
      and r.record_lifecycle='REVERSED'
      and c.attendance_required and w.pay_scheme in('DAILY','HYBRID')
      and exists(select 1 from erp.worker_employment_periods e where e.worker_id=w.id
        and r.attendance_date between e.started_on and coalesce(e.ended_on,r.attendance_date))
      and not exists(select 1 from erp.attendance_records a
        where a.worker_id=w.id and a.attendance_date=r.attendance_date and coalesce(a.record_lifecycle,'POSTED')='POSTED')
  ) x
  group by x.contractor_id,x.contractor_name,x.worker_id,x.worker_name;

  -- PAYROLL: payroll due on or before the date that is not approved (owner: labour recognised at period_end).
  return query
  select 'PAYROLL'::text,'PAYROLL_NOT_APPROVED'::text,'POLICY'::text,'AS_OF'::text,ps.period_end,
    jsonb_build_object('payroll_id',ps.id,'payroll_number',ps.payroll_number,'contractor_id',ps.contractor_id,
      'period_start',ps.period_start,'period_end',ps.period_end,'status',ps.status),
    format('Payroll %s (%s s/d %s) masih %s; belum disetujui.',ps.payroll_number,ps.period_start,ps.period_end,ps.status)
  from erp.payroll_settlements ps
  where ps.status in('DRAFT','CALCULATED','REVIEW') and ps.period_end<=p_through;

  -- PAYROLL: paid attendance on or before the date that no non-reversed payroll has taken (linkage, not date range).
  return query
  select 'PAYROLL'::text,'PAYROLL_ATTENDANCE_UNCOVERED'::text,'POLICY'::text,'AS_OF'::text,min(ar.attendance_date),
    jsonb_build_object('contractor_id',ar.contractor_id,'worker_id',ar.worker_id,'worker_name',w.worker_name,
      'records',count(*),'first_date',min(ar.attendance_date),'last_date',max(ar.attendance_date)),
    format('Absensi %s: %s hari berbayar antara %s dan %s belum masuk payroll.',w.worker_name,count(*),min(ar.attendance_date),max(ar.attendance_date))
  from erp.attendance_records ar
  join erp.contractor_workers w on w.id=ar.worker_id
  join erp.contractors c on c.id=ar.contractor_id
  where ar.attendance_date<=p_through and coalesce(ar.record_lifecycle,'POSTED')='POSTED'
    and ar.paid_fraction>0 and w.pay_scheme in('DAILY','HYBRID') and c.attendance_required
    and not exists(select 1 from erp.payroll_attendance_items pai join erp.payroll_settlements ps on ps.id=pai.payroll_id
      where pai.attendance_record_id=ar.id and ps.status<>'REVERSED')
  group by ar.contractor_id,ar.worker_id,w.worker_name;

  -- PAYROLL: eligible piece or rework work on or before the date that no non-reversed payroll has taken.
  return query
  select 'PAYROLL'::text,'PAYROLL_WORK_UNCOVERED'::text,'POLICY'::text,'AS_OF'::text,
    min(erp._cp3_business_date(e.eligible_at)),
    jsonb_build_object('contractor_id',e.contractor_id,'lines',count(*),'remaining_qty',sum(e.remaining_qty),
      'remaining_amount',sum(e.remaining_amount),'first_eligible_at',min(e.eligible_at)),
    format('Hasil kerja kontraktor %s: %s baris (%s pcs) pada atau sebelum %s belum masuk payroll.',
      e.contractor_id,count(*),sum(e.remaining_qty),p_through)
  from erp.v_payroll_eligible_work_lines e
  where e.eligible_at<v_end and e.remaining_qty>0
  group by e.contractor_id;

  -- LAUNDRY: sent quantity still costed at an unknown (null) delivery rate on or before the date.
  return query
  select 'LAUNDRY'::text,'LAUNDRY_PRICE_UNKNOWN'::text,'POLICY'::text,'AS_OF'::text,
    erp._cp3_business_date(ld.physical_at),
    jsonb_build_object('delivery_id',ld.id,'delivery_number',ld.delivery_number,'delivery_line_id',ldl.id,
      'po_id',ld.po_id,'uncosted_qty',greatest(ldl.qty_sent_pcs-coalesce(rc.costed_qty,0),0)),
    format('Harga laundry kiriman %s belum diketahui untuk %s pcs; isi estimasi owner.',
      ld.delivery_number,greatest(ldl.qty_sent_pcs-coalesce(rc.costed_qty,0),0))
  from erp.laundry_delivery_lines ldl
  join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
  left join lateral (select sum(lrl.qty_good_received+lrl.qty_bs_laundry) costed_qty
    from erp.laundry_receipt_lines lrl join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    where lrl.delivery_line_id=ldl.id and lr.status='POSTED' and lrl.actual_cost_status in('ESTIMATED','FINAL')) rc on true
  where ld.status not in('DRAFT','REVERSED') and ldl.estimated_rate_snapshot is null
    and ld.physical_at<v_end and ldl.qty_sent_pcs-coalesce(rc.costed_qty,0)>0;

  -- LAUNDRY: a delivery rate that is not a finite non-negative number is not a known price (P-02).
  return query
  select 'LAUNDRY'::text,'LAUNDRY_PRICE_INVALID'::text,'CRITICAL'::text,'AS_OF'::text,
    erp._cp3_business_date(ld.physical_at),
    jsonb_build_object('delivery_id',ld.id,'delivery_number',ld.delivery_number,'delivery_line_id',ldl.id,
      'po_id',ld.po_id,'rate',ldl.estimated_rate_snapshot::text),
    format('Harga laundry kiriman %s tidak valid (%s); harga harus angka hingga dan tidak negatif.',
      ld.delivery_number,ldl.estimated_rate_snapshot::text)
  from erp.laundry_delivery_lines ldl
  join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
  where ld.status not in('DRAFT','REVERSED') and ld.physical_at<v_end
    and (ldl.estimated_rate_snapshot='NaN'::numeric or ldl.estimated_rate_snapshot<0);

  -- GRNI: owner allows close with an estimate; reported, never blocking.
  return query
  select 'GRNI'::text,'GRNI_ESTIMATE_OPEN'::text,'INFO'::text,'CURRENT_STATE'::text,
    erp._cp3_business_date(min(g.physical_at)),
    jsonb_build_object('receipts',count(*),'estimated_amount',sum(g.grni_estimated_amount)),
    format('%s penerimaan bahan masih memakai estimasi GRNI (total %s); boleh ditutup dengan estimasi.',count(*),sum(g.grni_estimated_amount))
  from erp.v_material_grni_aging g
  where g.physical_at<v_end
  having count(*)>0;
end
$function$;
CREATE OR REPLACE FUNCTION erp.period_readiness_v1(p_through date, p_window_from date)
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
select jsonb_build_object(
  'engine','PERIOD_READINESS_V1','through',p_through,'window_from',p_window_from,
  'status',case when coalesce(bool_or(b.severity in('CRITICAL','POLICY')),false) then 'BLOCKED'
                when coalesce(bool_or(b.severity='RECALC'),false) then 'RECALC_PENDING' else 'READY' end,
  'blocker_count',count(*) filter(where b.severity<>'INFO'),
  'critical_count',count(*) filter(where b.severity='CRITICAL'),
  'policy_count',count(*) filter(where b.severity='POLICY'),
  'recalc_count',count(*) filter(where b.severity='RECALC'),
  'blockers',coalesce(jsonb_agg(to_jsonb(b) order by b.family,b.code,b.impact_date nulls first,b.reference::text) filter(where b.severity<>'INFO'),'[]'::jsonb),
  'info',coalesce(jsonb_agg(to_jsonb(b) order by b.family,b.code,b.reference::text) filter(where b.severity='INFO'),'[]'::jsonb))
from erp.period_blockers_v1(p_through,p_window_from) b
$function$;
CREATE OR REPLACE FUNCTION erp.period_completeness_from_v1()
 RETURNS date
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
-- First date whose completeness this engine enforces (P-01). Before the first filing it is the day after the
-- current closed_through; afterwards it stays at the day after the first filing's previous cutoff, so every date
-- closed by the engine is re-checked after a later correction. A reopen below that day moves it back. Null means
-- unbounded (nothing was ever closed, or the first filing started from an empty cutoff).
select case
  when c.closed_through is null then null
  when f.id is null then c.closed_through+1
  when f.previous_closed_through is null then null
  else least(f.previous_closed_through+1,c.closed_through+1) end
from erp.accounting_period_control c
left join lateral (select x.id,x.previous_closed_through from erp.accounting_close_filings_v1 x
  order by x.filed_at,x.id limit 1) f on true
where c.singleton_id=1
$function$;
CREATE OR REPLACE FUNCTION erp.accounting_close_preflight_v1(p_through date)
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
  return erp.period_readiness_v1(p_through,erp.period_completeness_from_v1())||jsonb_build_object(
    'closed_through',v_closed,
    'date_allowed',p_through<erp._cp3_business_date(statement_timestamp()) and (v_closed is null or p_through>=v_closed));
end
$function$;
CREATE OR REPLACE FUNCTION erp.set_laundry_rate_owner_estimate_v1(p_delivery_line_id uuid, p_rate numeric, p_reason text)
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
  -- A price is a finite, non-negative amount with at most two decimals that fits numeric(18,2) (P-02). NaN and
  -- Infinity are numeric values in PostgreSQL and pass the sign and scale tests, so they are refused by name.
  if p_rate is null or p_rate='NaN'::numeric or p_rate<0 or p_rate>=10000000000000000::numeric
     or p_rate<>round(p_rate,2) then
    raise exception 'LAUNDRY_ESTIMATE_RATE_INVALID';
  end if;
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
$function$;
CREATE OR REPLACE FUNCTION erp.close_accounting_through(p_closed_through date, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare v_old date; v_material uuid; v_readiness jsonb;
begin
  perform erp.require_owner_admin();
  if p_closed_through is null then raise exception 'Tanggal tutup buku wajib diisi'; end if;
  if p_closed_through>=erp._cp3_business_date(statement_timestamp()) then raise exception 'Tutup buku hanya boleh sampai tanggal sebelum hari ini'; end if;
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan tutup buku wajib diisi'; end if;
  select closed_through into v_old from erp.accounting_period_control where singleton_id=1 for update;
  if v_old is not null and p_closed_through<v_old then
    raise exception 'Untuk membuka kembali periode gunakan reopen_accounting_through(); periode saat ini sudah ditutup sampai %',v_old;
  end if;
  -- One engine, evaluated after the control row lock so posting paths that read closed_through wait for this close.
  v_readiness:=erp.period_readiness_v1(p_closed_through,erp.period_completeness_from_v1());
  if v_readiness->>'status'<>'READY' then
    raise exception using message=format('CLOSE_BLOCKED: tutup buku sampai %s ditolak, %s penghalang (%s).',p_closed_through,
      v_readiness->>'blocker_count',(select string_agg(distinct b->>'code',', ') from jsonb_array_elements(v_readiness->'blockers') b)),
      detail=v_readiness::text,hint='Lihat erp_accounting_close_preflight_v1 untuk daftar lengkap.';
  end if;
  update erp.accounting_period_control
  set closed_through=p_closed_through,updated_at=statement_timestamp(),updated_by=erp.current_app_user_id(),change_reason=p_reason
  where singleton_id=1;

  for v_material in select id from erp.materials order by id loop
    perform erp.refresh_material_cost_checkpoint(v_material,p_closed_through);
  end loop;

  insert into erp.audit_logs(entity_type,entity_id,action,old_data,new_data,changed_by,change_reason)
  values('accounting_period_control',null,'UPDATE',jsonb_build_object('closed_through',v_old),jsonb_build_object('closed_through',p_closed_through,'material_cost_checkpoints_refreshed',true),erp.current_app_user_id(),p_reason);

  -- Filed snapshot: never overwritten; later corrections are read from the engine as current-corrected values.
  insert into erp.accounting_close_filings_v1(closed_through,previous_closed_through,filed_by,reason,readiness,gl_balances)
  values(p_closed_through,v_old,erp.current_app_user_id(),p_reason,v_readiness,
    (select coalesce(jsonb_object_agg(ca.account_code,round(b.balance,2) order by ca.account_code),'{}'::jsonb)
     from (select a.account_id,sum(a.debit_total-a.credit_total) balance from erp.account_daily_balances a
           where a.balance_date<=p_closed_through group by a.account_id) b
     join erp.chart_accounts ca on ca.id=b.account_id));
end;
$function$;
CREATE OR REPLACE FUNCTION erp.get_owner_financial_snapshot_v2(p_from date, p_to date, p_as_of date DEFAULT ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_catalog', 'pg_temp'
AS $function$
declare
  v_assets numeric:=0;v_liabilities numeric:=0;v_equity numeric:=0;v_current_earnings numeric:=0;
  v_cash numeric:=0;v_ar numeric:=0;v_material numeric:=0;v_wip numeric:=0;v_fg numeric:=0;
  v_ap numeric:=0;v_grni numeric:=0;
  v_sales_revenue numeric:=0;v_cogs numeric:=0;v_other_income numeric:=0;v_opex numeric:=0;v_net_profit numeric:=0;
  v_gross_sales numeric:=0;v_discounts numeric:=0;v_sales_returns numeric:=0;
  v_operational_net_sales numeric:=0;v_sales_revenue_bridge numeric:=0;
  v_qc_good numeric:=0;v_qc_bs numeric:=0;
  v_laundry_good numeric:=0;v_laundry_bs numeric:=0;v_laundry_stuck numeric:=0;v_laundry_missing numeric:=0;
  v_laundry_outstanding numeric:=0;
  v_failed_checks jsonb:='[]'::jsonb;
  v_grni_docs bigint:=0;v_grni_oldest integer:=0;v_ap_docs bigint:=0;v_ap_overdue numeric:=0;
  v_critical bigint:=0;v_warning bigint:=0;v_pending bigint:=0;
  v_closed date;v_readiness jsonb;v_warnings jsonb:='[]'::jsonb;v_filing jsonb;
begin
  perform erp.require_owner_admin();
  if p_from is null or p_to is null or p_as_of is null then raise exception 'p_from, p_to and p_as_of are required'; end if;
  if p_from>p_to then raise exception 'p_from cannot be after p_to'; end if;
  if p_to>p_as_of then raise exception 'p_to cannot be after p_as_of'; end if;

  select
    coalesce(sum(case when ca.account_type='ASSET' then a.debit_total-a.credit_total else 0 end),0),
    coalesce(sum(case when ca.account_type='LIABILITY' then a.credit_total-a.debit_total else 0 end),0),
    coalesce(sum(case when ca.account_type='EQUITY' then a.credit_total-a.debit_total else 0 end),0),
    coalesce(sum(case when ca.account_type in('REVENUE','EXPENSE') then a.credit_total-a.debit_total else 0 end),0)
  into v_assets,v_liabilities,v_equity,v_current_earnings
  from erp.account_daily_balances a join erp.chart_accounts ca on ca.id=a.account_id
  where a.balance_date<=p_as_of;

  select coalesce(sum(a.debit_total-a.credit_total),0) into v_cash
  from erp.account_daily_balances a
  where a.balance_date<=p_as_of and a.account_id in(
    select ca.coa_account_id from erp.cash_accounts ca
    union select erp.account_id('CASH')
  );
  select coalesce(sum(a.debit_total-a.credit_total),0) into v_ar
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('AR_CUSTOMER');
  select coalesce(sum(a.debit_total-a.credit_total),0) into v_material
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('MATERIAL_INVENTORY');
  select coalesce(sum(a.debit_total-a.credit_total),0) into v_wip
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('WIP');
  select coalesce(sum(a.debit_total-a.credit_total),0) into v_fg
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('FG_INVENTORY');
  select coalesce(sum(a.credit_total-a.debit_total),0) into v_ap
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('AP_SUPPLIER');
  select coalesce(sum(a.credit_total-a.debit_total),0) into v_grni
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('GRNI_MATERIAL');

  select
    coalesce(sum(case when a.account_id=erp.account_id('SALES_REVENUE') then a.credit_total-a.debit_total else 0 end),0),
    coalesce(sum(case when a.account_id=erp.account_id('COGS') then a.debit_total-a.credit_total else 0 end),0),
    coalesce(sum(case when ca.account_type='REVENUE' and a.account_id<>erp.account_id('SALES_REVENUE') then a.credit_total-a.debit_total else 0 end),0),
    coalesce(sum(case when ca.account_type='EXPENSE' and a.account_id<>erp.account_id('COGS') then a.debit_total-a.credit_total else 0 end),0),
    coalesce(sum(case when ca.account_type in('REVENUE','EXPENSE') then a.credit_total-a.debit_total else 0 end),0)
  into v_sales_revenue,v_cogs,v_other_income,v_opex,v_net_profit
  from erp.account_daily_balances a join erp.chart_accounts ca on ca.id=a.account_id
  where a.balance_date between p_from and p_to;

  with sale_events as(
    select original.source_id sale_id,1::integer event_sign
    from erp.journal_entries original
    where original.source_type='SALE' and original.status in('POSTED','REVERSED')
      and original.transaction_date between p_from and p_to
    union all
    select original.source_id,-1::integer
    from erp.journal_entries reversal
    join erp.journal_entries original on original.id=reversal.reversal_of_id
      and original.source_type='SALE'
    where reversal.source_type='JOURNAL_REVERSAL' and reversal.status='POSTED'
      and reversal.transaction_date between p_from and p_to
  )
  select coalesce(sum(e.event_sign*i.qty_pcs*i.unit_price_snapshot),0),
         coalesce(sum(e.event_sign*i.discount_amount),0)
  into v_gross_sales,v_discounts
  from sale_events e join erp.sales_items i on i.sale_id=e.sale_id;

  with return_events as(
    select original.source_id return_id,1::integer event_sign
    from erp.journal_entries original
    where original.source_type='SALES_RETURN' and original.status in('POSTED','REVERSED')
      and original.transaction_date between p_from and p_to
    union all
    select original.source_id,-1::integer
    from erp.journal_entries reversal
    join erp.journal_entries original on original.id=reversal.reversal_of_id
      and original.source_type='SALES_RETURN'
    where reversal.source_type='JOURNAL_REVERSAL' and reversal.status='POSTED'
      and reversal.transaction_date between p_from and p_to
  )
  select coalesce(sum(e.event_sign*i.refund_amount),0) into v_sales_returns
  from return_events e join erp.sales_return_items i on i.return_id=e.return_id;
  v_operational_net_sales:=round(v_gross_sales-v_discounts-v_sales_returns,2);
  v_sales_revenue_bridge:=round(v_operational_net_sales-v_sales_revenue,2);

  select coalesce(sum(i.qty_good_pcs),0),coalesce(sum(i.qty_bs_pcs),0)
  into v_qc_good,v_qc_bs
  from erp.qc_inspection_items i join erp.qc_inspections h on h.id=i.inspection_id
  where h.status='POSTED' and erp._cp3_business_date(h.physical_at) between p_from and p_to;
  select coalesce(sum(i.qty_good_received),0),coalesce(sum(i.qty_bs_laundry),0),
         coalesce(sum(i.qty_stuck),0),coalesce(sum(i.qty_missing),0)
  into v_laundry_good,v_laundry_bs,v_laundry_stuck,v_laundry_missing
  from erp.laundry_receipt_lines i join erp.laundry_receipts h on h.id=i.receipt_id
  where h.status='POSTED' and erp._cp3_business_date(h.physical_at) between p_from and p_to;

  select greatest(coalesce(sum(case
    when w.stage_to='LAUNDRY' then w.qty_pcs
    when w.stage_from='LAUNDRY' then -w.qty_pcs
    else 0 end),0),0)
  into v_laundry_outstanding
  from erp.wip_stage_events w
  where erp._cp3_business_date(w.physical_at)<=p_as_of
    and w.source_type in(
      'LAUNDRY_DELIVERY_LINE','LAUNDRY_RECEIPT_LINE',
      'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL','CP6_LAUNDRY_RECEIPT_WIP_REVERSAL'
    );

  select count(*)::bigint,coalesce(max(unfinalized_days),0)::integer
  into v_grni_docs,v_grni_oldest from erp.v_material_grni_aging;
  select count(*)::bigint,coalesce(sum(case when days_overdue>0 then outstanding_amount else 0 end),0)
  into v_ap_docs,v_ap_overdue from erp.v_supplier_ap_aging where outstanding_amount>0.005;

  -- Confidence for the requested date comes from the close engine (AUD-S06/B04): open items dated on or before
  -- p_as_of, attendance completeness from the engine's first date, classified current-state integrity. A filed date
  -- shows its filing next to the current-corrected status; the filing itself is never rewritten.
  select closed_through into v_closed from erp.accounting_period_control where singleton_id=1;
  v_readiness:=erp.period_readiness_v1(p_as_of,erp.period_completeness_from_v1());
  select jsonb_build_object('filing_id',f.id,'closed_through',f.closed_through,'previous_closed_through',
    f.previous_closed_through,'filed_at',f.filed_at,'filed_status',f.readiness->>'status')
  into v_filing from erp.accounting_close_filings_v1 f
  where f.closed_through>=p_as_of and (f.previous_closed_through is null or f.previous_closed_through<p_as_of)
  order by f.filed_at desc,f.id desc limit 1;
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
  if abs(v_sales_revenue_bridge)>0.005 then
    v_critical:=v_critical+1;
    v_failed_checks:=v_failed_checks||jsonb_build_array(jsonb_build_object(
      'check_name','V2620D_PERIOD_SALES_REVENUE_BRIDGE_MISMATCH',
      'severity','CRITICAL','issue_count',1,
      'details','Signed Sale/Sales-return lifecycle events do not reconcile to SALES_REVENUE for the selected posting period'
    ));
  end if;

  return jsonb_build_object(
    'basis',jsonb_build_object(
      'period_from',p_from,'period_to',p_to,'balance_sheet_as_of',p_as_of,
      'supplier_exposure_basis','CURRENT_OPERATIONAL_STATE',
      'performance_lifecycle_basis','SIGNED_JOURNAL_LIFECYCLE_EVENTS_IN_POSTING_PERIOD',
      'performance_reconciliation_basis','OPERATIONAL_NET_SALES_MINUS_SALES_REVENUE_GL',
      'quality_event_basis','CURRENT_OPERATIONAL_STATE_WITH_EVENT_DATE_CUTOFF',
      'laundry_outstanding_basis','IMMUTABLE_WIP_STAGE_EVENT_NET_AS_OF_BALANCE_DATE'
    ),
    'data_confidence',jsonb_build_object(
      'status',case when v_critical>0 then 'BLOCKED'
                    when v_pending>0 then 'RECALC_PENDING' else 'READY' end,
      'critical_issue_count',v_critical,'warning_issue_count',v_warning,
      'pending_cost_recalc_count',v_pending,'failed_checks',v_failed_checks,
      'engine',v_readiness->>'engine','as_of',p_as_of,'window_from',v_readiness->'window_from',
      'closed_through',v_closed,'blockers',v_readiness->'blockers','info',v_readiness->'info',
      'filing',v_filing,'changed_since_filing',v_filing is not null and v_readiness->>'status'<>'READY'
    ),
    'financial_position',jsonb_build_object(
      'assets',round(v_assets,2),'cash',round(v_cash,2),'customer_ar',round(v_ar,2),
      'material_inventory',round(v_material,2),'wip_inventory',round(v_wip,2),'fg_inventory',round(v_fg,2),
      'liabilities',round(v_liabilities,2),'supplier_final_ap',round(v_ap,2),
      'grni_estimated_liability',round(v_grni,2),'recorded_equity',round(v_equity,2),
      'current_earnings',round(v_current_earnings,2),
      'liabilities_plus_equity',round(v_liabilities+v_equity+v_current_earnings,2),
      'balance_difference',round(v_assets-v_liabilities-v_equity-v_current_earnings,2)
    ),
    'performance',jsonb_build_object(
      'sales_revenue_gl',round(v_sales_revenue,2),'cogs_gl',round(v_cogs,2),
      'gross_profit',round(v_sales_revenue-v_cogs,2),
      'gross_margin_pct',case when abs(v_sales_revenue)>0.005 then round((v_sales_revenue-v_cogs)*100/v_sales_revenue,4) else null end,
      'other_income',round(v_other_income,2),'operating_and_other_expense',round(v_opex,2),
      'net_profit',round(v_net_profit,2),
      'net_margin_pct',case when abs(v_sales_revenue)>0.005 then round(v_net_profit*100/v_sales_revenue,4) else null end,
      'gross_sales_before_discount',round(v_gross_sales,2),'line_discounts',round(v_discounts,2),
      'posted_sales_returns',round(v_sales_returns,2),
      'operational_net_sales',v_operational_net_sales,
      'sales_revenue_bridge_delta',v_sales_revenue_bridge,
      'sales_revenue_reconciled',abs(v_sales_revenue_bridge)<=0.005
    ),
    'quality',jsonb_build_object(
      'qc_good_pcs',v_qc_good,'qc_bs_pcs',v_qc_bs,
      'qc_defect_rate_pct',case when v_qc_good+v_qc_bs>0 then round(v_qc_bs*100/(v_qc_good+v_qc_bs),4) else null end,
      'laundry_good_received_pcs',v_laundry_good,'laundry_bs_pcs',v_laundry_bs,
      'laundry_bs_rate_on_resolved_receipts_pct',case when v_laundry_good+v_laundry_bs>0 then round(v_laundry_bs*100/(v_laundry_good+v_laundry_bs),4) else null end,
      'laundry_outstanding_pcs',v_laundry_outstanding,
      'legacy_receipt_stuck_pcs',v_laundry_stuck,'legacy_receipt_missing_pcs',v_laundry_missing
    ),
    'supplier_exposure',jsonb_build_object(
      'unfinalized_receipt_count',v_grni_docs,'oldest_unfinalized_days',v_grni_oldest,
      'open_final_ap_document_count',v_ap_docs,'overdue_final_ap_amount',round(v_ap_overdue,2)
    )
  );
end
$function$;
CREATE OR REPLACE FUNCTION public.erp_accounting_close_preflight_v1(p_through date)
 RETURNS jsonb
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
 select erp.accounting_close_preflight_v1(p_through);
$function$;
CREATE OR REPLACE FUNCTION public.erp_close_accounting_through_v1(p_closed_through date, p_reason text)
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
$function$;
CREATE OR REPLACE FUNCTION public.erp_set_laundry_rate_owner_estimate_v1(p_delivery_line_id uuid, p_rate numeric, p_reason text)
 RETURNS jsonb
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
 select erp.set_laundry_rate_owner_estimate_v1(p_delivery_line_id,p_rate,p_reason);
$function$;
create trigger trg_guard_accounting_close_filing_immutable before update or delete on erp.accounting_close_filings_v1
  for each row execute function erp.guard_accounting_close_filing_immutable_v1();
create trigger trg_guard_accounting_close_filing_truncate before truncate on erp.accounting_close_filings_v1
  for each statement execute function erp.guard_accounting_close_filing_immutable_v1();
create trigger trg_guard_laundry_rate_owner_estimate_immutable before update or delete on erp.laundry_rate_owner_estimates_v1
  for each row execute function erp.guard_laundry_rate_owner_estimate_immutable_v1();
create trigger trg_guard_laundry_rate_owner_estimate_truncate before truncate on erp.laundry_rate_owner_estimates_v1
  for each statement execute function erp.guard_laundry_rate_owner_estimate_immutable_v1();
revoke all on function erp.guard_accounting_close_filing_immutable_v1() from public,anon,authenticated,service_role;
revoke all on function erp.guard_laundry_rate_owner_estimate_immutable_v1() from public,anon,authenticated,service_role;
revoke all on function erp.period_integrity_check_registry_v1() from public,anon,authenticated,service_role;
revoke all on function erp.period_blockers_v1(date,date) from public,anon,authenticated,service_role;
revoke all on function erp.period_readiness_v1(date,date) from public,anon,authenticated,service_role;
revoke all on function erp.period_completeness_from_v1() from public,anon,authenticated,service_role;
revoke all on function erp.accounting_close_preflight_v1(date) from public,anon,authenticated,service_role;
revoke all on function erp.set_laundry_rate_owner_estimate_v1(uuid,numeric,text) from public,anon,authenticated,service_role;
revoke all on function public.erp_accounting_close_preflight_v1(date) from public,anon;
grant execute on function public.erp_accounting_close_preflight_v1(date) to authenticated,service_role;
revoke all on function public.erp_close_accounting_through_v1(date,text) from public,anon;
grant execute on function public.erp_close_accounting_through_v1(date,text) to authenticated,service_role;
revoke all on function public.erp_set_laundry_rate_owner_estimate_v1(uuid,numeric,text) from public,anon;
grant execute on function public.erp_set_laundry_rate_owner_estimate_v1(uuid,numeric,text) to authenticated,service_role;
insert into erp.schema_migrations(version,description) values('v2.6.20aw','Close readiness engine: preflight, close and report share one per-date engine');
do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule')
), objects as (
 select 'FUNCTION:'||format('%I.%I(%s)',n.nspname,p.proname,replace(oidvectortypes(p.proargtypes),', ',',')) k,
 jsonb_build_array(pg_get_functiondef(p.oid),pg_get_userbyid(p.proowner),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl)a order by a::text) end) v
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p')
 union all
 select 'RELATION:'||format('%I.%I',nspname,relname),jsonb_build_array(relkind,pg_get_userbyid(relowner),
  case when relacl is null then null else array(select a::text from unnest(relacl)a order by a::text) end,
  relrowsecurity,relforcerowsecurity,relreplident,relpersistence,relispartition,reloptions)
 from relations
 union all
 select 'COLUMN:'||format('%I.%I.%I',r.nspname,r.relname,a.attname),
 jsonb_build_array((select count(*) from pg_attribute visible where visible.attrelid=a.attrelid and visible.attnum>0 and not visible.attisdropped and visible.attnum<=a.attnum),format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,
  pg_get_expr(d.adbin,d.adrelid),a.attcollation::regcollation::text,
  case when a.attacl is null then null else array(select x::text from unnest(a.attacl)x order by x::text) end)
 from relations r join pg_attribute a on a.attrelid=r.oid and a.attnum>0 and not a.attisdropped
 left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum
 union all
 select 'CONSTRAINT:'||format('%I.%I.%I',r.nspname,r.relname,c.conname),
 jsonb_build_array(c.contype,pg_get_constraintdef(c.oid),c.condeferrable,c.condeferred,c.convalidated,c.conislocal,c.connoinherit)
 from relations r join pg_constraint c on c.conrelid=r.oid
 union all
 select 'INDEX:'||format('%I.%I',r.nspname,c.relname),
 jsonb_build_array(pg_get_indexdef(i.indexrelid),i.indisunique,i.indisprimary,i.indisexclusion,i.indisvalid,i.indisready,i.indisclustered,i.indisreplident,c.reloptions)
 from relations r join pg_index i on i.indrelid=r.oid join pg_class c on c.oid=i.indexrelid
 union all
 select 'TRIGGER:'||format('%I.%I.%I',r.nspname,r.relname,t.tgname),jsonb_build_array(pg_get_triggerdef(t.oid),t.tgenabled)
 from relations r join pg_trigger t on t.tgrelid=r.oid and not t.tgisinternal
 union all
 select 'POLICY:'||format('%I.%I.%I',r.nspname,r.relname,p.polname),jsonb_build_array(p.polcmd,p.polpermissive,
  array(select case when x=0 then 'PUBLIC' else pg_get_userbyid(x) end from unnest(p.polroles)x order by 1),
  pg_get_expr(p.polqual,p.polrelid),pg_get_expr(p.polwithcheck,p.polrelid))
 from relations r join pg_policy p on p.polrelid=r.oid
 union all
 select 'VIEW:'||format('%I.%I',nspname,relname),to_jsonb(pg_get_viewdef(oid,false)) from relations where relkind in('v','m')
 union all
 select 'SEQUENCE:'||format('%I.%I',r.nspname,r.relname),jsonb_build_array(format_type(s.seqtypid,null),s.seqstart,s.seqincrement,s.seqmax,s.seqmin,s.seqcache,s.seqcycle)
 from relations r join pg_sequence s on s.seqrelid=r.oid
 union all
 select 'SCHEMA:'||nspname,jsonb_build_array(pg_get_userbyid(nspowner),
  case when nspacl is null then null else array(select a::text from unnest(nspacl)a order by a::text) end)
 from pg_namespace where nspname in('erp','public')
 union all
 select 'DEFAULT_ACL:'||pg_get_userbyid(d.defaclrole)||':'||coalesce(n.nspname,'GLOBAL')||':'||d.defaclobjtype::text,
 to_jsonb(array(select a::text from unnest(d.defaclacl)a order by a::text))
 from pg_default_acl d left join pg_namespace n on n.oid=d.defaclnamespace
 where n.nspname in('erp','public') or d.defaclnamespace=0
 union all
 select 'ENUM:'||format('%I.%I',n.nspname,t.typname),jsonb_build_array(pg_get_userbyid(t.typowner),
  (select jsonb_agg(e.enumlabel order by e.enumsortorder) from pg_enum e where e.enumtypid=t.oid))
 from pg_type t join pg_namespace n on n.oid=t.typnamespace where n.nspname in('erp','public') and t.typtype='e'
)
select coalesce(jsonb_object_agg(k,encode(extensions.digest(convert_to(v::text,'UTF8'),'sha256'),'hex')),'{}'::jsonb) from objects
) catalog;
 select count(*),encode(extensions.digest(convert_to(coalesce(string_agg(length(key)::text||':'||key||':'||value,E'\n' order by key collate "C"),''),'UTF8'),'sha256'),'hex') into object_count,fingerprint from jsonb_each_text(actual);
 if object_count<>7198 or fingerprint is distinct from '1d844c41d8ef5b8c9aefbc1afe6dbd5a106d43e9a4457bcd873fcf035dcdbbf1' then
  raise exception 'AW_INSTALLED_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
commit;
