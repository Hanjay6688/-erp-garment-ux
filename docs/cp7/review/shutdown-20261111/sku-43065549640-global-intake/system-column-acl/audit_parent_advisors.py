"""Exercise exact Afui and Mandor reviewer code on isolated catalogue fixtures."""
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import argparse
import json
import re
import subprocess
from types import SimpleNamespace

import psycopg
from psycopg import sql

from replay_system_acl import catalogue, fingerprint, profile_queries, refuses
from system_column_acl import observe, require_same


AFUI_HEAD = 'fd797083eab093d9dc97f2d52ca61dc37812b437'
MANDOR_HEAD = 'a0e7d5616a0ac470876409d31c41388159f17692'
AFUI_ADVISOR = 'scripts/cp7_accessory_nonpayable/advisor_review.py'
AFUI_SETTINGS = 'scripts/cp7_accessory_nonpayable/settings.sql'
MANDOR_ADVISOR = 'scripts/current-mandor-shop-native-qualification/advisor_review.py'
PROFILE = 'scripts/cp7_global_nonpo_envelope/catalogue_profile.py'


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def frozen_file(repo, head, path):
    checkout = subprocess.check_output(['git', '--no-lazy-fetch', '-C', str(repo), 'rev-parse', 'HEAD'])
    assert checkout.decode().strip() == head
    file = repo / path
    raw = file.read_bytes()
    assert raw == subprocess.check_output(['git', '--no-lazy-fetch', '-C', str(repo), 'show', head + ':' + path])
    return file, pin(raw)


def module(path, name):
    spec = spec_from_file_location(name, path)
    value = module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def private_tables(cur, schema, names, *, force=False):
    cur.execute(sql.SQL('create schema {} authorization postgres').format(sql.Identifier(schema)))
    for name in names:
        relation = sql.Identifier(schema, name)
        cur.execute(sql.SQL('create table {} (id uuid)').format(relation))
        cur.execute(sql.SQL('alter table {} enable row level security').format(relation))
        if force:
            cur.execute(sql.SQL('alter table {} force row level security').format(relation))


def grant_column(cur, schema, table, column, grantee):
    cur.execute(sql.SQL('grant select ({}) on {} to {}').format(sql.Identifier(column),
                sql.Identifier(schema, table), sql.Identifier(grantee)))
    return cur.execute('select has_column_privilege(%s,%s,%s,%s)',
                       (grantee, schema + '.' + table, column, 'SELECT')).fetchone()[0]


