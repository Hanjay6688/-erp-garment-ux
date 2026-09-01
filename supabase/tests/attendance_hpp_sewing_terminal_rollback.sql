\set ON_ERROR_STOP on

begin;
set local timezone = 'UTC';
set local lock_timeout = '5s';
set local statement_timeout = '120s';

create temporary table cp3_test_state(
  key text primary key,
  id uuid,
  value_text text,
  value_numeric numeric,
  value_bigint bigint
) on commit drop;

-- Fixed, rollback-only fixture identities.
insert into erp.product_models(id,model_code,model_name)
values ('26140000-0000-4000-8000-000000000001','CP3-MODEL','CP3 HPP Model');
insert into erp.sizes(id,size_code,sort_order)
values ('26140000-0000-4000-8000-000000000002','CP3-SIZE',1);
insert into erp.materials(id,material_sku,material_name,material_type,unit_code)
values ('26140000-0000-4000-8000-000000000003','CP3-FABRIC','CP3 Fabric','FABRIC','YARD');

insert into erp.contractors(id,contractor_code,contractor_name,contractor_type,attendance_required)
values
 ('26140000-0000-4000-8000-000000000011','CP3-N1','CP3 Normal 1','MANDOR',true),
 ('26140000-0000-4000-8000-000000000012','CP3-N2','CP3 Normal 2','MANDOR',true),
 ('26140000-0000-4000-8000-000000000013','CP3-SP','CP3 Explicit Special','MANDOR',true),
 ('26140000-0000-4000-8000-000000000014','CP3-EX','CP3 Attendance Exempt','MANDOR',false);

-- Worker, employment, and initial-rate history are created only through the
-- authoritative roster RPC. Generated identities are captured by psql variables so
-- the rollback fixture tests the guarded production contract instead of bypassing it.
select (erp.save_worker_roster_v1(
  jsonb_build_object(
    'contractor_id','26140000-0000-4000-8000-000000000011',
    'worker_code','CP3-W1','worker_name','Worker N1','job_description','Sewing',
    'pay_scheme','DAILY','joined_at','2026-01-01','is_active',true,
    'initial_daily_rate',1000,'rate_effective_from','2026-01-01',
    'reason','CP3 authoritative roster fixture'
  ),
  '26140000-0000-4000-8000-000000000091',null
)->>'worker_id')::text as cp3_worker_n1
\gset

select (erp.save_worker_roster_v1(
  jsonb_build_object(
    'contractor_id','26140000-0000-4000-8000-000000000012',
    'worker_code','CP3-W2','worker_name','Worker N2','job_description','Sewing',
    'pay_scheme','DAILY','joined_at','2026-01-01','is_active',true,
    'initial_daily_rate',500,'rate_effective_from','2026-01-01',
    'reason','CP3 authoritative roster fixture'
  ),
  '26140000-0000-4000-8000-000000000092',null
)->>'worker_id')::text as cp3_worker_n2
\gset

select (erp.save_worker_roster_v1(
  jsonb_build_object(
    'contractor_id','26140000-0000-4000-8000-000000000013',
    'worker_code','CP3-W3','worker_name','Worker Special','job_description','Sewing',
    'pay_scheme','DAILY','joined_at','2026-01-01','is_active',true,
    'initial_daily_rate',700,'rate_effective_from','2026-01-01',
    'reason','CP3 authoritative roster fixture'
  ),
  '26140000-0000-4000-8000-000000000093',null
)->>'worker_id')::text as cp3_worker_special
\gset

select (erp.save_worker_roster_v1(
  jsonb_build_object(
    'contractor_id','26140000-0000-4000-8000-000000000014',
    'worker_code','CP3-W4','worker_name','Worker Exempt','job_description','Sewing',
    'pay_scheme','DAILY','joined_at','2026-01-01','is_active',true,
    'initial_daily_rate',300,'rate_effective_from','2026-01-01',
    'reason','CP3 authoritative roster fixture'
  ),
  '26140000-0000-4000-8000-000000000094',null
)->>'worker_id')::text as cp3_worker_exempt
\gset

select erp.worker_daily_rate_version_id_at(:'cp3_worker_n1'::uuid,'2026-08-10')::text as cp3_rate_n1
\gset
select erp.worker_daily_rate_version_id_at(:'cp3_worker_n2'::uuid,'2026-08-10')::text as cp3_rate_n2
\gset
select erp.worker_daily_rate_version_id_at(:'cp3_worker_special'::uuid,'2026-08-10')::text as cp3_rate_special
\gset
select erp.worker_daily_rate_version_id_at(:'cp3_worker_exempt'::uuid,'2026-08-10')::text as cp3_rate_exempt
\gset

