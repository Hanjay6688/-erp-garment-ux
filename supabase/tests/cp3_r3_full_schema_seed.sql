-- Shared full-schema fixture seed for CP3 R3. Caller owns transaction/database cleanup.
\set ON_ERROR_STOP on

create temp table if not exists cp3_r3_ids(
  key text primary key,
  id uuid,
  value jsonb
) on commit preserve rows;

insert into erp.contractors(id,contractor_code,contractor_name,contractor_type,attendance_required)
values
 ('a1000000-0000-0000-0000-000000000001','CP3R3-NORMAL-A','CP3 R3 Normal A','MANDOR',true),
 ('a1000000-0000-0000-0000-000000000002','CP3R3-NORMAL-B','CP3 R3 Normal B','MANDOR',true),
 ('a1000000-0000-0000-0000-000000000003','CP3R3-SPECIAL','CP3 R3 Special','MANDOR',true),
 ('a1000000-0000-0000-0000-000000000004','CP3R3-EXEMPT','CP3 R3 Exempt','MANDOR',false);

insert into cp3_r3_ids(key,value) values
 ('policy_a',erp.set_contractor_hpp_policy_v1(
   jsonb_build_object('contractor_id','a1000000-0000-0000-0000-000000000001','effective_from','2025-12-01','is_special',false,'attendance_required',true,'reason','CP3 R3 normal A'),gen_random_uuid(),null)),
 ('policy_b',erp.set_contractor_hpp_policy_v1(
   jsonb_build_object('contractor_id','a1000000-0000-0000-0000-000000000002','effective_from','2025-12-01','is_special',false,'attendance_required',true,'reason','CP3 R3 normal B'),gen_random_uuid(),null)),
 ('policy_special',erp.set_contractor_hpp_policy_v1(
   jsonb_build_object('contractor_id','a1000000-0000-0000-0000-000000000003','effective_from','2025-12-01','is_special',true,'attendance_required',true,'reason','CP3 R3 explicit special'),gen_random_uuid(),null)),
 ('policy_exempt',erp.set_contractor_hpp_policy_v1(
   jsonb_build_object('contractor_id','a1000000-0000-0000-0000-000000000004','effective_from','2025-12-01','is_special',false,'attendance_required',false,'reason','CP3 R3 attendance exempt'),gen_random_uuid(),null));

insert into erp.product_models(id,model_code,model_name)
values('a2000000-0000-0000-0000-000000000001','CP3R3-MODEL','CP3 R3 Model');
insert into erp.sizes(id,size_code,sort_order)
values('a2100000-0000-0000-0000-000000000001','CP3R3-SIZE',9001);
insert into erp.product_model_sizes(model_id,size_id,sort_order)
values('a2000000-0000-0000-0000-000000000001','a2100000-0000-0000-0000-000000000001',1);

insert into erp.production_orders(
  id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,physical_start_at
) values
 ('a3000000-0000-0000-0000-000000000001','CP3R3-PO-A','a2000000-0000-0000-0000-000000000001','a1000000-0000-0000-0000-000000000001',100,'SEWING','SEWING','2025-12-31 08:00:00+07'),
 ('a3000000-0000-0000-0000-000000000002','CP3R3-PO-B','a2000000-0000-0000-0000-000000000001','a1000000-0000-0000-0000-000000000002',100,'SEWING','SEWING','2025-12-31 08:00:00+07'),
 ('a3000000-0000-0000-0000-000000000003','CP3R3-PO-S','a2000000-0000-0000-0000-000000000001','a1000000-0000-0000-0000-000000000003',100,'SEWING','SEWING','2025-12-31 08:00:00+07'),
 ('a3000000-0000-0000-0000-000000000004','CP3R3-PO-E','a2000000-0000-0000-0000-000000000001','a1000000-0000-0000-0000-000000000004',100,'SEWING','SEWING','2025-12-31 08:00:00+07');

insert into erp.cutting_batches(id,po_id,batch_number,cut_at,status,notes)
values
 ('a3100000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000001','CP3R3-BATCH-A','2025-12-31 09:00:00+07','OPEN','CP3 R3'),
 ('a3100000-0000-0000-0000-000000000002','a3000000-0000-0000-0000-000000000002','CP3R3-BATCH-B','2025-12-31 09:00:00+07','OPEN','CP3 R3'),
 ('a3100000-0000-0000-0000-000000000003','a3000000-0000-0000-0000-000000000003','CP3R3-BATCH-S','2025-12-31 09:00:00+07','OPEN','CP3 R3'),
 ('a3100000-0000-0000-0000-000000000004','a3000000-0000-0000-0000-000000000004','CP3R3-BATCH-E','2025-12-31 09:00:00+07','OPEN','CP3 R3');

