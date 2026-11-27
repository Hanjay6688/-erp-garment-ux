"""Render the qualified OW04 transaction for a managed Enteng Uji restore."""

from hashlib import sha256
import json
import re

from pglast import split

import cp7_enteng_managed_change_fence as fence
import cp7_full_owning_install as full


MIGRATION_NAME = 'enteng_uji_cp7_managed_ow04'
SQL_MAX_BYTES = 998_000
PHASES = ('OW04_COMPOSED', 'OW04_COMPOSED_NATIVE_EMPTY')
CREDIT_SOURCE = full.credit.ROOT / 'integration'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return sha256(value.encode()).hexdigest()


def literal_json(value):
    data = json.dumps(value, sort_keys=True, separators=(',', ':'))
    tag = '$ow04_expected$'
    require(tag not in data, 'Unexpected OW04 expectation delimiter')
    return tag + data + tag + '::jsonb'


def compact_native_guard(source, rows, facts, absent=()):
    # Keep every literal metadata and ACL comparison. Only the two exact text
    # comparisons use hashes so the reviewed definition and body needn't be
    # included a second time in this migration.
    original = split(source._guard_sql(rows, facts, absent))[0]
    compact = []
    for original_row in rows:
        row = dict(original_row)
        row['definition'] = digest(row['definition'])
        row['body'] = digest(row['body'])
        compact.append(row)
    prefix, sep, sql = original.partition('::jsonb;r jsonb;')
    start_tag = 'declare expected jsonb:='
    require(bool(sep) and prefix.count(start_tag) == 1, 'Unexpected Native guard declaration')
    start = prefix.partition(start_tag)[0] + start_tag
    for actual in ('pg_get_functiondef(p.oid)', 'p.prosrc'):
        check = f"encode(sha256(convert_to({actual},'UTF8')),'hex') is distinct from r"
        sql, changed = re.subn(re.escape(actual) + r'\s*is distinct from r', check, sql)
        require(changed == 1, 'Unexpected Native text guard ' + actual)
    payload = literal_json({'functions': compact, 'helper_sources': facts, 'absent_targets': list(absent)})
    return original, start + payload + ';r jsonb;' + sql


PORTABLE_PROJECTION = r"""select jsonb_build_object(
  'relations',(select jsonb_agg(r - 'oid' order by r->>'relation' collate "C") from jsonb_array_elements(c->'relations') r),
  'foreign_keys',(select jsonb_agg(r - 'oid' order by (r - 'oid')::text collate "C") from jsonb_array_elements(c->'foreign_keys') r),
  'functions',(select jsonb_agg((r - array['function_oid','owner_oid','language_oid','proc_raw']) ||
      jsonb_build_object('proc_raw',(r->'proc_raw') - array['oid','pronamespace','proowner','prolang'])
       order by r->>'identity' collate "C") from jsonb_array_elements(c->'functions') r),
  'triggers',(select jsonb_agg(portable order by portable::text collate "C") from (
      select case when (r->>'internal')::boolean then
        (r - array['trigger_oid','function_oid','name','constraint','definition','definition_sha256']) ||
        jsonb_build_object('constraint',(r->'constraint') - 'oid',
          'name',regexp_replace(r->>'name','^(RI_ConstraintTrigger_[ac]_)[0-9]+$','\1<oid>'),
          'definition',regexp_replace(r->>'definition','^(CREATE CONSTRAINT TRIGGER "RI_ConstraintTrigger_[ac]_)[0-9]+(" )','\1<oid>\2'))
        else r - array['trigger_oid','function_oid'] end as portable
        from jsonb_array_elements(c->'triggers') r) normalized)
 ) as catalogue from capture"""


def catalogue_digest_query(capture_query, projection=PORTABLE_PROJECTION):
    return "with capture(c) as (" + capture_query.strip().removesuffix(';') + "), portable as (" + projection + """
 ) select encode(sha256(convert_to(c::text,'UTF8')),'hex') as raw_sha256,
          encode(sha256(convert_to(catalogue::text,'UTF8')),'hex') as portable_sha256
      from capture,portable"""


def digest_snapshot(cur, snapshot, projection=PORTABLE_PROJECTION):
    return cur.execute(catalogue_digest_query('select %s::jsonb', projection), (json.dumps(snapshot),)).fetchone()


def seal_with_local_oid(statement, raw_sha, portable_sha, capture_sql, projection=PORTABLE_PROJECTION):
    require(bool(re.fullmatch(r'[0-9a-f]{64}', raw_sha)) and bool(re.fullmatch(r'[0-9a-f]{64}', portable_sha)),
            'Invalid staged catalogue fingerprint')
    require(statement.count(raw_sha) == 1 and statement.endswith('end $ow04_source_trigger_runtime$'),
            'Unexpected original runtime guard statement')
    tag = '$ow04_runtime_template$'
    require(tag not in statement, 'Unexpected OW04 template delimiter')
    return f"""do $enteng_hosted_seal$
declare raw_now text;portable_now text; saved_path text:=current_setting('search_path');
begin
  perform set_config('search_path','',true);
  select raw_sha256,portable_sha256 into strict raw_now,portable_now
    from ({catalogue_digest_query(capture_sql, projection)}) parsed;
  if portable_now is distinct from '{portable_sha}' then
    raise exception 'OW04 source-validated trigger metadata differs from the tested stage';
  end if;
  execute replace({tag}{statement}{tag},'{raw_sha}',raw_now);
  perform set_config('search_path',saved_path,true);
end $enteng_hosted_seal$"""


