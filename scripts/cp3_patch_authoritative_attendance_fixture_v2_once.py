#!/usr/bin/env python3
import importlib.util
from pathlib import Path

SOURCE = Path('scripts/cp3_patch_authoritative_attendance_fixture_once.py')
spec = importlib.util.spec_from_file_location('cp3_attendance_fixture_patch', SOURCE)
if spec is None or spec.loader is None:
    raise SystemExit('unable to load attendance fixture transformer')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

module.START_MARKER = (
    '-- Attendance and payroll sources for August.\n'
    'insert into erp.attendance_periods('
    'id,period_number,contractor_id,period_start,period_end,pay_date,status,posting_reason)'
)
module.END_MARKER = (
    'insert into erp.payroll_settlements('
    'id,payroll_number,contractor_id,period_start,period_end,status,payment_date)'
)

module.main()
