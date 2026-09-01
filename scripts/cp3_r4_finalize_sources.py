#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


# 1. Harden generic RPC argument discovery in the real two-session harness.
harness_path = ROOT / "scripts/cp3_r4_full_schema_concurrency.py"
harness = harness_path.read_text(encoding="utf-8")
harness = replace_once(
    harness,
    "    lower = arg.lower()\n    aliases = [",
    """    lower = arg.lower()
    if "expected" in lower:
        if "policy" in lower and "expected_policy_id" in values:
            return True, values["expected_policy_id"]
        if "expected_version" in values:
            return True, values["expected_version"]
    if "period_id" in lower and "period_id" in values:
        return True, values["period_id"]
    if "preview" in lower and "p_preview_only" in values:
        return True, values["p_preview_only"]
    if "worker" in lower and "expected" in lower and "expected_version" in values:
        return True, values["expected_version"]
    aliases = [""",
    "R4 harness argument alias patch",
)
harness_path.write_text(harness, encoding="utf-8")

# 2. Grant the test role access only to the session-local ID table.
accept_path = ROOT / "supabase/tests/attendance_hpp_r4_full_schema_rollback.sql"
accept = accept_path.read_text(encoding="utf-8")
accept = replace_once(
    accept,
    "set local role service_role;",
    "grant select on cp3_r4_journals to service_role;\nset local role service_role;",
    "R4 acceptance temp-table grant",
)
accept_path.write_text(accept, encoding="utf-8")

# 3. Make ACL snapshot conversion explicit and portable.
migration_path = ROOT / "supabase/migrations/20260901023400_erp_v2_6_14d_cp3_r4_race_and_reversal_hardening.sql"
migration = migration_path.read_text(encoding="utf-8")
migration = replace_once(
    migration,
    "  p.proacl::text[],\n  pg_get_userbyid(p.proowner)",
    "  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a) end,\n  pg_get_userbyid(p.proowner)",
    "R4 ACL snapshot cast",
)
migration_path.write_text(migration, encoding="utf-8")

# 4. Derive the R4 workflow from the already-proven R3 full-schema workflow.
r3_workflow_path = ROOT / ".github/workflows/cp3-r3-full-schema-validation.yml"
r4_workflow_path = ROOT / ".github/workflows/cp3-r4-full-schema-validation.yml"
workflow = r3_workflow_path.read_text(encoding="utf-8")
workflow = workflow.replace("name: CP3 R3 Full-Schema Validation", "name: CP3 R4 Full-Schema Validation", 1)
workflow = workflow.replace(
    "cp3/hpp-attendance-sewing-terminal-r3-20260901",
    "cp3/hpp-attendance-sewing-terminal-r4-20260901",
)
workflow = workflow.replace(
    ".github/workflows/cp3-r3-full-schema-validation.yml",
    ".github/workflows/cp3-r4-full-schema-validation.yml",
)
workflow = workflow.replace("cp3-r3-full-schema-proof", "cp3-r4-full-schema-proof")
workflow = workflow.replace("cp3-r3-proof", "cp3-r4-proof")

pgvar_match = re.search(r'psql\s+"\$([A-Z][A-Z0-9_]*PG[A-Z0-9_]*)"', workflow)
pgvar = pgvar_match.group(1) if pgvar_match else "PGURL"
pgref = f'"${pgvar}"'

before_behavior = "      - name: Run target-faithful behavior, accounting, timezone, JSON, and rollback acceptance\n"
if before_behavior not in workflow:
    raise SystemExit("R4 workflow: R3 behavior-step anchor missing")
pre14d_steps = f"""      - name: Capture exact pre-14d function and ACL baseline
        shell: bash
        run: |
          set -euo pipefail
          mkdir -p cp3-r4-proof
          psql {pgref} -At -v ON_ERROR_STOP=1 <<'SQL' > cp3-r4-proof/pre14d_function_acl_snapshot.json
          select jsonb_build_object(
            'functions',jsonb_agg(jsonb_build_object(
              'identity',format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
              'definition_sha256',encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
              'acl',coalesce(p.proacl::text,'NULL'),
              'owner',pg_get_userbyid(p.proowner)
            ) order by p.proname,pg_get_function_identity_arguments(p.oid))
          )
          from pg_proc p join pg_namespace n on n.oid=p.pronamespace
          where n.nspname='erp' and p.proname in (
            'approve_payroll','set_contractor_hpp_policy_v1','reverse_work_completion','reverse_journal',
            'cancel_attendance_hpp_pool_v1','cancel_unpaid_payroll','reverse_paid_payroll'
          );
          SQL

      - name: Prove exact v2.6.14d byte-bound rollback renderer
        shell: bash
        run: |
          set -euo pipefail
          python scripts/test_cp3_render_r4_reviewed_rollback.py | tee cp3-r4-proof/r4-renderer-unit.log
          python scripts/cp3_render_r4_reviewed_rollback.py \\
            --output cp3-r4-proof/v2.6.14d.reviewed.rollback.sql \\
            | tee cp3-r4-proof/r4-renderer-result.json

      - name: Apply exact v2.6.14d on restored full schema
        shell: bash
        run: |
          set -euo pipefail
          psql {pgref} -v ON_ERROR_STOP=1 \\
            -f supabase/migrations/20260901023400_erp_v2_6_14d_cp3_r4_race_and_reversal_hardening.sql \\
            2>&1 | tee cp3-r4-proof/r4-migration-apply.log

"""
workflow = workflow.replace(before_behavior, pre14d_steps + before_behavior, 1)

