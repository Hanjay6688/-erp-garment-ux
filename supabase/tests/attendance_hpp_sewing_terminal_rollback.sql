-- CP3 acceptance for v2.6.14a + v2.6.14b.
-- Prerequisite: disposable minimal/full baseline and both candidate migrations applied.
-- All business fixture rows are rolled back; schema candidate remains for subsequent tests.

\set ON_ERROR_STOP on

begin;
set local timezone='UTC';
set local lock_timeout='5s';
set local statement_timeout='60s';

select set_config('app.test_user_id','00000000-0000-0000-0000-000000000001',true);

insert into erp.app_users(id,display_name,role,is_active)
values('00000000-0000-0000-0000-000000000001','CP3 Owner','OWNER',true);

insert into erp.contractors(id,contractor_code,contractor_name,contractor_type,attendance_required)
values
 ('10000000-0000-0000-0000-000000000001','CP3-NORMAL-A','Normal A','MANDOR',true),
 ('10000000-0000-0000-0000-000000000002','CP3-NORMAL-B','Normal B','MANDOR',true),
 ('10000000-0000-0000-0000-000000000003','CP3-SPECIAL','Special Generic','MANDOR',true),
 ('10000000-0000-0000-0000-000000000004','CP3-EXEMPT','Attendance Exempt','MANDOR',false);

-- Explicit policy: Special and attendance-required are independent dimensions.
select erp.set_contractor_hpp_policy_v1(
  jsonb_build_object('contractor_id','10000000-0000-0000-0000-000000000001','effective_from','2026-01-01','is_special',false,'attendance_required',true,'reason','CP3 normal A'),
  '90000000-0000-0000-0000-000000000001',null
);
select erp.set_contractor_hpp_policy_v1(
  jsonb_build_object('contractor_id','10000000-0000-0000-0000-000000000002','effective_from','2026-01-01','is_special',false,'attendance_required',true,'reason','CP3 normal B'),
  '90000000-0000-0000-0000-000000000002',null
);
select erp.set_contractor_hpp_policy_v1(
  jsonb_build_object('contractor_id','10000000-0000-0000-0000-000000000003','effective_from','2026-01-01','is_special',true,'attendance_required',true,'reason','CP3 explicit special'),
  '90000000-0000-0000-0000-000000000003',null
);
select erp.set_contractor_hpp_policy_v1(
  jsonb_build_object('contractor_id','10000000-0000-0000-0000-000000000004','effective_from','2026-01-01','is_special',false,'attendance_required',false,'reason','CP3 attendance not required'),
  '90000000-0000-0000-0000-000000000004',null
);

insert into erp.production_orders(id,po_number,contractor_id,status)
values
 ('20000000-0000-0000-0000-000000000001','CP3-PO-A','10000000-0000-0000-0000-000000000001','IN_PROGRESS'),
 ('20000000-0000-0000-0000-000000000002','CP3-PO-B','10000000-0000-0000-0000-000000000002','IN_PROGRESS'),
 ('20000000-0000-0000-0000-000000000003','CP3-PO-S','10000000-0000-0000-0000-000000000003','IN_PROGRESS'),
 ('20000000-0000-0000-0000-000000000004','CP3-PO-E','10000000-0000-0000-0000-000000000004','IN_PROGRESS');

insert into erp.cutting_groups(id,po_id,total_pcs)
values
 ('30000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001',100),
 ('30000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000002',100),
 ('30000000-0000-0000-0000-000000000003','20000000-0000-0000-0000-000000000003',100),
 ('30000000-0000-0000-0000-000000000004','20000000-0000-0000-0000-000000000004',100);

insert into erp.work_components(id,component_name,component_category)
values('40000000-0000-0000-0000-000000000001','CP3 generic work component','SEWING');

insert into erp.po_work_component_snapshots(id,po_id,work_component_id,rate_per_pcs_snapshot)
values
 ('41000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','40000000-0000-0000-0000-000000000001',1),
 ('41000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000002','40000000-0000-0000-0000-000000000001',1),
 ('41000000-0000-0000-0000-000000000003','20000000-0000-0000-0000-000000000003','40000000-0000-0000-0000-000000000001',1),
 ('41000000-0000-0000-0000-000000000004','20000000-0000-0000-0000-000000000004','40000000-0000-0000-0000-000000000001',1);

insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,created_by)
values
 ('50000000-0000-0000-0000-000000000001','CP3-WC-A','20000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000001','2026-01-10 10:00:00+07','POSTED','00000000-0000-0000-0000-000000000001'),
 ('50000000-0000-0000-0000-000000000002','CP3-WC-B','20000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000002','30000000-0000-0000-0000-000000000002','2026-01-11 11:00:00+07','POSTED','00000000-0000-0000-0000-000000000001'),
 ('50000000-0000-0000-0000-000000000003','CP3-WC-S','20000000-0000-0000-0000-000000000003','10000000-0000-0000-0000-000000000003','30000000-0000-0000-0000-000000000003','2026-01-12 12:00:00+07','POSTED','00000000-0000-0000-0000-000000000001'),
 ('50000000-0000-0000-0000-000000000004','CP3-WC-E','20000000-0000-0000-0000-000000000004','10000000-0000-0000-0000-000000000004','30000000-0000-0000-0000-000000000004','2026-01-13 13:00:00+07','POSTED','00000000-0000-0000-0000-000000000001');

insert into erp.work_completion_lines(id,completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot)
values
 ('51000000-0000-0000-0000-000000000001','50000000-0000-0000-0000-000000000001','41000000-0000-0000-0000-000000000001','40000000-0000-0000-0000-000000000001',60,60,1),
 ('51000000-0000-0000-0000-000000000002','50000000-0000-0000-0000-000000000002','41000000-0000-0000-0000-000000000002','40000000-0000-0000-0000-000000000001',40,40,1),
 ('51000000-0000-0000-0000-000000000003','50000000-0000-0000-0000-000000000003','41000000-0000-0000-0000-000000000003','40000000-0000-0000-0000-000000000001',100,100,1),
 ('51000000-0000-0000-0000-000000000004','50000000-0000-0000-0000-000000000004','41000000-0000-0000-0000-000000000004','40000000-0000-0000-0000-000000000001',100,100,1);

create temp table cp3_results(key text primary key,value jsonb) on commit drop;

insert into cp3_results values('sew_a',erp.record_sewing_terminal_v1(
 jsonb_build_object('work_completion_id','50000000-0000-0000-0000-000000000001','qty_pcs',60,'reason','CP3 explicit terminal A'),
 '91000000-0000-0000-0000-000000000001'));
insert into cp3_results values('sew_b',erp.record_sewing_terminal_v1(
 jsonb_build_object('work_completion_id','50000000-0000-0000-0000-000000000002','qty_pcs',40,'reason','CP3 explicit terminal B'),
 '91000000-0000-0000-0000-000000000002'));
insert into cp3_results values('sew_special',erp.record_sewing_terminal_v1(
 jsonb_build_object('work_completion_id','50000000-0000-0000-0000-000000000003','qty_pcs',100,'reason','CP3 explicit terminal Special'),
 '91000000-0000-0000-0000-000000000003'));
insert into cp3_results values('sew_exempt',erp.record_sewing_terminal_v1(
 jsonb_build_object('work_completion_id','50000000-0000-0000-0000-000000000004','qty_pcs',100,'reason','CP3 explicit terminal exempt'),
 '91000000-0000-0000-0000-000000000004'));

-- Same idempotency key and same payload returns the same event.
do $test$
declare a uuid;b uuid;
begin
 a:=(select (value->>'sewing_terminal_event_id')::uuid from cp3_results where key='sew_a');
 b:=(erp.record_sewing_terminal_v1(
   jsonb_build_object('work_completion_id','50000000-0000-0000-0000-000000000001','qty_pcs',60,'reason','CP3 explicit terminal A'),
   '91000000-0000-0000-0000-000000000001')->>'sewing_terminal_event_id')::uuid;
 if a is distinct from b then raise exception 'same-key same-payload did not return cached event'; end if;
