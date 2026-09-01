#!/usr/bin/env python3
from pathlib import Path

PATH = Path('supabase/tests/attendance_hpp_sewing_terminal_rollback.sql')
START_MARKER = 'insert into erp.attendance_periods('
END_MARKER = 'insert into erp.payroll_settlements('


def attendance_document(
    *,
    contractor_id: str,
    worker_var: str,
    period_number: str,
    period_var: str,
    version_var: str,
    record_var: str,
    save_request_id: str,
    post_request_id: str,
) -> str:
    return f'''select (erp.save_attendance_period_v1(
  jsonb_build_object(
    'contractor_id','{contractor_id}',
    'period_number','{period_number}',
    'period_start','2026-08-01','period_end','2026-08-31','pay_date','2026-08-31',
    'reason','CP3 authoritative attendance fixture',
    'attendance',(
      select jsonb_agg(
        jsonb_build_object(
          'worker_id', :'{worker_var}'::uuid,
          'attendance_date', day_value::date,
          'status', case when day_value::date='2026-08-10'::date then 'PRESENT' else 'OFF' end,
          'paid_fraction', case when day_value::date='2026-08-10'::date then 1 else 0 end,
          'notes','CP3 explicit full-month matrix'
        ) order by day_value
      )
      from generate_series(
        '2026-08-01'::date,
        '2026-08-31'::date,
        interval '1 day'
      ) day_value
    )
  ),
  '{save_request_id}',null,false
)->>'period_id')::text as {period_var}
\\gset

select row_version::text as {version_var}
from erp.attendance_periods
where id=:'{period_var}'::uuid
\\gset

select erp.post_attendance_period_v1(
  :'{period_var}'::uuid,
  'CP3 authoritative attendance fixture post',
  '{post_request_id}',
  :'{version_var}'::bigint
);

select id::text as {record_var}
from erp.attendance_records
where attendance_period_id=:'{period_var}'::uuid
  and worker_id=:'{worker_var}'::uuid
  and attendance_date='2026-08-10'::date
  and record_lifecycle='POSTED'
\\gset
'''


REPLACEMENT = '''-- Attendance periods are authored as complete DRAFT matrices through the
-- authoritative RPC and then posted through the lifecycle RPC. Every eligible day is
-- explicit: 10 August is PRESENT and every other August day is OFF.
''' + '\n'.join([
    attendance_document(
        contractor_id='26140000-0000-4000-8000-000000000011',
        worker_var='cp3_worker_n1',
        period_number='CP3-ATT-N1-AUG',
        period_var='cp3_att_period_n1',
        version_var='cp3_att_period_n1_version',
        record_var='cp3_att_record_n1',
        save_request_id='26140000-0000-4000-8000-000000000111',
        post_request_id='26140000-0000-4000-8000-000000000121',
    ),
    attendance_document(
        contractor_id='26140000-0000-4000-8000-000000000012',
        worker_var='cp3_worker_n2',
        period_number='CP3-ATT-N2-AUG',
        period_var='cp3_att_period_n2',
        version_var='cp3_att_period_n2_version',
        record_var='cp3_att_record_n2',
        save_request_id='26140000-0000-4000-8000-000000000112',
        post_request_id='26140000-0000-4000-8000-000000000122',
    ),
    attendance_document(
        contractor_id='26140000-0000-4000-8000-000000000013',
        worker_var='cp3_worker_special',
        period_number='CP3-ATT-SP-AUG',
        period_var='cp3_att_period_special',
        version_var='cp3_att_period_special_version',
        record_var='cp3_att_record_special',
        save_request_id='26140000-0000-4000-8000-000000000113',
        post_request_id='26140000-0000-4000-8000-000000000123',
    ),
    attendance_document(
        contractor_id='26140000-0000-4000-8000-000000000014',
        worker_var='cp3_worker_exempt',
        period_number='CP3-ATT-EX-AUG',
        period_var='cp3_att_period_exempt',
        version_var='cp3_att_period_exempt_version',
        record_var='cp3_att_record_exempt',
        save_request_id='26140000-0000-4000-8000-000000000114',
        post_request_id='26140000-0000-4000-8000-000000000124',
    ),
]) + '\n'

SUBSTITUTIONS = {
    "'26140000-0000-4000-8000-000000000201'": ":'cp3_att_period_n1'::uuid",
    "'26140000-0000-4000-8000-000000000202'": ":'cp3_att_period_n2'::uuid",
    "'26140000-0000-4000-8000-000000000203'": ":'cp3_att_period_special'::uuid",
    "'26140000-0000-4000-8000-000000000204'": ":'cp3_att_period_exempt'::uuid",
    "'26140000-0000-4000-8000-000000000211'": ":'cp3_att_record_n1'::uuid",
    "'26140000-0000-4000-8000-000000000212'": ":'cp3_att_record_n2'::uuid",
    "'26140000-0000-4000-8000-000000000213'": ":'cp3_att_record_special'::uuid",
    "'26140000-0000-4000-8000-000000000214'": ":'cp3_att_record_exempt'::uuid",
}


def main() -> None:
    text = PATH.read_text()
    if text.count(START_MARKER) != 1 or text.count(END_MARKER) != 1:
        raise SystemExit('fixture attendance anchors are missing or ambiguous')

    start = text.index(START_MARKER)
    end = text.index(END_MARKER)
    if end <= start:
        raise SystemExit('fixture attendance anchors are out of order')

    text = text[:start] + REPLACEMENT + text[end:]

    replaced: dict[str, int] = {}
    for old, new in SUBSTITUTIONS.items():
        count = text.count(old)
        if old.endswith(('211\'', '212\'', '213\'', '214\'')) and count == 0:
            raise SystemExit(f'expected payroll attendance identity not found: {old}')
        if count:
            text = text.replace(old, new)
        replaced[old] = count

    for old in SUBSTITUTIONS:
        if old in text:
            raise SystemExit(f'legacy fixed attendance identity remains: {old}')
    if text.count('erp.save_attendance_period_v1(') != 4:
        raise SystemExit('expected exactly four authoritative attendance save calls')
    if text.count('erp.post_attendance_period_v1(') != 4:
        raise SystemExit('expected exactly four authoritative attendance post calls')
    if not text.rstrip().lower().endswith('rollback;'):
        raise SystemExit('outer rollback is missing')

    PATH.write_text(text)
    print({'replaced_identity_occurrences': replaced})


if __name__ == '__main__':
    main()
