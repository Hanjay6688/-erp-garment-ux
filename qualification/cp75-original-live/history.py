"""Seed business history on the old Global, upgrade it with the released installers, then reopen from another session."""
import hashlib
import importlib.util
import json
import os
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
import subprocess
import tempfile
import time
from live import WORK as PRIVATE, start, docker
from close11 import frozen, checkpoint

import psycopg
from psycopg import sql
import profile_figures
import cp7_master_cases as master
import cp7_p19_plan_v2_cases as plan
import cp7_p19_report_v2_cases as reports
import cp7_supplier_payment_cases as payments
import cp7_supplier_payment_create_cases as create
import cp7_supplier_payment_correction_cases as correction
from audit.codex import planner as planner_case
from common import admin, actors, db
from sales_collision import opening, stock, intent, command, review, balance
from supplier import read_state

WORK=Path(os.environ["GITHUB_WORKSPACE"])
OUT=Path(os.environ["RUNNER_TEMP"])/"cp75-original-observations"
TARGET="deb596acb49e10ac66e0a1616a582ff74889146c0b59ee0d81ac7c2818397821"
OLD="a3da0ecf21909731ab8474c54a7c91afb75bb58dd8b6042cc82314b20808dbd7"
MIDDLE="da0b424f305f0b423808d445034ff8a166e32a8d9d13f811078daf2c864b012b"


def canonical(value):
    return json.dumps(value,sort_keys=True,default=str,separators=(",",":"))


def stamp(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def record(name,data):
    path=OUT/(name+".json")
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data,indent=2,sort_keys=True,default=str)+"\n")
    tmp.replace(path)
    print("CP75_HISTORY",name,flush=True)


def posted(cur,who,product,count):
    payload=intent(count,product)
    created=command(cur,who,"CREATE",payload)
    doc={"p":payload,"id":created["sale_id"]}
    requested,version=review(cur,who,doc,"POST")
    saved=command(cur,who,"POST",requested,version)
    assert saved["status"]=="POSTED"
    return str(doc["id"])


def bank_code(cur,fixture,owner):
    offset=0
    while offset is not None:
        page=create.read(cur,fixture,owner,bank_offset=offset)["cash_accounts"]
        for row in page["rows"]:
            if row["id"]==fixture["cash"]:
                return row["code"]
        offset=page["next_offset"]
    raise ValueError("expected fixture bank missing")


def seed(day):
    with psycopg.connect(**db()) as conn,conn.cursor() as cur:
        owner,other=actors(cur)
        products=opening.import_batch(cur,day,2,opening.Phases())
        row,control=profile_figures.ordered_opening(cur,products)
        assert stock(cur,row)==50
        warm=posted(cur,owner,row,30)
        conn.commit()
        assert stock(cur,row)==20
        left=posted(cur,owner,row,16)
        conn.commit()
        right=posted(cur,other,row,4)
        conn.commit()
        assert stock(cur,row)==0
        # Finish the Planner stock movements before the supplier reader records its stock and HPP reference.
        x,draft=planner_case.setup(cur,day,subject=owner)
        admin(cur)
        conn.commit()
        f=payments.fixture(cur,day,26)
        f["payment"]=f["target"]
        bank=bank_code(cur,f,owner)
        conn.commit()
        before=read_state(cur,f,owner,bank)
        assert (Decimal(before["AP"]["paid"]),Decimal(before["AP"]["remaining"]))==(260,740)
        changed=correction.correct(cur,correction.payload(cur,f,"5.00",subject=other),subject=other)
        assert changed["original_status"]=="REVERSED" and changed["status"]=="POSTED"
        conn.commit()
        record("old-documents",{"sku":str(row["product"]),"sales":[warm,left,right],"purchase":f["receipt"]["purchase_id"],
                               "original_payment":f["target"],"replacement":changed["payment_id"],"actors":[owner,other]})
        # Published work and its draft must exist before migration, including the stored report sections.
        production=plan.schedule.supply.capture(cur,day,subject=owner)
        snap=reports.staged_run(cur,day,subject=owner)
        _,done,_=reports.published(cur,snap,subject=owner,title="CP7.5 laporan tersimpan")
        conn.commit()
        assert payments.physical_state(cur)==f["physical"]
        return dict(owner=owner,other=other,row=row,control=control["product"],deferred=x["f"]["product"],
                    supply_id=str(production["run_id"]),plan_query=x["query"],warm=warm,left=left,right=right,fixture=f,bank=bank,
                    replacement=changed["payment_id"],draft=draft["draft_id"],run=x["run"],job=x["key"],publication=done["publication_id"])


