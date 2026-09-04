-- Isolated-database fixture for real two-connection CP6 serialization races.
-- The workflow clones the disposable full-schema database, runs this seed only
-- in that clone, then destroys the whole clone after proof collection.
\set ON_ERROR_STOP on

begin;
set local timezone='UTC';
select set_config(
  'request.jwt.claims',
  jsonb_build_object('sub','c8c00000-0000-4000-8000-000000000101','role','authenticated')::text,
  true
);
select set_config('app.change_reason','CP6 isolated concurrency seed',true);

insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
select 'c8c00000-0000-4000-8000-000000000001','c8c00000-0000-4000-8000-000000000101',
  'CP6 Race Owner','OWNER',id,true
from erp.app_roles where role_code='OWNER';

insert into erp.production_patterns(
  id,pattern_code,revision,pattern_name,sort_order,is_active,created_by,updated_by
) values(
  'c8c10000-0000-4000-8000-000000000001','CP6-RACE','R1','CP6 Race Pattern',9801,true,
  'c8c00000-0000-4000-8000-000000000001','c8c00000-0000-4000-8000-000000000001'
);
insert into erp.sizes(id,size_code,sort_order)
values('c8c10000-0000-4000-8000-000000000002','CP6-RACE-S',9801);
insert into erp.product_model_sizes(model_id,size_id,sort_order)
values('a2000000-0000-0000-0000-000000000001','c8c10000-0000-4000-8000-000000000002',801);
insert into erp.brands(id,brand_code,brand_name)
values('c8c10000-0000-4000-8000-000000000003','CP6-RACE-BRAND','CP6 Race Brand');
insert into erp.products(
  id,sku,model_id,brand_id,color_name,size_id,product_name,
  identity_root_id,effective_from,is_active,is_portal_visible
) values(
  'c8c10000-0000-4000-8000-000000000004','CP6-RACE-SKU',
  'a2000000-0000-0000-0000-000000000001','c8c10000-0000-4000-8000-000000000003',
  'NAVY','c8c10000-0000-4000-8000-000000000002','CP6 Race Final SKU',
  'c8c10000-0000-4000-8000-000000000004','2026-01-01 00:00+00',true,true
);
insert into erp.accessory_bom_versions(
  product_id,version_label,effective_from,is_active,notes
) values(
  'c8c10000-0000-4000-8000-000000000004','CP6-RACE-EMPTY',
  '2026-01-01 00:00+00',true,'Explicit empty BOM for isolated race proof'
);

insert into erp.locations(id,location_code,location_name,location_type)
values('c8c20000-0000-4000-8000-000000000001','CP6-RACE-FG','CP6 Race FG','FG_WAREHOUSE');
insert into erp.laundry_vendors(id,vendor_code,vendor_name,is_active,notes)
values('c8c20000-0000-4000-8000-000000000002','CP6-RACE-L','CP6 Race Laundry',true,'Isolated race');
insert into erp.wash_processes(id,process_code,process_name,is_active)
values('c8c20000-0000-4000-8000-000000000003','CP6-RACE-WASH','CP6 Race Wash',true);
insert into erp.laundry_vendor_rate_versions(
  id,vendor_id,wash_process_id,rate_per_pcs,effective_from,effective_to,notes
) values(
  'c8c20000-0000-4000-8000-000000000004','c8c20000-0000-4000-8000-000000000002',
  'c8c20000-0000-4000-8000-000000000003',7,'2026-01-01 00:00+00',null,'Exact race rate'
);

insert into erp.suppliers(id,supplier_code,supplier_name,supplier_type)
values('c8c30000-0000-4000-8000-000000000001','CP6-RACE-SUP','CP6 Race Supplier','MATERIAL');
insert into erp.materials(id,material_sku,material_name,material_type,unit_code)
values('c8c30000-0000-4000-8000-000000000002','CP6-RACE-FAB','CP6 Race Fabric','FABRIC','yd');
insert into erp.material_rolls(
  id,material_id,supplier_id,roll_number,original_qty,cached_qty,status,received_at
) values(
  'c8c30000-0000-4000-8000-000000000003','c8c30000-0000-4000-8000-000000000002',
  'c8c30000-0000-4000-8000-000000000001','CP6-RACE-ROLL',10,10,'AVAILABLE','2026-08-31 07:00+00'
);

