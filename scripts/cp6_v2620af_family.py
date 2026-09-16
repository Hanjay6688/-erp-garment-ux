#!/usr/bin/env python3
"""AF focused and combined business qualification; old business oracles unchanged."""
from __future__ import annotations
import argparse
import json
import os
import traceback
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg import sql

import cp6_ae_independent_audit as peer
import cp6_v2620ae_family as ae
import cp6_v2620ae_runtime as predecessor
import cp6_v2620af_runtime as runtime
from cp6_v2620af_build_sql import DIRTY_QUERY
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot

actors,base,prior = ae.actors,ae.base,ae.prior
expected_refusal,sql_body = ae.expected_refusal,ae.sql_body
ROOT = Path("cp6-proof/writer-af")
EXPECTED_URL = ae.EXPECTED_URL
CHECK = "V2620AF_OPENING_SOURCE_LINEAGE_MISMATCH"


def save(name,value):
    ROOT.mkdir(parents=True,exist_ok=True)
    (ROOT/(name+".json")).write_text(json.dumps(value,indent=2,default=str)+"\n")


def report(cur,day,blocked=False):
    actors.owner(cur)
    state=base.one(cur,"select erp.get_owner_financial_snapshot_v2(%s,%s,%s)",(day,day,day))
    check=cur.execute("select severity,issue_count from erp.run_v268_financial_report_checks() where check_name=%s",(CHECK,)).fetchone()
    actors.admin(cur)
    expected="BLOCKED" if blocked else "READY"
    if state["data_confidence"]["status"]!=expected or check is None or check[0]!="CRITICAL" or (check[1]>0)!=blocked:
        raise AssertionError("AF_REPORT_VERDICT_MISMATCH:"+json.dumps({"state":state,"check":check},default=str))
    return {"status":"PASS","expected":expected,"check":check,"snapshot":state}


def opening_fixture(cur,day):
    material,location,roll=peer.rolls.create_roll(cur,"af-source")
    header,items=peer.rolls.create_opening(cur,day,"af-source",material,location,[(roll,Decimal("10"),material)])
    actors.owner(cur)
    cur.execute("select erp.post_opening_balance(%s)",(header,))
    return header,items[0]


def original_repair(action):
    def case(cur,day):
        result=peer.opening_change(cur,day,action)
        if result["status"]!="CONTROL_PASS":
            raise AssertionError("AF_ORIGINAL_ORACLE_STILL_FAILS:"+json.dumps(result,default=str))
        if action!="DRAFT_MOVE" and (result["error"]["sqlstate"]!="P0001" or "status is POSTED" not in result["error"]["message"]):
            raise AssertionError("AF_REFUSAL_MUST_BE_PARENT_STATUS_GUARD")
        result["status"]="PASS"
        return result
    return case


def admission_dirty(action):
    def case(cur,day):
        # Execute the original ordinary AE operation, never forge a posted row.
        result=peer.opening_change(cur,day,action)
        if result["status"]!="BUG_PROVEN":
            raise AssertionError("AF_ADMISSION_REQUIRES_ORIGINAL_AE_COUNTEREXAMPLE")
        error=expected_refusal(cur,lambda:cur.execute(sql_body(runtime.MIGRATION),prepare=False),
                               "AF_PREEXISTING_OPENING_LINEAGE_REVIEW_REQUIRED")
        return {"status":"PASS","original_ae":result,"admission_refusal":error}
    return case


def admission_change(mutation,message):
    def case(cur,day):
        actors.admin(cur)
        cur.execute(mutation)
        return {"status":"PASS","refusal":expected_refusal(cur,lambda:cur.execute(sql_body(runtime.MIGRATION),prepare=False),message)}
    return case


def clean_admission(cur,day):
    actors.admin(cur)
    assert base.one(cur,DIRTY_QUERY)==0
    # Native installation uses the postgres migration owner, not the fixture
    # administrator. Preserve the capsule-owner assertion without widening it.
    cur.execute("set local role postgres")
    cur.execute(sql_body(runtime.MIGRATION),prepare=False)
    cur.execute("insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)",
                (runtime.STAMP,runtime.NAME,[runtime.MIGRATION.read_text()]))
    assert len(runtime.verified_successor(cur))==278
    cur.execute(sql_body(runtime.ROLLBACK),prepare=False)
    assert len(runtime.verify_predecessor(cur))==276
    cur.execute("reset role")
    return {"status":"PASS","clean_install_and_preuse_restore":True}


