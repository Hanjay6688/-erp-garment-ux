"""Only accepted E01 Native controls on the isolated browser database."""
from datetime import date
from urllib.parse import urlparse
import contextlib
import io
import hashlib
import json
import os
import sys

import psycopg
import cp7_p18_e01_bridge_cases as cases


def main():
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    url = urlparse(target)
    assert url.hostname in ('localhost', '127.0.0.1') and url.path == '/cp6_auditor_browser', 'DISPOSABLE_BROWSER_ONLY'
    operation, payload = sys.argv[1], json.load(sys.stdin)
    with psycopg.connect(target) as conn, conn.cursor() as cur:
        had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl = cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:
            cur.execute('grant usage on schema erp to authenticated')
        if operation == 'prepare':
            # The worksheet prints checkpoints; retain them inside the returned
            # trace without corrupting the fixture's one JSON response.
            with contextlib.redirect_stdout(io.StringIO()):
                fixture, trace = cases.prepare(cur, date.fromisoformat(payload['today']))
            result = dict(fixture=fixture, trace=trace)
        elif operation == 'inverse':
            result = cases.inverse(cur, payload['fixture'])
            cases.literal(cur, payload['fixture'], '375.00')
        elif operation in ('deactivate', 'restore'):
            cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',
                        (operation == 'restore', payload['actor']))
            result = dict(status='PASS')
        elif operation == 'state':
            f = payload['fixture']
            detail = cases.worksheet.source.read(cur, f)['detail']
            result = dict(physical=cases.worksheet.physical(cur, f), financial=detail['financial'],
                          analysis_count=cur.execute('select count(*) from cp7_analysis_native.runs where actor=%s',
                                                     (payload['actor'],)).fetchone()[0],
                          appendix_count=cur.execute('select count(*) from cp7_reminder_native.obligation_reports where actor=%s',
                                                     (payload['actor'],)).fetchone()[0])
            cases.b.api.admin(cur)
            snapshot = cases.b.boundary.snapshot(cur)
            result['operational_boundary_sha256'] = hashlib.sha256(
                json.dumps(snapshot, sort_keys=True, separators=(',', ':'),
                           default=str).encode()).hexdigest()
        else:
            raise ValueError('UNKNOWN_E01_BRIDGE_FIXTURE_ACTION')
        cases.b.api.admin(cur)
        if not had:
            cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
        conn.commit()
    print(json.dumps(result, default=str))


if __name__ == '__main__':
    main()
