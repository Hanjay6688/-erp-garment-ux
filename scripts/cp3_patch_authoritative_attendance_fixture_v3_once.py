#!/usr/bin/env python3
import importlib.util
from pathlib import Path

SOURCE = Path('scripts/cp3_patch_authoritative_attendance_fixture_once.py')
spec = importlib.util.spec_from_file_location('cp3_attendance_fixture_patch', SOURCE)
if spec is None or spec.loader is None:
    raise SystemExit('unable to load attendance fixture transformer')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

path = module.PATH
text = path.read_text()
start_marker = (
    '-- Attendance and payroll sources for August.\n'
    'insert into erp.attendance_periods('
    'id,period_number,contractor_id,period_start,period_end,pay_date,status,posting_reason)'
)
end_marker = (
    'insert into erp.payroll_settlements('
    'id,payroll_number,contractor_id,period_start,period_end,status,payment_date)'
)

start_count = text.count(start_marker)
all_end_count = text.count(end_marker)
print({'start_count': start_count, 'all_payroll_header_count': all_end_count})
if start_count != 1:
    raise SystemExit('authoritative attendance setup start must appear exactly once')
start = text.index(start_marker)
end = text.find(end_marker, start + len(start_marker))
if end < 0 or end <= start:
    raise SystemExit('payroll boundary after attendance setup was not found')

text = text[:start] + module.REPLACEMENT + text[end:]

required_record_ids = {
    "'26140000-0000-4000-8000-000000000211'",
    "'26140000-0000-4000-8000-000000000212'",
    "'26140000-0000-4000-8000-000000000213'",
    "'26140000-0000-4000-8000-000000000214'",
}
replaced: dict[str, int] = {}
for old, new in module.SUBSTITUTIONS.items():
    count = text.count(old)
    if old in required_record_ids and count == 0:
        raise SystemExit(f'expected payroll attendance identity not found: {old}')
    if count:
        text = text.replace(old, new)
    replaced[old] = count

for old in module.SUBSTITUTIONS:
    if old in text:
        raise SystemExit(f'legacy fixed attendance identity remains: {old}')
if start_marker in text:
    raise SystemExit('legacy posted attendance setup remains')
if text.count('erp.save_attendance_period_v1(') != 4:
    raise SystemExit('expected exactly four authoritative attendance save calls')
if text.count('erp.post_attendance_period_v1(') != 4:
    raise SystemExit('expected exactly four authoritative attendance post calls')
if not text.rstrip().lower().endswith('rollback;'):
    raise SystemExit('outer rollback is missing')

path.write_text(text)
print({'replaced_identity_occurrences': replaced})
