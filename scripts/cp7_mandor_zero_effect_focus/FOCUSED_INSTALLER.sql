\set ON_ERROR_STOP on
begin;
set local lock_timeout = '30s';
set local statement_timeout = '5min';

do $guard$
declare actual text;
begin
 if current_setting('server_version_num')::integer <> 170006 then
  raise exception 'CP7_FOCUSED_POSTGRES_17_6_REQUIRED';
 end if;
 if pg_catalog.to_regnamespace('cp7_note_zero_effect') is not null then
  raise exception 'CP7_FOCUSED_ZERO_EFFECT_SCHEMA_ALREADY_EXISTS';
 end if;
 select md5(pg_get_functiondef('cp7_note.command(jsonb,uuid,text)'::regprocedure)) into actual;
 if actual is distinct from '96bf6ad085630b7d689666e564900e87' then
  raise exception 'CP7_FOCUSED_PREDECESSOR_CHANGED:cp7_note.command(jsonb,uuid,text):%',actual;
 end if;
 select md5(pg_get_functiondef('cp7_credit_note_carry_de.assert_effect_v1(jsonb,jsonb,uuid,uuid,numeric)'::regprocedure)) into actual;
 if actual is distinct from 'b228fb25e6208d5856c9f361bac72be2' then
  raise exception 'CP7_FOCUSED_PREDECESSOR_CHANGED:cp7_credit_note_carry_de.assert_effect_v1(jsonb,jsonb,uuid,uuid,numeric):%',actual;
 end if;
 select md5(pg_get_functiondef('cp7_credit.assert_current_source_plan_profile(uuid,uuid,uuid,jsonb)'::regprocedure)) into actual;
 if actual is distinct from '23f7a593ad9484a463ffdc3c2aee2e0f' then
  raise exception 'CP7_FOCUSED_PREDECESSOR_CHANGED:cp7_credit.assert_current_source_plan_profile(uuid,uuid,uuid,jsonb):%',actual;
 end if;
 select md5(pg_get_functiondef('cp7_credit.assert_initial_return_closed_v1(uuid)'::regprocedure)) into actual;
 if actual is distinct from 'd5f83430dc3ff04fa4a969730940fcff' then
  raise exception 'CP7_FOCUSED_PREDECESSOR_CHANGED:cp7_credit.assert_initial_return_closed_v1(uuid):%',actual;
 end if;
end
$guard$;

-- Private source proof for the ordinary zero-credit RETURN route.
-- This file is a staged adapter component. It does not replace a reader,
-- a command or a deferred constraint, and does not write financial data.
create schema cp7_note_zero_effect authorization postgres;
revoke all on schema cp7_note_zero_effect from public, anon, authenticated, service_role;

create function cp7_note_zero_effect.ordinary_reversed_history_v1(p_root uuid, p_leaf uuid, p_profile jsonb)
returns jsonb
language plpgsql stable security invoker
set search_path = '' set timezone = 'UTC'
as $function$
declare
  family cp7_credit.return_families;
  member cp7_credit.return_family_members;
  original erp.sales_returns;
  materialization cp7_credit.initial_return_materializations;
  source_journal erp.journal_entries;
  inverse_journal erp.journal_entries;
  original_lines jsonb;
  inverse_lines jsonb;
  return_item erp.sales_return_items;
  stock_outcome erp.fg_stock_movements;
  stock_inverse erp.fg_stock_movements;
  stock_facts jsonb;
  facts jsonb := '[]';
begin
  if p_root is null or p_leaf is null
     or (p_profile->>'sale_id', p_profile->>'root_sale_id', p_profile->>'current_leaf_id')
         is distinct from (p_leaf::text, p_root::text, p_leaf::text)
     or p_profile->'upstream_root_ids' is distinct from jsonb_build_array(p_root)
     or (p_profile->>'I')::numeric is distinct from 0::numeric
     or (p_profile->>'U')::numeric is distinct from 0::numeric
     or (p_profile->>'adjustment')::numeric is distinct from 0::numeric
     or exists (select 1 from erp.sales_payments where sale_id in (p_root, p_leaf))
     or exists (select 1 from cp7_credit.consumption_events where target_sale_id in (p_root, p_leaf))
     or exists (select 1 from cp7_sales_return_correction.links where sale_id in (p_root, p_leaf))
     or cp7_mandor_shop.invoice_offset_paid(p_root) is distinct from 0::numeric
     or cp7_mandor_shop.invoice_offset_paid(p_leaf) is distinct from 0::numeric then
    raise exception 'CP7_NOTE_ZERO_EFFECT_SOURCE_OUTSIDE_SCOPE';
  end if;

  -- Reject unregistered/draft/live return rows as well as any child of the
  -- replacement. Existing OW04 validation still owns registered lineage.
  if exists (
    select 1 from erp.sales_returns r
    where r.sale_id in (p_root, p_leaf)
      and (r.sale_id <> p_root or r.status is distinct from 'REVERSED'
        or not exists (
          select 1 from cp7_credit.return_families f
          where f.family_root_sale_id = p_root and f.first_return_id = r.id))
  ) then
    raise exception 'CP7_NOTE_ZERO_EFFECT_RETURN_OUTSIDE_SCOPE';
  end if;

  for family in
    select * from cp7_credit.return_families
    where family_root_sale_id = p_root order by family_ordinal, id
  loop
    select * into strict member from cp7_credit.return_family_members where family_id = family.id;
    select * into strict original from erp.sales_returns where id = family.first_return_id;
    select * into strict materialization from cp7_credit.initial_return_materializations
      where source_return_id = original.id;

    if family.assignment_kind is distinct from 'NEW_POST'
       or (member.return_id, member.member_kind, member.financial_state)
            is distinct from (original.id, 'ORIGINAL', 'JOURNAL')
       or (original.sale_id, original.status) is distinct from (p_root, 'REVERSED')
       or (materialization.origin, materialization.source_sale_id, materialization.family_id,
           materialization.family_ordinal, materialization.actor, materialization.request_id)
            is distinct from ('ORDINARY', p_root, family.id,
                              family.family_ordinal, family.actor, family.request_id)
       or materialization.cohort_id is not null or materialization.plan_id is not null
       or materialization.refund_operation_id is not null
       or (materialization.actual_kernel->>'net_current_k')::numeric is distinct from 0::numeric
       or exists (select 1 from cp7_credit.cohorts where family_id = family.id) then
      raise exception 'CP7_NOTE_ZERO_EFFECT_ORDINARY_RETURN_PROOF_REQUIRED';
    end if;

    perform ow04_source_proposal.verify_return_member_v1(original.id);
    select * into strict source_journal from erp.journal_entries where id = member.source_journal_id;
    select * into strict inverse_journal from erp.journal_entries
      where reversal_of_id = source_journal.id
         or (source_type = 'JOURNAL_REVERSAL' and source_id = source_journal.id);

    original_lines := cp7_credit.materialized_journal_payload(source_journal.id);
    inverse_lines := cp7_credit.materialized_journal_payload(inverse_journal.id);
    if (source_journal.source_type, source_journal.source_id, source_journal.status)
            is distinct from ('SALES_RETURN', original.id, 'REVERSED')
       or (inverse_journal.source_type, inverse_journal.source_id,
           inverse_journal.reversal_of_id, inverse_journal.status)
            is distinct from ('JOURNAL_REVERSAL', source_journal.id, source_journal.id, 'POSTED')
       or inverse_journal.economic_date < source_journal.economic_date
       or inverse_journal.transaction_date < source_journal.transaction_date
       or exists (select 1 from erp.journal_entries
           where reversal_of_id = inverse_journal.id
              or (source_type = 'JOURNAL_REVERSAL' and source_id = inverse_journal.id))
       or cp7_credit.source_inverse_vector_v1(inverse_lines->'lines')
            is distinct from cp7_credit.source_inverse_vector_v1(original_lines->'lines', true) then
      raise exception 'CP7_NOTE_ZERO_EFFECT_RETURN_INVERSE_CHANGED';
    end if;

    stock_facts := '[]';
    for return_item in
      select * from erp.sales_return_items where return_id = original.id order by id
    loop
      select * into strict stock_outcome from erp.fg_stock_movements
        where source_type = 'SALES_RETURN_ITEM' and source_id = return_item.id
          and reversal_of_id is null;
      select * into strict stock_inverse from erp.fg_stock_movements
        where reversal_of_id = stock_outcome.id;
      if (stock_outcome.movement_type, stock_outcome.product_id, stock_outcome.lot_id,
          stock_outcome.location_id, stock_outcome.quality_grade, stock_outcome.customer_id,
          stock_outcome.qty_signed, stock_outcome.unit_hpp_snapshot, stock_outcome.physical_at)
            is distinct from ('SALE_RETURN', return_item.product_id, return_item.lot_id,
              return_item.location_id, return_item.quality_grade, original.customer_id,
              return_item.qty_pcs, return_item.unit_hpp_snapshot, original.physical_at)
         or (stock_inverse.movement_type, stock_inverse.source_type, stock_inverse.source_id,
             stock_inverse.product_id, stock_inverse.lot_id, stock_inverse.location_id,
             stock_inverse.quality_grade, stock_inverse.customer_id, stock_inverse.qty_signed,
             stock_inverse.unit_hpp_snapshot)
            is distinct from ('REVERSAL', 'FG_MOVEMENT_REVERSAL', stock_outcome.id,
              stock_outcome.product_id, stock_outcome.lot_id, stock_outcome.location_id,
              stock_outcome.quality_grade, stock_outcome.customer_id, -stock_outcome.qty_signed,
              stock_outcome.unit_hpp_snapshot)
         or stock_inverse.physical_at < stock_outcome.physical_at
         or exists (select 1 from erp.fg_stock_movements where reversal_of_id = stock_inverse.id) then
        raise exception 'CP7_NOTE_ZERO_EFFECT_RETURN_STOCK_INVERSE_CHANGED';
      end if;
      stock_facts := stock_facts || jsonb_build_array(jsonb_build_array(
        to_jsonb(return_item), to_jsonb(stock_outcome) - 'book_order',
        to_jsonb(stock_inverse) - 'book_order'));
    end loop;
    if jsonb_array_length(stock_facts) = 0 then
      raise exception 'CP7_NOTE_ZERO_EFFECT_RETURN_STOCK_REQUIRED';
    end if;

    facts := facts || jsonb_build_array(jsonb_build_object(
      'family_id', family.id,
      'return_id', original.id,
      'operation_id', materialization.operation_id,
      'profile_fact_sha256', cp7_credit.pg_jsonb_sha256(jsonb_build_array(
        to_jsonb(family), to_jsonb(member), to_jsonb(original), to_jsonb(materialization))),
      'original_journal', original_lines,
      'inverse_journal', inverse_lines,
      'stock_facts_sha256', cp7_credit.pg_jsonb_sha256(stock_facts)));
  end loop;
  if jsonb_array_length(facts) = 0 then
    raise exception 'CP7_NOTE_ZERO_EFFECT_ORDINARY_RETURN_REQUIRED';
  end if;
  return facts;
