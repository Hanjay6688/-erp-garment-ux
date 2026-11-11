"""Reproduce the catalogue blind spot with the exact ERP grant source in local PG17."""
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import argparse
import json
import re

import psycopg
from psycopg import errors, sql

from system_column_acl import SNAPSHOT_RELATIONS, observe, require_same, require_snapshot_xmin

PROFILE = 'scripts/cp7_global_nonpo_envelope/catalogue_profile.py'
RESTORE = 'scripts/cp7_ow04_restore_bundle.py'
SNAPSHOT = 'scripts/cp7-src/planning/analysis-stage-snapshot.sql'
SOURCE_PINS = {
    PROFILE: dict(bytes=4607, sha256='e34234eab2e4c36f8c63742a504569f954957241c0cbc679e9b420d12218b19e'),
    RESTORE: dict(bytes=19828, sha256='a1605193347cf5b3321a7bdbf8ff6c634df4f4c0a5113eb295e8c3ce44428e00'),
    SNAPSHOT: dict(bytes=16768, sha256='083925b7d5a7dd2d62c24e0a218690a3eae054a7a59333e1974d93016958cbfb'),
}


def pin(path):
    data = path.read_bytes()
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def profile_queries(profile):
    spec = spec_from_file_location('exact_catalogue_profile', profile)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.queries()


def catalogue(cur, queries):
    result = {}
    for name, query in sorted(queries.items()):
        rows = cur.execute('select k,v from (' + query + ') q(k,v) order by k collate "C", v::text collate "C"').fetchall()
        result[name] = rows
    return result


def access(conn, relation, ordinary_column):
    try:
        with conn.transaction(), conn.cursor() as cur:
            cur.execute('set local role cp7_capture')
            values = cur.execute(sql.SQL('select {}::text, xmin::text from erp.{}')
                                 .format(sql.Identifier(ordinary_column), sql.Identifier(relation))).fetchall()
            cur.execute('reset role')
            assert len(values) == 1 and values[0][1].isdigit()
    except errors.InsufficientPrivilege as exc:
        return {'select': 'DENIED', 'sqlstate': exc.sqlstate}
    return {'select': 'PASS', 'sqlstate': None}


def effective(cur, relation):
    return cur.execute("select has_column_privilege('cp7_capture', %s, 'xmin', 'SELECT')",
                       ('erp.' + relation,)).fetchone()[0]