def report_permissions(cur, f):
    """Exercise active roles with temporary subjects. Preserve the exact privileges and all fixture rows."""
    admin(cur)
    permissions = cur.execute("""select r.role_code, p.permission_key
        from erp.app_roles r left join erp.app_role_permissions p on p.role_id=r.id
        where r.is_active order by r.role_code,p.permission_key""").fetchall()
    assert {"OWNER","ADMIN","KEUANGAN"} <= {role for role,_ in permissions}
    matrix = {"OWNER": {"own_report": "READ", "foreign_report": "42501"}}
    cur.execute("savepoint cp75_scoped_roles")
    try:
        for role in ("ADMIN", "KEUANGAN"):
            subject = master.role_actor(cur, role)
            profile = master.call(cur, "select public.erp_get_my_access_v1()", (), subject)
            assert profile["allowed"] is True, role
            state, code, _ = plan.refusal(cur, lambda: reports.read(cur, f["publication"], subject))
            assert state == "42501", (role, state, code)
            matrix[role] = {"profile_allowed":True, "foreign_report": state, "denial":code}
    finally:
        cur.execute("rollback to savepoint cp75_scoped_roles")
        cur.execute("release savepoint cp75_scoped_roles")
        admin(cur)
    return {"matrix":matrix,"active_role_grants_sha256":stamp(permissions),
            "active_roles":len({r for r,_ in permissions}), "granted_pairs":sum(p is not None for _,p in permissions)}


def read_history(f):
    with psycopg.connect(**db()) as c,c.cursor() as q:
        who=f["owner"]
        ap=read_state(q,f["fixture"],who,f["bank"])
        assert (Decimal(ap["AP"]["paid"]),Decimal(ap["AP"]["remaining"]))==(255,745)
        assert ap["original_status"]=="REVERSED" and ap["inverse"] and ap["replacement"]==f["replacement"]
        assert sum(len(v) for v in ap["history_pages"])==27
        sale_a=balance(q,f["left"],16,320)
        sale_b=balance(q,f["right"],4,80)
        assert stock(q,f["row"])==0
        draft=plan.read(q,f["draft"],who)
        assert draft["state"]=="SAVED"
        snapshot,pages,shape=plan.staged.fetch(q,f["run"],who)
        job=plan.staged.job_row(q,f["job"],who)
        doc=reports.read(q,f["publication"],who)
        assert doc["id"]==str(f["publication"]) and hashlib.sha256(doc["summary"].encode()).hexdigest()==doc["summary_sha256"]
        section_hashes=[]
        for part in doc["sections"]:
            body=reports.section(q,f["publication"],part["index"],doc["access_epoch"],who)
            digest=hashlib.sha256(body["body"].encode()).hexdigest()
            assert digest==part["sha256"]==body["sha256"]
            section_hashes.append(digest)
        assert hashlib.sha256("\n".join([doc["summary_sha256"]]+section_hashes).encode()).hexdigest()==doc["report_hash"]
        denial=plan.refusal(q,lambda:reports.read(q,f["publication"],f["other"]))
        assert tuple(denial[:2])==("42501","CP7_REPORT_UNAVAILABLE")
        preview=plan.preview(q,f["draft"],who)["live"]
        planner_values=planner_case.numbers(preview)
        assert planner_values==planner_case.BASELINE
        access=report_permissions(q,f)
        admin(q)
        panel_figures,dates=profile_figures.read(q,f,doc,snapshot)
        result=dict(panel_figures=panel_figures,document_dates=dates,production_id=f["supply_id"],role_access=access,planner_values=planner_values,accounts_payable=ap,sales=[sale_a,sale_b],available=0,
                    draft=draft["state"],snapshot_id=str(f["run"]),job_id=str(job["id"]),
                    stored_snapshot=stamp(snapshot),snapshot_identity=pages["identity_hash"],page_count=shape["page_count"],draft_id=str(f["draft"]),
                    published={"id":doc["id"],"hash":doc["report_hash"],"sections":section_hashes,"summary":doc["summary_sha256"]},
                    foreign_report={"sqlstate":denial[0],"reason":denial[1]})
        return json.loads(canonical(result))


def raw_state():
    # Full, unmasked equality is meaningful across time on this same database.
    result={}
    with psycopg.connect(**db()) as c,c.cursor() as q:
        tables=q.execute("""select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
                             where c.relkind in ('r','p') and (n.nspname in ('erp','auth') or left(n.nspname,4)='cp7_')
                             order by 1,2""").fetchall()
        for schema,name in tables:
            stmt=sql.SQL("select count(*),md5(coalesce(string_agg(h,'' order by h),'')) from "
                         "(select md5(to_jsonb(r)::text) h from {} r)x").format(sql.Identifier(schema,name))
            result[schema+"."+name]=list(q.execute(stmt).fetchone())
        seq=q.execute("""select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
                          where c.relkind='S' and (n.nspname in ('erp','auth') or left(n.nspname,4)='cp7_') order by 1,2""").fetchall()
        for schema,name in seq:
            result[schema+"."+name]=list(q.execute(sql.SQL("select last_value,is_called from {}").format(sql.Identifier(schema,name))).fetchone())
    return result


