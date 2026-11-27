"""Render the reviewed CP7 predecessor as bounded Enteng Uji migrations."""

import argparse
from hashlib import sha256
from pathlib import Path
import re

import cp7_enteng_managed_foundation_stage as foundation
import cp7_enteng_managed_predecessor_rehearsal as prelude


# Complete source sections. Finance is divided before the transaction-source
# package, which begins at statement 1347 in the reviewed predecessor.
PARTS = (
    ('procurement', 467),
    ('operations_finance', 1346),
    ('transaction_sources', 2128),
    ('planning', 2635),
    ('analysis', 3228),
    ('reminders', 3838),
)
ROLE_DECLARATION = re.compile(r'create role (cp7_[a-z0-9_]+) nologin', re.I)
MAX_BYTES = 800_000
REPAIRS = Path(__file__).with_name('cp7_enteng_managed_predecessor_repairs.sql')
REPAIR_SHA256 = 'e5ce111238890ca30632f6203e7ff3eaf8dbf4f3aa0967729bbecd714cc4eee0'


def sql_hash(body):
    return sha256(body.encode()).hexdigest()


def roles_sql(roles):
    return 'array[' + foundation.sql_list(roles) + ']'


def closed_roles(roles):
    names = roles_sql(roles)
    return f"""(select array_agg(rolname::text order by rolname) from pg_roles where left(rolname,4)='cp7_')
            is not distinct from {names}
      and not exists(select from pg_roles where rolname=any({names}) and
           (rolcanlogin or rolsuper or rolinherit or rolcreatedb or rolcreaterole or rolreplication
             or rolconnlimit<>-1 or rolconfig is not null))
      and (select count(*) from pg_auth_members m join pg_roles r on r.oid=m.roleid
            where r.rolname=any({names}) and m.member='postgres'::regrole
              and m.grantor<>'postgres'::regrole and m.admin_option and not m.inherit_option and not m.set_option)={len(roles)}
      and (select count(*) from pg_auth_members m join pg_roles r on r.oid=m.roleid
            where r.rolname=any({names}))={len(roles)}
      and not exists(select from pg_auth_members m join pg_roles r on r.oid=m.member where r.rolname=any({names}))
      and not exists(select from unnest({names}) r
          cross join unnest(array['postgres','anon','authenticated','service_role']) caller
          where pg_has_role(caller,r,'USAGE') or pg_has_role(caller,r,'SET'))"""


def role_membership(roles, *, open_for_install=False):
    names = ','.join(roles)
    if open_for_install:
        return f'grant {names} to postgres with inherit true, set true granted by postgres;\n'
    return f'revoke {names} from postgres granted by postgres restrict;\n'


def begin_part(history, prior_roles):
    receipt_checks = '\n'.join(f"""  if (select encode(sha256(convert_to(statements[1],'UTF8')),'hex')
      from supabase_migrations.schema_migrations where name='{name}' and cardinality(statements)=1)
      is distinct from '{digest}' then raise exception 'Predecessor receipt differs for {name}'; end if;"""
      for name, digest in history)
    return f"""do $predecessor_before$
begin
  if session_user<>'postgres' or current_user<>'postgres' or current_setting('is_superuser')<>'off'
     or (select version from erp.schema_migrations order by installed_at desc,version desc limit 1)
          is distinct from 'v2.6.20bf'
     or (select count(*) from supabase_migrations.schema_migrations)<>{139+len(history)}
     or exists (select from auth.users) or exists (select from auth.sessions) then
    raise exception 'Expected guarded, unconnected Enteng Uji for the managed CP7 predecessor';
  end if;
  perform {prelude.fence.SCHEMA}.enter_release();
{receipt_checks}
  if not ({closed_roles(prior_roles)}) then
    raise exception 'Existing CP7 installation roles differ before the predecessor migration';
  end if;
end $predecessor_before$;
set local createrole_self_grant='set,inherit';
""" + role_membership(prior_roles, open_for_install=True)


def scoped_statement(statement, schema, role):
    return f"""do $predecessor_owner$
declare schema_acl text;
begin
  select nspacl::text into strict schema_acl from pg_namespace where nspname='{schema}';
  if has_schema_privilege('{role}','{schema}','CREATE')
     or not has_schema_privilege(current_user,'{schema}','CREATE WITH GRANT OPTION')
     or not pg_has_role(current_user,(select nspowner from pg_namespace where nspname='{schema}'),'USAGE') then
    raise exception 'Unexpected CREATE scope for {role} on {schema}';
  end if;
  grant create on schema {schema} to {role};
  {statement};
  revoke create on schema {schema} from {role};
  if (select nspacl::text from pg_namespace where nspname='{schema}') is distinct from schema_acl then
    raise exception 'CREATE scope changed privileges on {schema}';
  end if;
end $predecessor_owner$;"""


def finish_part(roles):
    return role_membership(roles) + f"""do $predecessor_after$
begin
  if not ({closed_roles(roles)}) then
    raise exception 'Unexpected ownership or caller privileges after the predecessor migration';
  end if;
  perform {prelude.fence.SCHEMA}.assert_ddl_fence();
end $predecessor_after$;
"""


def section_sources():
    statements = prelude.statements()
    scopes = {index: key for key, positions in prelude.SCOPES.items() for index in positions}
    if len(scopes) != 81 or PARTS[-1][1] != len(statements):
        raise ValueError('Reviewed predecessor scope or boundaries changed')
    prior = tuple(sorted(foundation.ROLES))
    start = 0
    for name, end in PARTS:
        section = statements[start:end]
        new_roles = tuple(sorted(match[1] for statement in section if (match := ROLE_DECLARATION.match(statement))))
        all_roles = tuple(sorted((*prior, *new_roles)))
        sql = []
        for index, statement in enumerate(section, start + 1):
            scope = scopes.get(index)
            sql.append(scoped_statement(statement, *scope) if scope else statement + ';')
        yield name, prior, all_roles, '\n'.join(sql) + '\n'
        prior = all_roles
        start = end
    if len(prior) != 55 or sql_hash('\n'.join(prior)) != prelude.ROLE_SET_SHA256:
        raise ValueError('Managed predecessor role names changed')


def migrations(repair_sql):
    """Yield named SQL. The final repair is from the reviewed local prelude."""
    if sql_hash(repair_sql) != REPAIR_SHA256:
        raise ValueError('The rendered identity and verifier repairs differ from the reviewed prelude')
    history = [(foundation.MIGRATION_NAME, sql_hash(foundation.migration()))]
    for part, prior, roles, source in section_sources():
        suffix = ''
        if part == PARTS[-1][0]:
            suffix = repair_sql + '\n' + foundation.facade_grant(True)
        name = 'enteng_uji_cp7_managed_' + part
        body = begin_part(history, prior) + source + suffix + finish_part(roles)
        size = len(body.encode())
        if size > MAX_BYTES:
            raise ValueError(f'{name} exceeds the bounded migration size: {size}')
        yield name, body
        history.append((name, sql_hash(body)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path, help='Existing empty directory for the six SQL files')
    args = parser.parse_args()
    if not args.destination.is_dir() or any(args.destination.iterdir()):
        parser.error('An existing empty destination directory is required')
    for migration, script in list(migrations(REPAIRS.read_text())):
        with (args.destination / (migration + '.sql')).open('x') as stream:
            stream.write(script)
