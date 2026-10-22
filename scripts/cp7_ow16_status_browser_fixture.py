"""Native cutting-only browser fixture on the disposable browser database."""
from datetime import date
from urllib.parse import urlparse
import contextlib
import hashlib
import json
import os
import sys
import psycopg
import cp7_ow16_status_cases as case


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
                f = case.factory(cur, date.fromisoformat(p['today']), draft=True)
            out = dict(group=f['group'], group_number=f['group_number'], material=f['material'], roll=f['roll'], po=f['po'])
        elif operation == 'state':
            f = p['fixture']
            current = cur.execute('select material_issue_posted,cp7_planning.utc(cut_at)from erp.cutting_groups where id=%s', (f['group'],)).fetchone()
            quantities = cur.execute('select sum(qty_signed),sum(qty_signed*unit_cost_snapshot)from erp.material_stock_movements '
                                     'where material_id=%s', (f['material'],)).fetchone()
            snapshot = case.b.boundary.snapshot(cur)
            out = dict(posted=current[0], physical_at=current[1], raw_qty=quantities[0], raw_value=quantities[1],
                       native_hash=hashlib.sha256(json.dumps(snapshot,sort_keys=True,default=str).encode()).hexdigest(),
                       policy_revisions=cur.execute('select count(*)from cp7_cutting_status.policies').fetchone()[0],
                       own_requests=cur.execute('select count(*)from cp7_cutting_status.requests where actor=%s',(p['actor'],)).fetchone()[0])
        elif operation in ('deactivate', 'restore'):
            cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s', (operation == 'restore', p['actor']))
            out = dict(status='PASS')
        else:
            raise ValueError('UNKNOWN_OW16_BROWSER_OPERATION')
        case.b.api.admin(cur)
        if not had:
            cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
        conn.commit()
    print(json.dumps(out,default=str))


if __name__ == '__main__':
    main()
