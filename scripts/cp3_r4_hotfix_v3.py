#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / 'scripts/cp3_r4_full_schema_concurrency.py'
WORKFLOW = ROOT / '.github/workflows/cp3-r4-full-schema-validation.yml'
MANIFEST = ROOT / 'docs/evidence/cp3_r4_source_hashes.json'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected one anchor, found {count}')
    return text.replace(old, new, 1)


text = HARNESS.read_text(encoding='utf-8')
if 'from psycopg.types.json import Jsonb' not in text:
    text = replace_once(
        text,
        'from psycopg.rows import dict_row\n',
        'from psycopg.rows import dict_row\nfrom psycopg.types.json import Jsonb\n',
        'Jsonb import',
    )
    text = replace_once(
        text,
        '    placeholders = ",".join(f"{arg} => %s" for arg, _ in supplied)\n    sql = f"select erp.{name}({placeholders}) as result"\n    row = one(conn, sql, tuple(value for _, value in supplied))\n',
        '    placeholders = ",".join(f"{arg} => %s" for arg, _ in supplied)\n    sql = f"select erp.{name}({placeholders}) as result"\n    adapted = tuple(Jsonb(value) if isinstance(value, (dict, list)) else value for _, value in supplied)\n    row = one(conn, sql, adapted)\n',
        'Jsonb adaptation',
    )

# Commit paid approval before the independent service_role bypass attempt.
text = replace_once(
    text,
    '''        accrual = one(admin, """
            select id::text from erp.journal_entries where source_type='PAYROLL_ATTENDANCE_ACCRUAL'
              and source_id=%s::uuid and status='POSTED'
        """, (pending_d["payroll_id"],))
        direct_service_role_reversal_denied(dsn, accrual["id"], "paid payroll approval accrual")
        admin.execute("select erp.post_payroll_payment(%s::uuid)", (pending_d["payroll_id"],))
''',
    '''        accrual = one(admin, """
            select id::text from erp.journal_entries where source_type='PAYROLL_ATTENDANCE_ACCRUAL'
              and source_id=%s::uuid and status='POSTED'
        """, (pending_d["payroll_id"],))
        admin.commit()
    direct_service_role_reversal_denied(dsn, accrual["id"], "paid payroll approval accrual")
    with connect(dsn) as admin:
        admin.execute("select erp.post_payroll_payment(%s::uuid)", (pending_d["payroll_id"],))
''',
    'paid approval commit boundary',
)

# Expected reverse-sewing failure must be isolated in a savepoint so owning pool
# cancellation can continue in the same outer transaction.
text = replace_once(
    text,
    '''        try:
            call_rpc(admin, "reverse_sewing_terminal_v1", {
                "event_id": sewing_a["id"], "reason": "CP3 R4 active pool reverse sewing regression",
                "request_id": str(uuid.uuid4()), "expected_version": sewing_a["row_version"],
            })
        except Exception as exc:
            if "ACTIVE" not in str(exc).upper() and "POOL" not in str(exc).upper():
                raise RaceFailure(f"reverse sewing active-pool regression failed for wrong reason: {exc}") from exc
        else:
            raise RaceFailure("reverse sewing consumed by ACTIVE pool unexpectedly succeeded")
        cancel_pool(admin, active["id"], "CP3 R4 work reversal cleanup")
''',
    '''        try:
            with admin.transaction():
                call_rpc(admin, "reverse_sewing_terminal_v1", {
                    "event_id": sewing_a["id"], "reason": "CP3 R4 active pool reverse sewing regression",
                    "request_id": str(uuid.uuid4()), "expected_version": sewing_a["row_version"],
                })
        except Exception as exc:
            if "ACTIVE" not in str(exc).upper() and "POOL" not in str(exc).upper():
                raise RaceFailure(f"reverse sewing active-pool regression failed for wrong reason: {exc}") from exc
        else:
            raise RaceFailure("reverse sewing consumed by ACTIVE pool unexpectedly succeeded")
        cancel_pool(admin, active["id"], "CP3 R4 work reversal cleanup")
''',
    'reverse sewing savepoint',
)
HARNESS.write_text(text, encoding='utf-8')

# Normalize the concurrency step so the existing R3 regression and new R4 harness
# are two separate complete shell commands even if the R3 command is multiline.
workflow = WORKFLOW.read_text(encoding='utf-8')
old_head = '366a4b2fb6f6daa0ef1d9d47a78c7b83a8c89ceb'
normalized_lines: list[str] = []
for line in workflow.splitlines():
    if old_head in line:
        stripped = line.strip()
        if stripped.startswith('EXPECTED_HEAD:'):
            indent = line[:len(line)-len(line.lstrip())]
            line = indent + 'EXPECTED_HEAD: ${{ github.sha }}'
        else:
            line = line.replace(old_head, '${GITHUB_SHA}')
    normalized_lines.append(line)
workflow = '\n'.join(normalized_lines) + '\n'

step_name = '      - name: Run committed full-schema seed and real two-connection source races\n'
start = workflow.find(step_name)
if start < 0:
    raise SystemExit('R4 workflow concurrency step not found')
next_step = workflow.find('\n      - name:', start + len(step_name))
if next_step < 0:
    raise SystemExit('R4 workflow next step after concurrency not found')
block = workflow[start:next_step]
block_lines = block.splitlines()
# Remove prior R4 command fragments.
block_lines = [line for line in block_lines if 'cp3_r4_full_schema_concurrency.py' not in line]
# Locate full R3 command including continuation lines.
cmd_start = next((i for i,line in enumerate(block_lines) if 'python' in line and 'cp3_r3_full_schema_concurrency.py' in line), None)
if cmd_start is None:
    raise SystemExit('R4 workflow executable R3 concurrency command not found')
cmd_end = cmd_start
while cmd_end < len(block_lines)-1 and block_lines[cmd_end].rstrip().endswith('\\'):
    cmd_end += 1
r3_command = block_lines[cmd_start:cmd_end+1]
r4_command = []
for line in r3_command:
    changed = line.replace('scripts/cp3_r3_full_schema_concurrency.py','scripts/cp3_r4_full_schema_concurrency.py')
    changed = changed.replace('cp3-r3-concurrency','cp3-r4-concurrency').replace('cp3_r3_concurrency','cp3_r4_concurrency')
    r4_command.append(changed)
block_lines[cmd_end+1:cmd_end+1] = r4_command
new_block = '\n'.join(block_lines)
workflow = workflow[:start] + new_block + workflow[next_step:]
WORKFLOW.write_text(workflow, encoding='utf-8')

# Refresh every fixed hash after the source-only hotfix.
manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
for rel in manifest['files']:
    data = (ROOT / rel).read_bytes()
    manifest['files'][rel] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n', encoding='utf-8')
print(json.dumps({'status':'PASS','refreshed_files':len(manifest['files'])}, sort_keys=True))