end;
$test$;

-- Same key with different payload must fail.
do $test$
begin
 begin
  perform erp.record_sewing_terminal_v1(
    jsonb_build_object('work_completion_id','50000000-0000-0000-0000-000000000001','qty_pcs',59,'reason','changed'),
    '91000000-0000-0000-0000-000000000001');
  raise exception 'expected idempotency payload mismatch';
 exception when others then
  if sqlerrm not like '%different payload%' then raise; end if;
 end;
end;
$test$;

insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,status,attendance_total)
values
 ('60000000-0000-0000-0000-000000000001','CP3-PAY-A','10000000-0000-0000-0000-000000000001','2026-01-01','2026-01-15','PAID',100),
 ('60000000-0000-0000-0000-000000000002','CP3-PAY-B','10000000-0000-0000-0000-000000000002','2026-01-01','2026-01-15','PAID',50),
 ('60000000-0000-0000-0000-000000000003','CP3-PAY-S','10000000-0000-0000-0000-000000000003','2026-01-01','2026-01-15','PAID',999),
 ('60000000-0000-0000-0000-000000000004','CP3-PAY-E','10000000-0000-0000-0000-000000000004','2026-01-01','2026-01-15','PAID',777);

insert into erp.payroll_attendance_items(id,payroll_id,worker_id,attendance_record_id,paid_fraction_snapshot,daily_rate_snapshot)
values
 ('61000000-0000-0000-0000-000000000001','60000000-0000-0000-0000-000000000001',gen_random_uuid(),gen_random_uuid(),1,100),
 ('61000000-0000-0000-0000-000000000002','60000000-0000-0000-0000-000000000002',gen_random_uuid(),gen_random_uuid(),1,50),
 ('61000000-0000-0000-0000-000000000003','60000000-0000-0000-0000-000000000003',gen_random_uuid(),gen_random_uuid(),1,999),
 ('61000000-0000-0000-0000-000000000004','60000000-0000-0000-0000-000000000004',gen_random_uuid(),gen_random_uuid(),1,777);

select erp.post_journal('PAYROLL_EXTRA_ACCRUAL','60000000-0000-0000-0000-000000000001','2026-01-15','CP3 payroll A',jsonb_build_array(
 jsonb_build_object('mapping_key','LABOR_COST','debit',100,'credit',0,'contractor_id','10000000-0000-0000-0000-000000000001'),
 jsonb_build_object('mapping_key','WIP','debit',0,'credit',100,'contractor_id','10000000-0000-0000-0000-000000000001')));
select erp.post_journal('PAYROLL_EXTRA_ACCRUAL','60000000-0000-0000-0000-000000000002','2026-01-15','CP3 payroll B',jsonb_build_array(
 jsonb_build_object('mapping_key','LABOR_COST','debit',50,'credit',0,'contractor_id','10000000-0000-0000-0000-000000000002'),
 jsonb_build_object('mapping_key','WIP','debit',0,'credit',50,'contractor_id','10000000-0000-0000-0000-000000000002')));
select erp.post_journal('PAYROLL_EXTRA_ACCRUAL','60000000-0000-0000-0000-000000000003','2026-01-15','CP3 payroll Special',jsonb_build_array(
 jsonb_build_object('mapping_key','LABOR_COST','debit',999,'credit',0,'contractor_id','10000000-0000-0000-0000-000000000003'),
 jsonb_build_object('mapping_key','WIP','debit',0,'credit',999,'contractor_id','10000000-0000-0000-0000-000000000003')));
select erp.post_journal('PAYROLL_EXTRA_ACCRUAL','60000000-0000-0000-0000-000000000004','2026-01-15','CP3 payroll exempt',jsonb_build_array(
 jsonb_build_object('mapping_key','LABOR_COST','debit',777,'credit',0,'contractor_id','10000000-0000-0000-0000-000000000004'),
 jsonb_build_object('mapping_key','WIP','debit',0,'credit',777,'contractor_id','10000000-0000-0000-0000-000000000004')));

