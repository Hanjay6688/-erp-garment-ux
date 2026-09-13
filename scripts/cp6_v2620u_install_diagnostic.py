#!/usr/bin/env python3
"""Reproduce frozen U #150 without changing its rejection or admitting U."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

from cp6_v2620n_rollback_guards import function_catalog

FROZEN_HEAD = 'ce6df43ee4115b83dd921eb06a726356c278bb09'
SOURCE = 'supabase/migrations/20260913070000_erp_v2_6_20u_cp6_canonical_business_date.sql'
FROZEN_SHA256 = '83878cf18de9fad9bbaf4a306ad1a6d2527dbd6f45ecd85cd388f53a476bba85'
ERROR = 'U_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: erp.get_owner_financial_snapshot_v2(date,date,date)'
REPORT = Path('cp6-proof/CP6_V2620U_FAILED150_PREDICATES.json')


def sha(value):
    return hashlib.sha256(value).hexdigest()


def snapshot(cur):
    functions = function_catalog(cur)
    cur.execute("""select n.nspname,c.relname,c.relrowsecurity,
      pg_get_userbyid(c.relowner),c.relacl::text
      from pg_class c join pg_namespace n on n.oid=c.relnamespace
      where c.relkind='r' and n.nspname in('erp','supabase_migrations')
      order by 1,2""")
    tables = []
    for schema, name, rls, owner, acl in cur.fetchall():
        cur.execute(sql.SQL("""select count(*),encode(extensions.digest(
          convert_to(coalesce(string_agg(to_jsonb(t)::text,E'\\n'
            order by to_jsonb(t)::text),''),'UTF8'),'sha256'),'hex')
          from {} t""").format(sql.Identifier(schema, name)))
        count, digest = cur.fetchone()
        tables.append([schema, name, rls, owner, acl, count, digest])
    return {
        'function_count': len(functions),
        'function_catalog_sha256': sha(json.dumps(functions).encode()),
        'tables': tables,
    }


def instrument_notices(source):
    """Only add an observation before the original installed gate loop."""
    tag = 'do $installed_v2620u$\n'
    before, block = source.split(tag, 1)
    body, after = block.split('$installed_v2620u$;', 1)
    match = re.search(
        r'for r in select \* from\(values\n(.*?)\n  \) expected\(identity,predecessor_sha256,installed_sha256,acl\)',
        body, re.S,
    )
    if match is None:
        raise AssertionError('U_DIAGNOSTIC_FROZEN_GATE_NOT_FOUND')
    notice = """
  select jsonb_agg(jsonb_build_object(
    'identity',e.identity,'expected_predecessor_sha256',e.predecessor_sha256,
    'expected_installed_sha256',e.installed_sha256,'expected_owner','postgres',
    'expected_acl',e.acl,'capsule_identity',observed_cap.object_regidentity,
    'capsule_definition_sha256',observed_cap.definition_sha256,
    'capsule_definition_actual_sha256',encode(extensions.digest(
      convert_to(observed_cap.object_definition,'UTF8'),'sha256'),'hex'),
    'capsule_installed_sha256',observed_cap.installed_definition_sha256,
    'owner_before',observed_cap.owner_snapshot,'acl_before',observed_cap.acl_snapshot,
    'owner_after',pg_get_userbyid(p.proowner),
    'acl_after',array(select a::text from unnest(p.proacl) a order by a::text),
    'actual_live_sha256',encode(extensions.digest(
      convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
    'predecessor_definition',observed_cap.object_definition,
    'normalized_installed_definition',pg_get_functiondef(p.oid)
  ) order by e.identity) into diagnostic
  from(values
""" + match.group(1) + """
  ) e(identity,predecessor_sha256,installed_sha256,acl)
  left join erp.cp6_v2620u_rollback_capsule observed_cap on observed_cap.object_regidentity=e.identity
  left join pg_proc p on p.oid=to_regprocedure(e.identity);
  raise notice 'U_DIAGNOSTIC:%',diagnostic::text;
"""
    declaration = 'declare r record;c record;'
    anchor = '\n  for r in select * from(values\n'
    if body.count(declaration) != 1 or body.count(anchor) != 1:
        raise AssertionError('U_DIAGNOSTIC_INSTRUMENTATION_ANCHOR')
    changed = body.replace(declaration, declaration + 'diagnostic jsonb;')
    changed = changed.replace(anchor, notice + anchor)
    # Strip the added observation and declaration to prove every original byte remains.
    if changed.replace(notice, '').replace(
        declaration + 'diagnostic jsonb;', declaration
    ) != body:
        raise AssertionError('U_DIAGNOSTIC_CHANGED_ORIGINAL_ASSERTION')
    return before + tag + changed + '$installed_v2620u$;' + after


def run():
    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    expected = dict(user='postgres', password='postgres', host='127.0.0.1',
                    port='54322', dbname='postgres')
    if params != expected or os.environ.get('CP6_U_DISPOSABLE_CONFIRM') != 'postgres':
        raise AssertionError('U_DIAGNOSTIC_DISPOSABLE_ENDPOINT_REQUIRED')
    raw = subprocess.check_output(['git', 'show', FROZEN_HEAD + ':' + SOURCE])
    if len(raw) != 20907 or sha(raw) != FROZEN_SHA256:
        raise AssertionError('U_DIAGNOSTIC_FROZEN_BYTES_MISMATCH')
    source = raw.decode()
    notices = []
    observations = []
    with psycopg.connect(**params, autocommit=False) as conn, conn.cursor() as cur:
        def receive(diag):
            prefix = 'U_DIAGNOSTIC:'
            if diag.message_primary.startswith(prefix):
                notices.extend(json.loads(diag.message_primary[len(prefix):]))
        conn.add_notice_handler(receive)
        cur.execute("select version(),current_setting('search_path'),current_setting('TimeZone')")
        engine, search_path, timezone = cur.fetchone()
        baseline = snapshot(cur)
        conn.rollback()
        for name, text in [('FROZEN_EXACT', source),
                           ('NOTICE_ONLY_INSTRUMENTED', instrument_notices(source))]:
            error = None
            try:
                cur.execute(text, prepare=False)
            except psycopg.Error as exc:
                error = {'sqlstate': exc.sqlstate, 'message': exc.diag.message_primary}
            finally:
                conn.rollback()
            restored = snapshot(cur)
            conn.rollback()
            REPORT.parent.mkdir(parents=True, exist_ok=True)
            REPORT.write_text(json.dumps(dict(
                status='DIAGNOSTIC_IN_PROGRESS', failed_source_head=FROZEN_HEAD,
                observations=observations, current_case=name, current_error=error,
                current_rollback_exact=restored == baseline, production_go=False
            ), indent=2) + '\n')
            if error is None or error['message'] != ERROR:
                raise AssertionError('U_DIAGNOSTIC_ORIGINAL_REJECTION_NOT_REPRODUCED:' + str(error))
            if restored != baseline:
                raise AssertionError('U_DIAGNOSTIC_FAILED_INSTALL_LEFT_RESIDUE')
            observations.append({'case': name, 'error': error,
                                 'full_functions_owner_acl_tables_restored': True})
    if len(notices) != 5:
        raise AssertionError('U_DIAGNOSTIC_ALL_FIVE_FUNCTIONS_REQUIRED')
    for row in notices:
        row['predicates'] = {
            'capsule_present': row['capsule_identity'] == row['identity'],
            'predecessor_pin': row['capsule_definition_sha256'] == row['expected_predecessor_sha256'],
            'predecessor_bytes': row['capsule_definition_actual_sha256'] == row['expected_predecessor_sha256'],
            'installed_capsule_pin': row['capsule_installed_sha256'] == row['expected_installed_sha256'],
            'installed_live_pin': row['actual_live_sha256'] == row['expected_installed_sha256'],
            'owner_before': row['owner_before'] == row['expected_owner'],
            'owner_after': row['owner_after'] == row['expected_owner'],
            'acl_before': row['acl_before'] == row['expected_acl'],
            'acl_after': row['acl_after'] == row['expected_acl'],
        }
    result = dict(status='PASS_REPRODUCED_FROZEN_U_FAILURE',
                  head=os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'),
                  failed_source_head=FROZEN_HEAD, failed_source_sha256=FROZEN_SHA256,
                  engine=engine, search_path=search_path, timezone=timezone,
                  original_assertions_unchanged=True, observations=observations,
                  baseline=baseline, functions=notices, production_go=False)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'functions': len(notices),
                      'all_effects_rolled_back': True, 'production_go': False}))
    return result


if __name__ == '__main__':
    run()
