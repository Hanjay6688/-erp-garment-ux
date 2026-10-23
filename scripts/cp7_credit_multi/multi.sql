-- OW-04b slice B step 1 (docs/cp7/d17-14/ow04/OW04B_SLICE_B_INVENTORY.md B2/B7/B10). Private readers only: no installed
-- function is changed by this file, no row is written. Later steps substitute them into the quote, the registration
-- admission and the per-cohort profile. With one return family they give exactly today's values (local_check.py).
create schema cp7_credit_multi authorization postgres;
revoke all on schema cp7_credit_multi from public,anon,authenticated,service_role,cp7_capture;

-- Every member return of the families with ordinal >= p_ordinal on this root invoice.
create function cp7_credit_multi.later_family_returns_v1(p_sale uuid,p_ordinal bigint)returns uuid[]
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select coalesce(array_agg(m.return_id order by m.return_id),'{}'::uuid[])
 from cp7_credit.return_family_members m join cp7_credit.return_families f on f.id=m.family_id
 where f.family_root_sale_id=p_sale and f.family_ordinal>=p_ordinal
$$;

-- B10a. The before-events of family p_ordinal: the retained collector cp7_credit.initial_base_events_v1, minus the whole
-- journal subtree (original, inverse, restatement) of every return in families >= p_ordinal. Each subtree is exactly
-- what the retained collector drops for that one return, so no collector logic is copied here.
create function cp7_credit_multi.family_before_events_v1(p_sale uuid,p_ordinal bigint)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare whole jsonb;removed text[]:='{}';r uuid;answer jsonb;
begin
 if p_sale is null or p_ordinal is null or p_ordinal<1 then raise exception 'CP7_CREDIT_MULTI_FAMILY_ORDINAL_REQUIRED';end if;
 whole:=cp7_credit.initial_base_events_v1(p_sale);
 foreach r in array cp7_credit_multi.later_family_returns_v1(p_sale,p_ordinal)loop
  select removed||coalesce(array_agg(x->>'id'),'{}')into removed from jsonb_array_elements(whole)x
   where not exists(select 1 from jsonb_array_elements(cp7_credit.initial_base_events_v1(p_sale,r))y where y->>'id'=x->>'id');
 end loop;
 select coalesce(jsonb_agg(v order by v->>'id'collate"C"),'[]')into answer from jsonb_array_elements(whole)v where not(v->>'id'=any(removed));
 return answer;
end $$;

-- B10b. The preserved source snapshot of family p_ordinal: the retained cp7_credit.initial_preserved_source_v1 with
-- the returns of families >= p_ordinal left out of prior_returns, prior_return_items, events and base_journals, using
-- the retained expressions (same ordering and collation) for those four keys. Every other key is the retained value.
create function cp7_credit_multi.family_preserved_source_v1(p_sale uuid,p_ordinal bigint)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare later uuid[];events jsonb;
begin
 later:=cp7_credit_multi.later_family_returns_v1(p_sale,p_ordinal);
 events:=cp7_credit_multi.family_before_events_v1(p_sale,p_ordinal);
 return cp7_credit.initial_preserved_source_v1(p_sale)||jsonb_build_object(
  'prior_returns',(select coalesce(jsonb_agg(to_jsonb(r)order by r.id),'[]')from erp.sales_returns r where r.sale_id=p_sale and not(r.id=any(later))),
  'prior_return_items',(select coalesce(jsonb_agg(to_jsonb(i)order by i.id),'[]')from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id
   where r.sale_id=p_sale and not(r.id=any(later))),
  'events',events,
  'base_journals',(select coalesce(jsonb_agg(cp7_credit.materialized_journal_payload((x->>'id')::uuid)order by x->>'id'),'[]')
   from(select jsonb_build_object('id',substring(e->>'id'from 9))x from jsonb_array_elements(events)e)z));
end $$;

-- B2/B7. Replacement for assert_zero_excess_v1(before_events) in the quote (p_own_return = the own draft or null) and in
-- the registration admission (p_own_return = the own return, already a member of its new family there).
-- No cohort in an EARLIER family: exactly the retained assert_zero_excess_v1 (first return and EMPTY prior families).
-- Otherwise every earlier family must be fully reconciled and its credit recognized, and before_events must be exactly
-- base plus all earlier families: then the kernel's D for the new return is that family's own target, and no earlier
-- target changes (ordinal attribution).
create function cp7_credit_multi.assert_prior_families_reconciled_v1(p_sale uuid,p_before_events jsonb,p_own_return uuid default null)
returns void language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare own bigint;result jsonb;expected jsonb;retained numeric;excess numeric;
begin
 select f.family_ordinal into own from cp7_credit.return_family_members m join cp7_credit.return_families f on f.id=m.family_id
  where m.return_id=p_own_return and f.family_root_sale_id=p_sale;
 if not exists(select 1 from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id
  where f.family_root_sale_id=p_sale and(own is null or f.family_ordinal<own))then
  perform cp7_credit.assert_zero_excess_v1(p_before_events);return;
 end if;
 expected:=case when own is null then cp7_credit.initial_base_events_v1(p_sale,p_own_return)
  else cp7_credit_multi.family_before_events_v1(p_sale,own)end;
 if p_before_events is distinct from expected then raise exception 'CP7_CREDIT_MULTI_BEFORE_EVENTS_NOT_EXACT';end if;
 -- Raises BASE_OVERFLOW_NONZERO when the invoice without its returns is overfunded on any date pair.
 result:=ow04_ordinal_wrapper.reconcile_v1(cp7_credit.initial_ordinal_input_v1(p_sale));
 if exists(select 1 from jsonb_array_elements(result->'families')x where(own is null or(x->'registration'->>'ordinal')::bigint<own)
  and(not coalesce((x->>'arithmetic_supported')::boolean,false)or(x->>'has_reconciliation_effect')::boolean))then
  raise exception 'CP7_CREDIT_MULTI_PRIOR_FAMILY_UNRECONCILED';end if;
 select coalesce(sum((x->>'retained_net_current')::numeric),0)into retained from jsonb_array_elements(result->'families')x
  where own is null or(x->'registration'->>'ordinal')::bigint<own;
 excess:=(ow04_pure_kernel.recognition_plan_v1('[]',p_before_events)->>'net_current_k')::numeric;
 if excess is distinct from retained then raise exception 'CP7_CREDIT_MULTI_PRIOR_EXCESS_NOT_RECOGNIZED';end if;
end $$;

do $private_multi$declare sig text;begin
 foreach sig in array array['later_family_returns_v1(uuid,bigint)','family_before_events_v1(uuid,bigint)',
  'family_preserved_source_v1(uuid,bigint)','assert_prior_families_reconciled_v1(uuid,jsonb,uuid)']loop
  execute 'alter function cp7_credit_multi.'||sig||' owner to postgres';
  execute 'revoke all on function cp7_credit_multi.'||sig||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write';
 end loop;
end $private_multi$;