insert into erp.cutting_groups(
  id,po_id,group_number,cut_at,picked_up_at,status,cutting_batch_id,notes
) values
 ('a3200000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000001','CP3R3-GROUP-A','2025-12-31 09:00:00+07','2025-12-31 10:00:00+07','SEWING','a3100000-0000-0000-0000-000000000001','CP3 R3'),
 ('a3200000-0000-0000-0000-000000000002','a3000000-0000-0000-0000-000000000002','CP3R3-GROUP-B','2025-12-31 09:00:00+07','2025-12-31 10:00:00+07','SEWING','a3100000-0000-0000-0000-000000000002','CP3 R3'),
 ('a3200000-0000-0000-0000-000000000003','a3000000-0000-0000-0000-000000000003','CP3R3-GROUP-S','2025-12-31 09:00:00+07','2025-12-31 10:00:00+07','SEWING','a3100000-0000-0000-0000-000000000003','CP3 R3'),
 ('a3200000-0000-0000-0000-000000000004','a3000000-0000-0000-0000-000000000004','CP3R3-GROUP-E','2025-12-31 09:00:00+07','2025-12-31 10:00:00+07','SEWING','a3100000-0000-0000-0000-000000000004','CP3 R3');

insert into erp.cutting_group_size_slots(id,cutting_group_id,slot_no,size_id,drawing_no)
values
 ('a3210000-0000-0000-0000-000000000001','a3200000-0000-0000-0000-000000000001',1,'a2100000-0000-0000-0000-000000000001',1),
 ('a3210000-0000-0000-0000-000000000002','a3200000-0000-0000-0000-000000000002',1,'a2100000-0000-0000-0000-000000000001',1),
 ('a3210000-0000-0000-0000-000000000003','a3200000-0000-0000-0000-000000000003',1,'a2100000-0000-0000-0000-000000000001',1),
 ('a3210000-0000-0000-0000-000000000004','a3200000-0000-0000-0000-000000000004',1,'a2100000-0000-0000-0000-000000000001',1);

insert into erp.cutting_qty_corrections(
  id,correction_number,cutting_batch_id,correction_type,reason_code,reason,physical_at
) values
 ('a3300000-0000-0000-0000-000000000001','CP3R3-CORR-A','a3100000-0000-0000-0000-000000000001','RECOUNT','TEST_SEED','CP3 R3 100 pcs','2025-12-31 11:00:00+07'),
 ('a3300000-0000-0000-0000-000000000002','CP3R3-CORR-B','a3100000-0000-0000-0000-000000000002','RECOUNT','TEST_SEED','CP3 R3 100 pcs','2025-12-31 11:00:00+07'),
 ('a3300000-0000-0000-0000-000000000003','CP3R3-CORR-S','a3100000-0000-0000-0000-000000000003','RECOUNT','TEST_SEED','CP3 R3 100 pcs','2025-12-31 11:00:00+07'),
 ('a3300000-0000-0000-0000-000000000004','CP3R3-CORR-E','a3100000-0000-0000-0000-000000000004','RECOUNT','TEST_SEED','CP3 R3 100 pcs','2025-12-31 11:00:00+07');
insert into erp.cutting_qty_correction_lines(
  correction_id,cutting_group_id,size_slot_id,qty_delta_pcs,notes
) values
 ('a3300000-0000-0000-0000-000000000001','a3200000-0000-0000-0000-000000000001','a3210000-0000-0000-0000-000000000001',100,'CP3 R3'),
 ('a3300000-0000-0000-0000-000000000002','a3200000-0000-0000-0000-000000000002','a3210000-0000-0000-0000-000000000002',100,'CP3 R3'),
 ('a3300000-0000-0000-0000-000000000003','a3200000-0000-0000-0000-000000000003','a3210000-0000-0000-0000-000000000003',100,'CP3 R3'),
 ('a3300000-0000-0000-0000-000000000004','a3200000-0000-0000-0000-000000000004','a3210000-0000-0000-0000-000000000004',100,'CP3 R3');

insert into erp.work_components(id,component_code,component_name,component_category,sequence_default)
values('a4000000-0000-0000-0000-000000000001','CP3R3-SEW','CP3 R3 Sewing','LABOR',1);
insert into erp.po_work_component_snapshots(
  id,po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at
) values
 ('a4100000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000001','a4000000-0000-0000-0000-000000000001',1,1,'2025-12-31 10:00:00+07'),
 ('a4100000-0000-0000-0000-000000000002','a3000000-0000-0000-0000-000000000002','a4000000-0000-0000-0000-000000000001',1,1,'2025-12-31 10:00:00+07'),
 ('a4100000-0000-0000-0000-000000000003','a3000000-0000-0000-0000-000000000003','a4000000-0000-0000-0000-000000000001',1,1,'2025-12-31 10:00:00+07'),
 ('a4100000-0000-0000-0000-000000000004','a3000000-0000-0000-0000-000000000004','a4000000-0000-0000-0000-000000000001',1,1,'2025-12-31 10:00:00+07');

