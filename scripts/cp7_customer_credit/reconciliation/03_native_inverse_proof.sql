-- Root-integrated strict Native inverse proof; complete composition only.
-- The source trace is historical; fresh Native qualification is still required.
do $not_an_installer$begin raise exception 'OW04_RECONCILIATION_REQUIRES_COMPLETE_ATOMIC_COMPOSITION';end $not_an_installer$;

create function cp7_credit.source_rows_v1(p jsonb)returns jsonb
language sql immutable security invoker set search_path=''as $$
 select coalesce(jsonb_agg(x order by x::text collate"C"),'[]')
 from jsonb_array_elements(p)x
$$;

-- A line multiset, not totals by account. Full source payload comparison below
-- separately preserves every original line ID, description and other column.

create function cp7_credit.source_inverse_vector_v1(p jsonb,p_flip boolean default false)returns jsonb
language sql immutable security invoker set search_path=''as $$
 select cp7_credit.source_rows_v1(coalesce(jsonb_agg(jsonb_build_object(
  'account_id',x->'account_id','customer_id',x->'customer_id','vendor_id',x->'vendor_id',
  'contractor_id',x->'contractor_id','po_id',x->'po_id','product_id',x->'product_id',
  'debit',cp7_credit.cent_text((x->>case when p_flip then'credit'else'debit'end)::numeric::cp7_credit.cent_amount),
  'credit',cp7_credit.cent_text((x->>case when p_flip then'debit'else'credit'end)::numeric::cp7_credit.cent_amount)
 )),'[]'))from jsonb_array_elements(p)x
$$;

-- The four inputs are SEALED SERVER snapshots and source identity from the
-- actual owning request. Never expose this helper as an API accepting facts.
-- STABLE/auth-free: immutable materialization readers may re-run it later.
-- It does NOT compare the whole live sale with its historical snapshot.
-- Current status of unrelated historical journals may lawfully change later;
-- all actual immutable journal payloads must still match.
--
-- Snapshot contract in addition to source_native_snapshot_v1's present keys:
-- period_snapshot, nonpo_hpp_events, po_hpp_events, hpp_journals.
-- See 02_snapshot_and_terminal.sql for exact factual read snippets.

