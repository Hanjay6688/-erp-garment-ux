"""Prepared exact day5 replay on CP6 and the complete vendor41c composition.

No oracle/prerequisite repair is proposed. A known READY failure stays INCOMPLETE.
Execution requires the inherited disposable T3 runtime; no workflow is added.
"""
from pathlib import Path
from hashlib import sha256
from contextlib import contextmanager
import importlib.util
import json
import os
import subprocess
import sys
import traceback
import zipfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def original_gate():
    """Read exactly the retained failed Original, before any DB connection."""
    pins = json.loads((HERE / "SOURCE.json").read_bytes())["retained_original"]
    path = Path(os.environ["CP6_DAY5_CROSSFLOW_ORIGINAL"])
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            raw = archive.read(pins["entry"])
    else:
        raw = path.read_bytes()
    assert len(raw) == pins["bytes"] and sha256(raw).hexdigest() == pins["sha256"]
    actual = json.loads(raw)
    assert actual["qualification_commit"] == pins["head"]
    assert actual["status"] == "INCOMPLETE" and actual["cp6_restored"] and actual["advisor_gate"]
    for phase, counts in (("baseline", {"PASS": 124, "INCOMPLETE": 18}),
                          ("native", {"PASS": 112, "INCOMPLETE": 30})):
        assert actual[phase]["counts"] == counts
        for name in pins["case_ids"]:
            failed = actual[phase]["cases"][name]
            assert failed["status"] == "INCOMPLETE"
            assert "PAYROLL_ATTENDANCE_UNCOVERED" in failed["error"]
    return dict(pins, observed_status="INCOMPLETE", original_relabelled=False)


