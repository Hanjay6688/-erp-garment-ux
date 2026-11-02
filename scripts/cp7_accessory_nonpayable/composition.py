"""Prepared nonpayable GOOD delta, closed behind actual FREE3 acceptance.

No connection, commit, executable workflow or automatic seed is supplied.
The administrative caller owns its transaction and complete restore boundary.
"""
from hashlib import sha256
from pathlib import Path
import importlib
import json

from . import admission, native_derivation, ri_catalog, workflow

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCHEMA = ri_catalog.SCHEMA
CONTRACT = 'cp7.accessory-good-nonpayable.v1'
SQL = ('policy.sql', 'basis.sql')
TABLES = tuple(SCHEMA + '.' + name for name in ('category_versions_v1', 'good_bases_v1'))
USED_ERROR = 'NONPAYABLE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
EMPTY = [0, sha256(b'[]').hexdigest()]
FUNCTIONS = {
    'immutable_v1()': (False, 'v'),
    'timeline_token_v1()': (False, 's'),
    'record_version_v1(date,uuid,uuid,text,text)': (True, 'v'),
    'good_basis_v1(uuid,uuid,timestamp with time zone)': (True, 'v'),
    'snapshot_identity_v1(uuid)': (False, 's'),
    'capture_basis_v1(uuid,uuid,numeric,jsonb)': (True, 'v'),
    'guard_category_date_v1()': (True, 'v'),
    'guard_special_change_v1()': (True, 'v'),
    'zero_reimbursement_contractor_v1(uuid)': (True, 'v'),
    'booked_hpp_v1(uuid)': (True, 'v'),
    'recost_delta_v1(uuid)': (True, 'v'),
    'already_recosted_v1(uuid,numeric,numeric)': (True, 'v'),
}
FUNCTIONS = {SCHEMA + '.' + name: value for name, value in FUNCTIONS.items()}
RELATIONS = {SCHEMA + '.' + name for name in (
    'category_versions_v1', 'category_versions_v1_pkey', 'category_versions_v1_effective_from_key',
    'category_versions_v1_request_id_key', 'category_versions_source_event_v1', 'good_bases_v1',
    'good_bases_v1_pkey', 'good_bases_lot_v1', 'good_bases_special_policy_v1',
    'good_bases_category_policy_v1', 'good_bases_contractor_day_v1')}


def qualification():
    return admission.parent_receipt()


def parent():
    qualification()
    with admission.parent_scope():
        module = importlib.import_module('cp7_current_de_free_date.composition')
    if Path(module.__file__).resolve() != ROOT / 'scripts/cp7_current_de_free_date/composition.py':
        raise ValueError('NONPAYABLE_EXACT_NATURAL_PARENT_MODULE_REQUIRED')
    return module


def runtime():
    return parent().runtime()


def source_manifest():
    value = admission.strict((HERE / 'SOURCE.json').read_bytes())
    if (value.get('contract') != CONTRACT or type(value.get('actual_Native_cases')) is not int
        or value['actual_Native_cases'] != 0
        or value.get('production_go') is not False or value.get('independent_acceptance') is not False):
        raise ValueError('NONPAYABLE_EXACT_PREPARATION_SOURCE_REQUIRED')
    required = {str(path.relative_to(ROOT)) for path in HERE.rglob('*')
        if path.is_file() and (path.suffix in ('.py', '.sql', '.mjs')
            or path.name in ('NATIVE_ORIGIN.json', 'UI_ORIGIN.json', 'UI_SOURCE.json', 'afui15.workflow.yml.txt',
                'RUNTIME_DOMAIN_PREFLIGHT_ORIGIN.json'))}
    active_workflow = workflow.admit_source(value)
    if active_workflow is not None:
        required.add(workflow.WORKFLOW)
    if set(value['files']) != required:
        raise ValueError('NONPAYABLE_COMPLETE_OWN_SOURCE_MANIFEST_REQUIRED')
    for name, expected in value['files'].items():
        path = ROOT / name
        if ((not name.startswith('scripts/' + SCHEMA + '/')
                and not (name == workflow.WORKFLOW and active_workflow is not None)) or '..' in Path(name).parts
            or path.is_symlink() or admission.pin(path.read_bytes()) != admission.require_pin(expected)):
            raise ValueError('NONPAYABLE_OWN_SOURCE_CHANGED:' + name)
    native_derivation.derive(native_derivation.originals())
    return value


def owner_scope(cur):
    qualification()
    from cp7_laundry_unknown_wash.composition import as_owner
    return as_owner(cur, 'postgres')


def sources():
    receipt = qualification()
    manifest = source_manifest()
    actual = parent().sources()
    accepted = admission.qualified_parent_sources(receipt, actual)
    _, proof = native_derivation.derive(native_derivation.originals())
    return dict(contract=CONTRACT, parent=actual, source=manifest, qualified_parent_sources=accepted,
        Native_derivations=proof, GOOD_eligibility_policy_decided=True, owner_decision='D17-20',
        new_public_rpcs=0, actual_Native_cases=0, production_go=False, independent_acceptance=False)


