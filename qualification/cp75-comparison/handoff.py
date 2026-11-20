"""Assemble the per-document expected and measured comparison and identify generated IDs on each path."""
import argparse
import json
from pathlib import Path
from compare import compare, read, business, OLD, TARGET

def per_case(label, expected, clean, upgrade):
    return {"case":label,"expected":expected,"clean":clean,"upgrade":upgrade,"equal":clean==upgrade==expected}


def main(clean, upgrade, output, *, target=TARGET, predecessor=OLD):
    summary=compare(clean,upgrade,target=target,predecessor=predecessor)
    ch,uh=read(clean,"factory-posted")["history"],read(upgrade,"upgrade-after")["history"]
    clean_doc,up_doc=read(clean,"old-documents"),read(upgrade,"old-documents")
    def ids(h,d):
        ap=h["accounts_payable"]
        return {"sale_30":d["sales"][0],"sale_16":d["sales"][1],"sale_4":d["sales"][2],"SKU":d["sku"],
                "supplier_purchase":d["purchase"],"supplier_payment_original":d["original_payment"],
                "supplier_payment_replacement":d["replacement"],"original_payment_journal":ap["original_journal"],
                "reversal_of_payment_journal":ap["inverse"],"operator_A":d["actors"][0],"operator_B":d["actors"][1],
                **{"reader_"+role:subject for role,subject in d.get("readers",{}).items()},
                "saved_plan":h["draft_id"],"snapshot":h["snapshot_id"],"snapshot_job":h["job_id"],
                "publication":h["published"]["id"],"production_snapshot":h["production_id"]}
    c,u=ids(ch,clean_doc),ids(uh,up_doc)
    assert c.keys()==u.keys() and all(c.values()) and all(u.values())
    assert len(set(c.values()))==len(c) and len(set(u.values()))==len(u)
    summary["generated_ids"]={tag:{"clean":c[tag],"upgrade":u[tag],"basis":"same document, actor or snapshot role in the common fixture sequence"} for tag in c}
    summary["generated_dates"]={tag:{"clean":ch["document_dates"][tag],"upgrade":uh["document_dates"][tag],
        "basis":"independently posted in each lane; exact persisted dates compared within each lane across migration and recovery"} for tag in ch["document_dates"]}
    a,b=business(ch),business(uh)
    checked=[]
    for field,expected in (("paid","255"),("outstanding","745"),("cash_change","-255")):
        checked.append(per_case("supplier:"+field,expected,a["saldo"][field],b["saldo"][field]))
    for i,(sold,ar,cost,total) in enumerate([("16","320","96","416"),("4","80","24","104")]):
        for field,expected,ca,up in [
            ("available after posting","0",a["stok"]["available"],b["stok"]["available"]),
            ("sold",sold,a["stok"]["sales"][i]["sold"],b["stok"]["sales"][i]["sold"]),
            ("AR",ar,a["saldo"]["sales"][i]["ledger"]["AR_CUSTOMER"],b["saldo"]["sales"][i]["ledger"]["AR_CUSTOMER"]),
            ("HPP",cost,a["hpp"][i]["movement"],b["hpp"][i]["movement"]),
            ("journal debit",total,a["saldo"]["sales"][i]["debit"],b["saldo"]["sales"][i]["debit"]),
            ("journal credit",total,a["saldo"]["sales"][i]["credit"],b["saldo"]["sales"][i]["credit"])]:
            checked.append(per_case("sale "+sold+" "+field,expected,ca,up))
    for name,expected in (("fg","15"),("wip","40"),("need","85"),("capacity","60"),("selected","2")):
        checked.append(per_case("Planner "+name,expected,ch["planner_values"][name],uh["planner_values"][name]))
    for name,wanted in (("sold",[0,0,0]),("untouched",[50,0,50]),("deferred_laundry",[15,0,15])):
        checked.append(per_case("FG card "+name,wanted,ch["panel_figures"]["inventory"][name]["quantities"],
                                uh["panel_figures"]["inventory"][name]["quantities"]))
    pc,pu=ch["panel_figures"],uh["panel_figures"]
    summary["panels"]={"clean":pc,"upgrade":pu,"equal":pc==pu}
    summary["per_case"]=checked
    summary["clean_restored_to_pre_events"]=read(clean,"factory-baseline-restored")
    summary["expected_supplier_correction_and_sales"]="independent historical receipt 44812294178"
    summary["production_go"]=False
    output.write_text(json.dumps(summary,sort_keys=True,indent=2)+"\n")
    if not (all(summary["six_areas"].values()) and all(c["equal"] for c in checked) and pc==pu and
            summary["clean_restored_to_pre_events"]["all_rows_and_sequences_equal"]):
        raise SystemExit("A measured business result differs")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for key in ("clean","upgrade","output"):
        p.add_argument(key,type=Path)
    a=p.parse_args()
    main(a.clean,a.upgrade,a.output)