end
$function$;

alter function cp7_note_zero_effect.ordinary_reversed_history_v1(uuid, uuid, jsonb) owner to postgres;
revoke all on function cp7_note_zero_effect.ordinary_reversed_history_v1(uuid, uuid, jsonb)
  from public, anon, authenticated, service_role;

-- Bound the new ownership route to a price-only note change. The Native
-- command continues to own all actual document, stock and journal writes.
create function cp7_note_zero_effect.price_intent_v1(p_root uuid, p_payload jsonb)
returns jsonb
language plpgsql stable security invoker
set search_path = '' set timezone = 'UTC'
as $function$
declare
  source_header erp.sales_headers;
  source_item erp.sales_items;
  item record;
  source_id uuid;
  line_price numeric;
  lineage jsonb := '[]';
  before_net numeric := 0;
  after_net numeric;
begin
  select * into strict source_header from erp.sales_headers where id = p_root;
  if jsonb_typeof(p_payload->'items') is distinct from 'array'
     or (p_payload ? 'item_lineage'
         and jsonb_typeof(p_payload->'item_lineage') is distinct from 'array') then
    raise exception 'CP7_NOTE_ZERO_EFFECT_PRICE_ONLY_REQUIRED';
  end if;
  if source_header.status is distinct from 'POSTED'
     or (p_payload->>'sale_id', p_payload->>'sale_number',
         (p_payload->>'customer_id')::uuid, (p_payload->>'source_location_id')::uuid,
         (p_payload->>'sale_date')::timestamptz, (p_payload->>'due_date')::date,
         nullif(btrim(p_payload->>'payment_terms'), ''), nullif(btrim(p_payload->>'notes'), ''))
       is distinct from
        (p_root::text, source_header.sale_number, source_header.customer_id, source_header.source_location_id,
         source_header.sale_date, source_header.due_date, nullif(btrim(source_header.payment_terms), ''),
         nullif(btrim(source_header.notes), ''))
     or jsonb_array_length(p_payload->'items') not between 1 and 100
     or jsonb_array_length(p_payload->'items') is distinct from
        (select count(*)::integer from erp.sales_items where sale_id = p_root)
     or (p_payload ? 'item_lineage'
         and jsonb_array_length(p_payload->'item_lineage') is distinct from jsonb_array_length(p_payload->'items')) then
    raise exception 'CP7_NOTE_ZERO_EFFECT_PRICE_ONLY_REQUIRED';
  end if;

  for item in select value, ordinality from jsonb_array_elements(p_payload->'items') with ordinality
  loop
    if p_payload ? 'item_lineage' then
      source_id := (p_payload->'item_lineage'->>(item.ordinality::integer - 1))::uuid;
    else
      -- Exact legacy order used by cp7_note.bind_items for each SKU occurrence.
      select i.id into source_id from erp.sales_items i
      where i.sale_id = p_root and i.product_id = (item.value->>'product_id')::uuid
      order by i.id
      offset (select count(*) - 1 from jsonb_array_elements(p_payload->'items') with ordinality x
              where x.ordinality <= item.ordinality
                and (x.value->>'product_id')::uuid = (item.value->>'product_id')::uuid)
      limit 1;
    end if;
    select * into source_item from erp.sales_items where id = source_id and sale_id = p_root;
    line_price := (item.value->>'unit_price_snapshot')::numeric;
    if source_item.id is null
       or (source_item.product_id, source_item.qty_pcs, source_item.discount_amount,
           nullif(btrim(source_item.notes), ''))
            is distinct from ((item.value->>'product_id')::uuid, (item.value->>'qty_pcs')::integer,
                              (item.value->>'discount_amount')::numeric, nullif(btrim(item.value->>'notes'), ''))
       or line_price is null or line_price::text in ('NaN', 'Infinity', '-Infinity')
       or line_price < 0 or line_price <> round(line_price, 2)
       or line_price * source_item.qty_pcs < source_item.discount_amount then
      raise exception 'CP7_NOTE_ZERO_EFFECT_PRICE_ONLY_REQUIRED';
    end if;
    before_net := before_net + source_item.line_total;
    lineage := lineage || jsonb_build_array(source_id);
  end loop;

  -- Reuse the installed quantity/lineage bijection and amount calculation.
  after_net := cp7_credit_note_carry_de.assert_price_only_v1(
    p_payload || jsonb_build_object('item_lineage', lineage));
  if before_net <= 0 or after_net <= 0 or after_net = before_net then
    raise exception 'CP7_NOTE_ZERO_EFFECT_PRICE_DELTA_REQUIRED';
  end if;
  return jsonb_build_object('before_net', before_net, 'after_net', after_net,
                            'ar_delta', after_net - before_net, 'item_lineage', lineage);
end
$function$;

alter function cp7_note_zero_effect.price_intent_v1(uuid, jsonb) owner to postgres;
revoke all on function cp7_note_zero_effect.price_intent_v1(uuid, jsonb)
  from public, anon, authenticated, service_role;

CREATE OR REPLACE FUNCTION cp7_note_zero_effect.assert_price_effect_v1(p_before jsonb, p_after jsonb, p_original uuid, p_replacement uuid, p_new_net numeric)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare k text;row_value jsonb;next_value jsonb;item record;old_alloc jsonb;new_alloc jsonb;old_j erp.journal_entries;
 inverse erp.journal_entries;new_j erp.journal_entries;statement_row cp7_note.journal_restatements;old_ar jsonb;new_ar jsonb;
 old_lines jsonb;new_lines jsonb;old_sales uuid;revenue uuid;ar uuid;before_moves jsonb;added_moves jsonb;old_move jsonb;back jsonb;fresh jsonb;