def transition(before, after, definitions):
    if len(before) != 22 or set(before) != set(after):
        raise ValueError('NONPAYABLE_COMPLETE_ALL22_REQUIRED')
    expected_definitions, _ = native_derivation.derive(native_derivation.originals())
    if definitions != expected_definitions:
        raise ValueError('NONPAYABLE_EXACT_COUNTED_DERIVED_DEFINITIONS_REQUIRED')
    external = ri_catalog.expected_external_triggers(after['constraints'])
    for group in before:
        for key in set(before[group]) | set(after[group]):
            old, new = before[group].get(key), after[group].get(key)
            if old == new:
                continue
            if (group == 'functions' and key in definitions and old is not None and new is not None
                and new[0] == definitions[key] and old[1:] == new[1:]):
                continue
            if old is None and new is not None:
                if group == 'schemas' and key == SCHEMA:
                    continue
                if group == 'functions' and key in FUNCTIONS:
                    continue
                if group == 'triggers' and key in external and new == external[key]:
                    continue
                if (group in ('relations', 'columns', 'constraints', 'indexes', 'triggers',
                              'types', 'type_implementation', 'policies') and key.startswith(SCHEMA + '.')):
                    continue
            raise ValueError('NONPAYABLE_UNDECLARED_CATALOG_CHANGE:' + group + ':' + key)
    if set(after['functions']) - set(before['functions']) != set(FUNCTIONS):
        raise ValueError('NONPAYABLE_EXACT_PRIVATE_FUNCTION_SET_REQUIRED')
    if set(after['relations']) - set(before['relations']) != RELATIONS:
        raise ValueError('NONPAYABLE_EXACT_PRIVATE_RELATION_SET_REQUIRED')
    added = {key: value for key, value in after['triggers'].items()
        if key not in before['triggers'] and not key.startswith(SCHEMA + '.')}
    if added != external:
        raise ValueError('NONPAYABLE_EXACT_EXTERNAL_TRIGGER_SET_REQUIRED')
    for name in definitions:
        if after['functions'].get(name, [None])[0] != definitions[name]:
            raise ValueError('NONPAYABLE_DERIVED_NATIVE_FUNCTION_MISSING:' + name)


def raw_authority(cur):
    return {name: list(cur.execute('select p.oid::text,pg_get_userbyid(p.proowner),p.proacl::text '
        'from pg_proc p where p.oid=%s::regprocedure', (name,)).fetchone())
        for name in native_derivation.originals()}


def binding(catalog, state):
    return catalog.digest(dict(sources=state['sources'], parent_binding=state['parent_binding'],
        actual_parent_binding=state['predecessor']['component_binding'],
        recomputed_parent_binding=parent().binding(catalog, state['predecessor']),
        before=state['before'], after=state['after'], raw_native_authority=state['raw_native_authority'],
        definitions=state['definitions'], preuse=state['preuse_data_and_sequences'],
        before_data=state['before_data'], preinstall=state['preinstall_data_and_sequences']))


def require_parent_state(catalog, state):
    prior = state['predecessor']
    admission.qualified_parent_sources(qualification(), prior['sources'])
    if (prior['sources'] != parent().sources() or prior['after'] != state['before']
        or prior['component_binding'] != state['parent_binding']
        or parent().binding(catalog, prior) != state['parent_binding']
        or prior['preuse_data_and_sequences'] != state['before_data']
        or prior['preinstall_data_and_sequences'] != state['preinstall_data_and_sequences']
        or state['preuse_data_and_sequences'] != dict(state['before_data'], **{table: EMPTY for table in TABLES})):
        raise ValueError('NONPAYABLE_EXACT_ACCEPTED_PARENT_STATE_REQUIRED')


def private_authority(cur):
    roles = [row[0] for row in cur.execute("select rolname from pg_roles where "
        "rolname in('anon','authenticated','service_role') or rolname like 'cp7_%'")]
    for signature, (definer, volatility) in FUNCTIONS.items():
        owner, actual_definer, actual_volatility, config = cur.execute(
            'select pg_get_userbyid(proowner),prosecdef,provolatile,proconfig from pg_proc '
            'where oid=%s::regprocedure', (signature,)).fetchone()
        if (owner != 'postgres' or actual_definer != definer or actual_volatility != volatility
            or 'search_path=""' not in (config or ())):
            raise ValueError('NONPAYABLE_PRIVATE_FUNCTION_AUTHORITY_CHANGED:' + signature)
        for role in roles:
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (role, signature)).fetchone()[0]:
                raise ValueError('NONPAYABLE_PRIVATE_FUNCTION_EXPOSED:' + role + ':' + signature)
    for table in TABLES:
        if cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class '
                       'where oid=%s::regclass', (table,)).fetchone() != ('postgres', True):
            raise ValueError('NONPAYABLE_PRIVATE_RLS_AND_OWNER_REQUIRED:' + table)
    for role in roles:
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE,CREATE')", (role, SCHEMA)).fetchone()[0]:
            raise ValueError('NONPAYABLE_PRIVATE_SCHEMA_EXPOSED:' + role)
        for table in TABLES:
            if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",
                           (role, table)).fetchone()[0]:
                raise ValueError('NONPAYABLE_PRIVATE_TABLE_EXPOSED:' + role + ':' + table)


