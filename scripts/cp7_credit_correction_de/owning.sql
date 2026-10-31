-- Slice D1: an increased financial value with identical stock and physical facts.
-- Every broader class remains explicitly refused. Actual Native code is derived
-- at installation, never emulated by this coordinator.
create function cp7_credit_correction_de.has_source_v1(p_sale uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from cp7_credit_correction_de.operations_v1 where sale_id=p_sale)
 or exists(select 1 from cp7_credit_correction_de.work_v1 where sale_id=p_sale and phase='MATERIALIZED')
$$;

create function cp7_credit_correction_de.active_consumers_v1(p_sale uuid)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare c record;e jsonb;answer jsonb:='[]';begin
 for c in select ch.id,f.family_ordinal from cp7_credit.cohorts ch join cp7_credit.return_families f on f.id=ch.family_id
  where f.family_root_sale_id=p_sale order by f.family_ordinal loop
  for e in select value from jsonb_array_elements(cp7_credit.consumer_active_events_v1(c.id))loop
   answer:=answer||jsonb_build_array(jsonb_build_object('event_id',e->'id','event_kind',e->'event_kind',
    'amount',cp7_credit.cent_text((e->>'amount')::numeric),'cohort_id',c.id,'family_ordinal',c.family_ordinal::text,
    'target_sale_id',e->'target_sale_id','journal_id',e->'journal_id',
    'undo_action',case when e->>'event_kind'='APPLY'then'Batalkan penggunaan kredit di invoice tujuan'else'Batalkan pengembalian uang kredit' end));
  end loop;
 end loop;return answer;
end $$;