begin
 old_ar:=cp7_credit.consumer_invoice_ar_source_v1(p_original);new_ar:=cp7_credit.consumer_invoice_ar_source_v1(p_replacement);
 if(old_ar->>'customer_id',old_ar->>'account_id')is distinct from(new_ar->>'customer_id',new_ar->>'account_id')
  or(new_ar->>'gross_amount')::numeric is distinct from p_new_net then raise exception 'CP7_CREDIT_NOTE_CARRY_ACTUAL_AR_SOURCE_CHANGED';end if;
 ar:=(old_ar->>'account_id')::uuid;revenue:=cp7_credit.account_by_mapping_v1('SALES_REVENUE');
 select *into strict old_j from erp.journal_entries where id=(old_ar->>'sale_journal_id')::uuid;
 select *into strict new_j from erp.journal_entries where id=(new_ar->>'sale_journal_id')::uuid;
 select *into strict inverse from erp.journal_entries where source_type='JOURNAL_REVERSAL'and source_id=old_j.id and reversal_of_id=old_j.id;
 if old_j.status<>'REVERSED'or inverse.status<>'POSTED'or new_j.status<>'POSTED'
  or(new_j.economic_date,new_j.transaction_date)is distinct from(old_j.economic_date,old_j.transaction_date)
  or inverse.economic_date<old_j.economic_date or inverse.transaction_date<old_j.transaction_date
  or cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(inverse.id)->'lines')is distinct from
   cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(old_j.id)->'lines',true)then raise exception 'CP7_CREDIT_NOTE_CARRY_NATIVE_INVERSE_CHANGED';end if;
 select *into statement_row from cp7_note.journal_restatements where source_journal_id=old_j.id;
 if inverse.economic_date<>old_j.economic_date then
  if(statement_row.inverse_journal_id,statement_row.previous_sale_id,statement_row.native_economic_date,statement_row.corrected_economic_date)is distinct from
   (inverse.id,p_original,inverse.economic_date,old_j.economic_date)
   or not exists(select 1 from erp.journal_entries n join erp.journal_entries e on e.id=statement_row.effective_journal_id
    where n.id=statement_row.neutral_journal_id and(n.source_type,n.source_id,n.economic_date,n.transaction_date,n.status)is not distinct from
     ('NOTE_REVERSAL_TIME_NEUTRAL',inverse.id,inverse.economic_date,inverse.transaction_date,'POSTED')
     and(e.source_type,e.source_id,e.economic_date,e.transaction_date,e.status)is not distinct from('NOTE_REVERSAL_EFFECTIVE',inverse.id,old_j.economic_date,old_j.transaction_date,'POSTED'))
   or cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(statement_row.neutral_journal_id)->'lines')is distinct from
    cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(inverse.id)->'lines',true)
   or cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(statement_row.effective_journal_id)->'lines')is distinct from
    cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(inverse.id)->'lines')then raise exception 'CP7_CREDIT_NOTE_CARRY_RESTATEMENT_CHANGED';end if;
 elsif statement_row.inverse_journal_id is not null then raise exception 'CP7_CREDIT_NOTE_CARRY_UNEXPECTED_RESTATEMENT';end if;
 -- Native still creates every line. Prove the price-only delta and preserve
 -- each cost dimension/sign; no aggregate can hide a changed HPP mapping.
 select coalesce(jsonb_agg(v),'[]')into old_lines from jsonb_array_elements(cp7_credit.materialized_journal_payload(old_j.id)->'lines')v where(v->>'account_id')::uuid not in(ar,revenue);
 select coalesce(jsonb_agg(v),'[]')into new_lines from jsonb_array_elements(cp7_credit.materialized_journal_payload(new_j.id)->'lines')v where(v->>'account_id')::uuid not in(ar,revenue);
 if cp7_credit.source_inverse_vector_v1(old_lines)is distinct from cp7_credit.source_inverse_vector_v1(new_lines)
  or not exists(select 1 from erp.journal_lines where journal_entry_id=new_j.id and account_id=revenue and credit=p_new_net and debit=0
    and customer_id=(new_ar->>'customer_id')::uuid and vendor_id is null and contractor_id is null and product_id is null and po_id is null)
  or(select count(*)from erp.journal_lines where journal_entry_id=new_j.id and account_id=revenue)<>1 then raise exception 'CP7_CREDIT_NOTE_CARRY_PRICE_HPP_VECTOR_CHANGED';end if;
 foreach k in array array['fg_lots','hpp_versions','opening_hpp_states','opening_hpp_corrections','po_hpp_states','nonpo_hpp_events','po_hpp_events','hpp_balances','hpp_accounts','period_snapshot']loop
  if p_before->k is not distinct from p_after->k then continue;end if;
  if k='po_hpp_states' and jsonb_typeof(p_before->k)='array' and jsonb_typeof(p_after->k)='array' then
   -- Native reverse/repost refreshes only this state's maintenance timestamp.
   -- Keep PO identity, row order, every quantity and amount, and other HPP evidence exact.
   if not exists (
       select 1 from jsonb_array_elements((p_before->k)||(p_after->k)) r
       where jsonb_typeof(r) is distinct from 'object'
          or jsonb_typeof(r->'updated_at') is distinct from 'string'
          or not pg_input_is_valid(r->>'updated_at','timestamp with time zone')
      )
      and (select jsonb_agg(r-'updated_at' order by n) from jsonb_array_elements(p_before->k) with ordinality x(r,n))
       is not distinct from
          (select jsonb_agg(r-'updated_at' order by n) from jsonb_array_elements(p_after->k) with ordinality x(r,n)) then
    continue;
   end if;
  end if;
  raise exception 'CP7_CREDIT_NOTE_CARRY_UNQUALIFIED_NATIVE_DELTA:%',k;
 end loop;
 if exists(select 1 from erp.sales_payments where sale_id in(p_original,p_replacement))or exists(select 1 from erp.sales_returns where sale_id=p_replacement or(sale_id=p_original and status is distinct from 'REVERSED'))then
  raise exception 'CP7_CREDIT_NOTE_CARRY_CHILD_REPLAY_ADAPTER_REQUIRED';end if;
 for item in select l.previous_item_id,l.replacement_item_id from cp7_note.item_lineage l where l.correction_id=(select id from cp7_note.revisions where previous_sale_id=p_original and replacement_sale_id=p_replacement)loop
  select cp7_credit.source_rows_v1(coalesce(jsonb_agg(to_jsonb(a)-array['id','sale_item_id']),'[]'))into old_alloc from erp.sale_stock_allocations a where sale_item_id=item.previous_item_id;
  select cp7_credit.source_rows_v1(coalesce(jsonb_agg(to_jsonb(a)-array['id','sale_item_id']),'[]'))into new_alloc from erp.sale_stock_allocations a where sale_item_id=item.replacement_item_id;
  if old_alloc is distinct from new_alloc then raise exception 'CP7_CREDIT_NOTE_CARRY_ALLOCATION_HPP_CHANGED';end if;
 end loop;
 before_moves:=p_before->'stock_movements';
 for row_value in select value from jsonb_array_elements(before_moves)loop
  if not exists(select 1 from jsonb_array_elements(p_after->'stock_movements')v where v=row_value)then raise exception 'CP7_CREDIT_NOTE_CARRY_ORIGINAL_MOVEMENT_CHANGED';end if;
 end loop;
 select coalesce(jsonb_agg(v),'[]')into added_moves from jsonb_array_elements(p_after->'stock_movements')v where not exists(select 1 from jsonb_array_elements(before_moves)o where o->>'id'=v->>'id');
 for old_move in select value from jsonb_array_elements(before_moves)where value->>'source_type'='SALE_ITEM'and value->>'movement_type'='SALE'
  and exists(select 1 from erp.sales_items i where i.id=(value->>'source_id')::uuid and i.sale_id=p_original)loop
  select v into strict back from jsonb_array_elements(added_moves)v where v->>'reversal_of_id'=old_move->>'id';
  select v into strict fresh from jsonb_array_elements(added_moves)v where v->>'source_type'='SALE_ITEM'and v->>'movement_type'='SALE'and v->>'reversal_of_id'is null
   and v->>'source_id'=(select l.replacement_item_id::text from cp7_note.item_lineage l where l.previous_item_id=(old_move->>'source_id')::uuid)
   and v->>'lot_id'is not distinct from old_move->>'lot_id'and v->>'location_id'=old_move->>'location_id';
  if(back->>'product_id',back->>'lot_id',back->>'location_id',back->>'quality_grade',(back->>'qty_signed')::numeric,(back->>'unit_hpp_snapshot')::numeric,(back->>'physical_at')::timestamptz) is distinct from
   (old_move->>'product_id',old_move->>'lot_id',old_move->>'location_id',old_move->>'quality_grade',-(old_move->>'qty_signed')::numeric,(old_move->>'unit_hpp_snapshot')::numeric,(old_move->>'physical_at')::timestamptz)
   or(fresh->>'product_id',fresh->>'lot_id',fresh->>'location_id',fresh->>'quality_grade',(fresh->>'qty_signed')::numeric,(fresh->>'unit_hpp_snapshot')::numeric,(fresh->>'physical_at')::timestamptz) is distinct from
   (old_move->>'product_id',old_move->>'lot_id',old_move->>'location_id',old_move->>'quality_grade',(old_move->>'qty_signed')::numeric,(old_move->>'unit_hpp_snapshot')::numeric,(old_move->>'physical_at')::timestamptz)then
   raise exception 'CP7_CREDIT_NOTE_CARRY_PHYSICAL_BIJECTION_CHANGED';end if;
 end loop;
 if jsonb_array_length(added_moves)<>2*(select count(*)from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=p_original)then
  raise exception 'CP7_CREDIT_NOTE_CARRY_EXTRA_STOCK_EFFECT';end if;
 for row_value in select value from jsonb_array_elements(p_before->'inventory_balances')loop
  select v into strict next_value from jsonb_array_elements(p_after->'inventory_balances')v where(v->>'product_id',v->>'location_id',v->>'quality_grade')=
   (row_value->>'product_id',row_value->>'location_id',row_value->>'quality_grade');
  if row_value-'updated_at'is distinct from next_value-'updated_at'then raise exception 'CP7_CREDIT_NOTE_CARRY_INVENTORY_FINAL_DELTA';end if;
 end loop;
 if jsonb_array_length(p_before->'inventory_balances')<>jsonb_array_length(p_after->'inventory_balances')then raise exception 'CP7_CREDIT_NOTE_CARRY_INVENTORY_SET_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.note-ordinary-zero-effect-price-delta.v1','original_document',cp7_credit_note_carry_de.raw_document_v1(p_original),
  'replacement_document',cp7_credit_note_carry_de.raw_document_v1(p_replacement),'original_journal',cp7_credit.materialized_journal_payload(old_j.id),
  'inverse_journal',cp7_credit.materialized_journal_payload(inverse.id),'replacement_journal',cp7_credit.materialized_journal_payload(new_j.id),
  'restatement',to_jsonb(statement_row),'no_consumer_money_created',true,'same_physical_and_HPP',true);
end $function$;
alter function cp7_note_zero_effect.assert_price_effect_v1(jsonb,jsonb,uuid,uuid,numeric) owner to postgres;
revoke all on function cp7_note_zero_effect.assert_price_effect_v1(jsonb,jsonb,uuid,uuid,numeric) from public, anon, authenticated, service_role;

