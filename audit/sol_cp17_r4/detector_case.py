"""One safe recost-state counterfixture; never disables a trigger or guard."""
from hashlib import sha256
import json
from pathlib import Path
import sys
from decimal import Decimal

ROOT=Path(__file__).resolve().parent
PRODUCT=ROOT.parents[2]/"auditor"
sys.path.insert(0,str(PRODUCT/"scripts"))
import cp6_bd_probe as bd

ID="SOL_R4_D01_MATERIAL_RECOST_STATE_PLUS1"
TARGET="run_v255_material_cost_integrity_checks:MATERIAL_RECOST_GL_STATE_DRIFT"


def detector_rows(cur):
    out=[]
    for function in bd.bcp.DETECTORS:
        bd.api.admin(cur);bd.chain.production.owner(cur)
        rows=cur.execute("select * from erp."+function+"()").fetchall()
        bd.api.admin(cur)
        out.extend(dict(function=function,check_name=name,severity=severity,issue_count=int(count),details=details)for name,severity,count,details in rows)
    return out


def counts(rows):
    values={r["function"]+":"+r["check_name"]:r["issue_count"] for r in rows}
    assert len(values)==len(rows),"SOL_DETECTOR_DUPLICATE_IDENTITIES"
    return values


def cases(cur,today):
    def state_plus_one():
        seen=dict(case_id=ID,oracle_origin="SOL_DOCUMENT_LEVEL_ONE_MATERIAL_DRIFT_UNIT",fixture_origin="ACCEPTED_NATIVE_THREE_RECEIPT_CUT_INVOICE_WRITERS",guard_or_trigger_changed=False)
        try:
            bd.api.admin(cur)
            old={str(r[0])for r in cur.execute("select id from erp.materials")}
            books_before=bd.d07_books(cur)
            # Three receipt documents10 each, one physical unit cut from each,
            # late final12 each: total WIP36 and supplier obligation36.
            seen["lawful_fixture"]=bd.d07_path(cur,today,"STACKED",n=3,p0="10.00",p1="12.00")
            bd.api.admin(cur)
            books_after=bd.d07_books(cur)
            seen["book_deltas"]={key:str(books_after[key]-books_before[key])for key in books_before}
            assert Decimal(seen["book_deltas"]["wip"])==36 and Decimal(seen["book_deltas"]["obligation"])==-36 and Decimal(seen["book_deltas"]["material"])==0,seen["book_deltas"]
            fresh={str(r[0])for r in cur.execute("select id from erp.materials")}-old
            assert len(fresh)==1,("SOL_D01_FIXTURE_MATERIAL_COUNT",len(fresh))
            material=next(iter(fresh))
            state=cur.execute("select s.movement_id::text,s.applied_inventory_delta::text from erp.material_cost_revaluation_state s join erp.material_stock_movements m on m.id=s.movement_id where m.material_id=%s and m.source_type='CUTTING_GROUP' and abs(s.applied_inventory_delta)>.01 order by s.movement_id limit 1",(material,)).fetchone()
            assert state,"SOL_D01_NO_ORDINARY_RECOST_STATE"
            seen["material_id"],seen["movement_id"],seen["original_applied_inventory_delta"]=material,*state
            seen["before"]=detector_rows(cur)
            before=counts(seen["before"])
            assert seen["lawful_fixture"]["books_exact"] and before[TARGET]==0
            assert all(r["issue_count"]==0 for r in seen["before"]if r["severity"].upper()in("ERROR","CRITICAL")),"SOL_D01_BASELINE_NOT_CLEAN"
            cur.execute("savepoint sol_detector_state")
            try:
                bd.api.admin(cur)
                result=cur.execute("update erp.material_cost_revaluation_state set applied_inventory_delta=applied_inventory_delta+1 where movement_id=%s returning applied_inventory_delta::text",(state[0],)).fetchall()
                assert len(result)==1
                seen["changed_applied_inventory_delta"]=result[0][0]
                seen["during"]=detector_rows(cur)
            finally:
                cur.execute("rollback to savepoint sol_detector_state");bd.api.admin(cur)
                seen["after_rollback"]=detector_rows(cur)
            during,after=counts(seen["during"]),counts(seen["after_rollback"])
            assert set(before)==set(during)==set(after)
            changed={k:during[k]-before[k] for k in before if during[k]!=before[k]}
            seen["observed_count_deltas"]=changed
            assert changed=={TARGET:1},("SOL_D01_UNEXPECTED_ALARM_UNITS",changed)
            assert before==after,"SOL_D01_DETECTORS_NOT_RESTORED"
            restored=cur.execute("select applied_inventory_delta::text from erp.material_cost_revaluation_state where movement_id=%s",(state[0],)).fetchone()[0]
            assert restored==state[1]
            seen.update(status="PASS",counts_0_1_0=[before[TARGET],during[TARGET],after[TARGET]],all_nine_function_outputs_saved=True,all_other_detector_counts_unchanged=True)
            return seen
        finally:
            out=PRODUCT/"cp6-proof/t3"/(ID+"_OBSERVATIONS.json")
            out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(seen,indent=2,default=str)+"\n")
    return[(ID,state_plus_one)]
