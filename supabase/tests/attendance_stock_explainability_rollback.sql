-- Transactional acceptance for ERP Garment v2.6.12.
-- PT001 deliberately rolls back every synthetic business row.
-- Run only after 20260830125344_erp_v2_6_12_attendance_and_stock_explainability.sql.

create or replace function pg_temp.run_attendance_stock_explainability_test()
returns jsonb
language plpgsql
as $test$
declare
  v_normal_contractor uuid := gen_random_uuid();
  v_special_contractor uuid := gen_random_uuid();
  v_worker uuid;
  v_worker_create jsonb;
  v_worker_edit jsonb;
  v_worker_deactivated jsonb;
  v_worker_reactivated jsonb;
  v_rate_change jsonb;
  v_rate_change_replay jsonb;
  v_rate_request_id uuid := gen_random_uuid();
  v_rate_after_payroll jsonb;
  v_period jsonb;
  v_period_incomplete jsonb;
  v_normalized_preview jsonb;
  v_posted jsonb;
  v_correction jsonb;
  v_correction_posted jsonb;
  v_correction_lines jsonb;
  v_fake_supersedes uuid;
  v_reversed jsonb;
  v_payroll uuid := gen_random_uuid();
  v_corrected_payroll uuid := gen_random_uuid();
  v_restored_payroll uuid := gen_random_uuid();
  v_special_payroll uuid := gen_random_uuid();
  v_brand uuid := gen_random_uuid();
  v_model uuid := gen_random_uuid();
  v_size uuid := gen_random_uuid();
  v_product uuid := gen_random_uuid();
  v_location uuid := gen_random_uuid();
  v_lot uuid := gen_random_uuid();
  v_lot_grade_b uuid := gen_random_uuid();
  v_source uuid := gen_random_uuid();
  v_policy jsonb;
  v_policy_2 jsonb;
  v_explain jsonb;
  v_snapshot uuid := gen_random_uuid();
  v_before_start_blocked boolean := false;
  v_after_stop_blocked boolean := false;
  v_initial_rate_gap_blocked boolean := false;
  v_rate_resolver_fail_closed boolean := false;
  v_incomplete_post_blocked boolean := false;
  v_draft_snapshot_delete_verified boolean := false;
  v_bad_correction_lineage_blocked boolean := false;
  v_noncorrection_lineage_blocked boolean := false;
  v_backdated_roster_blocked boolean := false;
  v_duplicate_payload_blocked boolean := false;
  v_duplicate_posted_blocked boolean := false;
  v_posted_edit_blocked boolean := false;
  v_overlap_rate_blocked boolean := false;
  v_attendance_reverse_while_payroll_active_blocked boolean := false;
  v_fake_system_policy_blocked boolean := false;
  v_bad_stock_equation_blocked boolean := false;
  v_snapshot_mutation_blocked boolean := false;
  v_nonactive_default_count integer;
  v_rate_count integer;
  v_rate_version_count integer;
  v_snapshot_total numeric;
  v_snapshot_total_after numeric;
  v_corrected_payroll_total numeric;
  v_restored_payroll_total numeric;
  v_corrected_payroll_count integer;
  v_restored_payroll_count integer;
  v_snapshot_names text[];
  v_restored_source_count integer;
  v_position record;
  v_old_policy record;
  v_result jsonb;
