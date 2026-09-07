-- Independent, internally consistent Potongan fixtures for the CP6 reversal
-- race matrix. Disposable cp6_race database only; the workflow destroys it.
\set ON_ERROR_STOP on

begin;
set local timezone='UTC';
select set_config(
  'request.jwt.claims',
  jsonb_build_object('sub','c8c00000-0000-4000-8000-000000000101','role','authenticated')::text,
  true
);
select set_config('app.change_reason','CP6 reversal concurrency seed',true);

-- Eight distinct granular operators are reserved for the realistic scale
-- proof. They are not OWNER/ADMIN and can only use the public CP6 contracts.
insert into erp.app_roles(id,role_code,role_name,description)
values(
  md5('CP6-SCALE-OPERATOR-ROLE')::uuid,'CP6_SCALE_OPERATOR',
  'CP6 Scale Operator','Disposable multi-operator write/load proof'
);
insert into erp.app_role_permissions(role_id,permission_key)
select md5('CP6-SCALE-OPERATOR-ROLE')::uuid,x.permission_key
from unnest(array[
  'production.laundry.view','production.laundry.create',
  'production.laundry.post','production.laundry.reverse',
  'production.final_sku.view','production.final_sku.post',
  'production.final_sku.reverse'
]) x(permission_key);
insert into erp.app_users(
  id,auth_user_id,full_name,role,role_id,is_active
)
select
  md5('CP6-SCALE-APP-'||lpad(i::text,2,'0'))::uuid,
  md5('CP6-SCALE-AUTH-'||lpad(i::text,2,'0'))::uuid,
  'CP6 Scale Operator '||lpad(i::text,2,'0'),
  'CP6_SCALE_OPERATOR',md5('CP6-SCALE-OPERATOR-ROLE')::uuid,true
from generate_series(1,8) i;

do $seed$
declare
  v_case text;
  v_roll uuid;
  v_po uuid;
  v_cut uuid;
  v_group uuid;
  v_slot uuid;
  v_group_roll uuid;
  v_yield uuid;
  v_pickup uuid;
  v_batch uuid;
  v_allocation uuid;
  v_snapshot uuid;
  v_work uuid;
  v_work_line uuid;