-- Explicit effective-dated policy. Special and attendance-required are independent fields.
select erp.save_contractor_hpp_policy_v1(
  jsonb_build_object('contractor_id','26140000-0000-4000-8000-000000000011','effective_from','2026-01-01','attendance_required',true,'is_special',false,'change_reason','CP3 normal policy'),
  '26140000-0000-4000-8000-000000000101',null
);
select erp.save_contractor_hpp_policy_v1(
  jsonb_build_object('contractor_id','26140000-0000-4000-8000-000000000012','effective_from','2026-01-01','attendance_required',true,'is_special',false,'change_reason','CP3 normal policy'),
  '26140000-0000-4000-8000-000000000102',null
);
select erp.save_contractor_hpp_policy_v1(
  jsonb_build_object('contractor_id','26140000-0000-4000-8000-000000000013','effective_from','2026-01-01','attendance_required',true,'is_special',true,'change_reason','CP3 explicit Special policy'),
  '26140000-0000-4000-8000-000000000103',null
);
select erp.save_contractor_hpp_policy_v1(
  jsonb_build_object('contractor_id','26140000-0000-4000-8000-000000000014','effective_from','2026-01-01','attendance_required',false,'is_special',false,'change_reason','CP3 attendance-exempt policy'),
  '26140000-0000-4000-8000-000000000104',null
);

do $test$
begin
  if (select is_special from erp.contractor_hpp_policy_versions where contractor_id='26140000-0000-4000-8000-000000000013') is not true then
    raise exception 'Special policy was not stored explicitly';
  end if;
  if (select attendance_required from erp.contractor_hpp_policy_versions where contractor_id='26140000-0000-4000-8000-000000000014') is not false then
    raise exception 'attendance_required=false policy was not stored explicitly';
  end if;
end;
$test$;

-- Attendance and payroll sources for August.
insert into erp.attendance_periods(id,period_number,contractor_id,period_start,period_end,pay_date,status,posting_reason)
values
 ('26140000-0000-4000-8000-000000000201','CP3-ATT-N1-AUG','26140000-0000-4000-8000-000000000011','2026-08-01','2026-08-31','2026-08-31','POSTED','CP3 fixture'),
 ('26140000-0000-4000-8000-000000000202','CP3-ATT-N2-AUG','26140000-0000-4000-8000-000000000012','2026-08-01','2026-08-31','2026-08-31','POSTED','CP3 fixture'),
 ('26140000-0000-4000-8000-000000000203','CP3-ATT-SP-AUG','26140000-0000-4000-8000-000000000013','2026-08-01','2026-08-31','2026-08-31','POSTED','CP3 fixture'),
 ('26140000-0000-4000-8000-000000000204','CP3-ATT-EX-AUG','26140000-0000-4000-8000-000000000014','2026-08-01','2026-08-31','2026-08-31','POSTED','CP3 fixture');

insert into erp.attendance_records(id,contractor_id,worker_id,attendance_date,status,paid_fraction,attendance_period_id,record_lifecycle,change_reason)
values
 ('26140000-0000-4000-8000-000000000211','26140000-0000-4000-8000-000000000011',:'cp3_worker_n1'::uuid,'2026-08-10','PRESENT',1,'26140000-0000-4000-8000-000000000201','POSTED','CP3 fixture'),
 ('26140000-0000-4000-8000-000000000212','26140000-0000-4000-8000-000000000012',:'cp3_worker_n2'::uuid,'2026-08-10','PRESENT',1,'26140000-0000-4000-8000-000000000202','POSTED','CP3 fixture'),
 ('26140000-0000-4000-8000-000000000213','26140000-0000-4000-8000-000000000013',:'cp3_worker_special'::uuid,'2026-08-10','PRESENT',1,'26140000-0000-4000-8000-000000000203','POSTED','CP3 fixture'),
 ('26140000-0000-4000-8000-000000000214','26140000-0000-4000-8000-000000000014',:'cp3_worker_exempt'::uuid,'2026-08-10','PRESENT',1,'26140000-0000-4000-8000-000000000204','POSTED','CP3 fixture');

insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,status,payment_date)
values
 ('26140000-0000-4000-8000-000000000221','CP3-PAY-N1-AUG','26140000-0000-4000-8000-000000000011','2026-08-01','2026-08-31','DRAFT','2026-08-31'),
 ('26140000-0000-4000-8000-000000000222','CP3-PAY-N2-AUG','26140000-0000-4000-8000-000000000012','2026-08-01','2026-08-31','DRAFT','2026-08-31'),
 ('26140000-0000-4000-8000-000000000223','CP3-PAY-SP-AUG','26140000-0000-4000-8000-000000000013','2026-08-01','2026-08-31','DRAFT','2026-08-31'),
 ('26140000-0000-4000-8000-000000000224','CP3-PAY-EX-AUG','26140000-0000-4000-8000-000000000014','2026-08-01','2026-08-31','DRAFT','2026-08-31');

insert into erp.payroll_attendance_items(payroll_id,worker_id,attendance_record_id,paid_fraction_snapshot,daily_rate_snapshot,worker_rate_version_id,attendance_date_snapshot,worker_name_snapshot,job_description_snapshot)
values
 ('26140000-0000-4000-8000-000000000221',:'cp3_worker_n1'::uuid,'26140000-0000-4000-8000-000000000211',1,1000,:'cp3_rate_n1'::uuid,'2026-08-10','Worker N1','Sewing'),
 ('26140000-0000-4000-8000-000000000222',:'cp3_worker_n2'::uuid,'26140000-0000-4000-8000-000000000212',1,500,:'cp3_rate_n2'::uuid,'2026-08-10','Worker N2','Sewing'),
 ('26140000-0000-4000-8000-000000000223',:'cp3_worker_special'::uuid,'26140000-0000-4000-8000-000000000213',1,700,:'cp3_rate_special'::uuid,'2026-08-10','Worker Special','Sewing'),
 ('26140000-0000-4000-8000-000000000224',:'cp3_worker_exempt'::uuid,'26140000-0000-4000-8000-000000000214',1,300,:'cp3_rate_exempt'::uuid,'2026-08-10','Worker Exempt','Sewing');