def verify(cur, state):
    qualification()
    _, _, _, _, catalog = runtime()
    catalog._authority(cur)
    require_parent_state(catalog, state)
    if state['sources'] != sources() or state['component_binding'] != binding(catalog, state):
        raise ValueError('NONPAYABLE_SOURCE_OR_COMPONENT_BINDING_CHANGED')
    actual = catalog._catalog_rows(cur)
    if actual != state['after']:
        raise ValueError('NONPAYABLE_ACTUAL_COMPLETE_ALL22_CHANGED')
    transition(state['before'], actual, state['definitions'])
    if raw_authority(cur) != state['raw_native_authority']:
        raise ValueError('NONPAYABLE_RAW_NATIVE_OID_OWNER_OR_ACL_CHANGED')
    private_authority(cur)
    return dict(status='NONPAYABLE_EXACT_COUNTED_NATIVE_AND_ALL22',
        accepted_parent_verified_before_delta=True, projected_parent_catalog=False,
        Native_raw_authority_preserved=True, new_public_rpcs=0, actual_Native_cases=0,
        GOOD_eligibility_policy_decided=True, Afui_GOOD_nonpayable_path_complete=False,
        production_go=False, independent_acceptance=False)


def install_delta(cur, qualified_parent):
    receipt = qualification()
    p = parent()
    admission.qualified_parent_sources(receipt, qualified_parent['sources'])
    pins = sources()
    _, _, _, base, catalog = runtime()
    with base.atomic(cur):
        base.predecessor.predecessor._locks(cur)
        proof = p.verify(cur, qualified_parent)
        before, data = catalog._catalog_rows(cur), catalog._data(cur)
        if SCHEMA in before['schemas'] or data != qualified_parent['preuse_data_and_sequences']:
            raise ValueError('NONPAYABLE_EXACT_UNUSED_PARENT_REQUIRED')
        actual = {name: before['functions'][name][0] for name in native_derivation.originals()}
        origin = admission.strict((HERE / 'NATIVE_ORIGIN.json').read_bytes())
        if any(before['functions'][name][1:] != row['metadata'] for name, row in origin['functions'].items()):
            raise ValueError('NONPAYABLE_NATIVE_PREDECESSOR_METADATA_CHANGED')
        definitions, derivations = native_derivation.derive(actual)
        authority = raw_authority(cur)
        with owner_scope(cur):
            for name in SQL:
                cur.execute((HERE / name).read_text(), prepare=False)
            for definition in definitions.values():
                cur.execute(definition, prepare=False)
        after, preuse = catalog._catalog_rows(cur), catalog._data(cur)
        if preuse != dict(data, **{table: EMPTY for table in TABLES}):
            raise ValueError('NONPAYABLE_INSTALL_CHANGED_EXISTING_ROWS_OR_SEQUENCES')
        if raw_authority(cur) != authority:
            raise ValueError('NONPAYABLE_INSTALL_CHANGED_RAW_NATIVE_AUTHORITY')
        state = dict(sources=pins, predecessor=qualified_parent, parent_proof=proof,
            parent_binding=qualified_parent['component_binding'], before=before, after=after,
            raw_native_authority=authority, definitions=definitions, derivations=derivations,
            before_data=data, preuse_data_and_sequences=preuse,
            preinstall_data_and_sequences=qualified_parent['preinstall_data_and_sequences'])
        state['component_binding'] = binding(catalog, state)
        verify(cur, state)
        return state


def install(cur):
    qualification()
    p = parent()
    sources()
    _, _, _, base, _ = runtime()
    with base.atomic(cur):
        return install_delta(cur, p.install(cur))


def rollback_delta_preuse(cur, state):
    qualification()
    _, _, _, base, catalog = runtime()
    with base.atomic(cur):
        base.predecessor.predecessor._locks(cur)
        verify(cur, state)
        catalog._lock_tables(cur)
        if catalog._data(cur) != state['preuse_data_and_sequences']:
            raise ValueError(USED_ERROR)
        with owner_scope(cur):
            for signature in state['definitions']:
                cur.execute(native_derivation.originals()[signature], prepare=False)
            cur.execute('drop schema ' + SCHEMA + ' cascade')
        if (catalog._catalog_rows(cur) != state['before'] or catalog._data(cur) != state['before_data']
            or raw_authority(cur) != state['raw_native_authority']):
            raise ValueError('NONPAYABLE_EXACT_PARENT_NOT_RESTORED')
        return dict(status='NONPAYABLE_EXACT_PREUSE_DELTA_INVERSE', used_guard_before_DDL=True,
            parent=parent().verify(cur, state['predecessor']))


def rollback_preuse(cur, state):
    qualification()
    _, _, _, base, _ = runtime()
    with base.atomic(cur):
        delta = rollback_delta_preuse(cur, state)
        return dict(status='NONPAYABLE_FULL_PREUSE_INVERSE', delta=delta,
            parent=parent().rollback_preuse(cur, state['predecessor']))
