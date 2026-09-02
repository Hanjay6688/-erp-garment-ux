-- Shared full-schema fixture seed for CP3 R4. Caller owns transaction/database cleanup.
\set ON_ERROR_STOP on
\ir cp3_r3_full_schema_seed.sql

-- Additional normal Mandors isolate approval and work-completion races.
insert into erp.contractors(id,contractor_code,contractor_name,contractor_type,attendance_required)
values
 ('a1000000-0000-0000-0000-000000000005','CP3R4-PENDING-C','CP3 R4 Pending Approval C','MANDOR',true),
 ('a1000000-0000-0000-0000-000000000006','CP3R4-TERMINAL-D','CP3 R4 Terminal Only D','MANDOR',true);

insert into cp3_r3_ids(key,value) values
 ('policy_c',erp.set_contractor_hpp_policy_v1(
   jsonb_build_object('contractor_id','a1000000-0000-0000-0000-000000000005','effective_from','2025-12-01','is_special',false,'attendance_required',true,'reason','CP3 R4 normal C'),gen_random_uuid(),null)),
 ('policy_d',erp.set_contractor_hpp_policy_v1(
   jsonb_build_object('contractor_id','a1000000-0000-0000-0000-000000000006','effective_from','2025-12-01','is_special',false,'attendance_required',true,'reason','CP3 R4 normal D'),gen_random_uuid(),null));

-- Terminal-only D has no payroll work item, so the owning terminal->work reversal chain can succeed.
insert into erp.production_orders(id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,physical_start_at)
values('a3000000-0000-0000-0000-000000000006','CP3R4-PO-D','a2000000-0000-0000-0000-000000000001','a1000000-0000-0000-0000-000000000006',10,'SEWING','SEWING','2026-04-01 08:00:00+07');
insert into erp.cutting_batches(id,po_id,batch_number,cut_at,status,notes)
values('a3100000-0000-0000-0000-000000000006','a3000000-0000-0000-0000-000000000006','CP3R4-BATCH-D','2026-04-01 08:30:00+07','OPEN','CP3 R4');
insert into erp.cutting_groups(id,po_id,group_number,cut_at,picked_up_at,status,cutting_batch_id,notes)
values('a3200000-0000-0000-0000-000000000006','a3000000-0000-0000-0000-000000000006','CP3R4-GROUP-D','2026-04-01 08:30:00+07','2026-04-01 09:00:00+07','SEWING','a3100000-0000-0000-0000-000000000006','CP3 R4');
insert into erp.cutting_group_size_slots(id,cutting_group_id,slot_no,size_id,drawing_no)
values('a3210000-0000-0000-0000-000000000006','a3200000-0000-0000-0000-000000000006',1,'a2100000-0000-0000-0000-000000000001',1);
insert into erp.cutting_qty_corrections(id,correction_number,cutting_batch_id,correction_type,reason_code,reason,physical_at)
values('a3300000-0000-0000-0000-000000000006','CP3R4-CORR-D','a3100000-0000-0000-0000-000000000006','RECOUNT','TEST_SEED','CP3 R4 10 pcs','2026-04-01 09:15:00+07');
insert into erp.cutting_qty_correction_lines(correction_id,cutting_group_id,size_slot_id,qty_delta_pcs,notes)
values('a3300000-0000-0000-0000-000000000006','a3200000-0000-0000-0000-000000000006','a3210000-0000-0000-0000-000000000006',10,'CP3 R4');
insert into erp.po_work_component_snapshots(id,po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at)
values('a4100000-0000-0000-0000-000000000006','a3000000-0000-0000-0000-000000000006','a4000000-0000-0000-0000-000000000001',1,0,'2026-04-01 09:00:00+07');

-- Authoritative sewing facts for independent race periods.
insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes)
values
 ('a5000000-0000-0000-0000-000000000020','CP3R4-WC-FEB','a3000000-0000-0000-0000-000000000001','a1000000-0000-0000-0000-000000000001','a3200000-0000-0000-0000-000000000001','2026-02-01 10:00:00+07','DRAFT','CP3 R4 approval race'),
 ('a5000000-0000-0000-0000-000000000030','CP3R4-WC-MAR','a3000000-0000-0000-0000-000000000001','a1000000-0000-0000-0000-000000000001','a3200000-0000-0000-0000-000000000001','2026-03-01 10:00:00+07','DRAFT','CP3 R4 policy race'),
 ('a5000000-0000-0000-0000-000000000040','CP3R4-WC-APR-D','a3000000-0000-0000-0000-000000000006','a1000000-0000-0000-0000-000000000006','a3200000-0000-0000-0000-000000000006','2026-04-01 10:00:00+07','DRAFT','CP3 R4 reverse work race');
