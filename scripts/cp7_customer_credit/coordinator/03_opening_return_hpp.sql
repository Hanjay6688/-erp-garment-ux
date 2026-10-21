-- Atomic owning composition only. Native's opening status trigger normally
-- synchronizes HPP before post_sales_return builds its own cumulative lines.
-- For the exact guarded return, postpone that diagnostic refresh until the
-- full Native SALES_RETURN journal has been posted at its bound date pair.
do $not_an_installer$begin raise exception 'OW04_COORDINATOR_REQUIRES_ATOMIC_NATIVE_COMPOSITION';end $not_an_installer$;

create table cp7_credit.opening_return_hpp_work_v1(
 return_id uuid primary key,backend_pid integer not null,transaction_id bigint not null,
 owner_fact jsonb not null,lot_ids uuid[] not null,
 unique(backend_pid,transaction_id),
 check(jsonb_typeof(owner_fact)='object'and cardinality(lot_ids)>0)
);
alter table cp7_credit.opening_return_hpp_work_v1 owner to postgres;
alter table cp7_credit.opening_return_hpp_work_v1 enable row level security;
create policy deny_direct on cp7_credit.opening_return_hpp_work_v1 for all to public using(false)with check(false);
revoke all on cp7_credit.opening_return_hpp_work_v1 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;

