do $not_an_installer$begin raise exception 'OW04_RECONCILIATION_REQUIRES_COMPLETE_ATOMIC_COMPOSITION';end $not_an_installer$;

create function cp7_credit.source_operation_owns_v1(p_action text,p_source uuid)returns boolean
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select exists(select 1 from cp7_credit.source_operation_work_v1 where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid()and action=p_action and source_id=p_source)
$$;

create function cp7_credit.source_hpp_lot_ids_v1(p_sale uuid)returns uuid[]
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select coalesce(array_agg(l.id order by l.id),'{}'::uuid[])from erp.fg_lots l
 where l.product_id in(select i.product_id from erp.sales_items i where i.sale_id=p_sale)
  or l.po_id in(select l0.po_id from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id
   join erp.fg_lots l0 on l0.id=a.lot_id where i.sale_id=p_sale)
$$;

create function cp7_credit.source_hpp_balances_v1(p_sale uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare g record;b jsonb;t jsonb;answer jsonb:='[]';fg uuid;cogs uuid;expense uuid;income uuid;
begin
 fg:=cp7_credit.account_by_mapping_v1('FG_INVENTORY');cogs:=cp7_credit.account_by_mapping_v1('COGS');
 expense:=cp7_credit.account_by_mapping_v1('OTHER_EXPENSE');income:=cp7_credit.account_by_mapping_v1('OTHER_INCOME');
 for g in select distinct case when l.po_id is null then l.product_id end product_id,l.po_id
  from erp.fg_lots l where l.id=any(cp7_credit.source_hpp_lot_ids_v1(p_sale))order by l.po_id nulls first,product_id loop
  t:=cp7_credit.initial_hpp_targets_v1(g.product_id,g.po_id,'[]',false)->'target';
  if g.po_id is null then
   select jsonb_build_object('fg_value',coalesce(sum(l.debit-l.credit)filter(where l.account_id=fg),0),
    'cogs_value',coalesce(sum(l.debit-l.credit)filter(where l.account_id=cogs),0),
    'other_out_value',coalesce(sum(l.debit-l.credit)filter(where l.account_id in(expense,income)),0))into b
    from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id left join erp.journal_entries o on o.id=j.reversal_of_id
    where l.product_id=g.product_id and l.po_id is null and j.status in('POSTED','REVERSED')
     and(j.source_type<>'PRODUCT_CONVERSION'or erp.be_nonpo_admitted_v1(j.source_id))
     and(j.source_type<>'JOURNAL_REVERSAL'or o.source_type is distinct from'PRODUCT_CONVERSION'or erp.be_nonpo_admitted_v1(o.source_id));
   b:=b||jsonb_build_object('hpp_total_cost',(b->>'fg_value')::numeric+(b->>'cogs_value')::numeric+(b->>'other_out_value')::numeric);
  else b:=cp7_credit.initial_po_hpp_book_v1(g.po_id,fg,cogs,expense,income);end if;
  answer:=answer||jsonb_build_array(jsonb_build_object('product_id',g.product_id,'po_id',g.po_id,'target',t,'book',b));
 end loop;
 return answer;
end $$;

-- The durable current financial reader needs only these source documents,
-- never a new HPP/global-stock scan or a new account-authority decision.
create function cp7_credit.source_document_snapshot_v1(p_sale uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 with events as(select value e from jsonb_array_elements(cp7_credit.initial_base_events_v1(p_sale)))
 select jsonb_build_object('sale',(select to_jsonb(h)from erp.sales_headers h where h.id=p_sale),
  'items',(select coalesce(jsonb_agg(to_jsonb(i)order by i.id),'[]')from erp.sales_items i where i.sale_id=p_sale),
  'allocations',(select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]')from erp.sale_stock_allocations a
   join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=p_sale),
  'payments',(select coalesce(jsonb_agg(to_jsonb(p)order by p.id),'[]')from erp.sales_payments p where p.sale_id=p_sale),
  'payment_posting_facts',(select coalesce(jsonb_agg(to_jsonb(f)order by f.payment_id),'[]')from erp.sales_payment_posting_facts f where f.sale_id=p_sale),
  'payment_reversal_facts',(select coalesce(jsonb_agg(to_jsonb(f)order by f.payment_id),'[]')from erp.sales_payment_reversal_facts f
   join erp.sales_payments p on p.id=f.payment_id where p.sale_id=p_sale),
  'returns',(select coalesce(jsonb_agg(to_jsonb(r)order by r.id),'[]')from erp.sales_returns r where r.sale_id=p_sale),
  'return_items',(select coalesce(jsonb_agg(to_jsonb(i)order by i.id),'[]')from erp.sales_return_items i
   join erp.sales_returns r on r.id=i.return_id where r.sale_id=p_sale),
  'base_events',cp7_credit.initial_base_events_v1(p_sale),
  'journals',(select coalesce(jsonb_agg(jsonb_build_object('id',j.id,'status',j.status,
   'immutable_payload',cp7_credit.materialized_journal_payload(j.id))order by j.id),'[]')from erp.journal_entries j
   where j.id in(select substring(e->>'id'from 9)::uuid from events)),
  'advance_links',(select coalesce(jsonb_agg(to_jsonb(l)order by l.payment_id),'[]')from erp.initial_import_prepayment_payments l
   join erp.sales_payments p on p.id=l.payment_id where p.sale_id=p_sale))
$$;

-- Owned-operation before/actual/final snapshots additionally bind the full
-- physical/HPP graph. Status stays separate from immutable journal payload.
create function cp7_credit.source_native_snapshot_v1(p_sale uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 with lots as(select l.*from erp.fg_lots l where l.id=any(cp7_credit.source_hpp_lot_ids_v1(p_sale)))
 select cp7_credit.source_document_snapshot_v1(p_sale)||jsonb_build_object(
  'fg_lots',(select coalesce(jsonb_agg(to_jsonb(l)order by l.id),'[]')from lots l),
  'hpp_versions',(select coalesce(jsonb_agg(to_jsonb(h)order by h.id),'[]')from erp.hpp_versions h where h.lot_id in(select id from lots)),
  'stock_movements',(select coalesce(jsonb_agg(to_jsonb(m)order by m.id),'[]')from erp.fg_stock_movements m where m.lot_id in(select id from lots)),
  'inventory_balances',(select coalesce(jsonb_agg(to_jsonb(b)order by b.product_id,b.location_id,b.quality_grade),'[]')
   from erp.fg_inventory_balances b where b.product_id in(select product_id from lots)),
  'opening_hpp_states',(select coalesce(jsonb_agg(to_jsonb(s)order by s.lot_id),'[]')from erp.opening_lot_hpp_gl_state s where s.lot_id in(select id from lots)),
  'opening_hpp_corrections',(select coalesce(jsonb_agg(to_jsonb(c)order by c.id),'[]')from erp.opening_hpp_corrections c where c.lot_id in(select id from lots)),
  'po_hpp_states',(select coalesce(jsonb_agg(to_jsonb(s)order by s.po_id),'[]')from erp.po_hpp_gl_state s where s.po_id in(select po_id from lots)),
  'nonpo_hpp_events',(select coalesce(jsonb_agg(to_jsonb(e)order by e.id),'[]')from erp.non_po_hpp_gl_sync_events_v2620f e where e.product_id in(select product_id from lots)),
  'po_hpp_events',(select coalesce(jsonb_agg(to_jsonb(e)order by e.id),'[]')from erp.po_hpp_gl_events e where e.po_id in(select po_id from lots)),
  'hpp_journals',(select coalesce(jsonb_agg(jsonb_build_object('id',j.id,'status',j.status,
    'immutable_payload',cp7_credit.materialized_journal_payload(j.id))order by j.id),'[]')from erp.journal_entries j where j.id in(
     select l.journal_entry_id from erp.journal_lines l where l.product_id in(select product_id from lots)or l.po_id in(select po_id from lots))),
  'hpp_balances',cp7_credit.source_hpp_balances_v1(p_sale),
  'hpp_accounts',cp7_credit.initial_hpp_account_facts_v1(),
  'period_snapshot',(select to_jsonb(p)from erp.accounting_period_control p where singleton_id=1),
  'hpp_support',(select coalesce(jsonb_agg(jsonb_build_object('product_id',x.product_id,'po_id',x.po_id,
   'facts',cp7_credit.initial_hpp_support_v1(x.product_id,x.po_id))order by x.product_id,x.po_id),'[]')from(
    select distinct i.product_id,l.po_id from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots l on l.id=a.lot_id where i.sale_id=p_sale)x))
$$;

create function cp7_credit.assert_source_operation_work_v1(p_operation uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.source_operation_work_v1;q cp7_sales.requests;
begin
 if current_setting('transaction_isolation')<>'read committed'or auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'then
  raise exception using errcode='42501',message='CP7_CREDIT_SOURCE_CURRENT_ACTOR_REQUIRED';end if;
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=p_operation
  and backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 perform cp7_credit.assert_only_own_sales_source_context_v1(w.sale_id,w.action);
 select *into strict q from cp7_sales.requests where actor=w.actor and request_id=w.request_id;
 if q.response is not null or(q.action,q.payload,q.expected_version)is distinct from(w.action,w.payload,w.expected_version)
  or w.payload_sha256 is distinct from cp7_credit.pg_jsonb_sha256(w.payload)
  or(w.payload->>'sale_id')::uuid<>w.sale_id
  or(w.payload->>case when w.action='RETURN_REVERSE'then'return_id'else'payment_id'end)::uuid<>w.source_id then
  raise exception 'CP7_CREDIT_SOURCE_OWN_PENDING_REQUEST_REQUIRED';end if;
 if cp7_sales.command_access(w.action)is distinct from w.authority_snapshot then
  raise exception using errcode='42501',message='CP7_CREDIT_SOURCE_ACCESS_CHANGED';end if;
 if(select to_jsonb(c)from erp.accounting_period_control c where singleton_id=1)is distinct from w.period_snapshot then
  raise exception 'CP7_CREDIT_SOURCE_PERIOD_CHANGED';end if;
 if exists(select 1 from jsonb_array_elements(w.account_facts)x where
   (select to_jsonb(a)from erp.chart_accounts a where a.id=(x->>'id')::uuid)is distinct from x)
  or exists(select 1 from cp7_credit.initial_return_work where backend_pid=w.backend_pid and transaction_id=w.transaction_id)
  or exists(select 1 from cp7_credit.return_command_scope where backend_pid=w.backend_pid and transaction_id=w.transaction_id)then
  raise exception 'CP7_CREDIT_SOURCE_ACCOUNT_OR_NESTED_OPERATION_CHANGED';end if;
end $$;

-- Called from the captured postgres-owned CP7 apply_command after its exact
-- pending request, CAS/review and original source-status checks, before Native.
create function cp7_credit.source_request_enter_v1(p_action text,p_payload jsonb,p_request uuid,p_expected text)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare sale uuid:=(p_payload->>'sale_id')::uuid;v_source_id uuid;q cp7_sales.requests;src jsonb;
 before_input jsonb;before_result jsonb;profile jsonb;accounts jsonb;period jsonb;authority jsonb;blocked jsonb;
 op uuid:=gen_random_uuid();prior_op uuid;op_ordinal bigint;lot_ids uuid[];fresh_lot_ids uuid[];hpp_ids uuid[];fresh_hpp_ids uuid[];
begin
 if p_action not in('RETURN_REVERSE','PAYMENT_REVERSE')or p_action is null then raise exception 'CP7_CREDIT_SOURCE_ACTION_UNIMPLEMENTED';end if;
 if not exists(select 1 from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=sale)
  and not exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=sale)then return;end if;
 if auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'or current_setting('transaction_isolation')<>'read committed'then
  raise exception using errcode='42501',message='CP7_CREDIT_SOURCE_CURRENT_ACTOR_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform cp7_credit.assert_only_own_sales_source_context_v1(sale,p_action);
 authority:=cp7_sales.command_access(p_action);
 perform cp7_credit.assert_source_native_trigger_census_v1();
 select *into strict q from cp7_sales.requests where actor=auth.uid()and request_id=p_request;
 if q.response is not null or(q.action,q.payload,q.expected_version)is distinct from(p_action,p_payload,p_expected)then
  raise exception 'CP7_CREDIT_SOURCE_OWN_PENDING_REQUEST_REQUIRED';end if;
 if exists(select 1 from cp7_credit.source_operation_work_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_credit.execution_context where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
  raise exception 'CP7_CREDIT_SOURCE_NESTED_OPERATION';end if;
 v_source_id:=(p_payload->>case when p_action='RETURN_REVERSE'then'return_id'else'payment_id'end)::uuid;
 if p_action='RETURN_REVERSE'then
  if not exists(select 1 from erp.sales_returns where id=v_source_id and sale_id=sale and status='POSTED')then
   raise exception 'CP7_CREDIT_SOURCE_ACTUAL_RETURN_REQUIRED';end if;
 else
  if not exists(select 1 from erp.sales_payments where id=v_source_id and sale_id=sale and status='POSTED')then
   raise exception 'CP7_CREDIT_SOURCE_ACTUAL_PAYMENT_REQUIRED';end if;
  if exists(select 1 from erp.sales_payments where id=v_source_id and(cash_account_id is null or payment_method='OPENING_ADVANCE'))then
   raise exception 'CP7_CREDIT_SOURCE_ADVANCE_INVERSE_UNQUALIFIED';end if;
 end if;
 src:=ow04_source_proposal.locked_source_family(sale);
 if src->>'source_status'is distinct from'BASE_COLLECTED'or src#>>'{family,current_leaf_id}'is distinct from sale::text
  or src#>>'{family,root_sale_id}'is distinct from sale::text then
  raise exception 'CP7_CREDIT_SOURCE_SIMPLE_NATIVE_FAMILY_REQUIRED';end if;
 perform cp7_credit.assert_simple_native_base_v1(sale);
 -- First bounded adapter cannot adopt Native's global conversion expansion.
 -- Refuse before effects until that entire graph has an owning lock/proof.
 if exists(select 1 from erp.be_conversion_sources_v1 s
  join erp.fg_lots l on l.id=s.source_lot_id where l.po_id is null)then
  raise exception 'CP7_CREDIT_SOURCE_GLOBAL_HPP_GRAPH_UNQUALIFIED';end if;
 select coalesce(jsonb_agg(jsonb_build_object('event_id',e.id,'cohort_id',e.cohort_id,'event_kind',e.event_kind,
  'journal_id',e.journal_id,'source_sale_id',c.source_sale_id,'source_return_id',c.source_return_id)order by e.id),'[]')into blocked
  from cp7_credit.consumption_events e join cp7_credit.cohorts c on c.id=e.cohort_id
  join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=sale or e.target_sale_id=sale;
 if jsonb_array_length(blocked)>0 then
  raise exception 'CP7_CREDIT_SOURCE_CONSUMERS_REQUIRE_UNDO'using detail=blocked::text;end if;
 if exists(select 1 from erp.initial_import_prepayment_payments l join erp.sales_payments p on p.id=l.payment_id where p.sale_id=sale)
  or exists(select 1 from erp.sales_payments where sale_id=sale and(cash_account_id is null or payment_method='OPENING_ADVANCE'))then
  raise exception 'CP7_CREDIT_SOURCE_ADVANCE_INVERSE_UNQUALIFIED';end if;
 if p_action='RETURN_REVERSE'then
  perform 1 from erp.locations where id in(select location_id from erp.sales_return_items where return_id=v_source_id)order by id for share;
  perform 1 from erp.fg_inventory_balances b where exists(select 1 from erp.sales_return_items i where i.return_id=v_source_id
   and(i.product_id,i.location_id,i.quality_grade)=(b.product_id,b.location_id,b.quality_grade))
   order by b.product_id,b.location_id,b.quality_grade for update;
  perform 1 from erp.fg_stock_movements m where m.source_type='SALES_RETURN_ITEM'
   and exists(select 1 from erp.sales_return_items i where i.id=m.source_id and i.return_id=v_source_id)order by m.id for update;
 end if;
 lot_ids:=cp7_credit.source_hpp_lot_ids_v1(sale);
 select coalesce(array_agg(id order by id),'{}')into hpp_ids from erp.hpp_versions where lot_id=any(lot_ids);
 perform 1 from erp.fg_lots where id=any(lot_ids)order by id for update;
 perform 1 from erp.hpp_versions where id=any(hpp_ids)order by id for share;
 select coalesce(array_agg(id order by id),'{}')into fresh_hpp_ids from erp.hpp_versions where lot_id=any(lot_ids);
 if hpp_ids is distinct from fresh_hpp_ids then raise exception 'CP7_CREDIT_SOURCE_HPP_LOCK_SET_CHANGED';end if;
 perform 1 from erp.opening_lot_hpp_gl_state where lot_id=any(lot_ids)order by lot_id for update;
 perform 1 from erp.opening_hpp_corrections where lot_id=any(lot_ids)order by id for share;
 perform 1 from erp.po_hpp_gl_state where po_id in(select po_id from erp.fg_lots where id=any(lot_ids))order by po_id for update;
 fresh_lot_ids:=cp7_credit.source_hpp_lot_ids_v1(sale);
 select coalesce(array_agg(id order by id),'{}')into fresh_hpp_ids from erp.hpp_versions where lot_id=any(fresh_lot_ids);
 if fresh_lot_ids is distinct from lot_ids or fresh_hpp_ids is distinct from hpp_ids then
  raise exception 'CP7_CREDIT_SOURCE_LOT_LOCK_SET_CHANGED';end if;
 -- Honest first vertical: preserve Native opening/cache/PO/conversion code;
 -- do not enter a class whose complete effects are not qualified yet.
 if exists(select 1 from erp.fg_lots where id=any(lot_ids)and po_id is not null)
  or exists(select 1 from erp.po_hpp_gl_state where po_id in(select po_id from erp.fg_lots where id=any(lot_ids)))then
  raise exception 'CP7_CREDIT_SOURCE_PO_HPP_INVERSE_UNQUALIFIED';end if;
 if exists(select 1 from erp.opening_lot_hpp_gl_state where lot_id=any(lot_ids))then
  raise exception 'CP7_CREDIT_SOURCE_OPENING_HPP_INVERSE_UNQUALIFIED';end if;
 if exists(select 1 from erp.opening_hpp_corrections where lot_id=any(lot_ids))
  or exists(select 1 from erp.fg_lots l where l.id=any(lot_ids)and
   ((select count(*)from erp.hpp_versions h where h.lot_id=l.id)<>1
    or(select count(*)from erp.hpp_versions h where h.lot_id=l.id and h.is_current)<>1))then
  raise exception 'CP7_CREDIT_SOURCE_RECOST_INVERSE_UNQUALIFIED';end if;
 if exists(select 1 from erp.fg_lots where id=any(lot_ids)and lot_origin='CONVERSION')then
  raise exception 'CP7_CREDIT_SOURCE_CONVERSION_INVERSE_UNQUALIFIED';end if;
 perform 1 from erp.chart_accounts where id in(select c.credit_account_id from cp7_credit.cohorts c
  join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=sale)
  or id in(select c.ar_account_id from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id
   where f.family_root_sale_id=sale)order by id for share;
 select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]')into accounts from erp.chart_accounts a where a.id in(
  select c.credit_account_id from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=sale
  union select c.ar_account_id from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=sale);
 before_input:=cp7_credit.source_reconciliation_input_v1(sale);
 before_result:=ow04_ordinal_wrapper.reconcile_v1(before_input);
 if not(before_result->>'arithmetic_supported')::boolean or exists(select 1 from jsonb_array_elements(before_result->'families')f
  where(f->>'has_reconciliation_effect')::boolean)then raise exception 'CP7_CREDIT_SOURCE_BEFORE_PROFILE_UNRECONCILED';end if;
 perform cp7_credit.assert_current_materialized_profile(sale,sale,sale);
 profile:=cp7_credit.inspect_current_materialized_profile(sale,sale,sale);
 select operation_id,operation_ordinal+1 into prior_op,op_ordinal from cp7_credit.source_operation_materializations_v1
  where sale_id=sale order by operation_ordinal desc limit 1;
 if prior_op is null then op_ordinal:=1;
 elsif not exists(select 1 from cp7_credit.source_operation_completions_v1 where operation_id=prior_op)then
  raise exception 'CP7_CREDIT_SOURCE_PREDECESSOR_NOT_COMPLETE';end if;
 perform 1 from erp.accounting_period_control where singleton_id=1 for share;
 select to_jsonb(c)into strict period from erp.accounting_period_control c where singleton_id=1;
 if cp7_sales.command_access(p_action)is distinct from authority then
  raise exception using errcode='42501',message='CP7_CREDIT_SOURCE_ACCESS_CHANGED';end if;
 insert into cp7_credit.source_operation_work_v1(operation_id,operation_ordinal,predecessor_operation_id,backend_pid,transaction_id,actor,request_id,action,sale_id,source_id,
  expected_version,payload,payload_sha256,authority_snapshot,phase,before_source,before_ordinal_input,before_ordinal_result,
  before_financial_profile,account_facts,period_snapshot)
 values(op,op_ordinal,prior_op,pg_backend_pid(),txid_current(),auth.uid(),p_request,p_action,sale,v_source_id,p_expected,p_payload,
  cp7_credit.pg_jsonb_sha256(p_payload),authority,'PREPARED',cp7_credit.source_native_snapshot_v1(sale),before_input,before_result,
  profile,accounts,period);
 perform cp7_credit.assert_source_operation_work_v1(op);
end $$;

do $private_source_requests$declare sig text;begin
 foreach sig in array array['source_operation_owns_v1(text,uuid)','source_hpp_lot_ids_v1(uuid)','source_hpp_balances_v1(uuid)',
  'source_document_snapshot_v1(uuid)','source_native_snapshot_v1(uuid)',
  'assert_source_operation_work_v1(uuid)','source_request_enter_v1(text,jsonb,uuid,text)']loop
  execute 'alter function cp7_credit.'||sig||' owner to postgres';
  execute 'revoke all on function cp7_credit.'||sig||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write';
 end loop;
end $private_source_requests$;
