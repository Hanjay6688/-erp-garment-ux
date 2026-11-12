"""Reconstruct the ERP schema from the retained disposable AB clone dump."""

from hashlib import sha256
import json
import re
from zipfile import ZipFile


COPY = re.compile(rb'^COPY [^\n]+ FROM stdin;\n', re.MULTILINE)


def original(archive):
    with ZipFile(archive) as bundle:
        raw = bundle.read('CLONE_install.clone-erp.sql')
        assert raw == bundle.read('CLONE_install.source-erp.sql')
        catalogue = bundle.read('SKU_GLOBAL_PARENT_ACTUAL_FULL25.json')
    assert len(raw) == 5385610
    assert sha256(catalogue).hexdigest() == '5ff582717522b766c12024c1bf3299066475f14a3c6021a3543f378f829e0c07'
    return raw, json.loads(catalogue)


def restore(conn, raw, catalogue):
    funcs = dict(catalogue['functions'])
    conn.execute('create role anon; create role authenticated; create role service_role; '
                 'create schema auth; create schema extensions; create extension pgcrypto with schema extensions; '
                 'create table auth.users(id uuid primary key)', prepare=False)
    for signature in ('auth.uid()', 'auth.jwt()', 'auth.role()'):
        conn.execute(funcs[signature][0])
    # psql's restrict wrappers protect the file as a script. This reader sends
    # the archived SQL and COPY records through the PostgreSQL wire protocol.
    sql = re.sub(rb'^\\(?:un)?restrict [^\n]+\n', b'', raw, flags=re.MULTILINE)
    previous = 0
    count = 0
    with conn.cursor() as cursor:
        for match in COPY.finditer(sql):
            cursor.execute(sql[previous:match.start()].decode(), prepare=False)
            end = sql.index(b'\n\\.\n', match.end() - 1)
            with cursor.copy(match[0].decode()) as copy:
                copy.write(sql[match.end():end + 1])
            previous = end + 4
            count += 1
        cursor.execute(sql[previous:].decode(), prepare=False)
    return count