update erp.payroll_settlements set attendance_total=1000,status='PAID',settled_at='2026-08-31 10:00+00' where id='26140000-0000-4000-8000-000000000221';
update erp.payroll_settlements set attendance_total=500,status='PAID',settled_at='2026-08-31 10:00+00' where id='26140000-0000-4000-8000-000000000222';
update erp.payroll_settlements set attendance_total=700,status='PAID',settled_at='2026-08-31 10:00+00' where id='26140000-0000-4000-8000-000000000223';
update erp.payroll_settlements set attendance_total=300,status='PAID',settled_at='2026-08-31 10:00+00' where id='26140000-0000-4000-8000-000000000224';

-- N1 source debit intentionally includes Rp200 non-attendance extras. HPP may reclass only Rp1,000.
select erp.post_journal('PAYROLL_EXTRA_ACCRUAL','26140000-0000-4000-8000-000000000221','2026-08-31','CP3 N1 payroll accrual',jsonb_build_array(
 jsonb_build_object('mapping_key','LABOR_COST','debit',1200,'credit',0,'contractor_id','26140000-0000-4000-8000-000000000011','description','CP3 N1 payroll extra accrual'),
 jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',1200,'contractor_id','26140000-0000-4000-8000-000000000011','description','CP3 N1 payable')
));
select erp.post_journal('PAYROLL_EXTRA_ACCRUAL','26140000-0000-4000-8000-000000000222','2026-08-31','CP3 N2 payroll accrual',jsonb_build_array(
 jsonb_build_object('mapping_key','LABOR_COST','debit',500,'credit',0,'contractor_id','26140000-0000-4000-8000-000000000012','description','CP3 N2 payroll extra accrual'),
 jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',500,'contractor_id','26140000-0000-4000-8000-000000000012','description','CP3 N2 payable')
));
select erp.post_journal('PAYROLL_EXTRA_ACCRUAL','26140000-0000-4000-8000-000000000223','2026-08-31','CP3 Special payroll accrual',jsonb_build_array(
 jsonb_build_object('mapping_key','LABOR_COST','debit',700,'credit',0,'contractor_id','26140000-0000-4000-8000-000000000013','description','CP3 Special payroll extra accrual'),
 jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',700,'contractor_id','26140000-0000-4000-8000-000000000013','description','CP3 Special payable')
));
select erp.post_journal('PAYROLL_EXTRA_ACCRUAL','26140000-0000-4000-8000-000000000224','2026-08-31','CP3 Exempt payroll accrual',jsonb_build_array(
 jsonb_build_object('mapping_key','LABOR_COST','debit',300,'credit',0,'contractor_id','26140000-0000-4000-8000-000000000014','description','CP3 Exempt payroll extra accrual'),
 jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',300,'contractor_id','26140000-0000-4000-8000-000000000014','description','CP3 Exempt payable')
));

-- Four independent cutting groups. Only N1/N2 belong to the denominator.
insert into erp.production_orders(id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,physical_start_at)
values
 ('26140000-0000-4000-8000-000000000301','CP3-PO-N1','26140000-0000-4000-8000-000000000001','26140000-0000-4000-8000-000000000011',60,'SEWING','SEWING','2026-08-01'),
 ('26140000-0000-4000-8000-000000000302','CP3-PO-N2','26140000-0000-4000-8000-000000000001','26140000-0000-4000-8000-000000000012',40,'SEWING','SEWING','2026-08-01'),
 ('26140000-0000-4000-8000-000000000303','CP3-PO-SP','26140000-0000-4000-8000-000000000001','26140000-0000-4000-8000-000000000013',50,'SEWING','SEWING','2026-08-01'),
 ('26140000-0000-4000-8000-000000000304','CP3-PO-EX','26140000-0000-4000-8000-000000000001','26140000-0000-4000-8000-000000000014',30,'SEWING','SEWING','2026-08-01');

insert into erp.cutting_groups(id,po_id,group_number,cut_at,picked_up_at,status)
values
 ('26140000-0000-4000-8000-000000000311','26140000-0000-4000-8000-000000000301','CP3-G-N1','2026-08-01','2026-08-02','PICKED_UP'),
 ('26140000-0000-4000-8000-000000000312','26140000-0000-4000-8000-000000000302','CP3-G-N2','2026-08-01','2026-08-02','PICKED_UP'),
 ('26140000-0000-4000-8000-000000000313','26140000-0000-4000-8000-000000000303','CP3-G-SP','2026-08-01','2026-08-02','PICKED_UP'),
 ('26140000-0000-4000-8000-000000000314','26140000-0000-4000-8000-000000000304','CP3-G-EX','2026-08-01','2026-08-02','PICKED_UP');