benchmark_anchor = "      - name: Run bounded 2,000-destination validator benchmark on full schema\n"
if benchmark_anchor not in workflow:
    raise SystemExit("R4 workflow: benchmark anchor missing")
r4_accept_step = f"""      - name: Run CP3 R4 protected-journal and private-boundary acceptance
        shell: bash
        run: |
          set -euo pipefail
          psql {pgref} -v ON_ERROR_STOP=1 \\
            -f supabase/tests/attendance_hpp_r4_full_schema_rollback.sql \\
            2>&1 | tee cp3-r4-proof/r4-full-schema-acceptance.log

"""
workflow = workflow.replace(benchmark_anchor, r4_accept_step + benchmark_anchor, 1)

race_marker = "scripts/cp3_r3_full_schema_concurrency.py"
if workflow.count(race_marker) != 1:
    raise SystemExit(f"R4 workflow: expected one R3 concurrency command, found {workflow.count(race_marker)}")
lines = workflow.splitlines()
new_lines: list[str] = []
for line in lines:
    new_lines.append(line)
    if race_marker in line:
        indent = line[: len(line) - len(line.lstrip())]
        new_lines.append(indent + line.strip().replace(race_marker, "scripts/cp3_r4_full_schema_concurrency.py"))
workflow = "\n".join(new_lines) + "\n"

restore_anchor = "      - name: Restore baseline business data after race and prove zero residue\n"
if restore_anchor not in workflow:
    raise SystemExit("R4 workflow: restore-baseline anchor missing")
rollback_step = f"""      - name: Roll back exact v2.6.14d and prove byte-equivalent pre-14d restoration
        shell: bash
        run: |
          set -euo pipefail
          psql {pgref} -v ON_ERROR_STOP=1 \\
            -f cp3-r4-proof/v2.6.14d.reviewed.rollback.sql \\
            2>&1 | tee cp3-r4-proof/r4-reviewed-rollback-execution.log
          psql {pgref} -At -v ON_ERROR_STOP=1 <<'SQL' > cp3-r4-proof/post14d_rollback_function_acl_snapshot.json
          select jsonb_build_object(
            'functions',jsonb_agg(jsonb_build_object(
              'identity',format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
              'definition_sha256',encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
              'acl',coalesce(p.proacl::text,'NULL'),
              'owner',pg_get_userbyid(p.proowner)
            ) order by p.proname,pg_get_function_identity_arguments(p.oid))
          )
          from pg_proc p join pg_namespace n on n.oid=p.pronamespace
          where n.nspname='erp' and p.proname in (
            'approve_payroll','set_contractor_hpp_policy_v1','reverse_work_completion','reverse_journal',
            'cancel_attendance_hpp_pool_v1','cancel_unpaid_payroll','reverse_paid_payroll'
          );
          SQL
          cmp cp3-r4-proof/pre14d_function_acl_snapshot.json cp3-r4-proof/post14d_rollback_function_acl_snapshot.json
          psql {pgref} -At -v ON_ERROR_STOP=1 <<'SQL' | tee cp3-r4-proof/r4-rollback-residue.json
          select jsonb_build_object(
            'status',case when
              not exists(select 1 from erp.schema_migrations where version='v2.6.14d')
              and to_regclass('erp.cp3_r4_rollback_capsule') is null
              and to_regprocedure('erp._cp3_r4_reverse_journal_internal(uuid,text)') is null
              and to_regprocedure('erp._cp3_r4_active_pool_affects_contractor(uuid,date,date)') is null
              then 'PASS' else 'FAIL' end,
            'migration_marker',exists(select 1 from erp.schema_migrations where version='v2.6.14d'),
            'capsule',to_regclass('erp.cp3_r4_rollback_capsule'),
            'private_reverse',to_regprocedure('erp._cp3_r4_reverse_journal_internal(uuid,text)'),
            'active_pool_helper',to_regprocedure('erp._cp3_r4_active_pool_affects_contractor(uuid,date,date)')
          );
          SQL
          grep -F '"status" : "PASS"' cp3-r4-proof/r4-rollback-residue.json >/dev/null

"""
workflow = workflow.replace(restore_anchor, rollback_step + restore_anchor, 1)

