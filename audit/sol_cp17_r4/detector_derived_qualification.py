"""Once-only safe recost-state detector qualification, audit files only."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parent
PRODUCT = ROOT.parents[2] / "auditor"
sys.path.insert(0, str(PRODUCT / "scripts"))
import psycopg
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
import cp6_t3_package_run as package
import cp7_cp17_fix_probe as cp17
import cp7_p09_procurement_probe as p09
import cp7_p21_full_rehearsal_probe as installer
import cp7_restore_state as restore_state
import detector_derived_controls
from detector_case import bd as detector_bd

OUT = PRODUCT / "cp6-proof/t3/SOL_R4_DERIVED_DETECTOR_CONTROLS.json"
MANIFEST = ROOT / "DERIVED_DETECTOR_PREEXECUTION_MANIFEST.json"


def verify(cur):
    return {"full_composition": installer.verify(cur), "cp17": cp17.verify(cur)}


def cases(cur,today):
    return detector_derived_controls.cases(cur,today)


def run():
    declaration = json.loads(MANIFEST.read_text())
    for path, digest in declaration["pinned_product_sources"].items():
        assert hashlib.sha256((PRODUCT / path).read_bytes()).hexdigest() == digest
    for path, digest in declaration["audit_tools"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    report = dict(label="SOL_R4_DERIVED_DETECTOR_CONTROLS", status="INCOMPLETE",
                  candidate_sha=declaration["candidate_sha"], candidate_tree=declaration["candidate_tree"],
                  manifest_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
                  expected_case_ids=[row["id"] for row in declaration["cases"]],
                  case_origins={row["id"]:dict(oracle_origin=row["oracle_origin"],fixture_origin=row["fixture_origin"]) for row in declaration["cases"]},
                  production_go=False, independent_acceptance=False, full_family_acceptance=False,
                  oracle_origin="SOL_ACTIVE_PREDICATES_AND_EXACT_ONE_UNIT_COUNTERFIXTURES", fixture_origin="NATIVE_ACCEPTED_STARTS_AND_EXPLICIT_ADMIN_MUTABLE_COUNTERFIXTURES",
                  defined_scope="Nine finite controls: seven derived/configuration sensitivity cases and two guard-prevention-only cases. All167rows each phase; no protected fact/ledger/guard/grant/trigger edits.")
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
            report["installed_runtime"] = verify(cur)
            definitions = {name:cur.execute("select pg_get_functiondef(to_regprocedure(%s))", ("erp." + name + "()",)).fetchone()[0] for name in detector_bd.bcp.DETECTORS}
            (PRODUCT / "cp6-proof/t3/SOL_R4_DERIVED_DETECTOR_DEFINITIONS.json").write_text(json.dumps(definitions, indent=2) + "\n")
            for name, expected_hash in declaration['active_detector_function_sha256'].items():
                assert hashlib.sha256(definitions[name].encode()).hexdigest() == expected_hash, ('SOL_DERIVED_ACTIVE_DETECTOR_DRIFT', name)
            extra = {name:cur.execute('select pg_get_functiondef(to_regprocedure(%s))', ('erp.'+name,)).fetchone()[0] for name in declaration['additional_active_expression_pins']}
            for name, fragments in declaration['additional_active_expression_pins'].items():
                assert all(fragment in extra[name] for fragment in fragments), ('SOL_DERIVED_ACTIVE_PREDICATE_DRIFT', name)
            (PRODUCT / 'cp6-proof/t3/SOL_R4_DERIVED_SOURCE_DEFINITIONS.json').write_text(json.dumps(extra,indent=2)+'\n')
            triggers = cur.execute("select c.relname,t.tgname,pg_get_triggerdef(t.oid) from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relname=any(%s) and not t.tgisinternal order by c.relname,t.tgname", (declaration['runtime_trigger_tables'],)).fetchall()
            (PRODUCT / 'cp6-proof/t3/SOL_R4_DERIVED_ACTIVE_TRIGGERS.json').write_text(json.dumps(triggers,indent=2)+'\n')
            conn.rollback()
        # Direct once-only Native entry point; no business-day retry wrapper.
        report["native"] = native._strict_group_once("SOL_R4_DERIVED_DETECTOR_CONTROLS", cases, verify)
        rows = report["native"].get("cases", {})
        report["counts"] = dict(Counter(row["status"] for row in rows.values()))
        report["observed_case_ids"] = list(rows)
        report['phase_manifest_binding'] = all(
            rows.get(case['id'], {}).get('status') == 'PASS' and
            {p['name']: p['observed_deltas'] for p in rows[case['id']].get('phases', [])} == case['expected_phases']
            for case in declaration['cases'])
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
        n = report.get("native", {})
        report["status"] = "PASS" if not report.get("error") and report.get("cp6_restored") is True and set(report.get("observed_case_ids", [])) == set(report["expected_case_ids"]) and report.get("counts") == {"PASS": 9} and report.get("phase_manifest_binding") is True and n.get("status") == "PASS" and n.get("complete_boundary_restored") is True and n.get("missing") == [] and not n.get("error") else "INCOMPLETE"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2, default=str) + "\n")
        print(json.dumps({key: report.get(key) for key in ("label", "status", "counts", "cp6_restored", "error")}), flush=True)
    return {"status": report["status"], "production_go": False, "independent_acceptance": False, "full_family_acceptance": False}


if __name__ == "__main__":
    package._writer_runtime = lambda browser_mode=False: run()
    package.run("install")
