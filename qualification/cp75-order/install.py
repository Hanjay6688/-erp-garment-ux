"""Install or restore the ordered-window check on an existing Global database."""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import psycopg

PACKAGE = Path(__file__).resolve().parent
ROUTINE = 'cp7_reminders.workspace(jsonb)'
BEFORE = 'd88aec0885339e4271c6ac509bda457b57c0b45410f628ad81d0952c8912681a'
AFTER = '619183f4ccdb1c6a7a491cd189f787e73ca6e472ce42ef376acc3021d6cff772'


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def read(cur):
    row = cur.execute("""
        select pg_get_functiondef(oid), prosrc, oid, proowner, proacl::text,
               prosecdef, provolatile, proparallel, proisstrict, proconfig
        from pg_proc where oid = to_regprocedure(%s)
    """, (ROUTINE,)).fetchone()
    if row is None:
        raise ValueError('Manual reminders workspace is missing')
    return row


def apply(conn, direction):
    if direction not in ('up', 'down'):
        raise ValueError('Expected up or down')
    source, target = (BEFORE, AFTER) if direction == 'up' else (AFTER, BEFORE)
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("select pg_advisory_xact_lock(hashtextextended('cp7_reminders.workspace(jsonb)',0))")
        original = read(cur)
        ddl, body = original[:2]
        actual = sha(body)
        if actual == target:
            return {'direction': direction, 'changed': False, 'body_sha256': target}
        if actual != source or ddl.count(body) != 1:
            raise ValueError('Unsupported reminder workspace definition')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'workspace.body'
            path.write_text(body + '\n')
            args = ['git', 'apply', '--no-index', '--whitespace=nowarn']
            if direction == 'down':
                args.append('--reverse')
            subprocess.run([*args, str(PACKAGE / 'workspace.patch')], cwd=temp, check=True)
            replacement = path.read_text().removesuffix('\n')
        if sha(replacement) != target:
            raise ValueError('Reminder workspace patch does not match the pinned version')
        cur.execute(ddl.replace(body, replacement))
        installed = read(cur)
        if sha(installed[1]) != target or installed[2:] != original[2:]:
            raise ValueError('Reminder workspace body, identity or permissions differ after installation')
        return {'direction': direction, 'changed': True, 'body_sha256': target}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('direction', choices=('up', 'down'))
    args = parser.parse_args()
    with psycopg.connect(autocommit=True) as db:
        print(json.dumps(apply(db, args.direction)))
