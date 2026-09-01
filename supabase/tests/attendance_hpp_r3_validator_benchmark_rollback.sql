-- CP3 R3 bounded validator benchmark on the restored ERP Enteng schema.
\set ON_ERROR_STOP on
begin;
set local timezone='UTC';
set local statement_timeout='90s';

insert into erp.contractors(id,contractor_code,contractor_name,contractor_type,attendance_required)
values('b1000000-0000-0000-0000-000000000001','CP3R3-BENCH','CP3 R3 benchmark Mandor','MANDOR',true);
select erp.set_contractor_hpp_policy_v1(jsonb_build_object(
 'contractor_id','b1000000-0000-0000-0000-000000000001','effective_from','2026-03-01',
 'is_special',false,'attendance_required',true,'reason','CP3 R3 benchmark'),gen_random_uuid(),null);

insert into erp.product_models(id,model_code,model_name)
values('b2000000-0000-0000-0000-000000000001','CP3R3-BENCH-M','CP3 R3 benchmark model');
insert into erp.production_orders(id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage)
values('b3000000-0000-0000-0000-000000000001','CP3R3-BENCH-PO','b2000000-0000-0000-0000-000000000001','b1000000-0000-0000-0000-000000000001',2000,'SEWING','SEWING');
insert into erp.cutting_groups(id,po_id,group_number,cut_at,picked_up_at,status)
values('b4000000-0000-0000-0000-000000000001','b3000000-0000-0000-0000-000000000001','CP3R3-BENCH-G','2026-03-01 08:00+07','2026-03-01 09:00+07','SEWING');

insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status)
select ('b5'||lpad(g::text,30,'0'))::uuid,'CP3R3-BENCH-WC-'||g,
 'b3000000-0000-0000-0000-000000000001','b1000000-0000-0000-0000-000000000001',
 'b4000000-0000-0000-0000-000000000001','2026-03-10 00:00:00+07'::timestamptz+g*interval '1 microsecond','POSTED'
from generate_series(1,2000) g;
insert into erp.sewing_terminal_events(
 id,event_number,event_kind,source_work_completion_id,contractor_id,po_id,cutting_group_id,physical_at,qty_signed,reason
)
select ('b6'||lpad(g::text,30,'0'))::uuid,'CP3R3-BENCH-SEW-'||g,'SELESAI_DIJAHIT',
 ('b5'||lpad(g::text,30,'0'))::uuid,'b1000000-0000-0000-0000-000000000001',
 'b3000000-0000-0000-0000-000000000001','b4000000-0000-0000-0000-000000000001',
 '2026-03-10 00:00:00+07'::timestamptz+g*interval '1 microsecond',1,'CP3 R3 benchmark'
from generate_series(1,2000) g;

insert into erp.contractor_workers(id,contractor_id,worker_code,worker_name,pay_scheme,daily_rate,is_active,joined_at,job_description)
values('b7000000-0000-0000-0000-000000000001','b1000000-0000-0000-0000-000000000001','CP3R3-BENCH-W','Benchmark worker','DAILY',100,true,'2026-03-01','Jahit');
insert into erp.attendance_records(id,contractor_id,worker_id,attendance_date,status,paid_fraction)
values('b7100000-0000-0000-0000-000000000001','b1000000-0000-0000-0000-000000000001','b7000000-0000-0000-0000-000000000001','2026-03-10','PRESENT',1);
insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,status,attendance_total)
values('b7200000-0000-0000-0000-000000000001','CP3R3-BENCH-PAY','b1000000-0000-0000-0000-000000000001','2026-03-01','2026-03-15','APPROVED',100);
insert into erp.payroll_attendance_items(id,payroll_id,worker_id,attendance_record_id,paid_fraction_snapshot,daily_rate_snapshot)
values('b7300000-0000-0000-0000-000000000001','b7200000-0000-0000-0000-000000000001','b7000000-0000-0000-0000-000000000001','b7100000-0000-0000-0000-000000000001',1,100);
select erp.post_journal('PAYROLL_ATTENDANCE_ACCRUAL','b7200000-0000-0000-0000-000000000001','2026-03-15','CP3 R3 benchmark approval',jsonb_build_array(
 jsonb_build_object('mapping_key','WIP','debit',100,'credit',0,'contractor_id','b1000000-0000-0000-0000-000000000001'),
 jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',100,'contractor_id','b1000000-0000-0000-0000-000000000001')));

create temp table cp3_r3_benchmark_pool as
select erp.create_attendance_hpp_pool_v1(jsonb_build_object(
 'period_start','2026-03-01','period_end','2026-03-15','reason','CP3 R3 2000 destination benchmark'),gen_random_uuid()) result;

explain(analyze,buffers,format json)
select erp.validate_attendance_hpp_pool_v1((select (result->>'pool_id')::uuid from cp3_r3_benchmark_pool));

do $assert$
declare p uuid:=(select (result->>'pool_id')::uuid from cp3_r3_benchmark_pool);
begin
 if (select count(*) from erp.attendance_hpp_pool_allocations where pool_id=p)<>2000 then
  raise exception 'CP3 R3 benchmark allocation cardinality mismatch';
 end if;
 if (erp.validate_attendance_hpp_pool_v1(p)->>'validation') is distinct from 'PASS' then
  raise exception 'CP3 R3 bounded validator did not return PASS';
 end if;
 if exists(
  select 1 from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relname like 'attendance_hpp_%' and not t.tgisinternal
 ) then raise exception 'CP3 R3 benchmark found deferred/row triggers on pool objects'; end if;
end
$assert$;
rollback;

select jsonb_build_object('status','PASS','destinations',2000,'validator_calls',2,'pool_row_triggers',0,'residue',0)
as cp3_r3_validator_benchmark_result;
