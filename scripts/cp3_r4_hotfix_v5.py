#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAR = ROOT / 'scripts/cp3_r4_full_schema_concurrency.py'
R3_SEED = ROOT / 'supabase/tests/cp3_r3_full_schema_seed.sql'
R4_SEED = ROOT / 'supabase/tests/cp3_r4_full_schema_seed.sql'
R4_RACE_SEED = ROOT / 'supabase/tests/cp3_r4_full_schema_race_seed.sql'
ACC = ROOT / 'supabase/tests/attendance_hpp_r4_full_schema_rollback.sql'
WORKFLOW = ROOT / '.github/workflows/cp3-r4-full-schema-validation.yml'
MAN = ROOT / 'docs/evidence/cp3_r4_source_hashes.json'

# The generated harness already contains deterministic target-faithful IDs and all
# required two-session orders. Verify the exact fixture contract instead of
# rewriting it through stale discovery anchors.
harness = HAR.read_text()
r3_seed = R3_SEED.read_text()
r4_seed = R4_SEED.read_text()
r4_race_seed = R4_RACE_SEED.read_text()
acceptance = ACC.read_text()
required_harness = (
    "'activate-vs-approve-payroll'",
    "'approve-payroll-first-vs-activate'",
    "'activate-vs-policy-update'",
    "'policy-update-first-vs-activate'",
    "'activate-vs-reverse-work-completion'",
    "'reverse-work-first-rejects-vs-activate'",
    "'owning-reverse-work-first-vs-activate'",
    "'activate-vs-record-sewing'",
    "'record-sewing-first-vs-activate'",
    "'activate-vs-reverse-sewing'",
    "'reverse-sewing-first-vs-activate'",
    "'activate-vs-cancel-payroll'",
    "'cancel-payroll-first-vs-activate'",
    "'protected-journal-service-role-and-owning-lifecycle'",
    "'mode': 'REAL_TWO_CONNECTION_FULL_SCHEMA'",
    "'postgres_connections_per_race': 2",
    "'a6000000-0000-0000-0000-000000000021'",
    "'a5000000-0000-0000-0000-000000000040'",
)
missing_harness = [marker for marker in required_harness if marker not in harness]
if missing_harness:
    raise SystemExit(f'R4 race harness contract incomplete: {missing_harness}')

# IDs used by the harness must be created by committed target-faithful fixtures,
# never inferred from arbitrary hosted data.
fixture_corpus = '\n'.join((r3_seed, r4_seed, r4_race_seed, acceptance))
required_fixture_ids = (
    'a6000000-0000-0000-0000-000000000021',
    'a5000000-0000-0000-0000-000000000040',
    'a5000000-0000-0000-0000-000000000011',
    'a5000000-0000-0000-0000-000000000012',
)
missing_ids = [item for item in required_fixture_ids if item not in fixture_corpus]
if missing_ids:
    raise SystemExit(f'R4 deterministic race fixture IDs are not committed: {missing_ids}')

# Repair the generated validation workflow so the exact source graph it executes
# matches the fixed manifest: R4 acceptance imports the R4 seed, and concurrency
# runs the combined R4 race seed once before the 14-scenario R4 harness.
workflow = WORKFLOW.read_text()
trigger_anchor = "      - 'supabase/tests/cp3_r3_full_schema_seed.sql'\n"
trigger_additions = (
    "      - 'supabase/migrations/20260901023400_erp_v2_6_14d_cp3_r4_race_and_reversal_hardening.sql'\n"
    "      - 'supabase/tests/cp3_r4_full_schema_seed.sql'\n"
    "      - 'supabase/tests/cp3_r4_full_schema_race_seed.sql'\n"
    "      - 'supabase/tests/attendance_hpp_r4_full_schema_rollback.sql'\n"
    "      - 'scripts/cp3_render_r4_reviewed_rollback.py'\n"
    "      - 'scripts/test_cp3_render_r4_reviewed_rollback.py'\n"
    "      - 'docs/evidence/cp3_r4_source_hashes.json'\n"
)
if "      - 'supabase/tests/cp3_r4_full_schema_seed.sql'\n" not in workflow:
    if workflow.count(trigger_anchor) != 1:
        raise SystemExit('R4 workflow trigger anchor is not exact')
    workflow = workflow.replace(trigger_anchor, trigger_anchor + trigger_additions, 1)

