"""Read existing legacy Native documents. Never runs a provider or database."""
import collections
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"ci_receipts/sol_artifacts"


def case_map(value):
    return isinstance(value,dict) and bool(value) and all(isinstance(v,dict)and"status"in v for v in value.values())


def main():
    documents=[];ledger=[];aliases=[];seen={};checks=[]
    for rp in sorted(BASE.glob("*/DOWNLOAD_RECEIPT.json")):
        rc=json.loads(rp.read_text())
        for p in sorted((rp.parent/"files").rglob("*.json")):
            if p.name.startswith(("CP7","CP17","IDENTITY","SOL_")) or p.name in ("NATIVE_REPORT.json","results.json"):
                continue
            try:x=json.loads(p.read_text())
            except ValueError:continue
            if not isinstance(x,dict):continue
            candidates=[]
            if case_map(x.get("cases")):candidates.append(("/cases",x["cases"],x))
            if case_map(x.get("races")):candidates.append(("/races",x["races"],{}))
            if case_map(x.get("schedules")):candidates.append(("/schedules",x["schedules"],x))
            for k in ("temporal_races","master_races"):
                if case_map(x.get(k)):candidates.append(("/"+k,x[k],{}))
            if case_map(x):candidates.append(("/",x,{}))
            if not candidates:continue
            phase="HISTORICAL_BEFORE_DECLARED_REPAIR" if "_BEFORE"in p.name else "AFTER_DECLARED_REPAIR" if "_AFTER"in p.name else "NATIVE_STAGE_DECLARED_BY_ORIGINAL"
            doc=dict(run_id=rc["run_id"],artifact_id=rc["artifact_id"],path=str(p.relative_to(ROOT)),
                sha256=hashlib.sha256(p.read_bytes()).hexdigest(),status=x.get("status"),phase=phase,
                stage=x.get("stage"),complete_boundary_restored=x.get("complete_boundary_restored"),groups=[])
            for group,rows,node in candidates:
                semantic=hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                key=(rc["run_id"],phase,semantic)
                if key in seen:
                    aliases.append(dict(path=str(p.relative_to(ROOT)),group=group,alias_of=seen[key],counted_again=False));continue
                seen[key]=dict(path=str(p.relative_to(ROOT)),group=group)
                counts=dict(collections.Counter(r["status"]for r in rows.values()))
                errors=[];planned=node.get("planned_case_ids")
                if planned is not None and set(planned)!=set(rows):errors.append("PLANNED_IDS_DIFFER")
                if isinstance(node.get("counts"),dict)and node["counts"]!=counts:errors.append("COUNTS_DIFFER")
                if node.get("complete_boundary_restored")is False:errors.append("GROUP_BOUNDARY_NOT_RESTORED")
                doc["groups"].append(dict(path=group,rows=len(rows),counts=counts,errors=errors,planned_ids_available=planned is not None))
                for caseid,row in rows.items():
                    bad=[]
                    if row.get("full_boundary_restored")is False:bad.append("CASE_BOUNDARY_NOT_RESTORED")
                    if row.get("public_schema_unchanged")is False:bad.append("PUBLIC_CHANGED")
                    if bad:checks.append(dict(run_id=rc["run_id"],case=caseid,errors=bad))
                    item=dict(run_id=rc["run_id"],artifact_id=rc["artifact_id"],path=str(p.relative_to(ROOT)),group=group,
                        phase=phase,id=caseid,status=row["status"],raw_case_sha256=hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
                        full_boundary_restored=row.get("full_boundary_restored"),disposition=row.get("disposition"),supersedes=row.get("supersedes"))
                    if row["status"]not in("PASS","CONTROL_PASS"):
                        item["raw_nonpass"]=row
                    ledger.append(item)
            documents.append(doc)
    out=dict(scope="DOCUMENT_REVIEW_OF_ALREADY_EXECUTED_LEGACY_NATIVE_STAGES",full_audit_pass=False,
        oracle_origin="WRITER_OR_FROZEN_INHERITED; EXECUTION_INDEPENDENT_SOL",documents=documents,duplicate_group_documents=aliases,
        boundary_issues=checks,qualifications=[
            "Historical BEFORE documents intentionally precede a declared repair and are not current product acceptance.",
            "CONTROL_PASS and DATE_POLICY_REVIEW_REQUIRED remain their raw vocabulary; no green-job relabel.",
            "Native CP6 stage regression does not by itself apply the CP7 rate-revision bundle; full-F03 witnesses are separate.",
            "Group tables are not summed into an ERP completeness percentage. Same case IDs across phases/oracles are not new unique tests."])
    (ROOT/"LEGACY_DOCUMENT_REVIEW.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    (ROOT/"LEGACY_CASE_LEDGER.json").write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+"\n")
    print("legacy_documents",len(documents),"case_occurrences",len(ledger),"aliases",len(aliases),"boundary_issues",len(checks))


if __name__=="__main__":main()
