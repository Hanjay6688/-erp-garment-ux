"""Install the final reminder definition from its factory SQL and compare it with the released upgrade."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import psycopg

ROUTE = "scripts/cp7-src/manual-reminders/facade.sql"
OLD_SOURCE = "10baedebcbbc1ef87330d8577c673be0c02c8c67"
NEW_SOURCE = "a190100b085b34f825eb4062b5016bc28bb4ce5c"
BEFORE = "d88aec0885339e4271c6ac509bda457b57c0b45410f628ad81d0952c8912681a"
AFTER = "619183f4ccdb1c6a7a491cd189f787e73ca6e472ce42ef376acc3021d6cff772"
SIG = "cp7_reminders.workspace(jsonb)"
READER = re.compile(r"^create function cp7_reminders\.workspace\(p_query jsonb\)returns jsonb.*?^end \$\$;", re.M|re.S)
READ = """select prosrc, pg_get_userbyid(proowner),proacl::text,prosecdef,provolatile,proparallel,proisstrict,
                 proconfig,oid::text,pg_get_function_arguments(oid)
          from pg_proc where oid=to_regprocedure(%s)"""
SQL = """select n.nspname,p.proname,pg_get_function_identity_arguments(p.oid),
    pg_get_functiondef(p.oid), pg_get_userbyid(p.proowner),p.proacl::text, p.proconfig,
    has_function_privilege('anon',p.oid,'EXECUTE'), has_function_privilege('authenticated',p.oid,'EXECUTE'),
    has_function_privilege('service_role',p.oid,'EXECUTE'),p.prosecdef
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='cp7_reminders' or n.nspname='public' and p.proname in ('erp_cp7_get_reminders_v1','erp_cp7_save_reminder_v1')
    order by 1,2,3"""


def blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def digest(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


def sources(base, rig):
    raw=(base/ROUTE).read_bytes()
    assert blob(raw)==OLD_SOURCE
    manifest=json.loads((rig/"candidate.json").read_text())
    assert manifest["product"]=="48858590a361343e73a7f16f6646363dc155c04e"
    assert manifest["files"][ROUTE]=={"before":OLD_SOURCE,"after":NEW_SOURCE}
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/ROUTE
        path.parent.mkdir(parents=True)
        path.write_bytes(raw)
        subprocess.run(["git","apply","--no-index",str((rig/"factory.patch").resolve())],cwd=td,check=True)
        target=path.read_bytes()
    assert blob(target)==NEW_SOURCE
    return raw.decode(),target.decode()


def apply_factory(conn, module_sql):
    """Update the earlier factory layer, retaining ownership, ACL, OID and execution contract."""
    match=READER.findall(module_sql)
    assert len(match)==1
    literal=match[0]
    body=literal.split("as $$",1)[1].rsplit("$$;",1)[0]
    assert digest(body)==AFTER
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("select pg_advisory_xact_lock(hashtextextended(%s,0))",(SIG,))
        prior=cur.execute(READ,(SIG,)).fetchone()
        assert digest(prior[0]) in (BEFORE,AFTER)
        cur.execute(literal.replace("create function ","create or replace function ",1))
        now=cur.execute(READ,(SIG,)).fetchone()
        assert now[0]==body and now[1:]==prior[1:]
        return {"source_blob":NEW_SOURCE,"body_sha256":digest(now[0]),"owner":now[1],
                "identity_and_privileges_equal":True,"changed":prior[0]!=now[0]}


def inspect(host):
    with psycopg.connect(host=host,dbname="postgres",user="postgres") as c:
        assert c.execute("show server_version_num").fetchone()[0]=="170006"
        return c.execute(SQL).fetchall()


def main(base, rig, clean, upgrade, output):
    old,new=sources(base,rig)
    spec=importlib.util.spec_from_file_location("released_reminder_upgrade",rig/"install.py")
    installer=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    assert blob((rig/"install.py").read_bytes())=="7a6d8ec30f17ddada5941c9a923f699a1367656a"
    for host,raw in ((clean,new),(upgrade,old)):
        with psycopg.connect(host=host,dbname="postgres",user="postgres") as c:
            for role in ("anon","authenticated","service_role","cp7_capture"):
                c.execute("create role "+role)
            c.execute(raw)
    fresh=inspect(clean)
    predecessor=inspect(upgrade)
    assert len(fresh)==len(predecessor)==7
    assert [x[1] for x,y in zip(fresh,predecessor) if x!=y]==["workspace"]
    with psycopg.connect(host=upgrade,dbname="postgres",user="postgres") as c:
        first=installer.apply(c,"up")
    assert first["changed"] and first["body_sha256"]==AFTER and inspect(upgrade)==fresh
    with psycopg.connect(host=upgrade,dbname="postgres",user="postgres") as c:
        assert installer.apply(c,"down")["changed"]
        factory=apply_factory(c,new)
    assert factory["changed"] and inspect(upgrade)==fresh
    print("CP75_FACTORY_SQL_MATCH",json.dumps({"routines":len(fresh),"body":AFTER,"source_blob":NEW_SOURCE,
            "privileges_equal":True,"owners_equal":True}),flush=True)
    output.write_text(json.dumps({"product":"48858590a361343e73a7f16f6646363dc155c04e","scope":"seven reminder routines in two empty PostgreSQL 17.6 clusters",
        "source":NEW_SOURCE,"factory":factory,"upgrade":first,"routines":len(fresh),
        "catalogues_equal":True,"catalogue_sha256":digest(json.dumps(fresh,sort_keys=True,default=str)),"production_go":False},indent=2)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("base","rig","clean","upgrade","output"):
        p.add_argument(name,type=Path)
    args=p.parse_args()
    main(args.base,args.rig,str(args.clean),str(args.upgrade),args.output)
