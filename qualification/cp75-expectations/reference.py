"""Read prior independent numeric observations as fixtures for CP7.5. No target database is evaluated here."""
import hashlib
import json
import os
import subprocess
import tempfile
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT.parent / "cp75-global-pair/origins.json").read_text())
WRITER = {"artifact":14660574034,"digest":"sha256:d51822b2f6057d5b097898be276df758fa9bf574cc402c94f516b05891907615"}
OUT = Path(os.environ["RUNNER_TEMP"]) / "cp75-expectations"
OUT.mkdir(exist_ok=True)


def original(pin, filename, folder):
    path = folder / (str(pin["artifact"]) + ".zip")
    with path.open("xb") as out:
        subprocess.run(["gh", "api", f'repos/{CONFIG["repository"]}/actions/artifacts/{pin["artifact"]}/zip'],
                       stdout=out, check=True, timeout=120)
    with path.open("rb") as src:
        assert "sha256:" + hashlib.file_digest(src, "sha256").hexdigest() == pin["digest"]
    with ZipFile(path) as archive:
        assert archive.testzip() is None
        name, = [s for s in archive.namelist() if Path(s).name == filename]
        return json.loads(archive.read(name))


def one_branch(obj, field):
    found = []
    def visit(node):
        if isinstance(node, dict):
            if field in node:
                found.append(node[field])
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)
    visit(obj)
    if len(found) != 1:
        raise ValueError(f"Expected one {field}, found {len(found)}")
    return found[0]


def verify_note(row, pcs, ar):
    postings = {"COGS": 6*pcs, "FG_INVENTORY": -6*pcs, "AR_CUSTOMER": ar, "SALES_REVENUE": -ar}
    observed = {k:Decimal(str(v)) for k,v in row["postings"].items()}
    assert observed == postings
    expected = {"entries": 1, "sold": pcs, "reserve": 0, "fg_cost": 6*pcs, "debit": ar + 6*pcs, "credit": ar + 6*pcs}
    assert all(Decimal(str(row[k])) == n for k,n in expected.items())
    return {**expected, "postings": postings}


def main():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        clean = original(CONFIG["inputs"]["bf_proof"], "clean-bf.json", folder)
        writer = original(WRITER, "clean-bf.json", folder)
        g14 = original(CONFIG["inputs"]["sale_fixture"], "AUD-G14.json", folder)
        race = original(CONFIG["inputs"]["auditor"], "sales-collision.json", folder)
        supplier = original({"artifact":14609391145,"digest":"sha256:cfa4cfd0f5e5dbaa2efcbbb7920f8147c3cd354aefc480cc1b9a1a089cea1fe0"}, "AUD-G01.json", folder)
    assert clean["source"] == clean["restored"] and writer["source"] == writer["restored"]
    for name in ("postgres", "cp6_rollback"):
        assert clean["source"][name] == writer["source"][name], name
    marks = one_branch(g14, "sales_operator_latency")
    totals = []
    for note in marks:
        n = note["distinct_lines"]
        assert n in (1,10,100) and note["authoritative_status"] == "POSTED" and note["retained_lines"] == n
        assert Decimal(str(note["stock_before"])) - Decimal(str(note["stock_after_draft"])) == n
        assert Decimal(str(note["stock_after_draft"])) == Decimal(str(note["stock_after_post"]))
        assert Decimal(str(note["net"])) == 20*n
        totals.append({"pcs":n, "draft_reserved":n,"posted":verify_note(note["journal"], n, 20*n)})
    assert [i["pcs"] for i in totals] == [1,10,100]
    final = one_branch(race, "final")
    assert final["available"] == 0
    lost = one_branch(race, "lost_reply")
    assert lost["operator_observed_responses"] == 0 and lost["committed_seen_by_other"] and lost["same_result"] and lost["identical_tables"] == 14
    commit=supplier["rounds"]["COMMIT"]
    abort=supplier["rounds"]["ABORT"]
    assert supplier["outcome"]=="PASS" and abort["before"]==abort["after"]
    before,after=commit["before"],commit["after"]
    assert [Decimal(x["AP"]["paid"]) for x in (before,after)]==[260,255]
    assert [Decimal(x["AP"]["remaining"]) for x in (before,after)]==[740,745]
    assert Decimal(after["cash_delta"])==-255 and after["original_status"]=="REVERSED"
    assert after["replacement"]==commit["writer_result"]["payment_id"] and after["inverse"]
    assert sum(len(p) for p in after["history_pages"])==27 and after["all_stock_and_cost_same"]
    result = {"classification":"prior independent observations for the future two-path comparison",
              "new_target_db_cases":0,"production_go":False,"BF":clean["source"],"sales":totals,
              "last_20_pcs":{"available":0,"a":verify_note(final["invoice_a"],16,320),"b":verify_note(final["invoice_b"],4,80),
                             "unread_reply":0,"identical_tables_after_retry":14},
              "supplier_correction":{"purchase":1000,"paid_before":260,"paid_after":255,"payable_before":740,"payable_after":745,
                                     "cash_delta_after":-255,"posted_history_rows_after":27,"linked_inverse_and_replacement":True,
                                     "stock_and_cost_unchanged":True,"aborted_edit_restored_exactly":True},
              "source_runs":[44800849536,44801431651,44710562666,44800195953,44691911184]}
    (OUT/"expected.json").write_text(json.dumps(result,indent=2)+"\n")
    print("CP75_EXPECTED "+json.dumps(result,separators=(",",":")),flush=True)


if __name__ == "__main__":
    main()
