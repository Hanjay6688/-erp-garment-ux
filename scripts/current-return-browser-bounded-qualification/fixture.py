"""Disposable Native source and exact read-back for corrected return UI proof."""
from datetime import date
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse
import importlib.util,json,os,sys

sys.dont_write_bytecode=True
REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'scripts'))
import psycopg
# This fixture owns its operation/JSON arguments. Imported recovery entrypoints
# receive their unchanged empty CLI contract, never the fixture's commands.
_fixture_argv=sys.argv
try:
    sys.argv=sys.argv[:1]
    import cp7_p21_current_chain_rehearsal_probe
    spec=importlib.util.spec_from_file_location('retained_current_return_auth_fixture',REPO/'scripts/current-return-auth-bounded-qualification/cases.py')
    auth=importlib.util.module_from_spec(spec);spec.loader.exec_module(auth)
finally:
    sys.argv=_fixture_argv
retained=auth.retained


def fingerprint(value):
    return sha256(json.dumps(value,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()


def main():
    if sys.argv[1:]==['--check-import']:
        print(json.dumps(dict(status='FIXTURE_COMMAND_IMPORT_ADMITTED',arguments_preserved=sys.argv[1:])));return
    assert len(sys.argv)==3,'FIXTURE_REQUIRES_OPERATION_AND_JSON'
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in('127.0.0.1','localhost')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    op=sys.argv[1];p=json.loads(sys.argv[2]);http=SimpleNamespace(connect=lambda:psycopg.connect(target))
    if op=='create':
        f,rid,raw,before=auth.fixture(http,date.fromisoformat(p['today']))
        with http.connect()as conn,conn.cursor()as cur:
            retained.b.api.admin(cur)
            name='Browser return destination '+f['tag']
            cur.execute('update erp.locations set location_name=%s where id=%s',(name,f['destination']));assert cur.rowcount==1
            mapping={k:retained.cmd.mapping(cur,k)for k in('AR_CUSTOMER','SALES_REVENUE','FG_INVENTORY','COGS')}
            conn.commit()
        out=dict(f,bad_return_id=rid,bad_raw=raw,before_return=before,destination_name=name,mapping=mapping)
    elif op=='fingerprint':
        state=auth.snapshot(http)
        out={k:fingerprint(v)for k,v in state.items()}
    elif op=='read':
        with http.connect()as conn,conn.cursor()as cur:
            retained.b.api.admin(cur)
            bad=auth.bad_draft(cur,p['bad_return_id'])
            good=cur.execute('select id::text,return_number,status,physical_at from erp.sales_returns where sale_id=%s and id<>%s order by id',(p['sale'],p['bad_return_id'])).fetchall()
            out=dict(bad_raw=bad,bad_journals=cur.execute("select count(*)from erp.journal_entries where source_type='SALES_RETURN'and source_id=%s",(p['bad_return_id'],)).fetchone()[0],
                sale_status=cur.execute('select status from erp.sales_headers where id=%s',(p['sale'],)).fetchone()[0],
                good_returns=[dict(id=i,number=n,status=s,physical_at=t)for i,n,s,t in good],
                positions=[dict(location=l,grade=g,qty=n)for(l,g),n in sorted(retained.positions(cur,p).items())],
                accounts=retained.cmd.accounts(cur))
            conn.rollback()
    else:raise ValueError('UNKNOWN_BROWSER_FIXTURE_OPERATION')
    print(json.dumps(out,default=str))


if __name__=='__main__':main()
