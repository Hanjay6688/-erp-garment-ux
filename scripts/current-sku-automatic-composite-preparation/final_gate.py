"""Exact Native25, fresh browser2 Originals, and complete owning restoration."""
from pathlib import Path
from types import FunctionType, SimpleNamespace
import importlib.util
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RETAINED = ROOT / 'scripts/current-sku-money-composite-preparation/money_current_parent_final_gate.py'
RETAINED_PIN = dict(bytes=7590, sha256='893b39f9d88d134a3262f88c743e6085aad3967fc72dd0bc00a236c54dd9b60d')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load('automatic_final_owning_runtime', HERE / 'qualification.py')
component, admission = runtime.component, runtime.admission
money_gate = load('automatic_final_exact_retained_preflight_validator',
                  ROOT / 'scripts/current-sku-money-composite-preparation/money_gate_support.py')
prerequisites = load('automatic_final_complete_prerequisite_declarations', HERE / 'native_preflight.py')
MAIN, NATIVE = runtime.LABEL + '.json', component.LABEL + '.json'
PREFLIGHT = component.LABEL + '_PREFLIGHT.json'
SUPERVISION = 'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_RUNTIME_SUPERVISION.json'
BROWSER = 'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_BROWSER2.json'
browser_gate = load('automatic_final_complete_browser2_gate', HERE / 'browser_gate.py')
catalogue = load('automatic_final_complete_catalogue', HERE / 'global_parent_catalogue.py')
economic_pool = load('automatic_final_exact_economic_pool_projection', HERE / 'economic_pool.py')
# Full25 functions from the 0b59 owning Original. Only the credit guard's
# database-local trigger OID digest varies between the reviewed installations.
BASELINE_FUNCTIONS = dict(bytes=8582240, sha256='fca6874d731c369b2b19a370db1fc9b1675badeb00312fb4dd8ec19db5a3c275')
CREDIT_GUARD = 'cp7_credit.assert_source_native_trigger_census_v1()'
CREDIT_SEAL = '1ed4e207a3d715a522ed0b77b0f7629fa765721b4c034d847b54db5fafdaa25a'
SEAL_LITERAL = re.compile(r"(?m)^ if actual_sha256 is distinct from '([0-9a-f]{64})'then$")
ROUTES = (
    ('actual_Native_cases=19', 'actual_Native_cases=25', 3),
    ('actual_business_cases=19', 'actual_business_cases=27', 1),
    ('actual_browser_cases=0', 'actual_browser_cases=2', 2),
    ('real_Auth_browser_claim=False', 'real_Auth_browser_claim=True', 1),
    ('actual_Auth_browser=False', 'actual_Auth_browser=True', 1),
    ("qualification_scope='NATIVE_COMPONENT_ONLY'", "qualification_scope='NATIVE25_AND_CURRENT_BROWSER2'", 1),
    ("counts={'PASS':19}", "counts={'PASS':25}", 1),
    ("qualification_scope='CURRENT_PARENT_SKU_MONEY_NATIVE19_ONLY'",
     "qualification_scope='CURRENT_PARENT_SKU_MONEY_AUTOMATIC_NATIVE25_BROWSER2_ONLY'", 1),
)


