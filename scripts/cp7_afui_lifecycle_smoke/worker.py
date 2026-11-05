"""Exercise Afui report, transport and recovery code with an empty local fixture."""
import ast
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace

import psycopg
from psycopg import sql

from clock_window import require_window

SOURCE = Path(os.environ['GITHUB_WORKSPACE']) / 'frozen-afui'
OUT = Path(os.environ['GITHUB_WORKSPACE']) / 'auditor/cp6-proof/t3'
HEAD = '8db63458282d7d4cec79ea89c81d2480b51435a5'
DB = 'cp6_rollback'
DUMP = '/tmp/cp7-afui-smoke-pre.dump'
RUN = os.environ['GITHUB_RUN_ID']
CONTAINER = 'cp7-afui-smoke-' + RUN
FIRST = sha256(b'CP7_AFUI_ISOLATED_FIXTURE_FIRST_FAILURE').hexdigest() + '.jsonl'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def extract(relative, expected, names, bindings):
    path = SOURCE / relative
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == expected, 'AFUI_SMOKE_EXACT_RECOVERY_SOURCE:' + relative)
    nodes = []
    for node in ast.parse(raw).body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(n, ast.Name) and n.id in names for n in node.targets):
            nodes.append(node)
    require(len(nodes) == len(names), 'AFUI_SMOKE_EXACT_RECOVERY_CALLABLES')
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), bindings)
    return SimpleNamespace(**{name: bindings[name] for name in names})


def fixture_connection():
    require(os.environ.get('GITHUB_REF') == 'refs/heads/astra-a/afui-lifecycle-smoke-20261106'
            and RUN.isdecimal() and os.environ.get('AFUI_SMOKE_CONTAINER') == CONTAINER,
            'AFUI_SMOKE_ISOLATED_RUNNER_ONLY')
    require(subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip() == HEAD,
            'AFUI_SMOKE_EXACT_FROZEN_HEAD')
    label = subprocess.check_output(['docker', 'inspect', '-f', '{{ index .Config.Labels "cp7-afui-smoke" }}',
                                     CONTAINER], text=True).strip()
    port, password = os.environ['AFUI_SMOKE_PG_PORT'], os.environ['AFUI_SMOKE_PG_PASSWORD']
    listening = subprocess.check_output(['docker', 'port', CONTAINER, '5432/tcp'], text=True).strip()
    require(label == RUN and port.isdecimal() and listening == '127.0.0.1:' + port
            and re.fullmatch(r'[a-f0-9]{48}', password), 'AFUI_SMOKE_FIXED_LOOPBACK_FIXTURE_REQUIRED')
    return 'postgresql://postgres:' + password + '@127.0.0.1:' + port + '/' + DB


def fixture(dsn):
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        require(cur.execute("select current_database(), current_setting('server_version_num')").fetchone()
                == (DB, '170006'), 'AFUI_SMOKE_EXACT_DISPOSABLE_POSTGRES_17_6')
        cur.execute("""
            create role cp7_smoke_reader nologin;
            create schema smoke;
            create schema graphql;
            create schema graphql_public;
            grant usage on schema smoke, graphql, graphql_public to cp7_smoke_reader;
            create table smoke.witness(id bigint generated always as identity primary key,
                                      amount numeric(12,2) not null check (amount >= 0));
            insert into smoke.witness(amount) values (7.25), (11.50);
            grant select on smoke.witness to cp7_smoke_reader;
            alter database cp6_rollback connection limit 12;
            alter database cp6_rollback set timezone to 'UTC';
            alter role cp7_smoke_reader in database cp6_rollback set statement_timeout to '2s';
        """)


def observe(dsn, drill, restore):
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        rows = cur.execute('select id,amount::text from smoke.witness order by id').fetchall()
        seq = cur.execute('select last_value,is_called from smoke.witness_id_seq').fetchone()
        auth = cur.execute("""select has_table_privilege('cp7_smoke_reader','smoke.witness','SELECT'),
                                    has_table_privilege('cp7_smoke_reader','smoke.witness','UPDATE')""").fetchone()
        day = cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date::text").fetchone()[0]
        cur.execute('set local role cp7_smoke_reader')
        require(cur.execute('select count(*) from smoke.witness').fetchone() == (len(rows),), 'AFUI_SMOKE_READER_REQUIRED')
        try:
            cur.execute('update smoke.witness set amount=0')
        except psycopg.errors.InsufficientPrivilege:
            conn.rollback()
        else:
            raise ValueError('AFUI_SMOKE_WRONG_ACTOR_WRITE_SUCCEEDED')
    return dict(rows=rows, sequence=seq, permission_matrix=auth, wib_day=day,
                data=drill.data_hashes(DB), profile=restore._database_profile(DB))


class IntentionalFixtureFailure(Exception):
    pass


