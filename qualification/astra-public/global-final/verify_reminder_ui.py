"""Astra retest of the successor's installed source, ordered reminder window and native edits."""
import hashlib
import importlib.util
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import psycopg
import cp7_r3_reminders_cases as rem

PIN = "48858590a361343e73a7f16f6646363dc155c04e"
TREE = "21feb69a839e74773aa87bc587bbf91a2d301144"
PARENT = "486d344e0ce47d2b184e2a7bfccf2a927424d184"
ORIGIN_SEAL = "da0b424f305f0b423808d445034ff8a166e32a8d9d13f811078daf2c864b012b"
FINAL_SEAL = "deb596acb49e10ac66e0a1616a582ff74889146c0b59ee0d81ac7c2818397821"
ROOT = Path(os.environ["GITHUB_WORKSPACE"])
TRANSPORT = ROOT / "rig/qualification/cp75-reminders"
PACKAGE = ROOT / "rig/qualification/cp75-order"
OUT = Path(os.environ["WRITER_RESULTS"])
OUT.mkdir(parents=True,exist_ok=True)

def oid(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

old_pins={"check.py":"8e6230a7e636aff92ba2b527afba88d4225b1db7","browser.cjs":"4e832e0bb87bcc95fe00893640194a396b3b4672","candidate.json":"bdd314ca953940005b26d89b205944df10aab1eb","ui.patch":"1b5c05fead938791b43fb7f24d1e21d7d7a193d1"}
new_pins={"install.py":"7a6d8ec30f17ddada5941c9a923f699a1367656a","candidate.json":"9f1d9bfb92d7e49fe60f4be7ebc64d30a916fdee","workspace.patch":"9673a06747a7b1c99a36d2b58afadcbfff88da1a","ui.patch":"f9373ae8eb1e7f2cbaf6549e757c2dd4bf247b80","factory.patch":"e0d4adf9ae203978ae774a36fd1fb3efaddb6460"}
assert all(oid(TRANSPORT/n)==v for n,v in old_pins.items())
assert all(oid(PACKAGE/n)==v for n,v in new_pins.items())
fixture=module("parent_fixture",TRANSPORT/"check.py")
installer=module("ordered_window",PACKAGE/"install.py")
release=json.loads((PACKAGE/"candidate.json").read_bytes())
assert release["product"]==PIN and release["tree"]==TREE and release["parent"]==fixture.RELEASE["product"]==PARENT
assert release["parent_tree"]==fixture.RELEASE["tree"] and release["parent_catalogue"]==ORIGIN_SEAL
fixture.install()
(OUT/"installation.json").rename(OUT/"parent-installation.json")
app=fixture.APP
sql_path="scripts/cp7-src/manual-reminders/facade.sql"
for patch,root,files in [("ui.patch",app,[p for p in release["files"] if p.startswith("src/")]),("factory.patch",ROOT/"fixtures",[sql_path])]:
    assert all(oid(root/p)==release["files"][p]["before"] for p in files)
    subprocess.run(["git","apply","--no-index",str(PACKAGE/patch)],cwd=root,check=True)
    assert all(oid(root/p)==release["files"][p]["after"] for p in files)

def procedure_snapshot():
    with psycopg.connect(**fixture.DB) as db:
        rows=db.execute("""select p.oid::bigint, n.nspname||'.'||p.proname,
          md5((to_jsonb(p)-'prosrc')::text), encode(sha256(convert_to(p.prosrc,'UTF8')),'hex')
          from pg_proc p join pg_namespace n on n.oid=p.pronamespace
          where n.nspname !~ '^pg_(temp|toast_temp)_' order by p.oid""").fetchall()
        return {r[0]:r[1:] for r in rows}

before=procedure_snapshot()
parent=fixture.seal()
assert parent["sha256"]==ORIGIN_SEAL
ladder=[]
for direction,change in [("up",True),("up",False),("down",True),("down",False),("up",True)]:
    with psycopg.connect(**fixture.DB) as db:
        outcome=installer.apply(db,direction)
    after=procedure_snapshot()
    seal=fixture.seal()
    assert before.keys()==after.keys() and seal["counts"]==parent["counts"] and seal["groups"]==25
    changed=[i for i in before if before[i]!=after[i]]
    assert outcome["changed"] is change
    if direction=="down":
        assert not changed and seal==parent
    else:
        assert len(changed)==1 and before[changed[0]][:2]==after[changed[0]][:2]
        assert after[changed[0]][0]=='cp7_reminders.workspace' and after[changed[0]][2]==installer.AFTER
        assert before[changed[0]][2]==installer.BEFORE and seal["sha256"]==FINAL_SEAL
    ladder.append(dict(direction=direction,changed=change,seal=seal['sha256'],different_from_parent=[after[i][0] for i in changed]))
factory=(ROOT/'fixtures'/sql_path).read_text().split('create function cp7_reminders.workspace(',1)[1].split('as $$',1)[1].split('$$;',1)[0]
with psycopg.connect(**fixture.DB) as db:
    installed=db.execute("select prosrc from pg_proc where oid='cp7_reminders.workspace(jsonb)'::regprocedure").fetchone()[0]
assert installed==factory and hashlib.sha256(installed.encode()).hexdigest()==installer.AFTER
fixture.store('installation',dict(candidate=PIN,tree=TREE,run=os.environ['GITHUB_RUN_ID'],origin=PARENT,parent_seal=ORIGIN_SEAL,seal=FINAL_SEAL,groups=25,
    procedures_compared=len(before),factory_matches_installed=True,body_sha256=installer.AFTER,metadata_equal=True,steps=ladder))

def verify_window():
    with psycopg.connect(**fixture.DB) as db,db.cursor() as q:
        who=rem.owner(q)
        start=datetime(2032,4,10,tzinfo=timezone.utc)
        for i in range(201):
            rem.save(q,who,"SAVE",rem.body((start+timedelta(minutes=i)).isoformat(),title=f"Astra {i}"))
        positions=[0,25,150,175]
        def snapshot():
            ordered=rem.order_of(q,who,"OPEN")
            assert len(ordered)==201
            expected=hashlib.sha256(','.join(ordered[:200]).encode()).hexdigest()
            for offset in positions:
                reply=rem.get(q,who,dict(filter="OPEN",offset=offset,limit=25,include_order=True))
                assert reply["order_token"]==expected and reply["page"]["beyond_window"]==1
                assert [r["id"] for r in reply["items"]]==ordered[offset:offset+25]
            return ordered,expected
        original,first=snapshot()
        last=rem.row(q,original[-1])
        rem.save(q,who,"SAVE",rem.body((start-timedelta(days=1)).isoformat(),title=last["title"],rid=last["id"]),expected=last["row_version"])
        updated,second=snapshot()
        assert updated==[original[-1],*original[:-1]] and first!=second
        row=rem.row(q,updated[80])
        rem.save(q,who,"SAVE",rem.body(row['due_at'].isoformat(),title=row['title'],note="Perubahan catatan",rid=row['id']),expected=row["row_version"])
        assert snapshot()==(updated,second)
        legacy=rem.get(q,who,dict(filter="OPEN",offset=25,limit=25))
        assert "order_token" not in legacy and [r['id'] for r in legacy['items']]==updated[25:50]
        fixture.store('window',dict(candidate=PIN,actual=201,visible=200,offsets=positions,initial_token=first,new_token=second,
            newly_visible_id=updated[0],displaced_id=original[199],note_preserved_order=True,legacy_page_matches=True))
        db.rollback()
verify_window()
subprocess.run(["npm","ci","--no-audit","--no-fund"],cwd=app,check=True)
bootstrap=(TRANSPORT/"browser.cjs").read_text().split("  const browser=await chromium.launch",1)[0]
cases=Path(__file__).with_name("verify_reminder_browser.json")
driver=OUT/"independent.cjs"
driver.write_text(bootstrap+json.loads(cases.read_text()))
with ThreadingHTTPServer(("127.0.0.1",0),fixture.Adapter) as server:
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        subprocess.run(["node",str(driver),str(app),str(OUT),f"http://127.0.0.1:{server.server_address[1]}"],cwd=app,check=True)
    finally:
        server.shutdown()
        thread.join()
rows=json.loads((OUT/"browser.json").read_bytes())
assert len({i["id"] for i in rows})==len(rows)==18
assert all(i["outcome"] in {"PASS","FAIL"} for i in rows)
fixture.store("verdict",dict(candidate=PIN,tree=TREE,run=os.environ["GITHUB_RUN_ID"],head=os.environ["GITHUB_SHA"],
   results=[{"id":r["id"],"outcome":r["outcome"]} for r in rows],production_go=False))
if any(r["outcome"]=="FAIL" for r in rows):
    raise SystemExit("See browser observations for the product or fixture expectation that failed")
