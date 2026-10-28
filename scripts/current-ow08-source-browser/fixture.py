"""Existing Native source fixtures; only the disposable committed browser copy.

Fixture writes are not screen-creation evidence. Readback uses the existing
all-business-table/sequence comparator without dropping fields or rows.
"""
from pathlib import Path
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from cp7_kasbon_source import cases as kasbon
import cp7_ow04_restore_bundle as catalog

operation=sys.argv[1];payload=json.loads(sys.stdin.read())
url=os.environ['AUDITOR_BROWSER_DB_URL'];address=urlparse(url)
assert address.hostname in('127.0.0.1','localhost')and address.path=='/cp6_auditor_browser'
with psycopg.connect(url)as connection,connection.cursor()as cur:
    assert cur.execute('select current_database()').fetchone()[0]=='cp6_auditor_browser'
    if operation=='kasbon':
        kasbon.b.api.admin(cur)
        grant=not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if grant:cur.execute('grant usage on schema erp to authenticated')
        try:
            day=date.fromisoformat(payload['today'])
            given=kasbon.given(cur,day,'1200.00')
            cancelled=kasbon.given(cur,day,'800.00')
            w=kasbon.c17.kasbon_read(cur,cancelled['contractor'])
            done=kasbon.c17.kasbon(cur,'CANCEL',dict(contractor_id=cancelled['contractor'],advance_id=cancelled['kasbon']['id'],reason='OW08 source browser Native cancelled fixture'),w)
            assert done['advance']['status']=='CANCELLED'
            kasbon.b.api.admin(cur)
            inverse=cur.execute('select cancel_journal_id::text from cp7_kasbon.advances where id=%s',(cancelled['kasbon']['id'],)).fetchone()[0]
            rows=[]
            for fixture,journal,status in [(given,given['journal'],'GIVEN'),(cancelled,inverse,'CANCELLED')]:
                number,transaction_date,kind,source=cur.execute('select journal_number,transaction_date::text,source_type,source_id::text from erp.journal_entries where id=%s',(journal,)).fetchone()
                rows.append(dict(journal_id=journal,journal_number=number,date=transaction_date,source_type=kind,source_id=source,
                    kasbon_id=fixture['kasbon']['id'],kasbon_number=fixture['kasbon']['number'],contractor_id=fixture['contractor'],status=status))
        except Exception:
            connection.rollback();raise
        finally:
            kasbon.b.api.admin(cur)
            if grant:cur.execute('revoke usage on schema erp from authenticated')
        connection.commit();result=dict(rows=rows,fixture_source='EXISTING_NATIVE_GIVE_AND_CANCEL_NOT_SCREEN_CREATION')
    elif operation=='state':
        kasbon.b.api.admin(cur);result=catalog._data(cur);connection.rollback()
    else:raise ValueError('UNDECLARED_OW08_SOURCE_FIXTURE_OPERATION')
print(json.dumps(result,default=str))