insert into erp.material_rolls(id,material_id,roll_number,original_qty,cached_qty,status,received_at)
values
 ('26140000-0000-4000-8000-000000000321','26140000-0000-4000-8000-000000000003','CP3-R1',100,100,'AVAILABLE','2026-08-01'),
 ('26140000-0000-4000-8000-000000000322','26140000-0000-4000-8000-000000000003','CP3-R2',100,100,'AVAILABLE','2026-08-01'),
 ('26140000-0000-4000-8000-000000000323','26140000-0000-4000-8000-000000000003','CP3-R3',100,100,'AVAILABLE','2026-08-01'),
 ('26140000-0000-4000-8000-000000000324','26140000-0000-4000-8000-000000000003','CP3-R4',100,100,'AVAILABLE','2026-08-01');

insert into erp.cutting_group_rolls(id,cutting_group_id,roll_id,qty_issued,qty_consumed)
values
 ('26140000-0000-4000-8000-000000000331','26140000-0000-4000-8000-000000000311','26140000-0000-4000-8000-000000000321',60,60),
 ('26140000-0000-4000-8000-000000000332','26140000-0000-4000-8000-000000000312','26140000-0000-4000-8000-000000000322',40,40),
 ('26140000-0000-4000-8000-000000000333','26140000-0000-4000-8000-000000000313','26140000-0000-4000-8000-000000000323',50,50),
 ('26140000-0000-4000-8000-000000000334','26140000-0000-4000-8000-000000000314','26140000-0000-4000-8000-000000000324',30,30);
insert into erp.cutting_group_size_slots(id,cutting_group_id,slot_no,size_id)
values
 ('26140000-0000-4000-8000-000000000341','26140000-0000-4000-8000-000000000311',1,'26140000-0000-4000-8000-000000000002'),
 ('26140000-0000-4000-8000-000000000342','26140000-0000-4000-8000-000000000312',1,'26140000-0000-4000-8000-000000000002'),
 ('26140000-0000-4000-8000-000000000343','26140000-0000-4000-8000-000000000313',1,'26140000-0000-4000-8000-000000000002'),
 ('26140000-0000-4000-8000-000000000344','26140000-0000-4000-8000-000000000314',1,'26140000-0000-4000-8000-000000000002');
insert into erp.cutting_roll_yields(cutting_group_roll_id,size_slot_id,qty_pcs)
values
 ('26140000-0000-4000-8000-000000000331','26140000-0000-4000-8000-000000000341',60),
 ('26140000-0000-4000-8000-000000000332','26140000-0000-4000-8000-000000000342',40),
 ('26140000-0000-4000-8000-000000000333','26140000-0000-4000-8000-000000000343',50),
 ('26140000-0000-4000-8000-000000000334','26140000-0000-4000-8000-000000000344',30);

select erp.record_sewing_terminal_v1(jsonb_build_object('event_number','CP3-SEW-N1','po_id','26140000-0000-4000-8000-000000000301','cutting_group_id','26140000-0000-4000-8000-000000000311','qty_pcs',60,'physical_at','2026-08-20T08:00:00+07:00','reason','CP3 authoritative sewing completion'),'26140000-0000-4000-8000-000000000401');
select erp.record_sewing_terminal_v1(jsonb_build_object('event_number','CP3-SEW-N2','po_id','26140000-0000-4000-8000-000000000302','cutting_group_id','26140000-0000-4000-8000-000000000312','qty_pcs',40,'physical_at','2026-08-21T08:00:00+07:00','reason','CP3 authoritative sewing completion'),'26140000-0000-4000-8000-000000000402');
select erp.record_sewing_terminal_v1(jsonb_build_object('event_number','CP3-SEW-SP','po_id','26140000-0000-4000-8000-000000000303','cutting_group_id','26140000-0000-4000-8000-000000000313','qty_pcs',50,'physical_at','2026-08-22T08:00:00+07:00','reason','CP3 special sewing completion'),'26140000-0000-4000-8000-000000000403');
select erp.record_sewing_terminal_v1(jsonb_build_object('event_number','CP3-SEW-EX','po_id','26140000-0000-4000-8000-000000000304','cutting_group_id','26140000-0000-4000-8000-000000000314','qty_pcs',30,'physical_at','2026-08-23T08:00:00+07:00','reason','CP3 exempt sewing completion'),'26140000-0000-4000-8000-000000000404');

