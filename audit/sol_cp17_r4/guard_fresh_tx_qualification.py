"""Sol r4 functional qualification of the new no-assigned-transaction guard branch.

Only three valid legacy internal roles are exercised. This is not a race, Auth HTTP,
business-command or security-exploration suite. Each guard call has its own fresh
session, so a predecessor call cannot change the actual guard's initial txid state.
All fixture writes are confined to the existing disposable-copy runtime.
"""
import hashlib
import json
from pathlib import Path
import re
import sys
import traceback
import uuid

PRODUCT = Path(__file__).resolve().parents[3] / "auditor"
sys.path.insert(0, str(PRODUCT / "scripts"))

import psycopg
from psycopg import sql
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
import cp6_t3_package_run as package
import cp7_cp17_fix_probe as cp17
import cp7_f03_bundle as bundle
import cp7_p09_procurement_probe as p09
import cp7_p21_rehearsal_probe as installer
import cp7_restore_state as restore_state

IDS = tuple("SOL_R4_GUARD_FRESH_TX_" + role for role in ("OWNER", "ADMIN", "STAFF"))
SCHEMA = "audit_sol_r4_guard_fixture"
DATABASE = "cp6_auditor_race"  # Existing per-case disposable-copy carrier; race credit is explicitly zero.
OUT = PRODUCT / "cp6-proof/t3/SOL_R4_GUARD_FRESH_TX.json"
MANIFEST = Path(__file__).with_name("GUARD_FRESH_TX_PREEXECUTION_MANIFEST.json")


def one(cur, statement, args=()):
    return cur.execute(statement, args).fetchone()[0]


def fixture(tools, role):
    """Commit a synthetic app profile and private comparison functions before any measuring transaction starts."""
    subject, user = str(uuid.uuid4()), str(uuid.uuid4())
    with tools.connect() as conn, conn.cursor() as cur:
        tools.api.admin(cur)
        reviewed = bundle.internal_guard.verify(cur)
        actual = one(cur, "select pg_get_functiondef('erp.require_internal()'::regprocedure)")
        predecessor, probe = bundle.internal_guard.unpatched(actual)
        assert probe == bundle.internal_guard.probe(bundle.internal_guard.contexts(predecessor))
        body = one(cur, "select prosrc from pg_proc where oid='erp.require_internal()'::regprocedure")
        old_body, _ = bundle.internal_guard.unpatched(body)
        expected_body = bundle.sales.patched_internal(bundle.attendance_internal_body())
        assert old_body == expected_body, "SOL_R4_PREDECESSOR_BODY_DIFFERS"
        tables = bundle.internal_guard.contexts(predecessor)
        assert len(tables) == reviewed["tables"] == 10
        assert all(re.fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+", t) for t in tables)
        found = cur.execute("select id from erp.app_roles where role_code=%s and is_active", (role,)).fetchone()
        if found:
            profile = found[0]
        else:
            # The Native legacy STAFF field can be bound to a custom active profile, as existing P02 isolation fixtures do.
            assert role == "STAFF", "SOL_R4_REQUIRED_SEEDED_ROLE_MISSING"
            profile = uuid.uuid4()
            cur.execute("insert into erp.app_roles(id,role_code,role_name,is_system,is_protected,is_active)values(%s,%s,%s,false,false,true)",
                        (profile, "SOL_R4_TXID_" + profile.hex[:8].upper(), "Sol r4 valid STAFF fixture"))
        cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)values(%s,%s,%s,%s,%s,true)",
                    (user, subject, "Sol r4 fresh transaction " + role, role, profile))
        assert predecessor.count("FUNCTION erp.require_internal()") == 1
        baseline = predecessor.replace("FUNCTION erp.require_internal()", "FUNCTION " + SCHEMA + ".guard_before()", 1)
        cur.execute(sql.SQL("create schema {} authorization postgres").format(sql.Identifier(SCHEMA)))
        cur.execute(baseline, prepare=False)
        cur.execute(sql.SQL("alter function {}.guard_before() owner to postgres").format(sql.Identifier(SCHEMA)))
        # A private fixture bridge invokes the real product guard without granting extra access to Native schemas.
        cur.execute(sql.SQL("create function {}.guard_after()returns void language sql security definer set search_path=''as 'select erp.require_internal()'").format(sql.Identifier(SCHEMA)))
        cur.execute(sql.SQL("create function {}.role_now()returns text language sql security definer set search_path=''as 'select erp.current_app_role()'").format(sql.Identifier(SCHEMA)))
        for function in ("guard_after", "role_now"):
            cur.execute(sql.SQL("alter function {}.{}() owner to postgres").format(sql.Identifier(SCHEMA), sql.Identifier(function)))
        cur.execute(sql.SQL("revoke all on schema {} from public,anon,authenticated,service_role").format(sql.Identifier(SCHEMA)))
        cur.execute(sql.SQL("grant usage on schema {} to authenticated").format(sql.Identifier(SCHEMA)))
        cur.execute(sql.SQL("revoke all on all functions in schema {} from public,anon,authenticated,service_role").format(sql.Identifier(SCHEMA)))
        cur.execute(sql.SQL("grant execute on all functions in schema {} to authenticated").format(sql.Identifier(SCHEMA)))
        conn.commit()
        tools.api.admin(cur)
        before = package.boundary.snapshot(cur)
        public_before = native.public_state(cur)
        conn.rollback()
    return dict(subject=subject, tables=tables, before=before, public_before=public_before,
                current_definition=actual, current_sha256=hashlib.sha256(actual.encode()).hexdigest(),
                predecessor_sha256=hashlib.sha256(predecessor.encode()).hexdigest(), reviewed=reviewed)


