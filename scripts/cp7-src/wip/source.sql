-- Current scoped cutting source. All dependent rows share this statement's MVCC
-- snapshot. Explicit non-financial projections; no table-row JSON expansion.
grant select on erp.cutting_pickups,erp.cutting_distribution_batches,erp.cutting_distribution_allocations,
 erp.laundry_deliveries,erp.laundry_delivery_lines,erp.laundry_delivery_batch_size_lines,
 erp.laundry_receipts,erp.laundry_receipt_lines,erp.laundry_receipt_batch_size_lines,
 erp.qc_inspections,erp.qc_inspection_items,erp.bs_cases,erp.rework_orders,
 erp.laundry_failed_wash_attempts,erp.laundry_redispatch_participant_events,erp.bs_resolutions,
 erp.sewing_terminal_events to cp7_capture;
create function cp7_wip.capture_cutting_sources(p_groups uuid[]) returns jsonb
language sql stable security invoker set search_path='' set timezone='Asia/Jakarta' as $$
with clock as materialized(select clock_timestamp() at),
groups as materialized(
 select g.id,g.po_id,g.row_version::text revision,g.status,g.pattern_id,g.pattern_revision_snapshot,
 g.cut_at,g.picked_up_at,g.material_issue_posted,po.model_id
 from erp.cutting_groups g join erp.production_orders po on po.id=g.po_id cross join clock c
 where g.id=any(p_groups) and g.cut_at<=c.at order by g.id limit 51
),
yields as materialized(
 select y.id,g.id group_id,s.size_id,y.qty_pcs::text qty_pcs,g.revision
 from groups g join erp.cutting_group_rolls r on r.cutting_group_id=g.id
 join erp.cutting_roll_yields y on y.cutting_group_roll_id=r.id
 join erp.cutting_group_size_slots s on s.id=y.size_slot_id
 order by g.id,s.size_id,y.id limit 2001
),
batches as materialized(
 select a.id,b.id batch_id,p.id pickup_id,p.cutting_group_id group_id,p.status,
 p.picked_up_at,p.row_version::text revision,a.cutting_roll_yield_id yield_id,a.qty_pcs::text qty_pcs
 from groups g join erp.cutting_pickups p on p.cutting_group_id=g.id
 join erp.cutting_distribution_batches b on b.pickup_id=p.id
 join erp.cutting_distribution_allocations a on a.batch_id=b.id cross join clock c
 where p.picked_up_at<=c.at order by p.id,b.id,a.id limit 2001
),
deliveries as materialized(
 select l.id,l.cutting_group_id group_id,d.id delivery_id,d.status,d.physical_at,
 d.row_version::text revision,l.qty_sent_pcs::text qty_pcs,
 d.target_wash_process_id,d.target_dyeing_color
 from erp.laundry_delivery_lines l join groups g on g.id=l.cutting_group_id
 join erp.laundry_deliveries d on d.id=l.delivery_id cross join clock c
 where d.physical_at<=c.at order by d.physical_at,d.id,l.id limit 2001
),
delivery_sizes as materialized(
 select s.id,s.delivery_line_id,s.distribution_batch_id batch_id,s.size_id,s.qty_sent_pcs::text qty_pcs,d.group_id
 from erp.laundry_delivery_batch_size_lines s join deliveries d on d.id=s.delivery_line_id
 order by s.id limit 2001
),
receipts as materialized(
 select l.id,l.delivery_line_id,r.id receipt_id,r.status,r.physical_at,r.row_version::text revision,
 l.qty_good_received::text good_pcs,l.qty_bs_laundry::text bs_pcs,l.qty_missing::text missing_pcs,l.qty_stuck::text stuck_pcs,d.group_id
 from deliveries d join erp.laundry_receipt_lines l on l.delivery_line_id=d.id
 join erp.laundry_receipts r on r.id=l.receipt_id cross join clock c
 where r.physical_at<=c.at order by r.physical_at,r.id,l.id limit 2001
),
receipt_sizes as materialized(
 select s.id,s.receipt_line_id,s.delivery_batch_size_line_id delivery_size_id,s.size_id,
 s.qty_good_received::text good_pcs,s.qty_bs_laundry::text bs_pcs,r.group_id
 from erp.laundry_receipt_batch_size_lines s join receipts r on r.id=s.receipt_line_id order by s.id limit 2001
),
qc as materialized(
 select i.id,i.cutting_group_id group_id,q.id inspection_id,q.status,q.physical_at,q.row_version::text revision,
 i.source_laundry_receipt_line_id receipt_line_id,i.source_laundry_receipt_batch_size_line_id receipt_size_id,
 i.final_product_id,p.size_id,coalesce(p.identity_root_id,p.id) product_root,
 i.qty_good_pcs::text good_pcs,i.qty_bs_pcs::text bs_pcs
 from erp.qc_inspection_items i join groups g on g.id=i.cutting_group_id
 join erp.qc_inspections q on q.id=i.inspection_id join erp.products p on p.id=i.final_product_id cross join clock c
 where q.physical_at<=c.at order by q.physical_at,q.id,i.id limit 2001
),
bs as materialized(
 select b.id,b.cutting_group_id group_id,b.qc_item_id,b.product_id,p.size_id,b.source_laundry_receipt_line_id receipt_line_id,
 b.source_laundry_bs_allocation_id receipt_size_id,b.qty_pcs::text qty_pcs,b.status,b.detected_at_stage,b.physical_at,b.row_version::text revision
 from erp.bs_cases b join groups g on g.id=b.cutting_group_id left join erp.products p on p.id=b.product_id cross join clock c
 where b.physical_at<=c.at order by b.physical_at,b.id limit 2001
),
reworks as materialized(
 select r.id,r.bs_case_id,r.qty_sent::text sent_pcs,r.qty_good_returned::text good_pcs,r.qty_bs_returned::text bs_pcs,
 r.physical_sent_at,r.completed_at,r.status,r.row_version::text revision,r.good_fg_lot_id
 from erp.rework_orders r join bs b on b.id=r.bs_case_id cross join clock c
 where r.physical_sent_at<=c.at order by r.physical_sent_at,r.id limit 2001
),
resolutions as materialized(
 select r.id,r.bs_case_id,r.resolution_type,r.qty_pcs::text qty_pcs,r.source_rework_order_id,r.physical_at
 from erp.bs_resolutions r join bs b on b.id=r.bs_case_id cross join clock c
 where r.physical_at<=c.at order by r.physical_at,r.id limit 2001
),
failed as materialized(
 select a.id,a.receipt_line_id,a.delivery_id,a.custody_outcome,a.qty_attempted_pcs::text qty_pcs
 from erp.laundry_failed_wash_attempts a join receipts r on r.id=a.receipt_line_id order by a.id limit 2001
),
redispatch as materialized(
 select e.id,e.event_type,e.source_delivery_batch_size_line_id source_id,e.successor_delivery_batch_size_line_id successor_id,
 e.qty_pcs::text qty_pcs,e.releases_allocation_event_id,e.released_delivery_id
 from erp.laundry_redispatch_participant_events e where e.source_delivery_batch_size_line_id in (select id from delivery_sizes)
  or e.successor_delivery_batch_size_line_id in (select id from delivery_sizes) order by e.created_at,e.id limit 2001
),
sewing as materialized(
 select e.id,e.cutting_group_id group_id,e.qty_signed::text qty_signed,e.event_kind,e.reversal_of_id,e.physical_at,e.row_version::text revision
 from erp.sewing_terminal_events e join groups g on g.id=e.cutting_group_id cross join clock c where e.physical_at<=c.at order by e.physical_at,e.id limit 2001
),
source as (select jsonb_build_object(
 'groups',coalesce((select jsonb_agg(to_jsonb(x) order by id) from groups x),'[]'::jsonb),
 'yields',coalesce((select jsonb_agg(to_jsonb(x) order by id) from yields x),'[]'::jsonb),
 'batches',coalesce((select jsonb_agg(to_jsonb(x) order by id) from batches x),'[]'::jsonb),
 'deliveries',coalesce((select jsonb_agg(to_jsonb(x) order by id) from deliveries x),'[]'::jsonb),
 'delivery_sizes',coalesce((select jsonb_agg(to_jsonb(x) order by id) from delivery_sizes x),'[]'::jsonb),
 'receipts',coalesce((select jsonb_agg(to_jsonb(x) order by id) from receipts x),'[]'::jsonb),
 'receipt_sizes',coalesce((select jsonb_agg(to_jsonb(x) order by id) from receipt_sizes x),'[]'::jsonb),
 'qc',coalesce((select jsonb_agg(to_jsonb(x) order by id) from qc x),'[]'::jsonb),
 'bs',coalesce((select jsonb_agg(to_jsonb(x) order by id) from bs x),'[]'::jsonb),
 'reworks',coalesce((select jsonb_agg(to_jsonb(x) order by id) from reworks x),'[]'::jsonb),
 'resolutions',coalesce((select jsonb_agg(to_jsonb(x) order by id) from resolutions x),'[]'::jsonb),
 'failed',coalesce((select jsonb_agg(to_jsonb(x) order by id) from failed x),'[]'::jsonb),
 'redispatch',coalesce((select jsonb_agg(to_jsonb(x) order by id) from redispatch x),'[]'::jsonb),
 'sewing',coalesce((select jsonb_agg(to_jsonb(x) order by id) from sewing x),'[]'::jsonb)) facts)
select jsonb_build_object('contract_version','cp7.cutting-facts.v1','knowledge_mode','CURRENT',
 'captured_at',(select at from clock),'scope',to_jsonb(p_groups),'facts',facts,
 'status',case when jsonb_array_length(facts->'groups')=cardinality(p_groups)
  and not exists(select 1 from jsonb_each(facts) where key<>'groups' and jsonb_array_length(value)>2000) then 'COMPLETE' else 'INCOMPLETE' end)
from source
$$;