-- Required-key, NULL-safe, type, and unexpected-key negative corpus.
do $test$
declare v_failed boolean;
begin
  v_failed:=false;
  begin perform erp.record_sewing_terminal_v1(jsonb_build_object('event_number','BAD','po_id','26140000-0000-4000-8000-000000000301','cutting_group_id','26140000-0000-4000-8000-000000000311','qty_pcs',1,'physical_at','2026-08-20T08:00:00Z'),'26140000-0000-4000-8000-000000000411'); exception when others then v_failed:=true; end;
  if not v_failed then raise exception 'Missing required key passed'; end if;
  v_failed:=false;
  begin perform erp.record_sewing_terminal_v1(jsonb_build_object('event_number','BAD','po_id','26140000-0000-4000-8000-000000000301','cutting_group_id','26140000-0000-4000-8000-000000000311','qty_pcs',1,'physical_at','2026-08-20T08:00:00Z','reason',null),'26140000-0000-4000-8000-000000000412'); exception when others then v_failed:=true; end;
  if not v_failed then raise exception 'NULL required key passed'; end if;
  v_failed:=false;
  begin perform erp.record_sewing_terminal_v1(jsonb_build_object('event_number','BAD','po_id','26140000-0000-4000-8000-000000000301','cutting_group_id','26140000-0000-4000-8000-000000000311','qty_pcs','1','physical_at','2026-08-20T08:00:00Z','reason','bad type'),'26140000-0000-4000-8000-000000000413'); exception when others then v_failed:=true; end;
  if not v_failed then raise exception 'Wrong JSON type passed'; end if;
  v_failed:=false;
  begin perform erp.record_sewing_terminal_v1(jsonb_build_object('event_number','BAD','po_id','26140000-0000-4000-8000-000000000301','cutting_group_id','26140000-0000-4000-8000-000000000311','qty_pcs',1,'physical_at','2026-08-20T08:00:00Z','reason','rework injection','origin_type','REWORK'),'26140000-0000-4000-8000-000000000414'); exception when others then v_failed:=true; end;
  if not v_failed then raise exception 'Unexpected REWORK origin key passed'; end if;
end;
$test$;

-- Preview must use only normal Mandor sources and immutable SELESAI_DIJAHIT.
do $test$
declare v_preview jsonb;
begin
  v_preview:=erp.preview_attendance_hpp_pool_v1('2026-08-01','2026-08-31');
  if (v_preview->>'numerator_amount')::numeric is distinct from 1500
     or (v_preview->>'denominator_qty')::bigint is distinct from 100
     or v_preview->>'basis' is distinct from 'SELESAI_DIJAHIT'
     or (v_preview->>'qc_good_used')::boolean is not false
     or (v_preview->>'rework_good_used')::boolean is not false
  then raise exception 'Preview contract mismatch: %',v_preview; end if;
end;
$test$;

insert into cp3_test_state(key,id,value_bigint,value_text)
select 'aug_pool',(r->>'pool_id')::uuid,(r->>'row_version')::bigint,r->>'manifest_digest'
from (select erp.create_attendance_hpp_pool_v1(
 jsonb_build_object('pool_number','CP3-HPP-AUG','period_start','2026-08-01','period_end','2026-08-31','reason','CP3 August pool'),
 '26140000-0000-4000-8000-000000000501') r) x;

do $test$
declare v_pool uuid;v_digest_utc text;v_digest_jkt text;
begin
  select id into v_pool from cp3_test_state where key='aug_pool';
  if (select numerator_amount from erp.attendance_hpp_pools where id=v_pool) is distinct from 1500
     or (select denominator_qty from erp.attendance_hpp_pools where id=v_pool) is distinct from 100
     or (select count(*) from erp.attendance_hpp_pool_sources where pool_id=v_pool)<>2
     or (select count(*) from erp.attendance_hpp_pool_allocations where pool_id=v_pool)<>2
     or exists(select 1 from erp.attendance_hpp_pool_sources where pool_id=v_pool and contractor_id in ('26140000-0000-4000-8000-000000000013','26140000-0000-4000-8000-000000000014'))
     or exists(select 1 from erp.attendance_hpp_pool_allocations where pool_id=v_pool and contractor_id in ('26140000-0000-4000-8000-000000000013','26140000-0000-4000-8000-000000000014'))
  then raise exception 'Pool eligibility/source count mismatch'; end if;
  if (select allocation_amount from erp.attendance_hpp_pool_allocations where pool_id=v_pool and po_id='26140000-0000-4000-8000-000000000301') is distinct from 900
     or (select allocation_amount from erp.attendance_hpp_pool_allocations where pool_id=v_pool and po_id='26140000-0000-4000-8000-000000000302') is distinct from 600
  then raise exception 'Deterministic allocation mismatch'; end if;
  set local timezone='UTC'; select erp.attendance_hpp_pool_digest_v1(v_pool) into v_digest_utc;
  set local timezone='Asia/Jakarta'; select erp.attendance_hpp_pool_digest_v1(v_pool) into v_digest_jkt;
  if v_digest_utc is distinct from v_digest_jkt then raise exception 'Timezone changed manifest digest'; end if;
  perform erp.validate_attendance_hpp_pool_v1(v_pool);
end;
$test$;

-- Post and prove terminal credits are one-per-original debit line, not per destination.
insert into cp3_test_state(key,id,value_bigint,value_text)
select 'aug_post',(r->>'journal_entry_id')::uuid,(r->>'row_version')::bigint,r::text
from (
 select erp.post_attendance_hpp_pool_v1(
  (select id from cp3_test_state where key='aug_pool'),'CP3 post August',
  '26140000-0000-4000-8000-000000000502',
  (select row_version from erp.attendance_hpp_pools where id=(select id from cp3_test_state where key='aug_pool'))
 ) r
) x;