insert into erp.work_completion_lines(id,completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot)
values
 ('a5100000-0000-0000-0000-000000000020','a5000000-0000-0000-0000-000000000020','a4100000-0000-0000-0000-000000000001','a4000000-0000-0000-0000-000000000001',5,5,0),
 ('a5100000-0000-0000-0000-000000000030','a5000000-0000-0000-0000-000000000030','a4100000-0000-0000-0000-000000000001','a4000000-0000-0000-0000-000000000001',5,5,0),
 ('a5100000-0000-0000-0000-000000000040','a5000000-0000-0000-0000-000000000040','a4100000-0000-0000-0000-000000000006','a4000000-0000-0000-0000-000000000001',5,5,0);
select erp.post_work_completion('a5000000-0000-0000-0000-000000000020');
select erp.post_work_completion('a5000000-0000-0000-0000-000000000030');
select erp.post_work_completion('a5000000-0000-0000-0000-000000000040');
insert into cp3_r3_ids(key,value) values
 ('sew_feb',erp.record_sewing_terminal_v1(jsonb_build_object('work_completion_id','a5000000-0000-0000-0000-000000000020','qty_pcs',5,'reason','CP3 R4 February terminal'),gen_random_uuid())),
 ('sew_mar',erp.record_sewing_terminal_v1(jsonb_build_object('work_completion_id','a5000000-0000-0000-0000-000000000030','qty_pcs',5,'reason','CP3 R4 March terminal'),gen_random_uuid())),
 ('sew_apr_d',erp.record_sewing_terminal_v1(jsonb_build_object('work_completion_id','a5000000-0000-0000-0000-000000000040','qty_pcs',5,'reason','CP3 R4 April D terminal'),gen_random_uuid()));

-- Pending C attendance/payroll is deliberately left CALCULATED for approval races.
insert into cp3_r3_ids(key,value)
values('worker_c',erp.save_worker_roster_v1(jsonb_build_object(
  'contractor_id','a1000000-0000-0000-0000-000000000005','worker_code','CP3R4-W-C','worker_name','CP3 R4 Worker C',
  'job_description','Jahit','pay_scheme','DAILY','initial_daily_rate',70,'rate_effective_from','2026-02-01',
  'joined_at','2026-02-01','is_active',true,'reason','CP3 R4 seed'),gen_random_uuid(),null));
insert into cp3_r3_ids(key,value)
select 'attendance_c_feb',erp.save_attendance_period_v1(jsonb_build_object(
  'contractor_id','a1000000-0000-0000-0000-000000000005','period_number','CP3R4-ATT-C-FEB',
  'period_start','2026-02-01','period_end','2026-02-01','pay_date','2026-02-02','reason','CP3 R4 seed',
  'attendance',jsonb_build_array(jsonb_build_object('worker_id',(select value->>'worker_id' from cp3_r3_ids where key='worker_c'),'attendance_date','2026-02-01','status','PRESENT'))
),gen_random_uuid(),null,false);
select erp.post_attendance_period_v1(
  (select (value->>'period_id')::uuid from cp3_r3_ids where key='attendance_c_feb'),
  'CP3 R4 post C February',gen_random_uuid(),
  (select (value->>'row_version')::bigint from cp3_r3_ids where key='attendance_c_feb'));
insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,status,payment_cash_account_id,payment_date,notes)
values('a6000000-0000-0000-0000-000000000021','CP3R4-PAY-C-FEB-PENDING','a1000000-0000-0000-0000-000000000005','2026-02-01','2026-02-01','DRAFT',(select id from erp.cash_accounts where is_active order by cash_account_code limit 1),'2026-02-02','CP3 R4 pending approval');
select erp.populate_payroll_draft('a6000000-0000-0000-0000-000000000021');

