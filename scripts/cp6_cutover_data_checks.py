"""Read-only cutover data checks for CP6 (independent audit round 9: W12 part b, W6).

1. UUID quality (W12 b).

Since owner decision D08 (26 Sep 2026) the frontend parsers accept any canonical 8-4-4-4-12 UUID text, the form PostgreSQL's
uuid type produces (src/laundryQcModel.ts uuidPattern, src/accessoryIssue.ts accessoryUuid). Before D08 they accepted only
RFC 9562 versions 1-8 with the RFC variant, and the test seed's a1000000-.../a2000000-... ids made the Laundry/QC and note
pages fail to load (finding F3).

This check reads every uuid column of the erp schema and counts the values that the frontend pattern refuses, plus every
uuid column whose default is not a v4 generator (gen_random_uuid, uuid_generate_v4; a default is where new ids come from).
It also counts, for information only, the values that are not RFC-4122 (non_rfc_values: the pages accepted none of them
before D08 and accept all of them since); these do not change the status.
It only reads: the transaction is put in read-only mode first, so it can run on a cutover drill copy of hosted or legacy
data as well as on the T3 baseline.

Status: CLEAN (no refused value and every uuid default is a v4 generator or none), FOUND (the tables and counts are listed).

2. CASH_BANK aliases (W6). The opening CASH_BANK import is identified per cash_account_id (BA A1), not per COA account. Two
active cash accounts on one COA account would be two opening identities for one ledger balance. The check lists every COA
account that more than one active cash account points to. Status: NONE or FOUND.

Usage: python3 scripts/cp6_cutover_data_checks.py --pgurl postgresql://...   (prints one JSON line per check; exit 0 either way)
       import cp6_cutover_data_checks as checks; checks.uuid_quality(cur); checks.cash_bank_aliases(cur)
"""
import argparse,json
import psycopg
from psycopg import sql

# The frontend's own pattern (src/laundryQcModel.ts uuidPattern, D08), in PostgreSQL regex syntax.
PATTERN='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
# RFC-4122 versions 1-8 with the RFC variant (the frontend's pattern before D08); information only.
RFC_PATTERN='^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
V4_DEFAULTS={'gen_random_uuid()','public.gen_random_uuid()','extensions.gen_random_uuid()','pg_catalog.gen_random_uuid()',
             'uuid_generate_v4()','extensions.uuid_generate_v4()'}
COLUMNS="""select c.table_name,c.column_name,c.column_default from information_schema.columns c
  join information_schema.tables t on t.table_schema=c.table_schema and t.table_name=c.table_name and t.table_type='BASE TABLE'
  where c.table_schema='erp' and c.data_type='uuid' order by 1,2"""


def uuid_quality(cur):
    columns=cur.execute(COLUMNS).fetchall()
    refused={};defaults={};non_rfc={}
    for table,column,default in columns:
        n,r=cur.execute(sql.SQL('select count(*) filter (where {c}::text !~ %s),count(*) filter (where {c}::text !~ %s) from erp.{t} where {c} is not null').format(
            t=sql.Identifier(table),c=sql.Identifier(column)),(PATTERN,RFC_PATTERN)).fetchone()
        if n:refused['%s.%s'%(table,column)]=n
        if r:non_rfc['%s.%s'%(table,column)]=r
        if default is not None and default.strip() not in V4_DEFAULTS:defaults['%s.%s'%(table,column)]=default
    return dict(status='CLEAN' if not refused and not defaults else 'FOUND',pattern=PATTERN,columns_checked=len(columns),
                refused_values=refused,refused_total=sum(refused.values()),non_v4_defaults=defaults,
                non_rfc_values=non_rfc,non_rfc_total=sum(non_rfc.values()),
                reads_only=True,note='Frontend UUID pattern (canonical 8-4-4-4-12, D08) against every erp uuid column; non_rfc_values is information only')


ALIASES="""select c.coa_account_id,count(*),array_agg(c.cash_account_code order by c.cash_account_code)
  from erp.cash_accounts c where c.is_active group by c.coa_account_id having count(*)>1 order by 1"""


def cash_bank_aliases(cur):
    rows=cur.execute(ALIASES).fetchall()
    return dict(status='FOUND' if rows else 'NONE',aliases=[dict(coa_account_id=str(a),cash_accounts=n,codes=list(c)) for a,n,c in rows],
                reads_only=True,note='Active cash accounts sharing one COA account (CASH_BANK opening identity is per cash account)')


def run(cur):
    """Both checks in one read-only transaction."""
    cur.execute('set transaction read only')
    return dict(uuid_quality=uuid_quality(cur),cash_bank_aliases=cash_bank_aliases(cur))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--pgurl',required=True)
    with psycopg.connect(parser.parse_args().pgurl) as conn,conn.cursor() as cur:
        result=run(cur);conn.rollback()
    for name,value in result.items():print(json.dumps(dict(group='CP6_'+name.upper(),**value),default=str),flush=True)
