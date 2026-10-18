"""Classify existing non-PASS documents; preserves every raw status and source."""
import collections
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    rows=[]
    for r in json.loads((ROOT/"CASE_LEDGER_PARTIAL.json").read_text()):
        if r["status"]=="PASS":continue
        if r["category"]=="DIAGNOSTIC_LEGACY":
            kind="LEGACY_RUNTIME_OBSERVATION_ONLY"
            why="Readiness ran before CP7 RPC installation; raw INCOMPLETE retained, product_case_credit=0. Full-stack prefreeze31 is a separate PASS witness."
        elif r["business_day_rollover"]:
            kind="AUDITOR_TOOL_WIB_GROUP_DATE_CHANGED"
            why="Planned/before/after WIB dates differ. Initial outcome is retained; no product failure is inferred and no first result is relabelled PASS."
        else:
            kind="UNCLASSIFIED_INCOMPLETE";why="Requires manual disposition; no product PASS inferred."
        rows.append(dict(run_id=r["run_id"],artifact_id=r["artifact_id"],report=r["report"],group=r["group"],id=r["id"],
            raw_status=r["status"],category=r["category"],classification=kind,reason=why,business_day=r["business_day"],
            status_before_rollover=r["status_before_rollover"],raw_case_sha256=r["raw_case_sha256"],product_failure_proven=False))
    for r in json.loads((ROOT/"LEGACY_CASE_LEDGER.json").read_text()):
        if r["status"]in("PASS","CONTROL_PASS"):continue
        raw=r.get("raw_nonpass",{});fn=Path(r["path"]).name
        if r["phase"]=="HISTORICAL_BEFORE_DECLARED_REPAIR":
            kind="HISTORICAL_BEFORE_DECLARED_REPAIR"
            why="BE/AV capability or repair deliberately absent in BEFORE stage; AFTER results are separate. Original NO_ROUTE/COUNTEREXAMPLE/NOT_APPLICABLE remains unchanged."
        elif r["status"]=="DATE_POLICY_REVIEW_REQUIRED":
            kind="ACCEPTED_BY_DECISION_RAW_HOLD_RETAINED"
            why="Twelve calendar HOLD IDs retained; current T2 per_case_identity holds expected12/observed12/identical=true, with distinct C0/approved calendar oracles. Not relabelled PASS."
        elif fn=="NEW_CASES.json"and r["status"]=="COUNTEREXAMPLE"and raw.get("approved_oracle_20260924",{}).get("status")=="MATCH":
            kind="ACCEPTED_BY_DECISION"
            why="Eight frozen AS date oracles remain COUNTEREXAMPLE. Explicit owner24Sep approved_oracle matches8/8; HPP follows goods/sale and revaluation follows cutting, while invoice remains on E. C0 exact-date oracle is separate."
        elif fn=="NEW_CASES.json"and r["id"]=="ADJUSTMENT_DATE:False":
            kind="SUPERSEDED_BY_OWNER_RULE"
            why="Old adjustment assertion expects purchase day; ratified C0 D01.3 uses max(E, adjustment day) for value. APPROVED_ORACLE_B and C0 replacement witnesses are separate."
        elif fn=="AO_TRIAL.json"and r["status"]=="INCOMPLETE":
            kind="SUPERSEDED_BY_OWNER_RULE"
            why="Four frozen AO assertions expect invoice date for later production/revaluation. Ratified C0 D01.1-5 replacement checks the actual economic/recognition dates; raw INCOMPLETE retained."
        elif fn=="AR_SEQUENTIAL.json"and r["id"]=="ACCESSORY_CONNECTED_ZERO":
            kind="SUPERSEDED_BY_OWNER_RULE"
            why="Ordinary zero price lacks required FREE policy. Separate AR_SUPERSEDING ACCESSORY_CONNECTED_ZERO_REFUSED_BC_FREE_POLICY PASS references ERP-DEC02/M5023B; legal configured FREE is a distinct positive path."
        else:
            kind="UNCLASSIFIED_INCOMPLETE";why="Requires manual review; not attributed to product without further evidence."
        rows.append(dict(run_id=r["run_id"],artifact_id=r["artifact_id"],report=fn,path=r["path"],group=r["group"],id=r["id"],
            raw_status=r["status"],category=r["phase"],classification=kind,reason=why,raw_case_sha256=r["raw_case_sha256"],product_failure_proven=False))
    out=dict(scope="NONPASS_DISPOSITIONS_OF_EXISTING_RESULTS",full_audit_pass=False,raw_statuses_preserved=True,
        rows=rows,classification_counts=dict(collections.Counter(r["classification"]for r in rows)),
        raw_status_counts=dict(collections.Counter(r["raw_status"]for r in rows)),
        vocabulary_qualification="CONTROL_PASS is preserved separately in LEGACY_CASE_LEDGER, not a product failure or a renamed PASS.",
        whole_job_dispositions=[
            dict(run_id=39146521757,job_id=117731362035,raw_conclusion="failure",classification="AUDITOR_TOOL_WIB_GROUP_DATE_CHANGED",status="INCOMPLETE",new_run=False),
            dict(run_id=39146762479,raw_conclusion="failure",classification="AUDITOR_TOOL_CODEQL_BINDING",status="CLOSED_METADATA_Q1",qualification_run=39150692634,original_failure_preserved=True),
            dict(run_id=39146762759,job_id=117732074565,raw_conclusion="failure",classification="AUDITOR_TOOL_T3_HISTORICAL_IDENTITY_HOOK",status="CLOSED_METADATA_Q1",qualification_run=39150692618,original_failure_preserved=True),
        ])
    (ROOT/"NONPASS_DISPOSITIONS.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(dict(rows=len(rows),classes=out["classification_counts"],raw=out["raw_status_counts"])))
    for r in rows:
        if r["classification"]=="UNCLASSIFIED_INCOMPLETE":print("UNCLASSIFIED",r["run_id"],r["report"],r["id"],r["raw_status"])


if __name__=="__main__":main()