def load_installer(label,root,expected):
    raw=(root/"install.py").read_bytes()
    assert hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()==expected
    spec=importlib.util.spec_from_file_location(label,root/"install.py")
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def seal():
    with psycopg.connect(**db()) as c:
        return c.execute("select cp7_global_nonpo_envelope.catalogue_fingerprint_v1()").fetchone()[0]


def cold_copy(container, archive, image):
    docker("stop","-t","100",container,stdout=subprocess.DEVNULL)
    try:
        with archive.open("xb") as sink:
            docker("run","--rm","--network","none","--user","0","-v",container+"-data:/restore/data:ro",
                   "-v",container+"-config:/restore/config:ro","--entrypoint","sh",image,"-ec",
                   "tar -C /restore -czf - data config",stdout=sink)
    finally:
        docker("start",container,stdout=subprocess.DEVNULL)
    proof=frozen.inventory(archive)
    proof.update(audit_baseline="COLD_GLOBAL_WITH_INACTIVE_NATIVE_JOBS",cold_control_sha256=proof["source_control_sha256"])
    return proof


def wait_for_seal(expected):
    for _ in range(100):
        try:
            if seal()["sha256"]==expected:
                return
        except psycopg.OperationalError:
            pass
        time.sleep(1)
    raise RuntimeError("PostgreSQL did not reopen at the expected version")


def exercise_upgrade(container,image,origin,restore_lane):
    assert seal()["sha256"]==OLD
    with psycopg.connect(**db()) as c:
        day=c.execute("select (now() at time zone 'Asia/Jakarta')::date").fetchone()[0]
    f=seed(day)
    before=read_history(f)
    rows=raw_state()
    record("upgrade-before",{"origin":origin,"business_day":str(day),"history":before,"rows_sequences":rows,"seal":OLD})
    with tempfile.TemporaryDirectory(dir=PRIVATE) as directory:
        archive=Path(directory)/"old-with-history.tar.gz"
        proof=cold_copy(container,archive,image)
        wait_for_seal(OLD)
        restore_digest=checkpoint.digest(archive)
        backup=checkpoint.seal(archive,OUT/"historical-before-upgrade.cp75",WORK/"capture/qualification/close11/auditor-public.pem")
        record("upgrade-resume",{"origin":origin,"archive":backup,"physical_sha256":restore_digest,"image":image,"copy":proof})
        steps=[("g14",WORK/"g14/qualification/close12/product","77cc2c35a78c1fde725e37199a80f87a5f9965e3",MIDDLE),
               ("order",WORK/"rig/qualification/cp75-order","7a6d8ec30f17ddada5941c9a923f699a1367656a",TARGET)]
        for name,path,oid,want in steps:
            installer=load_installer(name,path,oid)
            with psycopg.connect(**db()) as c:
                applied=installer.apply(c,"up")
            observed=seal()
            assert applied["changed"] and observed["sha256"]==want and observed["groups"]==25
            record("up-"+name,{"fresh_seal":observed["sha256"],"changed":True})
        after=read_history(f)
        after_rows=raw_state()
        changed={k for k in set(rows)|set(after_rows) if rows.get(k)!=after_rows.get(k)}
        record("upgrade-after",{"history":after,"rows_sequences":after_rows,"changed_rows_or_sequences":sorted(changed),
                                 "history_equal":before==after,"seal":seal()["sha256"]})
        assert before==after and not changed
        _,socket=start(restore_lane,archive,image,proof,"cp6_rollback")
        os.environ["PGHOST"]=str(socket)
        restored=read_history(f)
        restored_rows=raw_state()
        record("upgrade-restored",{"origin_seal":seal()["sha256"],"history_equal":restored==before,
                                   "all_rows_sequences_equal":restored_rows==rows,"physical_sha256":restore_digest,
                                   "table_and_sequence_count":len(rows),"history":restored})
        assert seal()["sha256"]==OLD and restored==before and restored_rows==rows


def main():
    assert os.environ["PGHOST"].endswith("/upgrade-socket")
    meta=json.loads((PRIVATE/"upgrade.json").read_text())
    exercise_upgrade("cp75-upgrade-"+os.environ["GITHUB_RUN_ID"],meta["postgres_image"],
                     "original archived Global 44671146483","upgrade-restore")


if __name__=="__main__":
    main()