insert into erp.work_completion_events(
  id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes
) values
 ('a5000000-0000-0000-0000-000000000001','CP3R3-WC-A','a3000000-0000-0000-0000-000000000001','a1000000-0000-0000-0000-000000000001','a3200000-0000-0000-0000-000000000001','2025-12-31 17:30:00+00','DRAFT','00:30 Jakarta boundary'),
 ('a5000000-0000-0000-0000-000000000002','CP3R3-WC-B','a3000000-0000-0000-0000-000000000002','a1000000-0000-0000-0000-000000000002','a3200000-0000-0000-0000-000000000002','2026-01-01 11:00:00+07','DRAFT','CP3 R3'),
 ('a5000000-0000-0000-0000-000000000003','CP3R3-WC-S','a3000000-0000-0000-0000-000000000003','a1000000-0000-0000-0000-000000000003','a3200000-0000-0000-0000-000000000003','2026-01-01 12:00:00+07','DRAFT','CP3 R3'),
 ('a5000000-0000-0000-0000-000000000004','CP3R3-WC-E','a3000000-0000-0000-0000-000000000004','a1000000-0000-0000-0000-000000000004','a3200000-0000-0000-0000-000000000004','2026-01-01 13:00:00+07','DRAFT','CP3 R3');
insert into erp.work_completion_lines(
  id,completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot
) values
 ('a5100000-0000-0000-0000-000000000001','a5000000-0000-0000-0000-000000000001','a4100000-0000-0000-0000-000000000001','a4000000-0000-0000-0000-000000000001',60,60,0),
 ('a5100000-0000-0000-0000-000000000002','a5000000-0000-0000-0000-000000000002','a4100000-0000-0000-0000-000000000002','a4000000-0000-0000-0000-000000000001',40,40,0),
 ('a5100000-0000-0000-0000-000000000003','a5000000-0000-0000-0000-000000000003','a4100000-0000-0000-0000-000000000003','a4000000-0000-0000-0000-000000000001',100,100,0),
 ('a5100000-0000-0000-0000-000000000004','a5000000-0000-0000-0000-000000000004','a4100000-0000-0000-0000-000000000004','a4000000-0000-0000-0000-000000000001',100,100,0);

select erp.post_work_completion('a5000000-0000-0000-0000-000000000001');
select erp.post_work_completion('a5000000-0000-0000-0000-000000000002');
select erp.post_work_completion('a5000000-0000-0000-0000-000000000003');
select erp.post_work_completion('a5000000-0000-0000-0000-000000000004');

insert into cp3_r3_ids(key,value) values
 ('sew_a',erp.record_sewing_terminal_v1(jsonb_build_object('work_completion_id','a5000000-0000-0000-0000-000000000001','qty_pcs',60,'reason','CP3 R3 terminal A'),gen_random_uuid())),
 ('sew_b',erp.record_sewing_terminal_v1(jsonb_build_object('work_completion_id','a5000000-0000-0000-0000-000000000002','qty_pcs',40,'reason','CP3 R3 terminal B'),gen_random_uuid())),
 ('sew_special',erp.record_sewing_terminal_v1(jsonb_build_object('work_completion_id','a5000000-0000-0000-0000-000000000003','qty_pcs',100,'reason','CP3 R3 terminal special'),gen_random_uuid())),
 ('sew_exempt',erp.record_sewing_terminal_v1(jsonb_build_object('work_completion_id','a5000000-0000-0000-0000-000000000004','qty_pcs',100,'reason','CP3 R3 terminal exempt'),gen_random_uuid()));

-- Create workers through the owning roster RPC.
insert into cp3_r3_ids(key,value) values
 ('worker_a',erp.save_worker_roster_v1(jsonb_build_object(
   'contractor_id','a1000000-0000-0000-0000-000000000001','worker_code','CP3R3-W-A','worker_name','CP3 R3 Worker A',
   'job_description','Jahit','pay_scheme','DAILY','initial_daily_rate',100,'rate_effective_from','2026-01-01',
   'joined_at','2026-01-01','is_active',true,'reason','CP3 R3 seed'),gen_random_uuid(),null)),
 ('worker_b',erp.save_worker_roster_v1(jsonb_build_object(
   'contractor_id','a1000000-0000-0000-0000-000000000002','worker_code','CP3R3-W-B','worker_name','CP3 R3 Worker B',
   'job_description','Jahit','pay_scheme','DAILY','initial_daily_rate',50,'rate_effective_from','2026-01-01',
   'joined_at','2026-01-01','is_active',true,'reason','CP3 R3 seed'),gen_random_uuid(),null)),
 ('worker_special',erp.save_worker_roster_v1(jsonb_build_object(
   'contractor_id','a1000000-0000-0000-0000-000000000003','worker_code','CP3R3-W-S','worker_name','CP3 R3 Worker Special',
   'job_description','Jahit','pay_scheme','DAILY','initial_daily_rate',999,'rate_effective_from','2026-01-01',
   'joined_at','2026-01-01','is_active',true,'reason','CP3 R3 seed'),gen_random_uuid(),null));

