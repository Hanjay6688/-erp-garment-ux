"""Disposable state reader for the PL-5 B history yield policy browser cases; browser observations never change facts."""
from urllib.parse import urlparse
import os, sys, json
import psycopg


def main():
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    url = urlparse(target)
    assert url.hostname in ('localhost', '127.0.0.1') and url.path == '/cp6_auditor_browser', 'DISPOSABLE_BROWSER_ONLY'
    op, _ = sys.argv[1], json.load(sys.stdin)
    with psycopg.connect(target) as conn, conn.cursor() as cur:
        if op != 'state':
            raise ValueError('UNKNOWN_PL5_HISTORY_YIELD_BROWSER_CONTROL')
        revisions, latest, commands = cur.execute("""select count(*),coalesce(max(revision),0),(select count(*)from cp7_yield_policy.commands)
          from cp7_yield_policy.policies""").fetchone()
        state = cur.execute('select state from cp7_yield_policy.policies order by revision desc limit 1').fetchone()
        conn.rollback()
    print(json.dumps(dict(revisions=revisions, latest=latest, commands=commands, state=state[0] if state else None)))


if __name__ == '__main__':
    main()
