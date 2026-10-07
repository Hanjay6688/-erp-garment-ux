"""P19 scale ladder on the disposable browser copy: ordinary Native writers only, then read-back."""
from datetime import date
from urllib.parse import urlparse
import json
import os
import sys

import psycopg

import cp7_p19_scale_cases as scale


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
            out = scale.ensure(cur, today, int(p['size']), bool(p['wip_done']))
            out['history_source'] = scale.source_cap(cur)
            out['expected_caps_by_days'] = {str(days): scale.expected_caps(out['total_targets'], days)
                                            for days in scale.HISTORY_DAYS}
            out['caps'] = scale.CAPS
        elif op == 'observe':
            out = scale.observe(cur, p['actor'], p['requests'], p.get('run_id'), p['label'])
        else:
            raise ValueError('UNKNOWN_P19_SCALE_BROWSER_ACTION')
        scale.b.api.admin(cur)
        if not had:
            cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
        conn.commit()
    print(json.dumps(out, default=str))


if __name__ == '__main__':
    main()