insert into cp3_r3_ids(key,value)
select 'attendance_a',erp.save_attendance_period_v1(jsonb_build_object(
  'contractor_id','a1000000-0000-0000-0000-000000000001','period_number','CP3R3-ATT-A',
  'period_start','2026-01-01','period_end','2026-01-01','pay_date','2026-01-02','reason','CP3 R3 seed',
  'attendance',jsonb_build_array(jsonb_build_object('worker_id',(select value->>'worker_id' from cp3_r3_ids where key='worker_a'),'attendance_date','2026-01-01','status','PRESENT'))
),gen_random_uuid(),null,false);
insert into cp3_r3_ids(key,value)
select 'attendance_b',erp.save_attendance_period_v1(jsonb_build_object(
  'contractor_id','a1000000-0000-0000-0000-000000000002','period_number','CP3R3-ATT-B',
  'period_start','2026-01-01','period_end','2026-01-01','pay_date','2026-01-02','reason','CP3 R3 seed',
  'attendance',jsonb_build_array(jsonb_build_object('worker_id',(select value->>'worker_id' from cp3_r3_ids where key='worker_b'),'attendance_date','2026-01-01','status','PRESENT'))
),gen_random_uuid(),null,false);
insert into cp3_r3_ids(key,value)
select 'attendance_special',erp.save_attendance_period_v1(jsonb_build_object(
  'contractor_id','a1000000-0000-0000-0000-000000000003','period_number','CP3R3-ATT-S',
  'period_start','2026-01-01','period_end','2026-01-01','pay_date','2026-01-02','reason','CP3 R3 seed',
  'attendance',jsonb_build_array(jsonb_build_object('worker_id',(select value->>'worker_id' from cp3_r3_ids where key='worker_special'),'attendance_date','2026-01-01','status','PRESENT'))
),gen_random_uuid(),null,false);

select erp.post_attendance_period_v1((select (value->>'period_id')::uuid from cp3_r3_ids where key='attendance_a'),'CP3 R3 post',gen_random_uuid(),(select (value->>'row_version')::bigint from cp3_r3_ids where key='attendance_a'));
select erp.post_attendance_period_v1((select (value->>'period_id')::uuid from cp3_r3_ids where key='attendance_b'),'CP3 R3 post',gen_random_uuid(),(select (value->>'row_version')::bigint from cp3_r3_ids where key='attendance_b'));
select erp.post_attendance_period_v1((select (value->>'period_id')::uuid from cp3_r3_ids where key='attendance_special'),'CP3 R3 post',gen_random_uuid(),(select (value->>'row_version')::bigint from cp3_r3_ids where key='attendance_special'));

insert into erp.payroll_settlements(
  id,payroll_number,contractor_id,period_start,period_end,status,payment_cash_account_id,payment_date,notes
) values
 ('a6000000-0000-0000-0000-000000000001','CP3R3-PAY-A','a1000000-0000-0000-0000-000000000001','2026-01-01','2026-01-01','DRAFT',(select id from erp.cash_accounts where is_active order by cash_account_code limit 1),'2026-01-02','CP3 R3'),
 ('a6000000-0000-0000-0000-000000000002','CP3R3-PAY-B','a1000000-0000-0000-0000-000000000002','2026-01-01','2026-01-01','DRAFT',(select id from erp.cash_accounts where is_active order by cash_account_code limit 1),'2026-01-02','CP3 R3'),
 ('a6000000-0000-0000-0000-000000000003','CP3R3-PAY-S','a1000000-0000-0000-0000-000000000003','2026-01-01','2026-01-01','DRAFT',(select id from erp.cash_accounts where is_active order by cash_account_code limit 1),'2026-01-02','CP3 R3');
select erp.populate_payroll_draft('a6000000-0000-0000-0000-000000000001');
select erp.populate_payroll_draft('a6000000-0000-0000-0000-000000000002');
select erp.populate_payroll_draft('a6000000-0000-0000-0000-000000000003');
select erp.approve_payroll('a6000000-0000-0000-0000-000000000001');
select erp.approve_payroll('a6000000-0000-0000-0000-000000000002');
select erp.approve_payroll('a6000000-0000-0000-0000-000000000003');