insert into erp.production_orders(
  id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,physical_start_at,notes
) values(
  'c8c40000-0000-4000-8000-000000000001','CP6-RACE-PO',
  'a2000000-0000-0000-0000-000000000001','a1000000-0000-0000-0000-000000000001',
  10,'SEWING','SEWING','2026-09-01 07:00+00','CP6 isolated race'
);
insert into erp.cutting_batches(id,po_id,batch_number,cut_at,status,notes)
values(
  'c8c40000-0000-4000-8000-000000000002','c8c40000-0000-4000-8000-000000000001',
  'CP6-RACE-CUT','2026-09-01 08:00+00','OPEN','CP6 isolated race'
);
insert into erp.cutting_groups(
  id,po_id,group_number,cut_at,status,cutting_batch_id,pattern_id,notes
) values(
  'c8c40000-0000-4000-8000-000000000003','c8c40000-0000-4000-8000-000000000001',
  'CP6-RACE-GROUP','2026-09-01 08:00+00','CUT','c8c40000-0000-4000-8000-000000000002',
  'c8c10000-0000-4000-8000-000000000001','Immutable isolated race source'
);
insert into erp.cutting_group_size_slots(id,cutting_group_id,slot_no,size_id,drawing_no)
values(
  'c8c40000-0000-4000-8000-000000000004','c8c40000-0000-4000-8000-000000000003',
  1,'c8c10000-0000-4000-8000-000000000002',1
);
insert into erp.cutting_group_rolls(
  id,cutting_group_id,roll_id,qty_issued,qty_consumed,qty_reported_remaining,
  qty_physically_returned,return_destination,unit_cost_snapshot,notes
) values(
  'c8c40000-0000-4000-8000-000000000005','c8c40000-0000-4000-8000-000000000003',
  'c8c30000-0000-4000-8000-000000000003',10,10,0,0,'NONE',0,'CP6 isolated race'
);
insert into erp.cutting_roll_yields(id,cutting_group_roll_id,size_slot_id,qty_pcs)
values(
  'c8c40000-0000-4000-8000-000000000006','c8c40000-0000-4000-8000-000000000005',
  'c8c40000-0000-4000-8000-000000000004',10
);
insert into erp.cutting_pickups(
  id,cutting_group_id,contractor_id,picked_up_at,allocation_mode,status,notes,created_by
) values(
  'c8c40000-0000-4000-8000-000000000007','c8c40000-0000-4000-8000-000000000003',
  'a1000000-0000-0000-0000-000000000001','2026-09-01 09:00+00','ROLL','DRAFT',
  'CP6 isolated race','c8c00000-0000-4000-8000-000000000001'
);
insert into erp.cutting_distribution_batches(id,pickup_id,batch_no,notes)
values(
  'c8c40000-0000-4000-8000-000000000008','c8c40000-0000-4000-8000-000000000007',
  1,'CP6 isolated race'
);
insert into erp.cutting_distribution_allocations(id,batch_id,cutting_roll_yield_id,qty_pcs)
values(
  'c8c40000-0000-4000-8000-000000000009','c8c40000-0000-4000-8000-000000000008',
  'c8c40000-0000-4000-8000-000000000006',10
);
update erp.cutting_groups
set picked_up_at='2026-09-01 09:00+00',executor_name='CP6 Race Mandor',status='PICKED_UP'
where id='c8c40000-0000-4000-8000-000000000003';
update erp.cutting_pickups
set status='POSTED',posted_by='c8c00000-0000-4000-8000-000000000001',posted_at='2026-09-01 09:00+00'
where id='c8c40000-0000-4000-8000-000000000007';

insert into erp.po_work_component_snapshots(
  id,po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at
) values(
  'c8c50000-0000-4000-8000-000000000001','c8c40000-0000-4000-8000-000000000001',
  'a4000000-0000-0000-0000-000000000001',1,0,'2026-09-01 09:30+00'
);
insert into erp.work_completion_events(
  id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes,created_by
) values(
  'c8c50000-0000-4000-8000-000000000002','CP6-RACE-WC',
  'c8c40000-0000-4000-8000-000000000001','a1000000-0000-0000-0000-000000000001',
  'c8c40000-0000-4000-8000-000000000003','2026-09-01 10:00+00','DRAFT',
  'CP6 sewn race capacity','c8c00000-0000-4000-8000-000000000001'
);
insert into erp.work_completion_lines(
  id,completion_id,po_component_snapshot_id,work_component_id,
  qty_completed,qty_payable,rate_snapshot,notes
) values(
  'c8c50000-0000-4000-8000-000000000003','c8c50000-0000-4000-8000-000000000002',
  'c8c50000-0000-4000-8000-000000000001','a4000000-0000-0000-0000-000000000001',
  10,10,0,'CP6 sewn race capacity'
);
select erp.post_work_completion('c8c50000-0000-4000-8000-000000000002');
select erp.record_sewing_terminal_v1(jsonb_build_object(
  'work_completion_id','c8c50000-0000-4000-8000-000000000002',
  'qty_pcs',10,'reason','CP6 isolated concurrency terminal'
),gen_random_uuid());

commit;
