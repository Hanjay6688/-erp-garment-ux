"""Native disposable redye setup and exact read-only browser projection oracle."""
import json
import os
import sys
from datetime import date
from urllib.parse import urlparse
import psycopg
import cp7_f03_redye_cases as cases


def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in ('localhost','127.0.0.1') and url.path=='/cp6_auditor_browser'
    op,p=sys.argv[1],json.loads(sys.argv[2])
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if op=='prepare':
            if not had:cur.execute('grant usage on schema erp to authenticated')
            out=cases.fixture(cur,date.fromisoformat(p['today']))
            out['before']=cases.regroup(cur,out)
        elif op=='read':out=cases.observe(cur,p)
        elif op=='verify-price':
            out=cases.assert_first_price(cur,p,p['before'])
        elif op=='verify-card':
            actual=p['card']
            assert actual['page']['offset']==0 and actual['page']['limit']==25
            assert actual['page']['next_offset'] is None
            assert actual['contract_version']=='cp7.fg-ledger.v2'
            position=cases.position(p)
            cases.x04.fg.p02.actor(cur)
            query=dict(product_id=position['product'],lot_id=position['lot'],location_id=position['location'],quality_grade='GRADE_A',purpose='CARD',limit=25,offset=0)
            expected=cur.execute('select public.erp_cp7_get_fg_ledger_v2(%s::jsonb)',(json.dumps(query),)).fetchone()[0]
            cases.b.api.admin(cur)
            assert cases.x04.canonical_card(actual['page'])==cases.x04.canonical_card(expected['page'])
            assert actual['balances']==expected['balances'] and actual['position']==expected['position']
            out=dict(status='PASS',exact_native_public_reader_card_match=True)
        elif op=='verify-report':
            expected=cases.observe(cur,p)['report'];actual=p['report']
            for key in ('financial_position','performance','data_confidence'):
                assert actual['snapshot'][key]==expected['snapshot'][key]
            out=dict(status='PASS',exact_native_public_reader_money_and_readiness_match=True)
        else:raise ValueError('Unknown X04 redye fixture operation')
        cases.b.api.admin(cur)
        if op=='prepare' and not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))


if __name__=='__main__':main()