def validate_preflight(p, part, value):
    p.exact(part['native_prerequisites'], value, 'AUTOMATIC_COMPLETE_FIRST_PREFLIGHT_ORIGINAL')
    p.fields(value, dict(status='PASS', errors=[], all_prerequisites_checked_before_first_case=True,
                        all22_rows_and_all_sequences_unchanged=True, actual_ERP_cases=0, production_go=False),
             'AUTOMATIC_BATCH_PREFLIGHT_AND_UNCHANGED_CURRENT_BOUNDARY')
    # Validate the exact nested retained Original, without relabeling it.
    money_gate.validate_preflight(p, dict(part, native_prerequisites=value['retained_money19']), value['retained_money19'])
    p.exact(value['supplier_account_mappings'], {key: [[True, True]] for key in prerequisites.SUPPLIER_ACCOUNT_MAPPINGS},
            'AUTOMATIC_ACTIVE_POSTABLE_SUPPLIER_ACCOUNT_MAPPINGS')
    p.exact(value['automatic_functions'], {name: True for name in prerequisites.FUNCTIONS}, 'AUTOMATIC_ALL_SIX_NATIVE_FUNCTIONS')
    p.exact(set(value['automatic_actors']), set(prerequisites.ACTOR_FUNCTIONS), 'AUTOMATIC_BOTH_REAL_NATIVE_ACTORS')
    for name, signatures in prerequisites.ACTOR_FUNCTIONS.items():
        actor = value['automatic_actors'][name]
        if actor.get('role') not in ('OWNER', 'ADMIN'):
            raise ValueError('AUTOMATIC_ACTUAL_OWNER_ADMIN_REQUIRED:' + name)
        database = actor.get('database_role')
        if (type(database) is not list or len(database) != 2 or database[0] != 'authenticated'
                or type(database[1]) is not str or not database[1]):
            raise ValueError('AUTOMATIC_ORDINARY_AUTHENTICATED_ACTOR_REQUIRED:' + name)
        p.fields(actor, dict(permission_source='public.erp_get_my_access_v1()'), 'AUTOMATIC_EXACT_PUBLIC_ACCESS_SOURCE:' + name)
        p.exact(actor['permissions'], {key: True for key in prerequisites.ACTOR_PERMISSIONS[name]}, 'AUTOMATIC_ALL_ACTUAL_ACTOR_PERMISSIONS:' + name)
        p.exact(actor['functions'], {key: True for key in signatures}, 'AUTOMATIC_ALL_ACTUAL_ACTOR_EXECUTE_PRIVILEGES:' + name)
    p.exact(value['natural_callers'], dict(
        upstream=dict(status='NATIVE_AUTOMATIC_CALLER_APIS_BOUND_NOT_EXECUTED', calls=6,
                      original_AFUI_physical_constructor=True, actual_ERP_cases=0),
        invoices=dict(original_invoice_helper_shapes=4, actual_ERP_cases=0)), 'AUTOMATIC_COMPLETE_NATURAL_CALLER_SHAPES')


def derive(raw, *, focused=False):
    if admission.pin(raw) != RETAINED_PIN:
        raise ValueError('AUTOMATIC_EXACT_RETAINED_COMPLETE_GATE_SOURCE_REQUIRED')
    text = raw.decode()
    focus = {
        'actual_Native_cases=25': 'actual_Native_cases=13',
        'actual_business_cases=27': 'actual_business_cases=15',
        "counts={'PASS':25}": "counts={'PASS':13}",
        "qualification_scope='NATIVE25_AND_CURRENT_BROWSER2'":
            "qualification_scope='FRESH_SKU13_AND_CURRENT_BROWSER2'",
        "qualification_scope='CURRENT_PARENT_SKU_MONEY_AUTOMATIC_NATIVE25_BROWSER2_ONLY'":
            "qualification_scope='CURRENT_PARENT_SKU_MONEY_AUTOMATIC_CONTINUATION_BROWSER2'",
    } if focused else {}
    routes = tuple((before, focus.get(after, after), count) for before, after, count in ROUTES)
    for before, after, count in routes:
        if text.count(before) != count or after in text:
            raise ValueError('AUTOMATIC_EXACT_GATE_CASE_METADATA_ROUTE_REQUIRED')
        text = text.replace(before, after)
    recovered = text
    for before, after, _ in reversed(routes):
        recovered = recovered.replace(after, before)
    if recovered.encode() != raw:
        raise ValueError('AUTOMATIC_COMPLETE_RETAINED_GATE_NOT_RECOVERED')
    return text, dict(retained=RETAINED_PIN, metadata_expression_routes=sum(row[2] for row in routes),
                      retained_source_recovered_exactly=True, Auth_HTTP_and_race_counts_still_zero=True,
                      two_fresh_current_browser_originals_required=True,
                      complete_all5_recovery_and_worker_lifecycle_assertions_preserved=True, actual_ERP_cases=0)


def validator(*, focused=False):
    text, proof = derive(RETAINED.read_bytes(), focused=focused)
    code = runtime.report_io.function_code(text, str(RETAINED) + '::automatic-case-metadata', 'validate')
    namespace = dict(component=component, money_gate=SimpleNamespace(validate_preflight=validate_preflight), re=re,
                     MAIN=MAIN, NATIVE=NATIVE, PREFLIGHT=PREFLIGHT, SUPERVISION=SUPERVISION)
    return FunctionType(code, namespace, 'validate'), proof


def typed_reader():
    return load('automatic_final_exact_typed_original_reader', ROOT / 'scripts/current-s03-sku-s05-composite-qualification/parents.py')


def validate(p, docs, head, ids, *, focused=False):
    check, _ = validator(focused=focused)
    result = check(p, docs, head, ids)
    p.exact(docs[PREFLIGHT]['source'], docs[MAIN]['source_declaration']['complete_combined_sources'],
            'AUTOMATIC_PREFLIGHT_EXACT_CURRENT_COMBINED_SOURCE_GRAPH')
    part = docs[MAIN]['committed'][component.CASE]
    p.fields(part, dict(actual_browser_cases=2, actual_business_cases=15 if focused else 27, real_Auth_browser_claim=True),
             'AUTOMATIC_COMPONENT_ACTUAL_BROWSER2_AND_NATIVE25_COUNTS')
    result['current_browser2'] = browser_gate.validate(p, docs[BROWSER], part, head, docs[MAIN]['source_declaration'])
    return result