def context_counts(tools, tables, pid, txid):
    """An independent admin reader observes this measuring backend; it cannot assign that backend's txid."""
    with tools.connect() as conn, conn.cursor() as cur:
        rows = {t: one(cur, sql.SQL("select count(*) from {} where backend_pid=%s and transaction_id=%s").format(
                            sql.Identifier(*t.split("."))), (pid, txid)) for t in tables}
        conn.rollback()
    assert set(rows.values()) == {0}, ("SOL_R4_UNEXPECTED_CONTEXT", rows)
    return rows


def measure(tools, f, role, variant, assigned):
    """Read-only guard invocation. This connection is never reused for another guard invocation."""
    with tools.connect() as conn, conn.cursor() as cur:
        cur.execute("select set_config('request.jwt.claims',%s,true)", (json.dumps({"sub": f["subject"], "role": "authenticated"}),))
        cur.execute("set session authorization authenticator")
        cur.execute("set role authenticated")
        session, current, pid, start = cur.execute("select session_user::text,current_user::text,pg_backend_pid(),txid_current_if_assigned()").fetchone()
        assert (session, current, start) == ("authenticator", "authenticated", None), "SOL_R4_NOT_A_FRESH_APPLICATION_SESSION"
        observed_role = one(cur, sql.SQL("select {}.role_now()").format(sql.Identifier(SCHEMA)))
        assert observed_role == role, ("SOL_R4_FIXTURE_ROLE_DIFFERS", role, observed_role)
        if assigned:
            one(cur, "select txid_current()")  # Explicitly declared control; no business data is written.
        before = one(cur, "select txid_current_if_assigned()")
        assert (before is not None) == assigned, ("SOL_R4_WRONG_PRECALL_TXID_STATE", before, assigned)
        contexts = context_counts(tools, f["tables"], pid, before)
        # Recheck after the independent observer, immediately before this guard call.
        immediate = one(cur, "select txid_current_if_assigned()")
        assert immediate == before
        function = "guard_before" if variant == "predecessor" else "guard_after"
        cur.execute(sql.SQL("select {}.{}()").format(sql.Identifier(SCHEMA), sql.Identifier(function))).fetchone()
        after = one(cur, "select txid_current_if_assigned()")
        conn.rollback()
    return dict(variant=variant, state="ASSIGNED_CONTROL" if assigned else "UNASSIGNED",
                session_user=session, current_user=current, legacy_app_role=observed_role, backend_pid=pid,
                txid_at_session_start=start, txid_immediately_before=immediate, txid_after=after,
                current_context_counts=contexts, outcome="ALLOW")