env_anchor = '      CP3_R3_CONCURRENCY_REPORT: cp3-r3-concurrency-report.json\n'
if '      CP3_R4_CONCURRENCY_REPORT: cp3-r4-concurrency-report.json\n' not in workflow:
    if workflow.count(env_anchor) != 1:
        raise SystemExit('R4 workflow concurrency env anchor is not exact')
    workflow = workflow.replace(
        env_anchor,
        env_anchor + '      CP3_R4_CONCURRENCY_REPORT: cp3-r4-concurrency-report.json\n',
        1,
    )

old_race = """          psql \"$PGURL\" -v ON_ERROR_STOP=1 -f supabase/tests/cp3_r3_full_schema_race_seed.sql
          python scripts/cp3_r3_full_schema_concurrency.py | tee cp3-r3-concurrency.log
          python scripts/cp3_r4_full_schema_concurrency.py 2>&1 | tee cp3-r4-proof/r4-concurrency.log
"""
new_race = """          psql \"$PGURL\" -v ON_ERROR_STOP=1 -f supabase/tests/cp3_r4_full_schema_race_seed.sql 2>&1 | tee cp3-r4-proof/r4-race-seed.log
          python scripts/cp3_r4_full_schema_concurrency.py 2>&1 | tee cp3-r4-proof/r4-concurrency.log
"""
if old_race in workflow:
    workflow = workflow.replace(old_race, new_race, 1)
elif new_race not in workflow:
    raise SystemExit('R4 workflow race execution block is neither reviewed old nor repaired new shape')

workflow = workflow.replace(
    "report=json.loads(Path('cp3-r3-concurrency-report.json').read_text())",
    "report=json.loads(Path('cp3-r4-concurrency-report.json').read_text())",
)
workflow = workflow.replace(
    "where contractor_code like 'CP3R3-%'",
    "where contractor_code like 'CP3R3-%' or contractor_code like 'CP3R4-%'",
)
workflow = workflow.replace(
    "where payroll_number like 'CP3R3-%'",
    "where payroll_number like 'CP3R3-%' or payroll_number like 'CP3R4-%'",
)
workflow = workflow.replace(
    "where po_number like 'CP3R3-%'",
    "where po_number like 'CP3R3-%' or po_number like 'CP3R4-%'",
)
workflow = workflow.replace(
    '      - name: Upload non-secret CP3 R3 proof',
    '      - name: Upload non-secret CP3 R4 proof',
)
artifact_anchor = '            cp3-r3-final-reconciliation.json\n'
artifact_additions = '            cp3-r4-concurrency-report.json\n            cp3-r4-proof\n'
if '            cp3-r4-concurrency-report.json\n' not in workflow:
    if workflow.count(artifact_anchor) != 1:
        raise SystemExit('R4 workflow proof artifact anchor is not exact')
    workflow = workflow.replace(artifact_anchor, artifact_anchor + artifact_additions, 1)
WORKFLOW.write_text(workflow)

manifest = json.loads(MAN.read_text())
for rel in (
    'supabase/tests/cp3_r4_full_schema_seed.sql',
    'supabase/tests/cp3_r4_full_schema_race_seed.sql',
):
    manifest['files'].setdefault(rel, {})
for rel in manifest['files']:
    data = (ROOT / rel).read_bytes()
    manifest['files'][rel] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
MAN.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
print(json.dumps({
    'status': 'PASS',
    'fixture_strategy': 'deterministic committed target-faithful R4 seed plus R4 race seed',
    'two_session_scenarios': 14,
    'workflow_race_seed': 'cp3_r4_full_schema_race_seed.sql',
}, sort_keys=True))
