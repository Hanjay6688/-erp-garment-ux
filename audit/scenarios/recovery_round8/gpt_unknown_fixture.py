"""Known nonzero laundry/QC source on the browser's disposable copy only.
Upstream fixture uses existing native business commands, no direct quantity edit.
Temporary schema usage is restored before actual browser actors run.
"""
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit
import json, os, sys
import psycopg

sys.path.insert(0, str(Path.cwd() / 'scripts'))
sys.path.append(str(Path.cwd().parent / 'auditor/scripts'))
import cp6_aw_probe as awp


def fixture(scope, today):
    url = os.environ['AUDITOR_BROWSER_DB_URL']
    assert urlsplit(url).path == '/cp6_auditor_browser'
    with psycopg.connect(url) as conn, conn.cursor() as raw:
        cur = awp.OrdinaryDraftCursor(raw)
        awp.api.admin(cur)
        before = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not before:
            cur.execute('grant usage on schema erp to authenticated')
        awp.chain.production.prior.set_open_period(cur, today - timedelta(days=4))
        f = awp.r1.production(cur, today)
        if scope == 'QC':
            awp.r1.receipt(cur, f, awp.chain.production.at(f['day'], 13), 0)
        awp.api.admin(cur)
        if not before:
            cur.execute('revoke usage on schema erp from authenticated')
        after = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        assert before == after
        out = dict(scope=scope, delivery=str(f['delivery']), group=str(f['group']),
                   expected_source_pcs=10, schema_usage_before=before, schema_usage_after=after)
        conn.commit()
    return out


if __name__ == '__main__':
    print(json.dumps(fixture(sys.argv[1], date.fromisoformat(sys.argv[2])), default=str))
