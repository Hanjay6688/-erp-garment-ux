#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAR = ROOT / 'scripts/cp3_r4_full_schema_concurrency.py'
SEED = ROOT / 'supabase/tests/cp3_r3_full_schema_seed.sql'
ACC = ROOT / 'supabase/tests/attendance_hpp_r4_full_schema_rollback.sql'
MAN = ROOT / 'docs/evidence/cp3_r4_source_hashes.json'

# The generated harness already contains deterministic target-faithful IDs and all
# required two-session orders. Verify the exact fixture contract instead of
# rewriting it through stale discovery anchors.
harness = HAR.read_text()
seed = SEED.read_text()
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

# IDs used by the harness must be created by the committed restored-schema
# acceptance/seed chain, never inferred from arbitrary hosted data.
fixture_corpus = seed + '\n' + acceptance
required_fixture_ids = (
    'a6000000-0000-0000-0000-000000000021',
    'a5000000-0000-0000-0000-000000000040',
    'a5000000-0000-0000-0000-000000000011',
    'a5000000-0000-0000-0000-000000000012',
)
missing_ids = [item for item in required_fixture_ids if item not in fixture_corpus]
if missing_ids:
    raise SystemExit(f'R4 deterministic race fixture IDs are not committed: {missing_ids}')

manifest = json.loads(MAN.read_text())
for rel in manifest['files']:
    data = (ROOT / rel).read_bytes()
    manifest['files'][rel] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
MAN.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
print(json.dumps({
    'status': 'PASS',
    'fixture_strategy': 'deterministic committed target-faithful IDs',
    'two_session_scenarios': 14,
}, sort_keys=True))
