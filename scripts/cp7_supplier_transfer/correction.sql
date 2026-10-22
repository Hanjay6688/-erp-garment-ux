-- Read-only correction detector; used by the commit guard and the existing
-- Native financial checks. Exact economic and book facts stay in Native.
create function cp7_supplier_transfer.valid_correction_v1(p_original uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from cp7_supplier_transfer.corrections_v1 c
  join cp7_supplier_transfer.transfers_v1 o on o.id=c.original_id
  join cp7_supplier_transfer.transfers_v1 r on r.id=c.replacement_id
  join erp.journal_entries j on j.id=o.journal_id
  join erp.journal_entries inv on inv.reversal_of_id=j.id
  where c.original_id=p_original and o.status='REVERSED'and o.supplier_id=r.supplier_id
   and r.recorded_at>=o.recorded_at
   and cp7_supplier_transfer.valid_transfer_v1(o.id)and cp7_supplier_transfer.valid_transfer_v1(r.id)
   and case when j.economic_date=inv.economic_date then c.time_neutral_id is null and c.effective_inverse_id is null
   else c.time_neutral_id is not null and c.effective_inverse_id is not null
    and c.time_neutral_id<>c.effective_inverse_id
    and exists(select 1 from erp.journal_entries n where n.id=c.time_neutral_id and n.source_type='CP7_SUPPLIER_TRANSFER_TIME_NEUTRAL'
     and n.source_id=o.id and n.economic_date=inv.economic_date and n.status='POSTED'and n.reversal_of_id is null)
    and exists(select 1 from erp.journal_entries e where e.id=c.effective_inverse_id and e.source_type='CP7_SUPPLIER_TRANSFER_EFFECTIVE'
     and e.source_id=o.id and e.economic_date=j.economic_date and e.status='POSTED'and e.reversal_of_id is null)
    and(select count(*)from erp.journal_lines l where l.journal_entry_id=c.time_neutral_id)=2
    and(select count(*)from erp.journal_lines l where l.journal_entry_id=c.effective_inverse_id)=2
    and not exists(select 1 from erp.journal_lines l where l.journal_entry_id=c.time_neutral_id and not exists(
     select 1 from erp.journal_lines b where b.journal_entry_id=inv.id and b.account_id=l.account_id and b.debit=l.credit and b.credit=l.debit
      and(b.customer_id,b.vendor_id,b.contractor_id,b.po_id,b.product_id)is not distinct from(l.customer_id,l.vendor_id,l.contractor_id,l.po_id,l.product_id)))
    and not exists(select 1 from erp.journal_lines l where l.journal_entry_id=c.effective_inverse_id and not exists(
     select 1 from erp.journal_lines b where b.journal_entry_id=inv.id and b.account_id=l.account_id and b.debit=l.debit and b.credit=l.credit
      and(b.customer_id,b.vendor_id,b.contractor_id,b.po_id,b.product_id)is not distinct from(l.customer_id,l.vendor_id,l.contractor_id,l.po_id,l.product_id)))
   end
 )$$;
revoke all on function cp7_supplier_transfer.valid_correction_v1(uuid)from public,anon,authenticated,service_role,cp7_capture;
