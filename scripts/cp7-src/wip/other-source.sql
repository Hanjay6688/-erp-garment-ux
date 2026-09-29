-- Opening WIP/BS and explicitly unsourced BS. No stock movement is inferred
-- from a display reader or financial total. All columns here are operational.
grant select on erp.initial_import_production_sources,erp.opening_balance_items,
 erp.opening_balance_headers,erp.migration_batches,erp.initial_import_wip_outputs,
 erp.initial_import_wip_output_reversals,erp.bb_wip_pickups_v1,erp.bb_wip_bs_splits_v1,
 erp.bd_opening_laundry_claims_v1,erp.bd_opening_laundry_claim_events_v1 to cp7_capture;
create function cp7_wip.capture_other_sources(p_items uuid[],p_cases uuid[],p_at timestamptz) returns jsonb
language sql stable security invoker set search_path='' set timezone='Asia/Jakarta' as $$
with origins as materialized(
 select s.opening_item_id id,s.source_row_id,s.batch_id,s.po_id,s.size_id,s.stage,s.qty_pcs::text qty_pcs,s.bs_case_id,
 i.balance_type,i.qty::text opening_qty_pcs,i.product_id,i.model_id,i.customer_id,i.vendor_id,i.contractor_id,h.opening_date,h.status header_status,m.status batch_status
 from erp.initial_import_production_sources s join erp.opening_balance_items i on i.id=s.opening_item_id
 join erp.opening_balance_headers h on h.id=i.opening_id join erp.migration_batches m on m.id=s.batch_id
 where s.opening_item_id=any(p_items) and h.opening_date<=(p_at at time zone 'Asia/Jakarta')::date order by s.opening_item_id limit 51
),
pickups as materialized(
 select x.id,x.opening_item_id,x.physical_at,x.reversed_at
 from erp.bb_wip_pickups_v1 x join origins o on o.id=x.opening_item_id where x.physical_at<=p_at order by x.id limit 2001
),
outputs as materialized(
 select x.id,x.opening_item_id,x.lot_id,x.qty_pcs::text qty_pcs,x.physical_at,r.physical_at reversed_at,p.size_id
 from erp.initial_import_wip_outputs x join origins o on o.id=x.opening_item_id
 join erp.fg_lots l on l.id=x.lot_id join erp.products p on p.id=l.product_id
 left join erp.initial_import_wip_output_reversals r on r.output_id=x.id
 where x.physical_at<=p_at order by x.id limit 2001
),
splits as materialized(
 select x.id,x.opening_item_id,x.bs_case_id,x.product_id,p.size_id,x.qty_pcs::text qty_pcs,x.physical_at,x.reversed_at
 from erp.bb_wip_bs_splits_v1 x join origins o on o.id=x.opening_item_id join erp.products p on p.id=x.product_id
 where x.physical_at<=p_at order by x.id limit 2001
),
claims as materialized(
 select x.id,x.opening_item_id,x.claim_type,x.qty_claimed::text qty_pcs,x.claim_date,x.cancelled_at,x.row_version::text revision
 from erp.bd_opening_laundry_claims_v1 x join origins o on o.id=x.opening_item_id
 where x.claim_date<=(p_at at time zone 'Asia/Jakarta')::date order by x.id limit 2001
),
claim_events as materialized(
 select x.id,x.claim_id,x.event_kind,x.qty::text qty_pcs,x.resolution,x.event_date,x.reversed_at
 from erp.bd_opening_laundry_claim_events_v1 x join claims c on c.id=x.claim_id
 where x.event_date<=(p_at at time zone 'Asia/Jakarta')::date order by x.id limit 2001
),
non_po as materialized(
 select b.id,b.qty_pcs::text qty_pcs,p.size_id,b.row_version::text revision,b.untracked_type,b.physical_at
 from erp.bs_cases b left join erp.products p on p.id=b.product_id
 where b.id=any(p_cases) and b.cutting_group_id is null and b.qc_item_id is null and b.source_laundry_receipt_line_id is null
  and b.po_id is null and b.untracked_type in ('OUT_OF_NOWHERE','LEGACY') and b.physical_at<=p_at
  and not exists(select 1 from erp.initial_import_production_sources z where z.bs_case_id=b.id)
  and not exists(select 1 from erp.bb_wip_bs_splits_v1 z where z.bs_case_id=b.id)
 order by b.id limit 51
),
bs as materialized(
 select b.id,b.product_id,p.size_id,b.qty_pcs::text qty_pcs,b.status,b.physical_at,b.row_version::text revision
 from erp.bs_cases b left join erp.products p on p.id=b.product_id
 where b.id in (select bs_case_id from origins union select bs_case_id from splits where reversed_at is null or reversed_at>p_at union select id from non_po)
 and b.physical_at<=p_at order by b.id limit 2001
),
reworks as materialized(
 select r.id,r.bs_case_id,r.qty_sent::text sent_pcs,r.qty_good_returned::text good_pcs,r.qty_bs_returned::text bs_pcs,
 r.physical_sent_at,r.completed_at,r.status,r.row_version::text revision,r.good_fg_lot_id,r.cost_posted completion_posted
 from erp.rework_orders r join bs b on b.id=r.bs_case_id where r.physical_sent_at<=p_at order by r.id limit 2001
),
resolutions as materialized(
 select r.id,r.bs_case_id,r.resolution_type,r.qty_pcs::text qty_pcs,r.source_rework_order_id,r.physical_at
 from erp.bs_resolutions r join bs b on b.id=r.bs_case_id where r.physical_at<=p_at order by r.id limit 2001
),
holds as materialized(
 select h.id,h.bs_case_id,h.action,h.resulting_status,h.physical_at,h.created_at
 from erp.bs_case_hold_events h join bs b on b.id=h.bs_case_id where h.physical_at<=p_at order by h.id limit 2001
),
bs_fg as materialized(
 select x.id,x.bs_case_id,x.bs_resolution_id,x.qty_pcs::text qty_pcs,x.status,x.lot_id,x.quality_grade,x.physical_at
 from erp.fg_unsourced_receipts_v1 x join bs b on b.id=x.bs_case_id where x.physical_at<=p_at order by x.id limit 2001
),
source as (select jsonb_build_object(
 'origins',coalesce((select jsonb_agg(to_jsonb(x) order by id) from origins x),'[]'::jsonb),
 'pickups',coalesce((select jsonb_agg(to_jsonb(x) order by id) from pickups x),'[]'::jsonb),
 'outputs',coalesce((select jsonb_agg(to_jsonb(x) order by id) from outputs x),'[]'::jsonb),
 'splits',coalesce((select jsonb_agg(to_jsonb(x) order by id) from splits x),'[]'::jsonb),
 'claims',coalesce((select jsonb_agg(to_jsonb(x) order by id) from claims x),'[]'::jsonb),
 'claim_events',coalesce((select jsonb_agg(to_jsonb(x) order by id) from claim_events x),'[]'::jsonb),
 'non_po',coalesce((select jsonb_agg(to_jsonb(x) order by id) from non_po x),'[]'::jsonb),
 'bs',coalesce((select jsonb_agg(to_jsonb(x) order by id) from bs x),'[]'::jsonb),
 'reworks',coalesce((select jsonb_agg(to_jsonb(x) order by id) from reworks x),'[]'::jsonb),
 'resolutions',coalesce((select jsonb_agg(to_jsonb(x) order by id) from resolutions x),'[]'::jsonb),
 'holds',coalesce((select jsonb_agg(to_jsonb(x) order by id) from holds x),'[]'::jsonb),
 'bs_fg',coalesce((select jsonb_agg(to_jsonb(x) order by id) from bs_fg x),'[]'::jsonb)) facts)
select jsonb_build_object('contract_version','cp7.other-wip-facts.v1','captured_at',p_at,'facts',facts,
 'status',case when jsonb_array_length(facts->'origins')=cardinality(p_items) and jsonb_array_length(facts->'non_po')=cardinality(p_cases)
 and not exists(select 1 from jsonb_each(facts) where jsonb_array_length(value)>2000) then 'COMPLETE' else 'INCOMPLETE' end) from source
$$;