def fingerprint(data):
    return sha256(json.dumps(data, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def baseline(cur):
    return cur.execute("select to_regnamespace('erp') is null, "
                       "not exists(select 1 from pg_roles where rolname='cp7_capture')").fetchone()


def refuses(call, expected):
    try:
        call()
    except ValueError as exc:
        assert str(exc).startswith(expected)
        return
    raise AssertionError('Expected refusal: ' + expected)


def main(port, source_root):
    actual_pins = {name: pin(source_root / name) for name in SOURCE_PINS}
    if actual_pins != SOURCE_PINS:
        raise ValueError('CP7_SYSTEM_ACL_REPLAY_SOURCE_CHANGED')
    pattern = re.compile(r'^grant select\(([a-z_,]+),xmin\)on erp\.([a-z0-9_]+) to cp7_capture;$', re.M)
    grants = pattern.findall((source_root / SNAPSHOT).read_text())
    assert len(grants) == 4 and {relation for _, relation in grants} == set(SNAPSHOT_RELATIONS)
    queries = profile_queries(source_root / PROFILE)
    assert len(queries) == 25
    with psycopg.connect(host='127.0.0.1', port=port, user='postgres', dbname='postgres', autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("set search_path to ''; set timezone to 'UTC'")
            assert baseline(cur) == (True, True)
            version = cur.execute('show server_version').fetchone()[0]
        with conn.transaction(force_rollback=True), conn.cursor() as cur:
            cur.execute('create schema erp; create role cp7_capture nologin; grant usage on schema erp to cp7_capture')
            for columns, relation in grants:
                column_names = [sql.Identifier(name) for name in columns.split(',')]
                definitions = sql.SQL(', ').join(sql.SQL('{} text').format(name) for name in column_names)
                cur.execute(sql.SQL('create table erp.{} ({})').format(sql.Identifier(relation), definitions))
                cur.execute(sql.SQL('insert into erp.{} default values').format(sql.Identifier(relation)))
                cur.execute(sql.SQL('grant select ({}) on erp.{} to cp7_capture')
                            .format(sql.SQL(', ').join(column_names), sql.Identifier(relation)))
            baseline_catalogue = catalogue(cur, queries)
            baseline_acl = observe(cur)
            assert not baseline_acl
            refuses(lambda: require_snapshot_xmin(cur, baseline_acl), 'CP7_SNAPSHOT_XMIN_EXPLICIT_GRANT_MISSING')
            denied = {relation: access(conn, relation, columns.split(',')[0]) for columns, relation in grants}
            assert all(value == {'select': 'DENIED', 'sqlstate': '42501'} for value in denied.values())
            assert all(effective(cur, relation) is False for _, relation in grants)
            for columns, relation in grants:
                cur.execute(f'grant select({columns},xmin)on erp.{relation} to cp7_capture;')
            granted_catalogue = catalogue(cur, queries)
            granted_acl = observe(cur)
            assert granted_catalogue == baseline_catalogue
            refuses(lambda: require_same(cur, baseline_acl), 'CP7_SYSTEM_COLUMN_ACL_CHANGED')
            assert {(row['relation'], row['column'], row['attribute_number'], row['grantee'], row['privilege'])
                    for row in granted_acl} == {(relation, 'xmin', -2, 'cp7_capture', 'SELECT') for _, relation in grants}
            allowed = {relation: access(conn, relation, columns.split(',')[0]) for columns, relation in grants}
            assert all(value == {'select': 'PASS', 'sqlstate': None} for value in allowed.values())
            assert all(effective(cur, relation) is True for _, relation in grants)
            assert all(flag is True for _, flag in require_snapshot_xmin(cur, granted_acl))
            assert require_same(cur, granted_acl) == granted_acl
            for _, relation in grants:
                cur.execute(sql.SQL('revoke select (xmin) on erp.{} from cp7_capture').format(sql.Identifier(relation)))
            assert catalogue(cur, queries) == baseline_catalogue and observe(cur) == baseline_acl
            refuses(lambda: require_same(cur, granted_acl), 'CP7_SYSTEM_COLUMN_ACL_CHANGED')
            refuses(lambda: require_snapshot_xmin(cur, observe(cur)), 'CP7_SNAPSHOT_XMIN_EXPLICIT_GRANT_MISSING')
            assert all(access(conn, relation, columns.split(',')[0]) == denied[relation] for columns, relation in grants)
        with conn.cursor() as cur:
            assert baseline(cur) == (True, True)
    print(json.dumps({'status': 'SYSTEM_COLUMN_ACL_OMISSION_REPRODUCED', 'postgres': version,
        'exact_input_sources': actual_pins,
        'groups': len(queries), 'all25_digest_without_system_grants': fingerprint(baseline_catalogue),
        'all25_digest_with_system_grants': fingerprint(granted_catalogue), 'exact_all25_equal': True,
        'supplemental_acl_before': baseline_acl, 'supplemental_acl_with_grants': granted_acl,
        'read_before': denied, 'read_after_grant': allowed, 'read_after_revoke': denied,
        'observer_refuses_missing_grants_and_drift': True,
        'fixture_role_and_schema_restored': True, 'actual_combined_ERP_cases': 0,
        'active_candidate_changed': False, 'production_go': False}, indent=2))


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--port', required=True, type=int)
    cli.add_argument('--source-root', required=True, type=Path)
    args = cli.parse_args()
    main(args.port, args.source_root.resolve())
