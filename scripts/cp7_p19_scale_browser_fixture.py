"""P19 scale ladder on the disposable browser copy: ordinary Native writers only, then read-back.

prepare  grows the copy to the declared size, one writer call per committed
         transaction as the real app runs one RPC per transaction (no lock
         accumulation; no lock or other limit is changed).
measure  one size of the SQL ladder plus the phase profile, in one transaction
         that is rolled back (captures and Originals are not kept). Called only
         after that size's measured clicks.
observe  database read-back of one click (read only).
"""
from datetime import date
from urllib.parse import urlparse
import json
import os
import sys

import psycopg

import cp7_p19_scale_cases as scale

ACL = "select nspacl::text from pg_namespace where nspname='erp'"
USAGE = "select has_schema_privilege('authenticated','erp','USAGE')"


def main():
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    url = urlparse(target)
    assert url.hostname in ('localhost', '127.0.0.1') and url.path == '/cp6_auditor_browser', 'DISPOSABLE_BROWSER_ONLY'
    op, p = sys.argv[1], json.load(sys.stdin)
    with psycopg.connect(target) as conn, conn.cursor() as cur:
        acl, had = cur.execute(ACL).fetchone()[0], cur.execute(USAGE).fetchone()[0]
        try:
            if op == 'prepare':
                # Test-only USAGE for the accepted CP6 writer helpers that call erp.* as
                # an ordinary user; it is revoked below even when seeding fails.
                if not had:
                    cur.execute('grant usage on schema erp to authenticated')
                today = date.fromisoformat(p['today'])
                out = scale.ensure(cur, today, int(p['size']), bool(p['wip_done']), commit=conn.commit)
                out['history_source'] = scale.source_cap(cur)
                out['expected_caps_by_days'] = {str(days): scale.expected_caps(out['total_targets'], days)
                                                for days in scale.HISTORY_DAYS}
                out['caps'] = scale.CAPS
            elif op == 'measure':
                # Production privileges: no test-only grant for the measured calls.
                out = scale.measure(cur, date.fromisoformat(p['today']), int(p['size']))
            elif op == 'observe':
                out = scale.observe(cur, p['actor'], p['requests'], p.get('run_id'), p['label'])
            else:
                raise ValueError('UNKNOWN_P19_SCALE_BROWSER_ACTION')
        finally:
            # measure/observe keep nothing; prepare loses only an unfinished writer call.
            conn.rollback()
            scale.b.api.admin(cur)
            if not had and cur.execute(USAGE).fetchone()[0]:
                cur.execute('revoke usage on schema erp from authenticated')
            conn.commit()
            assert cur.execute(ACL).fetchone()[0] == acl, 'P19S_BROWSER_COPY_ERP_ACL_CHANGED'
    print(json.dumps(out, default=str))


if __name__ == '__main__':
    main()
