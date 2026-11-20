"""Compare business facts between two CP7.5 receipts; keep exact IDs for all within-path checks."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path

TARGET = "deb596acb49e10ac66e0a1616a582ff74889146c0b59ee0d81ac7c2818397821"
OLD = "a3da0ecf21909731ab8474c54a7c91afb75bb58dd8b6042cc82314b20808dbd7"


def read(directory, name):
    return json.loads((directory / (name + ".json")).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def amount(value):
    number = Decimal(str(value))
    require(number.is_finite(), "Invalid financial value")
    return str(number.normalize()) if number % 1 else str(int(number))


def business(history):
    ap = history["accounts_payable"]
    pages = [line for page in ap["history_pages"] for line in page]
    require(len(pages) == len(set(pages)) == 27 and ap["selected_id"] in pages and ap["replacement"] in pages,
            "Supplier payment history is incomplete")
    require(ap["selected_id"] != ap["replacement"] and ap["original_status"] == "REVERSED" and
            bool(ap["inverse"]) and ap["original_journal"] != ap["inverse"], "Missing linked reversal or replacement")
    require(ap["all_stock_and_cost_same"], "Supplier stock or cost changed")
    doc = history["published"]
    parts = [doc["summary"], *doc["sections"]]
    report_hash = hashlib.sha256("\n".join(parts).encode()).hexdigest()
    require(bool(doc["id"]) and bool(doc["sections"]) and report_hash == doc["hash"], "Invalid stored report")
    require(history["draft"] == "SAVED" and all(history[key] for key in
            ("draft_id","snapshot_id","job_id","stored_snapshot","snapshot_identity")), "Stored Planner work is missing")
    money, stock, cost, history_links = [], [], [], []
    for invoice in history["sales"]:
        money.append({"ledger": {key:amount(value) for key,value in invoice["postings"].items()},
                      "debit":amount(invoice["debit"]), "credit":amount(invoice["credit"])})
        stock.append({"sold":amount(invoice["sold"]), "reserve":amount(invoice["reserve"])})
        # Lots can receive different UUIDs on independent installs. Retain all their quantities and unit costs.
        allocations = sorted([[amount(qty),amount(unit)] for _,qty,unit in invoice["allocations"]])
        cost.append({"movement": amount(invoice["fg_cost"]), "allocations":allocations})
        history_links.append(invoice["entries"])
    access = history["role_access"]
    require(set(access["matrix"]) >= {"OWNER","ADMIN","KEUANGAN"} and
            history["foreign_report"] == {"sqlstate":"42501","reason":"CP7_REPORT_UNAVAILABLE"},
            "Independent reads for the requested roles are missing")
    facts = {"saldo": {"paid":amount(ap["AP"]["paid"]),"outstanding":amount(ap["AP"]["remaining"]),
                      "cash_change":amount(ap["cash_delta"]),"sales":money},
             "stok": {"available":amount(history["available"]),"sales":stock},
             "hpp": cost,
             "histori": {"posted_journal_counts":history_links,"supplier_history_pages":list(map(len,ap["history_pages"])),
                         "reversal_and_replacement_linked":True,"draft":history["draft"],
                         "planner_values":history["planner_values"], "published_sections":len(doc["sections"]),
                         "stored_snapshot_pages":history["page_count"]},
             "hak_akses":access}
    require((facts["saldo"]["paid"], facts["saldo"]["outstanding"],facts["saldo"]["cash_change"]) ==
            ("255","745","-255"), "Supplier monetary reference differs")
    require(facts["stok"] == {"available":"0","sales":[{"sold":"16","reserve":"0"},{"sold":"4","reserve":"0"}]} and
            [i["movement"] for i in cost]==["96","24"] and history_links==[1,1], "Sales reference differs")
    require(money == [{"ledger":{"COGS":"96","FG_INVENTORY":"-96","AR_CUSTOMER":"320","SALES_REVENUE":"-320"},
                       "debit":"416","credit":"416"},
                      {"ledger":{"COGS":"24","FG_INVENTORY":"-24","AR_CUSTOMER":"80","SALES_REVENUE":"-80"},
                       "debit":"104","credit":"104"}], "Sales journals differ")
    return facts


def compare(clean, upgrade):
    factory=read(clean,"factory-posted")
    recovered=read(clean,"factory-restored")
    parent, current, reversal=(read(upgrade, name) for name in ("upgrade-before","upgrade-after","upgrade-restored"))
    require(factory["target"] == current["seal"] == recovered["full25"]["sha256"] == TARGET and
            recovered["full25"]["groups"] == 25 and parent["seal"] == reversal["origin_seal"] == OLD,
            "Versions or catalogue differ")
    require(parent["rows_sequences"] == current["rows_sequences"] and not current["changed_rows_or_sequences"] and
            current["history_equal"] and parent["history"] == current["history"] == reversal["history"],
            "Historic IDs, stored values, links, or row contents differ across the upgrade")
    restore = {"clean":recovered["raw_state_equal"] and recovered["history_equal"] and bool(recovered["physical_sha256"]),
               "upgrade":reversal["all_rows_sequences_equal"] and reversal["history_equal"] and bool(reversal["physical_sha256"])}
    require(all(restore.values()), "Missing physical recovery")
    a,b = business(factory["history"]),business(current["history"])
    differences = {key:{"clean":a[key],"upgrade":b[key]} for key in a if a[key] != b[key]}
    return {"target":TARGET,"six_areas":{"saldo":a["saldo"]==b["saldo"],"stok":a["stok"]==b["stok"],
            "hpp":a["hpp"]==b["hpp"],"histori":a["histori"]==b["histori"],"hak_akses":a["hak_akses"]==b["hak_akses"],
            "pemulihan":all(restore.values())}, "differences":differences,"source_factory":factory["origin"],
            "source_upgrade":parent.get("origin","see exact opening receipt"), "business_facts":a,
            "production_go":False}


if __name__ == "__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("clean",type=Path)
    cli.add_argument("upgrade",type=Path)
    cli.add_argument("output",type=Path)
    args=cli.parse_args()
    evidence=compare(args.clean,args.upgrade)
    args.output.write_text(json.dumps(evidence,sort_keys=True,indent=2)+"\n")
    if not all(evidence["six_areas"].values()):
        raise SystemExit("CP7.5 receipts differ")
