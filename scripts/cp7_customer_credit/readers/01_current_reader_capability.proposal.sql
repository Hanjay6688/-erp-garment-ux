-- SOURCE-ONLY OW04 proposal outside the product checkout. Not an installer.
-- This barrier and the deliberate unfinished validator are mandatory until the
-- complete source/ledger/owning-operation integration exists. No Native claim.
do $not_an_installer$ begin
 raise exception 'OW04_CURRENT_READER_REQUIRES_COMPLETE_FEATURE';
end $not_an_installer$;

-- Concrete, read-only assignment of an ACTUAL requested invoice. Never return
-- a leaf's payment/return numbers as the financial history of an old header.
create function cp7_credit.current_leaf_assignment(p_sale uuid)
returns table(root_sale_id uuid,current_leaf_id uuid,customer_id uuid,requested_status text)
language plpgsql stable security definer set search_path='' as $$
declare roots uuid[];ids uuid[];previous uuid;root uuid;revision bigint:=0;r record;h erp.sales_headers;
begin
 select * into strict h from erp.sales_headers where id=p_sale;
 select array_agg(distinct x.root_sale_id) into roots from cp7_note.revisions x
  where p_sale in(x.root_sale_id,x.previous_sale_id,x.replacement_sale_id);
 if cardinality(roots)>1 then raise exception 'CP7_CREDIT_NOTE_ROOT_AMBIGUOUS';end if;
 root:=coalesce(roots[1],p_sale);previous:=root;ids:=array[root];
 for r in select *from cp7_note.revisions x where x.root_sale_id=root order by x.revision loop
  revision:=revision+1;
  if r.revision<>revision or r.previous_sale_id<>previous or r.replacement_sale_id=any(ids)then
   raise exception 'CP7_CREDIT_NOTE_CHAIN_INVALID';end if;
  ids:=ids||r.replacement_sale_id;previous:=r.replacement_sale_id;
 end loop;
 if not p_sale=any(ids)or exists(select 1 from unnest(ids)x left join erp.sales_headers s on s.id=x
  where s.id is null or s.customer_id is distinct from h.customer_id)then
  raise exception 'CP7_CREDIT_NOTE_MEMBERSHIP_UNPROVEN';end if;
 if h.status in('POSTED','PARTIAL_PAID','PAID')and(p_sale<>previous or exists(
  select 1 from erp.sales_headers s where s.id=any(ids)and s.id<>p_sale
   and s.status in('POSTED','PARTIAL_PAID','PAID')))then
  raise exception 'CP7_CREDIT_ACTIVE_LEAF_AMBIGUOUS';end if;
 return query select root,previous,h.customer_id,h.status::text;
end $$;

-- REQUIRED integration interface, deliberately not implemented here. It must
-- prove the complete exact registry/replay/source/component/consumption set in
-- this STABLE statement snapshot; every retained signed adjustment is included.
-- In particular prove each component's deterministic parts, all actual journal
-- links/lines/date pairs, expected counts/hashes, account/customer identity and
-- owning-operation completion. Pending plans/components are NEVER actual I.
-- It must reject incomplete materialization, unexplained inverse descendants,
-- unsupported old return-family order/replay mapping and unmapped incoming U.
-- It cannot call a VOLATILE lock-taking collector and claim one STABLE snapshot.
create function cp7_credit.assert_current_materialized_profile(p_sale uuid,p_root uuid,p_leaf uuid)
returns void language plpgsql stable security definer set search_path='' as $$
begin raise exception 'CP7_CREDIT_CURRENT_MATERIALIZED_PROFILE_UNIMPLEMENTED';end $$;

