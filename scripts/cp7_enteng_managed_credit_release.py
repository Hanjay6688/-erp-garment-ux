"""Bind the staged credit and note migrations to the reviewed application catalogue."""

import json

from cp7_enteng_managed_ow04_migration import digest, literal_json, require
from cp7_ow04_restore_bundle import QUERIES


CONSUMER = 'enteng_uji_cp7_managed_credit_consumer'
CORRECTIONS = 'enteng_uji_cp7_managed_credit_corrections'
ATTENDANCE = 'enteng_uji_cp7_managed_attendance'
OW04 = 'enteng_uji_cp7_managed_ow04'
OW04_SHA256 = '351d48d3ef4adf58812bd0cebd31ff2267cf8d478a90cd782d410f898ae9bc0f'
IMMUTABLE_CENSUS = 'cp7_credit.assert_source_native_trigger_census_v1()'
CATALOGUE_GROUPS = tuple(sorted(set(QUERIES) - {'database_authority','extensions','aggregates'}))


def pinned_groups(source):
    # Roles/objects outside the workspace's ERP and OW04 namespaces belong
    # to the platform. Compare all rows inside the named application scope.
    return f"""with originals as ({source}), projected as (
       select category,item,case when category='functions' and item='{IMMUTABLE_CENSUS}' then
          jsonb_set(attrs,'{{0}}',to_jsonb(regexp_replace(attrs->>0,
            '(if actual_sha256 is distinct from '')[0-9a-f]{{64}}(''then)', '\\1<runtime-census>\\2')))
          else attrs end as attrs
       from originals
       where item ~ '^(erp[.]+|cp7_|ow04_|public[.]erp_)'
          or category='schemas' and item in ('erp','public')
          or category='default_privileges' and item ~ ':(erp|public|cp7_[^:]+|ow04_[^:]+):'
    ), groups as (
       select category,count(*) as entries,encode(sha256(convert_to(jsonb_agg(jsonb_build_array(item,attrs)
           order by item collate "C",attrs::text collate "C")::text,'UTF8')),'hex') as sha256
       from projected group by category
    ) select jsonb_object_agg(category,jsonb_build_array(entries,sha256)) as credit_catalogue from groups"""


def live_profile_sql():
    statements = [f"select '{key}'::text as category, item, attrs from ({QUERIES[key]}) x(item,attrs)"
                  for key in CATALOGUE_GROUPS]
    return pinned_groups('\nunion all\n'.join(statements))


def reference_profile(cur, catalogue):
    filtered = {k:catalogue[k] for k in CATALOGUE_GROUPS}
    query = pinned_groups('select c.category,r.item,r.attrs from jsonb_each(%s::jsonb) c(category,items) '
                          'cross join lateral jsonb_each(c.items) r(item,attrs)')
    return cur.execute(query, (json.dumps(filtered),)).fetchone()[0]


def render(prerequisite, prerequisite_sha, count, before, after, statements):
    require((prerequisite,count) in ((OW04,147),(CONSUMER,148),(CORRECTIONS,149)),
            'Unexpected managed Enteng Uji release sequence')
    require(len(prerequisite_sha)==64 and len(before)>10 and set(before)<=set(CATALOGUE_GROUPS)
            and len(after)>10 and set(after)<=set(CATALOGUE_GROUPS), 'Incomplete credit application catalogue')
    profile = live_profile_sql()
    # Pin the original snapshot once more after taking the release lock.
    begin = f"""do $enteng_credit_before$
declare prior_path text:=current_setting('search_path');prior_zone text:=current_setting('TimeZone');profile jsonb;
begin
  if current_user<>'postgres' or session_user<>'postgres' or current_setting('is_superuser')<>'off'
     or (select version from erp.schema_migrations order by installed_at desc,version desc limit 1)
           is distinct from 'v2.6.20bf'
     or (select count(*) from supabase_migrations.schema_migrations)<>{count}
     or exists(select from auth.users) or exists(select from auth.sessions)
     or (select encode(sha256(convert_to(statements[1],'UTF8')),'hex')
         from supabase_migrations.schema_migrations where name='{prerequisite}' and cardinality(statements)=1)
         is distinct from '{prerequisite_sha}' then
    raise exception 'CP7 credit requires the exact tested Enteng Uji predecessor';
  end if;
  perform cp7_global_release_guard.enter_release();
  perform cp7_credit.assert_source_native_trigger_census_v1();
  perform set_config('search_path','',true);
  perform set_config('TimeZone','UTC',true);
  select credit_catalogue into strict profile from ({profile}) digest;
  if profile is distinct from {literal_json(before)} then
    raise exception 'CP7 credit predecessor application catalogue differs';
  end if;
  perform set_config('TimeZone',prior_zone,true);
  perform set_config('search_path',prior_path,true);
end $enteng_credit_before$;
"""
    end = f"""do $enteng_credit_after$
declare prior_path text:=current_setting('search_path');prior_zone text:=current_setting('TimeZone');profile jsonb;
begin
  perform cp7_credit.assert_source_native_trigger_census_v1();
  perform cp7_global_release_guard.assert_ddl_fence();
  perform set_config('search_path','',true);
  perform set_config('TimeZone','UTC',true);
  select credit_catalogue into strict profile from ({profile}) digest;
  if profile is distinct from {literal_json(after)}
     or exists(select from pg_roles r where left(rolname,4)='cp7_' and
          (pg_has_role('postgres',r.oid,'SET') or pg_has_role('postgres',r.oid,'USAGE'))) then
    raise exception 'CP7 credit functions, ownership or authorization changed';
  end if;
  perform set_config('TimeZone',prior_zone,true);
  perform set_config('search_path',prior_path,true);
end $enteng_credit_after$;
"""
    payload = begin + statements + '\n' + end
    require(len(payload.encode()) < 900_000, 'CP7 credit release SQL exceeds the reviewed transport limit')
    return payload, digest(payload)
