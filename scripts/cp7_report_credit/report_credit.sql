-- OW-08a (D17-14, D17-16): report readiness after customer credit.
-- The three Native AR checks compared posted payments P with net sales. An
-- invoice that took part in OW04 customer credit is settled by the effective
-- payment E=P+(U-I), the same quantity the credit-aware invoice readers use.
-- This private reader returns that proven signed adjustment U-I per invoice.

create schema cp7_report_credit;
revoke all on schema cp7_report_credit from public;

create function cp7_report_credit.adjustment_v1(p_sale uuid)returns numeric
language plpgsql stable security definer set search_path=''as $$
begin
 -- The OW04 core proves every retained credit part, journal and consumption
 -- before it answers; it raises when the profile cannot be proven. A report
 -- check must still return rows, so an unprovable profile becomes null and is
 -- counted by its own critical check (CP7_CUSTOMER_CREDIT_REPORT_UNPROVEN).
 return erp._cp7_current_credit_adjustment(p_sale);
exception when others then
 return null::numeric;
end $$;
alter function cp7_report_credit.adjustment_v1(uuid)owner to postgres;
revoke all on function cp7_report_credit.adjustment_v1(uuid)from public,anon,authenticated,service_role;
