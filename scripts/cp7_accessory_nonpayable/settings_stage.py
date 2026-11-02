"""Prepared settings facade over the gated nonpayable financial component.

The exact actual FREE3 receipt is still required before any ERP import or SQL.
No connection, commit, dispatch or executable workflow is provided.
"""
from hashlib import sha256
from pathlib import Path
import re

from . import composition as financial, ui_derivation

HERE = Path(__file__).resolve().parent
SCHEMA = financial.SCHEMA
ROLE = 'cp7_good_policy_date'
TABLE = SCHEMA + '.date_requests_v1'
CONTRACT = 'cp7.good-policy-date-settings-stage.v1'
USED_ERROR = 'GOOD_POLICY_DATE_SETTINGS_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
PUBLIC = {'public.erp_cp7_get_good_policy_dates_v1(jsonb)',
    'public.erp_cp7_save_good_policy_date_v1(jsonb,uuid,boolean)'}
PRIVATE = {SCHEMA + '.settings_access_v1(boolean)', SCHEMA + '.settings_event_v1(uuid)',
    SCHEMA + '.settings_workspace_v1(jsonb)', SCHEMA + '.settings_save_v1(jsonb,uuid,boolean)'}
ENTRYPOINTS = {SCHEMA + '.settings_workspace_v1(jsonb)', SCHEMA + '.settings_save_v1(jsonb,uuid,boolean)'}
RELATIONS = {TABLE, TABLE + '_pkey', SCHEMA + '.date_requests_actor_v1'}
COLUMNS = {TABLE + ':' + name for name in ('request_id', 'actor_id', 'request_body', 'response', 'recorded_at')}
COLUMNS |= {TABLE + '_pkey:request_id', SCHEMA + '.date_requests_actor_v1:actor_id'}


def runtime():
    financial.qualification()
    return financial.runtime()


def function_bodies():
    result = {}
    pattern = (r"create function ([a-z0-9_.]+)\(([^)]*)\)\nreturns jsonb language (sql|plpgsql) "
        r"(stable|volatile) security definer set search_path='' as \$\$(.*?)\$\$;")
    for name, arguments, language, volatility, body in re.findall(pattern, (HERE / 'settings.sql').read_text(), re.S):
        types = [argument.strip().split()[1] for argument in arguments.split(',') if argument.strip()]
        result[name + '(' + ','.join(types) + ')'] = dict(body=body, language=language,
            volatility={'stable': 's', 'volatile': 'v'}[volatility])
    if set(result) != PUBLIC | PRIVATE:
        raise ValueError('GOOD_POLICY_DATE_EXACT_SIX_FUNCTION_BODIES_REQUIRED')
    return result


def sources():
    financial.qualification()
    return dict(contract=CONTRACT, parent=financial.sources(), settings_ui=ui_derivation.source_manifest(),
        files={str((HERE / name).relative_to(financial.ROOT)): financial.admission.pin((HERE / name).read_bytes())
            for name in ('settings.sql', 'settings_stage.py', 'test_settings.mjs')},
        public_entrypoints=sorted(PUBLIC), new_public_rpcs=2, Native_financial_definitions_changed=0,
        actual_Native_cases=0, actual_Auth_HTTP_cases=0, actual_browser_cases=0,
        production_go=False, independent_acceptance=False)


def external_triggers(constraints):
    constraint = TABLE + ':date_requests_v1_actor_id_fkey'
    expected = ['f', False, False, True, True, 0, True, None, 'erp.app_users_pkey', TABLE,
        'FOREIGN KEY (actor_id) REFERENCES erp.app_users(id)']
    if constraints.get(constraint) != expected:
        raise ValueError('GOOD_POLICY_DATE_EXACT_ACTOR_FOREIGN_KEY_REQUIRED')
    result = {}
    for function, kind in (('"RI_FKey_noaction_del"()', 9), ('"RI_FKey_noaction_upd"()', 17)):
        key = 'erp.app_users:' + TABLE + ':date_requests_v1_actor_id_fkey:' + function + ':' + str(kind)
        result[key] = [True, 'O', kind, 0, '', [], False, False, function, None, None, None,
            'date_requests_v1_actor_id_fkey', TABLE, None, TABLE]
    return result