-- Manifest/hash must be timezone independent.
do $test$
declare h_utc text;h_jakarta text;m jsonb;summary jsonb;
begin
 set local timezone='UTC';
 m:=erp._build_attendance_hpp_manifest_v1('2026-01-01','2026-01-15');
 h_utc:=erp._cp3_manifest_sha256(m);
 perform erp._assert_attendance_hpp_manifest_v1(m);
 if (m->>'numerator_cents')::bigint<>15000 or (m->>'denominator_qty')::bigint<>100 then
  raise exception 'eligible numerator/denominator mismatch: %',m;
 end if;
 set local timezone='Asia/Jakarta';
 h_jakarta:=erp._cp3_manifest_sha256(erp._build_attendance_hpp_manifest_v1('2026-01-01','2026-01-15'));
 if h_utc is distinct from h_jakarta then raise exception 'manifest hash changed across timezone'; end if;
 summary:=erp.attendance_hpp_exclusion_summary_v1('2026-01-01','2026-01-15');
 if jsonb_array_length(summary->'excluded_payrolls')<>2
    or jsonb_array_length(summary->'excluded_sewing_events')<>2 then
  raise exception 'Special/exempt exclusion summary mismatch: %',summary;
 end if;
end;
$test$;

-- Closed JSON contract: wrong discriminator, extra key, missing/null/type all fail.
do $test$
declare m jsonb;
begin
 m:=erp._build_attendance_hpp_manifest_v1('2026-01-01','2026-01-15');
 begin perform erp._assert_attendance_hpp_manifest_v1(m||jsonb_build_object('operation_type','LAUNDRY_CLAIM')); raise exception 'expected wrong discriminator';
 exception when others then if sqlerrm not like '%discriminator%' then raise; end if; end;
 begin perform erp._assert_attendance_hpp_manifest_v1(m||jsonb_build_object('transfer',jsonb_build_object())); raise exception 'expected extra key';
 exception when others then if sqlerrm not like '%unexpected key%' then raise; end if; end;
 begin perform erp._assert_attendance_hpp_manifest_v1(m-'numerator_cents'); raise exception 'expected missing key';
 exception when others then if sqlerrm not like '%requires non-null key%' then raise; end if; end;
 begin perform erp._assert_attendance_hpp_manifest_v1(jsonb_set(m,'{numerator_cents}','null'::jsonb)); raise exception 'expected null key';
 exception when others then if sqlerrm not like '%requires non-null key%' then raise; end if; end;
 begin perform erp._assert_attendance_hpp_manifest_v1(jsonb_set(m,'{denominator_qty}','"100"'::jsonb)); raise exception 'expected wrong type';
 exception when others then if sqlerrm not like '%invalid top-level types%' then raise; end if; end;
end;
$test$;

insert into cp3_results values('pool',erp.create_attendance_hpp_pool_v1(
 jsonb_build_object('period_start','2026-01-01','period_end','2026-01-15','reason','CP3 initial pool'),
 '92000000-0000-0000-0000-000000000001'));

-- Exact deterministic cents: source 100 -> 60/40; source 50 -> 30/20.
do $test$
declare p uuid;
begin
 p:=(select (value->>'pool_id')::uuid from cp3_results where key='pool');
 if (select numerator_amount from erp.attendance_hpp_pools where id=p)<>150
    or (select denominator_qty from erp.attendance_hpp_pools where id=p)<>100 then
  raise exception 'pool basis mismatch';
 end if;
 if (select round(sum(allocated_amount),2) from erp.attendance_hpp_pool_allocations where pool_id=p and po_id='20000000-0000-0000-0000-000000000001')<>90
    or (select round(sum(allocated_amount),2) from erp.attendance_hpp_pool_allocations where pool_id=p and po_id='20000000-0000-0000-0000-000000000002')<>60 then
  raise exception 'destination allocation mismatch';
 end if;
 perform erp.validate_attendance_hpp_pool_v1(p);
end;
$test$;