-- Private ownership and closure receipt for the ordinary reversed-return
-- correction route. Install after 01_ordinary_reversed_history.sql,
-- 02_price_intent.sql and the exact derived price-effect verifier.
--
-- No object in this schema is a client API. The owning cp7_note.command is
-- the only writer, and every successful preparation/completion is append-only.

create table cp7_note_zero_effect.preparations (
  actor uuid not null,
  request_id uuid not null,
  correction_id uuid not null,
  root_sale_id uuid not null,
  previous_sale_id uuid not null,
  expected_version text not null,
  native_review_token text not null,
  request_payload_sha256 text not null,
  access_sha256 text not null,
  graph_sha256 text not null,
  source_profile_sha256 text not null,
  return_facts_sha256 text not null,
  price_intent jsonb not null,
  access_snapshot jsonb not null,
  source_graph jsonb not null,
  source_profile jsonb not null,
  return_facts jsonb not null,
  before_snapshot jsonb not null,
  prepared_at timestamptz not null default clock_timestamp(),
  primary key (actor, request_id),
  unique (correction_id),
  check (expected_version ~ '^[1-9][0-9]{0,18}$'),
  check (native_review_token ~ '^[0-9a-f]{32}$'),
  check (request_payload_sha256 ~ '^[0-9a-f]{64}$'),
  check (access_sha256 ~ '^[0-9a-f]{64}$'),
  check (graph_sha256 ~ '^[0-9a-f]{64}$'),
  check (source_profile_sha256 ~ '^[0-9a-f]{64}$'),
  check (return_facts_sha256 ~ '^[0-9a-f]{64}$'),
  check (jsonb_typeof(return_facts) = 'array' and jsonb_array_length(return_facts) > 0),
  check (price_intent->>'before_net' is not null and price_intent->>'after_net' is not null)
);

create table cp7_note_zero_effect.receipts (
  actor uuid not null,
  request_id uuid not null,
  correction_id uuid not null,
  root_sale_id uuid not null,
  previous_sale_id uuid not null,
  replacement_sale_id uuid not null,
  result_sha256 text not null,
  current_graph_sha256 text not null,
  current_profile_sha256 text not null,
  return_facts_sha256 text not null,
  effect_sha256 text not null,
  result jsonb not null,
  current_graph jsonb not null,
  current_profile jsonb not null,
  effect_proof jsonb not null,
  completed_at timestamptz not null default clock_timestamp(),
  primary key (actor, request_id),
  unique (correction_id),
  unique (root_sale_id, replacement_sale_id),
  foreign key (actor, request_id) references cp7_note_zero_effect.preparations(actor, request_id),
  check (result_sha256 ~ '^[0-9a-f]{64}$'),
  check (current_graph_sha256 ~ '^[0-9a-f]{64}$'),
  check (current_profile_sha256 ~ '^[0-9a-f]{64}$'),
  check (return_facts_sha256 ~ '^[0-9a-f]{64}$'),
  check (effect_sha256 ~ '^[0-9a-f]{64}$')
);

alter table cp7_note_zero_effect.preparations owner to postgres;
alter table cp7_note_zero_effect.receipts owner to postgres;
revoke all on cp7_note_zero_effect.preparations from public, anon, authenticated, service_role;
revoke all on cp7_note_zero_effect.receipts from public, anon, authenticated, service_role;
alter table cp7_note_zero_effect.preparations enable row level security;
alter table cp7_note_zero_effect.preparations force row level security;
alter table cp7_note_zero_effect.receipts enable row level security;
alter table cp7_note_zero_effect.receipts force row level security;

create function cp7_note_zero_effect.reject_receipt_mutation_v1()
returns trigger
language plpgsql security invoker
set search_path = ''
as $function$
begin
  raise exception 'CP7_NOTE_ZERO_EFFECT_RECEIPT_IMMUTABLE';
end
$function$;

alter function cp7_note_zero_effect.reject_receipt_mutation_v1() owner to postgres;
revoke all on function cp7_note_zero_effect.reject_receipt_mutation_v1()
  from public, anon, authenticated, service_role;

create trigger cp7_note_zero_effect_preparations_immutable
before update or delete on cp7_note_zero_effect.preparations
for each row execute function cp7_note_zero_effect.reject_receipt_mutation_v1();

create trigger cp7_note_zero_effect_receipts_immutable
before update or delete on cp7_note_zero_effect.receipts
for each row execute function cp7_note_zero_effect.reject_receipt_mutation_v1();

create function cp7_note_zero_effect.prepare_v1(
  p_payload jsonb,
  p_request uuid,
  p_expected text,
  p_correction uuid,
  p_access jsonb
)
returns jsonb
language plpgsql volatile security definer
-- Native review tokens and access must be recomputed in the calling note context.
set search_path = ''
as $function$
declare
  leaf uuid := (p_payload->>'sale_id')::uuid;
  root uuid;
  header erp.sales_headers;
  profile jsonb;
  graph jsonb;
  return_facts jsonb;
  price_intent jsonb;
  before_snapshot jsonb;
  native_token text;
  stored cp7_note_zero_effect.preparations;
begin
  if p_request is null or p_correction is null or p_access is null
     or p_expected is null or p_expected !~ '^[1-9][0-9]{0,18}$' then
    raise exception 'CP7_NOTE_ZERO_EFFECT_PREPARATION_REQUIRED';
  end if;

  select coalesce((select r.root_sale_id from cp7_note.revisions r
                    where r.replacement_sale_id = leaf), leaf)
    into root;

  -- Preserve every established E and flat path. This adapter only owns an
  -- ordinary coordinator return which has already been fully reversed.
  if cp7_credit_note_carry_de.has_root_v1(root)
     or not exists (
       select 1
       from cp7_credit.initial_return_materializations m
       join erp.sales_returns r on r.id = m.source_return_id
       where m.source_sale_id = root and m.origin = 'ORDINARY'
         and r.sale_id = root and r.status = 'REVERSED'
     ) then
    return null;
  end if;

  select * into strict header from erp.sales_headers where id = leaf for key share;
  native_token := cp7_sales.review_token(leaf);
  if header.status not in ('POSTED','PARTIAL_PAID','PAID')
     or header.row_version::text is distinct from p_expected
     or native_token is distinct from p_payload->>'review_token'
     or cp7_note.access_now() is distinct from p_access then
    raise exception 'CP7_NOTE_ZERO_EFFECT_REVIEW_CHANGED';
  end if;

  profile := cp7_credit.current_materialized_objects(leaf, root, leaf);
  return_facts := cp7_note_zero_effect.ordinary_reversed_history_v1(root, leaf, profile);
  price_intent := cp7_note_zero_effect.price_intent_v1(leaf, p_payload);
  graph := cp7_credit.consumer_joined_graph_v1(root, leaf);
  if graph->>'customer_id' is distinct from header.customer_id::text
     or jsonb_typeof(graph->'sale_ids') is distinct from 'array'
     or not (graph->'sale_ids' @> jsonb_build_array(root::text, leaf::text)) then
    raise exception 'CP7_NOTE_ZERO_EFFECT_GRAPH_CHANGED';
  end if;
  before_snapshot := cp7_credit_note_carry_de.raw_native_snapshot_v1(leaf);

  insert into cp7_note_zero_effect.preparations(
    actor, request_id, correction_id, root_sale_id, previous_sale_id,
    expected_version, native_review_token, request_payload_sha256,
    access_sha256, graph_sha256, source_profile_sha256, return_facts_sha256,
    price_intent, access_snapshot, source_graph, source_profile,
    return_facts, before_snapshot)
  values (
    auth.uid(), p_request, p_correction, root, leaf,
    p_expected, native_token, cp7_credit.pg_jsonb_sha256(p_payload),
    cp7_credit.pg_jsonb_sha256(p_access), cp7_credit.pg_jsonb_sha256(graph),
    cp7_credit.pg_jsonb_sha256(profile), cp7_credit.pg_jsonb_sha256(return_facts),
    price_intent, p_access, graph, profile, return_facts, before_snapshot)
  on conflict do nothing;

  select * into strict stored from cp7_note_zero_effect.preparations
    where actor = auth.uid() and request_id = p_request;
  if (stored.correction_id, stored.root_sale_id, stored.previous_sale_id,
      stored.expected_version, stored.native_review_token,
      stored.request_payload_sha256, stored.access_sha256,
      stored.graph_sha256, stored.source_profile_sha256,
      stored.return_facts_sha256)
     is distinct from
     (p_correction, root, leaf, p_expected, native_token,
      cp7_credit.pg_jsonb_sha256(p_payload), cp7_credit.pg_jsonb_sha256(p_access),
      cp7_credit.pg_jsonb_sha256(graph), cp7_credit.pg_jsonb_sha256(profile),
      cp7_credit.pg_jsonb_sha256(return_facts)) then
    raise exception 'CP7_NOTE_ZERO_EFFECT_PREPARATION_CHANGED';
  end if;

  return jsonb_build_object(
    'contract_version', 'cp7.note-ordinary-zero-effect-preparation.v1',
    'actor', auth.uid(), 'request_id', p_request,
    'correction_id', p_correction, 'root_sale_id', root,
    'previous_sale_id', leaf, 'backend_pid', pg_backend_pid(),
    'transaction_id', txid_current()::text,
    'request_payload_sha256', stored.request_payload_sha256,
    'return_facts_sha256', stored.return_facts_sha256);
end
$function$;