def case(tools, role):
    f = fixture(tools, role)
    observations = [measure(tools, f, role, variant, assigned)
                    for assigned in (False, True) for variant in ("predecessor", "actual")]
    assert len(observations) == 4 and all(r["outcome"] == "ALLOW" for r in observations)
    with tools.connect() as conn, conn.cursor() as cur:
        tools.api.admin(cur)
        assert package.boundary.snapshot(cur) == f["before"], "SOL_R4_GUARD_CHANGED_NATIVE_ROWS"
        assert native.public_state(cur) == f["public_before"], "SOL_R4_GUARD_CHANGED_PUBLIC_CATALOG"
        assert one(cur, "select pg_get_functiondef('erp.require_internal()'::regprocedure)") == f["current_definition"]
        conn.rollback()
    return dict(status="PASS", role=role, expected="ALLOW for both guard versions in both txid states",
                observations=observations, native_rows_unchanged_after_fixture=True, public_catalog_unchanged=True,
                actual_guard_definition_unchanged=True, actual_guard_sha256=f["current_sha256"],
                predecessor_guard_sha256=f["predecessor_sha256"], context_tables=f["reviewed"]["tables"],
                race_claim=False, Auth_HTTP_claim=False)


def functional_group():
    """Use existing copy/strict-row primitives directly, with no retry wrapper and no race claim."""
    report = dict(label="SOL_R4_GUARD_FRESH_TX", status="INCOMPLETE", cases={},
                  expected_case_ids=list(IDS), expected_guard_calls=12, race_case_credit=0, Auth_HTTP_case_credit=0)
    try:
        url = modes.copy_db(DATABASE)
        setup = modes.setup_copy(url, cp17.verify, False)
        tools = modes.RaceTools(url, setup["today"])
        planned = [(cid, lambda role=role: case(tools, role)) for cid, role in zip(IDS, ("OWNER", "ADMIN", "STAFF"))]
        def run_one(index, key, operation):
            if index:
                modes.copy_db(DATABASE)
                modes.setup_copy(url, cp17.verify, False)
            return operation()
        report["cases"], refusal = modes.strict_rows("SOL_R4_FUNCTIONAL_GUARD_FRESH_TX", planned, run_one, DATABASE, today=setup["today"])
        if refusal:
            report.update(refusal)
        report["copy_runtime"] = setup["runtime"]
    except Exception as error:
        report.update(error=str(error), traceback=traceback.format_exc())
    finally:
        report["database_remaining"] = modes.drop_db(DATABASE)
    report["counts"] = {state: sum(r.get("status") == state for r in report["cases"].values())
                        for state in sorted({r.get("status") for r in report["cases"].values()})}
    report["status"] = "PASS" if not report.get("error") and report["counts"] == {"PASS": 3} and set(report["cases"]) == set(IDS) and report["database_remaining"] == 0 else "INCOMPLETE"
    return report


def run():
    declaration = json.loads(MANIFEST.read_text())
    assert declaration["case_ids"] == list(IDS) and declaration["guard_calls"] == 12
    report = dict(label="SOL_R4_GUARD_FRESH_TX", status="INCOMPLETE", expected_case_count=3,
                  oracle_origin="SOL_NATIVE_INTERNAL_ROLE_CONTRACT_AND_R4_PREDECLARATION",
                  fixture_origin="SYNTHETIC_APP_PROFILES_ON_EXISTING_DISPOSABLE_COPY_RUNTIME",
                  declaration_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
                  source_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest(),
                  production_go=False, full_family_acceptance=False, independent_acceptance=False)
    installed = False
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
            p09.wip.policy.bf.verified(cur)
            before = restore_state.capture(cur, package.boundary.snapshot, native.public_state, p09.functions)
            conn.rollback()
            originals, installation = installer.install(cur)
            conn.commit()
            installed = True
            report["installation"] = installation
            report["installed_runtime"] = cp17.verify(cur)
            conn.rollback()
        report["functional"] = functional_group()
    except Exception as error:
        report.update(error=str(error), traceback=traceback.format_exc())
    finally:
        if installed:
            with psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
                installer.uninstall(cur, originals)
                conn.commit()
                report["cp6_restored"] = restore_state.prove(cur, before, package.boundary.snapshot, native.public_state, p09.functions, report)
                conn.rollback()
                p09.wip.policy.bf.verified(cur)
                conn.rollback()
        report["status"] = "PASS" if not report.get("error") and report.get("cp6_restored") and report.get("functional", {}).get("status") == "PASS" else "INCOMPLETE"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2, default=str) + "\n")
        print(json.dumps({k: report.get(k) for k in ("label", "status", "cp6_restored", "error")}), flush=True)
    return dict(status=report["status"], production_go=False, independent_acceptance=False, full_family_acceptance=False)


if __name__ == "__main__":
    package._writer_runtime = lambda browser_mode=False: run()
    package.run("install")