def detector(kind):
    def case(cur,day):
        header,item=opening_fixture(cur,day)
        report(cur,day)
        actors.admin(cur)
        if kind=="PARENT_MOVED":
            target=uuid.uuid4()
            cur.execute("insert into erp.opening_balance_headers(id,opening_number,opening_date,status) values(%s,%s,%s,'DRAFT')",(target,"AF-DET-"+target.hex,day))
            cur.execute("update erp.opening_balance_items set opening_id=%s where id=%s",(target,item))
        else:
            assignment={"QUANTITY":"qty=9","INPUT_COST":"unit_cost_snapshot=2.5","TYPE":"balance_type='WIP'"}[kind]
            cur.execute("update erp.opening_balance_items set "+assignment+" where id=%s",(item,))
        result=report(cur,day,blocked=True)
        result["synthetic_detector_control"]=True
        result["not_a_new_business_counterexample"]=True
        return result
    return case


def cash_lineage_control(cur,day):
    actors.admin(cur)
    cash=base.one(cur,"select id from erp.cash_accounts where is_active order by id limit 1")
    header,target,item,remaining=uuid.uuid4(),uuid.uuid4(),uuid.uuid4(),uuid.uuid4()
    actors.owner(cur)
    cur.executemany("insert into erp.opening_balance_headers(id,opening_number,opening_date,status) values(%s,%s,%s,'DRAFT')",
                    [(header,"AF-CASH-"+header.hex,day),(target,"AF-CASH-"+target.hex,day)])
    cur.executemany("insert into erp.opening_balance_items(id,opening_id,balance_type,cash_account_id,amount) values(%s,%s,'CASH_BANK',%s,%s)",
                    [(item,header,cash,Decimal('5.25')),(remaining,header,cash,Decimal('7.75'))])
    cur.execute("select erp.post_opening_balance(%s)",(header,))
    report(cur,day)
    actors.admin(cur)
    cur.execute("update erp.opening_balance_items set opening_id=%s where id=%s",(target,item))
    result=report(cur,day,blocked=True)
    result.update(synthetic_detector_control=True,nonempty_original_header=True)
    return result


def other_destination(cur,day,posted_source):
    material,location,roll=peer.rolls.create_roll(cur,"af-destination")
    target,items=peer.rolls.create_opening(cur,day,"af-destination",material,location,[(roll,Decimal("10"),material)])
    actors.owner(cur)
    cur.execute("select erp.post_opening_balance(%s)",(target,))
    material2,location2,roll2=peer.rolls.create_roll(cur,"af-origin")
    origin,orig_items=peer.rolls.create_opening(cur,day,"af-origin",material2,location2,[(roll2,Decimal("10"),material2)])
    actors.owner(cur)
    if posted_source: cur.execute("select erp.post_opening_balance(%s)",(origin,))
    before=peer.opening_observation(cur,origin,orig_items[0])
    result=peer.attempt(cur,"update erp.opening_balance_items set opening_id=%s where id=%s",(target,orig_items[0]))
    after=peer.opening_observation(cur,origin,orig_items[0])
    if not result["refused"] or result["error"]["sqlstate"]!="P0001" or "status is POSTED" not in result["error"]["message"] or before!=after:
        raise AssertionError("AF_POSTED_DESTINATION_NOT_PROTECTED")
    report(cur,day)
    return {"status":"PASS",**result,"posted_source":posted_source}


