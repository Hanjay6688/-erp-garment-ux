-- A receipt can have no final payable yet while some delivered units still
-- await an invoice. A settled or fully credited invoice is a different case.
create function erp.unpaid_purchase_awaits_invoice(p_purchase_id uuid)
returns boolean
language sql stable strict security invoker
set search_path = pg_catalog
as $function$
  select not exists (
    select from erp.supplier_payments p
    where p.purchase_id=p_purchase_id and p.status='POSTED'
  )
  and round(erp.material_purchase_payable_total(p_purchase_id),2)=0
  -- A charged final line may have been settled by credit or a supplier return.
  -- Keep that settlement, including matched amounts brought in at cutover.
  and not exists (
    select from erp.material_purchase_items i
    where i.purchase_id=p_purchase_id and (
      i.invoice_match_state='DIRECT_FINAL'
      or exists (
        select from erp.material_supplier_invoice_lines l
        join erp.material_supplier_invoices h on h.id=l.invoice_id
        where l.purchase_item_id=i.id and h.status='POSTED' and l.net_amount>0
      )
      or exists (
        select from erp.bb_receipt_invoiced_parts_v1 b
        where b.purchase_item_id=i.id and b.invoiced_amount>0
      )
    )
  )
  and exists (
    select from erp.material_purchase_items i
    where i.purchase_id=p_purchase_id and i.invoice_match_state<>'DIRECT_FINAL'
      and erp.material_purchase_invoice_capacity(i.id)>erp.material_purchase_posted_invoice_qty(i.id)
  )
$function$;
revoke all on function erp.unpaid_purchase_awaits_invoice(uuid) from public,anon,authenticated,service_role;

create function erp.keep_unbilled_purchase_unpaid()
returns trigger
language plpgsql security invoker
set search_path = pg_catalog
as $function$
begin
  if erp.unpaid_purchase_awaits_invoice(new.id) then
    new.payment_status := 'UNPAID';
  end if;
  return new;
end
$function$;
revoke all on function erp.keep_unbilled_purchase_unpaid() from public,anon,authenticated,service_role;

create trigger material_purchase_unbilled_payment_status
before update of status,payment_status on erp.material_purchase_headers
for each row when (new.status='POSTED' and new.payment_status='PAID')
execute function erp.keep_unbilled_purchase_unpaid();

-- Correct only a derived status on existing receipts through the ordinary
-- row audit. All quantities, amounts, invoices and journals retain their history.
do $existing$
declare previous_reason text := current_setting('app.change_reason',true);
begin
  perform set_config('app.change_reason','Koreksi status penerimaan tanpa pembayaran yang masih menunggu invoice supplier',true);
  update erp.material_purchase_headers h
  set payment_status='UNPAID'
  where h.status='POSTED' and h.payment_status='PAID'
    and erp.unpaid_purchase_awaits_invoice(h.id);
  perform set_config('app.change_reason',coalesce(previous_reason,''),true);
end $existing$;