def catalogue_functions(p, rows):
    current = dict(rows)
    if not (economic_pool.ROUTES.keys() | {economic_pool.FUNCTION, CREDIT_GUARD}) <= current.keys():
        raise ValueError('SKU_FULL25_REVIEWED_FUNCTIONS_REQUIRED')
    p.exact(current[economic_pool.FUNCTION], economic_pool.helper_row(), 'SKU_FULL25_EXACT_ECONOMIC_POOL_HELPER')
    before = {signature: economic_pool.restore(signature, current[signature]) for signature in economic_pool.ROUTES}
    guard = current[CREDIT_GUARD]
    if type(guard) is not list or len(guard) != 19 or type(guard[0]) is not str:
        raise ValueError('SKU_FULL25_EXACT_DATABASE_LOCAL_CREDIT_SEAL_REQUIRED')
    literals = SEAL_LITERAL.findall(guard[0])
    if len(literals) != 1:
        raise ValueError('SKU_FULL25_EXACT_DATABASE_LOCAL_CREDIT_SEAL_REQUIRED')
    definition = SEAL_LITERAL.sub(" if actual_sha256 is distinct from '" + CREDIT_SEAL + "'then", guard[0])
    before[CREDIT_GUARD] = [definition, *guard[1:]]
    restored = [[signature, before.get(signature, row)] for signature, row in rows if signature != economic_pool.FUNCTION]
    normalized = runtime.continuation.catalogue_group_pin(restored)
    p.exact(normalized, BASELINE_FUNCTIONS, 'SKU_FULL25_ONLY_REVIEWED_ECONOMIC_POOL_FUNCTIONS_MAY_CHANGE')
    return dict(added=economic_pool.FUNCTION, replaced=sorted(economic_pool.ROUTES),
                normalized_predecessor=normalized, database_local_credit_seal=literals[0])


def validate_catalogue(p, raw, capture, head, run_id, scope):
    readers = {name: dict(bytes=size, sha256=digest) for name, (size, digest) in catalogue.SOURCE_PINS.items()}
    p.fields(capture, dict(status='ACTUAL_FULL25_SKU_CATALOGUE_OBSERVED', head=head, run_id=run_id, attempt=1,
        original=dict(name=catalogue.ORIGINAL, **admission.pin(raw)), readers=readers, actual_ERP_case_credit=0,
        complete_input_review=False, production_go=False), 'SKU_FULL25_SAME_ACTUAL_CATALOGUE_OWNER')
    value = p.strict(raw)
    _, _, groups = catalogue.exact_readers()
    if type(value) is not dict:
        raise ValueError('SKU_FULL25_EXACT_CATALOGUE_OBJECT_REQUIRED')
    p.exact(set(value), groups, 'SKU_FULL25_EXACT_GROUPS')
    for name, rows in value.items():
        if type(rows) is not list or any(type(row) is not list or len(row) != 2 or type(row[0]) is not str for row in rows):
            raise ValueError('SKU_FULL25_EXACT_KEYED_CATALOGUE_ROWS_REQUIRED:' + name)
        keys = [row[0] for row in rows]
        p.exact(keys, sorted(set(keys)), 'SKU_FULL25_ORDERED_UNIQUE_CATALOGUE_KEYS:' + name)
    if any(not value[name] for name in ('functions', 'relations', 'roles', 'operators', 'casts', 'languages')):
        raise ValueError('SKU_FULL25_CURRENT_COMBINED_CATALOGUE_REQUIRED')
    fingerprint = capture['fingerprint']
    p.fields(fingerprint, dict(contract='cp7.global-catalogue-fingerprint.v1', groups=25,
        counts={name: len(rows) for name, rows in value.items()}), 'SKU_FULL25_EXACT_CAPTURE_FINGERPRINT')
    digest = fingerprint.get('sha256')
    if type(digest) is not str or re.fullmatch('[a-f0-9]{64}', digest) is None:
        raise ValueError('SKU_FULL25_EXACT_POSTGRES_FINGERPRINT_REQUIRED')
    functions = catalogue_functions(p, value['functions'])
    historical = runtime.continuation.catalogue_comparison(value, scope)
    return dict(original=capture['original'], fingerprint=fingerprint, readers=readers,
        current_group_pins=historical['actual'], economic_pool_functions=functions,
        historical_nonfunction_differences=[name for name in historical['differing_groups'] if name != 'functions'])