def shared_contract(allowed):
    def case(cur,day):
        actors.admin(cur)
        cur.execute("create table erp.cp6_af_contract_parent(id uuid primary key,status text)")
        cur.execute("create table erp.cp6_af_contract_child(id uuid primary key,parent_id uuid references erp.cp6_af_contract_parent(id),amount numeric)")
        cur.execute(sql.SQL("create trigger cp6_af_contract before insert or update or delete on erp.cp6_af_contract_child for each row execute function erp.guard_child_by_parent_status('cp6_af_contract_parent','parent_id',{})").format(sql.Literal(",".join(allowed))))
        cur.execute("grant select,insert,update,delete on erp.cp6_af_contract_parent,erp.cp6_af_contract_child to authenticated")
        p,q,closed,child=uuid.uuid4(),uuid.uuid4(),uuid.uuid4(),uuid.uuid4()
        cur.executemany("insert into erp.cp6_af_contract_parent values(%s,%s)",[(p,allowed[0]),(q,allowed[-1]),(closed,"POSTED")])
        actors.owner(cur)
        cur.execute("insert into erp.cp6_af_contract_child values(%s,%s,1)",(child,p))
        cur.execute("update erp.cp6_af_contract_child set parent_id=%s,amount=2 where id=%s",(q,child))
        assert cur.rowcount==1
        result=peer.attempt(cur,"update erp.cp6_af_contract_child set parent_id=%s where id=%s",(closed,child))
        assert result["refused"] and result["error"]["sqlstate"]=="P0001"
        actors.owner(cur)
        cur.execute("delete from erp.cp6_af_contract_child where id=%s",(child,))
        assert cur.rowcount==1
        # Construct a locked origin only as a trigger contract control.
        actors.admin(cur)
        cur.execute("insert into erp.cp6_af_contract_child values(%s,%s,1)",(child,closed))
        for statement,params in (("update erp.cp6_af_contract_child set parent_id=%s where id=%s",(p,child)),
                                 ("delete from erp.cp6_af_contract_child where id=%s",(child,))):
            result=peer.attempt(cur,statement,params)
            assert result["refused"] and result["error"]["sqlstate"]=="P0001"
        return {"status":"PASS","allowed_statuses":allowed,"synthetic_contract_control":True,
                "ordinary_business_bug_count":0,"checks":5}
    return case


def wiring(cur,day):
    actors.admin(cur)
    rows=cur.execute("""select n.nspname,c.relname,t.tgname,pg_get_triggerdef(t.oid)
      from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace
      where not t.tgisinternal and t.tgfoid='erp.guard_child_by_parent_status()'::regprocedure
      order by n.nspname,c.relname,t.tgname""").fetchall()
    expected=json.loads(Path("docs/evidence/cp6-af-family-disposition.json").read_text())["native_trigger_definitions"]
    assert json.loads(json.dumps(rows))==expected
    return {"status":"PASS","native_trigger_consumers":len(rows),"exact_ae_wiring_preserved":True}


def phase_cases(phase):
    if phase=="crossflow": return ae.crossflow_cases()
    if phase=="admission":
        return (("CLEAN_INSTALL_RESTORE",clean_admission),
                ("ORIGINAL_MOVE",admission_dirty("MOVE")),
                ("ORIGINAL_MOVE_AND_EDIT",admission_dirty("MOVE_AND_EDIT")),
                ("WRONG_FUNCTION",admission_change("alter function erp.guard_child_by_parent_status() set work_mem='64MB'","AF_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH")),
                ("WRONG_ACL",admission_change("grant execute on function erp.guard_child_by_parent_status() to authenticated","AF_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH")),
                ("WRONG_PLATFORM",admission_change("update supabase_migrations.schema_migrations set statements=array['wrong'] where name='erp_v2_6_20ae_cp6_opening_roll_integrity'","AF_REQUIRES_EXACT_AE_PLATFORM_CAPSULE")),
                ("MISSING_MARKER",admission_change("delete from erp.schema_migrations where version='v2.6.20ae'","AF_REQUIRES_EXACT_AE_WITHOUT_AF_RESIDUE")))
    if phase=="focused":
        cases=[("ORIGINAL_"+a,original_repair(a)) for a in ("SAME_PARENT_EDIT","DELETE","MOVE","MOVE_AND_EDIT","DRAFT_MOVE")]
        cases += [("DRAFT_TO_POSTED",lambda c,d:other_destination(c,d,False)),("POSTED_TO_POSTED",lambda c,d:other_destination(c,d,True)),("SHARED_WIRING",wiring)]
        cases += [("SHARED_CONTRACT_"+str(n),shared_contract(a)) for n,a in enumerate([("DRAFT",),("DRAFT","CALCULATED","REVIEW"),("OPEN","IN_PROGRESS","PARTIAL")])]
        cases += [("AE_"+name,fn) for name,fn in ae.phase_cases("successor")]
        return tuple(cases)
    if phase=="detector":
        return tuple((name,detector(name)) for name in ("PARENT_MOVED","QUANTITY","INPUT_COST","TYPE")) + (("MULTILINE_CASH_LINEAGE",cash_lineage_control),) + tuple(("AE_"+n,fn) for n,fn in ae.phase_cases("detector"))
    raise AssertionError(phase)