def main():
    dsn = fixture_connection()
    sys.path.insert(0, str(SOURCE / 'scripts'))
    from cp7_accessory_nonpayable import complete_original_io as io, lossless_state, progress, state_prepare

    io.OUT = OUT
    drill = extract('scripts/cp6_t3_backup_restore_drill.py',
        'dc64f7c2079cfff2aa585d8edbc6474a185913f042576fc3cc65dfc870dca94f',
        {'docker', 'url', 'data_hashes', 'CRON_ERROR'},
        dict(CONTAINER=CONTAINER, boundary=SimpleNamespace(ADMIN=dsn), subprocess=subprocess, psycopg=psycopg, sql=sql, re=re))
    restore = extract('scripts/ow04-payment-used-restore-qualification/restore_database.py',
        'dd1f9eacecaf3b933e64866c449881187a0670148b54b4d3562bef3d63bd28bc',
        {'_restore', '_database_profile', '_platform_schema_authority', '_roles'},
        dict(SOURCE=DB, RESTORED='ow04_payment_restore', PLATFORM_SCHEMAS=('graphql', 'graphql_public'),
             drill=drill, psycopg=psycopg, sql=sql))
    backup = extract('scripts/cp7_p21_full_rehearsal_probe.py',
        '849968a4cbc636bed3d4c24a880bc0207dc6aa24642a1a8a6dddd441bce93b53', {'dump'}, dict(drill=drill))
    role_cleanup = extract('scripts/current-choice-finance-cron-qualification/restore_roles.py',
        'c9d91b2acfbe33dcc750188427b3bc209a722d219f77f47dbf40ae685d0beefb', {'restore_roles'}, dict(sql=sql))

    def save(name, value):
        target = OUT / name
        pin = io.save_sorted(target, value, 'AFUI_SMOKE_FIRST_ORIGINAL_CONFLICT')
        io.publish(target)
        return pin

    window = require_window(SOURCE)
    report = dict(status='INCOMPLETE', financial_cases=0, production_go=False, runtime_head=HEAD, window=window)
    with progress.phase('WHOLE_PACKAGE'):
        fixture(dsn)
        before = observe(dsn, drill, restore)
        require(before['wib_day'] == window['business_day'] and before['permission_matrix'] == (True, False),
                'AFUI_SMOKE_DATE_AND_ACTOR_MATRIX_REQUIRED')
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            roles_before = restore._roles(cur)
        report['dump_bytes'] = backup.dump(DB, DUMP)
        require(report['dump_bytes'] > 0, 'AFUI_SMOKE_COMPLETE_BACKUP_REQUIRED')
        try:
            with progress.phase('COMPLETE_STATE_PREREQUISITE'):
                shared = [list(row) for row in before['rows']]
                prepared = state_prepare.prepare({'rows': shared, 'same': shared}, OUT, save)
                cache, original = prepared['browser_settings_cache_original'], prepared['browser_settings_state_original']
                fresh = lossless_state.read(OUT / cache['name'], cache['sha256'], OUT / original['name'], original['sha256'])
                require(lossless_state.graph_pin(fresh) == prepared['graph'] and fresh['rows'] is fresh['same'],
                        'AFUI_SMOKE_COLD_READ_MUST_KEEP_EVERY_VALUE_AND_ALIAS')
                report['cold_read'] = dict(original=original, cache=cache, graph=prepared['graph'])
            with progress.phase('NATIVE_CASE', 'ISOLATED_LIFECYCLE_FIXTURE'):
                with psycopg.connect(dsn) as conn, conn.cursor() as cur:
                    cur.execute("insert into smoke.witness(amount) values (101.25); create role cp7_smoke_transient nologin")
                changed = observe(dsn, drill, restore)
                require(changed['data'] != before['data'] and changed['sequence'] != before['sequence'],
                        'AFUI_SMOKE_COMMITTED_CHANGE_REQUIRED')
                raise IntentionalFixtureFailure('AFUI_SMOKE_EXPECTED_STOP_AFTER_COMMITTED_FIXTURE_CHANGE')
        except Exception as error:
            report['first_failure'] = save(FIRST, dict(status='FIRST_FIXTURE_FAILURE_RETAINED',
                expected=isinstance(error, IntentionalFixtureFailure), error_type=type(error).__name__,
                error=str(error), actual_case_credit=0, production_go=False))
            if not isinstance(error, IntentionalFixtureFailure):
                raise
        finally:
            report['restore'] = restore._restore(DUMP, DB, before['profile'])
            require(report['restore']['exit'] == 0 and report['restore']['only_pg_cron_errors'],
                    'AFUI_SMOKE_ACTUAL_RESTORE_FAILED')
            with psycopg.connect(dsn) as conn, conn.cursor() as cur:
                report['roles'] = role_cleanup.restore_roles(cur, roles_before, {'cp7_smoke_transient'}, restore._roles)
            require(observe(dsn, drill, restore) == before, 'AFUI_SMOKE_AFTER_RESTORE_NOT_IDENTICAL')
        report.update(status='PASS_ISOLATED_SHORT_LIFECYCLE', actual_fixture_rows_sequence_acl_profile_restored=True)
        io.save_sorted(OUT / 'AFUI_LIFECYCLE_SMOKE_RESULT.json', report, 'AFUI_SMOKE_FIRST_RESULT_CONFLICT')
        print(json.dumps(dict(status=report['status'], actual_case_credit=0)), flush=True)


if __name__ == '__main__':
    main()
