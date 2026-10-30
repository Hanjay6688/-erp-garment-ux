"""S05 reader on the actual SKU composition; no connection/commit.

Source integration candidate only. The caller must admit the current SKU
qualification and complete source before executing this additive installation.

The caller owns the isolated transaction. Native fixtures/transitions happen
on the parent BEFORE this stage is installed. The read must leave every row,
sequence and existing catalog object equal. Remove only this stage, verify the
actual parent, then perform another Native transition. No seal regeneration,
projected catalog, parent function replacement or automatic predecessor install.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCHEMA = 'cp7_accessory_standard_report'
ROLE = 'cp7_accessory_standard_read'
PUBLIC = 'public.erp_cp7_get_accessory_standard_report_v1(date,date,uuid,uuid,text,integer,integer)'
FUNCTIONS = {
    SCHEMA+'.iso(timestamp with time zone)': (False, 's'),
    SCHEMA+'.access_now()': (True, 'v'),
    SCHEMA+'.period_data(date,date,uuid,uuid)': (True, 's'),
    SCHEMA+'.workspace(date,date,uuid,uuid,text,integer,integer)': (True, 'v'),
    PUBLIC: (True, 'v'),
}


def parent():
    from cp7_sku_pair_conversion import composition
    return composition


def sources():
    pins = json.loads((HERE/'SOURCE.json').read_bytes())
    assert pins['contract'] == 'cp7.s05-sku-normal-app.v1'
    assert pins['production_go'] is pins['independent_acceptance'] is False
    for path, digest in pins['files'].items():
        if sha256((ROOT/path).read_bytes()).hexdigest() != digest:
            raise ValueError('S05_SOURCE_CHANGED: '+path)
    return dict(stage=pins, parent=parent().sources())


def function_sources():
    bodies = dict(re.findall(r'create function\s+([\w.]+)\([^$]*?as \$\$(.*?)\$\$;', (ROOT/'scripts/cp7_accessory_standard_report/report.sql').read_text(), re.I | re.S))
    if set(bodies) != {signature.split('(')[0] for signature in FUNCTIONS}:
        raise ValueError('S05_DECLARED_SOURCE_FUNCTION_SET_CHANGED')
    return bodies


def transition(before, after):
    if set(before) != set(after) or len(before) != 22:
        raise ValueError('S05_ALL22_REQUIRED')
    for group in before:
        for key in set(before[group]) | set(after[group]):
            old, new = before[group].get(key), after[group].get(key)
            if old == new:
                continue
            if old is None and new is not None:
                if group == 'schemas' and key == SCHEMA:
                    continue
                if group == 'roles' and key == ROLE:
                    continue
                if group == 'functions' and key in FUNCTIONS:
                    continue
            raise ValueError('S05_UNDECLARED_CATALOG_DELTA: '+group+':'+key)
    if set(after['functions'])-set(before['functions']) != set(FUNCTIONS):
        raise ValueError('S05_EXACT_FUNCTION_SET_REQUIRED')


def verify(cur, state):
    _, _, _, _, catalog = parent().runtime()
    catalog._authority(cur)
    if state['sources'] != sources() or state['parent_sources'] != parent().sources():
        raise ValueError('S05_PARENT_SOURCE_CHANGED')
    if state['parent_proof']['status'] != 'SKU_PAIR_CONVERSION_EXACT_SOURCE_AND_ALL22':
        raise ValueError('S05_EXACT_PARENT_PROOF_REQUIRED')
    if catalog.digest(dict(before=state['before'], proof=state['parent_proof'], sources=state['parent_sources'])) != state['parent_binding']:
        raise ValueError('S05_PARENT_BINDING_CHANGED')
    actual = catalog._catalog_rows(cur)
    if actual != state['after']:
        raise ValueError('S05_ACTUAL_ALL22_CHANGED')
    transition(state['before'], actual)
    if cur.execute('select rolcanlogin,rolinherit,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls from pg_roles where rolname=%s', (ROLE,)).fetchone() != (False,)*7:
        raise ValueError('S05_READER_AUTHORITY_CHANGED')
    if cur.execute('select exists(select 1 from pg_auth_members where roleid=%s::regrole or member=%s::regrole)', (ROLE, ROLE)).fetchone()[0]:
        raise ValueError('S05_ROLE_MEMBERSHIP')
    roles = [r[0] for r in cur.execute("select rolname from pg_roles where rolname in('anon','authenticated','service_role')or rolname like 'cp7_%'")]
    expected_sources = function_sources()
    for sig, (definer, volatility) in FUNCTIONS.items():
        expected_owner = ROLE if sig == PUBLIC else 'postgres'
        row = cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure', (sig,)).fetchone()
        if row != (expected_owner, definer, volatility, ['search_path=""']):
            raise ValueError('S05_FUNCTION_AUTHORITY: '+sig)
        if cur.execute('select prosrc from pg_proc where oid=%s::regprocedure', (sig,)).fetchone()[0] != expected_sources[sig.split('(')[0]]:
            raise ValueError('S05_INSTALLED_FUNCTION_SOURCE_CHANGED: '+sig)
        for who in roles:
            wanted = (sig == PUBLIC and who in ('authenticated', ROLE)) or (sig.endswith('.workspace(date,date,uuid,uuid,text,integer,integer)') and who == ROLE)
            if bool(cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0]) != wanted:
                raise ValueError('S05_FUNCTION_EXPOSED: '+who+':'+sig)
    for who in roles:
        if who != ROLE and cur.execute("select has_schema_privilege(%s,%s,'USAGE')", (who, SCHEMA)).fetchone()[0]:
            raise ValueError('S05_PRIVATE_SCHEMA_EXPOSED: '+who)
    if cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relkind in('r','p','v','m')and has_table_privilege(%s,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))", (ROLE,)).fetchone()[0]:
        raise ValueError('S05_NO_DIRECT_ERP_GRANTS')
    if cur.execute("select exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='erp'and has_function_privilege(%s,p.oid,'EXECUTE')and not has_function_privilege('public',p.oid,'EXECUTE'))", (ROLE,)).fetchone()[0]:
        raise ValueError('S05_NO_NATIVE_WRITER_GRANTS')
    return dict(status='S05_EXACT_ADDITIVE_READER_ALL22', parent_verified_before_addition=True, parent_definitions_and_grants_unchanged=True,
                actual_reader_function_source_sha256={sig: sha256(expected_sources[sig.split('(')[0]].encode()).hexdigest() for sig in FUNCTIONS},
                new_public_reads=1, business_DML=False, independent_acceptance=False, production_go=False)


def installer_identity(cur):
    """Supported rehearsal profile, checked before DDL; no role escalation.

    as_owner('postgres') may select a non-superuser CREATEROLE. The original
    report SQL explicitly sets all five final owners, so execute that complete
    SQL as the already-authorized administrative superuser instead. This avoids
    creator auto-memberships and temporary schema grants, including NULL ACL
    materialization. CP7C/non-superuser installation is not qualified here.
    """
    row = cur.execute("select current_user::text,session_user::text,r.rolsuper,"
                      "(select rolsuper from pg_roles where rolname=session_user),"
                      "current_setting('createrole_self_grant') "
                      "from pg_roles r where r.rolname=current_user").fetchone()
    if row is None or row[0] not in ('postgres', 'supabase_admin') or row[2] is not True:
        raise ValueError('S05_ALREADY_AUTHORIZED_ADMINISTRATIVE_SUPERUSER_REQUIRED_BEFORE_DDL')
    return dict(status='S05_EXISTING_OUTER_SUPERUSER_ORIGINAL_DDL', outer_role=row[0], session_role=row[1],
                outer_current_superuser=row[2], session_superuser=row[3], original_createrole_self_grant=row[4],
                temporary_schema_grants=0, temporary_role_memberships=0, GUC_changes=0,
                persistent_authority_change=False)


def installer_function_grants(cur):
    """An unexpected outer-role default grant is refused, never normalized."""
    actual = {}
    for signature in FUNCTIONS:
        rows = [tuple(row) for row in cur.execute(
            "select pg_get_userbyid(a.grantor)::text,case when a.grantee=0 then 'PUBLIC' "
            "else pg_get_userbyid(a.grantee)::text end,a.privilege_type,a.is_grantable "
            "from pg_proc p cross join lateral aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a "
            "where p.oid=%s::regprocedure", (signature,))]
        owner = ROLE if signature == PUBLIC else 'postgres'
        expected = {(owner, owner, 'EXECUTE', False)}
        if signature == PUBLIC:
            expected.add((owner, 'authenticated', 'EXECUTE', False))
        elif signature == SCHEMA+'.workspace(date,date,uuid,uuid,text,integer,integer)':
            expected.add((owner, ROLE, 'EXECUTE', False))
        if len(rows) != len(expected) or set(rows) != expected:
            # Retain a bounded explanation before the inherited atomic wrapper
            # rolls this DDL back. Never normalize an unexpected default grant.
            limit = 16
            defaults = [tuple(row) for row in cur.execute(
                "select pg_get_userbyid(d.defaclrole)::text,coalesce(n.nspname::text,'GLOBAL'),"
                "d.defaclobjtype::text,pg_get_userbyid(a.grantor)::text,"
                "case when a.grantee=0 then 'PUBLIC'else pg_get_userbyid(a.grantee)::text end,"
                "a.privilege_type,a.is_grantable,count(*)over() "
                "from pg_default_acl d left join pg_namespace n on n.oid=d.defaclnamespace "
                "cross join lateral aclexplode(d.defaclacl) a "
                "where d.defaclrole=(select oid from pg_roles where rolname=current_user) "
                "and d.defaclobjtype='f'and(d.defaclnamespace=0 or d.defaclnamespace="
                "(select pronamespace from pg_proc where oid=%s::regprocedure)) "
                "order by 1,2,3,4,5,6,7 limit 17", (signature,))]
            total = int(defaults[0][7]) if defaults else 0
            diagnostic = dict(installer=cur.execute('select current_user::text').fetchone()[0],
                row_limit=limit, actual_acl_rows=[list(row) for row in sorted(rows)[:limit]],
                actual_acl_total=len(rows), actual_acl_omitted=max(0, len(rows)-limit),
                expected_acl_rows=[list(row) for row in sorted(expected)],
                installer_function_default_acl_rows=[list(row[:7]) for row in defaults[:limit]],
                installer_function_default_acl_total=total,
                installer_function_default_acl_omitted=max(0, total-limit))
            raise ValueError('S05_UNEXPECTED_INSTALLER_FUNCTION_GRANT: '+signature+'; '+
                             json.dumps(diagnostic, sort_keys=True, separators=(',', ':')))
        actual[signature] = [list(row) for row in sorted(rows)]
    return actual


def install_delta(cur, qualified_parent):
    p = parent()
    _, _, _, predecessor, catalog = p.runtime()
    with predecessor.atomic(cur):
        capability = installer_identity(cur)
        proof = p.verify(cur, qualified_parent)  # actual installed parent, before DDL
        before, data = catalog._catalog_rows(cur), catalog._data(cur)
        if SCHEMA in before['schemas'] or ROLE in before['roles']:
            raise ValueError('S05_ALREADY_INSTALLED')
        pins = sources()
        cur.execute((ROOT/'scripts/cp7_accessory_standard_report/report.sql').read_text(), prepare=False)
        capability['actual_function_grants'] = installer_function_grants(cur)
        if installer_identity(cur) != {k: v for k, v in capability.items() if k != 'actual_function_grants'}:
            raise ValueError('S05_INSTALLER_ROLE_OR_GUC_CHANGED')
        state = dict(sources=pins, parent_sources=p.sources(), parent_proof=proof, before=before, data=data,
                     after=catalog._catalog_rows(cur), parent_binding=catalog.digest(dict(before=before, proof=proof, sources=p.sources())),
                     installer_capability=capability)
        transition(before, state['after'])
        if catalog._data(cur) != data:
            raise ValueError('S05_INSTALL_DML')
        verify(cur, state)
        return state


def uninstall_delta(cur, state, qualified_parent):
    p = parent()
    _, _, _, predecessor, catalog = p.runtime()
    with predecessor.atomic(cur):
        capability = installer_identity(cur)
        verify(cur, state)
        if catalog._data(cur) != state['data']:
            raise ValueError('S05_READ_CHANGED_ROWS_OR_SEQUENCES')
        cur.execute('drop owned by '+ROLE+' cascade; drop role '+ROLE, prepare=False)
        if installer_identity(cur) != capability:
            raise ValueError('S05_UNINSTALLER_ROLE_OR_GUC_CHANGED')
        if catalog._catalog_rows(cur) != state['before'] or catalog._data(cur) != state['data']:
            raise ValueError('S05_PARENT_NOT_EXACTLY_RESTORED')
        return p.verify(cur, qualified_parent)


@contextmanager
def reader_only(cur, qualified_parent):
    state = install_delta(cur, qualified_parent)
    try:
        yield state
    finally:
        uninstall_delta(cur, state, qualified_parent)