def transition(before, after):
    if len(before) != 22 or set(before) != set(after):
        raise ValueError('GOOD_POLICY_DATE_SETTINGS_COMPLETE_ALL22_REQUIRED')
    edges = external_triggers(after['constraints'])
    schema = before['schemas'][SCHEMA]
    expected_schema = [schema[0], sorted(schema[1] + [[ROLE, 'postgres', 'USAGE', False]])]
    expected_role = [False, False, False, False, False, False, False, -1, None, sha256(b'').hexdigest()]
    # Supabase's postgres is a CREATEROLE non-superuser. PostgreSQL 17 grants
    # its creator ADMIN-only membership using the bootstrap administrator.
    # A superuser creator (the explicit catalogue model) receives no such row.
    creator = before['roles']['postgres']
    automatic = {}
    if creator[0] is False:
        if creator[2] is not True or before['roles'].get('supabase_admin', [False])[0] is not True:
            raise ValueError('GOOD_POLICY_DATE_EXACT_POSTGRES_CREATOR_AND_BOOTSTRAP_REQUIRED')
        automatic[ROLE + ':postgres:supabase_admin'] = [True, False, False]
    for group in before:
        for key in set(before[group]) | set(after[group]):
            old, new = before[group].get(key), after[group].get(key)
            if old == new:
                continue
            if group == 'schemas' and key == SCHEMA and new == expected_schema:
                continue
            if old is None and new is not None:
                if group == 'roles' and key == ROLE and new == expected_role:
                    continue
                if group == 'memberships' and key in automatic and new == automatic[key]:
                    continue
                if group == 'functions' and key in PUBLIC | PRIVATE:
                    continue
                if group == 'triggers' and key in edges and new == edges[key]:
                    continue
                if group == 'relations' and key in RELATIONS:
                    continue
                if group == 'indexes' and key in RELATIONS - {TABLE}:
                    continue
                if group == 'columns' and key in COLUMNS:
                    continue
                if group in ('constraints', 'triggers') and key.startswith(TABLE + ':'):
                    continue
                if group in ('types', 'type_implementation') and key in (TABLE, TABLE + '[]'):
                    continue
            raise ValueError('GOOD_POLICY_DATE_SETTINGS_UNDECLARED_CATALOG_CHANGE:' + group + ':' + key)
    if set(after['functions']) - set(before['functions']) != PUBLIC | PRIVATE:
        raise ValueError('GOOD_POLICY_DATE_EXACT_SIX_NEW_FUNCTIONS_REQUIRED')
    if set(after['relations']) - set(before['relations']) != RELATIONS:
        raise ValueError('GOOD_POLICY_DATE_EXACT_THREE_NEW_RELATIONS_REQUIRED')
    if set(after['columns']) - set(before['columns']) != COLUMNS:
        raise ValueError('GOOD_POLICY_DATE_EXACT_TABLE_AND_INDEX_COLUMNS_REQUIRED')
    if set(after['roles']) - set(before['roles']) != {ROLE}:
        raise ValueError('GOOD_POLICY_DATE_EXACT_SINGLE_FACADE_ROLE_REQUIRED')
    if {key: value for key, value in after['memberships'].items()
        if key not in before['memberships']} != automatic:
        raise ValueError('GOOD_POLICY_DATE_EXACT_ADMIN_ONLY_CREATOR_MEMBERSHIP_REQUIRED')
    added = {key: row for key, row in after['triggers'].items()
        if key not in before['triggers'] and not key.startswith(TABLE + ':')}
    if added != edges:
        raise ValueError('GOOD_POLICY_DATE_EXACT_TWO_ACTOR_RI_TRIGGERS_REQUIRED')


def raw_schemas(cur):
    return {name: list(cur.execute('select pg_get_userbyid(nspowner),nspacl::text '
        'from pg_namespace where nspname=%s', (name,)).fetchone()) for name in ('public', SCHEMA)}


