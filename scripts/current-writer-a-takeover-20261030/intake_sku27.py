"""Bounded root intake of a18 SKU27 FIRST FAILURE; never a PASS admission.

--prepare reads immutable Git blobs only. --archive requires the one exact
terminal Original below, including all CRC members. No product module import,
database, Auth, browser or network execution is performed by either mode.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import argparse
import ast
import json
import math
import re

from intake_common import (GitBytes, digest, exact, fields, json_bytes, original_zip,
                           originals, pin, require, save, script_pins)
from intake_s05 import CONTRACT_DIRS, FILESET_DIRS

HEAD = 'a18ceb797840934f2cc45222b704b581a00cecf0'
TREE = '4882a589802c910bb433462f6a74d4b8f38add37'
BASE = 'f3d014648d12279dfa89ca8593f25585430a5efe'
BASE_TREE = 'b1c316d6e853805f933a6665a81edf9332d12a36'
NS = 'scripts/current-sku-managed-recovery-native27-qualification/'
WORKFLOW = '.github/workflows/cp7-sku-managed-recovery-native27.yml'
CASE = 'SKU_NATIVE7_COST5_RACES3_PERMISSION_WAITS7_RECOVERY_BUSY1_AUTH_BROWSER4'
MAIN = 'CP7_SKU_MANAGED_RECOVERY_NATIVE27.json'
NATIVE = 'CP7_SKU_PAIR_CONVERSION_NATIVE7.json'
COST = 'CP7_SKU_GROUP_COST_NATIVE5.json'
PACKAGE = 'T3_PACKAGE_INSTALL.json'
FILES = 'T3_PACKAGE_FILES_INSTALL.json'
RESTORE = 'T3_BACKUP_RESTORE_DRILL.json'
ZIP_PIN = dict(bytes=60998025, sha256='3e81b048586c72e5d97452ecdd1b01dbed60aed2c2914baf4bfaffe4601979b6')
RAW_PINS = {
    MAIN: dict(bytes=30196696, sha256='4246105c0126cf6a9937a8ad2b1e78963375ef2ded3146baad669f823fbb25d9'),
    NATIVE: dict(bytes=21032, sha256='02d4491b8c3106fbb31a07550dd16e735f3b6cc0533e2d5b1827b80ea71bb370'),
    COST: dict(bytes=39063, sha256='375dce21f69ded4a6d1be743fddb5af5ed1524bc77d288eaef45585fad096edf'),
    PACKAGE: dict(bytes=360424, sha256='ac3ac739d268dcd3e81940fcde785bc35efbe4a29091250936c8c8f17c536508'),
    FILES: dict(bytes=1806, sha256='14007d43dd9b8e1acfa2b91e35d59047f553b248e2fc06e8362e8ad813003ba7'),
    RESTORE: dict(bytes=1470, sha256='f6128238b3388ab21946e29af97b74c679fa376da51dd72e29543577accc7fa1'),
    'SKU_COST_ARTIFACT_COPY_RECEIPT.json': dict(bytes=11236, sha256='c48b1207729c2f5c47146fadb06903af2a2d82c21212590f98dfdae24558ed30'),
    'SKU27_ORIGINALS_COPY_RECEIPT.json': dict(bytes=14084, sha256='9254ed188a35c9d26168ffb1048380d17ac0f25302075b9818d7d8be9b324eb9'),
    'FROZEN_SOURCE_WORKTREES.json': dict(bytes=2291, sha256='fcfd46f56915951f56384722477fef48967e1239cf63293d285fe12182cd4a78'),
}
NO_GO = dict(production_go=False, independent_acceptance=False)
ALL22 = ('schemas', 'relations', 'columns', 'constraints', 'indexes', 'triggers',
         'functions', 'aggregates', 'types', 'enums', 'sequences', 'policies',
         'extensions', 'roles', 'memberships', 'event_triggers', 'rules',
         'inheritance', 'default_privileges', 'database_authority',
         'type_implementation', 'sequence_ownership')


def strict(raw):
    value = json_bytes(raw)
    def finite(item):
        if type(item) is float:
            require(math.isfinite(item), 'ROOT_SKU_NONFINITE_EXPONENT')
        elif type(item) is dict:
            for child in item.values(): finite(child)
        elif type(item) is list:
            for child in item: finite(child)
    finite(value)
    return value


def literal(g, path, name):
    nodes = [n for n in ast.parse(g.read(path)).body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    exact(len(nodes), 1, 'ROOT_SKU_ONE_LITERAL:' + path + ':' + name)
    return ast.literal_eval(nodes[0].value)


def pure_deriver(g, path, constants, legacy=None, function='derive'):
    """Compile only declarations/derivation function from already pinned blobs.

    Never execute module imports/loaders, entrypoints or business functions.
    Every derive call below supplies raw immutable Git bytes explicitly.
    """
    module = ModuleType('root_sku_pure_' + path.replace('/', '_'))
    module.__dict__.update(ast=ast, sha256=sha256, ROOT=g.root, legacy=legacy, old=legacy)
    selected = []
    for node in ast.parse(g.read(path)).body:
        if isinstance(node, ast.Assign):
            target = node.targets[0]
            root = target.id if isinstance(target, ast.Name) else (
                target.value.id if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) else None)
            if root in constants: selected.append(node)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value.func
            if isinstance(call, ast.Attribute) and isinstance(call.value, ast.Name) and call.value.id == 'SOURCES' and call.attr == 'update':
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name == function:
            selected.append(node)
    require(any(isinstance(n, ast.FunctionDef) for n in selected), 'ROOT_SKU_DERIVER_REQUIRED')
    exec(compile(ast.Module(body=selected, type_ignores=[]), path, 'exec'), module.__dict__)
    return module


def derive_all(g):
    old = pure_deriver(g, 'scripts/current-sku-combined-fixture-followup/derive.py',
                      {'NS', 'BASE', 'SOURCES', 'REPLACEMENTS'})
    prior = pure_deriver(g, 'scripts/current-sku-all-member-native23-qualification/derive.py',
                        {'NS', 'OLD_NS', 'SOURCES', 'IMPORT', 'EXTRA'}, old)
    current = pure_deriver(g, NS + 'derive.py', {'NS', 'OLD_NS', 'SOURCES', 'EXTRA'}, prior)
    texts, proofs = {}, {}
    for key, (path, expected) in current.SOURCES.items():
        raw = g.verify_pin(path, expected)
        texts[key], proofs[key] = current.derive(key, raw)
    engine_old = pure_deriver(g, 'scripts/current-sku-combined-followup-qualification/derive.py', {'REPLACEMENTS'})
    engine = pure_deriver(g, NS + 'engine_delta.py', {'BEFORE', 'AFTER'}, engine_old)
    _, engine_proof = engine.derive(g.read('scripts/current-vendor-receivable-qualification/probe.py'))
    return texts, proofs, engine_proof


def route(text):
    body = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == 'exercise')
    assignments = [n for n in body.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'business' for t in n.targets)]
    exact(len(assignments), 1, 'ROOT_SKU_ONE_ACTUAL_RACE_LOADER')
    expected = "business = load('sku_concurrency_current_pocket_races', ROOT / '" + NS + "races.py')"
    exact(ast.dump(assignments[0]), ast.dump(ast.parse(expected).body[0]), 'ROOT_SKU_CURRENT_CALLER_ROUTE')
    guards = [n for n in ast.walk(body) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and n.func.attr == 'require_runtime_module']
    exact(len(guards), 1, 'ROOT_SKU_ACTUAL_CALLABLE_GATE')
    exact(ast.unparse(guards[0]), 'race_binding.require_runtime_module(business)', 'ROOT_SKU_ACTUAL_CALLABLE_ARGUMENT')
    require(assignments[0].lineno < guards[0].lineno < next(n.lineno for n in body.body if isinstance(n, ast.ClassDef)),
            'ROOT_SKU_CALLABLE_GATE_BEFORE_ANY_CALLBACK')
    return ast.unparse(ast.parse(expected).body[0])


def source(g):
    own = strict(g.read(NS + 'SOURCE.json'))
    fields(own, dict(status='PREPARED_FULL_NATIVE27_NOT_EXECUTED', base_head=BASE,
        base_tree=BASE_TREE, base_file_count=13759, complete_vendor_engine_changes=6,
        frozen_original23_callbacks_edited=0, original_23_ids_retained=True,
        actual_successor_cases=0, actual_Auth_HTTP_cases=0, actual_real_browser_cases=0,
        group_recovery_supported=False, default_adoption=False, **NO_GO), 'ROOT_SKU_SOURCE_SCOPE')
    exact(len(own['files']), 79, 'ROOT_SKU_SOURCE79')
    for name, expected in own['files'].items(): g.verify_pin(name, expected)
    exact(g.git('rev-parse', BASE + '^{tree}').decode().strip(), BASE_TREE, 'ROOT_SKU_BASE_TREE')
    base = g.entries(BASE)
    exact(len(base), 13759, 'ROOT_SKU_PARENT13759')
    parent = strict(g.read(NS + 'PARENT_SOURCE.json'))
    fields(parent, dict(head=BASE, tree=BASE_TREE), 'ROOT_SKU_PARENT_DECLARATION')
    exact(set(parent['files']), set(base), 'ROOT_SKU_COMPLETE_PARENT_PINSET')
    for name, entry in base.items():
        exact(g.tree.get(name), entry, 'ROOT_SKU_PARENT_BLOB_OR_MODE:' + name)
        item = parent['files'][name]
        exact({k: item[k] for k in ('mode', 'blob')}, entry, 'ROOT_SKU_PARENT_PIN_MODE_BLOB')
        g.verify_pin(name, {k: item[k] for k in ('bytes', 'sha256', 'mode')})
    delta = set(g.tree) - set(base)
    exact(delta, set(own['allowed_changes']), 'ROOT_SKU_EXACT_SOURCE_DELTA')
    exact(delta, set(own['files']) | {NS + 'SOURCE.json'}, 'ROOT_SKU_CLOSED_SOURCE_FILES')
    exact(len(delta), 80, 'ROOT_SKU_DELTA80')
    require(all(p.startswith(NS) or p == WORKFLOW for p in delta), 'ROOT_SKU_ONLY_NEW_NAMESPACE_WORKFLOW')
    texts, proofs, engine = derive_all(g)
    exact(proofs, own['private_derivations'], 'ROOT_SKU_ALL15_REVERSIBLE_DERIVATIONS')
    exact(len(proofs), 15, 'ROOT_SKU_DERIVATIONS15')
    fields(engine, dict(counted_changes=6, additional_report_block_changes=1,
        all_install_preuse_reinstall_used_backup_roles_CP6_advisors_Auth_and_five_gates_retained=True), 'ROOT_SKU_ENGINE')
    loader = route(texts['concurrency'])
    schedule = g.read(NS + 'race_schedule.py')
    binder = g.read(NS + 'race_binding.py').decode()
    for anchor in ("actual.__code__!=expected", "actual.__globals__.get('schedule')is not schedule",
                   "getattr(module,'SKU27_DERIVATION',None)", "actual_function.__code__!=expected_functions[name]"):
        require(anchor in binder, 'ROOT_SKU_CODE_GLOBAL_DERIVATION_BINDING')
    # The only changed race assertion is its explicit contention schedule.
    frozen = g.read('scripts/current-sku-pair-conversion-qualification/races.py').decode()
    original_asserts = [ast.get_source_segment(frozen, n) for n in ast.walk(ast.parse(frozen)) if isinstance(n, ast.Assert)]
    current_asserts = [ast.get_source_segment(texts['races'], n) for n in ast.walk(ast.parse(texts['races'])) if isinstance(n, ast.Assert)]
    exact(current_asserts, [x for x in original_asserts if not x.startswith('assert contention.get')], 'ROOT_SKU_FINANCIAL_RACE_ASSERTIONS_EXACT')
    groups = {
        'native': list(literal(g, 'scripts/current-sku-pair-conversion-qualification/cases.py', 'IDS')),
        'cost': list(literal(g, 'scripts/current-sku-group-cost-qualification/cases.py', 'IDS')) + list(literal(g, NS + 'recovery_cases.py', 'IDS')),
        'races': list(literal(g, 'scripts/current-sku-pair-conversion-qualification/races.py', 'IDS')),
        'waits': list(literal(g, 'scripts/current-sku-pair-conversion-qualification/auth_waits.py', 'IDS')) + [literal(g, NS + 'recovery_sessions.py', 'IDS')[0]],
        'busy': [literal(g, NS + 'recovery_sessions.py', 'IDS')[1]],
        'browser': list(literal(g, 'scripts/current-sku-combined-followup-qualification/plan.py', 'BROWSER_IDS')),
    }
    exact([len(v) for v in groups.values()], [7, 5, 3, 7, 1, 4], 'ROOT_SKU_EXACT27_CATEGORIES')
    exact(len(set(x for v in groups.values() for x in v)), 27, 'ROOT_SKU_NO_AGGREGATED_OR_DUPLICATE_IDS')
    browser = strict(g.read(NS + 'BROWSER_SOURCE.json'))
    exact(browser['historical_files'], strict(g.read('scripts/current-sku-pair-browser-qualification/SOURCE.json'))['files'], 'ROOT_SKU_RETAINED_BROWSER_MANIFEST_EXACT')
    for name, expected in browser['current_files'].items(): g.verify_pin(name, expected)
    return dict(status='ROOT_SKU_EXACT_SOURCE_ONLY', head=HEAD, tree=TREE,
        manifest=pin(g.read(NS + 'SOURCE.json')), source_pins=79, parent_files_modes_and_bytes=13759,
        new_namespace_and_workflow_paths=80, immutable_parent_changes=0,
        actual_new_business_cases=0, private_derivations=proofs, complete_engine_derivation=engine,
        case_ids=groups, race_binding=dict(loader_statement=loader, wrapper_path=NS + 'races.py',
        wrapper_sha256=sha256(g.read(NS + 'races.py')).hexdigest(),
        caller_derived_sha256=sha256(texts['concurrency'].encode()).hexdigest(),
        race_derived_sha256=sha256(texts['races'].encode()).hexdigest(), derivation=proofs['races']),
        schedule_source=pin(schedule), current_product_files=browser['current_files'],
        browser_script_sha256=sha256(texts['cases'].encode()).hexdigest(), **NO_GO)


def declared_files(g, value):
    count = 0; maps = 0; unique = set()
    def walk(item):
        nonlocal count, maps
        if type(item) is dict:
            if type(item.get('files')) is dict:
                files = item['files']; maps += 1
                if all(name.startswith(('scripts/', 'src/', 'docs/', 'tests/', '.github/', 'supabase/')) for name in files):
                    prefix = ''
                else:
                    contract = item.get('contract')
                    directory = CONTRACT_DIRS.get(contract) if contract else FILESET_DIRS.get(tuple(files))
                    require(directory is not None, 'ROOT_SKU_UNBOUND_SOURCE_PRODUCER')
                    prefix = 'scripts/' + directory + '/'
                for name, expected in files.items():
                    path = prefix + name; g.verify_pin(path, expected); count += 1; unique.add(path)
            for child in item.values(): walk(child)
        elif type(item) is list:
            for child in item: walk(child)
    walk(value)
    return dict(file_maps=maps, pin_occurrences=count, unique_paths=len(unique), exact_producer_namespace=True)


def full_census(catalog, data):
    exact(set(catalog), set(ALL22), 'ROOT_SKU_ALL22_GROUPS')
    require(all(type(v) is dict for v in catalog.values()), 'ROOT_SKU_TYPED_CATALOG_GROUPS')
    tables = {name for name, row in catalog['relations'].items() if row[1] in ('r', 'p', 'm')}
    seq = {'sequence:' + name for name in catalog['sequences']}
    exact(len(seq), 15, 'ROOT_SKU_ALL15_SEQUENCES')
    exact(set(data), tables | seq, 'ROOT_SKU_ALL_CURRENT_ROWS_AND_ALL_SEQUENCES')
    for name, row in data.items():
        require(type(row) is list and len(row) == 2, 'ROOT_SKU_DATA_ABI')
        if name in seq:
            require(type(row[0]) is str and re.fullmatch(r'-?\d+', row[0]) is not None and type(row[1]) is bool, 'ROOT_SKU_SEQUENCE_ABI')
        else:
            require(type(row[0]) is int and row[0] >= 0 and type(row[1]) is str and re.fullmatch('[0-9a-f]{64}', row[1]) is not None, 'ROOT_SKU_ROW_COUNT_HASH_ABI')
    return dict(tables=len(tables), sequences=len(seq), catalog_groups=22)


def group(value, ids):
    fields(value, dict(status='PASS', counts={'PASS': len(ids)}, planned_case_ids=ids,
        final={key: 'PASS' for key in ids}, missing=[], complete_boundary_restored=True, **NO_GO), 'ROOT_SKU_STRICT_NATIVE_GROUP')
    exact(list(value['cases']), ids, 'ROOT_SKU_NATIVE_CASE_ORDER')
    for name, row in value['cases'].items():
        fields(row, dict(status='PASS', full_boundary_restored=True, public_schema_unchanged=True,
            session_leaks=dict(advisory_locks=0, advisory_lock_keys=[], other_sessions=[])), 'ROOT_SKU_NATIVE_CASE:' + name)


def checked(g, docs, src):
    m, n, cost, package, files, restore = (docs[x] for x in (MAIN, NATIVE, COST, PACKAGE, FILES, RESTORE))
    fields(m, dict(status='INCOMPLETE', qualification_commit=HEAD, expected_case_count=1,
        observed_case_count=1, required_case_ids=[CASE], required_case_ids_pass=False,
        real_Auth_browser_claim=False, formal_CP7C_started=False, full_OW11_acceptance=False,
        scheduler_quiet_before_baseline_restore=True, baseline_full22_all_rows_all_sequences_equal=True,
        restore_raw_public_equal=True, cp6_restored=True, baseline_advisors_equal=True, advisor_gate=True,
        **NO_GO), 'ROOT_SKU_ACTUAL_FIRST_FAILURE_OUTER')
    exact(set(m['committed']), {CASE}, 'ROOT_SKU_EXACT_CURRENT_COMPONENT')
    component = m['committed'][CASE]
    fields(component, dict(status='INCOMPLETE', **NO_GO), 'ROOT_SKU_FAILED_COMPONENT_NOT_PASS')
    ids = src['case_ids']; callback_ids = ids['races'] + ids['waits'][:-1] + ids['waits'][-1:] + ids['busy']
    first, second, follow, ui = (component[k] for k in ('fresh_base_native7', 'fresh_cost_native5', 'fresh_callbacks11', 'fresh_real_Auth_browser4'))
    exact(first['native'], n, 'ROOT_SKU_RAW_NATIVE7_EQUALS_EMBEDDED')
    exact(second['native'], cost, 'ROOT_SKU_RAW_COST5_EQUALS_EMBEDDED')
    exact(first['strict_group_originals'], [dict(name=NATIVE, **RAW_PINS[NATIVE])], 'ROOT_SKU_NATIVE7_RAW_PRODUCER_PIN')
    group(n, ids['native']); group(cost, ids['cost'])
    fields(first, dict(status='PASS', actual_Native_cases=7, used_guard_refused_before_DDL=True,
        full_manual_group_accessory_recovery_claim=False, new_cost_engine_created=False), 'ROOT_SKU_BASE7')
    fields(second, dict(status='PASS', actual_cost_Native_cases=5, group_recovery_supported=False), 'ROOT_SKU_COST5')
    fields(second['dependency'], dict(original_report_sha256=RAW_PINS[NATIVE]['sha256'],
        actual_Native7_original_admitted_by_outer_adapter=True), 'ROOT_SKU_SAME_RUN_NATIVE7_PREREQUISITE')
    fields(follow, dict(status='PASS', actual_two_session_conversion_races=3,
        actual_Native_session_permission_waits=7, actual_Native_nonblocking_busy_cases=1,
        actual_Native_cases=0, actual_Auth_HTTP_cases=0, actual_browser_cases=0,
        same_call_prerequisite_Native_cases=7, full_installed_copy_restores=11,
        used_guard_refused_before_DDL=True, real_Auth_claim=False, **NO_GO), 'ROOT_SKU_RACES11_COUNTS')
    fields(follow['actual_race_callback_binding'], dict(src['race_binding'],
        status='ACTUAL_CURRENT_RACE_MODULE_BOUND_BEFORE_CALLBACKS', compiled_function_identity=True,
        actual_schedule_global_identity=True, financial_case_success_not_implied=True,
        actual_Native_cases=0, actual_two_session_races=0, **NO_GO), 'ROOT_SKU_ACTUAL_CODE_GLOBALS_DERIVATION')
    races = follow['concurrency']
    fields(races, dict(status='RUN_COMPLETE', counts={'PASS': 11}, planned_race_ids=callback_ids,
        database_remaining=0, copy_per_race=True, **NO_GO), 'ROOT_SKU_FRESH_RACES11')
    exact(list(races['races']), callback_ids, 'ROOT_SKU_RACE_ORDER')
    for name, row in races['races'].items():
        fields(row, dict(status='PASS', session_leaks=[]), 'ROOT_SKU_RACE_CASE:' + name)
        retained = row['original_case_result']
        exact({key: row[key] for key in retained}, retained, 'ROOT_SKU_ORIGINAL_RESULT_UNPROJECTED')
        r = row['installed_baseline_restoration']
        fields(r, dict(complete_database_dump_restored=True, all22_all_rows_all_sequences_roles_exact=True,
            cp6_restored=True, advisors_equal=True, only_pg_cron_errors=True, selected_table_cleanup=False), 'ROOT_SKU_EACH_COPY_FULL_RESTORE')
        fields(r['observation'], dict(complete=True, source_scheduler_quiet=True, sessions_before_restore=[],
            all22_portable_unchanged=True, used_guard_refused_before_DDL=True,
            baseline_already_contains_same_call_Native_used_witness=True, restore_raw_public_equal=True), 'ROOT_SKU_COPY_RESTORE_OBSERVATION')
    for index, name in enumerate(ids['races']):
        r = races['races'][name]
        fields(r, dict(same_uuid=index == 0, first_commit=index != 2,
            one_group_exactly_two_Native_parts=True, source=dict(physical=6, reserved=1, available=5),
            target=dict(physical=8, reserved=0, available=8)), 'ROOT_SKU_REAL_RACE_FINANCIAL_POSTCONDITION')
        contention = r['contention']
        if index == 0:
            fields(contention, dict(kind='BLOCKED', holder_blocks_worker=True), 'ROOT_SKU_SAME_UUID_REAL_WAIT')
            exact(r['outcome']['result'], r['holder'], 'ROOT_SKU_COMPLETE_UUID_REPLAY')
        else:
            fields(contention, dict(kind='FAIL_FAST', holder_blocks_worker=False,
                distinct_actual_backend_pids=True, holder_in_transaction_at_refusal=True,
                retry_only_after_holder_release=True, same_request_and_payload_retried=True,
                holder_committed=index == 1), 'ROOT_SKU_ACTUAL_POCKET_SCHEDULE')
            a, b = contention['holder_backend_pid'], contention['worker_backend_pid']
            require(type(a) is type(b) is int and a > 0 and b > 0 and a != b, 'ROOT_SKU_TWO_REAL_BACKENDS')
            fields(contention['first_attempt'], dict(ok=False, sqlstate='P0001'), 'ROOT_SKU_POCKET_REFUSAL')
            require(contention['first_attempt']['message'].startswith('POCKET_PERIOD_BUSY:'), 'ROOT_SKU_POCKET_EXACT_ERROR')
            if index == 1:
                fields(r['outcome'], dict(ok=False, sqlstate='P0001'), 'ROOT_SKU_COMMITTED_STALE')
                require(r['outcome']['message'].startswith('STALE_VERSION:'), 'ROOT_SKU_COMMITTED_STALE_ERROR')
            else: fields(r['outcome'], dict(ok=True), 'ROOT_SKU_ROLLED_BACK_RECOVERY')
    busy = races['races'][ids['busy'][0]]
    fields(busy, dict(declared_cases=1, distinct_busy_attempts=2, complete_noeffect_each_attempt=True,
        actual_Auth_HTTP_cases=0), 'ROOT_SKU_ONE_BUSY_CASE_TWO_ATTEMPTS')
    exact([r['busy_holder'] for r in busy['attempts']], ['FG', 'MATERIAL_NONE'], 'ROOT_SKU_BOTH_LOCK_DOMAINS')
    for r in busy['attempts']:
        fields(r, dict(two_actual_backends=True, nonblocking_busy_refused_while_holder_still_held=True,
            completed_UUID_replay=False, full_copy_restore_required=True), 'ROOT_SKU_BUSY_BEFORE_HOLDER_RELEASE')
    cache = races['races'][ids['waits'][-1]]
    fields(cache, dict(two_actual_backends=True, completed_UUID_replay=True,
        actual_request_row_blocking_observed=True, administrative_actor_not_real_Auth_or_admin_UI=True), 'ROOT_SKU_CACHE_PERMISSION_WAIT')
    fields(cache['answer'], dict(ok=False, sqlstate='42501'), 'ROOT_SKU_CACHE_CURRENT_PERMISSION')
    handoff = component['Native_to_copy_handoff']
    fields(handoff, dict(all22_exact=True, committed_Native_business_rows_and_sequences_unchanged=True,
        source_all_rows_sequences_unchanged_after_callbacks=True), 'ROOT_SKU_HANDOFF')
    exact(handoff['full_data_and_sequences_before_handoff'], handoff['full_data_and_sequences_after_callbacks'], 'ROOT_SKU_FULL_HANDOFF_ROWS_SEQUENCES')
    census = full_census(handoff['raw_current_catalog'], handoff['full_data_and_sequences_before_handoff'])
    catalog_digest = sha256(json.dumps(handoff['raw_current_catalog'], sort_keys=True,
        separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    exact(catalog_digest, handoff['raw_current_catalog_sha256'], 'ROOT_SKU_HANDOFF_RAW_DIGEST')
    exact(handoff['every_race_copy_exact_admission_sha256'], [handoff['raw_current_catalog_sha256']] * 11, 'ROOT_SKU_COPY_HANDOFF_CHAIN')
    exact(len(follow['copy_catalog_admissions']), 11, 'ROOT_SKU_ALL11_COPY_ADMISSIONS')
    exact(len(ui['copy_catalog_admissions']), 1, 'ROOT_SKU_BROWSER_COPY_ADMISSION')
    for row in follow['copy_catalog_admissions'] + ui['copy_catalog_admissions']:
        fields(row, dict(full22_after_must_equal_original_install=True, product_state_modified=False,
            Native_or_schema_or_RPC_permissions_changed=False, all22_groups_equal_original_install=True,
            exact_catalog_sha256=handoff['raw_current_catalog_sha256']), 'ROOT_SKU_EXACT_COPY_AUTHORITY')
        exact(row['actual_copy_after_authority'], row['source_database_authority'], 'ROOT_SKU_COPY_AUTHORITY_RESTORED')
    browser = ui['browser']
    fields(ui, dict(status='INCOMPLETE'), 'ROOT_SKU_BROWSER_FAILED')
    fields(browser, dict(status='INCOMPLETE', counts={'INCOMPLETE': 4}, planned_case_ids=ids['browser'],
        real_auth=True, jwt_signed_by_runtime=False, script_sha256=src['browser_script_sha256'],
        host_exit=0, host_status='RUN_COMPLETE', console_errors=0, users_created=2,
        auth_cleanup_failures=[], host_error=None, session_leaks=[], cleanup_failures=False,
        database_remaining=0, auth_counts=dict(before=[0, 0, 0, 0], after=[0, 0, 0, 0], restored=True),
        cleanup=dict(users_created=0, cleanup_failures=[], rest_remaining=False), **NO_GO), 'ROOT_SKU_BROWSER_HOST_CLEANUP')
    exact(list(browser['cases']), ids['browser'], 'ROOT_SKU_BROWSER_ALL4_REACHED')
    for index, (name, row) in enumerate(browser['cases'].items()):
        fields(row, dict(status='INCOMPLETE'), 'ROOT_SKU_NO_FAILED_BROWSER_CREDIT')
        needle = 'locator.selectOption: Timeout 20000ms exceeded.' if index < 2 else 'AR_OPENING_REQUIRES_READ_COMMITTED'
        require(needle in row['error'], 'ROOT_SKU_EXACT_FIRST_BROWSER_FAILURE')
    fields(package, dict(status='ALL_STAGES_INSTALLED', auth_users_before=0, auth_users_after=0,
        primary_unchanged=True, backup_restore_drill='RESTORED_IDENTICAL', production_go=False, release_evidence=False), 'ROOT_SKU_PACKAGE')
    exact(package['gate'], dict(installed=True, primary_unchanged=True, backup_restore_drill=True,
        security_advisors=True, writer_runtime=False), 'ROOT_SKU_EXACT_FOUR_OF_FIVE_GATES')
    fields(package['run_identity'], dict(tool_head=HEAD, github_sha=HEAD, run_id='41039546903',
        run_attempt='1', workflow='CP7 A SKU managed recovery full Native27', job='p21', mode='install'), 'ROOT_SKU_RUN_IDENTITY')
    fields(restore, dict(status='RESTORED_IDENTICAL', production_go=False, release_evidence=False), 'ROOT_SKU_BACKUP_DRILL')
    exact(restore['checks'], dict(restore_errors_only_pg_cron=True, catalog_explained=True,
        data_identical=True, engine_answer_present=True, engine_equal=True), 'ROOT_SKU_BACKUP_ALL5_CHECKS')
    exact(restore['data']['differ'], {}, 'ROOT_SKU_BACKUP_DATA_EQUAL')
    fields(m['baseline_restore'], dict(unexplained=[], only_pg_cron_errors=True,
        database_owner_acl_and_settings_preserved=True), 'ROOT_SKU_OUTER_BACKUP_RESTORE')
    fields(m['baseline_role_cleanup'], dict(baseline_roles_exact=True), 'ROOT_SKU_OUTER_ROLE_RESTORE')
    exact(m['restore_components'], dict(erp_platform_auth_schema_acl=True,
        all_public_catalog_members_and_row_hashes=True, erp_public_auth_function_definitions_owners_acls=True), 'ROOT_SKU_OUTER_RAW_PUBLIC_AUTH')
    fields(m['focused_preuse_removal'], dict(status='SKU_PAIR_CONVERSION_EXACT_PREUSE_DELTA_RESTORE',
        used_guard_before_DDL=True), 'ROOT_SKU_PREUSE_INVERSE')
    fields(m['focused_preuse_removal']['parent_verified'], dict(status='VENDOR_RECEIVABLE_EXACT_SOURCE_AND_ALL22',
        actual_parent_verified_before_delta=True, projected_catalog=False), 'ROOT_SKU_PREUSE_ACTUAL_PARENT')
    declaration = m['source_declaration']
    fields(declaration, dict(status='EXACT_QUALIFIED21_AND_ACTUAL_CURRENT_F3D_NATIVE27_SOURCE_ADMITTED',
        actual_successor_cases=0, group_recovery_supported=False, **NO_GO), 'ROOT_SKU_ACTUAL_SOURCE_ADMISSION')
    exact(declaration['complete_engine_derivation'], src['complete_engine_derivation'], 'ROOT_SKU_ACTUAL_ENGINE_DERIVATION')
    fields(declaration['full_source_closure'], dict(status='EXACT_PUBLIC_F3D_AND_NEW_NATIVE27_QUALIFIER_SOURCE',
        unchanged_parent_files=13759, parent_sql_exceptions=0, current_physical_sources=True,
        financial_quantity_fullcensus_oracles_changed=False, actual_successor_execution=False, **NO_GO), 'ROOT_SKU_ACTUAL_FULL_SOURCE')
    exact(declaration['current_installation']['files'], src['current_product_files'], 'ROOT_SKU_ACTUAL_CURRENT_PRODUCT10')
    source_maps = declared_files(g, declaration['current_installation'])
    fields(files, dict(status='ALL_FILES_INSTALLED', production_go=False, release_evidence=False), 'ROOT_SKU_PACKAGE_SOURCE')
    package_keys = ['A' + chr(n) for n in range(ord('C'), ord('Z') + 1)] + ['B' + chr(n) for n in range(ord('A'), ord('F') + 1)]
    exact(files['files'], [dict(key=key, status='PASS') for key in package_keys], 'ROOT_SKU_ALL_AC_TO_BF_FILES')
    return dict(status='ROOT_VERIFIED_EXACT_A18_FIRST_FAILURE_NOT_QUALIFIED', source=src,
        original_zip=ZIP_PIN, original_raw_pins=RAW_PINS, CRC_members=150,
        run_id=41039546903, job_id=124008666380, artifact_id=12973314001,
        observed_same_run=dict(Native=7, cost_Native=5, conversion_races=3, permission_waits=7,
            busy_cases=1, busy_subattempts=2, browser_PASS=0, browser_INCOMPLETE=4),
        observed_case_counts=dict(PASS=23, INCOMPLETE=4), qualified_full27=False,
        prior_runs_aggregated=False, actual_Auth_HTTP_case_credit=0,
        package_gates=package['gate'], package_all_five=False, source_maps=source_maps,
        handoff_census=census, outer_restore_receipts=dict(full22_rows_ALL_sequences=True,
            roles=True, raw_public=True, Auth=True, CP6=True, advisors=True),
        outer_raw_before_after_not_serialized=True, browser_runtime_host_receipt='EMBEDDED_EXACT_ORIGINAL_MAIN',
        first_failures={name: row['error'] for name, row in browser['cases'].items()},
        financial_or_product_change_authorized=False, **NO_GO)


def raw_evidence(z, component):
    """Every referenced full refusal/replay census, plus complete cost prefixes.

    Inspect one large member at a time. The exact outer Original admits bytes;
    each producer receipt must independently pin its own physical member.
    """
    references = {}
    def walk(value):
        if type(value) is dict:
            if value.get('all22_and_all_current_rows_sequences_unchanged') is True:
                path = value['raw_path']
                require(path.startswith('cp6-proof/t3/') and Path(path).name == path.removeprefix('cp6-proof/t3/'), 'ROOT_SKU_EXACT_CENSUS_MEMBER_PATH')
                name = Path(path).name
                if name in references: exact(references[name], value, 'ROOT_SKU_DUPLICATE_RECEIPT_DISAGREES')
                references[name] = value
            for child in value.values(): walk(child)
        elif type(value) is list:
            for child in value: walk(child)
    walk(component)
    exact(len(references), 14, 'ROOT_SKU_ALL14_CURRENT_CENSUS_ORIGINALS')
    exact(set(references), {x for x in z.namelist() if x.endswith('_FULL_CURRENT_CENSUS.json')}, 'ROOT_SKU_NO_OMITTED_CENSUS_ORIGINAL')
    result = []
    for name, receipt in references.items():
        raw = z.read(name); exact(pin(raw), {k: receipt[k] for k in ('bytes', 'sha256')}, 'ROOT_SKU_CENSUS_PHYSICAL_PIN')
        value = strict(raw); del raw
        exact(set(value), {'before', 'after'}, 'ROOT_SKU_CENSUS_TWO_COMPLETE_BOUNDARIES')
        exact(value['before'], value['after'], 'ROOT_SKU_STRICT_FULL_NO_EFFECT')
        summary = full_census(value['before']['catalog'], value['before']['data_and_sequences'])
        exact(digest(value['before']), receipt['before_sha256'], 'ROOT_SKU_RAW_BEFORE_DIGEST')
        exact(digest(value['after']), receipt['after_sha256'], 'ROOT_SKU_RAW_AFTER_DIGEST')
        exact(receipt['dropped_fields'], [], 'ROOT_SKU_NO_DROPPED_FIELDS')
        result.append(dict(name=name, **pin(z.read(name)), **summary))
    prefix = component['cost_strict_rollback_and_sequence_prefix']
    fields(prefix, dict(all22_equal=True, all_current_table_rows_equal=True), 'ROOT_SKU_COST_STRICT_ROLLBACK')
    outer = prefix['sequence_prefix']; chain = outer['before']; rows = []
    for name, case in component['fresh_cost_native5']['native']['cases'].items():
        receipt = case['complete_case_sequence_raw']; path = receipt['path']
        require(path.startswith('cp6-proof/t3/') and Path(path).name == path.removeprefix('cp6-proof/t3/'), 'ROOT_SKU_EXACT_PREFIX_MEMBER')
        raw = z.read(Path(path).name); exact(pin(raw), {k: receipt[k] for k in ('bytes', 'sha256')}, 'ROOT_SKU_PREFIX_PIN')
        value = strict(raw); proof = case['complete_case_sequence_prefix']
        fields(value, dict(case_id=name, before=proof['before'], after=proof['after'], first_failure=None,
            observation_error=None, per_savepoint_sequence_restore_claim=False, full_restore_required=True), 'ROOT_SKU_PREFIX_ORIGINAL')
        exact(proof['before'], chain, 'ROOT_SKU_SEQUENCE_PREFIX_CHAIN')
        fields(proof, dict(all_current_sequences_recorded=True, per_case_sequence_restore_claim=False,
            full_sequence_restoration_owned_by='FULL_OUTER_DATABASE_BACKUP_RESTORE_AND_ALL_FIVE_PACKAGE_GATES'), 'ROOT_SKU_PREFIX_NO_RESEED_CLAIM')
        exact(len(proof['before']), 15, 'ROOT_SKU_ALL15_PREFIX_SEQUENCES')
        changed = {}
        for key, old in proof['before'].items():
            new = proof['after'][key]
            require(type(old[0]) is type(new[0]) is str and type(old[1]) is type(new[1]) is bool, 'ROOT_SKU_PREFIX_ABI')
            require(int(new[0]) >= int(old[0]) and not (old[1] and not new[1]), 'ROOT_SKU_SEQUENCE_REWIND')
            if old != new: changed[key] = dict(before=old, after=new, last_value_delta=str(int(new[0])-int(old[0])))
        exact(changed, proof['changed'], 'ROOT_SKU_COMPLETE_SEQUENCE_DELTA')
        chain = proof['after']; rows.append(dict(case_id=name, raw=pin(raw)))
    exact(chain, outer['after'], 'ROOT_SKU_GROUP_PREFIX_END')
    return dict(raw_full_noeffect_censuses=result, complete_cost_sequence_prefixes=rows,
        all14_full22_all_rows_ALL15_sequence_raw_boundaries_exact=True,
        all5_cost_sequence_prefixes_original_and_contiguous=True, per_savepoint_sequence_restore_claim=False)


def controls(g, docs, src):
    rows = []
    def refuse(name, operation):
        try: operation()
        except (ValueError, KeyError, AssertionError, TypeError) as error:
            rows.append(dict(name=name, refusal=str(error).splitlines()[0][:220])); return
        raise ValueError('ROOT_SKU_NEGATIVE_CONTROL_ACCEPTED:' + name)
    for name, raw in [('duplicate', b'{"a":1,"a":2}'), ('NaN', b'{"a":NaN}'),
                      ('overflow', b'{"a":1e999}')]:
        refuse(name, lambda raw=raw: strict(raw))
    refuse('bool_is_not_integer', lambda: exact(True, 1, 'ROOT_SKU_TYPED_COUNT'))
    refuse('float_is_not_integer', lambda: exact(7.0, 7, 'ROOT_SKU_TYPED_COUNT'))
    for name, change in [
        ('failed_outer_cannot_become_PASS', lambda d: d[MAIN].__setitem__('status', 'PASS')),
        ('historical_head_refused', lambda d: d[MAIN].__setitem__('qualification_commit', 'c397409a470c8c3d5f4963bbbdd7b676b1275af7')),
        ('fifth_gate_fabricated', lambda d: d[PACKAGE]['gate'].__setitem__('writer_runtime', True)),
        ('Auth_cleanup_missing', lambda d: d[MAIN]['committed'][CASE]['fresh_real_Auth_browser4']['browser']['auth_counts'].__setitem__('restored', False)),
        ('four_browser_failures_relabelled', lambda d: d[MAIN]['committed'][CASE]['fresh_real_Auth_browser4']['browser'].__setitem__('counts', {'PASS': 4})),
        ('actual_schedule_global_missing', lambda d: d[MAIN]['committed'][CASE]['fresh_callbacks11']['actual_race_callback_binding'].__setitem__('actual_schedule_global_identity', False)),
        ('actual_code_identity_missing', lambda d: d[MAIN]['committed'][CASE]['fresh_callbacks11']['actual_race_callback_binding'].__setitem__('compiled_function_identity', False)),
        ('outer_ALLseq_restore_false', lambda d: d[MAIN].__setitem__('baseline_full22_all_rows_all_sequences_equal', False)),
        ('raw_native_group_changed', lambda d: d[NATIVE]['cases'][src['case_ids']['native'][0]].__setitem__('status', 'INCOMPLETE')),
    ]:
        value = deepcopy(docs); change(value)
        refuse(name, lambda value=value: checked(g, value, src))
    return dict(status='ROOT_SOURCE_ONLY_NEGATIVE_CONTROLS_REFUSED', count=len(rows), rows=rows,
        actual_new_cases=0, fake_actual_PASS_fixtures=0)


def intake(root, archive=None, with_controls=False):
    with GitBytes(root, HEAD, TREE) as g:
        src = source(g)
        if archive is None:
            return dict(status='ROOT_SKU_SOURCE_PREPARED_ONLY_NO_ACTUAL_CREDIT', source=src,
                actual_current_cases_credited=0, full27_qualified=False, required_original=ZIP_PIN, **NO_GO)
        with original_zip(archive, ZIP_PIN, 150) as z:
            _, docs = originals(z, RAW_PINS)
            for value in docs.values(): strict(json.dumps(value).encode())
            result = checked(g, docs, src)
            result['raw_evidence'] = raw_evidence(z, docs[MAIN]['committed'][CASE])
            if with_controls: result['controls'] = controls(g, docs, src)
        result['intake_scripts'] = script_pins('intake_sku27.py', 'intake_s05.py')
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--archive')
    parser.add_argument('--controls', action='store_true')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    save(intake(args.source_root, args.archive, args.controls), args.output)