def execute():
    # Source-only invocation above never imports these modules or opens a DB.
    assert os.environ.get("CP6_ATTENDANCE_DAY5_CONFIRM") == "cp6_rollback"
    offline = load("day5_offline_admission", HERE / "preflight.py").check()
    retained = original_gate()
    import psycopg
    import cp7_p21_current_chain_rehearsal_probe as chain
    from cp7_vendor_receivable import composition as product
    from cp6_t3_aligned_install import advisors, advisor_delta
    from cp7_catalog_state import exact_public_catalog

    business = load("day5_exact_business", HERE / "cases.py")
    current = load("day5_current_runtime", ROOT / "scripts/current-analog-consumer-opening-qualification/probe.py")
    readonly = load("day5_readonly_installer", ROOT / "scripts/current-finance-readonly-integration-qualification/composition.py")
    roles = load("day5_role_cleanup", ROOT / "scripts/current-choice-finance-cron-qualification/restore_roles.py")
    advisor = load("day5_current_advisor", ROOT / "scripts/current-choice-preparation-native-qualification/advisor_review.py")
    stream = load("day5_streamed_data", ROOT / "scripts/current-factory-initial-stage/stream_data.py")
    control = chain.helper.control
    previous, native, package, core, p09 = chain.previous, control.native, chain.package, chain.core, chain.p09
    database, drill, dump = current.database, current.drill, current.dump
    _, _, _, _, catalog = product.runtime()
    # Existing retained-parent source admissions may require their Original dirs.
    sources = product.sources()
    report = dict(label=business.LABEL, status="INCOMPLETE", source_declaration=dict(
        offline=offline, retained_original=retained, current_installation=sources),
        qualification_commit=subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
        required_case_ids=list(business.IDS), expected_case_count=5,
        original_oracle_changed=False, post_attendance_payroll_added=False,
        real_Auth_browser_claim=False, actual_cron_claim=False,
        new_business_case_credit=0, production_go=False, independent_acceptance=False)
    state = None
    fixtures = {}
    before = None
    dumped = False
    new_roles = set()
    dump_path = "/tmp/current_cp6_attendance_day5_pre.dump"
    output = ROOT / "cp6-proof/t3" / (business.LABEL + ".json")

    def cases(cur, today):
        phase = "current" if state is not None else "baseline"
        selected = business.cases(cur, today, current=state is not None,
                                  evidence=fixtures.setdefault(phase, {}))
        assert tuple(name for name, _ in selected) == business.IDS
        return selected

    def verify(cur):
        assert state is not None
        with control.product_catalog(cur):
            return product.verify(cur, state)

    @contextmanager
    def strict_originals():
        old = native.r1.OUT
        native.r1.OUT = output.parent / "strict-groups-day5"
        try:
            yield
        finally:
            native.r1.OUT = old

    with stream.bound(catalog) as streaming:
        try:
            assert drill.SOURCE == database.SOURCE == "cp6_rollback"
            assert drill.CONTAINER == "supabase_db_cp5-local"
            report["baseline_advisors"] = advisors(package.boundary.PG)
            with psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
                assert conn.info.host in ("127.0.0.1", "localhost")
                assert cur.execute("select current_database()").fetchone() == (database.SOURCE,)
                assert streaming["original"](cur) == streaming["candidate"](cur)
                p09.wip.policy.bf.verified(cur)
                before_roles = database._roles(cur)
                baseline_catalog = catalog._portable(catalog._catalog_rows(cur))
                baseline_data = catalog._data(cur)
                before = previous.restore_state.capture(cur, package.boundary.snapshot, core.predecessor.public_state, p09.functions)
                conn.rollback()
            pre_data = drill.data_hashes(database.SOURCE)
            pre_profile = database._database_profile(database.SOURCE)
            dump.dump(database.SOURCE, dump_path)
            dumped = True

            def restore(cur_phase):
                restored = database._restore(dump_path, database.SOURCE, pre_profile)
                assert restored["only_pg_cron_errors"] and not restored["unexplained"]
                assert drill.data_hashes(database.SOURCE) == pre_data
                with psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
                    cleanup = roles.restore_roles(cur, before_roles, new_roles, database._roles)
                    conn.commit()
                    assert catalog._portable(catalog._catalog_rows(cur)) == baseline_catalog
                    assert catalog._data(cur) == baseline_data
                    p09.wip.policy.bf.verified(cur)
                    conn.rollback()
                report[cur_phase] = dict(restore=restored, roles=cleanup, all22_ALLrows_ALLsequences_equal=True)

            with strict_originals(), exact_public_catalog(native, retain_raw=True):
                report["baseline"] = native.strict_group(business.LABEL + "_BASELINE", cases, p09.wip.policy.bf.verified)
            assert report["baseline"]["complete_boundary_restored"]
            restore("between_phases_restore")
            with psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
                report["install_boundary_lock"] = current.acquire_boundary(cur)
                prior = readonly.install(cur)
                prior = product.parent().install_delta(cur, prior)
                state = product.install_delta(cur, prior)
                report["focused_preuse_removal"] = product.rollback_delta_preuse(cur, state)
                state = product.install_delta(cur, prior)
                control.STATE = dict(installed_catalog=state["after"])
                report["complete_installed_verification"] = product.verify(cur, state)
                report["verified_predecessor_info_manifest"] = core.predecessor_info_manifest(cur)
                report["current_private_info_authority"] = advisor.capture(cur)
                new_roles = database._roles(cur) - before_roles
                conn.commit()
            report["advisors_with_cp7"] = advisors(package.boundary.PG)
            with strict_originals(), exact_public_catalog(native, retain_raw=True):
                report["native"] = native.strict_group(business.LABEL, cases, verify)
            with psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
                current.acquire_boundary(cur)
                data, rows = catalog._data(cur), catalog._catalog_rows(cur)
                if data != state["preuse_data_and_sequences"]:
                    try:
                        product.rollback_delta_preuse(cur, state)
                    except ValueError as error:
                        assert str(error) == product.USED_ERROR
                    else:
                        raise AssertionError("DAY5_USED_INVERSE_NOT_REFUSED")
                    assert catalog._data(cur) == data and catalog._catalog_rows(cur) == rows
                    report["used_guard_refused_before_DDL"] = True
                conn.rollback()
        except Exception as error:
            report.update(error=str(error), traceback=traceback.format_exc())
        finally:
            if before is not None and dumped:
                try:
                    restore("final_restore")
                    with psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
                        report["cp6_restored"] = previous.restore_state.prove(cur, before, package.boundary.snapshot, core.predecessor.public_state, p09.functions, report)
                        conn.rollback()
                    report["baseline_advisors_equal"] = advisors(package.boundary.PG) == report["baseline_advisors"]
                    if "advisors_with_cp7" in report:
                        delta = advisor_delta(advisors(package.boundary.PG), report["advisors_with_cp7"])
                        report["advisor_delta"] = delta
                        report["advisor_disposition"] = advisor.review(delta, report["verified_predecessor_info_manifest"], report["current_private_info_authority"], core.advisor_disposition)
                        report["advisor_gate"] = report["advisor_disposition"]["gate"] and report["baseline_advisors_equal"]
                    else:
                        report["advisor_gate"] = report["baseline_advisors_equal"]
                except Exception as error:
                    report.update(restore_error=str(error), restore_traceback=traceback.format_exc(), cp6_restored=False, advisor_gate=False)
            drill.docker("rm", "-f", dump_path, check=False)
            report["seed_prerequisite_preparation"] = fixtures
            report["case_status_comparison"] = {name: {phase: report.get(key, {}).get("cases", {}).get(name, {}).get("status") for phase, key in (("baseline", "baseline"), ("current", "native"))} for name in business.IDS}
            report["observed_execution_count"] = sum(sum(report.get(key, {}).get("counts", {}).values()) for key in ("baseline", "native"))
            report["all_ten_executions_PASS"] = all(report.get(key, {}).get("counts") == {"PASS": 5} for key in ("baseline", "native"))
            if report["all_ten_executions_PASS"] and not report.get("error") and report.get("cp6_restored") and report.get("advisor_gate") and report.get("final_restore", {}).get("all22_ALLrows_ALLsequences_equal"):
                report["status"] = "PASS"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, indent=2, default=str) + "\n")
            print(json.dumps({key: report.get(key) for key in ("label", "status", "observed_execution_count", "cp6_restored", "advisor_gate", "error", "restore_error")}, default=str))
    return report


if __name__ == "__main__":
    if sys.argv[1:] == ["--preflight"]:
        print(json.dumps(load("day5_preflight_only", HERE / "preflight.py").check(), indent=2))
    else:
        result = execute()
        raise SystemExit(0 if result["status"] == "PASS" else 1)