-- Same key/same payload must return cached response despite changed pool row_version.
do $test$
declare v_retry jsonb;v_pool uuid;v_original_version bigint;
begin
  select id into v_pool from cp3_test_state where key='aug_pool';
  select value_bigint into v_original_version from cp3_test_state where key='aug_pool';
  v_retry:=erp.post_attendance_hpp_pool_v1(v_pool,'CP3 post August','26140000-0000-4000-8000-000000000502',v_original_version);
  if v_retry->>'status' is distinct from 'POSTED' then raise exception 'Idempotent retry did not return cached POSTED response'; end if;
end;
$test$;

do $test$
declare v_pool uuid;v_journal uuid;v_failed boolean:=false;
begin
  select id into v_pool from cp3_test_state where key='aug_pool';
  select allocation_journal_entry_id into v_journal from erp.attendance_hpp_pools where id=v_pool;
  if (select count(*) from erp.attendance_hpp_journal_credit_map where pool_id=v_pool)<>2 then raise exception 'Credit map cardinality mismatch'; end if;
  if (select amount from erp.attendance_hpp_journal_credit_map m join erp.attendance_hpp_pool_sources s using(pool_id,source_journal_line_id) where m.pool_id=v_pool and s.contractor_id='26140000-0000-4000-8000-000000000011') is distinct from 1000 then raise exception 'N1 terminal credit did not preserve original source-line share'; end if;
  if (select source_line_debit_snapshot from erp.attendance_hpp_pool_sources where pool_id=v_pool and contractor_id='26140000-0000-4000-8000-000000000011') is distinct from 1200 then raise exception 'N1 original debit snapshot not preserved'; end if;
  if (select sum(debit) from erp.journal_lines where journal_entry_id=v_journal and account_id=erp.account_id('WIP')) is distinct from 1500 then raise exception 'WIP debit mismatch'; end if;
  if (select sum(credit) from erp.journal_lines where journal_entry_id=v_journal and account_id=erp.account_id('LABOR_COST')) is distinct from 1500 then raise exception 'LABOR_COST credit mismatch'; end if;
  if (select count(*) from erp.journal_entries where source_type='ATTENDANCE_HPP_ALLOCATION' and source_id=v_pool and status='POSTED')<>1 then raise exception 'Duplicate/missing HPP allocation journal'; end if;
  begin
    perform erp.post_attendance_hpp_pool_v1(v_pool,'different payload','26140000-0000-4000-8000-000000000502',(select value_bigint from cp3_test_state where key='aug_pool'));
  exception when others then v_failed:=true; end;
  if not v_failed then raise exception 'Same idempotency key/different payload was not rejected'; end if;
end;
$test$;

-- Positive source with zero denominator must hard-block; no QC GOOD fallback exists.
insert into erp.attendance_periods(id,period_number,contractor_id,period_start,period_end,pay_date,status,posting_reason)
values ('26140000-0000-4000-8000-000000000601','CP3-ATT-N1-JUL','26140000-0000-4000-8000-000000000011','2026-07-01','2026-07-31','2026-07-31','POSTED','CP3 fixture');
insert into erp.attendance_records(id,contractor_id,worker_id,attendance_date,status,paid_fraction,attendance_period_id,record_lifecycle,change_reason)
values ('26140000-0000-4000-8000-000000000602','26140000-0000-4000-8000-000000000011',:'cp3_worker_n1'::uuid,'2026-07-10','PRESENT',1,'26140000-0000-4000-8000-000000000601','POSTED','CP3 fixture');
insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,status,payment_date)
values ('26140000-0000-4000-8000-000000000603','CP3-PAY-N1-JUL','26140000-0000-4000-8000-000000000011','2026-07-01','2026-07-31','DRAFT','2026-07-31');
insert into erp.payroll_attendance_items(payroll_id,worker_id,attendance_record_id,paid_fraction_snapshot,daily_rate_snapshot,worker_rate_version_id,attendance_date_snapshot,worker_name_snapshot,job_description_snapshot)
values ('26140000-0000-4000-8000-000000000603',:'cp3_worker_n1'::uuid,'26140000-0000-4000-8000-000000000602',1,1000,:'cp3_rate_n1'::uuid,'2026-07-10','Worker N1','Sewing');
update erp.payroll_settlements set attendance_total=1000,status='PAID',settled_at='2026-07-31' where id='26140000-0000-4000-8000-000000000603';
select erp.post_journal('PAYROLL_EXTRA_ACCRUAL','26140000-0000-4000-8000-000000000603','2026-07-31','CP3 July payroll accrual',jsonb_build_array(
 jsonb_build_object('mapping_key','LABOR_COST','debit',1000,'credit',0,'contractor_id','26140000-0000-4000-8000-000000000011','description','CP3 July labor'),
 jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',1000,'contractor_id','26140000-0000-4000-8000-000000000011','description','CP3 July payable')
));
do $test$
declare v_failed boolean:=false;
begin
  begin
    perform erp.create_attendance_hpp_pool_v1(jsonb_build_object('pool_number','CP3-HPP-JUL','period_start','2026-07-01','period_end','2026-07-31','reason','must hard block zero denominator'),'26140000-0000-4000-8000-000000000604');
  exception when others then v_failed:=true; end;
  if not v_failed then raise exception 'Positive pool with zero SELESAI_DIJAHIT denominator did not hard-block'; end if;