-- This core is private by ACL. Placing its name in erp allows the invoker
-- dispatcher to test its OID without granting authenticated USAGE on cp7_credit.
-- It returns only the signed adjustment U-I, leaving Native P under each
-- reader's original RLS/permissions. Refund never reduces I.
create function erp._cp7_current_credit_adjustment(p_sale uuid)returns numeric
language plpgsql stable security definer set search_path='' set TimeZone='UTC' as $$
declare h erp.sales_headers;m record;i numeric;u numeric;
begin
 select *into strict h from erp.sales_headers where id=p_sale;
 -- Preserve inactive/DRAFT document financial semantics: own Native P only.
 if h.status not in('POSTED','PARTIAL_PAID','PAID')then return 0::numeric;end if;
 select *into strict m from cp7_credit.current_leaf_assignment(p_sale);
 -- Legacy invoices/ordinary returns have no OW04 participation. Preserve the
 -- Native payment projection without inventing family order or requiring a
 -- retrofit of old posted returns. A protected journal cannot exploit this
 -- fast path: every such actual journal must have its exact retained link.
 if exists(select 1 from erp.journal_entries j
  where j.source_type='CP7_CUSTOMER_CREDIT_RECOGNITION'and not exists(
   select 1 from cp7_credit.component_journals cj
    join cp7_credit.component_parts q on q.id=cj.part_id
    join cp7_credit.recognition_components cc on cc.id=q.component_id
    join cp7_credit.recognition_plans p on p.id=cc.plan_id
    join cp7_credit.cohorts c on c.id=p.cohort_id
    join cp7_credit.return_families f on f.id=c.family_id
   where cj.journal_id=j.id and q.id=j.source_id))
  or exists(select 1 from erp.journal_entries j
   where j.source_type='CP7_CUSTOMER_CREDIT_REFUND'and not exists(
    select 1 from cp7_credit.consumption_events e
     join cp7_credit.cohorts c on c.id=e.cohort_id
     join cp7_credit.return_families f on f.id=c.family_id
    where e.journal_id=j.id and e.id=j.source_id and e.event_kind='REFUND'))then
  raise exception 'CP7_CREDIT_UNREPRESENTED_FINANCIAL_JOURNAL';end if;
 if not exists(select 1 from cp7_credit.return_families f where f.family_root_sale_id=m.root_sale_id)
  and not exists(select 1 from cp7_credit.consumption_events e
   where e.event_kind='APPLY'and e.target_sale_id=p_sale)then return 0::numeric;end if;
 perform cp7_credit.assert_current_materialized_profile(p_sale,m.root_sale_id,m.current_leaf_id);
 -- Validator above proves ALL parts have actual journals; this join is not a
 -- silent filter permitting a partial pending plan to masquerade as actual I.
 select coalesce(sum(q.amount),0)into i
  from cp7_credit.return_families f join cp7_credit.cohorts c on c.family_id=f.id
  join cp7_credit.recognition_plans p on p.cohort_id=c.id
  join cp7_credit.recognition_components cc on cc.plan_id=p.id
  join cp7_credit.component_parts q on q.component_id=cc.id
  join cp7_credit.component_journals j on j.part_id=q.id
  where f.family_root_sale_id=m.root_sale_id;
 -- Signed restores are retained, not filtered away by amount/status. An
 -- advance-backed Native sales_payment is already P and is NOT another U.
 select coalesce(sum(e.amount),0)into u from cp7_credit.consumption_events e
  where e.event_kind='APPLY'and e.target_sale_id=p_sale;
 return u-i;
end $$;
alter function erp._cp7_current_credit_adjustment(uuid)owner to postgres;
revoke all on function erp._cp7_current_credit_adjustment(uuid)from public,anon,authenticated,service_role;
revoke all on function cp7_credit.current_leaf_assignment(uuid),
 cp7_credit.assert_current_materialized_profile(uuid,uuid,uuid)from public,anon,authenticated,service_role;

-- Narrow capability for the existing invoker receivables view. It intentionally
-- adds NO sales.invoice.view or finance.ar.view requirement: those permissions
-- are absent from the existing Native view/RLS contract. Caller financial
-- permission remains enforced by P11/customer-history's existing facades.
create role cp7_credit_visible_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication nobypassrls;
grant usage on schema erp,auth to cp7_credit_visible_read;
grant select on erp.sales_headers,erp.customers,erp.sales_items to cp7_credit_visible_read;
grant execute on function erp.current_app_role(),erp.current_app_user_id(),auth.uid(),auth.jwt()
 to cp7_credit_visible_read;
grant execute on function erp._cp7_current_credit_adjustment(uuid)to cp7_credit_visible_read;

