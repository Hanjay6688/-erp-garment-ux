"""Fixture/state helpers restricted to the disposable Native browser copy."""
from datetime import date
from urllib.parse import urlparse
import contextlib
import json
import os
import sys
import psycopg
import cp7_ow10_reorder_cases as case


def main():
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    url = urlparse(target)
    assert url.hostname in ('localhost', '127.0.0.1') and url.path == '/cp6_auditor_browser', 'DISPOSABLE_BROWSER_ONLY'
    operation, p = sys.argv[1], json.load(sys.stdin)
    with psycopg.connect(target) as conn, conn.cursor() as cur:
        acl = cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not had:
            cur.execute('grant usage on schema erp to authenticated')
        case.b.api.admin(cur)
        if operation == 'prepare':
            with contextlib.redirect_stdout(sys.stderr):
                f, _ = case.configured(cur, date.fromisoformat(p['today']), subject=p['actor'])
                case.refresh(cur, p['actor'])
            out = f
        elif operation == 'state':
            out = dict(row=case.row(cur, dict(product=p['product'])),
                       revisions=cur.execute('select count(*)from cp7_stock_formula.manual_points where root_id=%s', (p['product'],)).fetchone()[0])
        elif operation in ('deactivate', 'restore'):
            cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s', (operation == 'restore', p['actor']))
            out = dict(status='PASS')
        else:
            raise ValueError('UNKNOWN_OW10R_BROWSER_OPERATION')
        case.b.api.admin(cur)
        if not had:
            cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
        conn.commit()
    print(json.dumps(out, default=str))


if __name__ == '__main__':
    main()