alter function cp7_note_zero_effect.prepare_v1(jsonb,uuid,text,uuid,jsonb) owner to postgres;
revoke all on function cp7_note_zero_effect.prepare_v1(jsonb,uuid,text,uuid,jsonb)
  from public, anon, authenticated, service_role;

create function cp7_note_zero_effect.finish_v1(p_proof jsonb, p_result jsonb)
returns void
language plpgsql volatile security definer
-- Compare access in the same calling context used by preparation.
set search_path = ''
as $function$
declare
  prep cp7_note_zero_effect.preparations;
  request_row cp7_note.requests;
  revision_row cp7_note.revisions;
  replacement erp.sales_headers;
  v_current_profile jsonb;
  v_current_graph jsonb;
  current_return_facts jsonb;
  after_snapshot jsonb;
  v_effect jsonb;
begin
  if p_proof->>'contract_version' is distinct from 'cp7.note-ordinary-zero-effect-preparation.v1'
     or (p_proof->>'actor')::uuid is distinct from auth.uid()
     or (p_proof->>'backend_pid')::integer is distinct from pg_backend_pid()
     or p_proof->>'transaction_id' is distinct from txid_current()::text then
    raise exception 'CP7_NOTE_ZERO_EFFECT_PREPARATION_SCOPE_CHANGED';
  end if;

  select * into strict prep from cp7_note_zero_effect.preparations
    where actor = auth.uid() and request_id = (p_proof->>'request_id')::uuid
    for key share;
  if (prep.correction_id, prep.root_sale_id, prep.previous_sale_id,
      prep.request_payload_sha256, prep.return_facts_sha256)
     is distinct from
     ((p_proof->>'correction_id')::uuid, (p_proof->>'root_sale_id')::uuid,
      (p_proof->>'previous_sale_id')::uuid, p_proof->>'request_payload_sha256',
      p_proof->>'return_facts_sha256') then
    raise exception 'CP7_NOTE_ZERO_EFFECT_PREPARATION_CHANGED';
  end if;

  select * into strict request_row from cp7_note.requests
    where actor = prep.actor and request_id = prep.request_id;
  select * into strict revision_row from cp7_note.revisions where id = prep.correction_id;
  if request_row.expected_version is distinct from prep.expected_version
     or request_row.response is distinct from p_result
     or cp7_credit.pg_jsonb_sha256(request_row.payload) is distinct from prep.request_payload_sha256
     or (p_result->>'contract_version', p_result->>'kind', p_result->>'action')
        is distinct from ('cp7.note-correction-outcome.v1', 'COMMITTED_OUTCOME', 'CORRECT')
     or (revision_row.root_sale_id, revision_row.previous_sale_id,
         revision_row.replacement_sale_id, revision_row.actor, revision_row.request_id)
        is distinct from
        (prep.root_sale_id, prep.previous_sale_id, (p_result->>'sale_id')::uuid,
         prep.actor, prep.request_id)
     or (p_result->>'root_sale_id', p_result->>'previous_sale_id',
         p_result->>'revision_id', p_result->>'request_id')
        is distinct from
        (prep.root_sale_id::text, prep.previous_sale_id::text,
         prep.correction_id::text, prep.request_id::text) then
    raise exception 'CP7_NOTE_ZERO_EFFECT_FINAL_RECEIPT_CHANGED';
  end if;

  select * into strict replacement from erp.sales_headers
    where id = revision_row.replacement_sale_id for key share;
  if replacement.status not in ('POSTED','PARTIAL_PAID','PAID')
     or cp7_note.access_now() is distinct from prep.access_snapshot then
    raise exception 'CP7_NOTE_ZERO_EFFECT_FINAL_STATE_CHANGED';
  end if;

  after_snapshot := cp7_credit_note_carry_de.raw_native_snapshot_v1(replacement.id);
  v_effect := cp7_note_zero_effect.assert_price_effect_v1(
    prep.before_snapshot, after_snapshot, prep.previous_sale_id,
    replacement.id, (prep.price_intent->>'after_net')::numeric);
  -- The paid and deferred closure readers verify the complete inspected profile.
  v_current_profile := cp7_credit.inspect_current_materialized_profile(
    replacement.id, prep.root_sale_id, replacement.id);
  current_return_facts := cp7_note_zero_effect.ordinary_reversed_history_v1(
    prep.root_sale_id, replacement.id, v_current_profile);
  if cp7_credit.pg_jsonb_sha256(current_return_facts) is distinct from prep.return_facts_sha256 then
    raise exception 'CP7_NOTE_ZERO_EFFECT_RETURN_HISTORY_CHANGED';
  end if;
  v_current_graph := cp7_credit.consumer_joined_graph_v1(prep.root_sale_id, replacement.id);
  if v_current_graph->>'customer_id' is distinct from replacement.customer_id::text
     or not (v_current_graph->'sale_ids' @> jsonb_build_array(
       prep.root_sale_id::text, prep.previous_sale_id::text, replacement.id::text)) then
    raise exception 'CP7_NOTE_ZERO_EFFECT_GRAPH_CHANGED';
  end if;

  insert into cp7_note_zero_effect.receipts(
    actor, request_id, correction_id, root_sale_id, previous_sale_id,
    replacement_sale_id, result_sha256, current_graph_sha256,
    current_profile_sha256, return_facts_sha256, effect_sha256,
    result, current_graph, current_profile, effect_proof)
  values (
    prep.actor, prep.request_id, prep.correction_id, prep.root_sale_id,
    prep.previous_sale_id, replacement.id, cp7_credit.pg_jsonb_sha256(p_result),
    cp7_credit.pg_jsonb_sha256(v_current_graph), cp7_credit.pg_jsonb_sha256(v_current_profile),
    prep.return_facts_sha256, cp7_credit.pg_jsonb_sha256(v_effect),
    p_result, v_current_graph, v_current_profile, v_effect)
  on conflict do nothing;

  if not exists (
    select 1 from cp7_note_zero_effect.receipts r
    where r.actor = prep.actor and r.request_id = prep.request_id
      and (r.correction_id, r.root_sale_id, r.previous_sale_id, r.replacement_sale_id,
           r.result_sha256, r.current_graph_sha256, r.current_profile_sha256,
           r.return_facts_sha256, r.effect_sha256)
          is not distinct from
          (prep.correction_id, prep.root_sale_id, prep.previous_sale_id, replacement.id,
           cp7_credit.pg_jsonb_sha256(p_result), cp7_credit.pg_jsonb_sha256(v_current_graph),
           cp7_credit.pg_jsonb_sha256(v_current_profile), prep.return_facts_sha256,
           cp7_credit.pg_jsonb_sha256(v_effect))
  ) then
    raise exception 'CP7_NOTE_ZERO_EFFECT_FINAL_RECEIPT_CHANGED';
  end if;
end
$function$;

alter function cp7_note_zero_effect.finish_v1(jsonb,jsonb) owner to postgres;
revoke all on function cp7_note_zero_effect.finish_v1(jsonb,jsonb)
  from public, anon, authenticated, service_role;

create function cp7_note_zero_effect.has_owned_root_v1(p_root uuid)
returns boolean
language sql stable security definer
set search_path = '' set timezone = 'UTC'
as $function$
  select exists (
    select 1
    from cp7_note_zero_effect.receipts r
    join cp7_note.revisions v on v.id = r.correction_id
    join erp.sales_headers h on h.id = r.replacement_sale_id
    where r.root_sale_id = p_root
      and (v.root_sale_id, v.previous_sale_id, v.replacement_sale_id,
           v.actor, v.request_id)
          is not distinct from
          (r.root_sale_id, r.previous_sale_id, r.replacement_sale_id,
           r.actor, r.request_id)
      and h.status in ('POSTED','PARTIAL_PAID','PAID')
      and not exists (select 1 from cp7_note.revisions n
                      where n.previous_sale_id = r.replacement_sale_id)
  )
$function$;

alter function cp7_note_zero_effect.has_owned_root_v1(uuid) owner to postgres;
revoke all on function cp7_note_zero_effect.has_owned_root_v1(uuid)
  from public, anon, authenticated, service_role;

create function cp7_note_zero_effect.assert_owned_profile_v1(
  p_sale uuid, p_root uuid, p_leaf uuid, p_actual jsonb)
returns void
language plpgsql stable security definer
set search_path = '' set timezone = 'UTC'
as $function$
declare
  receipt cp7_note_zero_effect.receipts;
  prep cp7_note_zero_effect.preparations;
  facts jsonb;
begin
  select * into strict receipt from cp7_note_zero_effect.receipts r
    where r.root_sale_id = p_root and r.replacement_sale_id = p_leaf
      and not exists (select 1 from cp7_note.revisions n
                      where n.previous_sale_id = r.replacement_sale_id);
  select * into strict prep from cp7_note_zero_effect.preparations
    where actor = receipt.actor and request_id = receipt.request_id;
  if (p_sale, p_root, p_leaf) is distinct from
       (receipt.replacement_sale_id, receipt.root_sale_id, receipt.replacement_sale_id)
     or (p_actual->>'sale_id', p_actual->>'root_sale_id', p_actual->>'current_leaf_id')
        is distinct from (p_sale::text, p_root::text, p_leaf::text)
     or cp7_credit.pg_jsonb_sha256(p_actual) is distinct from receipt.current_profile_sha256
     or not exists (
       select 1 from cp7_note.requests q
       where q.actor = receipt.actor and q.request_id = receipt.request_id
         and q.response is not distinct from receipt.result
         and cp7_credit.pg_jsonb_sha256(q.payload) = prep.request_payload_sha256)
     or not exists (
       select 1 from cp7_note.revisions v
       where v.id = receipt.correction_id
         and (v.root_sale_id, v.previous_sale_id, v.replacement_sale_id,
              v.actor, v.request_id)
             is not distinct from
             (receipt.root_sale_id, receipt.previous_sale_id,
              receipt.replacement_sale_id, receipt.actor, receipt.request_id)) then
    raise exception 'CP7_NOTE_ZERO_EFFECT_OWNED_PROFILE_CHANGED';
  end if;
  facts := cp7_note_zero_effect.ordinary_reversed_history_v1(p_root, p_leaf, p_actual);
  if cp7_credit.pg_jsonb_sha256(facts) is distinct from receipt.return_facts_sha256
     or cp7_credit.pg_jsonb_sha256(facts) is distinct from prep.return_facts_sha256 then
    raise exception 'CP7_NOTE_ZERO_EFFECT_RETURN_HISTORY_CHANGED';
  end if;
