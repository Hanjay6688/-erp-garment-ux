"""A-only disposable composition of the exact tested finance reader bodies.

This provider is not registered with the default installer. It preserves the
actual predecessor verification and every catalog group. Admission remains
closed until the concurrent-source qualification has an accepted Original.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CONTRACT = 'cp7.current-choice-readonly-finance-qualification.v1'
USED_ERROR = 'READONLY_FINANCE_COMPOSITION_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
REPLACED = {'erp.run_v268_financial_report_checks()', 'cp7_finance.workspace(jsonb)'}
ADDED = {'cp7_finance.read_opening_hpp_diagnostic_v1(uuid,date)',
         'cp7_finance.read_snapshot_readiness_diagnostic_v1(date,date,date)'}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prerequisites():
    binding = json.loads((HERE / 'PREREQUISITES.json').read_bytes())
    return accepted_prerequisites(binding)


def accepted_prerequisites(binding):
    race = binding['source_race']
    if race is None:
        raise ValueError('SOURCE_RACE_ACCEPTED_ORIGINAL_REQUIRED')
    if (race['head'] != 'bd3505f624fb4e821ea9ef2ea039313abd850fd5'
            or race['status'] != 'PASS' or race['source_change_race_qualification'] is not True
            or race['package_gate'] != {key: True for key in ('installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')}
            or race['cp6_restored'] is not True or race['advisor_gate'] is not True):
        raise ValueError('SOURCE_RACE_ACCEPTANCE_CHANGED')
    return binding


def runtime():
    import cp7_current_choice_preparation.installation as predecessor
    from cp7_production_stage import _row, _body
    reuse = load('composed_exact_readiness_reader', REPO / 'scripts/current-finance-check-reuse-diagnostic/readiness_reuse.py')
    return predecessor, reuse, _row, _body


def sources():
    binding = prerequisites()
    pins = json.loads((HERE / 'DERIVATION.json').read_bytes())
    for path, digest in pins['files'].items():
        if sha256((REPO / path).read_bytes()).hexdigest() != digest:
            raise ValueError('READONLY_FINANCE_QUALIFIED_DERIVATION_CHANGED:' + path)
    predecessor, _, _, _ = runtime()
    return dict(contract=CONTRACT, predecessor=predecessor.sources(),
                qualified_prerequisites=binding, exact_derivation=pins,
                files={name: sha256((HERE / name).read_bytes()).hexdigest()
                       for name in ('composition.py', 'PREREQUISITES.json', 'DERIVATION.json')})


def admit_delta(before, after):
    if set(before) != set(after) or len(before) != 22:
        raise ValueError('READONLY_FINANCE_ALL22_REQUIRED')
    changed = set()
    for group in before:
        for key in set(before[group]) | set(after[group]):
            left, right = before[group].get(key), after[group].get(key)
            if left == right:
                continue
            changed.add((group, key))
            if group == 'functions' and key in REPLACED:
                if left is not None and right is not None and left[1:] == right[1:]:
                    continue
            if group == 'functions' and key in ADDED and left is None and right is not None:
                continue
            raise ValueError('READONLY_FINANCE_UNDECLARED_DELTA:' + group + ':' + key)
    if changed != {('functions', key) for key in REPLACED | ADDED}:
        raise ValueError('READONLY_FINANCE_INCOMPLETE_DELTA')


def binding(predecessor, prior, proof):
    return predecessor.catalog.digest(dict(sources=prior['sources'], before=prior['before'],
                                           after=prior['after'], actual_verification=proof))


def verify(cur, state):
    predecessor, reuse, row, body = runtime()
    catalog = predecessor.catalog
    catalog._authority(cur)
    prior, proof = state['predecessor'], state['predecessor_verified_before_delta']
    if (state['sources'] != sources() or prior['sources'] != predecessor.sources()
            or state['predecessor_binding_sha256'] != binding(predecessor, prior, proof)
            or proof.get('contract') != predecessor.CONTRACT
            or proof.get('status') != 'EXACT_CURRENT_FROZEN_CHOICE_PREPARATION_ALL22'
            or proof.get('all22_transition_chain_verified') is not True
            or proof.get('substituted_catalog_or_definitions') is not False
            or state['before'] != prior['before']
            or state['preinstall_data_and_sequences'] != prior['preinstall_data_and_sequences']
            or state['preuse_data_and_sequences'] != prior['preuse_data_and_sequences']):
        raise ValueError('READONLY_FINANCE_ACTUAL_PREDECESSOR_CHANGED')
    admit_delta(prior['after'], state['after'])
    if catalog._catalog_rows(cur) != state['after']:
        raise ValueError('READONLY_FINANCE_ACTUAL_FULL22_CHANGED')
    originals = state['original_rows']
    if set(originals) != REPLACED or set(state['rows']) != REPLACED | ADDED:
        raise ValueError('READONLY_FINANCE_FUNCTION_SET_CHANGED')
    expected_bodies = {
        reuse.reader.REPORT: body(reuse.reader.report_definition(originals[reuse.reader.REPORT][0])),
        reuse.WORKSPACE: reuse.rewrite(originals[reuse.WORKSPACE][1]),
        reuse.reader.PRIVATE: reuse.reader.readonly_body(row(cur, reuse.reader.ORIGINAL)[1]),
        reuse.PRIVATE: reuse.sibling_body(row(cur, reuse.SNAPSHOT)[1], row(cur, reuse.PREFLIGHT)[1]),
    }
    for signature, expected in expected_bodies.items():
        actual = row(cur, signature)
        if actual != state['rows'][signature] or actual[1] != expected:
            raise ValueError('READONLY_FINANCE_LIVE_BODY_CHANGED:' + signature)
        if signature in REPLACED and actual[2:] != originals[signature][2:]:
            raise ValueError('READONLY_FINANCE_EXISTING_AUTHORITY_CHANGED:' + signature)
        if signature in ADDED:
            search_path = ['search_path=""'] if signature == reuse.reader.PRIVATE else ['search_path=erp, public, pg_catalog, pg_temp']
            if actual[2:6] != ['postgres', True, 's', search_path]:
                raise ValueError('READONLY_FINANCE_PRIVATE_AUTHORITY_CHANGED:' + signature)
            expected_grants = {('postgres', 'postgres', 'EXECUTE', False)}
            if signature == reuse.PRIVATE:
                expected_grants.add(('cp7_finance_read', 'postgres', 'EXECUTE', False))
            grants = state['after']['functions'][signature][-1]
            if len(grants) != len(expected_grants) or {tuple(x) for x in grants} != expected_grants:
                raise ValueError('READONLY_FINANCE_PRIVATE_GRANTS_CHANGED:' + signature)
            for role in ('anon', 'authenticated', 'service_role', 'cp7_capture', 'cp7_finance_read', 'cp7_alert'):
                expected_access = signature == reuse.PRIVATE and role == 'cp7_finance_read'
                if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (role, signature)).fetchone()[0] is not expected_access:
                    raise ValueError('READONLY_FINANCE_PRIVATE_EXECUTE_CHANGED:' + signature + ':' + role)
    return dict(contract=CONTRACT, status='EXACT_CURRENT_CHOICE_READONLY_FINANCE_ALL22',
                predecessor_verified_before_actual_delta=True, all22_transition_chain_verified=True,
                substituted_catalog_or_definitions=False, new_private_functions=2,
                existing_function_replacements=2, new_public_rpcs=0, new_tables=0,
                qualification_only=True, schedules_changed=False, timeout_changed=False,
                default_adopted=False, production_go=False)


def install(cur):
    pins = sources()  # Refuse missing actual race acceptance before any DDL.
    predecessor, reuse, row, _ = runtime()
    if cur.connection.info.host not in ('localhost', '127.0.0.1') or cur.connection.info.port != 54322:
        raise ValueError('READONLY_FINANCE_DISPOSABLE_HOST_REQUIRED')
    if cur.execute('select current_database()').fetchone() != ('cp6_rollback',):
        raise ValueError('READONLY_FINANCE_DISPOSABLE_DATABASE_REQUIRED')
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur)
        before, data = predecessor.catalog._catalog_rows(cur), predecessor.catalog._data(cur)
        prior = predecessor.install(cur)
        proof = predecessor.verify(cur, prior)
        old = {signature: row(cur, signature) for signature in REPLACED}
        evidence = reuse.install_for_rollback(cur)
        if predecessor.catalog._data(cur) != prior['preuse_data_and_sequences']:
            raise ValueError('READONLY_FINANCE_INSTALL_CHANGED_ROWS_OR_SEQUENCES')
        state = dict(sources=pins, before=before, preinstall_data_and_sequences=data, predecessor=prior,
                     predecessor_verified_before_delta=proof,
                     predecessor_binding_sha256=binding(predecessor, prior, proof),
                     original_rows=old, exact_reader_installation=evidence,
                     rows={signature: row(cur, signature) for signature in REPLACED | ADDED},
                     after=predecessor.catalog._catalog_rows(cur),
                     preuse_data_and_sequences=prior['preuse_data_and_sequences'])
        verify(cur, state)
        return state


def rollback_preuse(cur, state):
    predecessor, _, _, _ = runtime()
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur)
        verify(cur, state)
        predecessor.catalog._lock_tables(cur)
        if predecessor.catalog._data(cur) != state['preuse_data_and_sequences']:
            raise ValueError(USED_ERROR)
        for saved in state['original_rows'].values():
            cur.execute(saved[0], prepare=False)
        for signature in sorted(ADDED):
            cur.execute('drop function ' + signature + ' restrict')
        predecessor.verify(cur, state['predecessor'])
        removed = predecessor.rollback_preuse(cur, state['predecessor'])
        if predecessor.catalog._catalog_rows(cur) != state['before'] or predecessor.catalog._data(cur) != state['preinstall_data_and_sequences']:
            raise ValueError('READONLY_FINANCE_FULL_INVERSE_NOT_EXACT')
        return dict(contract=CONTRACT, status='EXACT_READONLY_FINANCE_PREUSE_INVERSE', predecessor=removed,
                    all22_preinstall_equal=True, all_rows_and_sequences_equal=True,
                    global_used_guard_before_any_DDL=True, qualification_only=True, production_go=False)
