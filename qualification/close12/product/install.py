"""Upgrade or restore the six pinned HPP routines on an installed CP7 Global."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import psycopg
from psycopg import sql

PACKAGE = Path(__file__).resolve().parent


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def read_functions(cur, signatures):
    rows = {}
    for signature in signatures:
        cur.execute("""
            select pg_get_functiondef(oid), oid, proowner, proacl::text, prosecdef,
                   provolatile, proparallel, proleakproof, proisstrict, proretset,
                   prorettype, proargtypes::text, proargmodes, proargnames
            from pg_proc where oid=to_regprocedure(%s)
        """, (signature,))
        row = cur.fetchone()
        if row is None:
            raise ValueError('Missing Global routine ' + signature)
        rows[signature] = row
    return rows


def read_indexes(cur, indexes):
    result = {}
    for name in indexes:
        cur.execute("""
            select pg_get_indexdef(i.indexrelid), i.indisvalid and i.indisready and i.indislive
            from pg_index i where i.indexrelid=to_regclass(%s)
        """, (name,))
        row = cur.fetchone()
        if row:
            if not row[1]:
                raise ValueError('Unusable index ' + name)
            result[name] = row[0]
        elif cur.execute("select to_regclass(%s) is not null", (name,)).fetchone()[0]:
            raise ValueError('Index name in use ' + name)
    return result


def version(rows, signatures, indexes, expected_indexes):
    actual = {key: sha(row[0]) for key, row in rows.items()}
    for side, required in ((0, {}), (1, expected_indexes)):
        if indexes == required and all(actual[k] == signatures[k][side] for k in signatures):
            return side
    raise ValueError('Global HPP definitions or indexes differ from the supported versions')


def apply(conn, direction):
    if direction not in ('up', 'down'):
        raise ValueError('Expected up or down')
    desired = int(direction == 'up')
    manifest = json.loads((PACKAGE / 'manifest.json').read_text())
    signatures, indexes = manifest['functions'], manifest['indexes']
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
        before = read_functions(cur, signatures)
        current = version(before, signatures, read_indexes(cur, indexes), indexes)
        if current == desired:
            return {'direction': direction, 'changed': False}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = {sig: root / (sig.split('(')[0] + '.sql') for sig in signatures}
            for sig, path in paths.items():
                path.write_text(before[sig][0])
            args = ['git', 'apply', '--no-index', '--whitespace=nowarn']
            if not desired:
                args.append('--reverse')
            subprocess.run([*args, str(PACKAGE / 'definitions.patch')], cwd=root, check=True)
            definitions = {sig: path.read_text() for sig, path in paths.items()}
            if any(sha(body) != signatures[sig][desired] for sig, body in definitions.items()):
                raise ValueError('Patched HPP definition differs from the expected release')
            for body in definitions.values():
                cur.execute(body)
        for name, ddl in indexes.items():
            if desired:
                cur.execute(ddl)
            else:
                cur.execute(sql.SQL('drop index {}').format(sql.Identifier(*name.split('.'))))
        after = read_functions(cur, signatures)
        if version(after, signatures, read_indexes(cur, indexes), indexes) != desired:
            raise ValueError('HPP upgrade readback failed')
        if any(before[sig][1:] != after[sig][1:] for sig in signatures):
            raise ValueError('Routine identity, contract or authority changed')
        return {'direction': direction, 'changed': True, 'routines': len(signatures), 'indexes': len(indexes)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('direction', choices=['up', 'down'])
    args = parser.parse_args()
    with psycopg.connect(autocommit=True) as db:
        print(json.dumps(apply(db, args.direction)))
