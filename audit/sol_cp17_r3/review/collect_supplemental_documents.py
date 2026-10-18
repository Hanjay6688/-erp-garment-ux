"""Index existing non-CP7-format CI results without executing a test or product."""
import collections
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "ci_receipts" / "sol_artifacts"


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def walk_playwright(suite):
    for spec in suite.get("specs", []):
        for test in spec.get("tests", []):
            yield spec, test
    for child in suite.get("suites", []):
        yield from walk_playwright(child)


def main():
    rows = []
    seen = {}
    for receipt in sorted(ARTIFACTS.glob("*/DOWNLOAD_RECEIPT.json")):
        rc = json.loads(receipt.read_text())
        for p in sorted((receipt.parent / "files").rglob("*.json")):
            if p.name not in ("NATIVE_REPORT.json", "results.json", "UI_PHONE_WIDTH.json"):
                continue
            x = json.loads(p.read_text())
            row = dict(run_id=rc["run_id"], artifact_id=rc["artifact_id"], path=str(p.relative_to(ROOT)), sha256=digest(p))
            key = (rc["run_id"], row["sha256"])
            row["exact_duplicate_of"] = seen.get(key)
            seen.setdefault(key, row["path"])
            if p.name == "UI_PHONE_WIDTH.json":
                row.update(kind="DEMO_MENU_WIDTH_CENSUS", menus=x["menus"], failed=x["failed"], viewport=x["viewport"],
                    qualification="Document width only, demo build. Does not prove all connected data flows, physical devices or every control reachable.")
            elif p.name == "NATIVE_REPORT.json":
                if x.get("contract") != "cp7.astra.timeline-reuse.v1":
                    row.update(kind="UNREVIEWED_NATIVE_REPORT_FORMAT", status=x.get("status"))
                else:
                    cases=x["cases"]
                    row.update(kind="OWN_EXECUTION_RETAINED_TIMELINE_COMPARATOR", counts=x["counts"],
                        cases=len(cases), nonidentical=[c["id"] for c in cases if not c["identical"]],
                        successes=sum(c["new_error"] == "NO_ERROR" for c in cases),
                        refusals=sum(c["new_error"] != "NO_ERROR" for c in cases),
                        original_error_differences=[c["id"] for c in cases if c["new_error"] != c["old_error"]],
                        mutation_controls=[dict(name=m["name"],caught=m["caught"]) for m in x["mutations"]],
                        oracle_origin=x["oracle_origin"], fixture_origin=x["fixture_origin"],
                        qualification="Exact predecessor equivalence, not 595 new independent business oracles; full_application=false.")
            else:
                cases=[(spec,test) for s in x["suites"] for spec,test in walk_playwright(s)]
                row.update(kind="PLAYWRIGHT_REPORT", stats=x["stats"], cases=len(cases),
                    counts=dict(collections.Counter(test["status"] for _,test in cases)), errors=len(x["errors"]),
                    case_ids=[dict(id=spec.get("id"), title=spec["title"], project=test.get("projectName"), status=test["status"],
                        attempts=len(test.get("results",[]))) for spec,test in cases],
                    qualification="Browser contract/demo tests. Exact copied report files are aliases, not additional executed cases.")
            rows.append(row)
    logs=[]
    for name,run_id in [("117732073486_offsite_backup.log",39146762489),("117732073837.log",39146762679)]:
        p=ROOT/"ci_receipts"/"sol_job_logs"/name
        if not p.exists(): continue
        groups=[];cases=[]
        for n,line in enumerate(p.read_text().splitlines(),1):
            line=re.sub(r"^\S+Z ","",line)
            if not line.startswith("{"): continue
            try: x=json.loads(line)
            except ValueError: continue
            if x.get("group") != "CP7_OFFSITE_BACKUP": continue
            if "planned" in x:
                groups.append(dict(line=n,planned=x["planned"],final=x["final"],source_unchanged=x["source_unchanged_by_the_backups"],status=x["status"]))
            if "case" in x: cases.append(dict(line=n,id=x["case"],status=x["status"]))
        logs.append(dict(run_id=run_id,path=str(p.relative_to(ROOT)),sha256=digest(p),groups=groups,cases=cases,
            counts=dict(collections.Counter(c["status"] for c in cases)), unique_ids=len({c["id"]for c in cases}),
            qualification="Two disposable targets (emulator/local); no claim about real offsite or hosted installation."))
    out=dict(scope="READ_ONLY_EXISTING_RESULT_DOCUMENTS",full_audit_pass=False,reports=rows,backup_logs=logs,
        build_log=dict(run_id=39146762599,job_id=117732073479,path="ci_receipts/sol_job_logs/117732073479.log",
            vitest_files=221,vitest_checks=1860,screen_activation_checks=6,
            qualification="Framework aggregate count from log; not 1860 individually inventoried business-case IDs. Source-contract checks and build are separate from Native runtime acceptance."))
    (ROOT/"SUPPLEMENTAL_DOCUMENT_REVIEW.json").write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    print("supplemental_reports",len(rows),"exact_copied_reports",sum(bool(r["exact_duplicate_of"])for r in rows),"backup_log_runs",len(logs))


if __name__ == "__main__":
    main()
