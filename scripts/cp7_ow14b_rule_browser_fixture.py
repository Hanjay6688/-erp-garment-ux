"""Native fabric-rule browser fixtures: disposable browser database only."""
from datetime import date
from urllib.parse import urlparse
import contextlib
import hashlib
import json
import os
import sys
import psycopg
import cp7_ow14b_rule_cases as case


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
                f = case.factory(cur, date.fromisoformat(p['today']))
            out = dict(material=f['material'], sku=f['sku'], name=f['name'], point=str(f['oracle']['point']),
                       free=str(f['oracle']['free']), reference='500')
        elif operation == 'state':
            f = p['fixture']
            evaluation = cur.execute('select to_jsonb(e)from cp7_stock_formula.material_evaluations e where material_id=%s', (f['material'],)).fetchone()
            settings = cur.execute('select revision,fabric_rule,manual_point::text from cp7_stock_formula.material_settings where material_id=%s order by revision desc limit 1', (f['material'],)).fetchone()
            snapshot = case.formula.business(cur)
            out = dict(evaluation=evaluation[0] if evaluation else None,
                       settings=dict(zip(('revision','fabric_rule','manual_point'), settings)) if settings else None,
                       revisions=case.revisions(cur, f),
                       native_hash=hashlib.sha256(json.dumps(snapshot,sort_keys=True,default=str).encode()).hexdigest())
            if p.get('with_source'):
                source = case.combined(cur, p['actor'])
                out.update(alerts=case.mine(source, f), source_state=source['states'].get(f['material']))
        elif operation in ('deactivate', 'restore'):
            cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s', (operation == 'restore', p['actor']))
            out = dict(status='PASS')
        else:
            raise ValueError('UNKNOWN_OW14B_BROWSER_OPERATION')
        case.b.api.admin(cur)
        if not had:
            cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
        conn.commit()
    print(json.dumps(out,default=str))


if __name__ == '__main__':
    main()