end;
$test$;

-- Atomic correction: old pool becomes CORRECTED and replacement becomes POSTED.
insert into cp3_test_state(key,id,value_bigint,value_text)
select 'aug_correction',(r->>'replacement_pool_id')::uuid,(r->>'replacement_row_version')::bigint,r::text
from (
 select erp.correct_attendance_hpp_pool_v1(
  (select id from cp3_test_state where key='aug_pool'),'CP3-HPP-AUG-C1','CP3 correction',
  '26140000-0000-4000-8000-000000000701',
  (select row_version from erp.attendance_hpp_pools where id=(select id from cp3_test_state where key='aug_pool'))
 ) r
) x;

do $test$
declare v_old uuid;v_new uuid;
begin
  select id into v_old from cp3_test_state where key='aug_pool';
  select id into v_new from cp3_test_state where key='aug_correction';
  if (select status from erp.attendance_hpp_pools where id=v_old) is distinct from 'CORRECTED'
     or (select status from erp.attendance_hpp_pools where id=v_new) is distinct from 'POSTED'
  then raise exception 'Atomic pool correction lifecycle mismatch'; end if;
  if (select count(*) from erp.journal_entries where source_type='ATTENDANCE_HPP_ALLOCATION' and status='POSTED')<>1 then raise exception 'Correction left more/less than one posted allocation'; end if;
end;
$test$;

select erp.reverse_attendance_hpp_pool_v1(
 (select id from cp3_test_state where key='aug_correction'),'CP3 reverse corrected replacement',
 '26140000-0000-4000-8000-000000000702',
 (select row_version from erp.attendance_hpp_pools where id=(select id from cp3_test_state where key='aug_correction'))
);

do $test$
begin
  if (select status from erp.attendance_hpp_pools where id=(select id from cp3_test_state where key='aug_correction')) is distinct from 'REVERSED' then raise exception 'Pool reversal lifecycle mismatch'; end if;
  if exists(select 1 from erp.journal_entries where source_type='ATTENDANCE_HPP_ALLOCATION' and status='POSTED') then raise exception 'Pool reversal left posted allocation journal residue'; end if;
end;
$test$;

-- With consuming pools terminal, sewing correction and reversal are permitted through owning RPCs.
insert into cp3_test_state(key,id,value_bigint,value_text)
select 'sew_correction',(r->>'replacement_event_id')::uuid,(r->>'replacement_row_version')::bigint,r::text
from (
 select erp.correct_sewing_terminal_v1(
  (select id from erp.sewing_terminal_events where event_number='CP3-SEW-N1'),
  jsonb_build_object('replacement_event_number','CP3-SEW-N1-C1','qty_pcs',60,'physical_at','2026-08-20T08:00:00+07:00','reason','CP3 correction'),
  '26140000-0000-4000-8000-000000000703',
  (select row_version from erp.sewing_terminal_events where event_number='CP3-SEW-N1')
 ) r
) x;
select erp.reverse_sewing_terminal_v1(
 (select id from cp3_test_state where key='sew_correction'),'CP3 reverse corrected sewing fact',
 '26140000-0000-4000-8000-000000000704',
 (select row_version from erp.sewing_terminal_events where id=(select id from cp3_test_state where key='sew_correction'))
);
do $test$
begin
  if (select status from erp.sewing_terminal_events where event_number='CP3-SEW-N1') is distinct from 'POSTED'
     or (select status from erp.sewing_terminal_events where id=(select id from cp3_test_state where key='sew_correction')) is distinct from 'REVERSED'
  then raise exception 'Correction reversal did not restore the original SELESAI_DIJAHIT fact'; end if;
end;
$test$;