def admission(readback, before_portable, capture_sql):
    receipts = literal_json([{k:row[k] for k in ('name','sql_sha256')} for row in readback])
    return f"""do $enteng_ow04_admission$
declare expected_receipt jsonb; portable_now text; saved_path text:=current_setting('search_path');
begin
  if current_user<>'postgres' or session_user<>'postgres' or current_setting('is_superuser')<>'off'
     or (select version from erp.schema_migrations order by installed_at desc,version desc limit 1)
           is distinct from 'v2.6.20bf'
     or (select count(*) from supabase_migrations.schema_migrations)<>146
     or (select count(*) from pg_roles where left(rolname,4)='cp7_')<>55
     or exists(select from auth.users) or exists(select from auth.sessions)
     or to_regnamespace('cp7_credit') is not null then
    raise exception 'OW04 requires the exact unconnected managed CP7 predecessor';
  end if;
  perform {fence.SCHEMA}.enter_release();
  for expected_receipt in select value from jsonb_array_elements({receipts}) loop
    if (select encode(sha256(convert_to(statements[1],'UTF8')),'hex')
          from supabase_migrations.schema_migrations where name=expected_receipt->>'name' and cardinality(statements)=1)
          is distinct from expected_receipt->>'sql_sha256' then
      raise exception 'OW04 predecessor migration differs: %',expected_receipt->>'name';
    end if;
  end loop;
  perform set_config('search_path','',true);
  select portable_sha256 into strict portable_now from ({catalogue_digest_query(capture_sql)}) parsed;
  if portable_now is distinct from '{before_portable}' then
    raise exception 'OW04 installed predecessor metadata differs from the tested stage';
  end if;
  perform set_config('search_path',saved_path,true);
end $enteng_ow04_admission$;
"""


END_CHECK = f"""do $enteng_ow04_after$
begin
  if (select count(*) from pg_roles where left(rolname,4)='cp7_')<>57
     or exists(select from pg_roles r where left(rolname,4)='cp7_' and
          (pg_has_role('postgres',r.oid,'SET') or pg_has_role('postgres',r.oid,'USAGE')))
     or exists(select from unnest(array['anon','authenticated','service_role','cp7_capture']) actor
          cross join unnest(array['cp7_credit','ow04_ordinal_wrapper','ow04_source_proposal','ow04_pure_kernel']) n
          where has_schema_privilege(actor,n,'USAGE')) then
    raise exception 'OW04 verification found unexpected installation or API access';
  end if;
  perform {fence.SCHEMA}.assert_ddl_fence();
  perform cp7_credit.assert_source_native_trigger_census_v1();
end $enteng_ow04_after$;
"""


def render(cur, ddl, state, phases, receipts):
    source = full.credit.load('enteng_managed_ow04_native_plan', CREDIT_SOURCE / 'derive_plan.py')
    guard = full.credit.load('enteng_managed_ow04_trigger_guard', CREDIT_SOURCE / 'source_triggers/trigger_guard.py')
    plan = source._checked_plan(state['plan'], state['approval'])
    entries = plan['entries']
    old_rows = [e['old'] for e in entries]
    new_rows = [e['new'] for e in entries] + [next(e['old'] for e in entries if e['source_identity'] == source.POSTER)]
    replacements = dict([compact_native_guard(source, old_rows, plan['immutable_helper_sources'], [source.BOUND]),
                         compact_native_guard(source, new_rows, plan['immutable_helper_sources'])])
    manifest = full.credit._trigger_manifest(guard, True)
    before = state['source_triggers']['before']
    guard.validate_source(before, manifest, 'VERIFIED_PREDECESSOR')
    _, before_portable = digest_snapshot(cur, before)
    for phase in PHASES:
        snapshot = phases[phase]
        raw_sha, portable_sha = digest_snapshot(cur, snapshot)
        guard_statements = split(guard.render_runtime_guard(snapshot, manifest, phase, raw_sha))
        statement = guard_statements[0]
        replacements[statement] = seal_with_local_oid(statement, raw_sha, portable_sha, guard.CAPTURE_SQL)
    require(len(replacements) == 4, 'Expected two exact text guards and two trigger census stages')
    statements = split(ddl)
    require(all(statements.count(s) == 1 for s in replacements), 'Recorded OW04 DDL lacks a reviewed guard')
    body = admission(receipts, before_portable, guard.CAPTURE_SQL) + '\n'.join(
        replacements.get(statement, statement) + ';' for statement in statements) + '\n' + END_CHECK
    require(len(body.encode()) <= SQL_MAX_BYTES, f'Managed OW04 migration is too large: {len(body.encode())}')
    return body, before_portable, catalogue_digest_query(guard.CAPTURE_SQL)