end
$function$;

alter function cp7_note_zero_effect.assert_owned_profile_v1(uuid,uuid,uuid,jsonb) owner to postgres;
revoke all on function cp7_note_zero_effect.assert_owned_profile_v1(uuid,uuid,uuid,jsonb)
  from public, anon, authenticated, service_role;

create function cp7_note_zero_effect.owned_leaf_for_return_v1(
  p_root uuid, p_operation uuid)
returns uuid
language plpgsql stable security definer
set search_path = '' set timezone = 'UTC'
as $function$
declare
  leaf uuid;
begin
  select r.replacement_sale_id into leaf
  from cp7_note_zero_effect.receipts r
  join cp7_note_zero_effect.preparations p
    on p.actor = r.actor and p.request_id = r.request_id
  join cp7_note.revisions v on v.id = r.correction_id
  join cp7_note.requests q on q.actor = r.actor and q.request_id = r.request_id
  join erp.sales_headers h on h.id = r.replacement_sale_id
  where r.root_sale_id = p_root
    and h.status in ('POSTED','PARTIAL_PAID','PAID')
    and (v.root_sale_id, v.previous_sale_id, v.replacement_sale_id,
         v.actor, v.request_id)
        is not distinct from
        (r.root_sale_id, r.previous_sale_id, r.replacement_sale_id,
         r.actor, r.request_id)
    and q.response is not distinct from r.result
    and cp7_credit.pg_jsonb_sha256(q.payload) = p.request_payload_sha256
    and cp7_credit.pg_jsonb_sha256(r.result) = r.result_sha256
    and exists (select 1 from jsonb_array_elements(p.return_facts) f
                where f->>'operation_id' = p_operation::text)
    and not exists (select 1 from cp7_note.revisions n
                    where n.previous_sale_id = r.replacement_sale_id);
  return leaf;
end
$function$;

alter function cp7_note_zero_effect.owned_leaf_for_return_v1(uuid,uuid) owner to postgres;
revoke all on function cp7_note_zero_effect.owned_leaf_for_return_v1(uuid,uuid)
  from public, anon, authenticated, service_role;