insert into cp3_results values('active',erp.activate_attendance_hpp_pool_v1(
 (select (value->>'pool_id')::uuid from cp3_results where key='pool'),
 'CP3 activate from DRAFT',
 '92000000-0000-0000-0000-000000000002',1));

-- Journal must have one source credit link per exact original payroll debit line.
do $test$
declare p uuid;j uuid;
begin
 p:=(select (value->>'pool_id')::uuid from cp3_results where key='pool');
 j:=(select post_journal_entry_id from erp.attendance_hpp_pools where id=p);
 if (select round(sum(debit),2) from erp.journal_lines where journal_entry_id=j)<>150
    or (select round(sum(credit),2) from erp.journal_lines where journal_entry_id=j)<>150 then
  raise exception 'activation journal does not balance to pool';
 end if;
 if (select count(*) from erp.attendance_hpp_journal_line_links where pool_id=p and link_type='SOURCE_CREDIT')<>2 then
  raise exception 'source credit cardinality is not per original debit line';
 end if;
 if exists(
  select 1 from erp.attendance_hpp_pool_sources s
  left join erp.attendance_hpp_journal_line_links l
    on l.pool_source_id=s.id and l.original_debit_journal_line_id=s.original_debit_journal_line_id
  where s.pool_id=p and l.id is null
 ) then raise exception 'original debit-line lineage missing'; end if;
 perform erp.validate_attendance_hpp_pool_v1(p);
end;
$test$;

insert into cp3_results values('cancel',erp.cancel_attendance_hpp_pool_v1(
 (select (value->>'pool_id')::uuid from cp3_results where key='pool'),
 'CP3 cancel ACTIVE atomically',
 '92000000-0000-0000-0000-000000000003',2));

-- Retry same cancel is cached; changed payload with same key is rejected.
do $test$
declare p uuid;a jsonb;b jsonb;
begin
 p:=(select (value->>'pool_id')::uuid from cp3_results where key='pool');
 a:=(select value from cp3_results where key='cancel');
 b:=erp.cancel_attendance_hpp_pool_v1(p,'CP3 cancel ACTIVE atomically','92000000-0000-0000-0000-000000000003',2);
 if a is distinct from b then raise exception 'cancel retry did not return cached terminal result'; end if;
 begin perform erp.cancel_attendance_hpp_pool_v1(p,'different reason','92000000-0000-0000-0000-000000000003',2); raise exception 'expected cancel request hash mismatch';
 exception when others then if sqlerrm not like '%different payload%' then raise; end if; end;
 if (select status from erp.attendance_hpp_pools where id=p)<>'CANCELLED' then raise exception 'pool not cancelled'; end if;
 if not exists(select 1 from erp.journal_entries where reversal_of_id=(select post_journal_entry_id from erp.attendance_hpp_pools where id=p) and status='POSTED') then
  raise exception 'active-pool cancellation did not own journal reversal';
 end if;
end;
$test$;

-- One correction successor, same period, then activate and cancel.
insert into cp3_results values('correction',erp.create_attendance_hpp_pool_v1(
 jsonb_build_object(
  'period_start','2026-01-01','period_end','2026-01-15','reason','CP3 replacement',
  'correction_of_pool_id',(select value->>'pool_id' from cp3_results where key='pool')
 ),
 '92000000-0000-0000-0000-000000000004'));

insert into cp3_results values('correction_active',erp.activate_attendance_hpp_pool_v1(
 (select (value->>'pool_id')::uuid from cp3_results where key='correction'),
 'CP3 activate correction','92000000-0000-0000-0000-000000000005',1));

select erp.cancel_attendance_hpp_pool_v1(
 (select (value->>'pool_id')::uuid from cp3_results where key='correction'),
 'CP3 cancel correction','92000000-0000-0000-0000-000000000006',2);