create function cp7_credit.source_return_stock_proof_v1(p_before jsonb,p_actual jsonb,p_return uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare selected_items jsonb;originals jsonb:='[]';additions jsonb:='[]';old_move jsonb;back jsonb;
 item jsonb;row jsonb;lot jsonb;now_lot jsonb;balance jsonb;now_balance jsonb;n integer;delta numeric;
begin
 select coalesce(jsonb_agg(x order by x->>'id'),'[]')into selected_items
  from jsonb_array_elements(p_before->'return_items')x where x->>'return_id'=p_return::text;
 if selected_items='[]'::jsonb then raise exception 'CP7_CREDIT_SOURCE_INVERSE_RETURN_ITEMS_MISSING';end if;
 for row in select x from jsonb_array_elements(p_before->'stock_movements')x loop
  if not exists(select 1 from jsonb_array_elements(p_actual->'stock_movements')z where z=row)
   or(select to_jsonb(m)from erp.fg_stock_movements m where m.id=(row->>'id')::uuid)is distinct from row then
   raise exception 'CP7_CREDIT_SOURCE_INVERSE_ORIGINAL_STOCK_CHANGED';end if;
 end loop;
 select coalesce(jsonb_agg(x order by x->>'id'),'[]')into additions
  from jsonb_array_elements(p_actual->'stock_movements')x where not exists(
   select 1 from jsonb_array_elements(p_before->'stock_movements')o where o->>'id'=x->>'id');
 for item in select x from jsonb_array_elements(selected_items)x loop
  select count(*)into n from jsonb_array_elements(p_before->'stock_movements')m
   where m->>'source_type'='SALES_RETURN_ITEM'and m->>'source_id'=item->>'id'
    and m->>'movement_type'='SALE_RETURN'and m->>'reversal_of_id'is null;
  if n<>1 then raise exception 'CP7_CREDIT_SOURCE_INVERSE_ORIGINAL_STOCK_NOT_UNIQUE';end if;
  select m into strict old_move from jsonb_array_elements(p_before->'stock_movements')m
   where m->>'source_type'='SALES_RETURN_ITEM'and m->>'source_id'=item->>'id'
    and m->>'movement_type'='SALE_RETURN'and m->>'reversal_of_id'is null;
  if(old_move->>'product_id',old_move->>'lot_id',old_move->>'location_id',old_move->>'quality_grade',
     (old_move->>'qty_signed')::numeric,(old_move->>'unit_hpp_snapshot')::numeric,old_move->>'customer_id')is distinct from
    (item->>'product_id',item->>'lot_id',item->>'location_id',item->>'quality_grade',
     (item->>'qty_pcs')::numeric,(item->>'unit_hpp_snapshot')::numeric,p_before#>>'{sale,customer_id}')
   or exists(select 1 from jsonb_array_elements(p_before->'stock_movements')m where m->>'reversal_of_id'=old_move->>'id')then
   raise exception 'CP7_CREDIT_SOURCE_INVERSE_ORIGINAL_STOCK_SOURCE_INVALID';end if;
  select count(*)into n from jsonb_array_elements(additions)m where m->>'reversal_of_id'=old_move->>'id';
  if n<>1 then raise exception 'CP7_CREDIT_SOURCE_INVERSE_STOCK_BIJECTION_REQUIRED';end if;
  select m into strict back from jsonb_array_elements(additions)m where m->>'reversal_of_id'=old_move->>'id';
  if(back->>'movement_type',back->>'source_type',back->>'source_id',back->>'reversal_of_id',
     back->>'product_id',back->>'lot_id',back->>'location_id',back->>'quality_grade',
     (back->>'qty_signed')::numeric,(back->>'unit_hpp_snapshot')::numeric,back->>'customer_id')is distinct from
    ('REVERSAL','FG_MOVEMENT_REVERSAL',old_move->>'id',old_move->>'id',
     old_move->>'product_id',old_move->>'lot_id',old_move->>'location_id',old_move->>'quality_grade',
     -(old_move->>'qty_signed')::numeric,(old_move->>'unit_hpp_snapshot')::numeric,old_move->>'customer_id')
   or(back->>'physical_at')::timestamptz is null
   or(back->>'physical_at')::timestamptz<(old_move->>'physical_at')::timestamptz
   or(back->>'system_created_at')::timestamptz<(old_move->>'system_created_at')::timestamptz
   or(select to_jsonb(m)from erp.fg_stock_movements m where m.id=(back->>'id')::uuid)is distinct from back then
   raise exception 'CP7_CREDIT_SOURCE_INVERSE_STOCK_DIMENSIONS_OR_CHRONOLOGY_CHANGED';end if;
  -- Native uses clock_timestamp() for physical reversal, statement_timestamp()
  -- for J. No assertion equates their Jakarta dates across midnight.
  originals:=originals||jsonb_build_array(old_move);
 end loop;
 if jsonb_array_length(additions)<>jsonb_array_length(selected_items)then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_EXTRA_STOCK_EFFECT';end if;
 if jsonb_array_length(p_before->'fg_lots')<>jsonb_array_length(p_actual->'fg_lots')then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_LOT_SET_CHANGED';end if;
 for lot in select x from jsonb_array_elements(p_before->'fg_lots')x loop
  select x into strict now_lot from jsonb_array_elements(p_actual->'fg_lots')x where x->>'id'=lot->>'id';
  select coalesce(sum((m->>'qty_signed')::numeric),0)into delta from jsonb_array_elements(additions)m where m->>'lot_id'=lot->>'id';
  if lot-array['cached_qty_pcs','is_open']is distinct from now_lot-array['cached_qty_pcs','is_open']
   or(now_lot->>'cached_qty_pcs')::numeric is distinct from(lot->>'cached_qty_pcs')::numeric+delta
   or(now_lot->>'is_open')::boolean is distinct from((now_lot->>'cached_qty_pcs')::numeric>0)then
   raise exception 'CP7_CREDIT_SOURCE_INVERSE_LOT_CACHE_OR_IDENTITY_CHANGED';end if;
 end loop;
 if jsonb_array_length(p_before->'inventory_balances')<>jsonb_array_length(p_actual->'inventory_balances')then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_INVENTORY_KEY_SET_CHANGED';end if;
 for balance in select x from jsonb_array_elements(p_before->'inventory_balances')x loop
  select x into strict now_balance from jsonb_array_elements(p_actual->'inventory_balances')x where
   (x->>'product_id',x->>'location_id',x->>'quality_grade')=
   (balance->>'product_id',balance->>'location_id',balance->>'quality_grade');
  select coalesce(sum((m->>'qty_signed')::numeric),0)into delta from jsonb_array_elements(additions)m where
   (m->>'product_id',m->>'location_id',m->>'quality_grade')=
   (balance->>'product_id',balance->>'location_id',balance->>'quality_grade');
  if balance-array['cached_qty_pcs','updated_at']is distinct from now_balance-array['cached_qty_pcs','updated_at']
   or(now_balance->>'cached_qty_pcs')::numeric is distinct from(balance->>'cached_qty_pcs')::numeric+delta
   or delta=0 and now_balance is distinct from balance
   or delta<>0 and(now_balance->>'updated_at')::timestamptz<(balance->>'updated_at')::timestamptz then
   raise exception 'CP7_CREDIT_SOURCE_INVERSE_INVENTORY_CACHE_CHANGED';end if;
 end loop;
 -- FIRST vertical: no cost correction or opening-state redistribution is
 -- adopted. It must refuse rather than accept a cache-only discrepancy.
 if p_actual->'opening_hpp_states'is distinct from p_before->'opening_hpp_states'
  or p_actual->'po_hpp_states'is distinct from p_before->'po_hpp_states'then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_HPP_STATE_EFFECT_UNQUALIFIED';end if;
 return jsonb_build_object('contract_version','ow04.native-return-stock-inverse-proof.v1','return_id',p_return,
  'original_movement_ids',(select jsonb_agg(m->'id'order by m->>'id')from jsonb_array_elements(originals)m),
  'inverse_movement_ids',(select jsonb_agg(m->'id'order by m->>'id')from jsonb_array_elements(additions)m),
  'originals_sha256',cp7_credit.pg_jsonb_sha256(cp7_credit.source_rows_v1(originals)),
  'inverses_sha256',cp7_credit.pg_jsonb_sha256(cp7_credit.source_rows_v1(additions)),
  'before_lot_cache_sha256',cp7_credit.pg_jsonb_sha256(p_before->'fg_lots'),
  'actual_lot_cache_sha256',cp7_credit.pg_jsonb_sha256(p_actual->'fg_lots'),
  'before_inventory_sha256',cp7_credit.pg_jsonb_sha256(p_before->'inventory_balances'),
  'actual_inventory_sha256',cp7_credit.pg_jsonb_sha256(p_actual->'inventory_balances'));
end $$;

-- Factual supplementary reader. Merge its keys into source_native_snapshot_v1
-- in the SAME server snapshot, after source locks. The original helper's raw
-- HPP/movement/cache additions from root are preserved, not replaced here.

create function cp7_credit.source_first_nonpo_hpp_alignment_v1(p_snapshot jsonb)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare product uuid;fg uuid;cogs uuid;expense uuid;income uuid;t jsonb;b jsonb;rows jsonb:='[]';
begin
 select(x->>'account_id')::uuid into strict fg from jsonb_array_elements(p_snapshot#>'{hpp_accounts,mappings}')x where x->>'mapping_key'='FG_INVENTORY';
 select(x->>'account_id')::uuid into strict cogs from jsonb_array_elements(p_snapshot#>'{hpp_accounts,mappings}')x where x->>'mapping_key'='COGS';
 select(x->>'account_id')::uuid into strict expense from jsonb_array_elements(p_snapshot#>'{hpp_accounts,mappings}')x where x->>'mapping_key'='OTHER_EXPENSE';
 select(x->>'account_id')::uuid into strict income from jsonb_array_elements(p_snapshot#>'{hpp_accounts,mappings}')x where x->>'mapping_key'='OTHER_INCOME';
 if exists(select 1 from jsonb_array_elements(p_snapshot->'fg_lots')x where x->>'po_id'is not null)then
  raise exception 'CP7_CREDIT_SOURCE_PO_HPP_INVERSE_UNQUALIFIED';end if;
 for product in select distinct(x->>'product_id')::uuid from jsonb_array_elements(p_snapshot->'fg_lots')x loop
  select to_jsonb(v)into strict t from erp.compute_non_po_product_hpp_targets_v2620f(product)v;
  select jsonb_build_object('hpp_total_cost',q.f+q.c+q.o,'fg_value',q.f,'cogs_value',q.c,'other_out_value',q.o)into b
   from(select coalesce(sum(l.debit-l.credit)filter(where l.account_id=fg),0)f,
    coalesce(sum(l.debit-l.credit)filter(where l.account_id=cogs),0)c,
    coalesce(sum(l.debit-l.credit)filter(where l.account_id in(expense,income)),0)o
    from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
    left join erp.journal_entries original on original.id=j.reversal_of_id
    where l.product_id=product and l.po_id is null and j.status in('POSTED','REVERSED')
     and(j.source_type<>'PRODUCT_CONVERSION'or erp.be_nonpo_admitted_v1(j.source_id))
     and(j.source_type<>'JOURNAL_REVERSAL'or original.source_type is distinct from'PRODUCT_CONVERSION'
      or erp.be_nonpo_admitted_v1(original.source_id)))q;
  if t is distinct from b then raise exception 'CP7_CREDIT_SOURCE_NATIVE_HPP_TARGET_BOOK_UNQUALIFIED';end if;
  rows:=rows||jsonb_build_array(jsonb_build_object('product_id',product,'target',t,'book',b));
 end loop;
 return rows;
end $$;

-- TERMINAL/DEFERRED PREDICATE, integration snippet, not a second Native writer:
--
-- 1. source_request_finish_v1 is AFTER erp.reverse_sales_* returns and AFTER its
--    original terminal native_source_complete hook. Require exact own pending
--    CP7 request; Native-complete phase; current authority and same period.
-- 2. Take fresh = source_native_snapshot_v1(sale). It must equal the recorded
--    N snapshot except sale.status,row_version,updated_at. For the sale identity
--    remove ONLY those three fields. Fresh physical/HPP/source facts are exact.
-- 3. Under the exact captured bump/touch trigger set (NATIVE_TRIGGER_TRACE):
--    Native performs exactly one remaining UPDATE sales_headers after N.
--    Require fresh.sale.row_version = N.sale.row_version + 1, and
--    fresh.sale.updated_at = actual_inverse_journal.posting_at. Both timestamp
--    values are this same public command's statement_timestamp(). There is no
--    child-parent version touch in the reviewed relevant Native trigger set.
-- 4. Re-run source_first_nonpo_hpp_alignment_v1(fresh), compare same source
--    inverse proof over sealed B/N, and verify actual financial materialization.
-- 5. Let a = inspect_current_materialized_profile(sale,sale,sale), factual only.
--    Nnet = SUM(sales_items.line_total) - SUM(refund_amount of POSTED returns).
--    E = SUM(amount of POSTED sales_payments) + a.U - a.I.
--    Require 0 <= E <= Nnet and actual final sale.status =
--      CASE WHEN E=Nnet THEN 'PAID' WHEN E>0 THEN 'PARTIAL_PAID' ELSE 'POSTED' END.
-- 6. Bind final receipt fields to exact request/action/source UUID and that
--    final status, persist immutable completion, then clear the mutable scope.
--    Deferred closure reads only immutable completion/materialization/CP7
--    request and factual ledgers. It must reject missing completion, mismatched
--    source/proof/plan/marker hashes, wrong receipt, leaked scope, or current
--    factual profile/status inconsistency. It MUST NOT call the live owning
--    assert_source_operation_work_v1 after work was cleared.
-- 7. Future legitimate source operations may change the live sale/profile.
--    Historical immutable B/N proof is rechecked against specific immutable
--    source journals/facts, not a requirement that today's whole sale equals
--    an earlier completion's historical snapshot.

-- This small factual terminal predicate checks the exact version/touch rule.
-- Root's assembler MUST first verify the actual composed trigger/function
-- sources described in NATIVE_TRIGGER_TRACE.json. Final financial status is
-- independently derived by root's current factual profile/receipt predicate.

create function cp7_credit.source_inverse_proof_v1(
 p_before jsonb,p_actual jsonb,p_action text,p_source uuid
)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare original jsonb;inverse jsonb;row jsonb;old_row jsonb;expected jsonb;
 old_event jsonb;actual_event jsonb;old_source jsonb;new_source jsonb;
 original_id uuid;inverse_id uuid;original_header erp.journal_entries;inverse_header erp.journal_entries;
 old_payment erp.sales_payments;new_payment erp.sales_payments;fact erp.sales_payment_posting_facts;
 reversal_fact erp.sales_payment_reversal_facts;fact_json jsonb;reversal_json jsonb;
 original_movements jsonb:='[]';new_movements jsonb:='[]';movement jsonb;back jsonb;
 selected_items jsonb;item jsonb;lot jsonb;new_lot jsonb;balance jsonb;new_balance jsonb;
 key text;source_type text;source_key text;n integer;closed date;lawful date;delta numeric;
 sale_id uuid;ar_account uuid;old_facts jsonb;after_facts jsonb;proof jsonb;
begin
 if p_action is null or p_action not in('RETURN_REVERSE','PAYMENT_REVERSE')or p_source is null then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_ACTION_REQUIRED';end if;
 if jsonb_typeof(p_before)is distinct from'object'or jsonb_typeof(p_actual)is distinct from'object'
  or not p_before?&array['sale','items','allocations','payments','payment_posting_facts','payment_reversal_facts',
   'returns','return_items','base_events','journals','advance_links','fg_lots','hpp_versions','stock_movements',
   'inventory_balances','opening_hpp_states','opening_hpp_corrections','po_hpp_states','hpp_accounts',
   'period_snapshot','nonpo_hpp_events','po_hpp_events','hpp_journals']
  or not p_actual?&array['sale','items','allocations','payments','payment_posting_facts','payment_reversal_facts',
   'returns','return_items','base_events','journals','advance_links','fg_lots','hpp_versions','stock_movements',
   'inventory_balances','opening_hpp_states','opening_hpp_corrections','po_hpp_states','hpp_accounts',
   'period_snapshot','nonpo_hpp_events','po_hpp_events','hpp_journals']then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_SNAPSHOT_INCOMPLETE';end if;
 sale_id:=(p_before#>>'{sale,id}')::uuid;
 if sale_id is null or p_actual#>>'{sale,id}'is distinct from sale_id::text
  or (p_before->'sale')-array['status','row_version','updated_at']is distinct from
     (p_actual->'sale')-array['status','row_version','updated_at']then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_SALE_IDENTITY_CHANGED';end if;
 -- The exact bounded hook is BEFORE Native's only sale-header UPDATE.
 -- NATIVE_TRIGGER_TRACE records no child-parent touch and the assembler must
 -- verify that composed trigger set. A shifted hook cannot silently qualify.
 if p_before->'sale'is distinct from p_actual->'sale'then
  raise exception 'CP7_CREDIT_SOURCE_HEADER_CHANGED_BEFORE_NATIVE_E';end if;
 foreach key in array array['items','allocations','return_items','payment_posting_facts','advance_links',
  'hpp_versions','opening_hpp_corrections','hpp_accounts','period_snapshot','nonpo_hpp_events','po_hpp_events']loop
  if p_actual->key is distinct from p_before->key then
   raise exception 'CP7_CREDIT_SOURCE_INVERSE_PRESERVED_FACT_CHANGED: %',key;end if;
 end loop;
 -- FIRST bounded vertical. These are pre-effect guards too, not a promise
 -- that a later adapter can adopt PO/recost/conversion synchronization.
 if p_before->'advance_links'<>'[]'::jsonb
  or exists(select 1 from jsonb_array_elements(p_before->'payments')x where
   x->>'cash_account_id'is null or x->>'payment_method'='OPENING_ADVANCE')then
  raise exception 'CP7_CREDIT_SOURCE_ADVANCE_INVERSE_UNQUALIFIED';end if;
 if exists(select 1 from jsonb_array_elements(p_before->'fg_lots')x where x->>'po_id'is not null)
  or p_before->'po_hpp_states'<>'[]'::jsonb then
  raise exception 'CP7_CREDIT_SOURCE_PO_HPP_INVERSE_UNQUALIFIED';end if;
 if p_before->'opening_hpp_corrections'<>'[]'::jsonb
  or exists(select 1 from jsonb_array_elements(p_before->'hpp_versions')x
   group by x->>'lot_id'having count(*)<>1)then
  raise exception 'CP7_CREDIT_SOURCE_RECOST_INVERSE_UNQUALIFIED';end if;
 if exists(select 1 from jsonb_array_elements(p_before->'fg_lots')x where x->>'lot_origin'='CONVERSION')then
  raise exception 'CP7_CREDIT_SOURCE_CONVERSION_INVERSE_UNQUALIFIED';end if;

 source_type:=case when p_action='RETURN_REVERSE'then'SALES_RETURN'else'SALES_PAYMENT'end;
 source_key:=case when p_action='RETURN_REVERSE'then'returns'else'payments'end;
 select count(*)into n from jsonb_array_elements(p_before->source_key)x where x->>'id'=p_source::text;
 if n<>1 then raise exception 'CP7_CREDIT_SOURCE_INVERSE_ORIGINAL_SOURCE_NOT_UNIQUE';end if;
 select x into strict old_source from jsonb_array_elements(p_before->source_key)x where x->>'id'=p_source::text;
 select x into strict new_source from jsonb_array_elements(p_actual->source_key)x where x->>'id'=p_source::text;
 if old_source->>'status'is distinct from'POSTED'or new_source->>'status'is distinct from'REVERSED'
  or old_source->>'sale_id'is distinct from sale_id::text
  or old_source-'status'is distinct from new_source-'status'then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_SOURCE_STATUS_OR_IDENTITY_CHANGED';end if;
 select cp7_credit.source_rows_v1(coalesce(jsonb_agg(case when x->>'id'=p_source::text
  then jsonb_set(x,'{status}','"REVERSED"')else x end),'[]'))into expected
  from jsonb_array_elements(p_before->source_key)x;
 if cp7_credit.source_rows_v1(p_actual->source_key)is distinct from expected then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_UNRELATED_SOURCE_CHANGED';end if;
 key:=case when p_action='RETURN_REVERSE'then'payments'else'returns'end;
 if p_before->key is distinct from p_actual->key then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_OTHER_SOURCE_KIND_CHANGED';end if;

 select count(*)into n from jsonb_array_elements(p_before->'journals')x where
  x#>>'{immutable_payload,journal,source_type}'=source_type
  and x#>>'{immutable_payload,journal,source_id}'=p_source::text;
 if n<>1 then raise exception 'CP7_CREDIT_SOURCE_INVERSE_ORIGINAL_JOURNAL_NOT_UNIQUE';end if;
 select x into strict original from jsonb_array_elements(p_before->'journals')x where
  x#>>'{immutable_payload,journal,source_type}'=source_type
  and x#>>'{immutable_payload,journal,source_id}'=p_source::text;
 original_id:=(original->>'id')::uuid;
 original_header:=jsonb_populate_record(null::erp.journal_entries,original#>'{immutable_payload,journal}');
 if original->>'status'is distinct from'POSTED'or original_header.id is distinct from original_id
  or original_header.reversal_of_id is not null then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_BAD_ORIGINAL_JOURNAL';end if;
 if exists(select 1 from jsonb_array_elements(p_before->'journals')x where
  x#>>'{immutable_payload,journal,source_id}'=original_id::text
  or x#>>'{immutable_payload,journal,reversal_of_id}'=original_id::text)then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_ALREADY_EXISTED';end if;
 select count(*)into n from jsonb_array_elements(p_actual->'journals')x where
  x#>>'{immutable_payload,journal,source_type}'='JOURNAL_REVERSAL'
  and x#>>'{immutable_payload,journal,source_id}'=original_id::text
  and x#>>'{immutable_payload,journal,reversal_of_id}'=original_id::text;
 if n<>1 then raise exception 'CP7_CREDIT_SOURCE_INVERSE_ACTUAL_JOURNAL_NOT_UNIQUE';end if;
 select x into strict inverse from jsonb_array_elements(p_actual->'journals')x where
  x#>>'{immutable_payload,journal,source_type}'='JOURNAL_REVERSAL'
  and x#>>'{immutable_payload,journal,source_id}'=original_id::text
  and x#>>'{immutable_payload,journal,reversal_of_id}'=original_id::text;
 inverse_id:=(inverse->>'id')::uuid;
 inverse_header:=jsonb_populate_record(null::erp.journal_entries,inverse#>'{immutable_payload,journal}');
 if inverse->>'status'is distinct from'POSTED'or inverse_id is null or inverse_header.id is distinct from inverse_id
  or inverse_id=original_id then raise exception 'CP7_CREDIT_SOURCE_INVERSE_BAD_ACTUAL_JOURNAL';end if;
 select cp7_credit.source_rows_v1(coalesce(jsonb_agg(case when x->>'id'=original_id::text
  then jsonb_set(x,'{status}','"REVERSED"')else x end),'[]')||jsonb_build_array(inverse))into expected
  from jsonb_array_elements(p_before->'journals')x;
 if cp7_credit.source_rows_v1(p_actual->'journals')is distinct from expected then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_ORIGINAL_PAYLOAD_OR_JOURNAL_SET_CHANGED';end if;
 for row in select x from jsonb_array_elements(p_actual->'journals')x loop
  if cp7_credit.materialized_journal_payload((row->>'id')::uuid)is distinct from row->'immutable_payload'then
   raise exception 'CP7_CREDIT_SOURCE_INVERSE_ACTUAL_IMMUTABLE_JOURNAL_CHANGED';end if;
 end loop;
 if cp7_credit.source_inverse_vector_v1(inverse#>'{immutable_payload,lines}')is distinct from
    cp7_credit.source_inverse_vector_v1(original#>'{immutable_payload,lines}',true)then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_SIGNED_VECTOR_OR_DIMENSIONS_CHANGED';end if;
 if not exists(select 1 from jsonb_array_elements(inverse#>'{immutable_payload,lines}')x having
  sum((x->>'debit')::numeric)=sum((x->>'credit')::numeric)and sum((x->>'debit')::numeric)>0)then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_UNBALANCED';end if;
 closed:=(p_before#>>'{period_snapshot,closed_through}')::date;
 lawful:=case when closed is not null and inverse_header.economic_date<=closed
  then greatest(inverse_header.economic_date,closed+1)else inverse_header.economic_date end;
 if inverse_header.economic_date is null or inverse_header.transaction_date is null or inverse_header.posting_at is null
  or inverse_header.economic_date is distinct from(inverse_header.posting_at at time zone'Asia/Jakarta')::date
  or inverse_header.transaction_date is distinct from lawful
  or inverse_header.economic_date<original_header.economic_date or inverse_header.posting_at<original_header.posting_at then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_ACTUAL_DATE_PAIR_INVALID';end if;
 -- Historical period proof uses the captured resolver input, never today's
 -- control row. The Native inverse's economic day equals its actual posting day.
 select x into strict old_event from jsonb_array_elements(p_before->'base_events')x
  where x->>'id'='journal:'||original_id::text;
 select x into strict actual_event from jsonb_array_elements(p_actual->'base_events')x
  where x->>'id'='journal:'||inverse_id::text;
 select count(distinct c.ar_account_id),min(c.ar_account_id::text)::uuid into n,ar_account
  from cp7_credit.cohorts c where c.source_sale_id=sale_id;
 if n<>1 then raise exception 'CP7_CREDIT_SOURCE_HISTORICAL_AR_IDENTITY_UNQUALIFIED';end if;
 if old_event->>'kind'is distinct from (case when p_action='RETURN_REVERSE'then'NET'else'FUNDING'end)
  or actual_event->>'kind'is distinct from old_event->>'kind'
  or(actual_event->>'amount')::numeric is distinct from -(old_event->>'amount')::numeric
  or(actual_event->>'economic_date')::date is distinct from inverse_header.economic_date
  or(actual_event->>'transaction_date')::date is distinct from inverse_header.transaction_date
  or old_event->>'source_sha256'is distinct from ow04_source_proposal.sha(
   ow04_source_proposal.financial_journal_payload(original_id,ar_account))
  or actual_event->>'source_sha256'is distinct from ow04_source_proposal.sha(
   ow04_source_proposal.financial_journal_payload(inverse_id,ar_account))
  or(actual_event->>'amount')::numeric is distinct from(case when p_action='PAYMENT_REVERSE'then -1 else 1 end)*(
   select coalesce(sum((x->>'debit')::numeric-(x->>'credit')::numeric),0)
   from jsonb_array_elements(inverse#>'{immutable_payload,lines}')x where(x->>'account_id')::uuid=ar_account)then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_ACTUAL_EVENT_CHANGED';end if;
 if cp7_credit.source_rows_v1(p_actual->'base_events')is distinct from
  cp7_credit.source_rows_v1((p_before->'base_events')||jsonb_build_array(actual_event))then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_BASE_EVENT_DELTA_CHANGED';end if;

 if p_action='PAYMENT_REVERSE'then
  old_payment:=jsonb_populate_record(null::erp.sales_payments,old_source);
  new_payment:=jsonb_populate_record(null::erp.sales_payments,new_source);
  select x into strict fact_json from jsonb_array_elements(p_before->'payment_posting_facts')x
   where x->>'payment_id'=p_source::text;
  fact:=jsonb_populate_record(null::erp.sales_payment_posting_facts,fact_json);
  if fact.original_journal_entry_id is distinct from original_id or fact.sale_id is distinct from sale_id
   or fact.customer_id is distinct from(p_before#>>'{sale,customer_id}')::uuid
   or fact.payment_number is distinct from old_payment.payment_number
   or fact.payment_date is distinct from old_payment.payment_date or fact.amount is distinct from old_payment.amount
   or fact.cash_account_id is distinct from old_payment.cash_account_id
   or fact.replaces_payment_id is distinct from old_payment.replaces_payment_id
   or fact.payment_snapshot is distinct from old_source-'status'
   or fact.journal_economic_date is distinct from original_header.economic_date
   or fact.journal_transaction_date is distinct from original_header.transaction_date
   or fact.journal_posting_at is distinct from original_header.posting_at
   or fact.lineage_sha256 is distinct from cp7_credit.pg_jsonb_sha256(jsonb_build_array(
    fact.payment_id,fact.sale_id,fact.customer_id,fact.payment_number,fact.payment_date,fact.amount,
    fact.cash_account_id,fact.original_journal_entry_id,fact.journal_economic_date,fact.journal_transaction_date,
    fact.journal_posting_at,fact.replaces_payment_id,fact.predecessor_reversal_journal_id,fact.payment_snapshot))then
   raise exception 'CP7_CREDIT_SOURCE_INVERSE_PAYMENT_POSTING_FACT_INVALID';end if;
  if(select to_jsonb(f)from erp.sales_payment_posting_facts f where f.payment_id=p_source)is distinct from fact_json then
   raise exception 'CP7_CREDIT_SOURCE_INVERSE_ACTUAL_POSTING_FACT_CHANGED';end if;
  if exists(select 1 from jsonb_array_elements(p_before->'payment_reversal_facts')x where x->>'payment_id'=p_source::text)then
   raise exception 'CP7_CREDIT_SOURCE_INVERSE_PAYMENT_FACT_ALREADY_EXISTED';end if;
  select x into strict reversal_json from jsonb_array_elements(p_actual->'payment_reversal_facts')x
   where x->>'payment_id'=p_source::text;
  reversal_fact:=jsonb_populate_record(null::erp.sales_payment_reversal_facts,reversal_json);
  if(reversal_fact.original_journal_entry_id,reversal_fact.reversal_journal_entry_id,
    reversal_fact.reversal_economic_date,reversal_fact.reversal_transaction_date,reversal_fact.reversal_posting_at)is distinct from
   (original_id,inverse_id,inverse_header.economic_date,inverse_header.transaction_date,inverse_header.posting_at)
   or reversal_fact.lineage_sha256 is distinct from cp7_credit.pg_jsonb_sha256(jsonb_build_array(
    reversal_fact.payment_id,reversal_fact.original_journal_entry_id,reversal_fact.reversal_journal_entry_id,
    reversal_fact.reversal_economic_date,reversal_fact.reversal_transaction_date,reversal_fact.reversal_posting_at))then
   raise exception 'CP7_CREDIT_SOURCE_INVERSE_PAYMENT_REVERSAL_FACT_INVALID';end if;
  if cp7_credit.source_rows_v1(p_actual->'payment_reversal_facts')is distinct from
    cp7_credit.source_rows_v1((p_before->'payment_reversal_facts')||jsonb_build_array(reversal_json))
   or(select to_jsonb(f)from erp.sales_payment_reversal_facts f where f.payment_id=p_source)is distinct from reversal_json then
   raise exception 'CP7_CREDIT_SOURCE_INVERSE_ACTUAL_REVERSAL_FACT_SET_CHANGED';end if;
  -- hpp_support includes ALLOCATION.sale = to_jsonb(sales_headers), including
  -- status/version/touch time. It is not a physical immutability predicate.
  -- Preserve every raw physical/HPP fact and full HPP J instead.
  foreach key in array array['fg_lots','stock_movements','inventory_balances','opening_hpp_states',
   'po_hpp_states','hpp_journals']loop
   if p_before->key is distinct from p_actual->key then
    raise exception 'CP7_CREDIT_SOURCE_INVERSE_PAYMENT_CHANGED_PHYSICAL_OR_HPP_FACTS: %',key;end if;
  end loop;
 else
  if p_actual->'payment_reversal_facts'is distinct from p_before->'payment_reversal_facts'then
   raise exception 'CP7_CREDIT_SOURCE_INVERSE_RETURN_CHANGED_PAYMENT_FACTS';end if;
  -- Physical bijection and cache arithmetic are delegated to another complete
  -- predicate, supplied in 02. That helper has no authority or work dependency.
  proof:=cp7_credit.source_return_stock_proof_v1(p_before,p_actual,p_source);
 end if;
 -- All relevant HPP journals are an exact before-set plus, for return only,
 -- the actual source inverse. This excludes hidden Native sync/revaluation J.
 expected:=p_before->'hpp_journals';
 if p_action='RETURN_REVERSE'then
  select cp7_credit.source_rows_v1(coalesce(jsonb_agg(case when x->>'id'=original_id::text
   then jsonb_set(x,'{status}','"REVERSED"')else x end),'[]')||case when exists(
    select 1 from jsonb_array_elements(p_before->'hpp_journals')z where z->>'id'=original_id::text)
    then jsonb_build_array(inverse)else'[]'::jsonb end)into expected
   from jsonb_array_elements(p_before->'hpp_journals')x;
 end if;
 if cp7_credit.source_rows_v1(p_actual->'hpp_journals')is distinct from cp7_credit.source_rows_v1(expected)then
  raise exception 'CP7_CREDIT_SOURCE_INVERSE_UNQUALIFIED_HPP_JOURNAL_EFFECT';end if;
 for row in select x from jsonb_array_elements(p_actual->'hpp_journals')x loop
  if cp7_credit.materialized_journal_payload((row->>'id')::uuid)is distinct from row->'immutable_payload'then
   raise exception 'CP7_CREDIT_SOURCE_INVERSE_ACTUAL_HPP_JOURNAL_CHANGED';end if;
 end loop;
 return jsonb_build_object('contract_version','ow04.native-source-inverse-proof.v1','action',p_action,
  'source_id',p_source,'sale_id',sale_id,'original_journal_id',original_id,'inverse_journal_id',inverse_id,
  'original_immutable_journal_sha256',cp7_credit.pg_jsonb_sha256(original->'immutable_payload'),
  'inverse_immutable_journal_sha256',cp7_credit.pg_jsonb_sha256(inverse->'immutable_payload'),
  'inverse_signed_vector_sha256',cp7_credit.pg_jsonb_sha256(cp7_credit.source_inverse_vector_v1(inverse#>'{immutable_payload,lines}')),
  'actual_event',actual_event,'actual_event_sha256',cp7_credit.pg_jsonb_sha256(actual_event),
  'actual_pair',jsonb_build_object('economic_date',inverse_header.economic_date,'transaction_date',inverse_header.transaction_date),
  'period_snapshot_sha256',cp7_credit.pg_jsonb_sha256(p_before->'period_snapshot'),
  'before_source_sha256',cp7_credit.pg_jsonb_sha256(p_before),'actual_source_sha256',cp7_credit.pg_jsonb_sha256(p_actual),
  'payment_posting_fact_sha256',case when fact_json is not null then cp7_credit.pg_jsonb_sha256(fact_json)end,
  'payment_reversal_fact_sha256',case when reversal_json is not null then cp7_credit.pg_jsonb_sha256(reversal_json)end,
  'physical_proof',proof,'additional_native_hpp_sync_effects',0);
end $$;

-- Bind the historical-capable factual proof to the ACTUAL live owner. This
-- wrapper cannot be called to approve an arbitrary caller-provided snapshot.

create function cp7_credit.assert_source_actual_v1(p_operation uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.source_operation_work_v1;actual jsonb;proof jsonb;alignment jsonb;
begin
 perform cp7_credit.assert_source_operation_work_v1(p_operation);
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=p_operation
  and backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 if w.phase not in('ENTERED','RECONCILING')then raise exception 'CP7_CREDIT_SOURCE_ACTUAL_NATIVE_PHASE_REQUIRED';end if;
 if(w.actual_source is null)<>(w.actual_source_proof is null)
  or w.phase='RECONCILING'and(w.actual_source is null or w.actual_source_proof is null)then
  raise exception 'CP7_CREDIT_SOURCE_RECORDED_ACTUAL_PROOF_REQUIRED';end if;
 actual:=cp7_credit.source_native_snapshot_v1(w.sale_id);
 if w.actual_source is not null and w.actual_source is distinct from actual then
  raise exception 'CP7_CREDIT_SOURCE_SEALED_ACTUAL_SNAPSHOT_CHANGED';end if;
 if actual->'period_snapshot'is distinct from w.period_snapshot then
  raise exception 'CP7_CREDIT_SOURCE_PERIOD_CHANGED';end if;
 proof:=cp7_credit.source_inverse_proof_v1(w.before_source,actual,w.action,w.source_id);
 if w.actual_source_proof is not null and w.actual_source_proof is distinct from proof then
  raise exception 'CP7_CREDIT_SOURCE_RECORDED_ACTUAL_PROOF_CHANGED';end if;
 alignment:=cp7_credit.source_first_nonpo_hpp_alignment_v1(actual);
 if(proof#>>'{actual_pair,transaction_date}')::date is distinct from
   erp.resolve_accounting_transaction_date((proof#>>'{actual_pair,economic_date}')::date)then
  raise exception 'CP7_CREDIT_SOURCE_ACTUAL_LAWFUL_DATE_CHANGED';end if;
 -- Actual source and typed proof are returned together so the caller seals
 -- exactly this read, not a later independent snapshot or client projection.
 return jsonb_build_object('actual_source',actual,'actual_source_proof',proof,'native_hpp_alignment',alignment);
end $$;

-- Root must set postgres ownership and revoke EXECUTE from every application
-- role when composing these private helpers; no grants are proposed here.

create function cp7_credit.source_native_terminal_header_v1(p_native jsonb,p_final jsonb,p_inverse uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare j erp.journal_entries;version_before bigint;version_after bigint;
begin
 select *into strict j from erp.journal_entries where id=p_inverse;
 if j.source_type is distinct from'JOURNAL_REVERSAL'or j.reversal_of_id is null then
  raise exception 'CP7_CREDIT_SOURCE_TERMINAL_ACTUAL_INVERSE_REQUIRED';end if;
 version_before:=(p_native#>>'{sale,row_version}')::bigint;
 version_after:=(p_final#>>'{sale,row_version}')::bigint;
 if (p_native->'sale')-array['status','row_version','updated_at']is distinct from
    (p_final->'sale')-array['status','row_version','updated_at']
  or version_before is null or version_after is distinct from version_before+1
  or(p_final#>>'{sale,updated_at}')::timestamptz is distinct from j.posting_at then
  raise exception 'CP7_CREDIT_SOURCE_TERMINAL_HEADER_NATIVE_TRIGGER_CHANGED';end if;
 -- Only the opaque support summary is allowed to differ alongside the header:
 -- its source includes full ALLOCATION.sale. All raw HPP/physical/J/source rows
 -- remain exact. Root also repeats the strict Native target/book read here.
 if p_native-array['sale','hpp_support']is distinct from p_final-array['sale','hpp_support']then
  raise exception 'CP7_CREDIT_SOURCE_TERMINAL_UNEXPECTED_NATIVE_TAIL_EFFECT';end if;
 return jsonb_build_object('contract_version','ow04.native-source-terminal-header.v1',
  'sale_id',p_final#>'{sale,id}','before_row_version',version_before,'final_row_version',version_after,
  'final_updated_at',p_final#>'{sale,updated_at}','inverse_journal_id',p_inverse,
  'inverse_posting_at',j.posting_at,'native_header_update_count',1);
end $$;

do $private_source_inverse$declare sig text;begin
 foreach sig in array array['source_rows_v1(jsonb)','source_inverse_vector_v1(jsonb,boolean)','source_inverse_proof_v1(jsonb,jsonb,text,uuid)','assert_source_actual_v1(uuid)','source_return_stock_proof_v1(jsonb,jsonb,uuid)','source_first_nonpo_hpp_alignment_v1(jsonb)','source_native_terminal_header_v1(jsonb,jsonb,uuid)']loop
  execute 'alter function cp7_credit.'||sig||' owner to postgres';
  execute 'revoke all on function cp7_credit.'||sig||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write';
 end loop;
end $private_source_inverse$;
