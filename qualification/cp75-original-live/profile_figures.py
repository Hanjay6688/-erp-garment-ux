"""Read the same stock cards and stored operational work that the ERP panels consume."""
from decimal import Decimal

from psycopg import sql

import cp7_fg_cases as inventory
import cp7_p19_plan_v2_cases as plan


def ordered_opening(cur, items):
    by_id = {str(item["product"]):item for item in items}
    ordered = cur.execute("select id::text from erp.products where id=any(%s::uuid[]) order by lower(sku)",
                          (list(by_id),)).fetchall()
    assert len(ordered)==len(by_id)==2
    return [by_id[key] for key, in ordered]


def stock_card(cur, product, who):
    sku=cur.execute("select sku from erp.products where id=%s",(product,)).fetchone()[0]
    card=inventory.workspace(cur,{"sku":sku},who,show_zero=True)
    rows=card["page"]["rows"]
    return {"quantities":inventory.qty(card),"values":[{"state":x["valuation"]["state"],
             "unit_cost":x["valuation"]["unit_cost"],"value":x["valuation"]["value"]} for x in rows]}


def stamps(cur, table, doc_id):
    row=cur.execute(sql.SQL("select to_jsonb(d) from {} d where id=%s").format(sql.Identifier(*table)),(doc_id,)).fetchone()[0]
    return {k:row[k] for k in sorted(row) if k=="id" or k.endswith(("_at","_date"))}


def read(cur, f, document, snapshot):
    who=f["owner"]
    cards={key:stock_card(cur, product, who) for key,product in {
        "sold":f["row"]["product"],"untouched":f["control"],"deferred_laundry":f["deferred"]}.items()}
    assert cards["sold"]["quantities"]==[0,0,0]
    assert cards["untouched"]["quantities"]==[50,0,50]
    known=cards["untouched"]["values"]
    assert known and all(v["state"]=="KNOWN" and Decimal(v["unit_cost"])==6 for v in known)
    assert sum(Decimal(v["value"]) for v in known)==300
    unknown=cards["deferred_laundry"]
    assert unknown["quantities"]==[15,0,15] and unknown["values"]
    assert all(v["state"]=="UNKNOWN" and v["unit_cost"] is None and v["value"] is None for v in unknown["values"])
    production=plan.schedule.supply.read(cur,f["supply_id"],who)
    assert str(production["run_id"])==f["supply_id"]
    plan_options=plan.options(cur,f["plan_query"],who)
    assert (Decimal(plan_options["available_fg_pcs"]),Decimal(plan_options["needed_pcs"]),
            Decimal(plan_options["capacity_pcs"]))==(15,85,60)
    assert document["finance"]=="DEFERRED" and document["financial_source_hash"] is None and snapshot["financial_source"] is None
    timestamps={tag:stamps(cur,("erp","sales_headers"),f[key]) for tag,key in
                (("sale_30","warm"),("sale_16","left"),("sale_4","right"))}
    for key,doc_id in (("payment_original", f["fixture"]["target"]),("payment_replacement",f["replacement"])):
        timestamps[key]=stamps(cur,("erp","supplier_payments"),doc_id)
    semantic={"inventory":cards,"production":{"wip_status":production["wip"]["status"],"allocation_state":production["allocation_state"],
        "quantities":plan.schedule.supply.vector(production) if production["wip"]["status"]=="COMPLETE" else None},
        "planner":{"stock":plan_options["available_fg_pcs"],"need":plan_options["needed_pcs"],"capacity":plan_options["capacity_pcs"]},
        "finance":{"report_state":document["finance"],"published_financial_source":document["financial_source_hash"],
                   "operational_snapshot_finance":snapshot["financial_source"]}}
    return semantic,timestamps
