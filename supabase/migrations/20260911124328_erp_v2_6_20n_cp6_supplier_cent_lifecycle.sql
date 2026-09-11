-- CP6 N: source-owned supplier cents across correction, invoice, return and inverse.
begin;
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;
lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.audit_logs,erp.journal_entries,erp.journal_lines,erp.account_daily_balances,erp.sales_headers,erp.sales_items,erp.sale_stock_allocations,erp.sales_returns,erp.sales_return_items,erp.sales_payments,erp.fg_lots,erp.fg_stock_movements,erp.fg_inventory_balances,erp.hpp_versions,erp.product_conversions,erp.product_conversion_allocations,erp.laundry_deliveries,erp.laundry_delivery_lines,erp.laundry_receipts,erp.laundry_failed_wash_attempts,erp.wip_stage_events,erp.cp6_v2620g_rollback_capsule,erp.cp6_v2620h_rollback_capsule,erp.cp6_v2620i_rollback_capsule,erp.sales_payment_posting_facts,erp.sales_payment_reversal_facts,erp.cp6_v2620j_rollback_capsule,erp.cp6_v2620k_rollback_capsule,erp.accounting_period_control,erp.accounting_account_mappings,erp.cash_accounts,erp.chart_accounts,erp.laundry_claims,erp.laundry_vendors,erp.cp6_v2620l_rollback_capsule,erp.opening_balance_headers,erp.opening_balance_items,erp.opening_subledger_balances,erp.opening_subledger_settlements,erp.opening_financial_corrections,erp.supplier_payments,erp.material_purchase_headers,erp.material_purchase_items,erp.material_supplier_invoices,erp.material_supplier_invoice_lines,erp.material_supplier_returns,erp.material_supplier_return_items,erp.material_purchase_cost_corrections,erp.material_purchase_cost_correction_items,erp.material_stock_movements,erp.material_rolls,erp.cost_recalc_queue,erp.cost_adjustments,erp.suppliers,erp.materials,erp.cp6_v2620m_rollback_capsule,erp.material_cost_history,erp.material_cost_revaluation_state,erp.material_cost_revaluation_events,erp.material_cost_checkpoints in share row exclusive mode;

