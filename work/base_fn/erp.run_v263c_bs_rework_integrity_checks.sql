-- bootstrap lines 27026-27109
CREATE OR REPLACE FUNCTION erp.run_v263c_bs_rework_integrity_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
  select 'rework_component_wrong_bs_case','CRITICAL',count(*)::bigint,
         'Every rework component must belong to the order BS case'
  from erp.rework_component_lines l
  join erp.rework_orders o on o.id=l.rework_order_id
  join erp.bs_case_components c on c.id=l.bs_case_component_id
  where c.bs_case_id<>o.bs_case_id

  union all
  select 'rework_rate_provenance_mismatch','CRITICAL',count(*)::bigint,
         'Server-priced rework rate must equal its immutable source snapshot'
  from erp.rework_component_lines l
  left join erp.contractor_work_rates r on r.id=l.source_contractor_rate_id
  left join erp.po_work_component_snapshots s on s.id=l.source_po_component_snapshot_id
  where (l.rate_basis='CONTRACTOR_RATE' and (r.id is null or l.rate_snapshot<>r.rate_per_pcs))
     or (l.rate_basis='PO_SNAPSHOT' and (s.id is null or l.rate_snapshot<>s.rate_per_pcs_snapshot))
     or (l.rate_basis='LAUNDRY_ZERO' and l.rate_snapshot<>0)

  union all
  select 'rework_component_qty_exceeds_sent','CRITICAL',count(*)::bigint,
         'Component performed qty cannot exceed physical rework qty sent'
  from erp.rework_component_lines l join erp.rework_orders o on o.id=l.rework_order_id
  where l.qty_performed>o.qty_sent

  union all
  select 'active_cross_mandor_without_explicit_rate','CRITICAL',count(*)::bigint,
         'Cross-Mandor contractor rework requires effective contractor-rate provenance'
  from erp.rework_component_lines l
  join erp.rework_orders o on o.id=l.rework_order_id
  join erp.bs_cases b on b.id=o.bs_case_id
  left join erp.production_orders po on po.id=b.po_id
  where o.destination_type='CONTRACTOR' and o.status<>'CANCELLED'
    and o.contractor_id is distinct from coalesce(po.contractor_id,b.responsible_contractor_id)
    and (l.rate_basis<>'CONTRACTOR_RATE' or l.source_contractor_rate_id is null)

  union all
  select 'active_rework_bs_status_mismatch','CRITICAL',count(*)::bigint,
         'A BS case with active rework must project IN_REWORK while unresolved'
  from erp.bs_cases b
  where b.status not in('CANCELLED','RESOLVED','SCRAPPED','WRITTEN_OFF')
    and exists(select 1 from erp.rework_orders o where o.bs_case_id=b.id and o.status in('OPEN','IN_PROGRESS','PARTIAL'))
    and b.status<>'IN_REWORK'

  union all
  select 'bs_resolution_qty_exceeds_case','CRITICAL',count(*)::bigint,
         'Lifetime BS dispositions/resolutions cannot exceed case quantity'
  from (
    select b.id
    from erp.bs_cases b join erp.bs_resolutions r on r.bs_case_id=b.id
    group by b.id,b.qty_pcs having sum(r.qty_pcs)>b.qty_pcs
  ) excessive

  union all
  select 'cash_bs_resolution_invalid_claim','CRITICAL',count(*)::bigint,
         'Cash BS disposition requires matching settled laundry claim and capacity'
  from erp.bs_resolutions r
  join erp.bs_cases b on b.id=r.bs_case_id
  left join erp.laundry_claims c on c.id=r.source_laundry_claim_id
  where r.resolution_type='CASH_COMPENSATION'
    and (c.id is null or c.status<>'SETTLED' or c.vendor_id is distinct from b.responsible_vendor_id)

  union all
  select 'manual_bs_invalid_origin','CRITICAL',count(*)::bigint,
         'Manual/untracked BS must be only LEGACY or OUT_OF_NOWHERE with traceability'
  from erp.bs_cases b
  where b.untracked_type is not null
    and (b.untracked_type not in('LEGACY','OUT_OF_NOWHERE') or b.cause_source<>'UNKNOWN' or b.legacy_reference is null)

  union all
  select 'browser_direct_bs_rework_write_grant','CRITICAL',count(*)::bigint,
         'Authenticated browser must write BS/rework only through domain RPCs'
  from information_schema.role_table_grants g
  where g.table_schema='erp' and g.grantee='authenticated'
    and g.table_name in('bs_cases','bs_case_components','bs_resolutions','rework_orders','rework_component_lines')
    and g.privilege_type in('INSERT','UPDATE','DELETE');
$function$;

alter function "erp"."run_v263c_bs_rework_integrity_checks"() owner to "postgres";