-- A supplies existing approved numerator for February, March, and April.
insert into cp3_r3_ids(key,value)
select 'attendance_a_feb',erp.save_attendance_period_v1(jsonb_build_object(
  'contractor_id','a1000000-0000-0000-0000-000000000001','period_number','CP3R4-ATT-A-FEB',
  'period_start','2026-02-01','period_end','2026-02-01','pay_date','2026-02-02','reason','CP3 R4 seed',
  'attendance',jsonb_build_array(jsonb_build_object('worker_id',(select value->>'worker_id' from cp3_r3_ids where key='worker_a'),'attendance_date','2026-02-01','status','PRESENT'))
),gen_random_uuid(),null,false);
insert into cp3_r3_ids(key,value)
select 'attendance_a_mar',erp.save_attendance_period_v1(jsonb_build_object(
  'contractor_id','a1000000-0000-0000-0000-000000000001','period_number','CP3R4-ATT-A-MAR',
  'period_start','2026-03-01','period_end','2026-03-01','pay_date','2026-03-02','reason','CP3 R4 seed',
  'attendance',jsonb_build_array(jsonb_build_object('worker_id',(select value->>'worker_id' from cp3_r3_ids where key='worker_a'),'attendance_date','2026-03-01','status','PRESENT'))
),gen_random_uuid(),null,false);
insert into cp3_r3_ids(key,value)
select 'attendance_a_apr',erp.save_attendance_period_v1(jsonb_build_object(
  'contractor_id','a1000000-0000-0000-0000-000000000001','period_number','CP3R4-ATT-A-APR',
  'period_start','2026-04-01','period_end','2026-04-01','pay_date','2026-04-02','reason','CP3 R4 seed',
  'attendance',jsonb_build_array(jsonb_build_object('worker_id',(select value->>'worker_id' from cp3_r3_ids where key='worker_a'),'attendance_date','2026-04-01','status','PRESENT'))
),gen_random_uuid(),null,false);
select erp.post_attendance_period_v1((select (value->>'period_id')::uuid from cp3_r3_ids where key='attendance_a_feb'),'CP3 R4 post A February',gen_random_uuid(),(select (value->>'row_version')::bigint from cp3_r3_ids where key='attendance_a_feb'));
select erp.post_attendance_period_v1((select (value->>'period_id')::uuid from cp3_r3_ids where key='attendance_a_mar'),'CP3 R4 post A March',gen_random_uuid(),(select (value->>'row_version')::bigint from cp3_r3_ids where key='attendance_a_mar'));
select erp.post_attendance_period_v1((select (value->>'period_id')::uuid from cp3_r3_ids where key='attendance_a_apr'),'CP3 R4 post A April',gen_random_uuid(),(select (value->>'row_version')::bigint from cp3_r3_ids where key='attendance_a_apr'));

insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,status,payment_cash_account_id,payment_date,notes)
values
 ('a6000000-0000-0000-0000-000000000020','CP3R4-PAY-A-FEB','a1000000-0000-0000-0000-000000000001','2026-02-01','2026-02-01','DRAFT',(select id from erp.cash_accounts where is_active order by cash_account_code limit 1),'2026-02-02','CP3 R4 February base'),
 ('a6000000-0000-0000-0000-000000000030','CP3R4-PAY-A-MAR','a1000000-0000-0000-0000-000000000001','2026-03-01','2026-03-01','DRAFT',(select id from erp.cash_accounts where is_active order by cash_account_code limit 1),'2026-03-02','CP3 R4 March base'),
 ('a6000000-0000-0000-0000-000000000040','CP3R4-PAY-A-APR','a1000000-0000-0000-0000-000000000001','2026-04-01','2026-04-01','DRAFT',(select id from erp.cash_accounts where is_active order by cash_account_code limit 1),'2026-04-02','CP3 R4 April base');
select erp.populate_payroll_draft('a6000000-0000-0000-0000-000000000020');
select erp.populate_payroll_draft('a6000000-0000-0000-0000-000000000030');
select erp.populate_payroll_draft('a6000000-0000-0000-0000-000000000040');
select erp.approve_payroll('a6000000-0000-0000-0000-000000000020');
select erp.approve_payroll('a6000000-0000-0000-0000-000000000030');
select erp.approve_payroll('a6000000-0000-0000-0000-000000000040');
