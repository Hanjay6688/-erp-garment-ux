-- CP6 T: document-cent material adjustment revaluation and canonical accounting day.
-- Forward-only successor; all published migrations and rollbacks through S stay immutable.
begin;
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;
lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.audit_logs,erp.journal_entries,erp.journal_lines,
  erp.account_daily_balances,erp.sales_headers,erp.sales_items,
  erp.sale_stock_allocations,erp.sales_returns,erp.sales_return_items,
  erp.sales_payments,erp.fg_lots,erp.fg_stock_movements,
  erp.fg_inventory_balances,erp.hpp_versions,erp.product_conversions,
  erp.product_conversion_allocations,erp.laundry_deliveries,
  erp.laundry_delivery_lines,erp.laundry_receipts,
  erp.laundry_failed_wash_attempts,erp.wip_stage_events,
  erp.cp6_v2620g_rollback_capsule,erp.cp6_v2620h_rollback_capsule,
  erp.cp6_v2620i_rollback_capsule,erp.sales_payment_posting_facts,
  erp.sales_payment_reversal_facts,erp.cp6_v2620j_rollback_capsule,
  erp.cp6_v2620k_rollback_capsule,erp.accounting_period_control,
  erp.accounting_account_mappings,erp.cash_accounts,erp.chart_accounts,
  erp.laundry_claims,erp.laundry_vendors,erp.cp6_v2620l_rollback_capsule,
  erp.opening_balance_headers,erp.opening_balance_items,
  erp.opening_subledger_balances,erp.opening_subledger_settlements,
  erp.opening_financial_corrections,erp.supplier_payments,
  erp.material_purchase_headers,erp.material_purchase_items,
  erp.material_supplier_invoices,erp.material_supplier_invoice_lines,
  erp.material_supplier_returns,erp.material_supplier_return_items,
  erp.material_purchase_cost_corrections,
  erp.material_purchase_cost_correction_items,erp.material_stock_movements,
  erp.material_rolls,erp.cost_recalc_queue,erp.cost_adjustments,
  erp.suppliers,erp.materials,erp.cp6_v2620m_rollback_capsule,
  erp.supplier_cent_posting_facts,erp.material_cost_history,
  erp.material_cost_revaluation_state,erp.material_cost_revaluation_events,
  erp.material_cost_checkpoints,erp.cp6_v2620n_rollback_capsule,
  erp.cp6_v2620o_rollback_capsule,erp.cp6_v2620p_rollback_capsule,erp.cp6_v2620q_rollback_capsule,erp.cp6_v2620r_rollback_capsule,erp.cp6_v2620s_rollback_capsule,
  erp.material_adjustments,erp.material_adjustment_items
in share row exclusive mode;