create function erp._cp7_current_credit_adjustment_visible(p_sale uuid)returns numeric
language plpgsql stable security definer set search_path='' as $$
declare visible_sale uuid;
begin
 -- This role owns NONE of these tables and has NOBYPASSRLS. Reuse actual
 -- current policies, not a copied role/permission predicate or null-auth escape.
 -- The join preserves the Native view's header+customer+nonempty-invoice gate.
 select h.id into visible_sale from erp.sales_headers h
  join erp.customers c on c.id=h.customer_id
  where h.id=p_sale and h.status in('POSTED','PARTIAL_PAID','PAID')
   and exists(select 1 from erp.sales_items s where s.sale_id=h.id);
 if visible_sale is null then return null::numeric;end if;
 return erp._cp7_current_credit_adjustment(visible_sale);
end $$;
alter function erp._cp7_current_credit_adjustment_visible(uuid)owner to cp7_credit_visible_read;
revoke all on function erp._cp7_current_credit_adjustment_visible(uuid)from public,anon,authenticated,service_role;
grant execute on function erp._cp7_current_credit_adjustment_visible(uuid)to authenticated;

create function erp._cp7_receivable_credit_adjustment(p_sale uuid)returns numeric
language plpgsql stable security invoker set search_path='' as $$
begin
 -- current_user here is the real invoking SQL role. Under the Native V263d
 -- SECURITY DEFINER checker it is postgres, even for an authenticated caller.
 -- This tests a non-spoofable ACL capability, never auth.uid() IS NULL, a GUC,
 -- a claimed role argument, session_user, or a hardcoded role-name allowlist.
 if pg_catalog.has_function_privilege(current_user,
   'erp._cp7_current_credit_adjustment(uuid)'::regprocedure,'EXECUTE')then
  return erp._cp7_current_credit_adjustment(p_sale);
 end if;
 return erp._cp7_current_credit_adjustment_visible(p_sale);
end $$;
alter function erp._cp7_receivable_credit_adjustment(uuid)owner to postgres;
revoke all on function erp._cp7_receivable_credit_adjustment(uuid)from public,anon,authenticated,service_role;
grant execute on function erp._cp7_receivable_credit_adjustment(uuid)to authenticated,service_role;
-- Service-role existing view reads retain their existing privileged semantics;
-- no authenticated membership/EXEC on this core and no new schema ERP grant.
grant execute on function erp._cp7_current_credit_adjustment(uuid)to service_role;

-- Private P11/header path already guards sales.invoice.view + optional AR.
-- History internals are postgres-owned; do NOT grant its outer facade role
-- ERP/new-fact SELECT or add a seventh history-schema function accidentally.
grant execute on function erp._cp7_current_credit_adjustment(uuid)to cp7_sales_read;

-- EXACT integration edits (to be captured/hash-pinned/restored by full bundle):
-- 1. Native invoker view: retain invoice/payment/returned CTEs and existing
--    joins/active WHERE/column order/types. Add lateral or CTE expression
--      coalesce(p.paid_amount,0) + erp._cp7_receivable_credit_adjustment(sh.id)
--    as E and use E in paid_amount, outstanding_amount=max(net-E,0), and legacy
--    credit_amount=max(E-net,0). Do NOT coalesce a failed/null adjustment to 0.
--    Keep security_invoker=true, owner and every ACL unchanged.
-- 2. P11 header: ONLY in the existing CASE WHEN p_financial branch, set
--      E=amounts.paid + erp._cp7_current_credit_adjustment(h.id).
--    Use E for paid_total/open_balance. CASE false must not execute this core;
--    preserve every nonfinancial field and INACTIVE_DOCUMENT open_balance=NULL.
-- 3. History: provide an internal financial boolean to invoices or a separate
--    guarded financial projection used ONLY inside financial branches. Existing
--    invoices(uuid) is ALSO used by events and summary counts on nonfinancial
--    reads. Do NOT unconditionally invoke the new core from invoices(uuid).
-- 4. Native status/capacity/V253/V268 use their private core capability, with
--    whole-source projection during an unfinished compound operation. Current
--    reader cannot count an unmaterialized plan to make an intermediate guard
--    pass. Dated GL/report checks still consume actual signed journal profiles.
-- 5. All function PUBLIC default EXEC privileges must be revoked in the same
--    transaction. Verifier proves exact owners, NOBYPASSRLS/role memberships,
--    empty search_paths/STABLE, existing Native RLS/ACL unchanged, no auth core
--    EXEC or ledger SELECT/DML, no extra erp USAGE, and full restoration.