CREATE OR REPLACE FUNCTION cp7_note.command(p_payload jsonb, p_request uuid, p_expected text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare a jsonb;old cp7_note.requests%rowtype;h erp.sales_headers%rowtype;root uuid;leaf uuid;
 revision bigint;replaced uuid;native_request uuid;result jsonb;draft jsonb;line jsonb;payment record;returned record;
 paid jsonb;returns jsonb;returned_lines jsonb;new_payment uuid;new_return uuid;new_return_item uuid;allocation uuid;
 return_lineage jsonb:='{}'::jsonb;
 zero_effect_proof jsonb;
 correction_id uuid:=gen_random_uuid();before_movements uuid[];origin record;new_move record;anchor uuid;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_note.access_now();perform cp7_sales.validate_draft(p_payload-'item_lineage',true);
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'then raise exception 'CP7_NOTE_REQUEST_REQUIRED';end if;
 insert into cp7_note.requests values(auth.uid(),p_request,p_payload,p_expected,null)on conflict do nothing;
 select *into strict old from cp7_note.requests where actor=auth.uid()and request_id=p_request for update;
 if old.payload is distinct from p_payload or old.expected_version is distinct from p_expected then raise exception 'CP7_NOTE_REQUEST_CHANGED';end if;
 if cp7_note.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_NOTE_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 perform cp7_mandor_shop.sale_change_preflight('CORRECT',(p_payload->>'sale_id')::uuid);
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform pg_advisory_xact_lock(hashtextextended('FGBOOK|GLOBAL',0));
 if cp7_note.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_NOTE_ACCESS_CHANGED';end if;
 leaf:=(p_payload->>'sale_id')::uuid;
 perform 1 from erp.sales_payments where sale_id=leaf order by id for update;
 perform 1 from erp.sales_returns where sale_id=leaf order by id for update;
 select *into h from erp.sales_headers where id=leaf for update;
 if h.id is null or h.status not in('POSTED','PARTIAL_PAID','PAID')then raise exception 'CP7_NOTE_ACTIVE_POSTED_ONLY';end if;
 if h.row_version::text<>p_expected or cp7_sales.review_token(h.id)<>p_payload->>'review_token'then raise exception 'CP7_NOTE_REVIEW_CHANGED';end if;
 -- Historical correction keeps the actual original event identity/time.
 if p_payload->>'sale_number'is distinct from h.sale_number
  or(p_payload->>'sale_date')::timestamptz is distinct from h.sale_date
  or(p_payload->>'customer_id')::uuid is distinct from h.customer_id
  or(p_payload->>'source_location_id')::uuid is distinct from h.source_location_id then raise exception 'CP7_NOTE_SOURCE_IDENTITY_CHANGED';end if;
 select root_sale_id into root from cp7_note.revisions where replacement_sale_id=leaf;
 root:=coalesce(root,leaf);
 select coalesce(max(r.revision),0)+1 into revision from cp7_note.revisions r where r.root_sale_id=root;
 if exists(select 1 from cp7_note.revisions where previous_sale_id=leaf)then raise exception 'CP7_NOTE_SOURCE_SUPERSEDED';end if;
 if exists(select 1 from erp.sales_payments where sale_id=leaf and status='DRAFT')
  or exists(select 1 from erp.sales_returns where sale_id=leaf and status='DRAFT')then
  raise exception 'CP7_NOTE_PENDING_CHILD_REVIEW_REQUIRED';end if;
 -- A native cash reallocation is journaled at its predecessor's reversal date.
 -- Replaying it here would move that cash back to the original receipt clock;
 -- like payment correction, such a payment stays outside this command.
 if exists(select 1 from erp.sales_payments where sale_id=leaf and status='POSTED'and replaces_payment_id is not null)then
  raise exception 'CP7_NOTE_REALLOCATED_PAYMENT_REVIEW_REQUIRED';end if;
 select coalesce(jsonb_agg(to_jsonb(p)||jsonb_build_object('advance_id',l.advance_id)order by p.payment_date,p.id),'[]')into paid
 from erp.sales_payments p left join erp.initial_import_prepayment_payments l on l.payment_id=p.id
 where p.sale_id=leaf and p.status='POSTED';
 select coalesce(jsonb_agg(to_jsonb(r)||jsonb_build_object('items',
  (select jsonb_agg(to_jsonb(i)||jsonb_build_object('allocation_location_id',x.location_id)order by i.id)
    from erp.sales_return_items i join erp.sale_stock_allocations x on x.id=i.sale_stock_allocation_id where i.return_id=r.id))order by r.physical_at,r.id),'[]')into returns
 from erp.sales_returns r where r.sale_id=leaf and r.status='POSTED';
 select array_agg(m.id)into before_movements from erp.fg_stock_movements m where
  (m.source_type='SALE_ITEM'and exists(select 1 from erp.sales_items i where i.id=m.source_id and i.sale_id=leaf)
   or m.source_type='SALES_RETURN_ITEM'and exists(select 1 from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where i.id=m.source_id and r.sale_id=leaf and r.status='POSTED'))
  and m.movement_type in('SALE','SALE_RETURN')and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id);
 zero_effect_proof:=cp7_note_zero_effect.prepare_v1(p_payload,p_request,p_expected,correction_id,a);
 insert into cp7_note.context values(pg_backend_pid(),txid_current(),auth.uid(),leaf);
 insert into cp7_sales.command_context values(pg_backend_pid(),txid_current(),auth.uid(),leaf,'SALE_REVERSE');
 perform set_config('app.change_reason',p_payload->>'change_reason',true);
 -- D15-1 / Sol SOL-R1-001: the cash guard judges the end state of inverse + replacement, not the half-way balance.
 if pg_catalog.to_regprocedure('cp7_guard.begin_compound(text)')is not null then perform cp7_guard.begin_compound('SALES_NOTE_CORRECTION');end if;
 -- Remove active children before reversing the invoice, then restore their
 -- immutable original physical inputs onto its replacement in one command.
 for payment in select *from jsonb_to_recordset(paid)as p(id uuid)loop
  perform cp7_sales.command_access('PAYMENT_REVERSE');perform cp7_note.reverse_sales_payment(payment.id,p_payload->>'change_reason');
 end loop;
 for returned in select *from jsonb_to_recordset(returns)as r(id uuid)loop
  perform cp7_sales.command_access('RETURN_REVERSE');perform cp7_note.reverse_sales_return(returned.id,p_payload->>'change_reason');
 end loop;
 perform cp7_note.reverse_sale(leaf,p_payload->>'change_reason');
 native_request:=md5(auth.uid()::text||':NOTE:'||p_request::text)::uuid;
 draft:=(p_payload-'sale_id'-'review_token'-'change_reason'-'item_lineage')||jsonb_build_object('sale_number',left((select sale_number from erp.sales_headers where id=root),38)||' · R'||revision::text||'-'||left(p_request::text,8),'reason',p_payload->>'change_reason');
 result:=erp.save_sale_draft_v2(draft,native_request,null);
 replaced:=(result->>'sale_id')::uuid;
 perform cp7_note.bind_items(leaf,replaced,correction_id,p_payload->'items',p_payload->'item_lineage');
 perform erp.post_sale(replaced);
 for returned in select value from jsonb_array_elements(returns)loop
  perform cp7_sales.command_access('RETURN');
  insert into erp.sales_returns(return_number,sale_id,customer_id,physical_at,notes,status,created_by)
  values(left(returned.value->>'return_number',38)||' · K-'||left(p_request::text,8),replaced,h.customer_id,
   (returned.value->>'physical_at')::timestamptz,returned.value->>'notes','DRAFT',erp.current_app_user_id())returning id into new_return;
  for line in select value from jsonb_array_elements(returned.value->'items')loop
   select x.id into allocation from erp.sale_stock_allocations x join erp.sales_items i on i.id=x.sale_item_id
    where i.sale_id=replaced and i.product_id=(line->>'product_id')::uuid and x.lot_id=(line->>'lot_id')::uuid
     and x.location_id=(line->>'allocation_location_id')::uuid
     and x.sale_item_id=(select l.replacement_item_id from cp7_note.item_lineage l
      join erp.sale_stock_allocations prior_allocation on prior_allocation.sale_item_id=l.previous_item_id
      where prior_allocation.id=(line->>'sale_stock_allocation_id')::uuid and l.replacement_item_id=x.sale_item_id)
     and not exists(select 1 from erp.sales_return_items z where z.return_id=new_return and z.sale_stock_allocation_id=x.id)
     and x.qty_pcs>=
      (line->>'qty_pcs')::integer+coalesce((select sum(z.qty_pcs)from erp.sales_return_items z where z.sale_stock_allocation_id=x.id),0)
    order by x.id limit 1;
   if allocation is null then raise exception 'CP7_NOTE_RETURN_ALLOCATION_CHANGED';end if;
   -- The refund was agreed for the old net price of each returned piece.
   -- Replaying it onto a line sold at another net price would overstate (or
   -- refuse) receivable without anyone seeing it: correct the return first.
   if exists(select 1 from erp.sale_stock_allocations old_x join erp.sales_items o on o.id=old_x.sale_item_id,
     erp.sale_stock_allocations new_x join erp.sales_items n on n.id=new_x.sale_item_id
    where old_x.id=(line->>'sale_stock_allocation_id')::uuid and new_x.id=allocation
     and(o.qty_pcs*o.unit_price_snapshot-coalesce(o.discount_amount,0))*n.qty_pcs
      <>(n.qty_pcs*n.unit_price_snapshot-coalesce(n.discount_amount,0))*o.qty_pcs)then
    raise exception 'CP7_NOTE_RETURNED_LINE_PRICE_CHANGED';end if;
   insert into erp.sales_return_items(return_id,sale_stock_allocation_id,product_id,lot_id,location_id,qty_pcs,quality_grade,refund_amount,notes)
   values(new_return,allocation,(line->>'product_id')::uuid,(line->>'lot_id')::uuid,(line->>'location_id')::uuid,
    (line->>'qty_pcs')::integer,line->>'quality_grade',(line->>'refund_amount')::numeric,line->>'notes')returning id into new_return_item;
   return_lineage:=return_lineage||jsonb_build_object(new_return_item::text,line->>'id');
  end loop;
  perform erp.post_sales_return(new_return);
 end loop;
 for payment in select value from jsonb_array_elements(paid)loop
  perform cp7_sales.command_access('PAYMENT');
  insert into erp.sales_payments(sale_id,payment_number,payment_date,amount,cash_account_id,payment_method,reference_number,notes,status,created_by)
  values(replaced,left(payment.value->>'payment_number',38)||' · K-'||left(p_request::text,8),
   (payment.value->>'payment_date')::timestamptz,(payment.value->>'amount')::numeric,(payment.value->>'cash_account_id')::uuid,
   payment.value->>'payment_method',payment.value->>'reference_number',payment.value->>'notes','DRAFT',erp.current_app_user_id())returning id into new_payment;
  if payment.value->>'advance_id'is not null then
   -- Same original wallet and amount. Accepted Native funding validation locks
   -- it, checks its actual remaining amount/customer/source snapshot and dates,
   -- and posts liability/AR rather than cash. No opening balance is edited.
   insert into erp.initial_import_prepayment_payments(payment_id,advance_id,sales_payment_id,payment_snapshot)
   select new_payment,(payment.value->>'advance_id')::uuid,new_payment,to_jsonb(p)-'status'
   from erp.sales_payments p where p.id=new_payment;
  end if;
  perform erp.post_sales_payment(new_payment);
  insert into cp7_note.payment_replays(previous_payment_id,replacement_payment_id,correction_id)
  values((payment.value->>'id')::uuid,new_payment,correction_id);
 end loop;
 if pg_catalog.to_regprocedure('cp7_guard.end_compound()')is not null then perform cp7_guard.end_compound();end if;
 -- Collapse compensating movements under their original source card. A newly
 -- added SKU gets its own Native card inserted beside this note's source,
 -- using the accepted move writer. Unrelated manual order is never reset.
 -- Original quantity, recorded clock and posted price are never edited.
 for new_move in select m.*from erp.fg_stock_movements m where m.reversal_of_id=any(coalesce(before_movements,'{}'::uuid[]))
  or m.source_type='SALE_ITEM'and exists(select 1 from erp.sales_items i where i.id=m.source_id and i.sale_id=replaced)
  or exists(select 1 from erp.fg_stock_movements reservation join erp.sales_items i on i.id=reservation.source_id
    where reservation.id=m.reversal_of_id and reservation.source_type='SALE_ITEM'and i.sale_id=replaced)
  or m.source_type='SALES_RETURN_ITEM'and exists(select 1 from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where i.id=m.source_id and r.sale_id=replaced)
  order by case when m.movement_type='SALE'and m.reversal_of_id is null then 0
    when m.reversal_of_id is null then 1 else 2 end,m.system_created_at,m.id loop
  anchor:=null;
  if new_move.reversal_of_id is not null then
   select coalesce(l.origin_id,new_move.reversal_of_id)into anchor from(select 1)x left join cp7_fg.correction_movements l on l.member_id=new_move.reversal_of_id;
  elsif new_move.source_type='SALE_ITEM'and exists(select 1 from erp.sales_items where id=new_move.source_id and sale_id=replaced)then
   anchor:=cp7_note.line_origin(leaf,new_move.source_id,new_move.product_id,new_move.lot_id,new_move.location_id,new_move.quality_grade);
   if anchor is null then
    select coalesce(l.origin_id,m.id)into anchor from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id
     left join cp7_fg.correction_movements l on l.member_id=m.id
     where i.sale_id=replaced and i.id=new_move.source_id and m.movement_type='SALE'and m.product_id=new_move.product_id
      and m.location_id=new_move.location_id and m.quality_grade=new_move.quality_grade
     order by(m.lot_id=new_move.lot_id)desc,m.book_order,m.id limit 1;
    if anchor=new_move.id then
     select coalesce(l.origin_id,m.id) as origin_id into origin from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id
      left join cp7_fg.correction_movements l on l.member_id=m.id
      where i.sale_id=leaf and m.movement_type='SALE'order by m.book_order,m.id limit 1;
     if origin.origin_id is null then raise exception 'CP7_NOTE_ORIGINAL_BOOK_SOURCE_REQUIRED';end if;
     perform erp.move_fg_stock_card_row_to_position(new_move.id,cp7_fg.book_anchor(new_move.id,origin.origin_id,'AFTER'));
    end if;
   end if;
  elsif new_move.source_type='SALES_RETURN_ITEM'then
   select coalesce(l.origin_id,m.id)into anchor from erp.fg_stock_movements m join erp.sales_return_items i on i.id=m.source_id join erp.sales_returns r on r.id=i.return_id
    left join cp7_fg.correction_movements l on l.member_id=m.id where r.sale_id=leaf and i.id=(return_lineage->>new_move.source_id::text)::uuid and m.movement_type='SALE_RETURN'
     and m.product_id=new_move.product_id and m.lot_id is not distinct from new_move.lot_id and m.location_id=new_move.location_id
     and m.quality_grade=new_move.quality_grade and m.physical_at=new_move.physical_at order by m.book_order,m.id limit 1;
  end if;
  if anchor is not null and anchor<>new_move.id then insert into cp7_fg.correction_movements values(new_move.id,anchor,correction_id,clock_timestamp());end if;
 end loop;
 if cp7_note.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_NOTE_ACCESS_CHANGED';end if;
 insert into cp7_note.revisions(id,root_sale_id,previous_sale_id,replacement_sale_id,revision,actor,request_id,reason,effective_at)
 values(correction_id,root,leaf,replaced,revision,auth.uid(),p_request,p_payload->>'change_reason',h.sale_date);
 delete from cp7_sales.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 delete from cp7_note.context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 result:=jsonb_build_object('contract_version','cp7.note-correction-outcome.v1','kind','COMMITTED_OUTCOME',
  'action','CORRECT','request_id',p_request,'root_sale_id',root,'previous_sale_id',leaf,
  'sale_id',replaced,'revision_id',correction_id,'revision',revision::text,'effective_at',h.sale_date);
 update cp7_note.requests set response=result where actor=auth.uid()and request_id=p_request;
 if zero_effect_proof is not null then
  perform cp7_note_zero_effect.finish_v1(zero_effect_proof,result);
 end if;
 return result;