begin
  foreach v_case in array array[
    'RECEIPT_FAILED','REVDEL_RECEIPT','RECEIPT_REVDEL',
    'REVDEL_FAILED','FAILED_REVDEL','REVRECEIPT_INVOICE',
    'REVRECEIPT_QC','REVQC_REVRECEIPT','REVRECEIPT_REVQC',
    'REPLACEMENT_INVERSE','REVQC_INVOICE',
    'INVOICE_REVQC','REVQC_INVOICE_REV','INVOICE_REV_REVQC',
    'REVQC_POSTQC','POSTQC_REVQC',
    'PARTIAL_LABOR_COST',
    'SALE_SAVE_INVOICE','INVOICE_SALE_SAVE',
    'SALE_POST_INVOICE','INVOICE_SALE_POST',
    'SALE_CANCEL_INVOICE','INVOICE_SALE_CANCEL',
    'SALE_REVERSE_INVOICE','INVOICE_SALE_REVERSE',
    'SCALE_OP_01','SCALE_OP_02','SCALE_OP_03','SCALE_OP_04',
    'SCALE_OP_05','SCALE_OP_06','SCALE_OP_07','SCALE_OP_08'
  ] loop
    v_roll:=md5('CP6-MATRIX-ROLL-'||v_case)::uuid;
    v_po:=md5('CP6-MATRIX-PO-'||v_case)::uuid;
    v_cut:=md5('CP6-MATRIX-CUT-'||v_case)::uuid;
    v_group:=md5('CP6-MATRIX-GROUP-'||v_case)::uuid;
    v_slot:=md5('CP6-MATRIX-SLOT-'||v_case)::uuid;
    v_group_roll:=md5('CP6-MATRIX-GROUP-ROLL-'||v_case)::uuid;
    v_yield:=md5('CP6-MATRIX-YIELD-'||v_case)::uuid;
    v_pickup:=md5('CP6-MATRIX-PICKUP-'||v_case)::uuid;
    v_batch:=md5('CP6-MATRIX-BATCH-'||v_case)::uuid;
    v_allocation:=md5('CP6-MATRIX-ALLOCATION-'||v_case)::uuid;
    v_snapshot:=md5('CP6-MATRIX-SNAPSHOT-'||v_case)::uuid;
    v_work:=md5('CP6-MATRIX-WORK-'||v_case)::uuid;
    v_work_line:=md5('CP6-MATRIX-WORK-LINE-'||v_case)::uuid;

    insert into erp.material_rolls(
      id,material_id,supplier_id,roll_number,original_qty,cached_qty,status,received_at
    ) values(
      v_roll,'c8c30000-0000-4000-8000-000000000002',
      'c8c30000-0000-4000-8000-000000000001','CP6-MX-'||v_case,
      10,10,'AVAILABLE','2026-08-29 07:00:00+00'
    );
    insert into erp.production_orders(
      id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,
      physical_start_at,notes
    ) values(
      v_po,'CP6-MX-'||v_case,'a2000000-0000-0000-0000-000000000001',
      'a1000000-0000-0000-0000-000000000001',10,'SEWING','SEWING',
      '2026-08-29 07:00:00+00','CP6 isolated reversal race source'
    );
    insert into erp.cutting_batches(id,po_id,batch_number,cut_at,status,notes)
    values(v_cut,v_po,'CP6-MX-CUT-'||v_case,'2026-08-29 08:00:00+00',
      'OPEN','CP6 isolated reversal race source');
    insert into erp.cutting_groups(
      id,po_id,group_number,cut_at,status,cutting_batch_id,pattern_id,notes
    ) values(
      v_group,v_po,'CP6-MX-G-'||v_case,'2026-08-29 08:00:00+00','CUT',
      v_cut,'c8c10000-0000-4000-8000-000000000001',
      'Immutable CP6 reversal race source'
    );
    insert into erp.cutting_group_size_slots(
      id,cutting_group_id,slot_no,size_id,drawing_no
    ) values(
      v_slot,v_group,1,'c8c10000-0000-4000-8000-000000000002',1
    );
    insert into erp.cutting_group_rolls(
      id,cutting_group_id,roll_id,qty_issued,qty_consumed,
      qty_reported_remaining,qty_physically_returned,return_destination,
      unit_cost_snapshot,notes
    ) values(
      v_group_roll,v_group,v_roll,10,10,0,0,'NONE',0,
      'CP6 isolated reversal race source'
    );
    insert into erp.cutting_roll_yields(
      id,cutting_group_roll_id,size_slot_id,qty_pcs
    ) values(v_yield,v_group_roll,v_slot,10);
    insert into erp.cutting_pickups(
      id,cutting_group_id,contractor_id,picked_up_at,allocation_mode,status,
      notes,created_by
    ) values(
      v_pickup,v_group,'a1000000-0000-0000-0000-000000000001',
      '2026-08-29 09:00:00+00','ROLL','DRAFT',
      'CP6 isolated reversal race source',
      'c8c00000-0000-4000-8000-000000000001'
    );
    insert into erp.cutting_distribution_batches(id,pickup_id,batch_no,notes)
    values(v_batch,v_pickup,1,'CP6 isolated reversal race source');
    insert into erp.cutting_distribution_allocations(
      id,batch_id,cutting_roll_yield_id,qty_pcs
    ) values(v_allocation,v_batch,v_yield,10);
    update erp.cutting_groups
    set picked_up_at='2026-08-29 09:00:00+00',
        executor_name='CP6 Matrix Mandor',status='PICKED_UP'
    where id=v_group;
    update erp.cutting_pickups
    set status='POSTED',
        posted_by='c8c00000-0000-4000-8000-000000000001',
        posted_at='2026-08-29 09:00:00+00'
    where id=v_pickup;

    insert into erp.po_work_component_snapshots(
      id,po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at
    ) values(
      v_snapshot,v_po,'a4000000-0000-0000-0000-000000000001',1,
      case when v_case='PARTIAL_LABOR_COST' then 2 else 0 end,
      '2026-08-29 09:30:00+00'
    );
    insert into erp.work_completion_events(
      id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,
      status,notes,created_by
    ) values(
      v_work,'CP6-MX-WC-'||v_case,v_po,
      'a1000000-0000-0000-0000-000000000001',v_group,
      '2026-08-29 10:00:00+00','DRAFT','CP6 matrix sewn capacity',
      'c8c00000-0000-4000-8000-000000000001'
    );
    insert into erp.work_completion_lines(
      id,completion_id,po_component_snapshot_id,work_component_id,
      qty_completed,qty_payable,rate_snapshot,notes
    ) values(
      v_work_line,v_work,v_snapshot,
      'a4000000-0000-0000-0000-000000000001',10,10,
      case when v_case='PARTIAL_LABOR_COST' then 2 else 0 end,
      'CP6 matrix sewn capacity'
    );
    perform erp.post_work_completion(v_work);
    perform erp.record_sewing_terminal_v1(jsonb_build_object(
      'work_completion_id',v_work,'qty_pcs',10,
      'reason','CP6 reversal matrix physical terminal'
    ),md5('CP6-MATRIX-TERMINAL-REQUEST-'||v_case)::uuid);
  end loop;
end
$seed$;

do $guard$
begin
  if (select count(*) from erp.production_orders
      where po_number like 'CP6-MX-%')<>33
     or exists(
       select 1 from erp.production_orders po
       join erp.cutting_groups g on g.po_id=po.id
       left join erp.v_wip_control_status_v1 w on w.cutting_group_id=g.id
       where po.po_number like 'CP6-MX-%'
         and coalesce(w.unsent_ready_qty_pcs,0)<>10
     ) then
    raise exception 'CP6 reversal concurrency foundation is incomplete';
  end if;
end
$guard$;

commit;
