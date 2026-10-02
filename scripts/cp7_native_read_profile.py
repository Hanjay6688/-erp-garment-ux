"""Read-only diagnosis after an actual disposable browser failure.

This records durations and sizes of real producer stages, never a Native PASS,
synthetic source, extra saved analysis or a relaxed HTTP timeout.
"""
from datetime import date
from time import monotonic
from urllib.parse import urlparse
import json
import os
import sys
import uuid

import psycopg
import cp7_analysis_cases as cases


def main():
    p = json.load(sys.stdin)
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    url = urlparse(target)
    assert url.hostname in ('localhost', '127.0.0.1') and url.path == '/cp6_auditor_browser', 'DISPOSABLE_BROWSER_ONLY'
    report = dict(status='DIAGNOSTIC_INCOMPLETE', diagnostic_only=True,
                  actual_actor=p['actor'], read_only=True, saved_runs_added=0,
                  Native_HTTP_timeout_changed=False, steps=[])
    try:
        with psycopg.connect(target) as conn, conn.cursor() as cur:
            cur.execute('set transaction read only')
            cases.auth.actor(cur, p['actor'])
            # Matches the security-definer producer's actual private principal.
            cur.execute('set local role cp7_capture')
            cur.execute("set local statement_timeout='8s'")
            today = date.fromisoformat(p['today'])
            query = cases.previous.baseline.history.query(today)
            access = cur.execute('select cp7_schedule_native.access_now(false)::text').fetchone()[0]
            started = monotonic()
            source = cur.execute('select cp7_analysis_native.source(cp7_planning.history_query(%s::jsonb))::text',
                                 (json.dumps(query),)).fetchone()[0]
            report['steps'].append(dict(stage='COMPLETE_NATIVE_SOURCE', elapsed_ms=round((monotonic()-started)*1000),
                                        utf8_bytes=len(source.encode('UTF8')),
                                        product_count=len(json.loads(source).get('facts', {}).get('products', []))))
            started = monotonic()
            # Feed the actual SQL JSON text back unchanged; no float roundtrip.
            original = cur.execute('select cp7_analysis_native.build(%s::jsonb,cp7_planning.history_query(%s::jsonb),%s,%s::jsonb)::text',
                                   (source, json.dumps(query), uuid.uuid4(), access)).fetchone()[0]
            report['steps'].append(dict(stage='PURE_NATIVE_COMPILER', elapsed_ms=round((monotonic()-started)*1000),
                                        utf8_bytes=len(original.encode('UTF8')),
                                        status=json.loads(original)['status']))
            started = monotonic()
            cur.execute('select cp7_analysis_native.source(cp7_planning.history_query(%s::jsonb))',
                        (json.dumps(query),)).fetchone()
            report['steps'].append(dict(stage='COMPLETE_NATIVE_SOURCE_AGAIN', elapsed_ms=round((monotonic()-started)*1000)))
            conn.rollback()
            report['status'] = 'READ_ONLY_DIAGNOSTIC_COMPLETE'
    except psycopg.Error as error:
        report.update(sqlstate=error.sqlstate, error=error.diag.message_primary)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