-- Positive attendance pool with no SELESAI_DIJAHIT in exact period must hard-block.
insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,status,attendance_total)
values('60000000-0000-0000-0000-000000000005','CP3-PAY-ZERO-DEN','10000000-0000-0000-0000-000000000001','2026-01-16','2026-01-31','PAID',25);
insert into erp.payroll_attendance_items(id,payroll_id,worker_id,attendance_record_id,paid_fraction_snapshot,daily_rate_snapshot)
values('61000000-0000-0000-0000-000000000005','60000000-0000-0000-0000-000000000005',gen_random_uuid(),gen_random_uuid(),1,25);
select erp.post_journal('PAYROLL_EXTRA_ACCRUAL','60000000-0000-0000-0000-000000000005','2026-01-31','CP3 zero denominator payroll',jsonb_build_array(
 jsonb_build_object('mapping_key','LABOR_COST','debit',25,'credit',0,'contractor_id','10000000-0000-0000-0000-000000000001'),
 jsonb_build_object('mapping_key','WIP','debit',0,'credit',25,'contractor_id','10000000-0000-0000-0000-000000000001')));

do $test$
begin
 begin perform erp.preview_attendance_hpp_pool_v1('2026-01-16','2026-01-31'); raise exception 'expected zero denominator hard block';
 exception when others then if sqlerrm not like '%POSITIVE_POOL_ZERO_SEWING_OUTPUT%' then raise; end if; end;
end;
$test$;

-- Direct browser/service route remains closed and no deferred validator exists.
do $test$
begin
 if has_table_privilege('authenticated','erp.attendance_hpp_pools','SELECT')
    or has_table_privilege('authenticated','erp.attendance_hpp_pools','INSERT')
    or has_table_privilege('service_role','erp.attendance_hpp_pools','SELECT') then
  raise exception 'CP3 private foundation leaked table privilege';
 end if;
 if has_function_privilege('authenticated','erp.activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint)','EXECUTE')
    or has_function_privilege('service_role','erp.activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint)','EXECUTE') then
  raise exception 'CP3 activation leaked execute privilege';
 end if;
 if exists(
  select 1 from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relname in(
   'contractor_hpp_policy_versions','sewing_terminal_events','attendance_hpp_pools',
   'attendance_hpp_pool_sources','attendance_hpp_pool_allocations','attendance_hpp_journal_line_links'
  ) and not t.tgisinternal
 ) then raise exception 'CP3 candidate unexpectedly added row/deferred triggers'; end if;
end;
$test$;

-- Once all active pools are cancelled, terminal reversal is allowed and append-only.
insert into cp3_results values('sew_a_reversal',erp.reverse_sewing_terminal_v1(
 (select (value->>'sewing_terminal_event_id')::uuid from cp3_results where key='sew_a'),
 'CP3 terminal correction','93000000-0000-0000-0000-000000000001',1));

do $test$
declare original_id uuid;
begin
 original_id:=(select (value->>'sewing_terminal_event_id')::uuid from cp3_results where key='sew_a');
 if (select count(*) from erp.sewing_terminal_events where reversal_of_id=original_id)<>1 then
  raise exception 'terminal event reversal lineage missing';
 end if;
 if (select qty_signed from erp.sewing_terminal_events where reversal_of_id=original_id)<>-60 then
  raise exception 'terminal reversal quantity mismatch';
 end if;
end;
$test$;

rollback;

-- Fixture residue must be zero after outer rollback.
do $residue$
begin
 if exists(select 1 from erp.contractors where contractor_code like 'CP3-%')
    or exists(select 1 from erp.attendance_hpp_pools)
    or exists(select 1 from erp.sewing_terminal_events)
    or exists(select 1 from erp.contractor_hpp_policy_versions)
    or exists(select 1 from erp.idempotency_requests where operation_name like '%hpp%' or operation_name like '%sewing_terminal%') then
  raise exception 'CP3 rollback fixture left synthetic residue';
 end if;
end;
$residue$;

select jsonb_build_object(
 'status','PASS',
 'contract','SELESAI_DIJAHIT_NOT_QC_GOOD',
 'timezone_determinism',true,
 'special_independent',true,
 'active_cancel_owned_reversal',true,
 'source_credit_per_original_debit_line',true,
 'closed_json_contract',true,
 'fixture_residue',0
) as cp3_acceptance_result;
