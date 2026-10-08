"""Disposable Native business setup for the plan v2 browser cases; browser observations never change facts."""
from datetime import date
from urllib.parse import urlparse
import os, sys, json
import psycopg
import cp7_p19_plan_v2_cases as cases


def main():
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    url = urlparse(target)
    assert url.hostname in ('localhost', '127.0.0.1') and url.path == '/cp6_auditor_browser', 'DISPOSABLE_BROWSER_ONLY'
    op, p = sys.argv[1], json.load(sys.stdin)
    with psycopg.connect(target) as conn, conn.cursor() as cur:
        had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl = cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:
            cur.execute('grant usage on schema erp to authenticated')
        if op == 'prepare':
            # v1's plan fixture through the ordinary Native writers; the staged run is the browser's own.
            x = cases.fixture(cur, date.fromisoformat(p['today']))
            sku, name = cur.execute('select sku,product_name from erp.products where id=%s', (x['root'],)).fetchone()
            out = dict(target_key=x['target'], root=x['root'], po_id=x['po'], location_id=str(x['fabric']['location']),
                       material_id=str(x['fabric']['material']), label=f'{sku} · {name}')
        elif op == 'state':
            q = lambda sql: cur.execute(sql, (p['actor'],)).fetchone()[0]
            out = dict(drafts=q('select count(*)from cp7_plan_native.drafts where actor=%s'),
                       staged_drafts=q('select count(*)from cp7_plan_native.staged_drafts s join cp7_plan_native.drafts d on d.id=s.draft_id where d.actor=%s'),
                       intents=q('select count(*)from cp7_plan_native.intents where actor=%s'),
                       domain_drafts=cur.execute('select count(*)from erp.cutting_groups where not material_issue_posted').fetchone()[0])
        elif op in ('deactivate', 'restore'):
            cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s', (op == 'restore', p['actor']))
            out = dict(status='PASS')
        else:
            raise ValueError('UNKNOWN_PLAN_V2_BROWSER_CONTROL')
        cases.b.api.admin(cur)
        if not had:
            cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
        conn.commit()
    print(json.dumps(out, default=str))


if __name__ == '__main__':
    main()