def run(afui_root, mandor_root, profile, port):
    afui_path, afui_pin = frozen_file(afui_root, AFUI_HEAD, AFUI_ADVISOR)
    settings, settings_pin = frozen_file(afui_root, AFUI_HEAD, AFUI_SETTINGS)
    mandor_path, mandor_pin = frozen_file(mandor_root, MANDOR_HEAD, MANDOR_ADVISOR)
    expected_profile = dict(bytes=4607, sha256='e34234eab2e4c36f8c63742a504569f954957241c0cbc679e9b420d12218b19e')
    assert pin(profile.read_bytes()) == expected_profile
    afui, mandor = module(afui_path, 'original_afui_advisor'), module(mandor_path, 'original_mandor_advisor')
    afui.parent = lambda: SimpleNamespace(capture=lambda _: {}, require_closed=lambda proof: proof)
    mandor.parent = lambda: afui
    grant_pattern = r'^grant usage on schema cp7_accessory_nonpayable to (cp7_good_policy_date);$'
    [role] = re.findall(grant_pattern, settings.read_text(), flags=re.M)
    queries = profile_queries(profile)
    assert len(queries) == 25
    with psycopg.connect(host='127.0.0.1', port=port, user='postgres', dbname='postgres', autocommit=True) as conn:
        with conn.transaction(force_rollback=True), conn.cursor() as cur:
            version = cur.execute('show server_version').fetchone()[0]
            assert version.startswith('17.6')
            roles = sorted(set(afui.ROLES) | set(mandor.ROLES) | {role})
            for name in roles:
                cur.execute(sql.SQL('create role {} nologin nosuperuser nobypassrls').format(sql.Identifier(name)))
            private_tables(cur, afui.SCHEMA, afui.TABLES)
            cur.execute(re.search(grant_pattern, settings.read_text(), re.M).group())
            for group, schema, tables, schema_roles in mandor.PRIVATE_GROUPS:
                private_tables(cur, schema, tables, force=group == 'ReviewAdapter')
                for schema_role in schema_roles:
                    cur.execute(sql.SQL('grant usage on schema {} to {}').format(
                        sql.Identifier(schema), sql.Identifier(schema_role)))
            baseline_afui = afui.capture(cur)
            baseline_mandor = mandor.capture(cur)
            raw_before = catalogue(cur, queries)
            acl_before = observe(cur)
            assert not acl_before

            cur.execute('savepoint afui_system_grant')
            assert grant_column(cur, afui.SCHEMA, afui.TABLES[0], 'xmin', role)
            assert afui.capture(cur) == baseline_afui
            assert mandor.capture(cur) == baseline_mandor
            assert catalogue(cur, queries) == raw_before
            afui_drift = observe(cur)
            assert len(afui_drift) == 1
            refuses(lambda: require_same(cur, acl_before), 'CP7_SYSTEM_COLUMN_ACL_CHANGED')
            cur.execute('rollback to savepoint afui_system_grant')

            cur.execute('savepoint afui_user_column_grant')
            assert grant_column(cur, afui.SCHEMA, afui.TABLES[0], 'id', role)
            assert afui.capture(cur) == baseline_afui
            assert catalogue(cur, queries) != raw_before
            cur.execute('rollback to savepoint afui_user_column_grant')

            cur.execute('savepoint mandor_system_grant')
            assert grant_column(cur, mandor.SCHEMA, mandor.TABLES[0], 'xmin', mandor.SCHEMA_ROLES[0])
            refuses(lambda: mandor.capture(cur), 'MANDOR_ADVISOR_PRIVATE_LIVE_AUTHORITY_CHANGED')
            assert catalogue(cur, queries) == raw_before
            refuses(lambda: require_same(cur, acl_before), 'CP7_SYSTEM_COLUMN_ACL_CHANGED')
            cur.execute('rollback to savepoint mandor_system_grant')
            assert require_same(cur, acl_before) == acl_before
            assert catalogue(cur, queries) == raw_before
        assert conn.execute('select to_regnamespace(%s) is null', (afui.SCHEMA,)).fetchone()[0]
        assert conn.execute('select count(*) from pg_roles where rolname=any(%s)', (roles,)).fetchone()[0] == 0
    return dict(status='PARENT_SYSTEM_COLUMN_AUTHORITY_COUNTEREXAMPLE_REPRODUCED',
                postgres=version, catalogue_groups=25, baseline_catalogue_sha256=fingerprint(raw_before),
                sources={AFUI_ADVISOR: afui_pin, AFUI_SETTINGS: settings_pin, MANDOR_ADVISOR: mandor_pin,
                         PROFILE: expected_profile},
                exact_Afui_schema_usage_reused=True, Afui_extra_xmin_row=afui_drift[0],
                Afui_original_advisor_missed_xmin=True, Afui_original_advisor_missed_ordinary_column=True,
                original_full25_detected_ordinary_column=True, original_full25_missed_xmin=True,
                Mandor_own_private_advisor_rejected_xmin=True, supplemental_observer_rejected_both_xmin_changes=True,
                fixture_rollback=True, production_go=False, actual_combined_ERP_cases=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for path in ('afui-checkout', 'mandor-checkout', 'catalogue-profile'):
        parser.add_argument('--' + path, type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    args = parser.parse_args()
    result = run(args.afui_checkout.resolve(), args.mandor_checkout.resolve(),
                 args.catalogue_profile.resolve(), args.port)
    print(json.dumps(result, indent=2))
