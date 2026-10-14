-- bootstrap lines 26982-27025
CREATE OR REPLACE FUNCTION erp.run_v263b_laundry_bs_integrity_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
  select 'posted_laundry_bs_allocation_mismatch','CRITICAL',count(*)::bigint,
         'Every posted laundry receipt line BS qty must equal its product allocations'
  from erp.laundry_receipt_lines l
  join erp.laundry_receipts h on h.id=l.receipt_id and h.status='POSTED'
  where l.qty_bs_laundry<>(select coalesce(sum(a.qty_bs),0) from erp.laundry_receipt_bs_product_allocations a where a.receipt_line_id=l.id)

  union all
  select 'active_laundry_bs_without_product_lineage','CRITICAL',count(*)::bigint,
         'Laundry-origin BS must retain product and receipt allocation lineage'
  from erp.bs_cases b
  where b.cause_source='LAUNDRY' and b.status<>'CANCELLED'
    and (b.product_id is null or b.source_laundry_receipt_line_id is null or b.source_laundry_bs_allocation_id is null)

  union all
  select 'laundry_bs_case_allocation_qty_mismatch','CRITICAL',count(*)::bigint,
         'Active laundry BS case qty/product must match its immutable allocation'
  from erp.bs_cases b
  join erp.laundry_receipt_bs_product_allocations a on a.id=b.source_laundry_bs_allocation_id
  where b.status<>'CANCELLED' and (b.qty_pcs<>a.qty_bs or b.product_id<>a.product_id)

  union all
  select 'settled_claim_followed_by_late_return','CRITICAL',count(*)::bigint,
         'No physical late return may post after final STUCK/MISSING claim resolution'
  from erp.laundry_claims c
  left join erp.laundry_receipt_lines claimed on claimed.id=c.receipt_line_id
  where c.status in('SETTLED','WRITTEN_OFF') and c.claim_type in('MISSING','STUCK')
    and exists(
      select 1 from erp.laundry_receipt_lines later
      join erp.laundry_receipts h on h.id=later.receipt_id and h.status='POSTED'
      where later.qty_good_received+later.qty_bs_laundry>0
        and h.physical_at>coalesce(c.resolved_at,c.opened_at)
        and (later.delivery_line_id=claimed.delivery_line_id
             or (c.receipt_line_id is null and h.delivery_id=c.delivery_id))
    );
$function$;

alter function "erp"."run_v263b_laundry_bs_integrity_checks"() owner to "postgres";
