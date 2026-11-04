"""Exact Native25 Originals and whole restoration; no Auth/full-ERP promotion."""
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
ROUTES = (
    ('actual_Native_cases=19', 'actual_Native_cases=25', 3),
    ('actual_business_cases=19', 'actual_business_cases=25', 1),
    ("counts={'PASS':19}", "counts={'PASS':25}", 1),
    ("qualification_scope='CURRENT_PARENT_SKU_MONEY_NATIVE19_ONLY'",
     "qualification_scope='CURRENT_PARENT_SKU_MONEY_AUTOMATIC_NATIVE25_ONLY'", 1),
)


def validate_preflight(p, part, value):
    p.exact(part['native_prerequisites'], value, 'AUTOMATIC_COMPLETE_FIRST_PREFLIGHT_ORIGINAL')
    p.fields(value, dict(status='PASS', errors=[], all_prerequisites_checked_before_first_case=True,
                        all22_rows_and_all_sequences_unchanged=True, actual_ERP_cases=0, production_go=False),
             'AUTOMATIC_BATCH_PREFLIGHT_AND_UNCHANGED_CURRENT_BOUNDARY')
    # Validate the exact nested retained Original, without relabeling it.
    money_gate.validate_preflight(p, dict(part, native_prerequisites=value['retained_money19']), value['retained_money19'])
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
        p.exact(actor['permissions'], {key: True for key in prerequisites.ACTOR_PERMISSIONS[name]}, 'AUTOMATIC_ALL_ACTUAL_ACTOR_PERMISSIONS:' + name)
        p.exact(actor['functions'], {key: True for key in signatures}, 'AUTOMATIC_ALL_ACTUAL_ACTOR_EXECUTE_PRIVILEGES:' + name)
    p.exact(value['natural_callers'], dict(
        upstream=dict(status='NATIVE_AUTOMATIC_CALLER_APIS_BOUND_NOT_EXECUTED', calls=6,
                      original_AFUI_physical_constructor=True, actual_ERP_cases=0),
        invoices=dict(original_invoice_helper_shapes=4, actual_ERP_cases=0)), 'AUTOMATIC_COMPLETE_NATURAL_CALLER_SHAPES')


def derive(raw):
    if admission.pin(raw) != RETAINED_PIN:
        raise ValueError('AUTOMATIC_EXACT_RETAINED_COMPLETE_GATE_SOURCE_REQUIRED')
    text = raw.decode()
    for before, after, count in ROUTES:
        if text.count(before) != count or after in text:
            raise ValueError('AUTOMATIC_EXACT_GATE_CASE_METADATA_ROUTE_REQUIRED')
        text = text.replace(before, after)
    recovered = text
    for before, after, _ in reversed(ROUTES):
        recovered = recovered.replace(after, before)
    if recovered.encode() != raw:
        raise ValueError('AUTOMATIC_COMPLETE_RETAINED_GATE_NOT_RECOVERED')
    return text, dict(retained=RETAINED_PIN, metadata_expression_routes=sum(row[2] for row in ROUTES),
                      retained_source_recovered_exactly=True, Auth_race_browser_counts_still_zero=True,
                      complete_all5_recovery_and_worker_lifecycle_assertions_preserved=True, actual_ERP_cases=0)


def validator():
    text, proof = derive(RETAINED.read_bytes())
    code = runtime.report_io.function_code(text, str(RETAINED) + '::automatic-case-metadata', 'validate')
    namespace = dict(component=component, money_gate=SimpleNamespace(validate_preflight=validate_preflight), re=re,
                     MAIN=MAIN, NATIVE=NATIVE, PREFLIGHT=PREFLIGHT, SUPERVISION=SUPERVISION)
    return FunctionType(code, namespace, 'validate'), proof


def typed_reader():
    return load('automatic_final_exact_typed_original_reader', ROOT / 'scripts/current-s03-sku-s05-composite-qualification/parents.py')


def validate(p, docs, head, ids):
    check, _ = validator()
    result = check(p, docs, head, ids)
    p.exact(docs[PREFLIGHT]['source'], docs[MAIN]['source_declaration']['complete_combined_sources'],
            'AUTOMATIC_PREFLIGHT_EXACT_CURRENT_COMBINED_SOURCE_GRAPH')
    return result


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
    names = (MAIN, NATIVE, PREFLIGHT, 'T3_PACKAGE_INSTALL.json', 'T3_BACKUP_RESTORE_DRILL.json', SUPERVISION)
    raw = {}
    for name in names:
        path = directory / name
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise ValueError('AUTOMATIC_ORIGINAL_PACKET_SYMLINK_REFUSED')
        raw[name] = path.read_bytes()
    docs = {name: p.strict(value) for name, value in raw.items()}
    result = validate(p, docs, head, ids)
    refs = docs[MAIN]['committed'][component.CASE]['strict_group_originals']
    originals = [row for row in refs if row['name'] == NATIVE]
    if len(originals) != 1:
        raise ValueError('AUTOMATIC_ONE_FIRST_NATIVE_ORIGINAL_REQUIRED')
    p.exact({key: originals[0][key] for key in ('bytes', 'sha256')}, admission.pin(raw[NATIVE]), 'AUTOMATIC_FIRST_NATIVE_ORIGINAL_EXACT_BYTES')
    fence = runtime.load('automatic_final_original_import_DB_fence',
        runtime.FROZEN_AFUI / 'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
    with fence.fenced_source_read(), runtime.inherited_scope():
        engine = runtime.runtime()
        with engine.inherited_admission.parent_scope():
            sources = engine.admitted()
    p.exact(docs[MAIN]['source_declaration'], sources, 'AUTOMATIC_COMPLETE_NATURAL_SOURCE_GRAPH_NOT_PROJECTED')
    return dict(status='CURRENT_MANDOR_PARENT_MONEY_AUTOMATIC_NATIVE25_AND_ALL5_PASS', head=head, **result,
                accepted_sources=receipt, parent_root=admission.pin(parent_raw), money_source_preflight=admission.pin(money_raw),
                automatic_source=reference['automatic_source'], complete_native_plan=admission.pin(plan_raw),
                originals={name: admission.pin(value) for name, value in raw.items()},
                concurrent_current_permission_Auth_browser_followups_pending=True, full_combined_final_qualification=False)


if __name__ == '__main__':
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    result = gate(ROOT / 'cp6-proof/t3', head)
    path = ROOT / 'cp6-proof/t3/SKU_CURRENT_PARENT_MONEY_AUTOMATIC_FINAL_GATE.json'
    with path.open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))
