-- OW-04b slice C step 1 (docs/cp7/d17-14/ow04/OW04B_SLICE_C_INVENTORY.md C2-C6). A private reader only: no installed
-- function changes and no row is written by this file.
-- U, the customer credit applied to an invoice: every APPLY-kind consumption event targeting it, signed. A named undo
-- is an APPLY-kind event with the negative amount and restores_event_id, so it is retained, not filtered by amount or
-- status. These are exactly the rows erp._cp7_current_credit_adjustment sums as u, the materialized profile adds to
-- v_u, consumer_incoming_funding_v1 turns into FUNDING events and the consumer fixture reads as U (local_check.py).
create schema cp7_credit_incoming authorization postgres;
revoke all on schema cp7_credit_incoming from public,anon,authenticated,service_role,cp7_capture;

create function cp7_credit_incoming.incoming_applied_v1(p_sale uuid)returns numeric
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select coalesce(sum(e.amount),0)from cp7_credit.consumption_events e where e.event_kind='APPLY'and e.target_sale_id=p_sale
$$;

alter function cp7_credit_incoming.incoming_applied_v1(uuid)owner to postgres;
revoke all on function cp7_credit_incoming.incoming_applied_v1(uuid)from public,anon,authenticated,service_role,cp7_capture,
 cp7_sales_read,cp7_sales_write,cp7_credit_write;