def gate(directory, head):
    parent_raw, money_raw, plan_raw, receipt = runtime.actual_inputs()
    p = typed_reader()
    ids = json.loads(plan_raw)['case_ids']
    reference = runtime.assembly.prepared_sources()[0]
    retained_ids = json.loads((ROOT / 'scripts/current-sku-money-composite-preparation/SOURCE_REFERENCE.json').read_bytes())['native_case_ids']
    suite = load('automatic_final_exact_ordered_source_suite', HERE / 'native_suite.py')
    p.exact(ids, retained_ids + list(suite.native.IDS) + list(suite.invoices.IDS), 'AUTOMATIC_EXACT_ORDERED_TWENTY_FIVE_CURRENT_CASES')
    if len(ids) != 25 or len(set(ids)) != 25:
        raise ValueError('AUTOMATIC_COMPLETE_DISTINCT_NATIVE25_PLAN_REQUIRED')
    names = (MAIN, NATIVE, PREFLIGHT, BROWSER, 'T3_PACKAGE_INSTALL.json', 'T3_BACKUP_RESTORE_DRILL.json', SUPERVISION)
    raw = {}
    for name in names:
        path = directory / name
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise ValueError('AUTOMATIC_ORIGINAL_PACKET_SYMLINK_REFUSED')
        raw[name] = path.read_bytes()
    docs = {name: p.strict(value) for name, value in raw.items()}
    continuation = runtime.continuation
    scope = continuation.admitted(plan_raw)
    result = validate(p, docs, head, ids)
    p.exact({case: row['caller_timezone'] for case, row in docs[NATIVE]['cases'].items() if 'caller_timezone' in row},
            dict.fromkeys(scope['non_po_affected_case_ids'], continuation.CALLER_TIMEZONE),
            'SKU_NON_PO_EXACT_EIGHT_ACTUAL_WIB_NATIVE_CASES_REQUIRED')
    refs = docs[MAIN]['committed'][component.CASE]['strict_group_originals']
    originals = [row for row in refs if row['name'] == NATIVE]
    if len(originals) != 1:
        raise ValueError('AUTOMATIC_ONE_FIRST_NATIVE_ORIGINAL_REQUIRED')
    p.exact({key: originals[0][key] for key in ('bytes', 'sha256')}, admission.pin(raw[NATIVE]), 'AUTOMATIC_FIRST_NATIVE_ORIGINAL_EXACT_BYTES')
    part = docs[MAIN]['committed'][component.CASE]
    result['current_browser2'] = browser_gate.gate(p, directory, docs[BROWSER], part, head, docs[MAIN]['source_declaration'])
    p.exact(part['current_browser_complete_evidence_gate'], result['current_browser2'],
            'AUTOMATIC_BROWSER_RECHECK_EQUALS_COMPLETE_FIRST_RUNTIME_GATE')
    raw_catalogue = browser_gate.asset(directory, catalogue.ORIGINAL)
    result['global_parent_catalogue'] = validate_catalogue(p, raw_catalogue, part['Global_parent_catalogue'],
                                                          head, result['run_id'], scope)
    runtime.frozen_afui()
    fence = runtime.load('automatic_final_original_import_DB_fence',
        runtime.FROZEN_AFUI / 'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
    with fence.fenced_source_read(), runtime.inherited_scope():
        engine = runtime.runtime()
        with engine.inherited_admission.parent_scope():
            sources = engine.admitted()
    p.exact(docs[MAIN]['source_declaration'], sources, 'AUTOMATIC_COMPLETE_NATURAL_SOURCE_GRAPH_NOT_PROJECTED')
    return dict(status='CURRENT_MANDOR_PARENT_MONEY_AUTOMATIC_NATIVE25_BROWSER2_AND_ALL5_PASS', head=head, **result,
                accepted_sources=receipt, parent_root=admission.pin(parent_raw), money_source_preflight=admission.pin(money_raw),
                automatic_source=reference['automatic_source'], complete_native_plan=admission.pin(plan_raw),
                originals={name: admission.pin(value) for name, value in raw.items()},
                concurrent_and_current_permission_Auth_HTTP_followups_pending=True, full_combined_final_qualification=False)


if __name__ == '__main__':
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    result = gate(ROOT / 'cp6-proof/t3', head)
    path = ROOT / 'cp6-proof/t3/SKU_CURRENT_PARENT_MONEY_AUTOMATIC_FINAL_GATE.json'
    with path.open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))
