"""Exact read-only before/after observations of the P21 disposable database."""
from pathlib import Path
import json
import os
import re
import sys
from urllib.parse import urlsplit

import psycopg
from psycopg import sql


def write(path, data):
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    encoded = json.dumps(data, ensure_ascii=False, default=str, sort_keys=True, indent=2) + '\n'
    with path.open('x', encoding='utf-8') as file:
        file.write(encoded)


def snapshot(cur):
    cur.execute("set transaction isolation level repeatable read, read only")
    cur.execute("set local time zone 'UTC'")
    relations = cur.execute("""
        select n.nspname, c.relname, c.relkind
        from pg_catalog.pg_class c
        join pg_catalog.pg_namespace n on n.oid=c.relnamespace
        where (n.nspname='erp' or left(n.nspname,4)='cp7_') and c.relkind in ('r','p','S')
        order by n.nspname,c.relname
    """).fetchall()
    tables, sequences = {}, {}
    for schema, name, kind in relations:
        ident = sql.Identifier(schema, name)
        key = f'{schema}.{name}'
        if kind == 'S':
            last, called = cur.execute(sql.SQL("select last_value, is_called from {}").format(ident)).fetchone()
            sequences[key] = [str(last), called]
        else:
            count, digest = cur.execute(sql.SQL("""
                select count(*), encode(sha256(convert_to(coalesce(string_agg(row_hash,'' order by row_hash),''),'UTF8')),'hex')
                from (select encode(sha256(convert_to(to_jsonb(t)::text,'UTF8')),'hex') as row_hash
                      from only {} t) as hashed
            """).format(ident)).fetchone()
            tables[key] = [count, digest]
    required = {'erp.material_stock_movements', 'erp.fg_stock_movements', 'erp.hpp_versions',
                'erp.journal_entries', 'erp.journal_lines', 'erp.cash_accounts', 'cp7_switch_roll.corrections'}
    if len(tables) < 380 or not required.issubset(tables) or not sequences:
        raise ValueError('P21_INSTALLED_OPERATIONAL_CENSUS_INCOMPLETE')
    cash, cogs = cur.execute("""
        select coalesce(sum(l.debit-l.credit) filter (where exists (
                   select 1 from erp.cash_accounts ca where ca.coa_account_id=l.account_id)),0),
               coalesce(sum(l.debit-l.credit) filter (where exists (
                   select 1 from erp.accounting_account_mappings a where a.mapping_key='COGS' and a.account_id=l.account_id)),0)
        from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
        where j.status in ('POSTED','REVERSED')
    """).fetchone()
    raw, fg = cur.execute("""select
        (select coalesce(sum(qty_signed),0) from erp.material_stock_movements),
        (select coalesce(sum(qty_signed),0) from erp.fg_stock_movements)
    """).fetchone()
    totals = dict(cash_idr=str(cash), cogs_idr=str(cogs), raw_movements_net_mixed_units=str(raw),
                  fg_pcs=str(fg), hpp_versions=tables['erp.hpp_versions'][0],
                  ledger_entries=tables['erp.journal_entries'][0], ledger_lines=tables['erp.journal_lines'][0])
    return dict(tables=tables, sequences=sequences, totals=totals)


def observe(label):
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    parsed = urlsplit(target)
    if (parsed.scheme != 'postgresql' or parsed.hostname not in ('127.0.0.1', 'localhost')
            or parsed.port != 54322 or parsed.path != '/cp6_rollback'
            or not re.fullmatch(r'[a-z0-9-]+', label)):
        raise ValueError('P21_STATE_OBSERVER_DISPOSABLE_CLONE_ONLY')
    with psycopg.connect(target, connect_timeout=5) as conn, conn.cursor() as cur:
        result = snapshot(cur)
    output = Path(os.environ['CP7_P21_FOLLOWUP_RAW'])
    write(output / f'state-{label}.json', result)
    return result


if __name__ == '__main__':
    try:
        print(json.dumps(observe(sys.argv[1]), separators=(',', ':')))
    except (ValueError, KeyError, OSError, psycopg.Error) as error:
        print(f'P21_STATE_OBSERVER_FAILED {getattr(error, "sqlstate", None) or type(error).__name__}', file=sys.stderr)
        sys.exit(1)