# Verify fixed source hashes in the same job before any database work can be claimed.
source_anchor = "      - name: Prove exact 14c rollback renderer on full schema\n"
if source_anchor not in workflow:
    raise SystemExit("R4 workflow: source-boundary insertion anchor missing")
hash_step = """      - name: Verify fixed CP3 R4 source hashes and exact runtime head
        shell: bash
        run: |
          set -euo pipefail
          mkdir -p cp3-r4-proof
          python - <<'PY' | tee cp3-r4-proof/r4-fixed-source-hash-verification.json
          import hashlib,json,os,pathlib,subprocess
          manifest=json.loads(pathlib.Path('docs/evidence/cp3_r4_source_hashes.json').read_text())
          failures=[]
          actual={}
          for path,expected in manifest['files'].items():
              data=pathlib.Path(path).read_bytes()
              digest=hashlib.sha256(data).hexdigest()
              actual[path]={'sha256':digest,'bytes':len(data)}
              if digest!=expected['sha256'] or len(data)!=expected['bytes']:
                  failures.append(path)
          head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
          if head!=os.environ['GITHUB_SHA']:
              failures.append('GITHUB_SHA')
          result={'status':'PASS' if not failures else 'FAIL','head':head,'schema_fingerprint':manifest['schema_fingerprint'],'files':actual,'failures':failures}
          print(json.dumps(result,sort_keys=True))
          if failures: raise SystemExit(1)
          PY

"""
workflow = workflow.replace(source_anchor, hash_step + source_anchor, 1)
r4_workflow_path.write_text(workflow, encoding="utf-8")

# 5. Fixed machine-readable source manifest. It deliberately does not claim an
# audit verdict; the exact final head is bound at runtime by GITHUB_SHA.
source_files = [
    "supabase/migrations/20260901023000_erp_v2_6_14_attendance_hpp_sewing_terminal_foundation.sql",
    "supabase/migrations/20260901023100_erp_v2_6_14b_attendance_hpp_candidate_hardening.sql",
    "supabase/migrations/20260901023200_erp_v2_6_14c_attendance_hpp_uat_alignment.sql",
    "supabase/migrations/20260901023400_erp_v2_6_14d_cp3_r4_race_and_reversal_hardening.sql",
    "supabase/rollbacks/20260901023400_erp_v2_6_14d_cp3_r4_race_and_reversal_hardening.rollback.sql",
    "supabase/tests/attendance_hpp_r3_full_schema_rollback.sql",
    "supabase/tests/attendance_hpp_r3_validator_benchmark_rollback.sql",
    "supabase/tests/attendance_hpp_r4_full_schema_rollback.sql",
    "supabase/tests/cp3_r3_full_schema_seed.sql",
    "scripts/cp3_r3_full_schema_concurrency.py",
    "scripts/cp3_r4_full_schema_concurrency.py",
    "scripts/cp3_render_reviewed_rollback.py",
    "scripts/cp3_render_r4_reviewed_rollback.py",
    "scripts/test_cp3_render_r4_reviewed_rollback.py",
    ".github/workflows/cp3-r4-full-schema-validation.yml",
]
files: dict[str, dict[str, object]] = {}
for rel in source_files:
    data = (ROOT / rel).read_bytes()
    files[rel] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
manifest = {
    "format": "CP3_R4_FIXED_SOURCE_HASHES_V1",
    "writer": "CHAT_SOL_PRO",
    "base_sha": "bf3ce8e2821f120d8abd8788daf07f6da7c15459",
    "reviewed_r3_parent_sha": "366a4b2fb6f6daa0ef1d9d47a78c7b83a8c89ceb",
    "schema_fingerprint": "a0c59b96b3879edd28f3d8c57d0894a3",
    "migration_version": "v2.6.14d",
    "source_only": True,
    "uat_applied": False,
    "legacy_mutated": False,
    "independent_audit_pending": True,
    "files": files,
}
evidence = ROOT / "docs/evidence/cp3_r4_source_hashes.json"
evidence.parent.mkdir(parents=True, exist_ok=True)
evidence.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")

print(json.dumps({"status":"PASS","generated_workflow":str(r4_workflow_path.relative_to(ROOT)),"hashed_files":len(files)},sort_keys=True))