def authority(cur):
    bodies = function_bodies()
    roles = [row[0] for row in cur.execute("select rolname from pg_roles where "
        "rolname in('anon','authenticated','service_role') or rolname like 'cp7_%'")]
    for signature, body in bodies.items():
        owner, definer, volatility, language, config, actual_body = cur.execute(
            'select pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile,l.lanname,p.proconfig,p.prosrc '
            'from pg_proc p join pg_language l on l.oid=p.prolang where p.oid=%s::regprocedure', (signature,)).fetchone()
        if (owner != (ROLE if signature in PUBLIC else 'postgres') or definer is not True
            or volatility != body['volatility'] or language != body['language']
            or config != ['search_path=""'] or actual_body != body['body']):
            raise ValueError('GOOD_POLICY_DATE_FUNCTION_BODY_OR_AUTHORITY_CHANGED:' + signature)
        for role in roles:
            expected = role in ('authenticated', ROLE) if signature in PUBLIC else role == ROLE and signature in ENTRYPOINTS
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (role, signature)).fetchone()[0] != expected:
                raise ValueError('GOOD_POLICY_DATE_FUNCTION_EXPOSURE_CHANGED:' + signature + ':' + role)
    for role in roles:
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')", (role, SCHEMA)).fetchone()[0] != (role == ROLE):
            raise ValueError('GOOD_POLICY_DATE_SCHEMA_EXPOSURE_CHANGED:' + role)
        if cur.execute("select has_schema_privilege(%s,%s,'CREATE')", (role, SCHEMA)).fetchone()[0]:
            raise ValueError('GOOD_POLICY_DATE_SCHEMA_CREATE_EXPOSED:' + role)
        for table in financial.TABLES + (TABLE,):
            if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",
                           (role, table)).fetchone()[0]:
                raise ValueError('GOOD_POLICY_DATE_PRIVATE_TABLE_EXPOSED:' + role + ':' + table)
        for signature in financial.FUNCTIONS:
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (role, signature)).fetchone()[0]:
                raise ValueError('GOOD_POLICY_DATE_FINANCIAL_FUNCTION_EXPOSED:' + role + ':' + signature)
    if cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class '
                   'where oid=%s::regclass', (TABLE,)).fetchone() != ('postgres', True):
        raise ValueError('GOOD_POLICY_DATE_REQUEST_RLS_AND_OWNER_REQUIRED')


def binding(catalog, state):
    return catalog.digest(dict(sources=state['sources'], before=state['before'], after=state['after'],
        parent_binding=state['parent_binding'], recomputed_parent_binding=financial.binding(catalog, state['parent']),
        before_data=state['before_data'], preuse=state['preuse_data_and_sequences'],
        preinstall=state['preinstall_data_and_sequences'], before_raw_schemas=state['before_raw_schemas'],
        after_raw_schemas=state['after_raw_schemas'], raw_native_authority=state['raw_native_authority']))


def verify(cur, state):
    financial.qualification()
    _, _, _, _, catalog = runtime()
    catalog._authority(cur)
    prior = state['parent']
    if (state['sources'] != sources() or prior['sources'] != financial.sources()
        or state['before'] != prior['after'] or state['before_data'] != prior['preuse_data_and_sequences']
        or state['parent_binding'] != prior['component_binding']
        or financial.binding(catalog, prior) != state['parent_binding']
        or state['preuse_data_and_sequences'] != dict(state['before_data'], **{TABLE: financial.EMPTY})
        or state['preinstall_data_and_sequences'] != prior['preinstall_data_and_sequences']):
        raise ValueError('GOOD_POLICY_DATE_SETTINGS_EXACT_FINANCIAL_PARENT_STATE_REQUIRED')
    if state['component_binding'] != binding(catalog, state):
        raise ValueError('GOOD_POLICY_DATE_SETTINGS_COMPONENT_BINDING_CHANGED')
    actual = catalog._catalog_rows(cur)
    if actual != state['after']:
        raise ValueError('GOOD_POLICY_DATE_SETTINGS_ACTUAL_ALL22_CHANGED')
    transition(state['before'], actual)
    if raw_schemas(cur) != state['after_raw_schemas'] or financial.raw_authority(cur) != state['raw_native_authority']:
        raise ValueError('GOOD_POLICY_DATE_RAW_SCHEMAS_OR_NATIVE_AUTHORITY_CHANGED')
    authority(cur)
    return dict(status='GOOD_POLICY_DATE_SETTINGS_EXACT_SOURCE_BODIES_AUTHORITY_AND_ALL22',
        financial_parent_verified_before_delta=True, parent_verifier_not_called_on_changed_catalogue=True,
        new_public_rpcs=2, Native_financial_definitions_changed=0, actual_Native_cases=0,
        actual_Auth_HTTP_cases=0, actual_browser_cases=0, production_go=False, independent_acceptance=False)


