"""Provision transport for the existing installer in the disposable original-BF copy."""
import json
import os
import secrets
from pathlib import Path

import psycopg
from psycopg import sql

ROLE="cp6_maintenance_admission"
ROOT=Path(os.environ["RUNNER_TEMP"])
ROLE_ROWS="""select rolname,rolsuper,rolinherit,rolcreaterole,rolcreatedb,rolcanlogin,rolreplication,
    rolconnlimit,rolbypassrls,rolvaliduntil,rolconfig from pg_roles where rolname=%s"""
MEMBERS="""select a.rolname,b.rolname,m.admin_option,m.inherit_option,m.set_option from pg_auth_members m
    join pg_roles a on a.oid=m.member join pg_roles b on b.oid=m.roleid
    where a.rolname=%s or b.rolname=%s order by 1,2"""


def authority(conn):
    return [conn.execute(ROLE_ROWS,(ROLE,)).fetchone(),conn.execute(MEMBERS,(ROLE,ROLE)).fetchall()]


def main():
    evidence=ROOT/"cp75-original-observations"
    opened=json.loads((evidence/"clean-opened.json").read_text())
    assert opened["origin_run"]==44800849536 and opened["container"]=="supabase_db_cp5-local" and opened["disposable"]
    secret=secrets.token_urlsafe(32)
    url="postgresql://"+ROLE+":"+secret+"@127.0.0.1:54322/template1"
    print("::add-mask::"+secret,flush=True)
    print("::add-mask::"+url,flush=True)
    socket=str(ROOT/"cp75-originals/clean-socket")
    with psycopg.connect(host=socket,dbname="template1",user="supabase_admin") as conn:
        previous=authority(conn)
        assert previous[0] and previous[0][1] is True and previous[0][5] is True
        conn.execute(sql.SQL("alter role {} password {}").format(sql.Identifier(ROLE),sql.Literal(secret)))
        assert authority(conn)==previous
    with psycopg.connect(url,connect_timeout=10) as conn:
        identity=conn.execute("select session_user,current_user,current_database(),inet_client_addr() is not null").fetchone()
        assert identity==(ROLE,ROLE,"template1",True) and authority(conn)==previous
    with open(os.environ["GITHUB_ENV"],"a",encoding="ascii") as target:
        target.write("CP6_ADMISSION_CONTROL_PGURL="+url+"\n")
    (evidence/"installer-identity.json").write_text(json.dumps({"role":ROLE,"database":"template1","transport":"loopback TCP",
        "original_BF_run":opened["origin_run"],"privilege_attributes":previous[0],"memberships":previous[1],
        "attributes_and_memberships_equal":True,"disposable_transport_password_rotated":True,"production_go":False},
        sort_keys=True,indent=2,default=str)+"\n")


if __name__=="__main__":
    main()