begin
  begin
    insert into erp.contractors(
      id, contractor_code, contractor_name, contractor_type, attendance_required
    ) values
      (v_normal_contractor, 'TST-ATT-NORMAL', 'Test Attendance Mandor', 'MANDOR', true),
      (v_special_contractor, 'TST-ATT-SPECIAL', 'Test Attendance Exempt', 'MANDOR', false);

    begin
      perform erp.save_worker_roster_v1(
        jsonb_build_object(
          'contractor_id', v_normal_contractor,
          'worker_code', 'TST-W-RATE-GAP',
          'worker_name', 'Rate Gap Must Fail',
          'job_description', 'Jahit',
          'pay_scheme', 'DAILY',
          'initial_daily_rate', 100,
          'rate_effective_from', '2026-08-07',
          'joined_at', '2026-08-05',
          'is_active', true,
          'reason', 'Rollback test uncovered initial rate'
        ),
        gen_random_uuid(),
        null
      );
    exception when others then
      if sqlerrm like 'Initial daily rate must cover the worker start date%' then
        v_initial_rate_gap_blocked := true;
      else
        raise;
      end if;
    end;

    v_worker_create := erp.save_worker_roster_v1(
      jsonb_build_object(
        'contractor_id', v_normal_contractor,
        'worker_code', 'TST-W-001',
        'worker_name', 'Nama Awal',
        'job_description', 'Jahit',
        'pay_scheme', 'DAILY',
        'initial_daily_rate', 100,
        'rate_effective_from', '2026-08-05',
        'joined_at', '2026-08-05',
        'is_active', true,
        'notes', 'Catatan roster harus round-trip',
        'reason', 'Rollback test create worker'
      ),
      gen_random_uuid(),
      null
    );
    v_worker := (v_worker_create->>'worker_id')::uuid;

    begin
      perform erp.require_worker_daily_rate_at(v_worker, date '2026-08-04');
    exception when others then
      if sqlerrm like 'Worker % has no daily-rate version covering 2026-08-04%' then
        v_rate_resolver_fail_closed := true;
      else
        raise;
      end if;
    end;

    v_rate_change := erp.set_worker_daily_rate_v1(
      v_worker, 120, date '2026-08-07', 'Rollback test mid-period rate',
      v_rate_request_id, (v_worker_create->>'row_version')::bigint
    );

    v_rate_change_replay := erp.set_worker_daily_rate_v1(
      v_worker, 120, date '2026-08-07', 'Rollback test mid-period rate',
      v_rate_request_id, (v_worker_create->>'row_version')::bigint
    );
    select count(*) into v_rate_version_count
    from erp.worker_daily_rate_versions r
    where r.worker_id = v_worker;
    if v_rate_change_replay is distinct from v_rate_change
       or v_rate_version_count is distinct from 2 then
      raise exception 'Worker rate idempotency replay changed the response or duplicated a version';
    end if;

    if erp.worker_daily_rate_at(v_worker, date '2026-08-06') is distinct from 100
       or erp.worker_daily_rate_at(v_worker, date '2026-08-07') is distinct from 120 then
      raise exception 'Effective-dated worker rate resolver returned the wrong version';
    end if;

    begin
      perform set_config('app.worker_rate_write', 'on', true);
      insert into erp.worker_daily_rate_versions(
        worker_id, daily_rate, effective_from, effective_to, change_reason
      ) values (
        v_worker, 999, date '2026-08-06', date '2026-08-08', 'Forbidden overlap test'
      );
    exception when others then
      if sqlerrm like 'Worker daily-rate periods cannot overlap%' then
        v_overlap_rate_blocked := true;
      else
        raise;
      end if;
    end;
    perform set_config('app.worker_rate_write', 'off', true);

    v_worker_edit := erp.save_worker_roster_v1(
      jsonb_build_object(
        'worker_id', v_worker,
        'contractor_id', v_normal_contractor,
        'worker_code', 'TST-W-001',
        'worker_name', 'Nama Baru',
        'job_description', 'Jahit Senior',
        'pay_scheme', 'DAILY',
        'joined_at', '2026-08-05',
        'is_active', true,
        'notes', 'Catatan roster harus round-trip',
        'reason', 'Rollback test rename without identity change'
      ),
      gen_random_uuid(),
      (v_rate_change->>'row_version')::bigint
    );

    begin
      insert into erp.attendance_records(
        contractor_id, worker_id, attendance_date, status, paid_fraction
      ) values (
        v_normal_contractor, v_worker, date '2026-08-04', 'PRESENT', 1
      );
    exception when others then
      if sqlerrm like 'Attendance date is outside the worker employment periods%'
         or sqlerrm like 'Attendance date is before the worker start date%' then
        v_before_start_blocked := true;
      else
        raise;
      end if;
    end;

    begin
      perform erp.save_attendance_period_v1(
        jsonb_build_object(
          'contractor_id', v_normal_contractor,
          'period_number', 'TST-ATT-DUP-PAYLOAD',
          'period_start', '2026-08-03',
          'period_end', '2026-08-09',
          'pay_date', '2026-08-10',
          'reason', 'Rollback duplicate payload test',
          'attendance', jsonb_build_array(
            jsonb_build_object('worker_id', v_worker, 'attendance_date', '2026-08-05', 'status', 'PRESENT'),
            jsonb_build_object('worker_id', v_worker, 'attendance_date', '2026-08-05', 'status', 'PRESENT')
          )
        ), gen_random_uuid(), null, true
      );
    exception when others then
      if sqlerrm like 'Duplicate worker/date exists in attendance payload%' then
        v_duplicate_payload_blocked := true;
      else
        raise;
      end if;
    end;

    v_normalized_preview := erp.save_attendance_period_v1(
      jsonb_build_object(
        'contractor_id', v_normal_contractor,
        'period_number', 'TST-ATT-NORMALIZED-PREVIEW',
        'period_start', '2026-08-03',
        'period_end', '2026-08-09',
        'pay_date', '2026-08-10',
        'reason', 'Rollback fraction normalization preview',
        'attendance', jsonb_build_array(
          jsonb_build_object(
            'worker_id', v_worker,
            'attendance_date', '2026-08-06',
            'status', 'HALF_DAY'
          ),
          jsonb_build_object(
            'worker_id', v_worker,
            'attendance_date', '2026-08-07',
            'status', 'ABSENT',
            'paid_fraction', 1
          )
        )
      ),
      gen_random_uuid(), null, true
    );
    if (v_normalized_preview->>'paid_day_equivalent')::numeric is distinct from 0.5
       or (v_normalized_preview->>'estimated_amount')::numeric is distinct from 50 then
      raise exception 'Attendance preview did not normalize HALF_DAY/ABSENT fractions: %',
        v_normalized_preview;
    end if;

    v_period := erp.save_attendance_period_v1(
      jsonb_build_object(
        'contractor_id', v_normal_contractor,
        'period_number', 'TST-ATT-20260803',
        'period_start', '2026-08-03',
        'period_end', '2026-08-09',
        'pay_date', '2026-08-10',
        'reason', 'Rollback test attendance week',
        'attendance', jsonb_build_array(
          jsonb_build_object('worker_id', v_worker, 'attendance_date', '2026-08-05', 'status', 'PRESENT'),
          jsonb_build_object('worker_id', v_worker, 'attendance_date', '2026-08-06', 'status', 'PRESENT'),
          jsonb_build_object('worker_id', v_worker, 'attendance_date', '2026-08-07', 'status', 'PRESENT'),
          jsonb_build_object('worker_id', v_worker, 'attendance_date', '2026-08-08', 'status', 'OFF', 'paid_fraction', 1),
          jsonb_build_object('worker_id', v_worker, 'attendance_date', '2026-08-09', 'status', 'OFF')
        )
      ),
      gen_random_uuid(), null, false
    );

    if (v_period#>>'{preview,line_count}')::integer is distinct from 5
       or (v_period#>>'{preview,estimated_amount}')::numeric is distinct from 320 then
      raise exception 'Attendance bulk preview did not expose 5 explicit cells / 320 amount: %', v_period;
    end if;

    select a.id into v_fake_supersedes
    from erp.attendance_records a
    where a.attendance_period_id = (v_period->>'period_id')::uuid
    order by a.attendance_date
    limit 1;

    begin
      perform erp.save_attendance_period_v1(
        jsonb_build_object(
          'period_id', v_period->>'period_id',
          'contractor_id', v_normal_contractor,
          'period_number', 'TST-ATT-20260803',
          'period_start', '2026-08-03',
          'period_end', '2026-08-09',
          'pay_date', '2026-08-10',
          'reason', 'Rollback reject lineage on ordinary attendance',
          'attendance', jsonb_build_array(
            jsonb_build_object(
              'worker_id', v_worker,
              'attendance_date', '2026-08-05',
              'status', 'PRESENT',
              'supersedes_attendance_record_id', v_fake_supersedes
            )
          )
        ),
        gen_random_uuid(), (v_period->>'row_version')::bigint, false
      );
    exception when others then
      if sqlerrm like 'Non-correction attendance cannot declare supersedes lineage%' then
        v_noncorrection_lineage_blocked := true;
      else
        raise;
      end if;
    end;

    v_period_incomplete := erp.save_attendance_period_v1(
      jsonb_build_object(
        'period_id', v_period->>'period_id',
        'contractor_id', v_normal_contractor,
        'period_number', 'TST-ATT-20260803',
        'period_start', '2026-08-03',
        'period_end', '2026-08-09',
        'pay_date', '2026-08-10',
        'reason', 'Rollback test full-snapshot removal',
        'attendance', jsonb_build_array(
          jsonb_build_object('worker_id', v_worker, 'attendance_date', '2026-08-05', 'status', 'PRESENT'),
          jsonb_build_object('worker_id', v_worker, 'attendance_date', '2026-08-06', 'status', 'HALF_DAY'),
          jsonb_build_object('worker_id', v_worker, 'attendance_date', '2026-08-07', 'status', 'PRESENT'),
          jsonb_build_object('worker_id', v_worker, 'attendance_date', '2026-08-08', 'status', 'OFF', 'paid_fraction', 1)
        )
      ),
      gen_random_uuid(), (v_period->>'row_version')::bigint, false
    );

    if (select count(*) from erp.attendance_records
        where attendance_period_id = (v_period->>'period_id')::uuid) is distinct from 4
       or (select paid_fraction from erp.attendance_records
           where attendance_period_id = (v_period->>'period_id')::uuid
             and attendance_date = date '2026-08-06') is distinct from 0.5
       or (select paid_fraction from erp.attendance_records
           where attendance_period_id = (v_period->>'period_id')::uuid
             and attendance_date = date '2026-08-08') is distinct from 0 then
      raise exception 'DRAFT full-snapshot delete or canonical fraction persistence failed';
    end if;
    v_draft_snapshot_delete_verified := true;

    begin
      perform erp.post_attendance_period_v1(
        (v_period->>'period_id')::uuid,
        'Must fail while one eligible cell is blank',
        gen_random_uuid(),
        (v_period_incomplete->>'row_version')::bigint
      );
    exception when others then
      if sqlerrm like 'Attendance period has 1 unrecorded eligible worker/day cells%' then
        v_incomplete_post_blocked := true;
      else
        raise;
      end if;
    end;

    v_period := erp.save_attendance_period_v1(
      jsonb_build_object(
        'period_id', v_period->>'period_id',
        'contractor_id', v_normal_contractor,
        'period_number', 'TST-ATT-20260803',
        'period_start', '2026-08-03',
        'period_end', '2026-08-09',
        'pay_date', '2026-08-10',
        'reason', 'Rollback test restore complete explicit matrix',
        'attendance', jsonb_build_array(
          jsonb_build_object('worker_id', v_worker, 'attendance_date', '2026-08-05', 'status', 'PRESENT'),
          jsonb_build_object('worker_id', v_worker, 'attendance_date', '2026-08-06', 'status', 'PRESENT'),
          jsonb_build_object('worker_id', v_worker, 'attendance_date', '2026-08-07', 'status', 'PRESENT'),
          jsonb_build_object('worker_id', v_worker, 'attendance_date', '2026-08-08', 'status', 'OFF'),
          jsonb_build_object('worker_id', v_worker, 'attendance_date', '2026-08-09', 'status', 'OFF')
        )
      ),
      gen_random_uuid(), (v_period_incomplete->>'row_version')::bigint, false
    );

    v_posted := erp.post_attendance_period_v1(
      (v_period->>'period_id')::uuid,
      'Rollback test post attendance',
      gen_random_uuid(),
      (v_period->>'row_version')::bigint
    );

    -- Each public RPC is a separate database transaction in the browser/server
    -- contract. This rollback fixture intentionally keeps every scenario inside
    -- one subtransaction, so clear the transaction-local lifecycle bypass before
    -- asserting that an ordinary caller cannot edit a posted detail row.
    perform set_config('app.attendance_period_lifecycle', 'off', true);

    begin
      perform erp.save_worker_roster_v1(
        jsonb_build_object(
          'contractor_id', v_normal_contractor,
          'worker_code', 'TST-W-BACKDATED',
          'worker_name', 'Backdated Worker Must Fail',
          'job_description', 'Jahit',
          'pay_scheme', 'DAILY',
          'initial_daily_rate', 100,
          'rate_effective_from', '2026-08-09',
          'joined_at', '2026-08-09',
          'is_active', true,
          'reason', 'Rollback test posted chronology guard'
        ),
        gen_random_uuid(), null
      );
    exception when others then
      if sqlerrm like 'A new worker start cannot overlap posted attendance history%' then
        v_backdated_roster_blocked := true;
      else
        raise;
      end if;
    end;

    begin
      update erp.attendance_records
      set notes = 'Forbidden posted overwrite'
      where attendance_period_id = (v_period->>'period_id')::uuid
        and attendance_date = date '2026-08-05';
    exception when others then
      if sqlerrm like 'Posted attendance details are immutable%' then
        v_posted_edit_blocked := true;
      else
        raise;
      end if;
    end;

    begin
      insert into erp.attendance_records(
        contractor_id, worker_id, attendance_date, status, paid_fraction
      ) values (
        v_normal_contractor, v_worker, date '2026-08-05', 'PRESENT', 1
      );
    exception when unique_violation then
      v_duplicate_posted_blocked := true;
    end;

    insert into erp.payroll_settlements(
      id, payroll_number, contractor_id, period_start, period_end, status, notes
    ) values (
      v_payroll, 'TST-PAY-ATT-1', v_normal_contractor,
      date '2026-08-03', date '2026-08-09', 'DRAFT', 'Rollback-only attendance payroll'
    );
    perform erp.populate_payroll_draft(v_payroll);

    select count(*), sum(daily_rate_snapshot), array_agg(worker_name_snapshot order by attendance_date_snapshot)
    into v_rate_count, v_snapshot_total, v_snapshot_names
    from erp.payroll_attendance_items
    where payroll_id = v_payroll;

    if v_rate_count is distinct from 3 or v_snapshot_total is distinct from 320
       or v_snapshot_names is distinct from array['Nama Baru','Nama Baru','Nama Baru']::text[] then
      raise exception 'Payroll did not preserve date-resolved rate/name snapshots: count %, total %, names %',
        v_rate_count, v_snapshot_total, v_snapshot_names;
    end if;

    v_rate_after_payroll := erp.set_worker_daily_rate_v1(
      v_worker, 150, date '2026-08-10', 'Rollback test later rate',
      gen_random_uuid(), (v_worker_edit->>'row_version')::bigint
    );

    v_worker_deactivated := erp.save_worker_roster_v1(
      jsonb_build_object(
        'worker_id', v_worker,
        'contractor_id', v_normal_contractor,
        'worker_code', 'TST-W-001',
        'worker_name', 'Nama Terbaru',
        'job_description', 'Jahit Senior',
        'pay_scheme', 'DAILY',
        'joined_at', '2026-08-05',
        'left_at', '2026-08-10',
        'is_active', false,
        'notes', 'Catatan roster harus round-trip',
        'reason', 'Rollback test deactivate worker'
      ),
      gen_random_uuid(), (v_rate_after_payroll->>'row_version')::bigint
    );

    select sum(daily_rate_snapshot) into v_snapshot_total_after
    from erp.payroll_attendance_items where payroll_id = v_payroll;
    if v_snapshot_total_after is distinct from v_snapshot_total then
      raise exception 'Historical payroll snapshot changed after master/rate edit';
    end if;

    select jsonb_array_length(
      public.erp_get_attendance_workspace_v1(
        v_normal_contractor, date '2026-08-03', date '2026-08-12', false
      )->'workers'
    ) into v_nonactive_default_count;
    if v_nonactive_default_count is distinct from 0 then
      raise exception 'Inactive worker appeared in default attendance workspace';
    end if;

    v_worker_reactivated := erp.save_worker_roster_v1(
      jsonb_build_object(
        'worker_id', v_worker,
        'contractor_id', v_normal_contractor,
        'worker_code', 'TST-W-001',
        'worker_name', 'Nama Terbaru',
        'job_description', 'Jahit Senior',
        'pay_scheme', 'DAILY',
        'joined_at', '2026-08-05',
        'reactivated_at', '2026-08-13',
        'is_active', true,
        'notes', 'Catatan roster harus round-trip',
        'reason', 'Rollback test reactivate stable worker identity'
      ),
      gen_random_uuid(), (v_worker_deactivated->>'row_version')::bigint
    );

    if (v_worker_reactivated->>'worker_id')::uuid is distinct from v_worker
       or erp.worker_is_employed_on(v_worker, date '2026-08-11') is distinct from false
       or erp.worker_is_employed_on(v_worker, date '2026-08-13') is distinct from true
       or v_worker_reactivated->>'notes' is distinct from 'Catatan roster harus round-trip' then
      raise exception 'Worker reactivation did not preserve stable ID, gap, or notes: %',
        v_worker_reactivated;
    end if;

    begin
      insert into erp.attendance_records(
        contractor_id, worker_id, attendance_date, status, paid_fraction
      ) values (
        v_normal_contractor, v_worker, date '2026-08-11', 'PRESENT', 1
      );
    exception when others then
      if sqlerrm like 'Attendance date is outside the worker employment periods%' then
        v_after_stop_blocked := true;
      else
        raise;
      end if;
    end;

    if public.erp_get_attendance_workspace_v1(
         v_normal_contractor, date '2026-08-13', date '2026-08-13', false
       )#>>'{workers,0,notes}' is distinct from 'Catatan roster harus round-trip' then
      raise exception 'Attendance workspace omitted worker notes needed for edit round-trip';
    end if;

    begin
      perform erp.reverse_attendance_period_v1(
        (v_period->>'period_id')::uuid,
        'Forbidden while payroll is active',
        gen_random_uuid(),
        (v_posted->>'row_version')::bigint
      );
    exception when others then
      if sqlerrm like 'Attendance reversal requires its consuming payroll to be reversed first%' then
        v_attendance_reverse_while_payroll_active_blocked := true;
      else
        raise;
      end if;
    end;

    perform erp.cancel_unpaid_payroll(v_payroll, 'Rollback test unlock attendance correction');

    select jsonb_agg(
      jsonb_build_object(
        'worker_id', a.worker_id,
        'attendance_date', a.attendance_date,
        'status', case
          when a.attendance_date = date '2026-08-06' then 'HALF_DAY'
          else a.status
        end,
        'paid_fraction', case
          when a.attendance_date = date '2026-08-06' then 0.5
          else a.paid_fraction
        end,
        'supersedes_attendance_record_id', a.id
      ) order by a.attendance_date
    ) into v_correction_lines
    from erp.attendance_records a
    where a.attendance_period_id = (v_period->>'period_id')::uuid;

    begin
      perform erp.save_attendance_period_v1(
        jsonb_build_object(
          'contractor_id', v_normal_contractor,
          'period_number', 'TST-ATT-20260803-BAD-LINEAGE',
          'period_start', '2026-08-03',
          'period_end', '2026-08-09',
          'pay_date', '2026-08-10',
          'correction_of_period_id', (v_period->>'period_id')::uuid,
          'reason', 'Rollback correction must reject missing source lineage',
          'attendance', jsonb_set(
            v_correction_lines,
            '{0,supersedes_attendance_record_id}',
            'null'::jsonb
          )
        ), gen_random_uuid(), null, false
      );
    exception when others then
      if sqlerrm like 'Correction must explicitly supersede every source attendance row%' then
        v_bad_correction_lineage_blocked := true;
      else
        raise;
      end if;
    end;

    v_correction := erp.save_attendance_period_v1(
      jsonb_build_object(
        'contractor_id', v_normal_contractor,
        'period_number', 'TST-ATT-20260803-C1',
        'period_start', '2026-08-03',
        'period_end', '2026-08-09',
        'pay_date', '2026-08-10',
        'correction_of_period_id', (v_period->>'period_id')::uuid,
        'reason', 'Rollback correction after payroll cancellation',
        'attendance', v_correction_lines
      ), gen_random_uuid(), null, false
    );

    v_correction_posted := erp.post_attendance_period_v1(
      (v_correction->>'period_id')::uuid,
      'Rollback test post correction',
      gen_random_uuid(),
      (v_correction->>'row_version')::bigint
    );

    if (select status from erp.attendance_periods where id = (v_period->>'period_id')::uuid)
         is distinct from 'CORRECTED'
       or (select count(*) from erp.attendance_records
           where worker_id = v_worker and attendance_date = date '2026-08-06'
             and coalesce(record_lifecycle, 'POSTED') = 'POSTED') is distinct from 1 then
      raise exception 'Attendance correction did not preserve one current posted fact';
    end if;

    insert into erp.payroll_settlements(
      id, payroll_number, contractor_id, period_start, period_end, status, notes
    ) values (
      v_corrected_payroll, 'TST-PAY-ATT-CORRECTED', v_normal_contractor,
      date '2026-08-03', date '2026-08-09', 'DRAFT',
      'Rollback-only payroll rebuilt from corrected attendance'
    );
    perform erp.populate_payroll_draft(v_corrected_payroll);
    select count(*), sum(paid_fraction_snapshot * daily_rate_snapshot)
    into v_corrected_payroll_count, v_corrected_payroll_total
    from erp.payroll_attendance_items
    where payroll_id = v_corrected_payroll;
    if v_corrected_payroll_count is distinct from 3
       or v_corrected_payroll_total is distinct from 270 then
      raise exception 'Corrected attendance payroll was duplicated or used the wrong snapshot total';
    end if;
    perform erp.cancel_unpaid_payroll(
      v_corrected_payroll,
      'Rollback test unlock correction reversal after corrected payroll rebuild'
    );

    v_reversed := erp.reverse_attendance_period_v1(
      (v_correction->>'period_id')::uuid,
      'Rollback test reverse correction',
      gen_random_uuid(),
      (v_correction_posted->>'row_version')::bigint
    );

    select count(*) into v_restored_source_count
    from erp.attendance_records a
    where a.attendance_period_id = (v_period->>'period_id')::uuid
      and a.record_lifecycle = 'POSTED';

    if (select status from erp.attendance_periods
        where id = (v_period->>'period_id')::uuid) is distinct from 'POSTED'
       or v_restored_source_count is distinct from 5
       or (select count(*) from erp.attendance_records a
           where a.attendance_period_id = (v_correction->>'period_id')::uuid
             and a.record_lifecycle = 'POSTED') is distinct from 0
       or (v_reversed->>'restored_source_period_id')::uuid is distinct from
          (v_period->>'period_id')::uuid then
      raise exception 'Correction reversal did not restore exactly one current source fact per cell';
    end if;

    insert into erp.payroll_settlements(
      id, payroll_number, contractor_id, period_start, period_end, status, notes
    ) values (
      v_restored_payroll, 'TST-PAY-ATT-RESTORED', v_normal_contractor,
      date '2026-08-03', date '2026-08-09', 'DRAFT',
      'Rollback-only payroll rebuilt after correction reversal'
    );
    perform erp.populate_payroll_draft(v_restored_payroll);
    select count(*), sum(paid_fraction_snapshot * daily_rate_snapshot)
    into v_restored_payroll_count, v_restored_payroll_total
    from erp.payroll_attendance_items
    where payroll_id = v_restored_payroll;
    if v_restored_payroll_count is distinct from 3
       or v_restored_payroll_total is distinct from 320 then
      raise exception 'Restored attendance payroll was duplicated or used the wrong snapshot total';
    end if;

    insert into erp.payroll_settlements(
      id, payroll_number, contractor_id, period_start, period_end, status, notes
    ) values (
      v_special_payroll, 'TST-PAY-ATT-SPECIAL', v_special_contractor,
      date '2026-08-03', date '2026-08-09', 'DRAFT', 'Rollback-only exempt payroll'
    );
    perform erp.populate_payroll_draft(v_special_payroll);
    if (select attendance_total from erp.payroll_settlements where id = v_special_payroll)
         is distinct from 0 then
      raise exception 'attendance_required=false contractor received attendance payroll cost';
    end if;

    insert into erp.brands(id, brand_code, brand_name)
    values(v_brand, 'TST-STK', 'Test Stock Explainability');
    insert into erp.product_models(id, model_code, model_name)
    values(v_model, 'TST-STK-MODEL', 'Test Stock Explainability Model');
    insert into erp.sizes(id, size_code, sort_order)
    values(v_size, 'TST-STK-SIZE', 998);
    insert into erp.product_model_sizes(model_id, size_id, sort_order)
    values(v_model, v_size, 1);
    insert into erp.products(
      id, sku, model_id, brand_id, color_name, size_id, product_name,
      identity_root_id, effective_from, is_active
    ) values(
      v_product, 'TST-STK-001', v_model, v_brand, 'Test', v_size,
      'Test Stock Product', v_product, clock_timestamp() - interval '3 days', true
    );
    insert into erp.locations(id, location_code, location_name, location_type)
    values(v_location, 'TST-STK-WH', 'Test Stock Warehouse', 'FG_WAREHOUSE');
    insert into erp.fg_lots(
      id, lot_number, product_id, initial_qty_pcs, cached_qty_pcs, produced_at, lot_origin
    ) values
      (
        v_lot, 'TST-STK-LOT-A', v_product, 10, 0,
        clock_timestamp() - interval '2 days', 'OTHER'
      ),
      (
        v_lot_grade_b, 'TST-STK-LOT-B', v_product, 3, 0,
        clock_timestamp() - interval '2 days', 'OTHER'
      );

    perform erp.post_fg_movement(
      v_product, v_lot, v_location, 'GRADE_A', 'OPENING', 10, 0, null,
      'TEST_SEED', v_source, clock_timestamp() - interval '2 days',
      'Rollback-only stock seed', false
    );
    perform erp.post_fg_movement(
      v_product, v_lot, v_location, 'GRADE_A', 'SALE_RESERVE', -4, 0, null,
      'TEST_RESERVE', gen_random_uuid(), clock_timestamp() - interval '1 day',
      'Rollback-only active reservation', false
    );
    perform erp.post_fg_movement(
      v_product, v_lot_grade_b, v_location, 'GRADE_B', 'OPENING', 3, 0, null,
      'TEST_SEED_GRADE_B', gen_random_uuid(), clock_timestamp() - interval '2 days',
      'Rollback-only non-sellable grade discriminator', false
    );

    select * into v_position
    from erp.v_fg_stock_position_v1
    where product_id = v_product and location_id = v_location and quality_grade = 'GRADE_A';

    if v_position.physical_stock_qty_pcs is distinct from 10
       or v_position.reserved_qty_pcs is distinct from 4
       or v_position.available_stock_qty_pcs is distinct from 6 then
      raise exception 'FG stock invariant double-subtracted reservation: %', to_jsonb(v_position);
    end if;

    v_explain := public.erp_get_fg_stock_explainability_v1(v_product, v_location);
    if jsonb_array_length(v_explain) is distinct from 1
       or v_explain#>>'{0,quality_grade}' is distinct from 'GRADE_A'
       or (v_explain#>>'{0,physical_stock_qty_pcs}')::numeric is distinct from 10
       or (v_explain#>>'{0,reserved_qty_pcs}')::numeric is distinct from 4
       or (v_explain#>>'{0,available_stock_qty_pcs}')::numeric is distinct from 6
       or v_explain#>>'{0,health_status}' is distinct from 'BELUM_CUKUP_DATA'
       or v_explain#>>'{0,basis_source}' is distinct from 'BELUM_DIATUR'
       or v_explain#>'{0,recommended_qty_pcs}' is distinct from 'null'::jsonb then
      raise exception 'Missing inputs were presented as a fake stock recommendation: %', v_explain;
    end if;

    v_policy := erp.set_fg_stock_policy_v1(
      v_product, v_location, 'MANUAL', 5, 12, 30, current_date,
      'Rollback test manual stock limit', null, gen_random_uuid()
    );

    v_explain := public.erp_get_fg_stock_explainability_v1(v_product, v_location);
    if jsonb_array_length(v_explain) is distinct from 1
       or v_explain#>>'{0,basis_source}' is distinct from 'MANUAL'
       or v_explain#>>'{0,health_status}' is distinct from 'BELUM_CUKUP_DATA'
       or v_explain#>>'{0,calculation_readiness}' is distinct from 'BLOCKED_AUTHORITATIVE_INPUTS'
       or v_explain#>>'{0,manual_policy_status}' is distinct from 'STORED_NOT_CALCULATED'
       or (v_explain#>>'{0,manual_reorder_point_qty_pcs}')::numeric is distinct from 5
       or v_explain#>'{0,recommended_qty_pcs}' is distinct from 'null'::jsonb then
      raise exception 'Manual basis was not separated from calculated health: %', v_explain;
    end if;

    v_policy_2 := erp.set_fg_stock_policy_v1(
      v_product, v_location, 'MANUAL', 6, 14, 30, current_date + 1,
      'Rollback test next policy version', (v_policy->>'policy_version_id')::uuid,
      gen_random_uuid()
    );
    select * into v_old_policy
    from erp.stock_policy_versions
    where id = (v_policy->>'policy_version_id')::uuid;
    if v_old_policy.manual_reorder_point_qty is distinct from 5
       or v_old_policy.manual_target_stock_qty is distinct from 12
       or v_old_policy.effective_to is distinct from current_date then
      raise exception 'Effective-dated stock override rewrote historical values';
    end if;

    begin
      perform erp.set_fg_stock_policy_v1(
        v_product, v_location, 'REKOMENDASI_SISTEM', null, null, 30,
        current_date + 2, 'Forbidden fake system recommendation',
        (v_policy_2->>'policy_version_id')::uuid, gen_random_uuid()
      );
    exception when others then
      if sqlerrm like 'REKOMENDASI_SISTEM cannot be selected by a user%' then
        v_fake_system_policy_blocked := true;
      else
        raise;
      end if;
    end;

    begin
      insert into erp.stock_explainability_snapshots(
        id, subject_type, product_id, location_id, source_as_of,
        health_status, basis_source, physical_stock_qty, reserved_qty,
        available_stock_qty, formula_version, formula_expression,
        source_manifest, calculation_key
      ) values(
        gen_random_uuid(), 'FG', v_product, v_location, clock_timestamp(),
        'BELUM_CUKUP_DATA', 'MANUAL', 10, 4, 5,
        'TEST', 'bad equation', '{}'::jsonb, gen_random_uuid()::text
      );
    exception when check_violation then
      v_bad_stock_equation_blocked := true;
    end;

    insert into erp.stock_explainability_snapshots(
      id, subject_type, product_id, location_id, source_as_of,
      health_status, basis_source, policy_version_id,
      physical_stock_qty, reserved_qty, available_stock_qty,
      formula_version, formula_expression, source_manifest, calculation_key
    ) values(
      v_snapshot, 'FG', v_product, v_location, clock_timestamp(),
      'BELUM_CUKUP_DATA', 'MANUAL', (v_policy->>'policy_version_id')::uuid,
      10, 4, 6, 'TEST_INPUTS_NOT_CONNECTED',
      'physical = available + reserved; other inputs unavailable',
      jsonb_build_object('test_data', true), gen_random_uuid()::text
    );

    begin
      update erp.stock_explainability_snapshots
      set health_status = 'AMAN'
      where id = v_snapshot;
    exception when others then
      if sqlerrm like 'Stock explainability snapshots are immutable%' then
        v_snapshot_mutation_blocked := true;
      else
        raise;
      end if;
    end;

    if not v_initial_rate_gap_blocked
       or not v_rate_resolver_fail_closed
       or not v_overlap_rate_blocked
       or not v_before_start_blocked
       or not v_after_stop_blocked
       or not v_incomplete_post_blocked
       or not v_draft_snapshot_delete_verified
       or not v_bad_correction_lineage_blocked
       or not v_noncorrection_lineage_blocked
       or not v_backdated_roster_blocked
       or not v_duplicate_payload_blocked
       or not v_duplicate_posted_blocked
       or not v_posted_edit_blocked
       or not v_attendance_reverse_while_payroll_active_blocked
       or not v_fake_system_policy_blocked
       or not v_bad_stock_equation_blocked
       or not v_snapshot_mutation_blocked then
      raise exception 'Negative control failure: %', jsonb_build_object(
        'initial_rate_gap', v_initial_rate_gap_blocked,
        'rate_resolver_fail_closed', v_rate_resolver_fail_closed,
        'rate_overlap', v_overlap_rate_blocked,
        'before_start', v_before_start_blocked,
        'after_stop', v_after_stop_blocked,
        'incomplete_post', v_incomplete_post_blocked,
        'draft_snapshot_delete', v_draft_snapshot_delete_verified,
        'bad_correction_lineage', v_bad_correction_lineage_blocked,
        'noncorrection_lineage', v_noncorrection_lineage_blocked,
        'backdated_roster', v_backdated_roster_blocked,
        'duplicate_payload', v_duplicate_payload_blocked,
        'duplicate_posted', v_duplicate_posted_blocked,
        'posted_edit', v_posted_edit_blocked,
        'reverse_active_payroll', v_attendance_reverse_while_payroll_active_blocked,
        'fake_system_policy', v_fake_system_policy_blocked,
        'bad_stock_equation', v_bad_stock_equation_blocked,
        'snapshot_mutation', v_snapshot_mutation_blocked
      );
    end if;

    if exists (
      select 1
      from information_schema.table_privileges g
      where g.table_schema = 'erp'
        and g.table_name in (
          'worker_daily_rate_versions','worker_employment_periods','attendance_periods',
          'stock_policy_versions','stock_explainability_snapshots'
        )
        and g.grantee in ('PUBLIC','anon','authenticated')
    ) then
      raise exception 'New private ERP tables received a direct browser grant';
    end if;

    if (
      select count(*)
      from pg_class c
      join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'erp'
        and c.relname in (
          'worker_daily_rate_versions','worker_employment_periods','attendance_periods',
          'stock_policy_versions','stock_explainability_snapshots'
        )
        and c.relrowsecurity
    ) is distinct from 5 then
      raise exception 'One or more new private ERP tables do not have RLS enabled';
    end if;

    if exists (
      select 1
      from pg_proc p
      join pg_namespace n on n.oid = p.pronamespace
      where n.nspname = 'erp'
        and p.proname in (
          'save_worker_roster_v1','set_worker_daily_rate_v1',
          'save_attendance_period_v1','post_attendance_period_v1',
          'reverse_attendance_period_v1','set_fg_stock_policy_v1'
        )
        and (
          has_function_privilege('anon', p.oid, 'EXECUTE')
          or has_function_privilege('authenticated', p.oid, 'EXECUTE')
          or not p.prosecdef
          or coalesce(array_to_string(p.proconfig, ','), '') not like '%search_path=%'
        )
    ) then
      raise exception 'Internal ERP writer ACL or SECURITY DEFINER search_path is unsafe';
    end if;

    if exists (
      select 1
      from pg_proc p
      join pg_namespace n on n.oid = p.pronamespace
      where n.nspname = 'public'
        and p.proname in (
          'erp_save_worker_roster_v1','erp_set_worker_daily_rate_v1',
          'erp_save_attendance_period_v1','erp_post_attendance_period_v1',
          'erp_reverse_attendance_period_v1','erp_set_fg_stock_policy_v1',
          'erp_get_attendance_workspace_v1','erp_get_fg_stock_explainability_v1'
        )
        and (
          has_function_privilege('anon', p.oid, 'EXECUTE')
          or not has_function_privilege('authenticated', p.oid, 'EXECUTE')
          or not p.prosecdef
          or coalesce(array_to_string(p.proconfig, ','), '') not like '%search_path=%'
        )
    ) then
      raise exception 'Public ERP facade ACL or SECURITY DEFINER search_path is unsafe';
    end if;

    v_result := jsonb_build_object(
      'initial_rate_coverage_guard', v_initial_rate_gap_blocked,
      'rate_resolver_fail_closed', v_rate_resolver_fail_closed,
      'attendance_start_guard', v_before_start_blocked,
      'attendance_stop_guard', v_after_stop_blocked,
      'reactivation_gap_preserved', erp.worker_is_employed_on(v_worker, date '2026-08-11') is false,
      'stable_worker_id_after_reactivation',
        (v_worker_reactivated->>'worker_id')::uuid is not distinct from v_worker,
      'rate_overlap_guard', v_overlap_rate_blocked,
      'rate_idempotency_version_count', v_rate_version_count,
      'duplicate_payload_guard', v_duplicate_payload_blocked,
      'duplicate_posted_guard', v_duplicate_posted_blocked,
      'draft_full_snapshot_delete', v_draft_snapshot_delete_verified,
      'blank_cell_post_guard', v_incomplete_post_blocked,
      'correction_lineage_guard', v_bad_correction_lineage_blocked,
      'noncorrection_lineage_guard', v_noncorrection_lineage_blocked,
      'backdated_roster_guard', v_backdated_roster_blocked,
      'bulk_preview_amount', v_period#>'{preview,estimated_amount}',
      'payroll_rate_snapshot_total', v_snapshot_total,
      'payroll_snapshot_unchanged_after_master_edit',
        v_snapshot_total_after is not distinct from v_snapshot_total,
      'inactive_hidden_by_default', v_nonactive_default_count is not distinct from 0,
      'attendance_payroll_guard', v_attendance_reverse_while_payroll_active_blocked,
      'correction_status', v_correction_posted->>'status',
      'reversal_status', v_reversed->>'status',
      'correction_source_restored_count', v_restored_source_count,
      'corrected_payroll_item_count', v_corrected_payroll_count,
      'corrected_payroll_total', v_corrected_payroll_total,
      'restored_payroll_item_count', v_restored_payroll_count,
      'restored_payroll_total', v_restored_payroll_total,
      'special_contractor_attendance_total', (
        select attendance_total from erp.payroll_settlements where id = v_special_payroll
      ),
      'fg_physical_qty_pcs', v_position.physical_stock_qty_pcs,
      'fg_reserved_qty_pcs', v_position.reserved_qty_pcs,
      'fg_available_qty_pcs', v_position.available_stock_qty_pcs,
      'stock_no_data_status', v_explain#>>'{0,health_status}',
      'manual_basis_separate', v_explain#>>'{0,basis_source}',
      'fake_system_policy_blocked', v_fake_system_policy_blocked,
      'stock_equation_guard', v_bad_stock_equation_blocked,
      'snapshot_immutable', v_snapshot_mutation_blocked,
      'direct_browser_table_grants', false,
      'private_tables_rls_enabled', true,
      'function_acl_and_search_path_checked', true,
      'test_data_persisted', false
    );

    raise exception using errcode = 'PT001', message = 'ROLLBACK_ATTENDANCE_STOCK_EXPLAINABILITY_TEST';
  exception when sqlstate 'PT001' then
    if sqlerrm is distinct from 'ROLLBACK_ATTENDANCE_STOCK_EXPLAINABILITY_TEST' then raise; end if;
    return v_result;
  end;
end;
$test$;

select pg_temp.run_attendance_stock_explainability_test() as result;