def install_delta(cur, financial_state):
    financial.qualification()
    pins = sources()
    _, _, _, base, catalog = runtime()
    with base.atomic(cur):
        base.predecessor.predecessor._locks(cur)
        proof = financial.verify(cur, financial_state)
        before, data, raw = catalog._catalog_rows(cur), catalog._data(cur), raw_schemas(cur)
        if (ROLE in before['roles'] or any(signature in before['functions'] for signature in PUBLIC | PRIVATE)
            or data != financial_state['preuse_data_and_sequences']):
            raise ValueError('GOOD_POLICY_DATE_SETTINGS_EXACT_UNUSED_FINANCIAL_PARENT_REQUIRED')
        if any(row[1] is None for row in raw.values()):
            raise ValueError('GOOD_POLICY_DATE_EXPLICIT_RAW_SCHEMA_ACLS_REQUIRED_BEFORE_DDL')
        native = financial.raw_authority(cur)
        with financial.owner_scope(cur):
            cur.execute((HERE / 'settings.sql').read_text(), prepare=False)
        after, preuse, raw_after = catalog._catalog_rows(cur), catalog._data(cur), raw_schemas(cur)
        if preuse != dict(data, **{TABLE: financial.EMPTY}) or raw_after['public'] != raw['public']:
            raise ValueError('GOOD_POLICY_DATE_SETTINGS_INSTALL_CHANGED_ROWS_SEQUENCES_OR_PUBLIC_RAW_ACL')
        if financial.raw_authority(cur) != native:
            raise ValueError('GOOD_POLICY_DATE_SETTINGS_INSTALL_CHANGED_RAW_NATIVE_AUTHORITY')
        state = dict(sources=pins, parent=financial_state, parent_proof=proof,
            parent_binding=financial_state['component_binding'], before=before, after=after, before_data=data,
            preuse_data_and_sequences=preuse, preinstall_data_and_sequences=financial_state['preinstall_data_and_sequences'],
            before_raw_schemas=raw, after_raw_schemas=raw_after, raw_native_authority=native)
        state['component_binding'] = binding(catalog, state)
        verify(cur, state)
        return state


def install(cur):
    financial.qualification()
    sources()
    _, _, _, base, _ = runtime()
    with base.atomic(cur):
        return install_delta(cur, financial.install(cur))


def inverse_sql():
    return ("drop function public.erp_cp7_get_good_policy_dates_v1(jsonb);\n"
        "drop function public.erp_cp7_save_good_policy_date_v1(jsonb,uuid,boolean);\n"
        "drop table cp7_accessory_nonpayable.date_requests_v1;\n"
        "drop function cp7_accessory_nonpayable.settings_access_v1(boolean);\n"
        "drop function cp7_accessory_nonpayable.settings_event_v1(uuid);\n"
        "drop function cp7_accessory_nonpayable.settings_workspace_v1(jsonb);\n"
        "drop function cp7_accessory_nonpayable.settings_save_v1(jsonb,uuid,boolean);\n"
        "revoke usage on schema cp7_accessory_nonpayable from cp7_good_policy_date;\n"
        "drop role cp7_good_policy_date;")


def rollback_delta_preuse(cur, state):
    financial.qualification()
    _, _, _, base, catalog = runtime()
    with base.atomic(cur):
        base.predecessor.predecessor._locks(cur)
        verify(cur, state)
        catalog._lock_tables(cur)
        if catalog._data(cur) != state['preuse_data_and_sequences']:
            raise ValueError(USED_ERROR)
        with financial.owner_scope(cur):
            cur.execute(inverse_sql(), prepare=False)
        if (catalog._catalog_rows(cur) != state['before'] or catalog._data(cur) != state['before_data']
            or raw_schemas(cur) != state['before_raw_schemas'] or financial.raw_authority(cur) != state['raw_native_authority']):
            raise ValueError('GOOD_POLICY_DATE_SETTINGS_EXACT_FINANCIAL_PARENT_NOT_RESTORED')
        return dict(status='GOOD_POLICY_DATE_SETTINGS_EXACT_PREUSE_DELTA_INVERSE', used_guard_before_DDL=True,
            financial_parent=financial.verify(cur, state['parent']))


def rollback_preuse(cur, state):
    financial.qualification()
    _, _, _, base, _ = runtime()
    with base.atomic(cur):
        delta = rollback_delta_preuse(cur, state)
        return dict(status='GOOD_POLICY_DATE_SETTINGS_FULL_PREUSE_INVERSE', delta=delta,
            financial_parent=financial.rollback_preuse(cur, state['parent']))
