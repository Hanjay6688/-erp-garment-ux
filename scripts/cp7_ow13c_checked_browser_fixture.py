"""Loopback disposable Native setup/observations for checked-save browser controls."""
from datetime import date
from urllib.parse import urlparse
import json
import os
import sys
import psycopg
import cp7_p19_plan_v2_cases as plan


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
            today = date.fromisoformat(p['today'])
            x = plan.fixture(cur, today)
            sku, name = cur.execute('select sku,product_name from erp.products where id=%s', (x['root'],)).fetchone()
            out = dict(target_key=x['target'], root=x['root'], po_id=x['po'], location_id=str(x['fabric']['location']),
                       material_id=str(x['fabric']['material']), label=f'{sku} · {name}', query=plan.staged.query(today))
        elif op == 'state':
            q = lambda sql: cur.execute(sql, (p['actor'],)).fetchone()[0]
            out = dict(drafts=q('select count(*)from cp7_plan_native.drafts where actor=%s'),
                       receipts=q('select count(*)from cp7_cutting_checked.receipts where actor=%s'),
                       intents=q('select count(*)from cp7_plan_native.intents where actor=%s'),
                       monetary=plan.monetary_state(cur))
        elif op == 'stock':
            # The unchanged Native stock writer, never a raw balance update.
            plan.found_fg(cur, dict(root=p['root']), '1')
            out = dict(status='PASS', actual_Native_stock_writer=True)
        elif op in ('deactivate', 'restore'):
            cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s', (op == 'restore', p['actor']))
            out = dict(status='PASS')
        else:
            raise ValueError('UNKNOWN_CHECKED_SAVE_BROWSER_CONTROL')
        plan.b.api.admin(cur)
        if not had:
            cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
        conn.commit()
    print(json.dumps(out, default=str))


if __name__ == '__main__':
    main()
