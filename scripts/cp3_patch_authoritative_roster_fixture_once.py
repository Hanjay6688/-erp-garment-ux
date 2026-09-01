#!/usr/bin/env python3
from pathlib import Path

PATH = Path('supabase/tests/attendance_hpp_sewing_terminal_rollback.sql')
START_MARKER = 'insert into erp.contractor_workers('
END_MARKER = '-- Explicit effective-dated policy.'

REPLACEMENT = r'''-- Worker, employment, and initial-rate history are created only through the
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

'''

SUBSTITUTIONS = {
    "'26140000-0000-4000-8000-000000000021'": ":'cp3_worker_n1'::uuid",
    "'26140000-0000-4000-8000-000000000022'": ":'cp3_worker_n2'::uuid",
    "'26140000-0000-4000-8000-000000000023'": ":'cp3_worker_special'::uuid",
    "'26140000-0000-4000-8000-000000000024'": ":'cp3_worker_exempt'::uuid",
    "'26140000-0000-4000-8000-000000000041'": ":'cp3_rate_n1'::uuid",
    "'26140000-0000-4000-8000-000000000042'": ":'cp3_rate_n2'::uuid",
    "'26140000-0000-4000-8000-000000000043'": ":'cp3_rate_special'::uuid",
    "'26140000-0000-4000-8000-000000000044'": ":'cp3_rate_exempt'::uuid",
}


def main() -> None:
    text = PATH.read_text()
    if text.count(START_MARKER) != 1 or text.count(END_MARKER) != 1:
        raise SystemExit('fixture roster anchors are missing or ambiguous')

    start = text.index(START_MARKER)
    end = text.index(END_MARKER)
    if end <= start:
        raise SystemExit('fixture roster anchors are out of order')

    text = text[:start] + REPLACEMENT + text[end:]

    replaced: dict[str, int] = {}
    for old, new in SUBSTITUTIONS.items():
        count = text.count(old)
        if count == 0:
            raise SystemExit(
                f'expected fixture identity not found after roster block replacement: {old}'
            )
        text = text.replace(old, new)
        replaced[old] = count

    forbidden = (
        'insert into erp.worker_employment_periods',
        'insert into erp.worker_daily_rate_versions',
    )
    for token in forbidden:
        if token in text:
            raise SystemExit(f'authoritative fixture still contains forbidden direct write: {token}')
    for old in SUBSTITUTIONS:
        if old in text:
            raise SystemExit(f'legacy fixed worker/rate identity remains: {old}')
    if text.count('erp.save_worker_roster_v1(') != 4:
        raise SystemExit('expected exactly four authoritative roster RPC calls')
    if not text.rstrip().lower().endswith('rollback;'):
        raise SystemExit('outer rollback is missing')

    PATH.write_text(text)
    print({'replaced_identity_occurrences': replaced})


if __name__ == '__main__':
    main()