create function cp7_credit.opening_return_hpp_owner_v1(p_return uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.initial_return_work;n cp7_credit.return_native_scope;r erp.sales_returns;
begin
 select *into strict r from erp.sales_returns where id=p_return;
 select *into w from cp7_credit.initial_return_work where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if w.operation_id is not null then
  perform cp7_credit.assert_return_owner_context(p_return);
  select *into strict n from cp7_credit.return_native_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current();
  if w.phase<>'ENTERED'or r.status<>'POSTED'or n.completed
   or(n.actor,n.request_id,n.return_id,n.source_sale_id,n.customer_id,n.origin,n.source_lock_sha256,n.projection_sha256)is distinct from
    (w.actor,w.request_id,p_return,w.source_sale_id,r.customer_id,w.origin,w.source_lock_sha256,w.projection_sha256)
   or n.native_refund is null or n.native_net_after is null or n.guard_effective_paid is null
   or(n.native_refund,n.native_net_after)is distinct from((w.projection->>'return_amount')::numeric,(w.projection->>'net_after')::numeric)
   or n.guard_effective_paid is distinct from((w.projection->>'raw_paid')::numeric-
    case when w.origin='REVIEWED_SETTLEMENT'then(w.projected_kernel->>'net_current_k')::numeric else 0 end)then
   raise exception 'CP7_CREDIT_OPENING_HPP_GUARDED_OWNER_REQUIRED';end if;
  perform erp.require_internal();
  return jsonb_build_object('kind','CP7_RETURN','operation_id',w.operation_id,'actor',w.actor,'request_id',w.request_id,
   'return_id',p_return,'sale_id',w.source_sale_id,'customer_id',r.customer_id,'projection_sha256',w.projection_sha256);
 end if;
 -- Direct Native EMPTY and all other existing contexts retain the original
 -- trigger. This adapter claims only the CP7 source-sealed initial return.
 return null;
end $$;

create function cp7_credit.defer_opening_return_hpp_v1(p_return uuid,p_old text,p_new text)returns boolean
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare owner_fact jsonb;lots uuid[];w cp7_credit.initial_return_work;g jsonb;
begin
 if p_old is distinct from'DRAFT'or p_new is distinct from'POSTED'then return false;end if;
 owner_fact:=cp7_credit.opening_return_hpp_owner_v1(p_return);
 if owner_fact is null then return false;end if;
 select *into strict w from cp7_credit.initial_return_work where return_id=p_return;
 for g in select value from jsonb_array_elements(w.projection#>'{hpp,groups}')loop
  if cp7_credit.initial_opening_hpp_source_v1((g->>'product_id')::uuid,(g->>'po_id')::uuid)is distinct from g->'opening_source'then
   raise exception 'CP7_CREDIT_OPENING_HPP_SEALED_SOURCE_CHANGED';end if;
 end loop;
 select array_agg(lot_id order by lot_id)into lots from(
  select distinct i.lot_id from erp.sales_return_items i join erp.fg_lots l on l.id=i.lot_id
  where i.return_id=p_return and l.lot_origin='OPENING'
   and exists(select 1 from erp.opening_lot_hpp_gl_state s where s.lot_id=l.id))x;
 if lots is null then return false;end if;
 if exists(select 1 from unnest(lots)as candidate(lot_id)where not((w.projection#>'{hpp,locked_lot_ids}')?candidate.lot_id::text))then
  raise exception 'CP7_CREDIT_OPENING_HPP_LOT_OUTSIDE_SEALED_LOCKS';end if;
 insert into cp7_credit.opening_return_hpp_work_v1 values(p_return,pg_backend_pid(),txid_current(),owner_fact,lots);
 return true;
end $$;

create function cp7_credit.flush_opening_return_hpp_v1(p_return uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.opening_return_hpp_work_v1;owner_fact jsonb;lots uuid[];p record;l uuid;before_support jsonb;
begin
 select *into w from cp7_credit.opening_return_hpp_work_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if not found then return;end if;
 owner_fact:=cp7_credit.opening_return_hpp_owner_v1(p_return);
 select array_agg(lot_id order by lot_id)into lots from(
  select distinct i.lot_id from erp.sales_return_items i join erp.fg_lots f on f.id=i.lot_id
  where i.return_id=p_return and f.lot_origin='OPENING'
   and exists(select 1 from erp.opening_lot_hpp_gl_state s where s.lot_id=f.id))x;
 if w.return_id<>p_return or owner_fact is null or w.owner_fact is distinct from owner_fact or w.lot_ids is distinct from lots then
  raise exception 'CP7_CREDIT_OPENING_HPP_DEFERRED_SCOPE_CHANGED';end if;
 for p in select distinct f.product_id from erp.fg_lots f where f.id=any(w.lot_ids)order by f.product_id loop
  -- Existing Native full-vector assertion, before diagnostics may do anything.
  perform erp.assert_non_po_product_hpp_target_book_v2620f(p.product_id);
  before_support:=cp7_credit.initial_hpp_support_v1(p.product_id,null);
  for l in select f.id from erp.fg_lots f where f.id=any(w.lot_ids)and f.product_id=p.product_id order by f.id loop
   perform cp7_credit.refresh_opening_return_hpp_diagnostics_v1(p_return,l);
  end loop;
  perform erp.assert_non_po_product_hpp_target_book_v2620f(p.product_id);
  if cp7_credit.initial_hpp_support_v1(p.product_id,null)is distinct from before_support then
   raise exception 'CP7_CREDIT_OPENING_HPP_DIAGNOSTICS_CHANGED_POSTED_SOURCE';end if;
 end loop;
 delete from cp7_credit.opening_return_hpp_work_v1 where return_id=p_return;
end $$;

create function cp7_credit.enforce_opening_return_hpp_closed_v1()returns trigger
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
begin
 if exists(select 1 from cp7_credit.opening_return_hpp_work_v1 where backend_pid=new.backend_pid and transaction_id=new.transaction_id)then
  raise exception 'CP7_CREDIT_OPENING_HPP_DEFERRED_SCOPE_LEAK';end if;
 return null;
end $$;
create constraint trigger opening_return_hpp_closed after insert or update on cp7_credit.opening_return_hpp_work_v1
 deferrable initially deferred for each row execute function cp7_credit.enforce_opening_return_hpp_closed_v1();

do $private_opening_hpp$declare sig text;begin
 foreach sig in array array['opening_return_hpp_owner_v1(uuid)','defer_opening_return_hpp_v1(uuid,text,text)',
  'flush_opening_return_hpp_v1(uuid)','enforce_opening_return_hpp_closed_v1()']loop
  execute 'alter function cp7_credit.'||sig||' owner to postgres';
  execute 'revoke all on function cp7_credit.'||sig||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write';
 end loop;
end $private_opening_hpp$;
