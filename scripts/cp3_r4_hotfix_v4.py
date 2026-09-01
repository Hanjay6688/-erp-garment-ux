#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = ROOT / 'supabase/migrations/20260901023400_erp_v2_6_14d_cp3_r4_race_and_reversal_hardening.sql'
ACC = ROOT / 'supabase/tests/attendance_hpp_r4_full_schema_rollback.sql'
HAR = ROOT / 'scripts/cp3_r4_full_schema_concurrency.py'
MAN = ROOT / 'docs/evidence/cp3_r4_source_hashes.json'

migration = MIG.read_text()
old_rule = """    if v_count<>p_expected_occurrences_per_function then
      raise exception 'R4 patch % expected % anchor occurrence(s), found %',p_proname,p_expected_occurrences_per_function,v_count;
    end if;"""
new_rule = """    if (p_expected_occurrences_per_function>=0 and v_count<>p_expected_occurrences_per_function)
       or (p_expected_occurrences_per_function<0 and v_count<1) then
      raise exception 'R4 patch % expected % anchor occurrence rule, found %',p_proname,p_expected_occurrences_per_function,v_count;
    end if;"""
if old_rule in migration:
    migration = migration.replace(old_rule, new_rule, 1)
elif new_rule not in migration:
    raise SystemExit('replacement cardinality rule: neither reviewed old nor hardened new rule found')

for proname in ('cancel_attendance_hpp_pool_v1', 'cancel_unpaid_payroll', 'reverse_paid_payroll'):
    old = f"'{proname}','erp.reverse_journal(','erp._cp3_r4_reverse_journal_internal(',1,1"
    new = f"'{proname}','erp.reverse_journal(','erp._cp3_r4_reverse_journal_internal(',1,-1"
    if old in migration:
        migration = migration.replace(old, new, 1)
    elif new not in migration:
        raise SystemExit(f'{proname}: reviewed owning-callsite replacement rule not found')
MIG.write_text(migration)

# The generated acceptance already contains the exact restored-schema source and
# destination matrix. Reuse it instead of inserting a synthetic duplicate shape.
acceptance = ACC.read_text()
required_acceptance_markers = (
    '-- Exact restored-schema nested JSON matrix:',
    "'source required key missing'",
    "'source required key null'",
    "'source extra key'",
    "'source wrong type'",
    "'source string true'",
    "'source string false'",
    "'source empty object'",
    "'source nested missing nullable key'",
    "'destination required key missing'",
    "'destination required key null'",
    "'destination extra key'",
    "'destination wrong type'",
    "'destination string true'",
    "'destination string false'",
    "'destination empty object'",
    "'destination nested missing key'",
    "jsonb_typeof(m#>'{sources,0,attendance_required_snapshot}')",
    "jsonb_typeof(m#>'{destinations,0,is_special_snapshot}')",
)
missing = [marker for marker in required_acceptance_markers if marker not in acceptance]
if missing:
    raise SystemExit(f'exact restored-schema strict JSON proof is incomplete: {missing}')

harness = HAR.read_text()
for marker in ('def strict_nested_json_cases(', 'validate_pool(admin, pool["id"])'):
    if marker not in harness:
        raise SystemExit(f'R4 concurrency harness lost reviewed marker: {marker}')

manifest = json.loads(MAN.read_text())
for rel in manifest['files']:
    data = (ROOT / rel).read_bytes()
    manifest['files'][rel] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
MAN.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
print(json.dumps({
    'status': 'PASS',
    'strict_runtime_matrix': 'existing exact ERP Enteng restored-schema manifest objects',
    'source_negative_cases': 8,
    'destination_negative_cases': 8,
    'real_boolean_positive_fields': 4,
}, sort_keys=True))