-- October ACTIVE pool cancellation must work directly, without a manual pre-reversal.
insert into erp.attendance_periods(id,period_number,contractor_id,period_start,period_end,pay_date,status,posting_reason)
values ('26140000-0000-4000-8000-000000000801','CP3-ATT-N2-JUN','26140000-0000-4000-8000-000000000012','2026-06-01','2026-06-30','2026-06-30','POSTED','CP3 fixture');
insert into erp.attendance_records(id,contractor_id,worker_id,attendance_date,status,paid_fraction,attendance_period_id,record_lifecycle,change_reason)
values ('26140000-0000-4000-8000-000000000802','26140000-0000-4000-8000-000000000012',:'cp3_worker_n2'::uuid,'2026-06-10','PRESENT',1,'26140000-0000-4000-8000-000000000801','POSTED','CP3 fixture');
insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,status,payment_date)
values ('26140000-0000-4000-8000-000000000803','CP3-PAY-N2-JUN','26140000-0000-4000-8000-000000000012','2026-06-01','2026-06-30','DRAFT','2026-06-30');
insert into erp.payroll_attendance_items(payroll_id,worker_id,attendance_record_id,paid_fraction_snapshot,daily_rate_snapshot,worker_rate_version_id,attendance_date_snapshot,worker_name_snapshot,job_description_snapshot)
values ('26140000-0000-4000-8000-000000000803',:'cp3_worker_n2'::uuid,'26140000-0000-4000-8000-000000000802',1,500,:'cp3_rate_n2'::uuid,'2026-06-10','Worker N2','Sewing');
update erp.payroll_settlements set attendance_total=500,status='PAID',settled_at='2026-06-30' where id='26140000-0000-4000-8000-000000000803';
select erp.post_journal('PAYROLL_EXTRA_ACCRUAL','26140000-0000-4000-8000-000000000803','2026-06-30','CP3 June payroll accrual',jsonb_build_array(
 jsonb_build_object('mapping_key','LABOR_COST','debit',500,'credit',0,'contractor_id','26140000-0000-4000-8000-000000000012','description','CP3 June labor'),
 jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',500,'contractor_id','26140000-0000-4000-8000-000000000012','description','CP3 June payable')
));
insert into erp.production_orders(id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,physical_start_at)
values ('26140000-0000-4000-8000-000000000811','CP3-PO-JUN','26140000-0000-4000-8000-000000000001','26140000-0000-4000-8000-000000000012',10,'SEWING','SEWING','2026-06-01');
insert into erp.cutting_groups(id,po_id,group_number,cut_at,picked_up_at,status)
values ('26140000-0000-4000-8000-000000000812','26140000-0000-4000-8000-000000000811','CP3-G-JUN','2026-06-01','2026-06-02','PICKED_UP');
insert into erp.material_rolls(id,material_id,roll_number,original_qty,cached_qty,status,received_at)
values ('26140000-0000-4000-8000-000000000813','26140000-0000-4000-8000-000000000003','CP3-R-JUN',20,20,'AVAILABLE','2026-06-01');
insert into erp.cutting_group_rolls(id,cutting_group_id,roll_id,qty_issued,qty_consumed)
values ('26140000-0000-4000-8000-000000000814','26140000-0000-4000-8000-000000000812','26140000-0000-4000-8000-000000000813',10,10);
insert into erp.cutting_group_size_slots(id,cutting_group_id,slot_no,size_id)
values ('26140000-0000-4000-8000-000000000815','26140000-0000-4000-8000-000000000812',1,'26140000-0000-4000-8000-000000000002');
insert into erp.cutting_roll_yields(cutting_group_roll_id,size_slot_id,qty_pcs)
values ('26140000-0000-4000-8000-000000000814','26140000-0000-4000-8000-000000000815',10);
select erp.record_sewing_terminal_v1(jsonb_build_object('event_number','CP3-SEW-JUN','po_id','26140000-0000-4000-8000-000000000811','cutting_group_id','26140000-0000-4000-8000-000000000812','qty_pcs',10,'physical_at','2026-06-20T08:00:00+07:00','reason','CP3 June sewing'),'26140000-0000-4000-8000-000000000816');
insert into cp3_test_state(key,id,value_bigint)
select 'oct_pool',(r->>'pool_id')::uuid,(r->>'row_version')::bigint
from (select erp.create_attendance_hpp_pool_v1(jsonb_build_object('pool_number','CP3-HPP-JUN','period_start','2026-06-01','period_end','2026-06-30','reason','CP3 active cancellation'),'26140000-0000-4000-8000-000000000817') r) x;
do $test$
declare v_failed boolean:=false;
begin
  begin
    perform erp.create_attendance_hpp_pool_v1(
      jsonb_build_object('pool_number','CP3-HPP-OVERLAP','period_start','2026-06-15','period_end','2026-07-15','reason','must reject overlap'),
      '26140000-0000-4000-8000-000000000819'
    );
  exception when others then v_failed:=true; end;
  if not v_failed then raise exception 'Overlapping ACTIVE/POSTED pool range was not rejected'; end if;
end;
$test$;
select erp.cancel_attendance_hpp_pool_v1(
 (select id from cp3_test_state where key='oct_pool'),'CP3 cancel active directly',
 '26140000-0000-4000-8000-000000000818',
 (select value_bigint from cp3_test_state where key='oct_pool')
);

do $test$
declare v_pool uuid;
begin
  select id into v_pool from cp3_test_state where key='oct_pool';
  if (select status from erp.attendance_hpp_pools where id=v_pool) is distinct from 'CANCELLED' then raise exception 'ACTIVE pool cancel failed'; end if;
  if exists(select 1 from erp.journal_entries where source_type='ATTENDANCE_HPP_ALLOCATION' and source_id=v_pool) then raise exception 'Cancelled ACTIVE pool created financial residue'; end if;
end;
$test$;

-- Bounded integrity query must report zero current issues.
do $test$
declare v_issues bigint;
begin
  select coalesce(sum(issue_count),0) into v_issues from erp.run_v2614_attendance_hpp_integrity_checks();
  if v_issues<>0 then raise exception 'CP3 integrity suite found % issue(s)',v_issues; end if;
end;
$test$;

select '00_ALL_CHECKS_PASS' as check_name,true as pass;
select '00_EXECUTION_QUIESCENT' as check_name,
       not exists(select 1 from pg_stat_activity where application_name like 'CP3_HPP_%' and pid<>pg_backend_pid()) as pass;

rollback;
