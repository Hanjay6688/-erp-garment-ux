"""Disposable setup/observation only; browser performs posting and cash writes."""
from datetime import date
from urllib.parse import urlparse
import json
import os
import sys
import psycopg
import f03_independent_cases as audit

target = os.environ['AUDITOR_BROWSER_DB_URL']
u = urlparse(target)
assert u.hostname in ('127.0.0.1','localhost') and u.path == '/cp6_auditor_browser'
op, p = sys.argv[1], json.loads(sys.argv[2])
with psycopg.connect(target) as conn, conn.cursor() as cur:
    had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
    if not had: cur.execute('grant usage on schema erp to authenticated')
    if op == 'create':
        f = audit.seven(cur, date.fromisoformat(p['today']))
        f['bank_code'] = cur.execute('select cash_account_code from erp.cash_accounts where id=%s', (f['bank'],)).fetchone()[0]
        f['cash_coa'] = audit.payments.bank_account(cur, f)
        f['ar_coa'] = audit.command.mapping(cur, 'AR_CUSTOMER')
        out = f
    elif op == 'read':
        out = dict(document=audit.sales.read(cur,p)['detail'], available=audit.command.available(cur,p),
                   accounts={k:str(v) for k,v in audit.gl(cur).items()},
                   payments=audit.payments.cash(cur,p)['payments'])
    else:
        raise ValueError('UNKNOWN_INDEPENDENT_BROWSER_OPERATION')
    audit.b.api.admin(cur)
    if not had: cur.execute('revoke usage on schema erp from authenticated')
    assert cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0] == had
    conn.commit()
print(json.dumps(out, default=str))
