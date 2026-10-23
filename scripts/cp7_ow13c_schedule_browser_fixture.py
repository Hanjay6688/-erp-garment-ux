"""Only loopback disposable setup and observations; browser uses real RPCs."""
from datetime import date
from urllib.parse import urlparse
import json
import os
import sys
import psycopg
import cp7_ow13c_schedule_cases as work


def main():
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    url = urlparse(target)
    assert url.hostname in ('localhost', '127.0.0.1') and url.path == '/cp6_auditor_browser'
    op, p = sys.argv[1], json.load(sys.stdin)
    with psycopg.connect(target) as conn, conn.cursor() as cur:
        had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl = cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:
            cur.execute('grant usage on schema erp to authenticated')
        if op == 'prepare':
            today = date.fromisoformat(p['today'])
            x = work.plan.fixture(cur, today)
            config = cur.execute('select config from cp7_schedule_native.plans order by revision desc limit 1').fetchone()[0]
            out = dict(root=x['root'], query=work.plan.staged.query(today), config=config)
        elif op == 'state':
            work.plan.b.api.admin(cur)
            out = dict(plans=cur.execute('select count(*)from cp7_schedule_native.plans where actor=%s', (p['actor'],)).fetchone()[0],
                       commands=cur.execute('select count(*)from cp7_schedule_native.commands where actor=%s', (p['actor'],)).fetchone()[0],
                       physical=work.plan.monetary_state(cur))
        elif op == 'stock':
            work.plan.found_fg(cur, dict(root=p['root']), '1')
            out = dict(actual_Native_stock_writer=True)
        elif op in ('deactivate', 'restore'):
            cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s', (op == 'restore', p['actor']))
            out = dict(status='PASS')
        else:
            raise ValueError('UNKNOWN_WORK_SCHEDULE_BROWSER_CONTROL')
        work.plan.b.api.admin(cur)
        if not had:
            cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
        conn.commit()
    print(json.dumps(out, default=str))


if __name__ == '__main__':
    main()