end $function$;

CREATE OR REPLACE FUNCTION cp7_credit.assert_current_source_plan_profile(p_sale uuid, p_root uuid, p_leaf uuid, p_actual jsonb)
 RETURNS void
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare root uuid;actual jsonb;e record;
begin
 if(p_actual->>'sale_id',p_actual->>'root_sale_id',p_actual->>'current_leaf_id')is distinct from
   (p_sale::text,p_root::text,p_leaf::text)then raise exception 'CP7_CREDIT_CURRENT_ASSIGNMENT_CHANGED';end if;
 if jsonb_typeof(p_actual->'upstream_root_ids')is distinct from'array'
  or not(p_actual->'upstream_root_ids')@>jsonb_build_array(p_root)then raise exception 'CP7_CREDIT_CURRENT_SOURCE_ROOT_SET_REQUIRED';end if;
 for root in select value::uuid from jsonb_array_elements_text(p_actual->'upstream_root_ids')order by value loop
  actual:=case when root=p_root then p_actual else cp7_credit.current_materialized_objects(root,root,root)end;
  for e in select ce.id from cp7_credit.consumption_events ce join cp7_credit.cohorts c on c.id=ce.cohort_id
   join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=root order by ce.id loop
   perform cp7_credit.consumer_event_data_v1(e.id);
  end loop;
  if root=p_root and cp7_credit_note_carry_de.has_root_v1(root)then
   perform cp7_credit_note_carry_de.assert_profile_v1(p_sale,p_root,p_leaf,actual);
  elsif root=p_root and cp7_note_zero_effect.has_owned_root_v1(root)then
   perform cp7_note_zero_effect.assert_owned_profile_v1(p_sale,p_root,p_leaf,actual);
  else perform cp7_credit._consumer_root_source_profile_v1(root,root,root,actual);end if;
 end loop;
end $function$;

CREATE OR REPLACE FUNCTION cp7_credit.assert_initial_return_closed_v1(p_operation uuid)
 RETURNS void
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare m cp7_credit.initial_return_materializations;c cp7_credit.initial_return_completions;q cp7_sales.requests;a jsonb;h erp.sales_headers;net numeric;paid numeric; leaf uuid;
begin
 select *into strict m from cp7_credit.initial_return_materializations where operation_id=p_operation;
 select *into strict q from cp7_sales.requests where actor=m.actor and request_id=m.request_id;
 if q.action<>'RETURN'or q.payload is distinct from m.legacy_payload or q.expected_version is distinct from m.expected_version
  or(q.response->>'sale_id',q.response->>'return_id',q.response->>'return_status',q.response->>'action',q.response->>'request_id')is distinct from
   (m.source_sale_id::text,m.source_return_id::text,'POSTED','RETURN',m.request_id::text)then raise exception 'CP7_CREDIT_FINAL_INNER_RECEIPT_REQUIRED';end if;
 if m.origin='REVIEWED_SETTLEMENT'then
  select *into strict c from cp7_credit.initial_return_completions where operation_id=m.operation_id;
  if c.inner_receipt is distinct from q.response or c.final_manifest_sha256 is distinct from ow04_source_proposal.sha(c.final_manifest)
   or not exists(select 1 from cp7_credit.return_requests o where o.actor=m.actor and o.request_id=m.request_id and o.expected_version=m.expected_version
    and cp7_credit.pg_jsonb_sha256(o.payload)=m.payload_sha256 and o.response=c.outer_receipt)then raise exception 'CP7_CREDIT_FINAL_OUTER_RECEIPT_REQUIRED';end if;
 end if;
 if exists(select 1 from cp7_credit.initial_return_work where operation_id=m.operation_id)
  or exists(select 1 from cp7_credit.execution_context where actor=m.actor and request_id=m.request_id)
  or exists(select 1 from cp7_credit.return_native_scope where actor=m.actor and return_id=m.source_return_id)
  or exists(select 1 from cp7_credit.return_command_scope where actor=m.actor and request_id=m.request_id)
  or exists(select 1 from cp7_credit.posting_scope where actor=m.actor and request_id=m.request_id)
  or exists(select 1 from cp7_credit.initial_refund_posting_scope where actor=m.actor and request_id=m.request_id)then raise exception 'CP7_CREDIT_FINAL_PRIVATE_SCOPE_LEAK';end if;
 select *into strict h from erp.sales_headers where id=m.source_sale_id;
 if h.status='REVERSED'and m.origin='ORDINARY'then
  leaf:=cp7_note_zero_effect.owned_leaf_for_return_v1(m.source_sale_id,m.operation_id);
  if leaf is not null then select *into strict h from erp.sales_headers where id=leaf;end if;
 end if;
 if h.status not in('POSTED','PARTIAL_PAID','PAID')then raise exception 'CP7_CREDIT_NEW_RETURN_FINAL_ACTIVE_SALE_REQUIRED';end if;
 a:=cp7_credit.inspect_current_materialized_profile(h.id,m.source_sale_id,h.id);
 perform cp7_credit.assert_current_source_plan_profile(h.id,m.source_sale_id,h.id,a);
 perform cp7_credit.assert_financial_materialization_provenance(a);
 net:=(select coalesce(sum(line_total),0)from erp.sales_items where sale_id=h.id)
  -(select coalesce(sum(i.refund_amount),0)from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where r.sale_id=h.id and r.status='POSTED');
 paid:=(select coalesce(sum(amount),0)from erp.sales_payments where sale_id=h.id and status='POSTED')+(a->>'U')::numeric-(a->>'I')::numeric;
 if net<0 or paid<0 or paid>net or h.status<>(case when paid=net then'PAID'when paid>0 then'PARTIAL_PAID'else'POSTED'end)then
  raise exception 'CP7_CREDIT_FINAL_AR_OR_STATUS_MISMATCH';end if;
 if m.cohort_id is not null and m.settlement->>'mode'='REFUND'and not exists(select 1 from cp7_credit.consumption_events ce
  where ce.id=m.refund_operation_id and ce.cohort_id=m.cohort_id and ce.amount=(m.actual_kernel->>'net_current_k')::numeric)then
  raise exception 'CP7_CREDIT_FINAL_FULL_REFUND_MISSING';end if;
end $function$;

do $guard$
declare actual text;
begin
 select md5(pg_get_functiondef('cp7_note.command(jsonb,uuid,text)'::regprocedure)) into actual;
 if actual is distinct from '0712b785c0d44b46878e2cca642be71f' then
  raise exception 'CP7_FOCUSED_INSTALLED_DEFINITION_CHANGED:cp7_note.command(jsonb,uuid,text):%',actual;
 end if;
 select md5(pg_get_functiondef('cp7_credit.assert_current_source_plan_profile(uuid,uuid,uuid,jsonb)'::regprocedure)) into actual;
 if actual is distinct from '8011f1995b6249d5d72fa98910c2bda3' then
  raise exception 'CP7_FOCUSED_INSTALLED_DEFINITION_CHANGED:cp7_credit.assert_current_source_plan_profile(uuid,uuid,uuid,jsonb):%',actual;
 end if;
 select md5(pg_get_functiondef('cp7_credit.assert_initial_return_closed_v1(uuid)'::regprocedure)) into actual;
 if actual is distinct from 'bf3e85df164913ba6a10e3d90a0c9b0c' then
  raise exception 'CP7_FOCUSED_INSTALLED_DEFINITION_CHANGED:cp7_credit.assert_initial_return_closed_v1(uuid):%',actual;
 end if;
 select md5(pg_get_functiondef('cp7_note_zero_effect.assert_price_effect_v1(jsonb,jsonb,uuid,uuid,numeric)'::regprocedure)) into actual;
 if actual is distinct from '0692f43fc8d09d0d0c3ba3238b0fb521' then
  raise exception 'CP7_FOCUSED_INSTALLED_DEFINITION_CHANGED:cp7_note_zero_effect.assert_price_effect_v1(jsonb,jsonb,uuid,uuid,numeric):%',actual;
 end if;
 if has_function_privilege('anon','cp7_note_zero_effect.prepare_v1(jsonb,uuid,text,uuid,jsonb)','EXECUTE')
    or has_function_privilege('authenticated','cp7_note_zero_effect.finish_v1(jsonb,jsonb)','EXECUTE')
    or has_function_privilege('service_role','cp7_note_zero_effect.has_owned_root_v1(uuid)','EXECUTE') then
  raise exception 'CP7_FOCUSED_PRIVATE_EXECUTE_LEAK';
 end if;
 if has_table_privilege('anon','cp7_note_zero_effect.preparations','SELECT')
    or has_table_privilege('authenticated','cp7_note_zero_effect.receipts','SELECT') then
  raise exception 'CP7_FOCUSED_PRIVATE_RECEIPT_LEAK';
 end if;
end
$guard$;

commit;