def run_phase(phase):
    head,tree=runtime.verify_audit_source()
    if os.environ.get("PGURL")!=EXPECTED_URL or os.environ.get("CP6_AF_FAMILY_CONFIRM")!="postgres":
        raise AssertionError("AF_EXACT_DISPOSABLE_TARGET_REQUIRED")
    result=dict(format="CP6_AF_FAMILY_V1",phase=phase,status="INCOMPLETE",head=head,tree=tree,
                run_id=os.environ.get("GITHUB_RUN_ID"),hosted_database_used=False,
                http_ui_reachability_proven=False,production_go=False,cases={})
    save(phase,result)
    with psycopg.connect(EXPECTED_URL.replace("postgres:postgres@","supabase_admin:postgres@")) as connection,connection.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
        untouched=actors.boundary(cur)
        if phase=="admission":
            assert len(runtime.verify_predecessor(cur))==276
            catalog,boundary=function_catalog(cur),snapshot(cur)
            assert len(catalog)==533 and len(boundary["tables"])==220
            save("AE_COMPLETE_CATALOG",catalog);save("AE_COMPLETE_BOUNDARY",boundary)
        else: assert len(runtime.verified_successor(cur))==278
        original_catalog=function_catalog(cur)
        usage=base.one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")
        result["schema_usage_fixture_grant"]=not usage
        if not usage: cur.execute("grant usage on schema erp to authenticated")
        cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps({"sub":base.OPERATOR_AUTH,"role":"authenticated"}),))
        base.load_fixture_foundation(cur);actors.admin(cur)
        day=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3)
        prior.set_open_period(cur,date(2026,8,31) if phase=="crossflow" else day-timedelta(days=2))
        for name,fn in phase_cases(phase):
            actors.admin(cur);before=actors.boundary(cur)
            cur.execute("savepoint af_case")
            try: record=fn(cur,day)
            except Exception as exc: record=dict(status="FAIL",error=str(exc),traceback=traceback.format_exc())
            finally:
                cur.execute("rollback to savepoint af_case");actors.admin(cur);cur.execute("release savepoint af_case")
            record["full_boundary_restored"]=actors.boundary(cur)==before
            if not record["full_boundary_restored"]: record["status"]="FAIL"
            result["cases"][name]=record;save(phase,result)
            print(json.dumps(dict(phase=phase,case=name,status=record["status"],error=record.get("error"))),flush=True)
        actors.admin(cur)
        result["function_catalog_unchanged"]=function_catalog(cur)==original_catalog
        connection.rollback();cur.execute("set local timezone='Asia/Jakarta'")
        result["unseeded_boundary_restored"]=actors.boundary(cur)==untouched
        result["schema_usage_restored"]=base.one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")==usage
        connection.rollback()
    result["passed"]=sum(r["status"]=="PASS" for r in result["cases"].values())
    result["failed"]=len(result["cases"])-result["passed"]
    if result["failed"]==0 and len(result["cases"])==len(phase_cases(phase)) and all(result[k] for k in ("function_catalog_unchanged","unseeded_boundary_restored","schema_usage_restored")):
        result["status"]="PASS"
    save(phase,result)
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--phase",choices=("admission","focused","detector","crossflow"),required=True)
    args=p.parse_args()
    try: result=run_phase(args.phase)
    except Exception as exc:
        result=dict(status="FAIL",error=str(exc),traceback=traceback.format_exc(),production_go=False)
        save(args.phase,result)
    print(json.dumps({k:v for k,v in result.items() if k!="cases"},default=str),flush=True)
    raise SystemExit(0 if result["status"]=="PASS" else 1)
