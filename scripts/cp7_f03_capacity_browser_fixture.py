"""Actual disposable stock sources and read-only full-capacity UI observations."""
from datetime import date
from urllib.parse import urlparse
import json
import os
import sys
import psycopg
import cp7_f03_capacity_cases as cases


def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in ('127.0.0.1','localhost') and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    op,p=sys.argv[1],json.loads(sys.argv[2])
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if op=='prepare':
            if not had: cur.execute('grant usage on schema erp to authenticated')
            out=cases.fixture(cur,date.fromisoformat(p['today']));out['before']=cases.observe(cur,out)
            out['mapping']={k:cases.cmd.mapping(cur,k) for k in ('AR_CUSTOMER','SALES_REVENUE','FG_INVENTORY','COGS')}
            if p.get('ops'):
                role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
                cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
                for key in ('warehouse.fg.view','warehouse.stock.view'):
                    cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,key))
        elif op=='read': out=cases.observe(cur,p)
        elif op=='verify-pages':
            pages=p['pages'];assert [len(x['page']['rows']) for x in pages]==[25,5]
            assert [x['page']['next_offset'] for x in pages]==[25,None]
            assert all(x['page']['total']=='30' for x in pages)
            rows=[r for x in pages for r in x['page']['rows']]
            assert len({r['lot_id'] for r in rows})==30 and set(r['lot_id'] for r in rows)==set(p['lots'])
            actual=cases.observe(cur,p)
            assert all(cases.fg.qty(x)==actual['qty'] for x in pages)
            if p.get('ops'):
                for page in pages: assert page['financial_captured'] is False;cases.no_money(page)
            else:
                expected=cases.page_pair(cur,p)
                for page,want in zip(pages,expected): assert cases.x04.canonical_card(page['page'])==cases.x04.canonical_card(want['page'])
            out=dict(status='PASS',complete_lots=30,qty=actual['qty'])
        elif op=='verify-card':
            card=p['card'];assert card['financial_captured'] is False;cases.no_money(card)
            assert card['position']['lot_id'] in p['lots'] and card['balances']['physical_qty']=='1'
            assert card['contract_version']=='cp7.fg-ledger.v2'
            cases.auth.actor(cur)
            query=dict(product_id=p['product'],lot_id=card['position']['lot_id'],location_id=p['location'],quality_grade='GRADE_A',purpose='CARD',limit=25,offset=0)
            expected=cur.execute('select public.erp_cp7_get_fg_ledger_v2(%s::jsonb)',(json.dumps(query),)).fetchone()[0]
            cases.b.api.admin(cur)
            strip=lambda x:[{k:v for k,v in r.items() if k!='valuation'} for r in x['page']['rows']]
            assert cases.x04.canonical_card(strip(card))==cases.x04.canonical_card(strip(expected))
            out=dict(status='PASS',actual_card_redacted=True)
        elif op=='verify-posted': out=cases.assert_posted(cur,p,p['before']);out['status']='PASS'
        elif op=='revoke-ops':
            role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
            cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
            out=dict(status='PASS',source=cases.observe(cur,p))
        else: raise ValueError('Unknown capacity fixture operation')
        cases.b.api.admin(cur)
        if not had and op=='prepare': cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))


if __name__=='__main__': main()