do $predecessor_v2620t$
declare r record;c record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20s')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20t')
     or to_regclass('erp.cp6_v2620t_rollback_capsule') is not null
     or to_regclass('erp.material_adjustment_revaluation_facts') is not null
     or to_regprocedure('erp._cp6_material_adjustment_revaluation_state(uuid)') is not null
     or to_regprocedure('erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)') is not null
     or to_regprocedure('erp.guard_material_adjustment_revaluation_fact_v2620t()') is not null then
    raise exception 'T_REQUIRES_EXACT_S_WITHOUT_T_RESIDUE';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20s_cp6_supplier_payment_business_date')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260912132445'
         and name='erp_v2_6_20s_cp6_supplier_payment_business_date'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('c9e35612100f0e387a7fdb80fda382ea1212df0cf5200ebceeaf67df9f77cf1f',
              'e0516a4533c76c416f6385cb07c33ab9ea9a7a50386fa818ac6c232fd5e21b7d'))
     or exists(select 1 from supabase_migrations.schema_migrations
       where version>'20260912132445')
     or (select count(*) from erp.cp6_v2620s_rollback_capsule)<>3 then
    raise exception 'T_PREDECESSOR_PLATFORM_OR_CAPSULE_MISMATCH';
  end if;
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()','8b3617725cd9061137dc55d6e2b5af75a87453929c93918b9e0acddea34f3cb2','2eb47603dcfefe58ea89e8f3cf832aca187f397d66b99bd7a4ab3bb5d6c428ad',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_supplier_payment(uuid)','231d2e8132d966e3b539015e3e9fc463e758c2e0bcfe4ecdb89414fc5c0b97f8','ad780c4b00261b6ee1890391cac1c459c23d06b041859399e6ccc2f73d67f421',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()','ce489ade327609230a40a0e804b1b67a9cecb11bb08a42bb470b9ba556183066','e5f4d8749851824e11bb7b76bb3614963aa26feca7034962f47cc198a7962e89',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620s_rollback_capsule
    where object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex')
            is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres'
       or c.acl_snapshot is distinct from r.acl
       or encode(extensions.digest(convert_to(
            pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
            is distinct from r.installed_sha256
       or (select pg_get_userbyid(proowner) from pg_proc
            where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
            from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'T_TRUSTED_S_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  -- Pin every additional replaced input and both inherited private dependencies.
  for r in select * from(values
    ('erp.resolve_accounting_transaction_date(date)','13fa7b70e1b723bb5d0f0f112f19ff9f7f928c587aef75b9ad4737e135b0a769',array['postgres=X/postgres']::text[]),
    ('erp.reverse_journal(uuid,text)','3ff7dec1176c79b58a981e5fdc68a3ce47908cfd5347cbd192d40022c9d7aee1',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_material_adjustment(uuid,text)','38800321130b33af3b127928b724f4e2b7b02342c62087a25536580c1eba8043',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.sync_material_cost_revaluation(uuid)','57b213f5b7adb8abc78eafd8639cbc1907fd49319027534166a10365cfb69b83',array['postgres=X/postgres']::text[]),
    ('erp._cp3_business_date(timestamp with time zone)','adf1fb87dd9f0b6a856bcb109b5118f9c4aac5da0ac32554ecbbc009f6d88248',array['postgres=X/postgres']::text[]),
    ('erp._cp6_supplier_cent_ledger(uuid[])','43572de7870afb9050d5af24a05ff6f5b91063d9a46de2cf6616f1f1edb0e49c',array['postgres=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    if encode(extensions.digest(convert_to(pg_get_functiondef(
        to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.sha256
       or (select pg_get_userbyid(proowner) from pg_proc
         where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
         from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'T_TRUSTED_S_INPUT_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  if not exists(select 1 from pg_class
      where oid='erp.supplier_cent_posting_facts'::regclass
        and relrowsecurity and relowner='postgres'::regrole)
     or exists(select 1 from information_schema.role_table_grants
       where table_schema='erp' and table_name='supplier_cent_posting_facts'
         and grantee in('PUBLIC','anon','authenticated','service_role')) then
    raise exception 'T_INHERITED_S_SECURITY_MISMATCH';
  end if;
  if exists(
    select 1 from erp.supplier_payments p
    join erp.journal_entries j on j.source_type='SUPPLIER_PAYMENT' and j.source_id=p.id
      and j.status in('POSTED','REVERSED')
    where p.status in('POSTED','REVERSED')
      and j.economic_date is distinct from erp._cp3_business_date(p.payment_date)
  ) then
    raise exception 'T_PREEXISTING_PAYMENT_DATE_REVIEW_REQUIRED';
  end if;
end
$predecessor_v2620t$;

create table erp.cp6_v2620t_rollback_capsule(
  like erp.cp6_v2620s_rollback_capsule including all
);
alter table erp.cp6_v2620t_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620t_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620t_rollback_capsule(
  object_identity,object_regidentity,object_definition,definition_sha256,
  acl_snapshot,owner_snapshot
)
select format('%I.%I(%s)',n.nspname,p.proname,
    pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  array(select a::text from unnest(p.proacl) a order by a::text),
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in(
  'erp._v268_financial_report_checks_pre_scope()'::regprocedure,
  'erp.resolve_accounting_transaction_date(date)'::regprocedure,
  'erp.reverse_journal(uuid,text)'::regprocedure,
  'erp.reverse_material_adjustment(uuid,text)'::regprocedure,
  'erp.run_v267_financial_truth_checks()'::regprocedure,
  'erp.sync_material_cost_revaluation(uuid)'::regprocedure
);

create table erp.material_adjustment_revaluation_facts(
 id uuid primary key,
 adjustment_id uuid not null references erp.material_adjustments(id),
 triggering_material_id uuid not null references erp.materials(id),
 effective_date date not null,
 prior_ledger jsonb not null,
 target_ledger jsonb not null,
 ledger_delta jsonb not null,
 journal_entry_id uuid not null unique references erp.journal_entries(id),
 created_at timestamptz not null default clock_timestamp()
);
create index material_adjustment_revaluation_facts_source_idx
 on erp.material_adjustment_revaluation_facts(adjustment_id);
alter table erp.material_adjustment_revaluation_facts enable row level security;
revoke all on erp.material_adjustment_revaluation_facts from public,anon,authenticated,service_role;

create function erp.guard_material_adjustment_revaluation_fact_v2620t()
returns trigger language plpgsql security definer set search_path=pg_catalog as $$
begin
 raise exception using errcode='42501',message='MATERIAL_ADJUSTMENT_REVALUATION_FACT_APPEND_ONLY';
end
$$;
revoke all on function erp.guard_material_adjustment_revaluation_fact_v2620t() from public,anon,authenticated,service_role;
create trigger trg_material_adjustment_revaluation_fact_append_only
 before update or delete on erp.material_adjustment_revaluation_facts
 for each row execute function erp.guard_material_adjustment_revaluation_fact_v2620t();
create trigger trg_material_adjustment_revaluation_fact_no_truncate
 before truncate on erp.material_adjustment_revaluation_facts
 for each statement execute function erp.guard_material_adjustment_revaluation_fact_v2620t();

create function erp._cp6_material_adjustment_revaluation_state(p_adjustment uuid)
returns jsonb language sql stable security definer set search_path=erp,pg_catalog,pg_temp as $$
 with movements as(
  select m.*,exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id) reversed
  from erp.material_stock_movements m join erp.material_adjustment_items i on i.id=m.source_id
  where m.source_type='MATERIAL_ADJUSTMENT_ITEM' and m.reversal_of_id is null
    and i.adjustment_id=p_adjustment
 ), amounts as(
  select round(coalesce(sum(qty_signed*unit_cost_snapshot) filter(where not reversed),0),2) current_value,
    round(coalesce(sum(qty_signed*coalesce(original_unit_cost_snapshot,unit_cost_snapshot)) filter(where not reversed),0),2) original_value,
    count(*) filter(where not reversed and unit_cost_snapshot is null) incomplete_cost
  from movements
 ), desired as(
  select erp.account_id(mapping) account_id,sum(amount) amount
  from amounts cross join lateral(values
   ('MATERIAL_INVENTORY',current_value-original_value),
   ('OTHER_EXPENSE',greatest(-current_value,0)-greatest(-original_value,0)),
   ('OTHER_INCOME',least(-current_value,0)-least(-original_value,0))
  ) values_by_account(mapping,amount)
  group by erp.account_id(mapping) having sum(amount)<>0
 ), originals as(
  select e.journal_entry_id from erp.material_cost_revaluation_events e
  join movements m on m.id=e.movement_id
  union
  select f.journal_entry_id from erp.material_adjustment_revaluation_facts f
  where f.adjustment_id=p_adjustment
 ), journals as(
  select journal_entry_id from originals
  union
  select j.id from erp.journal_entries j join originals o on j.reversal_of_id=o.journal_entry_id
 )
 select jsonb_build_object(
  'target',coalesce((select jsonb_object_agg(account_id::text,amount) from desired),'{}'::jsonb),
  'book',erp._cp6_supplier_cent_ledger((select array_agg(journal_entry_id) from journals)),
  'current_value',current_value,'original_value',original_value,'incomplete_cost',incomplete_cost
 ) from amounts
$$;
revoke all on function erp._cp6_material_adjustment_revaluation_state(uuid) from public,anon,authenticated,service_role;

create function erp._cp6_sync_material_adjustment_revaluation(p_adjustment uuid,p_material uuid)
returns void language plpgsql security definer set search_path=erp,pg_catalog,pg_temp as $$
declare s jsonb;v_delta jsonb;v_lines jsonb;v_event uuid;v_journal uuid;v_date date;
begin
 perform erp.require_internal();
 if not exists(select 1 from erp.material_adjustment_items where adjustment_id=p_adjustment and material_id=p_material) then
  raise exception 'T_MATERIAL_ADJUSTMENT_SOURCE_MISMATCH';
 end if;
 -- The material writer already owns its material/movement locks. Serialize the
 -- shared document without taking another material or document-row lock.
 perform pg_advisory_xact_lock(hashtextextended('MATERIAL_ADJUSTMENT_REVALUE|'||p_adjustment::text,0));
 s:=erp._cp6_material_adjustment_revaluation_state(p_adjustment);
 if (s->>'incomplete_cost')::bigint>0 then
  if exists(select 1 from erp.material_adjustments where id=p_adjustment and status in('POSTED','REVERSED')) then
   raise exception 'T_MATERIAL_ADJUSTMENT_COST_SNAPSHOT_MISSING';
  end if;
  return;
 end if;
 select coalesce(jsonb_object_agg(k,amount),'{}'::jsonb) into v_delta from(
  select coalesce(t.key,b.key) k,coalesce(t.value::numeric,0)-coalesce(b.value::numeric,0) amount
  from jsonb_each_text(s->'target') t full join jsonb_each_text(s->'book') b using(key)
 ) d where amount<>0;
 if v_delta='{}'::jsonb then return;end if;
 select jsonb_agg(jsonb_build_object('account_id',key::uuid,
  'debit',greatest(value::numeric,0),'credit',greatest(-value::numeric,0)) order by key)
 into v_lines from jsonb_each_text(v_delta);
 v_event:=gen_random_uuid();v_date:=erp._cp3_business_date(current_timestamp);
 v_journal:=erp.post_journal('MATERIAL_ADJUSTMENT_REVALUATION',v_event,v_date,
  'Document cumulative material adjustment recost: '||p_adjustment::text,v_lines);
 insert into erp.material_adjustment_revaluation_facts(
  id,adjustment_id,triggering_material_id,effective_date,prior_ledger,target_ledger,ledger_delta,journal_entry_id
 ) values(v_event,p_adjustment,p_material,v_date,s->'book',s->'target',v_delta,v_journal);
 if erp._cp6_supplier_cent_ledger(array[v_journal]) is distinct from v_delta
    or erp._cp6_material_adjustment_revaluation_state(p_adjustment)->'book' is distinct from s->'target' then
  raise exception 'T_MATERIAL_ADJUSTMENT_REVALUATION_POSTCONDITION';
 end if;
end
$$;
revoke all on function erp._cp6_sync_material_adjustment_revaluation(uuid,uuid) from public,anon,authenticated,service_role;

do $patch$
declare d text;anchor text;replacement text;
begin
 select pg_get_functiondef('erp.sync_material_cost_revaluation(uuid)'::regprocedure) into d;
 anchor:=$a$'CONTRACTOR_MATERIAL_ISSUE_ITEM','MATERIAL_ADJUSTMENT_ITEM','MATERIAL_SUPPLIER_RETURN_ITEM'$a$;
 replacement:=$r$'CONTRACTOR_MATERIAL_ISSUE_ITEM','MATERIAL_SUPPLIER_RETURN_ITEM'$r$;
 if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then raise exception 'T_REVALUATION_SOURCE_ANCHOR';end if;
 d:=replace(d,anchor,replacement);
 -- Remove the dead per-movement branch after routing adjustments by document.
 anchor:=$a$    elsif r.source_type='MATERIAL_ADJUSTMENT_ITEM' then
      v_counterpart:=case when r.qty_signed<0 then 'OTHER_EXPENSE' else 'OTHER_INCOME' end;
$a$;
 if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then raise exception 'T_REVALUATION_DEAD_BRANCH_ANCHOR';end if;
 d:=replace(d,anchor,'');
 anchor:=$a$  end loop;
end;$a$;
 replacement:=$r$  end loop;
  for r in select distinct i.adjustment_id
    from erp.material_adjustment_items i
    join erp.material_stock_movements m on m.source_type='MATERIAL_ADJUSTMENT_ITEM'
      and m.source_id=i.id and m.reversal_of_id is null
    where m.material_id=p_material_id order by i.adjustment_id
  loop
    perform erp._cp6_sync_material_adjustment_revaluation(r.adjustment_id,p_material_id);
  end loop;
end;$r$;
 if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then raise exception 'T_REVALUATION_DOCUMENT_HOOK_ANCHOR';end if;
 execute replace(d,anchor,replacement);
end
$patch$;

do $detector$
declare d text;anchor text;replacement text;
begin
 select pg_get_functiondef('erp.run_v267_financial_truth_checks()'::regprocedure) into d;
 anchor:=$a$  union all
  select 'V2620S_SUPPLIER_PAYMENT_BUSINESS_DATE'$a$;
 replacement:=$r$  union all
  select 'V2620T_JOURNAL_FUTURE_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Journal economic dates may not exceed the canonical Jakarta day of the recorded posting instant'
  from erp.journal_entries j
  where j.status in('POSTED','REVERSED')
    and j.economic_date>erp._cp3_business_date(j.posting_at)

  union all
  select 'V2620T_MATERIAL_ADJUSTMENT_REVALUATION','CRITICAL',count(*)::bigint,
    'Material adjustment revaluation must conserve document cents at original and corrected valuation endpoints'
  from erp.material_adjustments h
  cross join lateral(select erp._cp6_material_adjustment_revaluation_state(h.id) s) x
  where h.status in('POSTED','REVERSED')
    and (x.s->'target' is distinct from x.s->'book' or (x.s->>'incomplete_cost')::bigint>0)

  union all
  select 'V2620T_MATERIAL_ADJUSTMENT_FACT_LEDGER','CRITICAL',count(*)::bigint,
    'Append-only material adjustment revaluation facts must match their protected original journal'
  from erp.material_adjustment_revaluation_facts f
  left join erp.journal_entries j on j.id=f.journal_entry_id
  where j.id is null or j.status<>'POSTED' or j.source_type<>'MATERIAL_ADJUSTMENT_REVALUATION'
    or j.source_id is distinct from f.id or j.economic_date is distinct from f.effective_date
    or erp._cp6_supplier_cent_ledger(array[f.journal_entry_id]) is distinct from f.ledger_delta

  union all
  select 'V2620S_SUPPLIER_PAYMENT_BUSINESS_DATE'$r$;
 if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then raise exception 'T_REVALUATION_DETECTOR_ANCHOR';end if;
 execute replace(d,anchor,replacement);
 select pg_get_functiondef('erp._v268_financial_report_checks_pre_scope()'::regprocedure) into d;
 anchor:=$a$or r.check_name like 'V2620S_%'$a$;
 replacement:=$r$or r.check_name like 'V2620S_%' or r.check_name like 'V2620T_%'$r$;
 if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then raise exception 'T_REVALUATION_REPORT_SCOPE_ANCHOR';end if;
 execute replace(d,anchor,replacement);
end
$detector$;

do $calendar$
declare d text;anchor text:='current_date';
begin
 select pg_get_functiondef('erp.resolve_accounting_transaction_date(date)'::regprocedure) into d;
 if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>2 then raise exception 'T_CANONICAL_JOURNAL_DAY_ANCHOR';end if;
 execute replace(d,anchor,'erp._cp3_business_date(current_timestamp)');
end
$calendar$;

do $journal_guard$
declare d text;anchor text;replacement text;
begin
 select pg_get_functiondef('erp.reverse_journal(uuid,text)'::regprocedure) into d;
 anchor:=$a$  if v_source_type in ('ATTENDANCE_HPP_POOL','PAYROLL_ATTENDANCE_ACCRUAL') then$a$;
 replacement:=$r$  if v_source_type='MATERIAL_ADJUSTMENT_REVALUATION' then
    raise exception 'T_PROTECTED_REVALUATION_JOURNAL_USE_SOURCE_WORKFLOW';
  end if;
  if v_source_type in ('ATTENDANCE_HPP_POOL','PAYROLL_ATTENDANCE_ACCRUAL') then$r$;
 if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then raise exception 'T_REVALUATION_JOURNAL_GUARD_ANCHOR';end if;
 execute replace(d,anchor,replacement);
end
$journal_guard$;

do $zero_inverse$
declare d text;anchor text;replacement text;
begin
 select pg_get_functiondef('erp.reverse_material_adjustment(uuid,text)'::regprocedure) into d;
 anchor:=$a$and exists(select 1 from erp.material_stock_movements msm join erp.material_adjustment_items mai on mai.id=msm.source_id where mai.adjustment_id=h.id and msm.source_type='MATERIAL_ADJUSTMENT_ITEM' and abs(msm.qty_signed*msm.unit_cost_snapshot)>0.005)$a$;
 replacement:=$r$and coalesce((select round(sum(msm.qty_signed*coalesce(msm.original_unit_cost_snapshot,msm.unit_cost_snapshot)),2)
       from erp.material_stock_movements msm
       join erp.material_adjustment_items mai on mai.id=msm.source_id
       where mai.adjustment_id=h.id and msm.source_type='MATERIAL_ADJUSTMENT_ITEM'
         and msm.reversal_of_id is null),0)<>0$r$;
 if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then raise exception 'T_ZERO_NET_INVERSE_ANCHOR';end if;
 execute replace(d,anchor,replacement);
end
$zero_inverse$;

do $installed_v2620t$
declare r record;c record;v_count bigint;
begin
  if (select count(*) from erp.cp6_v2620t_rollback_capsule)<>6 then
    raise exception 'T_CAPSULE_CARDINALITY_MISMATCH';
  end if;
  update erp.cp6_v2620t_rollback_capsule cap set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(
      to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()','2eb47603dcfefe58ea89e8f3cf832aca187f397d66b99bd7a4ab3bb5d6c428ad','8e0e303066c23476223089e2705b8ad0861b34faa2efb12c58663677f454b196',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.resolve_accounting_transaction_date(date)','13fa7b70e1b723bb5d0f0f112f19ff9f7f928c587aef75b9ad4737e135b0a769','92e6c30c60bce3406178bd661ca5df2e5d12e17380fad2a8730be0c91d86bf48',array['postgres=X/postgres']::text[]),
    ('erp.reverse_journal(uuid,text)','3ff7dec1176c79b58a981e5fdc68a3ce47908cfd5347cbd192d40022c9d7aee1','a6f635cd2319a68a1afa522fa4682921a6f7b80afd0e31fbdc4271cf53fcfef4',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_material_adjustment(uuid,text)','38800321130b33af3b127928b724f4e2b7b02342c62087a25536580c1eba8043','c90fd34d4045a060ae4d36413d6520068281066d0de52dc766583c5f6e7d7288',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()','e5f4d8749851824e11bb7b76bb3614963aa26feca7034962f47cc198a7962e89','acd6f623c83f1ce74323a11b9224955ea922b10788ed631b9973aa9345698af8',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.sync_material_cost_revaluation(uuid)','57b213f5b7adb8abc78eafd8639cbc1907fd49319027534166a10365cfb69b83','3334800b5888000a4388dda4362ebd0db4c5f0dcdc0bbf3e41acfcf629d720f0',array['postgres=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620t_rollback_capsule
    where object_regidentity=r.identity;
    if c.object_regidentity is null or c.definition_sha256 is distinct from r.predecessor_sha256
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex')
            is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres' or c.acl_snapshot is distinct from r.acl
       or encode(extensions.digest(convert_to(pg_get_functiondef(
            to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.installed_sha256
       or (select pg_get_userbyid(proowner) from pg_proc
            where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
            from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'T_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  if exists(select 1 from erp.run_v267_financial_truth_checks()
      where check_name like 'V2620T_%' and issue_count>0) then
    raise exception 'T_PREEXISTING_ADJUSTMENT_OR_BUSINESS_DATE_REVIEW_REQUIRED';
  end if;
  if (select count(*) from erp.run_v268_financial_report_checks()
      where check_name in('V2620T_JOURNAL_FUTURE_BUSINESS_DATE',
       'V2620T_MATERIAL_ADJUSTMENT_REVALUATION','V2620T_MATERIAL_ADJUSTMENT_FACT_LEDGER')
       and severity='CRITICAL' and issue_count=0)<>3 then
    raise exception 'T_FINANCIAL_REPORT_SCOPE_NOT_CONNECTED';
  end if;
end
$installed_v2620t$;

do $t_extra_objects$
declare r record;
begin
  for r in select * from(values
    ('erp._cp6_material_adjustment_revaluation_state(uuid)','47a2c15955a682040d2c0c6b72f2941eaae8467e2b16fa5c4bbc10dff27a3c2e',array['postgres=X/postgres']::text[]),
    ('erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)','355246b52dc88e5d91643485fe796f24e7975d0629824c5b28c31074469ed7ba',array['postgres=X/postgres']::text[]),
    ('erp.guard_material_adjustment_revaluation_fact_v2620t()','c2cc7ddb076f557d0f71df9170b9d02425fc17c2f33e471bd1af48e61729829e',array['postgres=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    if encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
        is distinct from r.sha256
       or (select pg_get_userbyid(proowner) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'T_EXTRA_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  if not exists(select 1 from pg_class where oid=to_regclass('erp.material_adjustment_revaluation_facts')
       and relrowsecurity and relowner='postgres'::regrole)
     or exists(select 1 from information_schema.role_table_grants where table_schema='erp'
       and table_name='material_adjustment_revaluation_facts' and grantee in('PUBLIC','anon','authenticated','service_role'))
     or (select count(*) from pg_trigger where tgrelid=to_regclass('erp.material_adjustment_revaluation_facts')
       and not tgisinternal and tgenabled='O'
       and tgfoid=to_regprocedure('erp.guard_material_adjustment_revaluation_fact_v2620t()')
       and tgname in('trg_material_adjustment_revaluation_fact_append_only','trg_material_adjustment_revaluation_fact_no_truncate'))<>2 then
    raise exception 'T_ADJUSTMENT_FACT_SECURITY_MISMATCH';
  end if;
end
$t_extra_objects$;

do $boundary_v2620t$
declare v_table text;v_hash text;v_snapshot jsonb:='{}';
begin
  foreach v_table in array array[
    'app_users','idempotency_requests','products','audit_logs','journal_entries',
    'journal_lines','account_daily_balances','sales_headers','sales_items',
    'sale_stock_allocations','sales_returns','sales_return_items','sales_payments',
    'fg_lots','fg_stock_movements','fg_inventory_balances','hpp_versions',
    'product_conversions','product_conversion_allocations','laundry_deliveries',
    'laundry_delivery_lines','laundry_receipts','laundry_failed_wash_attempts',
    'wip_stage_events','cp6_v2620g_rollback_capsule','cp6_v2620h_rollback_capsule',
    'cp6_v2620i_rollback_capsule','sales_payment_posting_facts',
    'sales_payment_reversal_facts','cp6_v2620j_rollback_capsule',
    'cp6_v2620k_rollback_capsule','accounting_period_control',
    'accounting_account_mappings','cash_accounts','chart_accounts','laundry_claims',
    'laundry_vendors','cp6_v2620l_rollback_capsule','opening_balance_headers',
    'opening_balance_items','opening_subledger_balances','opening_subledger_settlements',
    'opening_financial_corrections','supplier_payments','material_purchase_headers',
    'material_purchase_items','material_supplier_invoices',
    'material_supplier_invoice_lines','material_supplier_returns',
    'material_supplier_return_items','material_purchase_cost_corrections',
    'material_purchase_cost_correction_items','material_stock_movements','material_rolls',
    'cost_recalc_queue','cost_adjustments','suppliers','materials',
    'cp6_v2620m_rollback_capsule','supplier_cent_posting_facts','material_cost_history',
    'material_cost_revaluation_state','material_cost_revaluation_events',
    'material_cost_checkpoints','cp6_v2620n_rollback_capsule',
    'cp6_v2620o_rollback_capsule','cp6_v2620p_rollback_capsule','cp6_v2620q_rollback_capsule','cp6_v2620r_rollback_capsule','cp6_v2620s_rollback_capsule','material_adjustments','material_adjustment_items','material_adjustment_revaluation_facts'
  ]::text[] loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  update erp.cp6_v2620t_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary_v2620t$;

insert into erp.schema_migrations(version,description)
values('v2.6.20t','Document-cent material adjustment recost, lawful net-zero inverse and canonical accounting admission day');
commit;