create function cp7_credit_correction_de.quote_v1(p jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare sale uuid:=(p->>'sale_id')::uuid;ret uuid:=(p->>'return_id')::uuid;r erp.sales_returns;
 inp jsonb;after_inp jsonb;families jsonb:='[]';f jsonb;events jsonb;review jsonb;active jsonb;issues jsonb:='[]';old_total numeric;new_total numeric;
 j erp.journal_entries;family uuid;delta numeric;source jsonb;authority jsonb;profile jsonb;binding jsonb;physical jsonb;proposed jsonb;
 cap_inputs jsonb:='[]';cap_line jsonb;cap_allocation jsonb;cap_item jsonb;cap_count int;max_refund numeric(24,6);
 cap_products jsonb:='[]';cap_product text;product_sale_value numeric(24,6);prior_product_refund numeric(24,6);current_product_refund numeric(24,6);
 cap_source_unavailable boolean:=false;cap_exceeded boolean:=false;
begin
 authority:=cp7_sales_return_correction.access_now();perform cp7_sales_return_correction.validate(p-'credit_review_token');
 select *into strict r from erp.sales_returns where id=ret and sale_id=sale;
 if r.status<>'POSTED'or not cp7_credit_correction_de.participates_v1(ret)then raise exception 'CP7_CREDIT_DE_CURRENT_REGISTERED_RETURN_REQUIRED';end if;
 select m.family_id into strict family from cp7_credit.return_family_members m where m.return_id=ret;
 select *into strict j from erp.journal_entries where source_type='SALES_RETURN'and source_id=ret and reversal_of_id is null;
 perform cp7_credit.assert_current_materialized_profile(sale,sale,sale);
 profile:=cp7_credit.inspect_current_materialized_profile(sale,sale,sale);
 inp:=cp7_credit.initial_ordinal_input_v1(sale);
 select coalesce(sum(refund_amount),0)into old_total from erp.sales_return_items where return_id=ret;
 select coalesce(sum((v->>'refund_amount')::numeric),0)into new_total from jsonb_array_elements(p#>'{replacement,items}')v;
 delta:=new_total-old_total;
 select jsonb_agg(jsonb_build_object('allocation_id',i.sale_stock_allocation_id,'location_id',i.location_id,
  'qty_pcs',i.qty_pcs::text,'quality_grade',i.quality_grade)order by i.sale_stock_allocation_id)into physical from erp.sales_return_items i where i.return_id=ret;
 select jsonb_agg(v-array['refund_amount','notes']order by v->>'allocation_id')into proposed from jsonb_array_elements(p#>'{replacement,items}')v;
 if physical is distinct from proposed or r.physical_at is distinct from(p#>>'{replacement,physical_at}')::timestamptz then
  issues:=issues||'"PHYSICAL_OR_QUANTITY_CHANGE_ADAPTER_REQUIRED"'::jsonb;end if;
 -- One current factual snapshot supplies both the Native cap inputs and token.
 -- prepare_v1 calls this same reader after the original source/allocation locks.
 source:=cp7_credit.source_native_snapshot_v1(sale);
 if jsonb_typeof(source->'sale')is distinct from'object'or source#>>'{sale,id}'is distinct from sale::text
  or source#>>'{sale,customer_id}'is distinct from r.customer_id::text
  or jsonb_typeof(source->'allocations')is distinct from'array'or jsonb_typeof(source->'items')is distinct from'array'
  or jsonb_typeof(source->'returns')is distinct from'array'or jsonb_typeof(source->'return_items')is distinct from'array'then
  cap_source_unavailable:=true;
 else
  -- The snapshot contains every status, including the old current return.
  -- Reject incomplete/ambiguous facts before any join can omit a peer or
  -- duplicate an item's capacity. Native owns these identities and fields.
  if exists(select 1 from jsonb_array_elements(source->'items')i where jsonb_typeof(i)is distinct from'object'
    or i->>'id'is null or i->>'product_id'is null or i->>'sale_id'is distinct from sale::text
    or coalesce(i->>'line_total','')!~'^-?[0-9]+([.][0-9]{1,2})?$')
   or exists(select 1 from jsonb_array_elements(source->'items')i group by i->>'id'having count(*)<>1)
   or exists(select 1 from jsonb_array_elements(source->'allocations')a where jsonb_typeof(a)is distinct from'object'
    or a->>'id'is null or(select count(*)from jsonb_array_elements(source->'items')i where i->>'id'=a->>'sale_item_id')<>1)
   or exists(select 1 from jsonb_array_elements(source->'allocations')a group by a->>'id'having count(*)<>1)
   or exists(select 1 from jsonb_array_elements(source->'returns')h where jsonb_typeof(h)is distinct from'object'
    or h->>'id'is null or h->>'sale_id'is distinct from sale::text or h->>'customer_id'is distinct from r.customer_id::text
    or coalesce(h->>'status','')not in('DRAFT','POSTED','REVERSED'))
   or exists(select 1 from jsonb_array_elements(source->'returns')h group by h->>'id'having count(*)<>1)
   or exists(select 1 from jsonb_array_elements(source->'returns')h where h->>'status'<>'DRAFT'
    and not exists(select 1 from jsonb_array_elements(source->'return_items')i where i->>'return_id'=h->>'id'))
   or(select count(*)from jsonb_array_elements(source->'returns')h where h->>'id'=ret::text and h=to_jsonb(r))<>1
   or exists(select 1 from jsonb_array_elements(source->'return_items')i where jsonb_typeof(i)is distinct from'object'
    or i->>'id'is null or i->>'product_id'is null or coalesce(i->>'refund_amount','')!~'^[0-9]+([.][0-9]{1,2})?$'
    or(select count(*)from jsonb_array_elements(source->'returns')h where h->>'id'=i->>'return_id')<>1
    or(select count(*)from jsonb_array_elements(source->'allocations')a join jsonb_array_elements(source->'items')s
     on s->>'id'=a->>'sale_item_id'where a->>'id'=i->>'sale_stock_allocation_id'and s->>'product_id'=i->>'product_id')<>1)
   or exists(select 1 from jsonb_array_elements(source->'return_items')i group by i->>'id'having count(*)<>1)then
   cap_source_unavailable:=true;
  end if;
  if not cap_source_unavailable then
  for cap_line in select value from jsonb_array_elements(p#>'{replacement,items}')loop
   select count(*)into cap_count from jsonb_array_elements(source->'allocations')a where a->>'id'=cap_line->>'allocation_id';
   if cap_count<>1 then cap_source_unavailable:=true;continue;end if;
   select a into strict cap_allocation from jsonb_array_elements(source->'allocations')a where a->>'id'=cap_line->>'allocation_id';
   select count(*)into cap_count from jsonb_array_elements(source->'items')i where i->>'id'=cap_allocation->>'sale_item_id';
   if cap_count<>1 then cap_source_unavailable:=true;continue;end if;
   select i into strict cap_item from jsonb_array_elements(source->'items')i where i->>'id'=cap_allocation->>'sale_item_id';
   if cap_item->>'sale_id'is distinct from sale::text or coalesce((cap_item->>'qty_pcs')::integer,0)<=0
    or cap_item->>'line_total'is null or coalesce((cap_allocation->>'qty_pcs')::integer,0)<(cap_line->>'qty_pcs')::integer then
    cap_source_unavailable:=true;continue;end if;
   -- Exact erp.normalize_sales_return_item_from_allocation arithmetic: its
   -- numeric(24,6) assignment precedes the 0.01 tolerance, never cent rounding.
   max_refund:=case when(cap_item->>'qty_pcs')::integer>0 then
    ((cap_item->>'line_total')::numeric(24,6)/(cap_item->>'qty_pcs')::integer)*(cap_line->>'qty_pcs')::integer else 0 end;
   cap_exceeded:=cap_exceeded or (cap_line->>'refund_amount')::numeric>max_refund+0.01;
   cap_inputs:=cap_inputs||jsonb_build_array(jsonb_build_object('allocation',cap_allocation,'sale_item',cap_item,
    'qty_pcs',cap_line->'qty_pcs','refund_amount',cap_line->'refund_amount','max_refund_native_numeric24_6',max_refund::text));
  end loop;
  end if;
  if not cap_source_unavailable then
   -- Exact erp.post_sales_return product cap: all sale items for the product,
   -- only peer POSTED returns, numeric(24,6) sums, strict > with no tolerance.
   -- Native reverses the old current return before posting its replacement;
   -- exclude exactly that old id here, never its whole family or other peers.
   for cap_product in select distinct i#>>'{sale_item,product_id}'from jsonb_array_elements(cap_inputs)i order by 1 loop
    select coalesce(sum((i->>'line_total')::numeric),0)into product_sale_value
     from jsonb_array_elements(source->'items')i where i->>'sale_id'=sale::text and i->>'product_id'=cap_product;
    select coalesce(sum((i->>'refund_amount')::numeric),0)into prior_product_refund
     from jsonb_array_elements(source->'return_items')i join jsonb_array_elements(source->'returns')h on h->>'id'=i->>'return_id'
     where h->>'sale_id'=sale::text and h->>'id'<>ret::text and h->>'status'='POSTED'and i->>'product_id'=cap_product;
    select coalesce(sum((i->>'refund_amount')::numeric),0)into current_product_refund
     from jsonb_array_elements(cap_inputs)i where i#>>'{sale_item,product_id}'=cap_product;
    cap_exceeded:=cap_exceeded or prior_product_refund+current_product_refund>product_sale_value;
    cap_products:=cap_products||jsonb_build_array(jsonb_build_object('product_id',cap_product,
     'sold_value_native_numeric24_6',product_sale_value::text,'peer_POSTED_refund_native_numeric24_6',prior_product_refund::text,
     'replacement_refund_native_numeric24_6',current_product_refund::text,'excluded_current_return_id',ret));
   end loop;
  end if;
 end if;
 if cap_source_unavailable then issues:=issues||'"REFUND_CAP_SOURCE_UNAVAILABLE"'::jsonb;end if;
 if cap_exceeded then issues:=issues||'"REFUND_EXCEEDS_ORIGINAL_NET_SALES_CAP"'::jsonb;end if;
 if cp7_credit_incoming.incoming_applied_v1(sale)<>0 or exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=sale)then
  issues:=issues||'"INCOMING_CREDIT_CORRECTION_ADAPTER_REQUIRED"'::jsonb;end if;
 if erp.resolve_accounting_transaction_date(j.economic_date)is distinct from j.transaction_date then
  issues:=issues||'"CAUSAL_BOOK_FLOOR_ADAPTER_REQUIRED"'::jsonb;end if;
 if exists(select 1 from erp.fg_lots l where l.id=any(cp7_credit.source_hpp_lot_ids_v1(sale))and(l.po_id is not null or l.lot_origin='CONVERSION'))
  or exists(select 1 from erp.opening_lot_hpp_gl_state where lot_id=any(cp7_credit.source_hpp_lot_ids_v1(sale)))
  or exists(select 1 from erp.opening_hpp_corrections where lot_id=any(cp7_credit.source_hpp_lot_ids_v1(sale)))
  or exists(select 1 from erp.fg_lots l where l.id=any(cp7_credit.source_hpp_lot_ids_v1(sale))and
   ((select count(*)from erp.hpp_versions h where h.lot_id=l.id)<>1 or(select count(*)from erp.hpp_versions h where h.lot_id=l.id and h.is_current)<>1))
  or exists(select 1 from erp.be_conversion_sources_v1 s join erp.fg_lots l on l.id=s.source_lot_id where l.po_id is null)then
  issues:=issues||'"STOCK_HPP_CLASS_ADAPTER_REQUIRED"'::jsonb;end if;
 for f in select value from jsonb_array_elements(inp->'families')loop
  if f->>'family_id'=family::text then
   select coalesce(jsonb_agg(case when v->>'id'='journal:'||j.id::text then
    v||jsonb_build_object('amount',cp7_credit.cent_text((v->>'amount')::numeric-delta),'source_sha256',ow04_source_proposal.sha(p->'replacement'))else v end
    order by v->>'id'collate"C"),'[]')into events from jsonb_array_elements(f->'events')v;
   if not exists(select 1 from jsonb_array_elements(f->'events')v where v->>'id'='journal:'||j.id::text)then
    raise exception 'CP7_CREDIT_DE_SOURCE_EVENT_NOT_IN_FAMILY';end if;
   f:=jsonb_set(f,'{events}',events);
  end if;
  families:=families||jsonb_build_array(f);
 end loop;
 after_inp:=jsonb_set(inp,'{families}',families);review:=cp7_credit_correction_de.review_vectors_v1(inp,after_inp);
 if delta<=0 then issues:=issues||'"SIGNED_DECREASE_ADAPTER_REQUIRED"'::jsonb;end if;
 active:=cp7_credit_correction_de.active_consumers_v1(sale);
 if review->'requires_undo'='true'::jsonb then issues:=issues||to_jsonb(case when jsonb_array_length(active)>0
  then'UNDO_ACTIVE_CONSUMERS_FIRST'else'HISTORICAL_CAPACITY_ADAPTER_REQUIRED'end);end if;
 if exists(select 1 from jsonb_array_elements(review->'families')ff where(ff->>'needs_cohort_configuration')::boolean
  or exists(select 1 from jsonb_array_elements(ff->'vector')v where(v->>'amount')::numeric<0))then
  issues:=issues||'"SIGNED_COMPONENT_ADAPTER_REQUIRED"'::jsonb;end if;
 binding:=jsonb_build_object('payload',p-'credit_review_token','authority',authority,'source',source,'refund_cap_basis',cap_inputs,
  'refund_product_cap_basis',cap_products,'profile',profile,'input',inp,'review',review);
 return jsonb_build_object('contract_version','cp7.credit-correction-de.v1','state',case when issues='[]'::jsonb then'READY'else'REFUSE'end,
  'review_token',ow04_source_proposal.sha(binding),'credit_delta',review->'credit_delta','before_available',review->'before_available',
  'after_available',review->'after_available','issues',issues,'active_consumers',active,
  'families',review->'families','source_authority_proven',true,'increase_policy','AUTO_CREDIT_INCREMENT',
  'shortfall_policy','UNDO_ACTIVE_CONSUMERS_FIRST','replacement_invoice_policy','AUTO_TRANSFER_TO_REPLACEMENT');
end $$;

create function cp7_credit_correction_de.workspace_v1(p jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare result jsonb;payload jsonb;credit jsonb;begin
 result:=cp7_sales_return_correction.workspace(p-'proposed');
 if not cp7_credit_correction_de.participates_v1((p->>'return_id')::uuid)then return result;end if;
 if p?'proposed'then
  if jsonb_typeof(p->'proposed')is distinct from'object'or not(p->'proposed'?&array['replacement','change_reason'])
   or (p->'proposed')-array['replacement','change_reason']<>'{}'::jsonb then raise exception 'CP7_CREDIT_DE_PROPOSED_FIELDS_REQUIRED';end if;
  payload:=jsonb_build_object('sale_id',p->'sale_id','return_id',p->'return_id','review_token',result#>'{source,review_token}',
   'return_review_token',result->'return_review_token','replacement',p#>'{proposed,replacement}','change_reason',p#>'{proposed,change_reason}');
  credit:=cp7_credit_correction_de.quote_v1(payload);
 else credit:=jsonb_build_object('contract_version','cp7.credit-correction-de.v1','state','REVIEW_REQUIRED','review_token',null,
  'credit_delta',null,'before_available',null,'after_available',null,'issues','[]'::jsonb,
  'active_consumers',cp7_credit_correction_de.active_consumers_v1((p->>'sale_id')::uuid),'families','[]'::jsonb,
  'source_authority_proven',false,'increase_policy','AUTO_CREDIT_INCREMENT','shortfall_policy','UNDO_ACTIVE_CONSUMERS_FIRST',
  'replacement_invoice_policy','AUTO_TRANSFER_TO_REPLACEMENT');end if;
 return result||jsonb_build_object('credit_correction',credit);
end $$;

create function cp7_credit_correction_de.prepare_v1(p jsonb,p_request uuid,p_expected text,p_authority jsonb)returns void
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare quote jsonb;src jsonb;inp jsonb;profile jsonb;ord bigint;previous uuid;lots uuid[];hpps uuid[];fresh uuid[];begin
 -- Existing command already owns FG, invoice/return/item/allocation locks and CAS.
 -- Complete the exact physical/HPP/source/account/period graph before effects.
 if exists(select 1 from cp7_credit_correction_de.work_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_credit.execution_context where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
  raise exception 'CP7_CREDIT_DE_NESTED_OPERATION';end if;
 src:=ow04_source_proposal.locked_source_family((p->>'sale_id')::uuid);
 if src->>'source_status'<>'BASE_COLLECTED'or src#>>'{family,root_sale_id}'<>p->>'sale_id'
  or src#>>'{family,current_leaf_id}'<>p->>'sale_id'then raise exception 'CP7_CREDIT_DE_FLAT_CURRENT_SOURCE_REQUIRED';end if;
 perform cp7_credit.assert_source_native_trigger_census_v1();
 lots:=cp7_credit.source_hpp_lot_ids_v1((p->>'sale_id')::uuid);
 perform 1 from erp.fg_inventory_balances b where exists(select 1 from erp.sales_return_items i where i.return_id=(p->>'return_id')::uuid
  and(i.product_id,i.location_id,i.quality_grade)=(b.product_id,b.location_id,b.quality_grade))order by b.product_id,b.location_id,b.quality_grade for update;
 perform 1 from erp.fg_stock_movements where lot_id=any(lots)order by id for update;
 perform 1 from erp.fg_lots where id=any(lots)order by id for update;
 select coalesce(array_agg(id order by id),'{}')into hpps from erp.hpp_versions where lot_id=any(lots);
 perform 1 from erp.hpp_versions where id=any(hpps)order by id for share;
 select coalesce(array_agg(id order by id),'{}')into fresh from erp.hpp_versions where lot_id=any(lots);
 if fresh is distinct from hpps or lots is distinct from cp7_credit.source_hpp_lot_ids_v1((p->>'sale_id')::uuid)then
  raise exception 'CP7_CREDIT_DE_LOCK_GRAPH_CHANGED';end if;
 lock table erp.accounting_account_mappings in share mode;
 perform 1 from erp.chart_accounts where id in(select c.ar_account_id from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id
  where f.family_root_sale_id=(p->>'sale_id')::uuid union select c.credit_account_id from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id
  where f.family_root_sale_id=(p->>'sale_id')::uuid)order by id for share;
 perform 1 from erp.accounting_period_control where singleton_id=1 for share;
 quote:=cp7_credit_correction_de.quote_v1(p);
 if cp7_sales_return_correction.access_now()is distinct from p_authority then raise exception 'CP7_SALES_ACCESS_CHANGED';end if;
 if quote->'state'<>'"READY"'::jsonb then raise exception 'CP7_CREDIT_DE_REVIEW_REFUSED'using detail=quote::text;end if;
 if p->>'credit_review_token'is distinct from quote->>'review_token'then raise exception 'CP7_CREDIT_DE_STALE_REVIEW';end if;
 perform cp7_credit.source_first_nonpo_hpp_alignment_v1(cp7_credit.source_native_snapshot_v1((p->>'sale_id')::uuid));
 select coalesce(max(operation_ordinal),0)+1 into ord from cp7_credit_correction_de.operations_v1 where sale_id=(p->>'sale_id')::uuid;
 select operation_id into previous from cp7_credit_correction_de.operations_v1 where sale_id=(p->>'sale_id')::uuid and operation_ordinal=ord-1;
 inp:=cp7_credit.initial_ordinal_input_v1((p->>'sale_id')::uuid);
 profile:=cp7_credit.inspect_current_materialized_profile((p->>'sale_id')::uuid,(p->>'sale_id')::uuid,(p->>'sale_id')::uuid);
 insert into cp7_credit_correction_de.work_v1(operation_id,operation_ordinal,predecessor_id,backend_pid,transaction_id,actor,request_id,sale_id,return_id,
  expected_version,payload,authority,period,before_source,before_input,before_profile,review,phase)
 values(gen_random_uuid(),ord,previous,pg_backend_pid(),txid_current(),auth.uid(),p_request,(p->>'sale_id')::uuid,(p->>'return_id')::uuid,p_expected,p,
  p_authority,(select to_jsonb(x)from erp.accounting_period_control x where singleton_id=1),cp7_credit.source_native_snapshot_v1((p->>'sale_id')::uuid),inp,profile,quote,'PREPARED');
end $$;

create function cp7_credit_correction_de.temporary_paid_v1(p_sale uuid,p_after boolean)returns numeric
language plpgsql volatile security definer set search_path=''as $$
declare w cp7_credit_correction_de.work_v1;paid numeric;begin
 perform cp7_credit_correction_de.assert_work_v1();select *into strict w from cp7_credit_correction_de.work_v1
  where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and sale_id=p_sale;
 select coalesce(sum(amount),0)into paid from erp.sales_payments where sale_id=p_sale and status='POSTED';
 return paid-(w.before_profile->>'I')::numeric-case when p_after then(w.review->>'credit_delta')::numeric else 0 end;
end $$;
create function cp7_credit_correction_de.reverse_enter_v1(p_action text,p_source uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
begin perform cp7_credit_correction_de.assert_work_v1();
 if not exists(select 1 from cp7_credit_correction_de.work_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current()
  and actor=auth.uid()and return_id=p_source and phase='PREPARED')or p_action<>'RETURN_REVERSE'then raise exception 'CP7_CREDIT_DE_REVERSE_CONTEXT_CHANGED';end if;
end $$;
create function cp7_credit_correction_de.reverse_reconciled_v1(p_action text,p_source uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
begin perform cp7_credit_correction_de.reverse_enter_v1(p_action,p_source);end $$;
create function cp7_credit_correction_de.reverse_complete_v1(p_action text,p_source uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
begin perform cp7_credit_correction_de.reverse_enter_v1(p_action,p_source);
 if not exists(select 1 from erp.sales_returns where id=p_source and status='REVERSED')then raise exception 'CP7_CREDIT_DE_REVERSE_NOT_COMPLETE';end if;
 update cp7_credit_correction_de.work_v1 set phase='REVERSED'where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();end $$;
create function cp7_credit_correction_de.native_return_enter_v1(p_return uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
declare w cp7_credit_correction_de.work_v1;r erp.sales_returns;begin
 perform cp7_credit_correction_de.assert_work_v1();select *into strict w from cp7_credit_correction_de.work_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 select *into strict r from erp.sales_returns where id=p_return;
 if w.phase<>'REVERSED'or r.sale_id<>w.sale_id or r.status<>'DRAFT'or r.return_number<>'K-'||w.request_id::text
  or r.physical_at is distinct from(w.payload#>>'{replacement,physical_at}')::timestamptz then raise exception 'CP7_CREDIT_DE_OWN_REPLACEMENT_REQUIRED';end if;
 update cp7_credit_correction_de.work_v1 set phase='POSTING',replacement_id=p_return where operation_id=w.operation_id;
end $$;
create function cp7_credit_correction_de.native_return_guard_v1(p_return uuid,p_refund numeric,p_net numeric,p_paid numeric)returns numeric
language plpgsql volatile security definer set search_path=''as $$
declare w cp7_credit_correction_de.work_v1;total numeric;net numeric;paid numeric;answer numeric;begin
 perform cp7_credit_correction_de.assert_work_v1();select *into strict w from cp7_credit_correction_de.work_v1
  where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and replacement_id=p_return and phase='POSTING';
 select sum((v->>'refund_amount')::numeric)into total from jsonb_array_elements(w.payload#>'{replacement,items}')v;
 select sum(line_total)into net from erp.sales_items where sale_id=w.sale_id;
 net:=net-total-(select coalesce(sum(i.refund_amount),0)from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where r.sale_id=w.sale_id and r.status='POSTED');
 select coalesce(sum(amount),0)into paid from erp.sales_payments where sale_id=w.sale_id and status='POSTED';
 answer:=cp7_credit_correction_de.temporary_paid_v1(w.sale_id,true);
 if(p_refund,p_net,p_paid)is distinct from(total,net,paid)or answer<0 or answer>net then raise exception 'CP7_CREDIT_DE_NATIVE_TOTALS_CHANGED';end if;
 return answer;
end $$;
create function cp7_credit_correction_de.native_return_complete_v1(p_return uuid,p_refund numeric,p_net numeric)returns numeric
language plpgsql volatile security definer set search_path=''as $$
declare w cp7_credit_correction_de.work_v1;begin
 perform cp7_credit_correction_de.assert_work_v1();select *into strict w from cp7_credit_correction_de.work_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and replacement_id=p_return and phase='POSTING';
 return cp7_credit_correction_de.temporary_paid_v1(w.sale_id,true);
end $$;
create function cp7_credit_correction_de.native_return_leave_v1(p_return uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
begin perform cp7_credit_correction_de.assert_work_v1();
 if not exists(select 1 from erp.sales_returns where id=p_return and status='POSTED')then raise exception 'CP7_CREDIT_DE_REPLACEMENT_NOT_POSTED';end if;
 update cp7_credit_correction_de.work_v1 set phase='POSTED'where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and replacement_id=p_return and phase='POSTING';
 if not found then raise exception 'CP7_CREDIT_DE_POSTING_PHASE_CHANGED';end if;end $$;
create function cp7_credit_correction_de.assert_nonopening_v1(p_return uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
begin perform cp7_credit_correction_de.assert_work_v1();if exists(select 1 from erp.sales_return_items i join erp.opening_lot_hpp_gl_state s on s.lot_id=i.lot_id where i.return_id=p_return)
 then raise exception 'CP7_CREDIT_DE_OPENING_HPP_UNSUPPORTED';end if;end $$;
