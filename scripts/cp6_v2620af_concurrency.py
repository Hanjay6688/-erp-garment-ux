#!/usr/bin/env python3
"""Real opening transactions in two sessions, on a disposable physical clone."""
from __future__ import annotations
import argparse
import json
import os
import threading
import time
import traceback
import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import psycopg

import cp6_v2620af_runtime as runtime
import cp6_v2620ae_runtime as ae_runtime
import cp6_v2620af_family as family
import cp6_v2620h_maintenance_rollback_matrix as matrix

actors,base,prior=family.actors,family.base,family.prior
SOURCE=matrix.SOURCE
CLONE="postgresql://supabase_admin:postgres@127.0.0.1:54322/cp6_rollback"
ROOT=Path("cp6-proof/writer-af/concurrency")


def connect(label):
    conn=psycopg.connect(CLONE,application_name="cp6-af-"+label)
    conn.execute("set statement_timeout='30s';set lock_timeout='20s';set timezone='Asia/Jakarta'")
    return conn


def await_lock(pid):
    deadline=time.monotonic()+8
    with psycopg.connect(CLONE,autocommit=True) as observer:
        while time.monotonic()<deadline:
            row=observer.execute("select wait_event_type,wait_event,pg_blocking_pids(pid) from pg_stat_activity where pid=%s",(pid,)).fetchone()
            if row and row[0]=="Lock" and row[2]: return row
            time.sleep(.025)
    raise AssertionError("AF_REQUIRED_DATABASE_LOCK_NOT_OBSERVED")


def fixture():
    with connect("fixture") as conn,conn.cursor() as cur:
        actors.admin(cur)
        day=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3)
        material,location,roll=family.peer.rolls.create_roll(cur,"af-race-first")
        header,items=family.peer.rolls.create_opening(cur,day,"af-race",material,location,[(roll,Decimal("10"),material)])
        material2,location2,roll2=family.peer.rolls.create_roll(cur,"af-race-second")
        return dict(header=header,first_item=items[0],second_item=uuid.uuid4(),material=material2,location=location2,roll=roll2,day=day)


def insert(cur,f):
    actors.owner(cur)
    cur.execute("""insert into erp.opening_balance_items
      (id,opening_id,balance_type,material_id,roll_id,location_id,qty,unit_cost_snapshot)
      values(%s,%s,'MATERIAL',%s,%s,%s,10,1.25)""",
      (f["second_item"],f["header"],f["material"],f["roll"],f["location"]))


def post(cur,f):
    actors.owner(cur)
    cur.execute("select erp.post_opening_balance(%s)",(f["header"],))


def worker(connection,operation,fixture,result):
    try:
        with connection.cursor() as cur: operation(cur,fixture)
        connection.commit();result.update(committed=True,sqlstate=None)
    except psycopg.Error as exc:
        connection.rollback();result.update(committed=False,sqlstate=exc.sqlstate,error=str(exc))
    except Exception as exc:
        connection.rollback();result.update(committed=False,sqlstate=None,error=str(exc),traceback=traceback.format_exc())


def observation(f):
    with connect("observe") as conn,conn.cursor() as cur:
        return cur.execute("""select h.status,
          (select count(*) from erp.opening_balance_items i where i.opening_id=h.id),
          (select count(*) from erp.material_stock_movements m join erp.opening_balance_items i on i.id=m.source_id
            where m.source_type='OPENING_BALANCE_ITEM' and i.opening_id=h.id),
          (select sum(l.debit) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
            where j.source_type='OPENING_BALANCE' and j.source_id=h.id),
          (select count(*) from erp.journal_entries j where j.source_type='OPENING_BALANCE' and j.source_id=h.id)
          from erp.opening_balance_headers h where h.id=%s""",(f["header"],)).fetchone()


