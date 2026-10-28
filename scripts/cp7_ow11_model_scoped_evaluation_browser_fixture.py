"""Native business controls and immutable-row observations on one disposable copy."""
from datetime import date
from urllib.parse import urlparse
import hashlib
import json
import os
import sys
import psycopg
import cp7_ow11_model_scoped_evaluation_cases as native


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
            f = native.history.history.fixture(cur, today)
            q = native.history.query(cur, f, today)
            out = dict(f, query=q)
        elif op == 'state':
            before = native.plan.monetary_state(cur)
            out = dict(business_sha256=hashlib.sha256(json.dumps(before, sort_keys=True, default=str).encode()).hexdigest())
            for key, table in (('history', 'cp7_model_history_runtime.runs'),
                               ('model', 'cp7_model_scoped_evaluation.runs'),
                               ('legacy_v2', 'cp7_model_registry_adapter.runs')):
                count, digest = cur.execute("select count(*),md5(coalesce(jsonb_agg(to_jsonb(r)order by r.id)::text,'[]'))from " + table + " r where actor=%s", (p['actor'],)).fetchone()
                out[key + '_rows'], out[key + '_hash'] = count, digest
        elif op == 'post':
            native.history.history.sales.fg.post_sale(cur, p['draft'])
            out = dict(status='PASS', actual_posted_sale=True)
        elif op in ('deactivate', 'restore'):
            cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s', (op == 'restore', p['actor']))
            out = dict(status='PASS')
        else:
            raise ValueError('UNKNOWN_SCOPED_MODEL_BROWSER_CONTROL')
        native.plan.b.api.admin(cur)
        if not had:
            cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
        conn.commit()
    print(json.dumps(out, default=str))


if __name__ == '__main__':
    main()
