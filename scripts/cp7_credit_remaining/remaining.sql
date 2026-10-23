-- OW-04b slice A (docs/cp7/d17-14/ow04/OW04B_MULTI_COHORT_DESIGN.md): pay the remaining balance of an invoice that
-- received customer credit (APPLY) and has no credit of its own. The admission below only decides WHICH payments may
-- pass the retained OW04 source hooks; it posts nothing. The proof stays with the retained verifiers: the hooks set the
-- existing "had families" scope flag, so native_source_enter (before) and native_source_complete (after) both run
-- assert_simple_native_base_v1 and assert_zero_excess_v1(initial_base_events_v1(sale)) - no overfunding on ANY
-- (economic, book) date pair, incoming credit U included - and the composed Native poster keeps its
-- current_effective_paid (P+U-I) remaining check and status. Everything else stays refused exactly as before.
create schema cp7_credit_remaining authorization postgres;
revoke all on schema cp7_credit_remaining from public,anon,authenticated,service_role,cp7_capture;

-- An ordinary cash/bank payment (or its inverse) on an invoice whose only credit participation is incoming APPLY.
create function cp7_credit_remaining.payment_admitted_v1(p_action text,p_payment uuid,p_sale uuid)returns boolean
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if p_action is null or p_action not in('PAYMENT','PAYMENT_REVERSE')or p_payment is null or p_sale is null then return false;end if;
 -- Incoming credit only: no return family (credit-bearing or EMPTY) and no cohort on this invoice.
 if not exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=p_sale)
  or exists(select 1 from cp7_credit.return_families where family_root_sale_id=p_sale)
  or exists(select 1 from cp7_credit.cohorts where source_sale_id=p_sale)then return false;end if;
 -- The plain Native document: no note revision, return correction or payment correction anywhere on it.
 if exists(select 1 from cp7_note.revisions where p_sale in(root_sale_id,previous_sale_id,replacement_sale_id))
  or exists(select 1 from cp7_sales_return_correction.links where sale_id=p_sale)
  or exists(select 1 from cp7_payment_correction.links l join erp.sales_payments p0 on p0.id in(l.original_id,l.replacement_id)
   where p0.sale_id=p_sale)then return false;end if;
 -- Ordinary cash receipts only: no opening/import advance on the invoice, no allocation replacement.
 if exists(select 1 from erp.sales_payments where sale_id=p_sale and(cash_account_id is null or payment_method='OPENING_ADVANCE'))
  or exists(select 1 from erp.initial_import_prepayment_payments l join erp.sales_payments p on p.id=l.payment_id where p.sale_id=p_sale)
  or not exists(select 1 from erp.sales_payments where id=p_payment and sale_id=p_sale and replaces_payment_id is null)then
  return false;end if;
 return true;
end $$;

-- The CP7 PAYMENT_REVERSE request on such an invoice: no source operation is opened (nothing is recognized); the
-- Native inverse then passes the admitted hook above with the same before/after proof.
create function cp7_credit_remaining.request_admitted_v1(p_action text,p_payload jsonb,p_sale uuid)returns boolean
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare v_text text;v_payment uuid;
begin
 if p_action is distinct from'PAYMENT_REVERSE'or jsonb_typeof(p_payload->'payment_id')is distinct from'string'then return false;end if;
 v_text:=p_payload->>'payment_id';
 if v_text!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'then return false;end if;
 v_payment:=v_text::uuid;
 if not exists(select 1 from erp.sales_payments p where p.id=v_payment and p.sale_id=p_sale and p.status='POSTED')then return false;end if;
 return cp7_credit_remaining.payment_admitted_v1(p_action,v_payment,p_sale);
end $$;

do $private_remaining$declare sig text;begin
 foreach sig in array array['payment_admitted_v1(text,uuid,uuid)','request_admitted_v1(text,jsonb,uuid)']loop
  execute 'alter function cp7_credit_remaining.'||sig||' owner to postgres';
  execute 'revoke all on function cp7_credit_remaining.'||sig||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write';
 end loop;
end $private_remaining$;