def run_case(generation,mode):
    f=fixture();response={};thread=None
    with connect("first") as first,connect("second") as second:
        try:
            if mode=="CHILD_FIRST":
                with first.cursor() as cur: insert(cur,f)
                operation=post
            else:
                with first.cursor() as cur: post(cur,f)
                operation=post if mode=="DOUBLE_POST" else insert
            thread=threading.Thread(target=worker,args=(second,operation,f,response),daemon=True)
            thread.start()
            lock=await_lock(second.info.backend_pid)
            if mode=="POST_ABORT": first.rollback()
            else: first.commit()
            thread.join(30)
            if thread.is_alive():
                second.cancel();thread.join(5)
                raise AssertionError("AF_SESSION_DID_NOT_FINISH")
        finally:
            first.rollback()
            if thread is not None and thread.is_alive():
                second.cancel();thread.join(5)
    state=observation(f)
    if mode=="POST_FIRST" and generation=="AE":
        assert response.get("committed") is True and state==("POSTED",2,1,Decimal("12.50"),1),(response,state)
        status="ORIGINAL_BUG_CONFIRMED"
    elif mode=="POST_FIRST":
        assert response.get("sqlstate")=="P0001" and "status is POSTED" in response.get("error","") and state==("POSTED",1,1,Decimal("12.50"),1),(response,state)
        status="PASS"
    elif mode=="POST_ABORT":
        assert response.get("committed") is True and state==("DRAFT",2,0,None,0),(response,state)
        with connect("after-abort") as conn,conn.cursor() as cur: post(cur,f)
        state=observation(f)
        assert state==("POSTED",2,2,Decimal("25.00"),1),state
        status="PASS"
    elif mode=="CHILD_FIRST":
        assert response.get("committed") is True and state==("POSTED",2,2,Decimal("25.00"),1),(response,state)
        status="PASS"
    else:
        assert response.get("sqlstate")=="P0001" and "must be DRAFT" in response.get("error","") and state==("POSTED",1,1,Decimal("12.50"),1),(response,state)
        status="PASS"
    return dict(status=status,mode=mode,observed_lock=lock,second=response,final_state=state,
                fixture_admin_changed_posted_data=False,http_ui_reachability_proven=False)


def run(generation):
    head,tree=runtime.verify_audit_source()
    if os.environ.get("PGURL")!=SOURCE or os.environ.get("CP6_AF_FAMILY_CONFIRM")!="postgres":
        raise AssertionError("AF_CONCURRENCY_EXACT_DISPOSABLE_REQUIRED")
    folder=ROOT/generation;folder.mkdir(parents=True,exist_ok=True)
    result=dict(status="INCOMPLETE",generation=generation,head=head,tree=tree,cases=[],production_go=False)
    with psycopg.connect(SOURCE) as conn,conn.cursor() as cur:
        if generation=="AE": assert len(ae_runtime.verified_successor(cur))==276
        else: assert len(runtime.verified_successor(cur))==278
    try:
        matrix.command(["bash","scripts/clone-cp6-disposable-database.sh",SOURCE,matrix.MAINTENANCE,matrix.CLONE,
                        "cp6_rollback",matrix.CONTAINER,str(folder/"PHYSICAL_BOUNDARY")],folder/"clone.log")
        with connect("foundation") as conn,conn.cursor() as cur:
            cur.execute("grant usage on schema erp to authenticated")
            cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps({"sub":base.OPERATOR_AUTH,"role":"authenticated"}),))
            base.load_fixture_foundation(cur);actors.admin(cur)
            day=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3)
            prior.set_open_period(cur,day-timedelta(days=2))
        for mode in (("POST_FIRST",) if generation=="AE" else ("POST_FIRST","POST_ABORT","CHILD_FIRST","DOUBLE_POST")):
            try: item=run_case(generation,mode)
            except Exception as exc: item=dict(status="FAIL",mode=mode,error=str(exc),traceback=traceback.format_exc())
            result["cases"].append(item)
            print(json.dumps(item,default=str),flush=True)
            (folder/"RESULT.json").write_text(json.dumps(result,indent=2,default=str)+"\n")
    finally:
        matrix.legacy.drop_clone()
    with psycopg.connect(matrix.MAINTENANCE) as conn:
        result["clone_removed"]=conn.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]==0
    expected="ORIGINAL_BUG_CONFIRMED" if generation=="AE" else "PASS"
    if result["clone_removed"] and len(result["cases"])==(1 if generation=="AE" else 4) and all(c["status"]==expected for c in result["cases"]):
        result["status"]=expected
    (folder/"RESULT.json").write_text(json.dumps(result,indent=2,default=str)+"\n")
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--generation",choices=("AE","AF"),required=True)
    args=parser.parse_args()
    try: result=run(args.generation)
    except Exception as exc:
        result=dict(status="FAIL",error=str(exc),traceback=traceback.format_exc(),production_go=False)
        folder=ROOT/args.generation;folder.mkdir(parents=True,exist_ok=True)
        (folder/"RESULT.json").write_text(json.dumps(result,indent=2,default=str)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="cases"},default=str))
    raise SystemExit(0 if result["status"] in {"PASS","ORIGINAL_BUG_CONFIRMED"} else 1)