do $predecessor$
declare r record;c record;
begin
 if not exists(select 1 from erp.schema_migrations where version='v2.6.20m') or exists(select 1 from erp.schema_migrations where version='v2.6.20n') or to_regclass('erp.cp6_v2620n_rollback_capsule') is not null or to_regclass('erp.supplier_cent_posting_facts') is not null then raise exception 'N_REQUIRES_EXACT_M';end if;
 if (select count(*) from erp.cp6_v2620m_rollback_capsule)<>15 or (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20m_cp6_subledger_exact_cent_closure')<>1 or not exists(select 1 from supabase_migrations.schema_migrations where version='20260911092622' and name='erp_v2_6_20m_cp6_subledger_exact_cent_closure' and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex') in('c5404de584a4734fb235f5253f10fb10a1d13f01f3f993b99150a422008e2268','b1e5014c656fc654ff9e1d79736420adacf062a67a26716951293a2dabb3451f')) or exists(select 1 from supabase_migrations.schema_migrations where version>'20260911092622') or exists(select 1 from erp.cp6_laundry_qc_execution_context) then raise exception 'N_PREDECESSOR_PLATFORM_CONTEXT_MISMATCH';end if;
 for r in select * from(values
('erp._v268_financial_report_checks_pre_scope()','dc4ed2384dda4b34a30093cad8cb13fa80db26201371569a88dbaee790a24108','98fac1a865982d5c60fc5e6a5caae9033755ff915b7e53d22213c0d1d1765ca1',array['postgres=X/postgres','service_role=X/postgres']::text[]),
('erp.post_material_purchase_cost_correction(uuid)','d80d5d357acddd562412ada1a27fced5ac979c0ab1aa1dc0a9cbefa81aee0ad8','9542acde669945e633d5929cb5b441a2119b8f3bf9a69919ae46725d598e8ba9',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
('erp.post_material_supplier_invoice(uuid)','ec73a81f2bae980039edde861f01157337814a3bb9a0554f9d0275716c1f19d5','65ae76bce50952c2ced64ad7ec25c1039a1e3086048e5ea39eae71ec4c8b7d69',array['postgres=X/postgres','service_role=X/postgres']::text[]),
('erp.post_material_supplier_return(uuid)','562140bee0171cb892501ca4499e93e8b6d661772d1d03c95271283e6cea8714','f5f6603b258eeda0b34a10f06a301b94c488525dfddfe0863e5ded8f56244ad1',array['postgres=X/postgres','service_role=X/postgres']::text[]),
('erp.post_opening_financial_correction(uuid,numeric,text,date)','41ef3e9b7e9be5432cd09db2e4cba4d303c6c7205c2dcf92cb052293dc4062a7','95ad1f5db523bdc19d7b21d1f1b9e1baa49a499fb791f937fe43b0291d4bd7f1',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
('erp.post_opening_subledger_settlement(uuid)','95eb1e84cd0dabd02b3f11dc8745f72997b56fea47c04a9f56a9e18e9a9ebdf2','c56b387a8593b19cd3b92e6dc20ac95459d2aedeb2b616b6fb1e4d812e729393',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
('erp.post_supplier_payment(uuid)','3d77b3cc0339606aa7eb456b9b341af33f8251a7a0415229a2d7c08cfe54ef60','231d2e8132d966e3b539015e3e9fc463e758c2e0bcfe4ecdb89414fc5c0b97f8',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
('erp.reverse_material_purchase_cost_correction(uuid,text)','2cbfb722a7b644d47886e23555ef8dcffb2ea2060525c6251afa43e52689389b','dc17e41110f001f6f16d18d065745dc8e85bb9e58ef28e162522976da45c4a6f',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
('erp.reverse_material_supplier_invoice(uuid,text)','c269a2cb171184f49be2720e195bd24292f76d0127cb752ffc158a894768d1cb','76ee31ad50c747b5a9f5730a5a3e81ba79c1685f57f716ac211197f11aa7080e',array['postgres=X/postgres','service_role=X/postgres']::text[]),
('erp.reverse_material_supplier_return(uuid,text)','570bb23aeebdf5f309e34a84071a247ff201855b6c283f8a6264b7389816eaa6','ac2504b1f04d5eaf8bf63b13ce945adf17fda0104ac6e4f6c44ac831c255706b',array['postgres=X/postgres','service_role=X/postgres']::text[]),
('erp.reverse_opening_financial_correction(uuid,text)','5d794a5d6d4d63b2bc5e4b6407523488d1b87ba5c47ab557056fd566442ec50c','1ce99785ee8dc682b1b0f2aa9171f2110614baf4c9a99ecf4880b547496947fe',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
('erp.reverse_opening_subledger_settlement(uuid,text)','d5c1e4b368a13de3738d458c89584ec181149f6f070cc697111c61e56bfba07e','c01292aebb98ea09d0fb440215f9c4cdbd9ece3b98caa641b9b308faec542e1a',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
('erp.reverse_supplier_payment(uuid,text)','b6518df0cc3941554eca06016e483e8e020112778db67dad69202d4c032d40be','9733b0e39d82732fb4b2ec7be17c66bcff2a088a81cccd25892eb440d4923102',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
('erp.run_v267_financial_truth_checks()','368c7f97b895ce7d08aa6b5fa5a77b50957191465a44e26ef9268b6424c93aea','efde954275e89f01793f405e2b000c6c599bae0be731869802f288994dd154fa',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
('erp.run_v268_financial_report_checks()','2bffd2d8f33ad2d918d1fb2f767676dc403ac777ad9a8ff69d4f32bf74067eff','48d60613970b015d1afb30a2f8a7cec0e5d56d1f692c6a1acfa0ffd48684fda1',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
 ) expected(identity,predecessor_sha256,installed_sha256,acl) loop
 select * into c from erp.cp6_v2620m_rollback_capsule where object_regidentity=r.identity;
 if c.object_regidentity is null or c.definition_sha256 is distinct from r.predecessor_sha256 or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex') is distinct from r.predecessor_sha256 or c.installed_definition_sha256 is distinct from r.installed_sha256 or c.owner_snapshot is distinct from 'postgres' or c.acl_snapshot is distinct from r.acl or encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.installed_sha256 or (select pg_get_userbyid(proowner) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from 'postgres' or (select array(select a::text from unnest(proacl) a order by a::text) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then raise exception 'N_PREDECESSOR_M_CAPSULE_MISMATCH';end if;
 end loop;
 if exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='erp' and p.proname in('_cp6_supplier_cent_state','_cp6_supplier_cent_ledger','_cp6_apply_supplier_cent_event')) then raise exception 'N_EXTRA_FUNCTION_RESIDUE';end if;
end
$predecessor$;
create table erp.cp6_v2620n_rollback_capsule(like erp.cp6_v2620m_rollback_capsule including all);
alter table erp.cp6_v2620n_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620n_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620n_rollback_capsule(object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),p.oid::regprocedure::text,pg_get_functiondef(p.oid),encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),array(select a::text from unnest(proacl) a order by a::text),pg_get_userbyid(p.proowner) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where p.oid in('erp.post_material_purchase_cost_correction(uuid)'::regprocedure,'erp.post_material_supplier_invoice(uuid)'::regprocedure,'erp.post_material_supplier_return(uuid)'::regprocedure,'erp.reverse_material_purchase_cost_correction(uuid,text)'::regprocedure,'erp.reverse_material_supplier_invoice(uuid,text)'::regprocedure,'erp.reverse_material_supplier_return(uuid,text)'::regprocedure,'erp.run_v267_financial_truth_checks()'::regprocedure);
create table erp.supplier_cent_posting_facts(
 source_type text not null check(source_type in('MATERIAL_PURCHASE_COST_CORRECTION','MATERIAL_SUPPLIER_INVOICE','MATERIAL_SUPPLIER_RETURN')),
 source_id uuid not null,
 phase text not null check(phase in('POST','REVERSE')),
 before_state jsonb not null,
 after_state jsonb not null,
 ledger_delta jsonb not null,
 journal_entry_id uuid references erp.journal_entries(id),
 adjustment_journal_entry_id uuid references erp.journal_entries(id),
 legacy_original boolean not null default false,
 recorded_at timestamptz not null default clock_timestamp(),
 primary key(source_type,source_id,phase),
 check(phase='REVERSE' or adjustment_journal_entry_id is null)
);
alter table erp.supplier_cent_posting_facts enable row level security;
revoke all on erp.supplier_cent_posting_facts from public,anon,authenticated,service_role;
create trigger trg_supplier_cent_fact_append_only before update or delete
on erp.supplier_cent_posting_facts for each row execute function erp.guard_sales_payment_fact_append_only();
create trigger trg_supplier_cent_fact_no_truncate before truncate
on erp.supplier_cent_posting_facts for each statement execute function erp.guard_sales_payment_fact_append_only();

create function erp._cp6_supplier_cent_state(p_purchases uuid[])
returns jsonb language sql stable security definer set search_path='erp','pg_catalog','pg_temp'
as $function$
 select coalesce(jsonb_object_agg(h.id::text,jsonb_build_object(
  'ap',round(erp.material_purchase_final_ap_total(h.id),2),
  'grni',round(erp.material_purchase_grni_total(h.id),2),
  'inventory',round(coalesce((select sum(i.qty*erp.material_purchase_current_unit_cost(i.id))
    from erp.material_purchase_items i where i.purchase_id=h.id),0)
   -coalesce((select sum(-m.qty_signed*coalesce(m.original_unit_cost_snapshot,m.unit_cost_snapshot))
    from erp.material_supplier_return_items ri
    join erp.material_supplier_returns r on r.id=ri.return_id and r.status='POSTED'
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    join erp.material_stock_movements m on m.source_type='MATERIAL_SUPPLIER_RETURN_ITEM'
      and m.source_id=ri.id and m.movement_type='SUPPLIER_RETURN'
    where i.purchase_id=h.id),0),2))), '{}')
 from erp.material_purchase_headers h where h.id=any(p_purchases) and h.status='POSTED'
$function$;
revoke all on function erp._cp6_supplier_cent_state(uuid[]) from public,anon,authenticated,service_role;

create function erp._cp6_supplier_cent_ledger(p_journals uuid[])
returns jsonb language sql stable security definer set search_path='erp','pg_catalog','pg_temp'
as $function$
 select coalesce(jsonb_object_agg(account_id::text,amount),'{}') from(
  select l.account_id,sum(l.debit-l.credit) amount
  from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
  where j.id=any(p_journals) and j.status in('POSTED','REVERSED')
  group by l.account_id having sum(l.debit-l.credit)<>0
 ) net
$function$;
revoke all on function erp._cp6_supplier_cent_ledger(uuid[]) from public,anon,authenticated,service_role;

create function erp._cp6_apply_supplier_cent_event(p_source text,p_id uuid,p_date date,
 p_description text,p_before jsonb,p_reverse boolean default false)
returns void language plpgsql security definer set search_path='erp','pg_catalog','pg_temp'
as $function$
declare
 v_purchases uuid[];v_after jsonb;v_ap numeric;v_grni numeric;v_inventory numeric;
 v_expected jsonb;v_adjust jsonb;v_lines jsonb;v_original uuid;v_journal uuid;v_adjustment uuid;
 v_fact erp.supplier_cent_posting_facts%rowtype;v_status text;v_phase text;
begin
 perform erp.require_internal();
 v_phase:=case when p_reverse then 'REVERSE' else 'POST' end;
 if p_source='MATERIAL_PURCHASE_COST_CORRECTION' then
  select array[h.purchase_id],h.status into v_purchases,v_status from erp.material_purchase_cost_corrections h where h.id=p_id;
 elsif p_source='MATERIAL_SUPPLIER_INVOICE' then
  select array_agg(distinct i.purchase_id order by i.purchase_id),h.status into v_purchases,v_status
  from erp.material_supplier_invoices h join erp.material_supplier_invoice_lines l on l.invoice_id=h.id
  join erp.material_purchase_items i on i.id=l.purchase_item_id where h.id=p_id group by h.status;
 elsif p_source='MATERIAL_SUPPLIER_RETURN' then
  select array_agg(distinct i.purchase_id order by i.purchase_id),h.status into v_purchases,v_status
  from erp.material_supplier_returns h join erp.material_supplier_return_items l on l.return_id=h.id
  join erp.material_purchase_items i on i.id=l.purchase_item_id where h.id=p_id group by h.status;
 else raise exception 'N_UNSUPPORTED_SUPPLIER_CENT_SOURCE';end if;
 if v_status is distinct from (case when p_reverse then 'REVERSED' else 'POSTED' end)
   or v_purchases is null or jsonb_typeof(p_before) is distinct from 'object'
   or (select array_agg(key::uuid order by key::uuid) from jsonb_object_keys(p_before) key) is distinct from v_purchases then
  raise exception 'N_SUPPLIER_CENT_SOURCE_STATE_MISMATCH';end if;
 v_after:=erp._cp6_supplier_cent_state(v_purchases);
 if (select count(*) from jsonb_object_keys(v_after))<>cardinality(v_purchases) then
  raise exception 'N_SUPPLIER_CENT_PURCHASE_STATE_MISMATCH';end if;
 select sum((a.value->>'ap')::numeric-(b.value->>'ap')::numeric),
  sum((a.value->>'grni')::numeric-(b.value->>'grni')::numeric),
  sum((a.value->>'inventory')::numeric-(b.value->>'inventory')::numeric)
 into v_ap,v_grni,v_inventory
 from jsonb_each(v_after) a join jsonb_each(p_before) b using(key);
 if v_ap::text in('NaN','Infinity','-Infinity') or v_grni::text in('NaN','Infinity','-Infinity')
   or v_inventory::text in('NaN','Infinity','-Infinity') then raise exception 'N_NONFINITE_SUPPLIER_CENT_DELTA';end if;
 select coalesce(jsonb_object_agg(account_id::text,amount),'{}') into v_expected from(
  select erp.account_id(mapping) account_id,sum(amount) amount from(values
   ('AP_SUPPLIER',-v_ap),('GRNI_MATERIAL',-v_grni),
   ('MATERIAL_INVENTORY',v_inventory),('MATERIAL_PURCHASE_VARIANCE',v_ap+v_grni-v_inventory)
  ) d(mapping,amount) group by erp.account_id(mapping) having sum(amount)<>0
 ) net;
 v_adjust:=v_expected;
 if p_reverse then
  select * into v_fact from erp.supplier_cent_posting_facts
  where source_type=p_source and source_id=p_id and phase='POST' for update;
  select id into v_original from erp.journal_entries where source_type=p_source and source_id=p_id and status='POSTED';
  if v_fact.source_id is not null and (v_original is distinct from v_fact.journal_entry_id
    or erp._cp6_supplier_cent_ledger(array[v_original]) is distinct from v_fact.ledger_delta) then
   raise exception 'N_SUPPLIER_CENT_ORIGINAL_JOURNAL_DRIFT';end if;
  if v_original is not null then
   v_journal:=erp.reverse_journal(v_original,p_description);
   select coalesce(jsonb_object_agg(k,amount),'{}') into v_adjust from(
    select coalesce(e.key,a.key) k,coalesce(e.value::numeric,0)-coalesce(a.value::numeric,0) amount
    from jsonb_each_text(v_expected) e full join jsonb_each_text(erp._cp6_supplier_cent_ledger(array[v_journal])) a using(key)
   ) d where amount<>0;
  end if;
 end if;
 select coalesce(jsonb_agg(jsonb_build_object('account_id',key::uuid,
  'debit',greatest(value::numeric,0),'credit',greatest(-value::numeric,0)) order by key),'[]')
 into v_lines from jsonb_each_text(v_adjust);
 if jsonb_array_length(v_lines)>0 then
  if p_reverse then
   v_adjustment:=erp.post_journal('CENT_INVERSE:'||p_source,p_id,
    coalesce((select economic_date from erp.journal_entries where id=v_journal),current_date),
    'Linked cumulative-cent adjustment: '||p_description,v_lines);
  else
   v_journal:=erp.post_journal(p_source,p_id,p_date,p_description,v_lines);
  end if;
 end if;
 insert into erp.supplier_cent_posting_facts(source_type,source_id,phase,before_state,after_state,
  ledger_delta,journal_entry_id,adjustment_journal_entry_id,legacy_original)
 values(p_source,p_id,v_phase,p_before,v_after,v_expected,v_journal,v_adjustment,p_reverse and v_fact.source_id is null);
 if erp._cp6_supplier_cent_ledger(array[v_journal,v_adjustment]) is distinct from v_expected then
  raise exception 'N_SUPPLIER_CENT_POSTCONDITION_FAILED';end if;
end;
$function$;
revoke all on function erp._cp6_apply_supplier_cent_event(text,uuid,date,text,jsonb,boolean) from public,anon,authenticated,service_role;

CREATE OR REPLACE FUNCTION erp.post_material_purchase_cost_correction(p_correction_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_n_before jsonb;v_n_purchases uuid[];
  h erp.material_purchase_cost_corrections%rowtype;
  p erp.material_purchase_headers%rowtype;
  m record;
  r record;
  v_delta_payable numeric(24,6);
  v_old_cost numeric(18,6);
  v_current_payable numeric(24,6);
  v_proposed_payable numeric(24,6);
  v_paid numeric(24,6);
  v_post_seq bigint;
begin
  perform erp.require_owner_admin();
  select * into h from erp.material_purchase_cost_corrections where id=p_correction_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Material purchase cost correction must be DRAFT'; end if;
  select * into p from erp.material_purchase_headers where id=h.purchase_id for update;
  if p.id is null or p.status<>'POSTED' then raise exception 'Source material purchase must be POSTED'; end if;
  v_n_purchases:=array[p.id];v_n_before:=erp._cp6_supplier_cent_state(v_n_purchases);
  if not exists(select 1 from erp.material_purchase_cost_correction_items where correction_id=h.id) then raise exception 'Cost correction has no lines'; end if;

  select coalesce(max(c.post_seq),0)+1 into v_post_seq
  from erp.material_purchase_cost_corrections c
  where c.purchase_id=p.id and c.post_seq is not null;

  select erp.material_purchase_payable_total(p.id) into v_current_payable;
  select coalesce(sum(mpi.qty*(ci.new_unit_price-erp.material_purchase_current_unit_cost(mpi.id))),0)
  into v_delta_payable
  from erp.material_purchase_cost_correction_items ci
  join erp.material_purchase_items mpi on mpi.id=ci.purchase_item_id
  where ci.correction_id=h.id;
  v_proposed_payable:=v_current_payable+v_delta_payable;
  select coalesce(sum(sp.amount),0) into v_paid from erp.supplier_payments sp where sp.purchase_id=p.id and sp.status='POSTED';
  if round(v_proposed_payable,2)<0 then raise exception 'Corrected purchase payable cannot become negative'; end if;
  if v_paid>round(v_proposed_payable,2) then raise exception 'Cost correction would make supplier payments exceed corrected payable. Use supplier credit/receivable correction flow'; end if;

  for m in
    select distinct mpi.material_id
    from erp.material_purchase_cost_correction_items ci join erp.material_purchase_items mpi on mpi.id=ci.purchase_item_id
    where ci.correction_id=h.id
  loop
    for r in
      select ci.id as correction_item_id,ci.purchase_item_id,ci.new_unit_price,mpi.qty,mpi.material_id
      from erp.material_purchase_cost_correction_items ci
      join erp.material_purchase_items mpi on mpi.id=ci.purchase_item_id
      where ci.correction_id=h.id and mpi.material_id=m.material_id
      order by ci.id
    loop
      v_old_cost:=erp.material_purchase_current_unit_cost(r.purchase_item_id);
      update erp.material_purchase_cost_correction_items
      set old_unit_cost_snapshot=v_old_cost,qty_basis=r.qty,delta_amount=r.qty*(r.new_unit_price-v_old_cost)
      where id=r.correction_item_id;
      update erp.material_stock_movements msm
      set input_unit_cost=r.new_unit_price
      where msm.movement_type='PURCHASE' and msm.qty_signed>0 and (
        (msm.source_type='MATERIAL_PURCHASE_ITEM' and msm.source_id=r.purchase_item_id)
        or (msm.source_type='MATERIAL_PURCHASE_ROLL' and msm.source_id in(select mr.id from erp.material_rolls mr where mr.purchase_item_id=r.purchase_item_id))
      );
      if not found then raise exception 'Original purchase stock movement not found for purchase item %',r.purchase_item_id; end if;
    end loop;

    perform erp.recalculate_material_cost(m.material_id,p.physical_at);

  end loop;

  update erp.material_purchase_cost_corrections
  set status='POSTED',posted_at=clock_timestamp(),post_seq=v_post_seq
  where id=h.id;
  select erp.material_purchase_payable_total(p.id) into v_proposed_payable;
  select coalesce(sum(sp.amount),0) into v_paid from erp.supplier_payments sp where sp.purchase_id=p.id and sp.status='POSTED';
  update erp.material_purchase_headers set payment_status=case when v_paid=round(v_proposed_payable,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end where id=p.id;
  perform erp._cp6_apply_supplier_cent_event('MATERIAL_PURCHASE_COST_CORRECTION',h.id,h.invoice_date,'Supplier document cents '||h.id::text,v_n_before,false);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_material_supplier_invoice(p_invoice_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_n_before jsonb;v_n_purchases uuid[];
  h erp.material_supplier_invoices%rowtype;
  r record;
  v_capacity numeric;
  v_matched numeric;
  v_old_cost numeric;
  v_new_cost numeric;
  v_basis_qty numeric;
  v_delta_before numeric;
  v_delta_after numeric;
  v_inventory_delta numeric;
  v_liability_delta numeric;
  v_bridge numeric;
  v_purchase uuid;
  v_paid numeric;
  v_payable numeric;
begin
  perform erp.require_owner_admin();
  select * into h from erp.material_supplier_invoices where id=p_invoice_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Material supplier invoice must be DRAFT'; end if;
  if h.invoice_date>current_date then raise exception 'Supplier invoice date cannot be in the future'; end if;
  if h.received_at::date>current_date then raise exception 'Supplier invoice received_at cannot be in the future'; end if;
  if not exists(select 1 from erp.material_supplier_invoice_lines where invoice_id=h.id) then
    raise exception 'Material supplier invoice has no lines';
  end if;

  -- Deterministic lock order protects concurrent invoice/payment/return clicks.
  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id order by i.purchase_id
  loop
    perform 1 from erp.material_purchase_headers where id=v_purchase for update;
  end loop;
  select array_agg(distinct i.purchase_id order by i.purchase_id) into v_n_purchases
  from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.invoice_id=h.id;
  perform 1 from erp.material_purchase_headers where id=any(v_n_purchases) order by id for update;
  v_n_before:=erp._cp6_supplier_cent_state(v_n_purchases);
  for r in
    select distinct i.id
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id order by i.id
  loop
    perform 1 from erp.material_purchase_items where id=r.id for update;
  end loop;

  for r in
    select l.*,i.qty as receipt_qty,i.unit_price as estimate_unit_cost,
           i.material_id,i.purchase_id,i.invoice_match_state,
           ph.supplier_id,ph.physical_at
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    join erp.material_purchase_headers ph on ph.id=i.purchase_id
    where l.invoice_id=h.id order by i.id
  loop
    if r.supplier_id is distinct from h.supplier_id then
      raise exception 'Invoice supplier does not match receipt supplier for item %',r.purchase_item_id;
    end if;
    if r.invoice_match_state='DIRECT_FINAL' then
      raise exception 'Receipt item % was already final-invoiced at physical receipt',r.purchase_item_id;
    end if;
    v_capacity:=erp.material_purchase_invoice_capacity(r.purchase_item_id);
    v_matched:=erp.material_purchase_posted_invoice_qty(r.purchase_item_id);
    if v_matched+r.qty_invoiced>v_capacity+0.000001 then
      raise exception 'Invoice quantity exceeds unmatched receipt quantity for item %. Capacity %, already matched %, requested %',
        r.purchase_item_id,v_capacity,v_matched,r.qty_invoiced;
    end if;

    v_old_cost:=erp.material_purchase_current_unit_cost(r.purchase_item_id);
    v_basis_qty:=v_capacity;
    select coalesce(sum(x.net_amount-(x.qty_invoiced*r.estimate_unit_cost)),0)
    into v_delta_before
    from erp.material_supplier_invoice_lines x
    join erp.material_supplier_invoices xh on xh.id=x.invoice_id
    where x.purchase_item_id=r.purchase_item_id and xh.status='POSTED';
    v_delta_after:=v_delta_before+(r.net_amount-(r.qty_invoiced*r.estimate_unit_cost));
    v_new_cost:=greatest(((v_basis_qty*r.estimate_unit_cost)+v_delta_after)/v_basis_qty,0);
    v_inventory_delta:=r.receipt_qty*(v_new_cost-v_old_cost);
    v_liability_delta:=r.net_amount-(r.qty_invoiced*r.estimate_unit_cost);
    v_bridge:=v_inventory_delta-v_liability_delta;

    update erp.material_supplier_invoice_lines
    set receipt_estimate_unit_cost_snapshot=r.estimate_unit_cost,
        prior_blended_unit_cost_snapshot=v_old_cost,
        posted_blended_unit_cost_snapshot=v_new_cost,
        grni_clear_amount_snapshot=r.qty_invoiced*r.estimate_unit_cost,
        ap_create_amount_snapshot=r.net_amount,
        inventory_revaluation_snapshot=v_inventory_delta,
        bridge_variance_snapshot=v_bridge
    where id=r.id;

  end loop;

  update erp.material_supplier_invoices
  set status='POSTED',posted_at=clock_timestamp(),posting_reason=coalesce(posting_reason,'Supplier invoice posted')
  where id=h.id;

  for r in
    select distinct l.purchase_item_id
    from erp.material_supplier_invoice_lines l
    where l.invoice_id=h.id order by l.purchase_item_id
  loop
    perform erp.refresh_material_purchase_item_cost(r.purchase_item_id);
    perform erp.refresh_material_purchase_item_match_state(r.purchase_item_id);
  end loop;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id order by i.purchase_id
  loop
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0)
    into v_payable,v_paid;
    update erp.material_purchase_headers
    set supplier_invoice_number=h.invoice_number,
        due_date=coalesce(h.due_date,due_date),
        payment_status=case when v_paid=round(v_payable,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end
    where id=v_purchase;
  end loop;
  perform erp._cp6_apply_supplier_cent_event('MATERIAL_SUPPLIER_INVOICE',h.id,h.invoice_date,'Supplier document cents '||h.id::text,v_n_before,false);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_material_supplier_return(p_return_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_n_before jsonb;v_n_purchases uuid[];
  h erp.material_supplier_returns%rowtype;
  r record;
  v_purchase uuid;
  v_invoiced_qty numeric;
  v_prior_ap_qty numeric;
  v_ap_qty numeric;
  v_grni_qty numeric;
  v_paid numeric;
  v_payable numeric;
  v_proposed_relief numeric;
begin
  perform erp.require_internal();
  select * into h from erp.material_supplier_returns where id=p_return_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Supplier return must be DRAFT'; end if;
  if h.location_id is null then raise exception 'Supplier return location is required'; end if;
  if not exists(select 1 from erp.material_supplier_return_items where return_id=h.id) then
    raise exception 'Supplier return has no lines';
  end if;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id order by i.purchase_id
  loop
    perform 1 from erp.material_purchase_headers where id=v_purchase for update;
  end loop;

  select array_agg(distinct i.purchase_id order by i.purchase_id) into v_n_purchases
  from erp.material_supplier_return_items l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.return_id=h.id;
  perform 1 from erp.material_purchase_headers where id=any(v_n_purchases) order by id for update;
  v_n_before:=erp._cp6_supplier_cent_state(v_n_purchases);
  -- Allocate each physical return against already-final AP first; any remaining
  -- quantity cancels the receipt estimate in GRNI. These snapshots are immutable
  -- once the document posts and make reversal deterministic.
  for r in
    select ri.*,i.qty as receipt_qty,i.unit_price as estimate_unit_cost,
           i.invoice_match_state,i.purchase_id
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id order by i.id,ri.id
  loop
    perform 1 from erp.material_purchase_items where id=r.purchase_item_id for update;
    v_invoiced_qty:=case when r.invoice_match_state='DIRECT_FINAL'
      then r.receipt_qty else erp.material_purchase_posted_invoice_qty(r.purchase_item_id) end;
    select coalesce(sum(coalesce(x.ap_relief_qty_snapshot,0)),0)
    into v_prior_ap_qty
    from erp.material_supplier_return_items x
    join erp.material_supplier_returns xh on xh.id=x.return_id
    where x.purchase_item_id=r.purchase_item_id and xh.status='POSTED';
    v_ap_qty:=least(r.qty,greatest(v_invoiced_qty-v_prior_ap_qty,0));
    v_grni_qty:=r.qty-v_ap_qty;
    update erp.material_supplier_return_items
    set ap_relief_qty_snapshot=v_ap_qty,
        grni_relief_qty_snapshot=v_grni_qty,
        ap_relief_amount_snapshot=v_ap_qty*r.supplier_credit_unit_price,
        grni_relief_amount_snapshot=v_grni_qty*r.estimate_unit_cost
    where id=r.id;
  end loop;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id order by i.purchase_id
  loop
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0),
           coalesce(sum(ri.ap_relief_amount_snapshot),0)
    into v_payable,v_paid,v_proposed_relief
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id and i.purchase_id=v_purchase;
    if v_paid>round(v_payable-v_proposed_relief,2) then
      raise exception 'Supplier return would make payment % exceed projected final AP %. Reverse/correct supplier payment first.',
        v_paid,v_payable-v_proposed_relief;
    end if;
  end loop;

  update erp.material_supplier_returns set status='POSTED' where id=h.id;

  for r in
    select ri.*
    from erp.material_supplier_return_items ri
    where ri.return_id=h.id order by ri.material_id,ri.id
  loop
    insert into erp.material_stock_movements(
      material_id,roll_id,location_id,movement_type,qty_signed,
      source_type,source_id,physical_at,created_by,note
    ) values(
      r.material_id,r.roll_id,h.location_id,'SUPPLIER_RETURN',-r.qty,
      'MATERIAL_SUPPLIER_RETURN_ITEM',r.id,h.physical_at,erp.current_app_user_id(),h.reason
    );

    -- GRNI-backed returns reduce the cost-basis quantity. Recompute the source
    -- purchase layer before replaying chronological MA.
    perform erp.refresh_material_purchase_item_cost(r.purchase_item_id);
    if r.roll_id is not null then
      update erp.material_rolls
      set status=case when cached_qty=0 then 'RETURNED_SUPPLIER' else status end,updated_at=now()
      where id=r.roll_id;
    end if;
  end loop;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id order by i.purchase_id
  loop
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0)
    into v_payable,v_paid;
    update erp.material_purchase_headers
    set payment_status=case when v_paid=round(v_payable,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end
    where id=v_purchase;
  end loop;
  perform erp._cp6_apply_supplier_cent_event('MATERIAL_SUPPLIER_RETURN',h.id,erp._cp3_business_date(h.physical_at),'Supplier document cents '||h.id::text,v_n_before,false);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_material_purchase_cost_correction(p_correction_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_n_before jsonb;v_n_purchases uuid[];
  h erp.material_purchase_cost_corrections%rowtype;
  p erp.material_purchase_headers%rowtype;
  r record;
  m uuid;
  v_journal uuid;
  v_current_payable numeric(24,6);
  v_delta numeric(24,6);
  v_projected numeric(24,6);
  v_paid numeric(24,6);
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal koreksi harga pembelian wajib diisi'; end if;
  select * into h from erp.material_purchase_cost_corrections where id=p_correction_id for update;
  if h.id is null then raise exception 'Koreksi harga pembelian tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya koreksi harga pembelian POSTED yang dapat direverse'; end if;
  if h.post_seq is null then raise exception 'Urutan posting koreksi harga pembelian tidak ditemukan; reversal dibatalkan'; end if;
  select * into p from erp.material_purchase_headers where id=h.purchase_id for update;
  if p.id is null or p.status<>'POSTED' then raise exception 'Pembelian sumber harus masih POSTED'; end if;
  v_n_purchases:=array[p.id];v_n_before:=erp._cp6_supplier_cent_state(v_n_purchases);

  if exists(
    select 1
    from erp.material_purchase_cost_correction_items ci
    join erp.material_purchase_cost_correction_items ci2 on ci2.purchase_item_id=ci.purchase_item_id
    join erp.material_purchase_cost_corrections c2 on c2.id=ci2.correction_id
    where ci.correction_id=h.id and c2.status='POSTED' and c2.id<>h.id
      and c2.post_seq>h.post_seq
  ) then
    raise exception 'Ada koreksi harga yang lebih baru pada item pembelian ini. Reverse koreksi terbaru terlebih dahulu.';
  end if;

  select erp.material_purchase_payable_total(p.id) into v_current_payable;
  select coalesce(sum(delta_amount),0) into v_delta
  from erp.material_purchase_cost_correction_items where correction_id=h.id;
  v_projected:=v_current_payable-v_delta;
  select coalesce(sum(amount),0) into v_paid from erp.supplier_payments where purchase_id=p.id and status='POSTED';
  if v_paid>round(v_projected,2) then
    raise exception 'Reversal koreksi harga membuat pembayaran supplier melebihi hutang tersisa. Reverse/koreksi pembayaran supplier terlebih dahulu.';
  end if;

  for r in
    select ci.*,mpi.material_id
    from erp.material_purchase_cost_correction_items ci
    join erp.material_purchase_items mpi on mpi.id=ci.purchase_item_id
    where ci.correction_id=h.id order by ci.id
  loop
    if r.old_unit_cost_snapshot is null then
      raise exception 'Snapshot harga sebelum koreksi tidak ditemukan untuk item %; reversal dibatalkan',r.purchase_item_id;
    end if;
    update erp.material_stock_movements msm
    set input_unit_cost=r.old_unit_cost_snapshot
    where msm.movement_type='PURCHASE' and msm.qty_signed>0 and (
      (msm.source_type='MATERIAL_PURCHASE_ITEM' and msm.source_id=r.purchase_item_id)
      or (msm.source_type='MATERIAL_PURCHASE_ROLL' and msm.source_id in (select mr.id from erp.material_rolls mr where mr.purchase_item_id=r.purchase_item_id))
    );
  end loop;

  update erp.material_purchase_cost_corrections set status='REVERSED' where id=h.id;
  for m in
    select distinct mpi.material_id from erp.material_purchase_cost_correction_items ci
    join erp.material_purchase_items mpi on mpi.id=ci.purchase_item_id where ci.correction_id=h.id
  loop
    perform erp.recalculate_material_cost(m,p.physical_at);
  end loop;

  select id into v_journal from erp.journal_entries
  where source_type='MATERIAL_PURCHASE_COST_CORRECTION' and source_id=h.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if abs(v_delta)>0.005 and v_journal is null and not exists(select 1 from erp.supplier_cent_posting_facts where source_type='MATERIAL_PURCHASE_COST_CORRECTION' and source_id=h.id and phase='POST') then
    raise exception 'Jurnal koreksi harga pembelian tidak ditemukan; reversal dibatalkan agar inventory/AP tidak rusak';
  end if;


  select erp.material_purchase_payable_total(p.id) into v_projected;
  select coalesce(sum(amount),0) into v_paid from erp.supplier_payments where purchase_id=p.id and status='POSTED';
  update erp.material_purchase_headers set payment_status=case when v_paid=round(v_projected,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end where id=p.id;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('material_purchase_cost_corrections',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
  perform erp._cp6_apply_supplier_cent_event('MATERIAL_PURCHASE_COST_CORRECTION',h.id,h.invoice_date,p_reason,v_n_before,true);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_material_supplier_invoice(p_invoice_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_n_before jsonb;v_n_purchases uuid[];
  h erp.material_supplier_invoices%rowtype;
  r record;
  v_purchase uuid;
  v_current_ap numeric;
  v_invoice_ap numeric;
  v_paid numeric;
  v_journal uuid;
  v_latest record;
begin
  perform erp.require_owner_admin();
  if nullif(btrim(p_reason),'') is null then raise exception 'Supplier invoice reversal reason is required'; end if;
  select * into h from erp.material_supplier_invoices where id=p_invoice_id for update;
  if h.id is null then raise exception 'Material supplier invoice not found'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Only a POSTED supplier invoice may be reversed'; end if;

  select array_agg(distinct i.purchase_id order by i.purchase_id) into v_n_purchases
  from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.invoice_id=h.id;
  perform 1 from erp.material_purchase_headers where id=any(v_n_purchases) order by id for update;
  v_n_before:=erp._cp6_supplier_cent_state(v_n_purchases);
  if exists(
    select 1
    from erp.material_supplier_invoice_lines l
    join erp.material_supplier_return_items ri on ri.purchase_item_id=l.purchase_item_id
    join erp.material_supplier_returns rh on rh.id=ri.return_id
    where l.invoice_id=h.id and rh.status='POSTED'
      and coalesce(ri.ap_relief_qty_snapshot,0)>0
  ) then
    raise exception 'Reverse AP-backed supplier returns before reversing this invoice';
  end if;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id order by i.purchase_id
  loop
    perform 1 from erp.material_purchase_headers where id=v_purchase for update;
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce(sum(l.net_amount),0),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0)
    into v_current_ap,v_invoice_ap,v_paid
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id and i.purchase_id=v_purchase;
    if v_paid>round(v_current_ap-v_invoice_ap,2) then
      raise exception 'Reverse supplier payments first: payment % would exceed projected final AP %',
        v_paid,v_current_ap-v_invoice_ap;
    end if;
  end loop;

  select id into v_journal from erp.journal_entries
  where source_type='MATERIAL_SUPPLIER_INVOICE' and source_id=h.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if exists(
    select 1 from erp.material_supplier_invoice_lines
    where invoice_id=h.id and(
      coalesce(grni_clear_amount_snapshot,0)<>0
      or coalesce(ap_create_amount_snapshot,0)<>0
      or coalesce(inventory_revaluation_snapshot,0)<>0
    )
  ) and v_journal is null and not exists(select 1 from erp.supplier_cent_posting_facts where source_type='MATERIAL_SUPPLIER_INVOICE' and source_id=h.id and phase='POST') then
    raise exception 'Supplier invoice journal is missing; reversal aborted to protect AP/GRNI/HPP';
  end if;

  update erp.material_supplier_invoices
  set status='REVERSED',reversed_at=clock_timestamp(),reversal_reason=btrim(p_reason)
  where id=h.id;


  for r in
    select distinct l.purchase_item_id
    from erp.material_supplier_invoice_lines l
    where l.invoice_id=h.id order by l.purchase_item_id
  loop
    perform erp.refresh_material_purchase_item_cost(r.purchase_item_id);
    perform erp.refresh_material_purchase_item_match_state(r.purchase_item_id);
  end loop;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id order by i.purchase_id
  loop
    select ih.invoice_number,ih.due_date into v_latest
    from erp.material_supplier_invoices ih
    join erp.material_supplier_invoice_lines il on il.invoice_id=ih.id
    join erp.material_purchase_items pi on pi.id=il.purchase_item_id
    where pi.purchase_id=v_purchase and ih.status='POSTED'
    order by ih.posted_at desc,ih.id desc limit 1;
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0)
    into v_current_ap,v_paid;
    update erp.material_purchase_headers
    set supplier_invoice_number=v_latest.invoice_number,
        due_date=v_latest.due_date,
        payment_status=case when v_paid=round(v_current_ap,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end
    where id=v_purchase;
  end loop;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('material_supplier_invoices',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
  perform erp._cp6_apply_supplier_cent_event('MATERIAL_SUPPLIER_INVOICE',h.id,h.invoice_date,p_reason,v_n_before,true);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_material_supplier_return(p_return_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_n_before jsonb;v_n_purchases uuid[];
  h erp.material_supplier_returns%rowtype;
  r record;
  v_journal uuid;
  v_purchase uuid;
  v_payable numeric;
  v_paid numeric;
  v_roll_qty numeric;
  v_cost numeric;
begin
  perform erp.require_owner_admin();
  if nullif(btrim(p_reason),'') is null then raise exception 'Alasan reversal retur supplier wajib diisi'; end if;
  select * into h from erp.material_supplier_returns where id=p_return_id for update;
  if h.id is null then raise exception 'Retur supplier tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya retur supplier POSTED yang dapat direverse'; end if;

  perform erp.lock_supplier_return_source_purchases(h.id);  select array_agg(distinct i.purchase_id order by i.purchase_id) into v_n_purchases
  from erp.material_supplier_return_items l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.return_id=h.id;
  perform 1 from erp.material_purchase_headers where id=any(v_n_purchases) order by id for update;
  v_n_before:=erp._cp6_supplier_cent_state(v_n_purchases);

  select id into v_journal from erp.journal_entries
  where source_type='MATERIAL_SUPPLIER_RETURN' and source_id=h.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if exists(
    select 1 from erp.material_supplier_return_items
    where return_id=h.id and(
      coalesce(ap_relief_amount_snapshot,0)<>0
      or coalesce(grni_relief_amount_snapshot,0)<>0
    )
  ) and v_journal is null and not exists(select 1 from erp.supplier_cent_posting_facts where source_type='MATERIAL_SUPPLIER_RETURN' and source_id=h.id and phase='POST') then
    raise exception 'Jurnal retur supplier tidak ditemukan; reversal dibatalkan agar stok/AP/GRNI tidak rusak';
  end if;

  update erp.material_supplier_returns set status='REVERSED',updated_at=now() where id=h.id;

  -- Recalculate the purchase source input before reverse_material_movement runs,
  -- so its single chronological replay sees the restored GRNI cost-basis.
  for r in
    select distinct ri.purchase_item_id,i.material_id
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id order by ri.purchase_item_id
  loop
    v_cost:=erp.material_purchase_current_unit_cost(r.purchase_item_id);
    update erp.material_stock_movements msm
    set input_unit_cost=v_cost
    where msm.movement_type='PURCHASE' and msm.qty_signed>0 and(
      (msm.source_type='MATERIAL_PURCHASE_ITEM' and msm.source_id=r.purchase_item_id)
      or
      (msm.source_type='MATERIAL_PURCHASE_ROLL' and msm.source_id in(
        select mr.id from erp.material_rolls mr where mr.purchase_item_id=r.purchase_item_id
      ))
    );
  end loop;

  for r in
    select msm.id,ri.roll_id,ri.purchase_item_id
    from erp.material_stock_movements msm
    join erp.material_supplier_return_items ri on ri.id=msm.source_id
    where ri.return_id=h.id
      and msm.source_type='MATERIAL_SUPPLIER_RETURN_ITEM'
      and msm.movement_type='SUPPLIER_RETURN'
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id)
    order by msm.physical_at desc,msm.id desc
  loop
    perform erp.reverse_material_movement(r.id,p_reason);
    perform erp.refresh_material_purchase_item_match_state(r.purchase_item_id);
    if r.roll_id is not null then
      select coalesce(sum(qty_signed),0) into v_roll_qty
      from erp.material_stock_movements where roll_id=r.roll_id;
      update erp.material_rolls
      set cached_qty=v_roll_qty,
          status=case when v_roll_qty<=0 then 'EXHAUSTED'
                      when v_roll_qty<original_qty then 'HALF_USED' else 'AVAILABLE' end,
          updated_at=now()
      where id=r.roll_id;
    end if;
  end loop;


  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id order by i.purchase_id
  loop
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0)
    into v_payable,v_paid;
    update erp.material_purchase_headers
    set payment_status=case when v_paid=round(v_payable,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end
    where id=v_purchase;
  end loop;
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('material_supplier_returns',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
  perform erp._cp6_apply_supplier_cent_event('MATERIAL_SUPPLIER_RETURN',h.id,erp._cp3_business_date(h.physical_at),p_reason,v_n_before,true);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.run_v267_financial_truth_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_catalog', 'information_schema', 'pg_temp'
AS $function$
  select 'V267_GRNI_MAPPING_INVALID','CRITICAL',count(*)::bigint,
         'GRNI_MATERIAL must map to an active CREDIT liability account'
  from erp.accounting_account_mappings m
  join erp.chart_accounts a on a.id=m.account_id
  where m.mapping_key='GRNI_MATERIAL'
    and not(a.account_type='LIABILITY' and a.normal_balance='CREDIT' and a.is_active and a.is_postable)

  union all
  select 'V267_MISSING_GRNI_MAPPING','CRITICAL',case when exists(
    select 1 from erp.accounting_account_mappings where mapping_key='GRNI_MATERIAL'
  ) then 0 else 1 end::bigint,'GRNI mapping is required'

  union all
  select 'V267_ESTIMATED_RECEIPT_MISSING_GRNI_RECLASS','CRITICAL',count(*)::bigint,
         'Posted estimated receipts require an AP-to-GRNI reclassification journal'
  from erp.material_purchase_headers h
  where h.status='POSTED' and erp.material_purchase_grni_total(h.id)>0.005
    and not exists(
      select 1 from erp.journal_entries j
      where j.source_type='MATERIAL_PURCHASE_GRNI_RECLASS' and j.source_id=h.id
        and j.status in('POSTED','REVERSED')
    )

  union all
  select 'V267_POSTED_INVOICE_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
         'Every non-zero posted supplier invoice requires an AP/GRNI journal'
  from erp.material_supplier_invoices h
  where h.status='POSTED'
    and exists(select 1 from erp.material_supplier_invoice_lines l where l.invoice_id=h.id and(l.net_amount<>0 or l.grni_clear_amount_snapshot<>0))
    and not exists(
      select 1 from erp.journal_entries j
      where j.source_type='MATERIAL_SUPPLIER_INVOICE' and j.source_id=h.id and j.status='POSTED'
    )

  union all
  select 'V267_INVOICE_MATCH_OVER_RECEIPT','CRITICAL',count(*)::bigint,
         'Posted supplier-invoice quantity exceeds receipt quantity net of GRNI-backed returns'
  from erp.material_purchase_items i
  where erp.material_purchase_posted_invoice_qty(i.id)>erp.material_purchase_invoice_capacity(i.id)+0.000001

  union all
  select 'V267_PAYMENT_EXCEEDS_FINAL_AP','CRITICAL',count(*)::bigint,
         'Supplier payment must never consume GRNI or exceed final AP'
  from erp.material_purchase_headers h
  where coalesce((select sum(p.amount) from erp.supplier_payments p where p.purchase_id=h.id and p.status='POSTED'),0)
        >round(erp.material_purchase_final_ap_total(h.id),2)

  union all
  select 'V267_LEGACY_CORRECTION_ON_GRNI','CRITICAL',count(*)::bigint,
         'Legacy price corrections may only touch DIRECT_FINAL receipt items'
  from erp.material_purchase_cost_correction_items ci
  join erp.material_purchase_cost_corrections c on c.id=ci.correction_id
  join erp.material_purchase_items i on i.id=ci.purchase_item_id
  where c.status='POSTED' and i.invoice_match_state<>'DIRECT_FINAL'

  union all
  select 'V267_POSTED_RETURN_MISSING_LIABILITY_SNAPSHOT','CRITICAL',count(*)::bigint,
         'Posted supplier returns require AP/GRNI quantity and amount snapshots'
  from erp.material_supplier_return_items ri
  join erp.material_supplier_returns rh on rh.id=ri.return_id
  where rh.status='POSTED' and(
    ri.ap_relief_qty_snapshot is null or ri.grni_relief_qty_snapshot is null
    or ri.ap_relief_amount_snapshot is null or ri.grni_relief_amount_snapshot is null
  )

  union all
  select 'V267_GRNI_GL_SUBLEDGER_MISMATCH','CRITICAL',case when abs(
    coalesce((select sum(a.credit_total-a.debit_total)
      from erp.account_daily_balances a
      where a.account_id=erp.account_id('GRNI_MATERIAL')),0)
    -coalesce((select sum(round(erp.material_purchase_grni_total(h.id),2))
      from erp.material_purchase_headers h where h.status='POSTED'),0)
  )<>0 then 1 else 0 end::bigint,
  'GRNI general ledger must equal estimated unmatched receipt liability'

  union all
  select 'V267_AP_GL_SUBLEDGER_MISMATCH','CRITICAL',case when abs(
    coalesce((select sum(a.credit_total-a.debit_total)
      from erp.account_daily_balances a
      where a.account_id=erp.account_id('AP_SUPPLIER')),0)
    -coalesce((select sum(greatest(
      round(erp.material_purchase_final_ap_total(h.id),2)
      -coalesce((select sum(p.amount) from erp.supplier_payments p where p.purchase_id=h.id and p.status='POSTED'),0),0
    )) from erp.material_purchase_headers h where h.status='POSTED'),0)
    -coalesce((select sum(b.original_amount-b.settled_amount)
      from erp.opening_subledger_balances b
      join erp.opening_balance_items i on i.id=b.opening_item_id
      join erp.opening_balance_headers oh on oh.id=i.opening_id and oh.status='POSTED'
      where b.party_type='SUPPLIER' and b.direction='PAYABLE'),0)
  )<>0 then 1 else 0 end::bigint,
  'Supplier AP general ledger must equal final-invoice subledger net of payment/returns'

  union all
  select 'V267_BROWSER_ROLE_DIRECT_INVOICE_WRITE','CRITICAL',count(*)::bigint,
         'Supplier invoice aggregate must be writable only through v2 RPCs'
  from information_schema.role_table_grants g
  where g.table_schema='erp' and g.table_name in('material_supplier_invoices','material_supplier_invoice_lines')
    and g.grantee in('PUBLIC','anon','authenticated')
    and g.privilege_type in('INSERT','UPDATE','DELETE')
  union all
  select 'V2620M_SUPPLIER_PAYMENT_EXACT_STATUS','CRITICAL',count(*)::bigint,
    'Supplier payment status and capacity must equal the rounded final liability of each purchase'
  from erp.material_purchase_headers h
  cross join lateral(select round(erp.material_purchase_final_ap_total(h.id),2) payable,
    coalesce((select sum(p.amount) from erp.supplier_payments p
      where p.purchase_id=h.id and p.status='POSTED'),0) paid) x
  where h.status='POSTED' and(
    x.paid<0 or x.paid>x.payable
    or x.paid::text in('NaN','Infinity','-Infinity')
    or x.payable::text in('NaN','Infinity','-Infinity')
    or(h.payment_status='PAID' and x.paid<>x.payable)
    or(h.payment_status='PARTIAL' and not(x.paid>0 and x.paid<x.payable))
    or(h.payment_status='UNPAID' and x.paid<>0))

  union all
  select 'V2620M_OPENING_SUBLEDGER_STATE','CRITICAL',count(*)::bigint,
    'Every posted financial opening requires one source-matched balance, exact settlements, and exact status'
  from erp.opening_balance_items i
  join erp.opening_balance_headers h on h.id=i.opening_id and h.status='POSTED'
  left join erp.opening_subledger_balances b on b.opening_item_id=i.id
  cross join lateral(select coalesce((select c.corrected_amount
      from erp.opening_financial_corrections c where c.opening_item_id=i.id and c.status='POSTED'
      order by c.correction_seq desc limit 1),i.amount) original,
    coalesce((select sum(s.amount) from erp.opening_subledger_settlements s
      where s.balance_id=b.id and s.status='POSTED'),0) paid) x
  where i.balance_type in('CUSTOMER_RECEIVABLE','SUPPLIER_PAYABLE','VENDOR_PAYABLE',
    'CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE') and(
    b.id is null or (select count(*) from erp.opening_subledger_balances bx where bx.opening_item_id=i.id)<>1
    or b.original_amount is distinct from x.original
    or b.settled_amount is distinct from x.paid
    or b.original_amount::text in('NaN','Infinity','-Infinity')
    or b.settled_amount::text in('NaN','Infinity','-Infinity')
    or b.original_amount<0 or b.settled_amount<0 or b.settled_amount>b.original_amount
    or b.status is distinct from case when x.paid=x.original then 'SETTLED'
      when x.paid>0 then 'PARTIAL' else 'OPEN' end
    or b.party_type is distinct from split_part(i.balance_type,'_',1)
    or b.direction is distinct from split_part(i.balance_type,'_',2)
    or b.customer_id is distinct from i.customer_id
    or b.supplier_id is distinct from i.supplier_id
    or b.vendor_id is distinct from i.vendor_id
    or b.contractor_id is distinct from i.contractor_id)

  union all
  select 'V2620M_PAYMENT_SOURCE_JOURNAL_MISMATCH','CRITICAL',count(*)::bigint,
    'Each supplier or opening settlement must match its own original and inverse money, accounts, party, and lifecycle'
  from(
    select p.id,p.status,p.amount,p.cash_account_id,'SUPPLIER_PAYMENT'::text source_type,
      erp.account_id('AP_SUPPLIER') balance_account,false incoming,
      null::uuid customer_id,null::uuid vendor_id,null::uuid contractor_id
    from erp.supplier_payments p
    union all
    select s.id,s.status,s.amount,s.cash_account_id,'OPENING_SUBLEDGER_SETTLEMENT',
      erp.account_id(case when b.party_type='CUSTOMER' then 'AR_CUSTOMER'
        when b.party_type='SUPPLIER' then 'AP_SUPPLIER'
        when b.party_type='VENDOR' then 'AP_VENDOR'
        when b.direction='RECEIVABLE' then 'CONTRACTOR_RECEIVABLE' else 'CONTRACTOR_PAYABLE' end),
      b.direction='RECEIVABLE',b.customer_id,b.vendor_id,b.contractor_id
    from erp.opening_subledger_settlements s
    join erp.opening_subledger_balances b on b.id=s.balance_id
  ) x
  left join erp.cash_accounts ca on ca.id=x.cash_account_id
  where x.amount<=0 or x.amount::text in('NaN','Infinity','-Infinity') or ca.id is null
    or (select count(*) from erp.journal_entries j
      where j.source_type=x.source_type and j.source_id=x.id and j.status in('POSTED','REVERSED'))
      <>case when x.status='DRAFT' then 0 else 1 end
    or exists(
      select 1 from erp.journal_entries j
      where j.source_type=x.source_type and j.source_id=x.id and j.status in('POSTED','REVERSED') and(
        j.status is distinct from x.status
        or (select count(*) from erp.journal_lines l where l.journal_entry_id=j.id)<>2
        or exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and(
          l.customer_id is distinct from x.customer_id or l.vendor_id is distinct from x.vendor_id
          or l.contractor_id is distinct from x.contractor_id
          or not((l.account_id=ca.coa_account_id and
                l.debit=case when x.incoming then x.amount else 0 end and
                l.credit=case when x.incoming then 0 else x.amount end)
            or (l.account_id=x.balance_account and
                l.debit=case when x.incoming then 0 else x.amount end and
                l.credit=case when x.incoming then x.amount else 0 end))))
        or (select count(*) from erp.journal_entries inv where inv.reversal_of_id=j.id)
          <>case when x.status='REVERSED' then 1 else 0 end
        or exists(select 1 from erp.journal_entries inv where inv.reversal_of_id=j.id and(
          inv.source_type<>'JOURNAL_REVERSAL' or inv.status<>'POSTED'
          or (select count(*) from erp.journal_lines l where l.journal_entry_id=inv.id)<>2
          or exists(select 1 from erp.journal_lines l where l.journal_entry_id=inv.id and(
            l.customer_id is distinct from x.customer_id or l.vendor_id is distinct from x.vendor_id
            or l.contractor_id is distinct from x.contractor_id
            or not((l.account_id=ca.coa_account_id and
                  l.credit=case when x.incoming then x.amount else 0 end and
                  l.debit=case when x.incoming then 0 else x.amount end)
              or (l.account_id=x.balance_account and
                  l.credit=case when x.incoming then 0 else x.amount end and
                  l.debit=case when x.incoming then x.amount else 0 end))))))
      ))

  union all
  select 'V2620M_ORPHAN_PAYMENT_JOURNAL','CRITICAL',count(*)::bigint,
    'A supplier payment or opening settlement journal must retain its business source'
  from erp.journal_entries j
  where j.status in('POSTED','REVERSED') and(
    (j.source_type='SUPPLIER_PAYMENT' and not exists(select 1 from erp.supplier_payments p where p.id=j.source_id))
    or(j.source_type='OPENING_SUBLEDGER_SETTLEMENT' and not exists(
      select 1 from erp.opening_subledger_settlements s where s.id=j.source_id)))

  union all
  select 'V2620N_SUPPLIER_CENT_FACT_LEDGER','CRITICAL',count(*)::bigint,
    'Supplier cent posting and linked inverse must retain their exact source and ledger vector'
  from erp.supplier_cent_posting_facts f
  where f.ledger_delta is distinct from erp._cp6_supplier_cent_ledger(array[f.journal_entry_id,f.adjustment_journal_entry_id])
    or(f.phase='POST' and f.adjustment_journal_entry_id is not null)
    or not exists(select 1 from(
      select 'MATERIAL_PURCHASE_COST_CORRECTION'::text source_type,id,status from erp.material_purchase_cost_corrections
      union all select 'MATERIAL_SUPPLIER_INVOICE',id,status from erp.material_supplier_invoices
      union all select 'MATERIAL_SUPPLIER_RETURN',id,status from erp.material_supplier_returns
    ) s where s.source_type=f.source_type and s.id=f.source_id
      and s.status=case when exists(select 1 from erp.supplier_cent_posting_facts r
        where r.source_type=f.source_type and r.source_id=f.source_id and r.phase='REVERSE') then 'REVERSED' else 'POSTED' end)
    or(f.journal_entry_id is not null and not exists(select 1 from erp.journal_entries j
      where j.id=f.journal_entry_id and(
        (f.phase='POST' and j.source_type=f.source_type and j.source_id=f.source_id)
        or(f.phase='REVERSE' and j.source_type='JOURNAL_REVERSAL' and exists(select 1
          from erp.journal_entries original where original.id=j.reversal_of_id
            and original.source_type=f.source_type and original.source_id=f.source_id)))))
    or(f.adjustment_journal_entry_id is not null and not exists(select 1 from erp.journal_entries j
      where j.id=f.adjustment_journal_entry_id and j.source_type='CENT_INVERSE:'||f.source_type
        and j.source_id=f.source_id))
;

$function$;

do $installed$
declare r record;
begin
 if (select count(*) from erp.cp6_v2620n_rollback_capsule)<>7 then raise exception 'N_CAPSULE_CARDINALITY_MISMATCH';end if;
 for r in select * from(values
('erp.post_material_purchase_cost_correction(uuid)','9542acde669945e633d5929cb5b441a2119b8f3bf9a69919ae46725d598e8ba9','5839dee0ab9db69ebabf5f08894b5c6603c851c1d55aa9eff30a12dd0331dff9',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
('erp.post_material_supplier_invoice(uuid)','65ae76bce50952c2ced64ad7ec25c1039a1e3086048e5ea39eae71ec4c8b7d69','da4ce12c6f41625933511e6fd59246c2410b80ce02ddf865c489803070f7b8b0',array['postgres=X/postgres','service_role=X/postgres']::text[]),
('erp.post_material_supplier_return(uuid)','f5f6603b258eeda0b34a10f06a301b94c488525dfddfe0863e5ded8f56244ad1','b4ac34b5df0e35f0cf1afe85d4a92e0b369922f91d0ce9eb4e2589a71367d607',array['postgres=X/postgres','service_role=X/postgres']::text[]),
('erp.reverse_material_purchase_cost_correction(uuid,text)','dc17e41110f001f6f16d18d065745dc8e85bb9e58ef28e162522976da45c4a6f','9913ee82901495aa850712c29d21ab8a8b96a5d71c29fca20fb0844b1af1dddd',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
('erp.reverse_material_supplier_invoice(uuid,text)','76ee31ad50c747b5a9f5730a5a3e81ba79c1685f57f716ac211197f11aa7080e','b4b10a9021e4360a25327656217fac0ed8a171748c215af2291ed00539684cb2',array['postgres=X/postgres','service_role=X/postgres']::text[]),
('erp.reverse_material_supplier_return(uuid,text)','ac2504b1f04d5eaf8bf63b13ce945adf17fda0104ac6e4f6c44ac831c255706b','5659d9755c81ae4134a494d1ebd0aaaec29ed82b75a5a32bdfd6d048e6ebaca3',array['postgres=X/postgres','service_role=X/postgres']::text[]),
('erp.run_v267_financial_truth_checks()','efde954275e89f01793f405e2b000c6c599bae0be731869802f288994dd154fa','f50decac0d38f9ddc2cfc5a28af53607fb8c1cf38cde5a65f13b38ec748a6fda',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
 ) expected(identity,predecessor_sha256,installed_sha256,acl) loop
 if encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.installed_sha256 or (select pg_get_userbyid(proowner) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from 'postgres' or (select array(select a::text from unnest(proacl) a order by a::text) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then raise exception 'N_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH';end if;
 end loop;
 for r in select * from(values
('erp._cp6_apply_supplier_cent_event(text,uuid,date,text,jsonb,boolean)','390fc3fae9bf59cf35fbc699f988521b3bde572e266937fdce99e0854c1756a3',array['postgres=X/postgres']::text[]),
('erp._cp6_supplier_cent_ledger(uuid[])','43572de7870afb9050d5af24a05ff6f5b91063d9a46de2cf6616f1f1edb0e49c',array['postgres=X/postgres']::text[]),
('erp._cp6_supplier_cent_state(uuid[])','19d43e3e32d94c6aaaf0acbb1f6e55946701fa10b9f53df7a990ea9375fad191',array['postgres=X/postgres']::text[])) expected(identity,installed_sha256,acl) loop
 if encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.installed_sha256 or (select pg_get_userbyid(proowner) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from 'postgres' or (select array(select a::text from unnest(proacl) a order by a::text) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then raise exception 'N_EXTRA_FUNCTION_OWNER_ACL_MISMATCH';end if;
end loop;
if not exists(select 1 from pg_class where oid='erp.supplier_cent_posting_facts'::regclass and relrowsecurity and relowner='postgres'::regrole) or exists(select 1 from information_schema.role_table_grants where table_schema='erp' and table_name='supplier_cent_posting_facts' and grantee in('PUBLIC','anon','authenticated','service_role')) or (select count(*) from pg_trigger where tgrelid='erp.supplier_cent_posting_facts'::regclass and not tgisinternal and tgenabled='O' and tgfoid='erp.guard_sales_payment_fact_append_only()'::regprocedure and tgname in('trg_supplier_cent_fact_append_only','trg_supplier_cent_fact_no_truncate'))<>2 then raise exception 'N_CENT_FACT_SECURITY_MISMATCH';end if;
if encode(extensions.digest(convert_to(pg_get_functiondef('erp.guard_sales_payment_fact_append_only()'::regprocedure),'UTF8'),'sha256'),'hex') is distinct from '2011da553bc46c6106ba4c638c0f695da4bb2c1855bd1518b42df8215cf81cf5' or (select pg_get_userbyid(proowner) from pg_proc where oid='erp.guard_sales_payment_fact_append_only()'::regprocedure) is distinct from 'postgres' or (select array(select a::text from unnest(proacl) a order by a::text) from pg_proc where oid='erp.guard_sales_payment_fact_append_only()'::regprocedure) is distinct from array['postgres=X/postgres']::text[] then raise exception 'N_INHERITED_FACT_GUARD_MISMATCH';end if;

 if exists(select 1 from erp.run_v267_financial_truth_checks() where issue_count<>0 and severity='CRITICAL') then raise exception 'N_PREEXISTING_SUPPLIER_REVIEW_REQUIRED';end if;
 update erp.cp6_v2620n_rollback_capsule c set installed_definition_sha256=encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'),'sha256'),'hex');
end
$installed$;
do $boundary$
declare v_table text;v_hash text;v_snapshot jsonb:='{}';
begin
 foreach v_table in array array['app_users','idempotency_requests','products','audit_logs','journal_entries','journal_lines','account_daily_balances','sales_headers','sales_items','sale_stock_allocations','sales_returns','sales_return_items','sales_payments','fg_lots','fg_stock_movements','fg_inventory_balances','hpp_versions','product_conversions','product_conversion_allocations','laundry_deliveries','laundry_delivery_lines','laundry_receipts','laundry_failed_wash_attempts','wip_stage_events','cp6_v2620g_rollback_capsule','cp6_v2620h_rollback_capsule','cp6_v2620i_rollback_capsule','sales_payment_posting_facts','sales_payment_reversal_facts','cp6_v2620j_rollback_capsule','cp6_v2620k_rollback_capsule','accounting_period_control','accounting_account_mappings','cash_accounts','chart_accounts','laundry_claims','laundry_vendors','cp6_v2620l_rollback_capsule','opening_balance_headers','opening_balance_items','opening_subledger_balances','opening_subledger_settlements','opening_financial_corrections','supplier_payments','material_purchase_headers','material_purchase_items','material_supplier_invoices','material_supplier_invoice_lines','material_supplier_returns','material_supplier_return_items','material_purchase_cost_corrections','material_purchase_cost_correction_items','material_stock_movements','material_rolls','cost_recalc_queue','cost_adjustments','suppliers','materials','cp6_v2620m_rollback_capsule','supplier_cent_posting_facts','material_cost_history','material_cost_revaluation_state','material_cost_revaluation_events','material_cost_checkpoints']::text[] loop
 execute format($sql$select encode(extensions.digest(convert_to(coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex') from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
 v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
 end loop;
 update erp.cp6_v2620n_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary$;
insert into erp.schema_migrations(version,description) values('v2.6.20n','Supplier cent lifecycle, immutable cent facts and atomic linked inverse rounding adjustments');
commit;
