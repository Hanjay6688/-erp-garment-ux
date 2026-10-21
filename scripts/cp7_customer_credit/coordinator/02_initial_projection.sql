-- OUTSIDE PRODUCT. No public facade is created. All reads below are private
-- source capabilities and confer no Native admission on their own.
do $not_an_installer$begin raise exception 'OW04_COORDINATOR_REQUIRES_ATOMIC_NATIVE_COMPOSITION';end $not_an_installer$;

create function cp7_credit.account_by_mapping_v1(p_key text)returns uuid
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare a uuid;
begin
 select m.account_id into strict a from erp.accounting_account_mappings m join erp.chart_accounts c on c.id=m.account_id
  where m.mapping_key=p_key and c.is_active and c.is_postable;
 return a;
end $$;

-- Approved BB per-document LIABILITY/CREDIT eligibility, with explicit actual
-- Native/BB journal ownership and per-customer reconciliation. No default,
-- invented batch, unexplained account adoption or caller account payload.
create function cp7_credit.credit_account_facts_v1(p_id uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare a erp.chart_accounts;expected numeric;actual numeric;c uuid;js uuid[];
begin
 select *into strict a from erp.chart_accounts where id=p_id;
 if a.account_type<>'LIABILITY'or a.normal_balance<>'CREDIT'or not a.is_active or not a.is_postable
  or exists(select 1 from erp.cash_accounts where coa_account_id=a.id)
  or exists(select 1 from erp.accounting_account_mappings where account_id=a.id)
  or exists(select 1 from erp.initial_import_prepayments where coa_account_id=a.id)then
  raise exception 'CP7_CREDIT_LIABILITY_ACCOUNT_INELIGIBLE';end if;
 with recursive roots(id)as(
  select journal_entry_id from erp.bb_customer_credits_v1 where coa_account_id=a.id and journal_entry_id is not null
  union select e.journal_entry_id from erp.bb_customer_credit_events_v1 e join erp.bb_customer_credits_v1 b on b.id=e.credit_id
   where b.coa_account_id=a.id and e.journal_entry_id is not null
  union select j.id from erp.bb_customer_credit_events_v1 e join erp.bb_customer_credits_v1 b on b.id=e.credit_id
   join erp.journal_entries j on j.source_type='OPENING_SUBLEDGER_SETTLEMENT'and j.source_id=e.settlement_id where b.coa_account_id=a.id
  union select cj.journal_id from cp7_credit.component_journals cj join cp7_credit.component_parts pp on pp.id=cj.part_id
   join cp7_credit.recognition_components cc on cc.id=pp.component_id join cp7_credit.recognition_plans p on p.id=cc.plan_id
   join cp7_credit.cohorts ch on ch.id=p.cohort_id where ch.credit_account_id=a.id
  union select ce.journal_id from cp7_credit.consumption_events ce join cp7_credit.cohorts ch on ch.id=ce.cohort_id where ch.credit_account_id=a.id
 ),walk(id)as(select id from roots union select j.id from walk w join erp.journal_entries j
  on j.reversal_of_id=w.id or(j.source_type='JOURNAL_REVERSAL'and j.source_id=w.id))
 select coalesce(array_agg(id order by id),'{}')into js from walk;
 if exists(select 1 from erp.journal_lines l where l.account_id=a.id and not l.journal_entry_id=any(js))then
  raise exception 'CP7_CREDIT_UNTRACKED_LIABILITY_JOURNAL';end if;
 for c in select customer_id from erp.bb_customer_credits_v1 where coa_account_id=a.id
  union select customer_id from cp7_credit.cohorts where credit_account_id=a.id
  union select l.customer_id from erp.journal_lines l where l.account_id=a.id loop
  if c is null then raise exception 'CP7_CREDIT_LIABILITY_CUSTOMER_MISSING';end if;
  select coalesce(sum((erp.bb_customer_credit_state_v1(b.id)->>'remaining_amount')::numeric),0)into expected
   from erp.bb_customer_credits_v1 b where b.coa_account_id=a.id and b.customer_id=c;
  expected:=expected+coalesce((select sum(pp.amount)from cp7_credit.component_parts pp join cp7_credit.recognition_components cc on cc.id=pp.component_id
   join cp7_credit.recognition_plans p on p.id=cc.plan_id join cp7_credit.cohorts ch on ch.id=p.cohort_id
   join cp7_credit.component_journals cj on cj.part_id=pp.id where ch.credit_account_id=a.id and ch.customer_id=c),0)
   -coalesce((select sum(ce.amount)from cp7_credit.consumption_events ce join cp7_credit.cohorts ch on ch.id=ce.cohort_id
    where ch.credit_account_id=a.id and ch.customer_id=c),0);
  select coalesce(sum(l.credit-l.debit),0)into actual from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
   where l.account_id=a.id and l.customer_id=c and j.status in('POSTED','REVERSED');
  if expected is distinct from actual or expected<0 then raise exception 'CP7_CREDIT_LIABILITY_RECONCILIATION_FAILED';end if;
 end loop;
 return jsonb_build_object('account',to_jsonb(a),'approved_predicate','BB_ACTIVE_POSTABLE_LIABILITY_CREDIT',
  'actual_journal_ids',to_jsonb(js),'all_tracked_customer_balances_reconciled',true);
end $$;

create function cp7_credit.cash_account_facts_v1(p_id uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare c erp.cash_accounts;a erp.chart_accounts;
begin
 select *into strict c from erp.cash_accounts where id=p_id;
 select *into strict a from erp.chart_accounts where id=c.coa_account_id;
 if not c.is_active or not a.is_active or not a.is_postable or a.account_type<>'ASSET'
  or exists(select 1 from erp.accounting_account_mappings m where m.account_id=a.id and m.mapping_key not in('CASH','BANK'))then
  raise exception 'CP7_CREDIT_REFUND_CASH_ACCOUNT_INELIGIBLE';end if;
 return jsonb_build_object('cash',to_jsonb(c),'account',to_jsonb(a),'mappings',coalesce(
  (select jsonb_agg(to_jsonb(m)order by m.mapping_key)from erp.accounting_account_mappings m where m.account_id=a.id),'[]'));
end $$;

-- Hypothetical cumulative BE targets. PO rounds AFTER pooling its lots;
-- non-PO rounds EACH lot before pooling by product. Movement snapshots are
-- deliberately not the calculator: their six decimals are physical history.
-- The complete raw inputs are retained in the private, source-bound quote.
create function cp7_credit.initial_hpp_targets_v1(p_product uuid,p_po uuid,p_items jsonb,p_after boolean)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 with requested as(
  select (x->>'lot_id')::uuid lot_id,sum((x->>'qty_pcs')::numeric)qty
  from jsonb_array_elements(p_items)x group by (x->>'lot_id')::uuid
 ),lot_source as(
  select fl.id lot_id,fl.product_id,fl.po_id,fl.lot_origin,fl.initial_qty_pcs,
   to_jsonb(fl)lot_source,to_jsonb(hv)hpp_source,
   case when coalesce(hv.qty_basis_pcs,0)>0 then hv.total_cost/hv.qty_basis_pcs else 0 end::numeric unit_raw,
   case when p_po is not null then case when fl.lot_origin='PRODUCTION' then coalesce(hv.total_cost,0)else 0 end
    else (case when fl.lot_origin<>'CONVERSION'or exists(select 1 from erp.product_conversion_allocations a
      join erp.product_conversions c on c.id=a.conversion_id where a.destination_lot_id=fl.id and c.status='POSTED')
      then coalesce(hv.total_cost,0)else 0 end)-coalesce((select sum(a.qty_pcs*(hv.total_cost/nullif(hv.qty_basis_pcs,0)))
       from erp.product_conversion_allocations a join erp.product_conversions c on c.id=a.conversion_id
       where a.source_lot_id=fl.id and c.status='POSTED'),0)end::numeric raw_total
  from erp.fg_lots fl left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current
  where (p_po is not null and fl.po_id=p_po and fl.lot_origin in('PRODUCTION','CONVERSION'))
   or(p_po is null and fl.po_id is null and fl.product_id=p_product and fl.lot_origin<>'VOIDED_PRODUCTION')
 ),facts as(
  select l.*,coalesce(q.qty,0)::numeric requested_qty,m.owned_qty,s.sold_qty,r.returned_qty,
   (m.owned_qty+case when p_after then coalesce(q.qty,0)else 0 end)::numeric owned_after,
   (s.sold_qty-r.returned_qty-case when p_after then coalesce(q.qty,0)else 0 end)::numeric net_sold_after
  from lot_source l left join requested q on q.lot_id=l.lot_id
  cross join lateral(select(coalesce(sum(m.qty_signed),0)+coalesce(sum(abs(m.qty_signed))filter(
   where m.movement_type='SALE_RESERVE'and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)),0))::numeric owned_qty
   from erp.fg_stock_movements m where m.lot_id=l.lot_id)m
  cross join lateral(select coalesce(sum(a.qty_pcs),0)::numeric sold_qty from erp.sale_stock_allocations a
   join erp.sales_items i on i.id=a.sale_item_id join erp.sales_headers h on h.id=i.sale_id
   where a.lot_id=l.lot_id and h.status in('POSTED','PARTIAL_PAID','PAID'))s
  cross join lateral(select coalesce(sum(i.qty_pcs),0)::numeric returned_qty from erp.sales_return_items i
   join erp.sales_returns h on h.id=i.return_id where i.lot_id=l.lot_id and h.status='POSTED')r
 ),extra as(select case when p_po is null then 0 else erp.be_po_extra_v1(p_po)end::numeric amount),cents as(
  select round(f.raw_total,2)::numeric hpp,round(f.raw_total-greatest(f.owned_after,0)*f.unit_raw,2)::numeric total_out,
   round(greatest(f.net_sold_after,0)*f.unit_raw,2)::numeric cogs from facts f where p_po is null
  union all
  select round(coalesce(sum(f.raw_total),0)+(select amount from extra),2)::numeric,
   round(coalesce(sum(f.raw_total),0)+(select amount from extra)-coalesce(sum(greatest(f.owned_after,0)*f.unit_raw),0),2)::numeric,
   round(coalesce(sum(greatest(f.net_sold_after,0)*f.unit_raw),0),2)::numeric
  from facts f having p_po is not null
 ),target as(
  select coalesce(sum(hpp),0)::numeric hpp_total_cost,coalesce(sum(hpp-total_out),0)::numeric fg_value,
   coalesce(sum(cogs),0)::numeric cogs_value,coalesce(sum(total_out-cogs),0)::numeric other_out_value from cents
 )select jsonb_build_object('target',to_jsonb(t)||case when p_po is null then'{}'::jsonb else jsonb_build_object(
   'base_output_qty',(select coalesce(sum(initial_qty_pcs),0)from facts where lot_origin='PRODUCTION'))end,
  'lots',(select coalesce(jsonb_agg(to_jsonb(f)order by f.lot_id),'[]')from facts f),
  'po_extra',(select amount from extra),'conversions',(select coalesce(jsonb_agg(jsonb_build_object(
   'allocation',to_jsonb(a),'conversion',to_jsonb(c))order by a.id),'[]')from erp.product_conversion_allocations a
   join erp.product_conversions c on c.id=a.conversion_id where a.source_lot_id in(select lot_id from facts)
    or a.destination_lot_id in(select lot_id from facts)))from target t
$$;

-- Full target AFTER the entire return minus authoritative BEFORE book. A
-- scalar cannot stand in for the signed FG/COGS/OTHER vector. Public v1's
-- hpp_amount is its positive debit magnitude per group, before cross-group
-- netting; it is NOT qty*unit-cost or the returned inventory value.
create function cp7_credit.initial_hpp_projection_v1(p_legacy jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare x jsonb;a record;r record;t record;b record;cost numeric;owned numeric;sold numeric;returned numeric;
 hpp numeric:=0;items jsonb:='[]';groups jsonb:='[]';lines jsonb:='[]';group_amount numeric;
 products uuid[];pos uuid[];lots uuid[];versions uuid[];fresh_lots uuid[];fresh_versions uuid[];
 before_profile jsonb;after_profile jsonb;before_target jsonb;after_target jsonb;actual_book jsonb;saved_state jsonb;account_facts jsonb;source_support jsonb;
 delta_fg numeric;delta_cogs numeric;delta_other numeric;fg_account uuid;cogs_account uuid;expense_account uuid;income_account uuid;
begin
 select array_agg(distinct i.product_id order by i.product_id),array_agg(distinct fl.po_id order by fl.po_id)filter(where fl.po_id is not null)
 into products,pos from jsonb_array_elements(p_legacy->'items')as draft_item(value)join erp.sale_stock_allocations sa on sa.id=(draft_item.value->>'allocation_id')::uuid
  join erp.sales_items i on i.id=sa.sale_item_id join erp.fg_lots fl on fl.id=sa.lot_id;
 pos:=coalesce(pos,'{}'::uuid[]);
 select coalesce(array_agg(id order by id),'{}'::uuid[])into lots from erp.fg_lots where product_id=any(products)or po_id=any(pos);
 select coalesce(array_agg(id order by id),'{}'::uuid[])into versions from erp.hpp_versions where lot_id=any(lots);
 perform 1 from erp.locations where id in(select(value->>'location_id')::uuid from jsonb_array_elements(p_legacy->'items'))order by id for share;
 perform 1 from erp.fg_inventory_balances inv where exists(select 1 from jsonb_array_elements(p_legacy->'items')draft_item
  join erp.sale_stock_allocations sa on sa.id=(draft_item->>'allocation_id')::uuid join erp.sales_items si on si.id=sa.sale_item_id
  where inv.product_id=si.product_id and inv.location_id=(draft_item->>'location_id')::uuid and inv.quality_grade=draft_item->>'quality_grade')
  order by inv.product_id,inv.location_id,inv.quality_grade for update;
 -- Include PO siblings even when another product owns them. Never acquire
 -- newly discovered earlier-order rows from the completion callback.
 perform 1 from erp.fg_lots where id=any(lots)order by id for update;
 perform 1 from erp.hpp_versions where id=any(versions)order by id for share;
 perform 1 from erp.po_hpp_gl_state where po_id=any(pos)order by po_id for update;
 select coalesce(array_agg(id order by id),'{}'::uuid[])into fresh_lots from erp.fg_lots where product_id=any(products)or po_id=any(pos);
 select coalesce(array_agg(id order by id),'{}'::uuid[])into fresh_versions from erp.hpp_versions where lot_id=any(fresh_lots);
 if fresh_lots is distinct from lots or fresh_versions is distinct from versions then raise exception 'CP7_CREDIT_HPP_LOCK_SET_CHANGED';end if;
 account_facts:=cp7_credit.initial_hpp_account_facts_v1();
 fg_account:=cp7_credit.account_by_mapping_v1('FG_INVENTORY');cogs_account:=cp7_credit.account_by_mapping_v1('COGS');
 expense_account:=cp7_credit.account_by_mapping_v1('OTHER_EXPENSE');income_account:=cp7_credit.account_by_mapping_v1('OTHER_INCOME');
 if exists(select 1 from jsonb_array_elements(account_facts->'mappings')as mapped(value)where(mapped.value->>'account_id')::uuid is distinct from
  case mapped.value->>'mapping_key'when'FG_INVENTORY'then fg_account when'COGS'then cogs_account when'OTHER_EXPENSE'then expense_account else income_account end)then
  raise exception 'CP7_CREDIT_HPP_ACCOUNT_SOURCE_CHANGED';end if;
 for x in select value from jsonb_array_elements(p_legacy->'items')loop
  select sa.*,i.sale_id,i.product_id,fl.po_id,fl.lot_origin,hv.id hpp_id,hv.total_cost,hv.qty_basis_pcs,hv.hpp_per_pcs current_unit_snapshot into strict a
   from erp.sale_stock_allocations sa join erp.sales_items i on i.id=sa.sale_item_id join erp.fg_lots fl on fl.id=sa.lot_id
   join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current where sa.id=(x->>'allocation_id')::uuid;
  if a.sale_id<>(p_legacy->>'sale_id')::uuid or a.qty_basis_pcs<=0 or a.lot_origin='VOIDED_PRODUCTION'
   or not exists(select 1 from erp.locations where id=(x->>'location_id')::uuid and is_active and location_type='FG_WAREHOUSE')then
   raise exception 'CP7_CREDIT_RETURN_SOURCE_OR_DESTINATION_CHANGED';end if;
  if a.total_cost::text in('NaN','Infinity','-Infinity')or a.current_unit_snapshot::text in('NaN','Infinity','-Infinity')then
   raise exception 'CP7_CREDIT_NONFINITE_HPP_SOURCE';end if;
  cost:=a.total_cost/a.qty_basis_pcs;
  if cost<0 then raise exception 'CP7_CREDIT_NEGATIVE_HPP_SOURCE';end if;
  select coalesce(sum(m.qty_signed),0)+coalesce(sum(abs(m.qty_signed))filter(where m.movement_type='SALE_RESERVE'
   and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)),0)into owned
   from erp.fg_stock_movements m where m.lot_id=a.lot_id;
  select coalesce(sum(sa.qty_pcs),0)into sold from erp.sale_stock_allocations sa join erp.sales_items si on si.id=sa.sale_item_id
   join erp.sales_headers sh on sh.id=si.sale_id where sa.lot_id=a.lot_id and sh.status in('POSTED','PARTIAL_PAID','PAID');
  select coalesce(sum(ri.qty_pcs),0)into returned from erp.sales_return_items ri join erp.sales_returns rr on rr.id=ri.return_id
   where ri.lot_id=a.lot_id and rr.status='POSTED';
  -- Preserve the retained Native allocation refusal before the extra HPP
  -- target checks; a prior completed return consumes this same allocation.
  if (x->>'qty_pcs')::numeric>a.qty_pcs-coalesce((select sum(ri.qty_pcs)from erp.sales_return_items ri join erp.sales_returns rr on rr.id=ri.return_id
    where rr.status='POSTED'and ri.sale_stock_allocation_id=a.id),0)then raise exception 'AH_RETURN_EXCEEDS_ORIGINAL_ALLOCATION';end if;
  if owned<0 or sold-returned<(select sum((v->>'qty_pcs')::numeric)from jsonb_array_elements(p_legacy->'items')v
   join erp.sale_stock_allocations s on s.id=(v->>'allocation_id')::uuid where s.lot_id=a.lot_id)then raise exception 'CP7_CREDIT_RETURN_QTY_SOURCE_INVALID';end if;
  items:=items||jsonb_build_array(x||jsonb_build_object('product_id',a.product_id,'lot_id',a.lot_id,'po_id',a.po_id,
   'hpp_version_id',a.hpp_id,'unit_hpp_raw',cost::text,'unit_hpp_snapshot',a.current_unit_snapshot::text));
 end loop;
 for r in select distinct case when z->>'po_id'is null then(z->>'product_id')::uuid end product_id,
  (z->>'po_id')::uuid po_id from jsonb_array_elements(items)z
  order by po_id nulls first,product_id loop
  saved_state:=null;
  source_support:=cp7_credit.initial_hpp_support_v1(r.product_id,r.po_id);
  if r.po_id is null then
   select *into strict t from erp.compute_non_po_product_hpp_targets_v2620f(r.product_id);
   select coalesce(sum(l.debit-l.credit)filter(where l.account_id=fg_account),0)fg_value,
    coalesce(sum(l.debit-l.credit)filter(where l.account_id=cogs_account),0)cogs_value,
    coalesce(sum(l.debit-l.credit)filter(where l.account_id in(expense_account,income_account)),0)other_out_value
   into b from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id left join erp.journal_entries o on o.id=j.reversal_of_id
    where l.product_id=r.product_id and l.po_id is null and j.status in('POSTED','REVERSED')
     and(j.source_type<>'PRODUCT_CONVERSION'or erp.be_nonpo_admitted_v1(j.source_id))
     and(j.source_type<>'JOURNAL_REVERSAL'or o.source_type is distinct from'PRODUCT_CONVERSION'or erp.be_nonpo_admitted_v1(o.source_id));
   if round(t.fg_value,2)<>b.fg_value or round(t.cogs_value,2)<>b.cogs_value or round(t.other_out_value,2)<>b.other_out_value then
    raise exception 'CP7_CREDIT_HPP_TARGET_BOOK_NOT_RECONCILED';end if;
   actual_book:=to_jsonb(b)||jsonb_build_object('hpp_total_cost',b.fg_value+b.cogs_value+b.other_out_value);
  else
   -- PO groups are emitted once, and the source is the actual Native book
   -- reader's safe private equivalent, not the possibly stale cache alone.
   select *into strict t from erp.compute_po_hpp_gl_targets_v2620d(r.po_id);
   select to_jsonb(st)into strict saved_state from erp.po_hpp_gl_state st where st.po_id=r.po_id;
   if t.base_output_qty is distinct from(saved_state->>'base_output_qty')::integer
    or t.hpp_total_cost is distinct from(saved_state->>'hpp_total_cost')::numeric
    or t.fg_value is distinct from(saved_state->>'fg_value')::numeric or t.cogs_value is distinct from(saved_state->>'cogs_value')::numeric
    or t.other_out_value is distinct from(saved_state->>'other_out_value')::numeric then
    raise exception 'CP7_CREDIT_HPP_TARGET_BOOK_NOT_RECONCILED';end if;
   actual_book:=cp7_credit.initial_po_hpp_book_v1(r.po_id,fg_account,cogs_account,expense_account,income_account);
   select (actual_book->>'hpp_total_cost')::numeric hpp_total_cost,(actual_book->>'fg_value')::numeric fg_value,
    (actual_book->>'cogs_value')::numeric cogs_value,(actual_book->>'other_out_value')::numeric other_out_value into b;
   if round(t.hpp_total_cost,2)<>b.hpp_total_cost or round(t.fg_value,2)<>b.fg_value or round(t.cogs_value,2)<>b.cogs_value
    or round(t.other_out_value,2)<>b.other_out_value then raise exception 'CP7_CREDIT_HPP_TARGET_BOOK_NOT_RECONCILED';end if;
  end if;
  before_profile:=cp7_credit.initial_hpp_targets_v1(r.product_id,r.po_id,items,false);
  after_profile:=cp7_credit.initial_hpp_targets_v1(r.product_id,r.po_id,items,true);
  before_target:=before_profile->'target';after_target:=after_profile->'target';
  if before_target is distinct from to_jsonb(t)then raise exception 'CP7_CREDIT_HPP_CANONICAL_TARGET_MISMATCH';end if;
  if exists(select 1 from jsonb_array_elements(before_profile->'lots')f where(f->>'unit_raw')::text in('NaN','Infinity','-Infinity')
   or(f->>'raw_total')::text in('NaN','Infinity','-Infinity')or(f->>'unit_raw')::numeric<0
   or(f->>'owned_qty')::numeric<0 or(f->>'sold_qty')::numeric-(f->>'returned_qty')::numeric<(f->>'requested_qty')::numeric)then
   raise exception 'CP7_CREDIT_RETURN_QTY_SOURCE_INVALID';end if;
  delta_fg:=(after_target->>'fg_value')::numeric-b.fg_value;
  delta_cogs:=(after_target->>'cogs_value')::numeric-b.cogs_value;
  delta_other:=(after_target->>'other_out_value')::numeric-b.other_out_value;
  if cp7_credit.initial_hpp_support_v1(r.product_id,r.po_id)is distinct from source_support then
   raise exception 'CP7_CREDIT_HPP_SUPPORT_CHANGED_DURING_READ';end if;
  if delta_fg+delta_cogs+delta_other<>0 or(after_target->>'hpp_total_cost')::numeric<>(before_target->>'hpp_total_cost')::numeric
   or r.po_id is not null and(delta_fg<0 or delta_cogs>0)then raise exception 'CP7_CREDIT_HPP_VECTOR_NOT_CONSERVED';end if;
  group_amount:=greatest(delta_fg,0)+greatest(delta_cogs,0)+greatest(delta_other,0);hpp:=hpp+group_amount;
  groups:=groups||jsonb_build_array(jsonb_build_object('product_id',case when r.po_id is null then r.product_id end,'po_id',r.po_id,
   'amount',cp7_credit.cent_text(group_amount),'before_target',before_target,'after_target',after_target,'before_book',actual_book,'before_saved_state',saved_state,
   'before_profile',before_profile,'after_profile',after_profile,'source_support',source_support,
   'delta',jsonb_build_object('fg_value',delta_fg,'cogs_value',delta_cogs,'other_out_value',delta_other)));
  for x in select *from jsonb_array_elements(jsonb_build_array(
   jsonb_build_object('mapping_key','FG_INVENTORY','signed_amount',delta_fg),jsonb_build_object('mapping_key','COGS','signed_amount',delta_cogs),
   jsonb_build_object('mapping_key',case when delta_other>0 then'OTHER_EXPENSE'else'OTHER_INCOME'end,'signed_amount',delta_other)))loop
   if(x->>'signed_amount')::numeric<>0 then lines:=lines||jsonb_build_array(jsonb_strip_nulls(jsonb_build_object(
    'mapping_key',x->>'mapping_key','debit',greatest((x->>'signed_amount')::numeric,0),'credit',greatest(-(x->>'signed_amount')::numeric,0),
    'product_id',case when r.po_id is null then r.product_id end,'po_id',r.po_id)));end if;
  end loop;
 end loop;
 -- The existing source-bound NO_JOURNAL reader proves physical snapshot0.
 -- Do not silently widen it for positive-cost stock with a zero cent vector.
 if hpp=0 and(select coalesce(sum((v->>'refund_amount')::numeric),0)from jsonb_array_elements(items)v)=0
  and exists(select 1 from jsonb_array_elements(items)v where(v->>'unit_hpp_snapshot')::numeric>0)then
  raise exception 'CP7_CREDIT_POSITIVE_HPP_ZERO_VECTOR_UNPROVEN';end if;
 return jsonb_build_object('items',items,'groups',groups,'hpp_amount',cp7_credit.cent_text(hpp),'lines',lines,
  'locked_lot_ids',to_jsonb(lots),'locked_hpp_version_ids',to_jsonb(versions),'account_facts',account_facts);
end $$;

create function cp7_credit.component_movements_v1(p_kernel jsonb)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select coalesce(jsonb_agg(jsonb_build_object('id','component:'||n::text,'amount',x->>'amount','economic_date',x->>'economic_date',
  'transaction_date',x->>'transaction_date','source_sha256',cp7_credit.pg_jsonb_sha256(x))order by n),'[]')
 from jsonb_array_elements(p_kernel->'components')with ordinality e(x,n)
$$;

create function cp7_credit.initial_refund_book_plan_v1(p_kernel jsonb,p_full numeric,p_physical timestamptz,p_lawful date,p_return_book date)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare e date;minimum_book date;selected date;candidate date;books jsonb;profiles jsonb:='[]';cap jsonb;eligible boolean;
begin
 if p_full is null or p_full<=0 or p_full::text in('NaN','Infinity','-Infinity')or p_full*100<>trunc(p_full*100)
  or p_physical is null or not isfinite(p_physical)or p_lawful is null or p_return_book is null
  or not isfinite(p_lawful)or not isfinite(p_return_book)then raise exception 'CP7_CREDIT_REFUND_BOOK_PLAN_INPUT';end if;
 e:=(p_physical at time zone'Asia/Jakarta')::date;minimum_book:=greatest(p_lawful,p_return_book);
 if p_lawful<e then raise exception 'CP7_CREDIT_REFUND_LAWFUL_DATE_BEFORE_ECONOMIC';end if;
 select jsonb_agg(b::text order by b)into books from(select minimum_book b union select(x->>'transaction_date')::date
  from jsonb_array_elements(p_kernel->'components')x where(x->>'transaction_date')::date>=minimum_book)s;
 for candidate in select value::date from jsonb_array_elements_text(books)loop
  cap:=ow04_pure_kernel.credit_capacity_v1(cp7_credit.component_movements_v1(p_kernel),'[]',e::text,candidate::text);
  eligible:=(cap->>'source_prefixes_nonnegative')::boolean and(cap->>'current_balance')::numeric=p_full and(cap->>'minimum_available')::numeric>=p_full;
  profiles:=profiles||jsonb_build_array(jsonb_build_object('transaction_date',candidate,'capacity',cap,'eligible',eligible));
  if eligible and selected is null then selected:=candidate;end if;
 end loop;
 return jsonb_build_object('contract_version','ow04.initial-refund-book-plan.v1','full_k',cp7_credit.cent_text(p_full),'economic_date',e,
  'lawful_book_date',p_lawful,'return_book_floor',p_return_book,'candidate_books',books,'candidates',profiles,'selected_book_date',selected);
end $$;

-- Internal return includes private source/projection and an exact public quote.
-- Root's read RPC exposes ONLY ->'quote', retaining the established UI wire.
create function cp7_credit.build_initial_return_for_draft_v1(p_legacy jsonb,p_expected text,p_choice jsonb,p_own_return uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare h erp.sales_headers;src jsonb;preserved jsonb;before_events jsonb;hpp jsonb;prior jsonb;prior_manifest jsonb;
 period jsonb;authority jsonb;projected jsonb;projection jsonb;added jsonb;k jsonb;quote jsonb;binding jsonb;totals_before jsonb;totals_after jsonb;
 credit jsonb;cash jsonb;refund jsonb;capacity jsonb;book_plan jsonb;components jsonb;issues jsonb:='[]';mode text;amount numeric;gross numeric;returns numeric;paid numeric;
 net numeric;after_net numeric;issued numeric;book date;economic date;floor date;cash_econ date;cash_book date;ar uuid;lines jsonb;draft_sha text;
begin
 perform cp7_sales.validate_return(p_legacy,false);
 authority:=cp7_credit.return_command_access(p_choice->>'mode');
 if p_own_return is not null and(not exists(select 1 from erp.sales_returns r join cp7_sales.command_context c on c.sale_id=r.sale_id
  join cp7_sales.requests q on q.actor=c.actor and q.action='RETURN'and q.payload=p_legacy and q.expected_version=p_expected and q.response is null
  where r.id=p_own_return and r.status='DRAFT'and r.sale_id=(p_legacy->>'sale_id')::uuid and c.action='RETURN'and c.actor=auth.uid()
   and c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current())
  or p_choice is distinct from cp7_credit.initial_choice_v1(null))then raise exception 'CP7_CREDIT_OWN_DRAFT_EXCLUSION_UNBOUND';end if;
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 src:=ow04_source_proposal.locked_source_family((p_legacy->>'sale_id')::uuid);
 if src->>'source_status'<>'BASE_COLLECTED'or jsonb_array_length(src->'family'->'note_revisions')<>0
  or exists(select 1 from cp7_credit.cohorts ch join cp7_credit.return_families f on f.id=ch.family_id where f.family_root_sale_id=(p_legacy->>'sale_id')::uuid)
  or exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=(p_legacy->>'sale_id')::uuid)
  or exists(select 1 from cp7_sales_return_correction.links where sale_id=(p_legacy->>'sale_id')::uuid)then
  raise exception 'CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED';end if;
 select *into strict h from erp.sales_headers where id=(p_legacy->>'sale_id')::uuid;
 if h.status not in('POSTED','PARTIAL_PAID','PAID')or h.row_version::text is distinct from p_expected
  or p_own_return is null and cp7_sales.review_token(h.id)is distinct from p_legacy->>'review_token'then raise exception 'CP7_SALES_REVIEW_CHANGED';end if;
 -- The exact verified Native apply_command already checked the ordinary
 -- request's review token under its caller timezone BEFORE inserting this
 -- own DRAFT, while owning FG/source rows. Re-serializing that old MD5 under
 -- this callback's UTC pin would incorrectly reject non-UTC Native callers.
 -- The branch above proves the exact still-pending ordinary Native request,
 -- current fine authority, expected version and no financial choice. Public
 -- quote/reviewed sealing always uses p_own_return=NULL and full fresh token.
 if(p_legacy->>'physical_at')::timestamptz<h.sale_date or(p_legacy->>'physical_at')::timestamptz>statement_timestamp()then
  raise exception 'CP7_CREDIT_RETURN_PHYSICAL_DATE_INVALID';end if;
 ar:=(src->'ar_account'->>'id')::uuid;
 before_events:=cp7_credit.initial_base_events_v1(h.id);
 if cp7_credit.initial_event_semantics_v1(before_events)is distinct from cp7_credit.initial_event_semantics_v1(src->'events')then
  raise exception 'CP7_CREDIT_NATIVE_SOURCE_VECTOR_INCOMPLETE';end if;
 -- Existing empty families may retain their real ordinals. Before any new
 -- family, their aggregate profile must be identically empty at every cut.
 perform cp7_credit.assert_zero_excess_v1(before_events);
 select coalesce(sum(line_total),0)into gross from erp.sales_items where sale_id=h.id;
 select coalesce(sum(i.refund_amount),0)into returns from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where r.sale_id=h.id and r.status='POSTED';
 select coalesce(sum(pay.amount),0)into paid from erp.sales_payments pay where pay.sale_id=h.id and pay.status='POSTED';
 select sum((x->>'refund_amount')::numeric)into amount from jsonb_array_elements(p_legacy->'items')x;
 net:=gross-returns;after_net:=net-amount;
 if gross<0 or net<0 or paid<0 or paid>net or amount<0 or after_net<0 then raise exception 'CP7_CREDIT_CORRUPT_BEFORE_AR_OR_RETURN';end if;
 if exists(select 1 from jsonb_array_elements(p_legacy->'items')x join erp.sale_stock_allocations a on a.id=(x->>'allocation_id')::uuid
  join erp.sales_items i on i.id=a.sale_item_id group by i.product_id having sum((x->>'refund_amount')::numeric)
   >coalesce((select sum(si.line_total)from erp.sales_items si where si.sale_id=h.id and si.product_id=i.product_id),0)
    -coalesce((select sum(ri.refund_amount)from erp.sales_return_items ri join erp.sales_returns rr on rr.id=ri.return_id
     where rr.sale_id=h.id and rr.status='POSTED'and ri.product_id=i.product_id),0))then raise exception 'CP7_CREDIT_REFUND_PRODUCT_VALUE_EXCEEDED';end if;
 -- All source/master locks precede period SHARE. No callback below may
 -- discover another earlier-order lock after this sealer returns.
 hpp:=cp7_credit.initial_hpp_projection_v1(p_legacy);
 perform 1 from erp.accounting_account_mappings where mapping_key in('AR_CUSTOMER','SALES_REVENUE','FG_INVENTORY','COGS','OTHER_EXPENSE','OTHER_INCOME')order by mapping_key for share;
 perform 1 from erp.chart_accounts where id in(select account_id from erp.accounting_account_mappings
  where mapping_key in('AR_CUSTOMER','SALES_REVENUE','FG_INVENTORY','COGS','OTHER_EXPENSE','OTHER_INCOME'))
  or id=(p_choice->>'credit_account_id')::uuid or id in(select coa_account_id from erp.cash_accounts where id=(p_choice->>'cash_account_id')::uuid)order by id for share;
 perform 1 from erp.cash_accounts where id=(p_choice->>'cash_account_id')::uuid for share;
 -- The HPP book was read before these globally ordered account locks. Prove
 -- that every mapping/master used for it is still precisely the locked one.
 if cp7_credit.initial_hpp_account_facts_v1()is distinct from hpp->'account_facts'then
  raise exception 'CP7_CREDIT_HPP_ACCOUNT_SOURCE_CHANGED';end if;
 mode:=p_choice->>'mode';
 if p_choice->>'credit_account_id'is not null then credit:=cp7_credit.credit_account_facts_v1((p_choice->>'credit_account_id')::uuid);end if;
 if p_choice->>'cash_account_id'is not null then cash:=cp7_credit.cash_account_facts_v1((p_choice->>'cash_account_id')::uuid);end if;
 select max(j.transaction_date)into floor from erp.journal_entries j where j.source_type='SALE'and j.source_id=h.id and j.reversal_of_id is null;
 if floor is null then
  prior_manifest:=jsonb_build_object('contract_version','ow04.initial-prior-causal-manifest.v1','sale_id',h.id,
   'sale_absence',ow04_source_proposal.sale_absence_fact_v1(h.id),'existing_return_members',(select coalesce(jsonb_agg(
    ow04_source_proposal.verify_return_member_v1(r.id)order by r.id),'[]')from erp.sales_returns r where r.sale_id=h.id and r.status<>'DRAFT'));
  if gross<>0 or returns<>0 or paid<>0 or amount<>0 or jsonb_array_length(before_events)<>0 then
   raise exception 'CP7_CREDIT_PRIOR_ABSENCE_FULL_ZERO_PROFILE_REQUIRED';end if;
 else prior_manifest:=jsonb_build_object('contract_version','ow04.initial-prior-causal-manifest.v1','sale_id',h.id,
  'actual_sale_journals',(select jsonb_agg(cp7_credit.materialized_journal_payload(j.id)order by j.id)from erp.journal_entries j
   where j.source_type='SALE'and j.source_id=h.id and j.reversal_of_id is null),'causal_book_floor',floor);end if;
 prior:=jsonb_build_object('contract_version','ow04.prior-causal-book-proof.v1','scope','PRIOR_CAUSAL_SALE_RETURN',
  'state',case when floor is null then'PROVEN_ABSENT'else'DATED'end,'causal_book_floor',floor,'proof_sha256',ow04_source_proposal.sha(prior_manifest));
 perform 1 from erp.accounting_period_control where singleton_id=1 for share;
 select to_jsonb(p)into strict period from erp.accounting_period_control p where singleton_id=1;
 economic:=((p_legacy->>'physical_at')::timestamptz at time zone'Asia/Jakarta')::date;
 if amount<>0 or(hpp->>'hpp_amount')::numeric<>0 then book:=greatest(erp.resolve_accounting_transaction_date(economic),floor);end if;
 draft_sha:=ow04_source_proposal.sha(p_legacy);
 projected:=jsonb_build_object('id','projected-return:'||draft_sha,'kind','NET','amount',cp7_credit.cent_text(-amount),
  'economic_date',economic::text,'transaction_date',book::text,'source_sha256',draft_sha);
 added:=case when book is null then'[]'::jsonb else jsonb_build_array(projected)end;
 k:=ow04_pure_kernel.recognition_plan_v1(before_events,added);issued:=(k->>'net_current_k')::numeric;
 if issued<0 or issued>amount or paid-issued>after_net or paid-issued<0 then raise exception 'CP7_CREDIT_INITIAL_K_OUTSIDE_RETURN_SCOPE';end if;
 lines:=case when amount=0 then'[]'::jsonb else jsonb_build_array(
  jsonb_build_object('mapping_key','SALES_REVENUE','debit',amount,'credit',0,'customer_id',h.customer_id),
  jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',amount,'customer_id',h.customer_id))end;
 select lines||coalesce(jsonb_agg(x||jsonb_build_object('customer_id',h.customer_id)),'[]')into lines from jsonb_array_elements(hpp->'lines')x;
 projection:=jsonb_build_object('contract_version','ow04.initial-return-projection.v1','source_sale_id',h.id,'customer_id',h.customer_id,
  'draft_sha256',draft_sha,'legacy_payload',p_legacy,'return_amount',cp7_credit.cent_text(amount),'hpp',hpp,
  'economic_date',economic,'prior_causal',prior,'journal_effect',case when book is null then'NO_JOURNAL'else'JOURNAL_EXPECTED'end,
  'planned_book_date',book,'lines',case when jsonb_array_length(lines)=0 then'[]'::jsonb else cp7_credit.native_cent_lines(lines)end,
  'net_before',cp7_credit.cent_text(net),'net_after',cp7_credit.cent_text(after_net),'raw_paid',cp7_credit.cent_text(paid),
  'current_k',cp7_credit.cent_text(issued),'ar_account_id',ar,'credit_account',credit,'cash_account',cash);
 if(k->>'has_recognition_effect')::boolean then
  if mode is null then issues:=issues||'"CHOOSE_MODE"'::jsonb;end if;
  if credit is null then issues:=issues||'"CHOOSE_CREDIT_ACCOUNT"'::jsonb;end if;
 elsif mode is not null or credit is not null then issues:=issues||'"CLEAR_UNNEEDED_SETTLEMENT"'::jsonb;end if;
 if mode='REFUND'then
  if issued=0 then issues:=issues||'"REFUND_ZERO_CURRENT_AMOUNT"'::jsonb;end if;
  if cash is null then issues:=issues||'"CHOOSE_REFUND_ACCOUNT"'::jsonb;end if;
  if p_choice->>'refund_physical_at'is null then issues:=issues||'"ENTER_REFUND_TIME"'::jsonb;
  else
   if(p_choice->>'refund_physical_at')::timestamptz>statement_timestamp()then raise exception 'CP7_CREDIT_REFUND_FUTURE_DATE';end if;
   cash_econ:=((p_choice->>'refund_physical_at')::timestamptz at time zone'Asia/Jakarta')::date;
   if issued>0 and book is not null then
    book_plan:=cp7_credit.initial_refund_book_plan_v1(k,issued,(p_choice->>'refund_physical_at')::timestamptz,erp.resolve_accounting_transaction_date(cash_econ),book);
    cash_book:=(book_plan->>'selected_book_date')::date;
    select z->'capacity'into capacity from jsonb_array_elements(book_plan->'candidates')z where(z->>'transaction_date')::date=cash_book;
   end if;
   if cash_book is null then issues:=issues||'"REFUND_EXCEEDS_DATED_CAPACITY"'::jsonb;end if;
  end if;
  refund:=jsonb_build_object('amount',cp7_credit.cent_text(issued),'physical_at',p_choice->'refund_physical_at','economic_date',cash_econ,
   'book_date',cash_book,'safe_capacity',case when capacity is not null then cp7_credit.cent_text(greatest((capacity->>'minimum_available')::numeric,0))end,
   'capacity_sha256',case when book_plan is not null then cp7_credit.pg_jsonb_sha256(book_plan)end);
 end if;
 projection:=projection||jsonb_build_object('refund_book_plan',book_plan);
 totals_before:=jsonb_build_object('gross_total',cp7_credit.cent_text(gross),'return_total',cp7_credit.cent_text(returns),'net_total',cp7_credit.cent_text(net),
  'payments_received',cp7_credit.cent_text(paid),'credit_applied','0.00','credit_recognized','0.00','effective_paid',cp7_credit.cent_text(paid),'receivable_remaining',cp7_credit.cent_text(net-paid));
 totals_after:=totals_before||jsonb_build_object('return_total',cp7_credit.cent_text(returns+amount),'net_total',cp7_credit.cent_text(after_net),
  'credit_recognized',cp7_credit.cent_text(issued),'effective_paid',cp7_credit.cent_text(paid-issued),'receivable_remaining',cp7_credit.cent_text(after_net-paid+issued));
 select coalesce(jsonb_agg(jsonb_build_object('component_key',cp7_credit.pg_jsonb_sha256(x),'economic_date',x->>'economic_date','book_date',x->>'transaction_date',
  'signed_amount',x->>'amount','support_sha256',cp7_credit.pg_jsonb_sha256(k->'support'))order by n),'[]')into components from jsonb_array_elements(k->'components')with ordinality e(x,n);
 preserved:=cp7_credit.initial_preserved_source_v1(h.id,p_own_return);
 binding:=jsonb_build_object('immutable_source_sha256',ow04_source_proposal.sha(before_events),'current_state_sha256',src->>'state_sha256',
  'draft_sha256',draft_sha,'choice_sha256',ow04_source_proposal.sha(p_choice),'projection_sha256',ow04_source_proposal.sha(projection),
  'authority_sha256',ow04_source_proposal.sha(authority),'period_sha256',ow04_source_proposal.sha(period),'dependency_sha256',ow04_source_proposal.sha(src->'lineage'),'quote_sha256',null);
 quote:=jsonb_build_object('contract_version','cp7.sales-return-settlement-quote.v1','kind','QUOTE','read_only',true,'business_DML',false,'captured_at',statement_timestamp(),
  'input_echo',jsonb_build_object('sale_id',h.id,'expected_version',p_expected,'review_token',p_legacy->'review_token','return_payload',p_legacy-'sale_id'-'review_token','settlement',p_choice),
  'source',jsonb_build_object('sale_id',h.id,'sale_number',h.sale_number,'customer_id',h.customer_id,'customer_name',src->'customer'->>'customer_name','row_version',p_expected,'review_token',p_legacy->'review_token'),
  'binding',binding,'has_recognition_effect',k->'has_recognition_effect','current_credit_amount',cp7_credit.cent_text(issued),'components',components,
  'return_projection',jsonb_build_object('economic_date',economic,'prior_causal',prior,'journal_effect',projection->'journal_effect','planned_book_date',book,
   'return_amount',cp7_credit.cent_text(amount),'hpp_amount',hpp->>'hpp_amount','receivable_account_id',case when amount<>0 then ar end),
  'totals',jsonb_build_object('before',totals_before,'after',totals_after),
  'credit_account',case when credit is not null then jsonb_build_object('id',p_choice->'credit_account_id','code',credit->'account'->'account_code','name',credit->'account'->'account_name','facts_sha256',ow04_source_proposal.sha(credit))end,
  'cash_account',case when cash is not null then jsonb_build_object('id',p_choice->'cash_account_id','code',cash->'cash'->'cash_account_code','name',cash->'cash'->'cash_account_name','facts_sha256',ow04_source_proposal.sha(cash))end,
  'refund_projection',refund,'capabilities',jsonb_build_object('record_return',true,'recognize_credit',true,'refund_cash',mode='REFUND'),
  'readiness',jsonb_build_object('state',case when jsonb_array_length(issues)=0 then'READY'else'CHOICE_REQUIRED'end,'issues',issues));
 -- captured_at is display-only, not part of the reproducible full semantic
 -- quote binding. Every source, input, choice, account, authority, period,
 -- dependency and component field remains inside this exact digest.
 if jsonb_array_length(issues)=0 then binding:=binding||jsonb_build_object('quote_sha256',ow04_source_proposal.sha(quote-'captured_at'));
  quote:=quote||jsonb_build_object('binding',binding);end if;
 if cp7_credit.return_command_access(mode)is distinct from authority then raise exception using errcode='42501',message='CP7_CREDIT_ACCESS_CHANGED_AFTER_SOURCE_WAIT';end if;
 return jsonb_build_object('quote',quote,'source',src,'preserved_source',preserved,'before_events',before_events,'projection',projection,'projected_kernel',k,
  'prior_causal',prior,'prior_causal_manifest',prior_manifest,'period_snapshot',period,'authority',authority,'credit_account_snapshot',credit,'cash_account_snapshot',cash);
end $$;

create function cp7_credit.build_initial_return_v1(p_legacy jsonb,p_expected text,p_choice jsonb)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$
 select cp7_credit.build_initial_return_for_draft_v1(p_legacy,p_expected,p_choice,null)
$$;
