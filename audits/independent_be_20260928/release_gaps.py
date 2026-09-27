#!/usr/bin/env python3
"""Independent build gate and unchanged-source install, on disposable CI only.

Modes:
  build     Run the literal official npm run build; record tsc/vite separately.
  bootstrap From the frozen base checkout, restore only the CP4.5a fixture.
  source55  From the audit checkout, install source v18..AV then dev AW..BE.
  inventory Verify source bytes and original ledger serialization, without a DB.

This runner imports no writer/peer business tests or their expected results.
The reused Applier is an installation primitive. Its closed/drained admission,
SQL guards, catalog pins, and source text are not patched or re-pinned.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "audit-results"
PRODUCT = "e09b0207f08b7736fad79e82fd81f1bf5dc1a85d"
BASE = "1bdca3766f7c9800d68295ff5122798060b8a05d"
BASE_TREE = "334629c626257b8b713826f491cdf62385d5299b"
PRIMARY = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
CLONE = "postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback"
FROZEN_WORKFLOW = ".github/workflows/cp6-full-schema-validation.yml"
T1_KEYS = ("aw", "ax", "ay", "az", "ba", "bb", "bc", "bd", "be")
EMPTY_LEDGER = {"18", "18a", "19", "19a", "19b"}
TRIM_LF_LEDGER = {"20", "20a", "20b", "20c", "20d", "20e", "20f"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str, cwd: Path = ROOT) -> bytes:
    return subprocess.check_output(["git", *args], cwd=cwd)


def save(name: str, report: dict) -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(json.dumps(report, indent=2, default=str) + "\n")


def identity() -> dict:
    changed = git("diff", "--name-only", PRODUCT, "--").decode().splitlines()
    assert all(
        path.startswith("audits/independent_be_20260928/")
        or path == ".github/workflows/be-independent-20260928.yml"
        for path in changed
    ), ("FROZEN_PRODUCT_DRIFT", changed)
    return {
        "frozen_product": PRODUCT,
        "audit_head": git("rev-parse", "HEAD").decode().strip(),
        "runner_sha256": sha(Path(__file__).read_bytes()),
        "production_go": False,
        "uat_used": False,
    }


def exact_file(path: Path, head: str = PRODUCT) -> bytes:
    relative = path.relative_to(ROOT).as_posix()
    data = path.read_bytes()
    assert data == git("show", f"{head}:{relative}"), ("SOURCE_BYTES_DRIFT", relative)
    return data


def frozen_workflow() -> tuple[bytes, dict]:
    import yaml

    data = git("show", f"{BASE}:{FROZEN_WORKFLOW}")
    return data, yaml.safe_load(data)


def run_logged(command: list[str], name: str, *, cwd: Path = ROOT,
               env: dict | None = None, timeout: int = 1200) -> dict:
    OUT.mkdir(exist_ok=True)
    log = OUT / name
    started = time.monotonic()
    error = None
    with log.open("wb") as stream:
        try:
            result = subprocess.run(command, cwd=cwd, env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=timeout)
            code = result.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            code = 124 if isinstance(exc, subprocess.TimeoutExpired) else 127
            error = type(exc).__name__
            stream.write((str(exc) + "\n").encode())
    data = log.read_bytes()
    return {
        "command": command,
        "exit_code": code,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "status": "PASS" if code == 0 else "FAIL",
        "execution_error": error,
        "log": name,
        "log_sha256": sha(data),
        "log_tail": data.decode(errors="replace")[-10000:],
    }


def build() -> int:
    report = dict(identity(), scope="Shared frozen repository official build gate",
                  status="INCOMPLETE", commands=[], bd_attribution="NOT_ESTABLISHED")
    try:
        package = json.loads(exact_file(ROOT / "package.json"))
        exact_file(ROOT / "package-lock.json")
        report["declared_scripts"] = {
            key: package["scripts"][key] for key in ("prebuild", "build", "postbuild")
        }
        report["node_version"] = subprocess.check_output(["node", "--version"], text=True).strip()
        report["npm_version"] = subprocess.check_output(["npm", "--version"], text=True).strip()
        # No npm lifecycle bypass, --ignore-scripts, source edits, or replacement
        # command. The official gate is recorded independently of compilation.
        official = run_logged(["npm", "run", "build"], "release-build-official.log")
        report["commands"].append(official)
        if official["exit_code"]:
            for executable, args, name in (
                ("tsc", ["-b"], "release-build-tsc.log"),
                ("vite", ["build"], "release-build-vite.log"),
            ):
                row = run_logged([str(ROOT / "node_modules" / ".bin" / executable), *args], name)
                row["scope"] = "Compilation diagnostic only; does not satisfy official npm gate"
                report["commands"].append(row)
        report["official_gate_passed"] = official["exit_code"] == 0
        report["source_ownership_drift_observed"] = "Browser RPC ownership drift" in official["log_tail"]
        report["status"] = "PASS" if report["official_gate_passed"] else "OFFICIAL_BUILD_GATE_FAILED"
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
    save("release-build.json", report)
    print(json.dumps({key: report.get(key) for key in
                      ("scope", "status", "official_gate_passed", "bd_attribution")}), flush=True)
    # A completed refusal is audit evidence, not an unhandled runner failure.
    return int(report["status"] == "INCOMPLETE")


def bootstrap() -> int:
    report = dict(identity(), scope="Fresh unaligned CP4.5a catalog/config fixture only",
                  status="INCOMPLETE", steps=[])
    try:
        assert Path.cwd() != ROOT, "BOOTSTRAP_REQUIRES_SEPARATE_FROZEN_BASE_CHECKOUT"
        assert git("rev-parse", "HEAD", cwd=Path.cwd()).decode().strip() == BASE
        assert git("rev-parse", "HEAD^{tree}", cwd=Path.cwd()).decode().strip() == BASE_TREE
        assert os.environ.get("PGURL") == PRIMARY
        assert os.environ.get("CP6_DATABASE_CONTAINER") == "supabase_db_cp5-local"
        data, workflow = frozen_workflow()
        assert Path(FROZEN_WORKFLOW).read_bytes() == data
        report["frozen_workflow_sha256"] = sha(data)
        proof = Path("cp6-proof")
        proof.mkdir(exist_ok=True)
        names = (
            "Verify immutable CP4.5a catalog/config bootstrap",
            "Restore exact CP4.5a schema and allowlisted configuration",
        )
        steps = workflow["jobs"]["validate-full-schema"]["steps"]
        env = os.environ.copy()
        env.update(workflow["env"])
        env["GITHUB_SHA"] = BASE
        for index, name in enumerate(names):
            selected = [step for step in steps if step.get("name") == name]
            assert len(selected) == 1
            code = selected[0]["run"]
            script = proof / f"independent-source55-bootstrap-{index}.sh"
            script.write_text(code)
            row = run_logged(["bash", str(script)], f"source55-bootstrap-{index}.log",
                             cwd=Path.cwd(), env=env)
            row.update(name=name, code_sha256=sha(code.encode()))
            report["steps"].append(row)
            save("source55-bootstrap.json", report)
            if row["exit_code"]:
                report["status"] = "BOOTSTRAP_REFUSED"
                return 1
        for name in ("CP45A_CATALOG_BOOTSTRAP_VERIFICATION.json", "CP45A_RESTORED_BOUNDARY.json"):
            report[name] = json.loads((proof / name).read_text())
        report["status"] = "READY_CLEAN_CP45A"
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
    finally:
        save("source55-bootstrap.json", report)
        print(json.dumps({"source55_bootstrap": report["status"]}), flush=True)
    return int(report["status"] != "READY_CLEAN_CP45A")


def inventory() -> list[dict]:
    _, workflow = frozen_workflow()
    applies = [step["run"].split("\nset +e\n", 1)[0]
               for step in workflow["jobs"]["validate-full-schema"]["steps"]
               if step.get("name", "").startswith("Apply ")]
    paths = [path for path in sorted((ROOT / "supabase/migrations").glob("*.sql"))
             if path.name[:14] > "20260902185106"]
    assert len(paths) == 55 and "_20av_" in paths[-1].name
    rows = []
    for path in paths:
        data = exact_file(path)
        relative = path.relative_to(ROOT).as_posix()
        stamp, name = path.stem.split("_", 1)
        version = re.fullmatch(r"erp_v2_6_([0-9]+[a-z]*)_.+", name).group(1)
        ledger_mode = "WHOLE_SOURCE"
        if version in EMPTY_LEDGER or version in TRIM_LF_LEDGER:
            # Preserve the recorded native bootstrap's ledger serialization.
            # These affect ledger metadata only; executable source is unchanged.
            matching = [code for code in applies if relative in code]
            assert len(matching) == 1, ("AMBIGUOUS_FROZEN_LEDGER_CONTRACT", relative)
            if version in EMPTY_LEDGER:
                assert "array[]::text[]" in matching[0]
                ledger_mode = "EMPTY_ARRAY_AS_FROZEN_WORKFLOW"
            else:
                assert "base64.b64encode(p[:-1])" in matching[0] and data.endswith(b"\n")
                ledger_mode = "SOURCE_WITHOUT_LAST_LF_AS_FROZEN_WORKFLOW"
        rows.append(dict(kind="source_migration", file=relative, stamp=stamp, name=name,
                         version="v2.6." + version, bytes=len(data), sha256=sha(data),
                         closed_admission="PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE" in data.decode(),
                         ledger_mode=ledger_mode))
    assert sum(row["closed_admission"] for row in rows) == 8
    for key in T1_KEYS:
        path = ROOT / "supabase/dev" / f"cp6_{key}_t1_family.sql"
        data = exact_file(path)
        assert b"PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE" not in data
        assert b"supabase_migrations.schema_migrations" not in data
        assert f"values('v2.6.20{key}'".encode() in data
        rows.append(dict(kind="dev_t1", file=path.relative_to(ROOT).as_posix(),
                         version="v2.6.20" + key, bytes=len(data), sha256=sha(data),
                         closed_admission=False, ledger_mode="NO_PLATFORM_ROW_IN_DEV_T1"))
    return rows


def expected_statements(row: dict, text: str) -> list[str]:
    if row["ledger_mode"] == "EMPTY_ARRAY_AS_FROZEN_WORKFLOW":
        return []
    if row["ledger_mode"] == "SOURCE_WITHOUT_LAST_LF_AS_FROZEN_WORKFLOW":
        assert text.endswith("\n")
        return [text[:-1]]
    assert row["ledger_mode"] == "WHOLE_SOURCE"
    return [text]


def database_state(url: str) -> dict:
    import psycopg

    with psycopg.connect(url) as conn:
        conn.read_only = True
        database, user, server = conn.execute(
            "select current_database(),current_user,current_setting('server_version')").fetchone()
        versions = [row[0] for row in conn.execute("select version from erp.schema_migrations order by version")]
        ledger = []
        for stamp, name, statements in conn.execute(
                "select version,name,statements from supabase_migrations.schema_migrations order by version"):
            ledger.append(dict(stamp=stamp, name=name, statements_count=len(statements or []),
                               statements_sha256=None if statements is None else sha("\n".join(statements).encode())))
        return dict(database=database, user=user, server_version=server,
                    application_versions=versions, application_count=len(versions),
                    platform_ledger=ledger, platform_count=len(ledger),
                    auth_users=conn.execute("select count(*) from auth.users").fetchone()[0],
                    app_users=conn.execute("select count(*) from erp.app_users").fetchone()[0],
                    audit_rows=conn.execute("select count(*) from erp.audit_logs").fetchone()[0],
                    admission_open=conn.execute("select datallowconn from pg_database where datname=current_database()").fetchone()[0])


def source55() -> int:
    report = dict(identity(), scope="Independent unchanged source55 plus dev AW..BE install",
                  status="INCOMPLETE", files=[], guards_changed=False, hosted_alignment_used=False,
                  repinned_release_package_used=False, business_test_verdict_reused=False)
    primary_before = None
    try:
        import psycopg

        assert os.environ.get("PGURL") == PRIMARY
        assert os.environ.get("CP6_MAINTENANCE_CONFIRM_DATABASE") == "cp6_rollback"
        assert os.environ.get("CP6_DATABASE_CONTAINER") == "supabase_db_cp5-local"
        rows = inventory()
        report["inventory"] = rows
        # Only the installer primitive is reused. No package capture/build or
        # business-test module is called; the immutable source SQL is supplied.
        sys.path.insert(0, str(ROOT / "scripts"))
        from cp6_t3_release_package import Applier

        applier = Applier(CLONE, os.environ["CP6_ADMISSION_CONTROL_PGURL"])
        primary_before = database_state(PRIMARY)
        before = database_state(CLONE)
        report["before"] = before
        assert before["database"] == "cp6_rollback" and before["user"] == "postgres"
        assert before["server_version"].startswith("17.6")
        assert before["application_count"] == 48 and before["platform_count"] == 63
        assert "v2.6.17a" in before["application_versions"]
        assert not any(row["version"] in before["application_versions"] for row in rows)
        assert before["auth_users"] == before["app_users"] == before["audit_rows"] == 0
        assert before["admission_open"]
        for row in rows:
            current = dict(row, status="STARTED")
            report["files"].append(current)
            save("source55-install.json", report)
            started = time.monotonic()
            source = exact_file(ROOT / row["file"]).decode("utf-8")
            try:
                if row["kind"] == "dev_t1":
                    with psycopg.connect(CLONE, autocommit=True, application_name="independent-be-source55") as conn:
                        conn.execute(source, prepare=False)
                elif row["closed_admission"]:
                    # This unwraps only the source's reviewed outer transaction;
                    # every SQL admission, catalog and capsule guard still runs.
                    applier.install({"stamp": row["stamp"], "name": row["name"], "closed": True}, source)
                else:
                    with psycopg.connect(CLONE, autocommit=True, application_name="independent-be-source55") as conn:
                        conn.execute(source, prepare=False)
                        with conn.transaction():
                            conn.execute("insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)",
                                         (row["stamp"], row["name"], expected_statements(row, source)))
                with psycopg.connect(CLONE) as conn:
                    conn.read_only = True
                    assert conn.execute("select count(*) from erp.schema_migrations where version=%s", (row["version"],)).fetchone() == (1,)
                    if row["kind"] == "source_migration":
                        observed = conn.execute("select version,name,statements from supabase_migrations.schema_migrations where version=%s or name=%s",
                                                (row["stamp"], row["name"])).fetchall()
                        assert observed == [(row["stamp"], row["name"], expected_statements(row, source))], "SOURCE_LEDGER_CONTENT_MISMATCH"
                        current["exact_platform_statements_verified"] = True
                    assert conn.execute("select datallowconn from pg_database where datname=current_database()").fetchone() == (True,)
                current.update(status="INSTALLED", elapsed_seconds=round(time.monotonic() - started, 3))
                print(json.dumps({"source55": row["version"], "status": current["status"], "sha256": row["sha256"]}), flush=True)
            except Exception as exc:
                current.update(status="REFUSED", error_type=type(exc).__name__, error=str(exc),
                               sqlstate=getattr(exc, "sqlstate", None), traceback=traceback.format_exc())
                report["status"] = "REFUSED_UNCHANGED_SOURCE"
                report["refused_file"] = row["file"]
                print(json.dumps({"source55_refused": current}, default=str), flush=True)
                break
            finally:
                save("source55-install.json", report)
        report["after"] = database_state(CLONE)
        installed = [row for row in report["files"] if row["status"] == "INSTALLED"]
        report["source_migrations_installed"] = sum(row["kind"] == "source_migration" for row in installed)
        report["dev_t1_files_installed"] = sum(row["kind"] == "dev_t1" for row in installed)
        if len(installed) == 64:
            expected_versions = sorted(before["application_versions"] + [row["version"] for row in rows])
            assert report["after"]["application_versions"] == expected_versions
            assert report["after"]["platform_count"] == 118
            old_stamps = {row["stamp"] for row in before["platform_ledger"]}
            assert [row for row in report["after"]["platform_ledger"] if row["stamp"] in old_stamps] == before["platform_ledger"]
            report["status"] = "PASS_SOURCE55_PLUS_DEV_AW_BE"
        report["primary_marker_ledger_and_empty_state_unchanged"] = database_state(PRIMARY) == primary_before
        assert report["primary_marker_ledger_and_empty_state_unchanged"]
    except Exception as exc:
        report.update(status="INCOMPLETE", error=str(exc), traceback=traceback.format_exc())
    finally:
        save("source55-install.json", report)
        print(json.dumps({key: report.get(key) for key in
                          ("scope", "status", "source_migrations_installed", "dev_t1_files_installed", "refused_file")}), flush=True)
    return int(report["status"] == "INCOMPLETE")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "bootstrap", "source55", "inventory"))
    args = parser.parse_args()
    if args.mode == "inventory":
        report = dict(identity(), inventory=inventory(), status="SOURCE_BYTES_VERIFIED_RUNTIME_NOT_RUN")
        save("source55-inventory.json", report)
        print(json.dumps({"status": report["status"], "files": len(report["inventory"])}))
        return 0
    return {"build": build, "bootstrap": bootstrap, "source55": source55}[args.mode]()


if __name__ == "__main__":
    raise SystemExit(main())
