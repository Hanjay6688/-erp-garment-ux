"""Read-only root intake of actual D1/E/SKU catalogues; no business execution."""
from collections import Counter
from hashlib import sha256
from types import ModuleType
import argparse
import csv
import json
import re
import sys

from intake_common import (GitBytes, digest, exact, fields, json_bytes, original_zip,
                           pin, require, save, script_pins)
from intake_s05 import CONTRACT_DIRS, FILESET_DIRS

HEAD = 'bce07059f7a351372e40bb7c2e4453876320a2e8'
TREE = 'e2e6c38a63f7fee3aa27922c9379b79d180a2edf'
BASE = 'c397409a470c8c3d5f4963bbbdd7b676b1275af7'
IMPORTED = 'e299aa25fd96a422d71b16a2eb024011b3a6fa69'
NS = 'scripts/current-de-sku-parent-catalogue-qualification/'
CASE = 'D1_E_SKU_ACTUAL_PARENT_CATALOGUE_RAW_ACL_SOURCE_ONLY'
MAIN = 'CP7_D1_E_SKU_PARENT_CATALOGUE.json'
GATE = 'DE_SKU_PARENT_CATALOGUE_GATE.json'
PACKAGE = 'T3_PACKAGE_INSTALL.json'
FILES = 'T3_PACKAGE_FILES_INSTALL.json'
RESTORE = 'T3_BACKUP_RESTORE_DRILL.json'
ZIP_PIN = dict(bytes=16764082, sha256='74335122eb5ce2e8457e7183c89eab34e6f7e889bcfd6a5c79a5f47a2d596644')
RAW_PINS = {
    MAIN: dict(bytes=151798168, sha256='757cea6bd13480bcea6f4832a4e311795b7105cbab516a8a9e8aba6e5c3722a9'),
    GATE: dict(bytes=712, sha256='832f398b554ac0cc970a9a0e18d8a33d7ce2b69e6dc3b2956f1892c90641cd6b'),
    PACKAGE: dict(bytes=360438, sha256='f8381fa740414ef667d2b395e48228ebec26736d6560999ba58a6c519a291175'),
    FILES: dict(bytes=1806, sha256='14007d43dd9b8e1acfa2b91e35d59047f553b248e2fc06e8362e8ad813003ba7'),
    RESTORE: dict(bytes=1470, sha256='c6c3d0c742a4868899d3c5822463bf2f07c9abd4d97a92c845b67dabd4d3825d'),
}
HOOKS = (
    'cp7_credit_correction_de.quote_v1(jsonb)',
    'cp7_credit_correction_de.prepare_v1(jsonb,uuid,text,jsonb)',
    'cp7_credit_correction_de.finish_v1(jsonb)',
    'cp7_credit_note_carry_de.basis_v1(uuid)',
    'cp7_credit_note_carry_de.prepare_v1(jsonb,uuid,text,uuid,jsonb)',
    'cp7_credit_note_carry_de.finish_v1(jsonb)',
    'cp7_credit.source_request_enter_v1(text,jsonb,uuid,text)',
    'cp7_credit.source_request_finish_v1(uuid)',
)
PRIVILEGES = ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER')
ZERO = dict(actual_business_cases=0, actual_Native_cases=0, actual_Auth_HTTP_cases=0, actual_browser_cases=0)
NO_GO = dict(production_go=False, independent_acceptance=False)


def strict_stream(stream):
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, 'ROOT_DE_SKU_DUPLICATE_JSON_KEY')
            result[key] = value
        return result

    def constant(_):
        raise ValueError('ROOT_DE_SKU_NONFINITE_JSON_VALUE')

    return json.load(stream, object_pairs_hook=pairs, parse_constant=constant)


def read_originals(archive):
    """Hash zip members in chunks; keep no second 152MB raw report copy."""
    docs = {}
    for name, expected in RAW_PINS.items():
        total = 0; hashed = sha256()
        with archive.open(name) as stream:
            while chunk := stream.read(1024 * 1024):
                total += len(chunk); hashed.update(chunk)
        exact(dict(bytes=total, sha256=hashed.hexdigest()), expected, 'ROOT_DE_SKU_RAW_PIN:' + name)
        with archive.open(name) as stream:
            docs[name] = strict_stream(stream)
    return docs


def pure_module(g, name, path):
    module = ModuleType(name)
    module.__file__ = str(g.root / path)
    exec(compile(g.read(path), module.__file__, 'exec'), module.__dict__)
    return module


def source(g, actual):
    raw = g.read(NS + 'SOURCE.json'); cfg = json_bytes(raw)
    fields(cfg, dict(base=BASE, exact_public_import_head=IMPORTED,
        business_runtime_entry=None, actual_business_cases=0, actual_Native_cases=0, **NO_GO), 'ROOT_DE_SKU_SOURCE_SCOPE')
    exact(len(cfg['files']), 41, 'ROOT_DE_SKU_SOURCE41')
    fields(actual, dict(status='EXACT_C397_PLUS_PUBLIC_PHASE2_D1_E_SKU_CATALOGUE_SUCCESSOR',
        unchanged_parent_files=13834, exact_public_imports=22, source_files=41,
        old_source_manifests_resealed=False, old_catalogue_projections=False,
        actual_business_cases=0, actual_Native_cases=0, business_runtime_entry=None, **NO_GO), 'ROOT_DE_SKU_ACTUAL_ADMISSION')
    declaration = json_bytes(g.read(NS + 'IMPORTED_SOURCE.json'))
    fields(declaration, dict(base=BASE, actual_command_runtime_opened=False), 'ROOT_DE_SKU_IMPORT_SCOPE')
    imports = declaration['records']; exact(len(imports), 22, 'ROOT_DE_SKU_PUBLIC_IMPORT22')
    for name, expected in cfg['files'].items():
        g.verify_pin(name, expected)
    for name, expected in imports.items():
        exact(expected['source_head'], IMPORTED, 'ROOT_DE_SKU_IMPORT_PUBLIC_HEAD')
        raw_import = g.verify_pin(name, {key: expected[key] for key in ('bytes', 'sha256')})
        exact(raw_import, g.read(expected.get('source_path', name), IMPORTED), 'ROOT_DE_SKU_EXACT_IMPORTED_GIT_BYTES')
    baseline = g.entries(BASE); preserved = 0; replacements = []
    for name, entry in baseline.items():
        if name in imports:
            exact(sha256(g.read(name, BASE)).hexdigest(), imports[name]['previous_sha256'], 'ROOT_DE_SKU_IMPORT_PREIMAGE')
            replacements.append(name)
        else:
            exact(g.tree.get(name), entry, 'ROOT_DE_SKU_PARENT_BLOB_OR_MODE_CHANGED:' + name); preserved += 1
    exact(preserved, 13834, 'ROOT_DE_SKU_IMMUTABLE_PARENT_COUNT')
    exact(replacements, ['scripts/cp7_sku_pair_conversion/composition.py'], 'ROOT_DE_SKU_ONLY_EXISTING_PRODUCT_PARENT_IMPORT_CHANGED')
    allowed = set(cfg['files']) | {NS + 'SOURCE.json'}
    changed = {name for name in set(g.tree) | set(baseline) if g.tree.get(name) != baseline.get(name)}
    exact(changed, allowed, 'ROOT_DE_SKU_EXACT_DECLARED_SOURCE_DELTA')
    stage = actual['actual_stage_sources']
    fields(stage, dict(contract='cp7.de-sku.parent-catalogue-only.v1', manifest_sha256=sha256(raw).hexdigest(),
        business_runtime_entry=None, qualification_only=True, **NO_GO), 'ROOT_DE_SKU_ACTUAL_STAGE_BINDING')
    exact(stage['files'], {name: expected['sha256'] for name, expected in cfg['files'].items()}, 'ROOT_DE_SKU_STAGE_FILE_PINS')
    deriver = pure_module(g, 'root_exact_de_sku_deriver', NS + 'derive.py')
    _, proof = deriver.derive(g.read(deriver.OLD))
    exact(proof, cfg['complete_engine_derivation'], 'ROOT_DE_SKU_REVERSIBLE_ENGINE_DERIVATION')
    fields(proof, dict(counted_changes=13, original_engine_bytes_preserved=True,
        all_install_preuse_reinstall_backup_roles_CP6_advisor_Auth_package_checks_retained=True,
        original_business_case_requirement_replaced_by_explicit_catalogue_only_group=True,
        no_used_business_witness_claim=True, actual_Native_cases=0), 'ROOT_DE_SKU_HONEST_CATALOGUE_ENGINE')
    # Exact producer paths bind relative names. No matching-hash search is used.
    routes = [
        ('scripts/cp7_sku_pair_conversion/composition.py', 'from cp7_credit_correction_de import e_composition as vendor_parent'),
        ('scripts/cp7_credit_correction_de/e_composition.py', 'from . import composition as predecessor'),
        ('scripts/cp7_credit_correction_de/composition.py', 'from cp7_vendor_receivable import composition as predecessor'),
        ('scripts/cp7_vendor_receivable/composition.py', 'scripts/current-factory-initial-stage/composition.py'),
        ('scripts/current-factory-initial-stage/composition.py', 'scripts/current-finance-factory-progress-followup-qualification/composition.py'),
    ]
    for path, anchor in routes:
        require(anchor in g.read(path).decode(), 'ROOT_DE_SKU_EXACT_PRODUCER_ROUTE_REQUIRED:' + path)
    contracts = dict(CONTRACT_DIRS, **{'cp7.credit-correction-de.v1': 'cp7_credit_correction_de',
                                    'cp7.note-credit-carry.v1': 'cp7_credit_correction_de'})
    bound = set(); occurrences = 0; maps = 0

    def walk(value):
        nonlocal occurrences, maps
        if type(value) is dict:
            if 'files' in value and type(value['files']) is dict:
                files = value['files']; maps += 1
                if all(name.startswith(('scripts/', 'src/', 'docs/', 'tests/', '.github/', 'supabase/')) for name in files):
                    prefix = ''
                else:
                    directory = contracts.get(value.get('contract'))
                    if directory is None:
                        require(value.get('contract') is None, 'ROOT_DE_SKU_UNKNOWN_RELATIVE_SOURCE_CONTRACT')
                        directory = FILESET_DIRS.get(tuple(files))
                    require(directory is not None, 'ROOT_DE_SKU_UNBOUND_RELATIVE_SOURCE')
                    prefix = 'scripts/' + directory + '/'
                for name, expected in files.items():
                    path = prefix + name; g.verify_pin(path, expected)
                    bound.add((path, sha256(g.read(path)).hexdigest())); occurrences += 1
            for value in value.values():
                walk(value)
        elif type(value) is list:
            for value in value:
                walk(value)

    walk(stage)
    exact((maps, occurrences), (68, 330), 'ROOT_DE_SKU_ALL_DECLARED_FILE_MAPS_REQUIRED')
    return dict(own_manifest=pin(raw), source_files=41, exact_public_imports=22,
        preserved_parent_files_and_modes=preserved, only_existing_product_change=replacements,
        declared_delta_paths=len(changed), complete_reversible_engine_changes=13,
        file_map_occurrences=maps, file_pin_occurrences=occurrences, unique_bound_path_digest_pairs=len(bound),
        exact_namespace_binding=True, matching_hash_in_other_namespace_accepted=False,
        historical_manifests_resealed=False, actual_business_runtime_entry=None)


def pg_array(raw):
    if raw is None:
        return None
    require(type(raw) is str and raw.startswith('{') and raw.endswith('}'), 'ROOT_DE_SKU_RAW_ACL_ARRAY_REQUIRED')
    if raw == '{}':
        return []
    return next(csv.reader([raw[1:-1]], delimiter=',', quotechar='"', escapechar='\\'))


def acl_rows(raw, owner, schema=False):
    codes = dict(a='INSERT', r='SELECT', w='UPDATE', d='DELETE', D='TRUNCATE', x='REFERENCES', t='TRIGGER',
                 m='MAINTAIN', U='USAGE', C='CREATE')
    items = pg_array(raw)
    if items is None:
        return [[owner, owner, right, False] for right in (('CREATE', 'USAGE') if schema else PRIVILEGES + ('MAINTAIN',))]
    rows = []
    for item in items:
        match = re.fullmatch(r'([A-Za-z_][A-Za-z_0-9]*|)=([A-Za-z*]*)/([A-Za-z_][A-Za-z_0-9]*)', item)
        require(match is not None, 'ROOT_DE_SKU_UNSUPPORTED_RAW_ACL_ITEM')
        who, rights, grantor = match.groups(); who = who or 'PUBLIC'; index = 0
        while index < len(rights):
            code = rights[index]; require(code in codes, 'ROOT_DE_SKU_UNDECLARED_ACL_PRIVILEGE')
            grantable = index + 1 < len(rights) and rights[index + 1] == '*'
            rows.append([who, grantor, codes[code], grantable]); index += 2 if grantable else 1
    return rows


def catalogue(case, cc, inventory):
    expected = sorted(set(inventory['actual_common51']) | {'cp7_credit_correction_de.work_v1',
        'cp7_credit_correction_de.posting_v1', 'cp7_credit_note_carry_de.work_v1', 'cp7_sku_conversion.execution_v1'})
    exact(len(inventory['actual_common51']), 51, 'ROOT_DE_SKU_BASE_CONTEXT51')
    context = case['actual_context55']; full = case['actual_composite_catalogue']
    exact(context['names'], expected, 'ROOT_DE_SKU_EXACT_SOURCE_DERIVED_CONTEXT55')
    exact(len(expected), 55, 'ROOT_DE_SKU_EXACT_CONTEXT55_COUNT')
    fields(context, dict(schema_exclusions=[], runtime_entry=None, actual_Native_credit=0,
        active_row_authority_decided=False, all_transaction_tables_are_ephemeral=False, production_go=False),
        'ROOT_DE_SKU_CONTEXT_PROFILE_IS_NOT_RUNTIME_AUTHORITY')
    cc.validate(full, context)
    layers = case['actual_layer_catalogues']; exact(set(layers), {'D1', 'E', 'SKU'}, 'ROOT_DE_SKU_THREE_LAYER_NAMES')
    for value in [full, *layers.values()]:
        exact(set(value), set(cc.ALL22), 'ROOT_DE_SKU_ALL22_REQUIRED')
        require(all(type(group) is dict for group in value.values()), 'ROOT_DE_SKU_TYPED_ALL22_GROUPS')
    exact(layers['SKU'], full, 'ROOT_DE_SKU_TOP_LAYER_EQUALS_ACTUAL_COMPOSITE')
    exact(case['read_before'], case['read_after'], 'ROOT_DE_SKU_FULL_READ_BOUNDARY_CHANGED')
    exact(case['read_before']['catalog'], full, 'ROOT_DE_SKU_EXACT_EMBEDDED_FULL_CATALOGUE')
    data = case['read_before']['data_and_sequences']
    tables = {name for name, row in full['relations'].items() if row[1] in ('r', 'p', 'm')}
    sequences = set(full['sequences'])
    exact(set(data), tables | {'sequence:' + name for name in sequences}, 'ROOT_DE_SKU_ALL_ROWS_AND_EVERY_SEQUENCE_CENSUS')
    for name, row in data.items():
        require(type(row) is list and len(row) == 2, 'ROOT_DE_SKU_DATA_CENSUS_ROW_ABI')
        if name.startswith('sequence:'):
            require(type(row[0]) is str and re.fullmatch(r'-?\d+', row[0]) and type(row[1]) is bool,
                    'ROOT_DE_SKU_SEQUENCE_STATE_ABI')
        else:
            require(type(row[0]) is int and row[0] >= 0 and type(row[1]) is str
                    and re.fullmatch('[0-9a-f]{64}', row[1]), 'ROOT_DE_SKU_COMPLETE_ROW_COUNT_HASH_ABI')
    hooks = case['current_eight_hook_rows']; exact(set(hooks), set(HOOKS), 'ROOT_DE_SKU_EXACT_EIGHT_CURRENT_HOOKS')
    for name, row in hooks.items():
        require(type(row) is list and len(row) == 19, 'ROOT_DE_SKU_EXACT_FUNCTION19_ABI')
        exact(row, full['functions'][name], 'ROOT_DE_SKU_HOOK_MUST_EQUAL_CURRENT_ACTUAL_FUNCTION')
    raw = case['actual_raw_context_authority']
    exact(set(raw), {'schemas', 'relations', 'columns', 'effective_role_table_privileges'}, 'ROOT_DE_SKU_RAW_AUTHORITY_GROUPS')
    schema_names = sorted({name.split('.')[0] for name in expected})
    exact([row[0] for row in raw['schemas']], schema_names, 'ROOT_DE_SKU_ALL_RAW_SCHEMA_ACLS')
    for name, owner, acl in raw['schemas']:
        exact(owner, full['schemas'][name][0], 'ROOT_DE_SKU_RAW_SCHEMA_OWNER')
        exact(sorted(acl_rows(acl, owner, True)), sorted(full['schemas'][name][1]), 'ROOT_DE_SKU_RAW_SCHEMA_ACL_EXACT')
    exact([row[0] for row in raw['relations']], expected, 'ROOT_DE_SKU_ALL_RAW_RELATION_ACLS')
    for name, owner, kind, persistence, rls, forced, acl in raw['relations']:
        exact([owner, kind, persistence, rls, forced], full['relations'][name][:5], 'ROOT_DE_SKU_RAW_RELATION_AUTHORITY')
        exact(sorted(acl_rows(acl, owner)), sorted(full['relations'][name][12]), 'ROOT_DE_SKU_RAW_RELATION_ACL_EXACT')
    columns = context['catalog']['columns']; seen = set(); positions = Counter(); attnums = set()
    for table, number, name, acl in raw['columns']:
        require(table in expected and type(number) is int and number > 0, 'ROOT_DE_SKU_RAW_COLUMN_IDENTITY')
        key = table + ':' + name
        require(key not in seen and (table, number) not in attnums, 'ROOT_DE_SKU_DUPLICATE_RAW_COLUMN')
        seen.add(key); attnums.add((table, number)); positions[table] += 1
        exact(columns[key][0:2], [name, positions[table]], 'ROOT_DE_SKU_PORTABLE_COLUMN_IDENTITY')
        exact(pg_array(acl), columns[key][12], 'ROOT_DE_SKU_RAW_COLUMN_ACL_EXACT')
    exact(seen, set(columns), 'ROOT_DE_SKU_COMPLETE_RAW_COLUMN_CENSUS')
    privileges = raw['effective_role_table_privileges']
    identities = {(role, table, right) for role in full['roles'] for table in expected for right in PRIVILEGES}
    exact(len(privileges), len(identities), 'ROOT_DE_SKU_COMPLETE_EFFECTIVE_PRIVILEGE_COUNT')
    exact({tuple(row[:3]) for row in privileges}, identities, 'ROOT_DE_SKU_COMPLETE_ROLE_TABLE_PRIVILEGE_IDENTITIES')
    require(all(type(row) is list and len(row) == 4 and type(row[3]) is bool for row in privileges),
            'ROOT_DE_SKU_EFFECTIVE_PRIVILEGES_MUST_BE_OBSERVED_BOOLEANS')
    exact((len(schema_names), len(columns), len(full['roles']), len(privileges)), (25, 543, 89, 34265),
          'ROOT_DE_SKU_ACTUAL_RAW_AUTHORITY_COUNTS')
    return dict(context_names=expected, portable_context_sha256=cc.digest(context),
        complete_layer_catalogue_sha256={name: cc.digest(value) for name, value in layers.items()},
        complete_read_boundary_sha256=cc.digest(case['read_before']), all_catalogue_groups=22,
        complete_tables=len(tables), complete_sequences=len(sequences), raw_schemas=25, raw_relations=55,
        raw_columns=543, effective_roles=89, effective_role_table_privilege_rows=34265,
        raw_ACL_meanings_equal_portable_catalogue=True,
        hook_rows={name: dict(fields=19, row_sha256=cc.digest(row), definition_sha256=sha256(row[0].encode()).hexdigest())
                   for name, row in hooks.items()}, active_row_or_phase_authority_qualified=False)


def checked(g, docs):
    report, package, files, restore = (docs[name] for name in (MAIN, PACKAGE, FILES, RESTORE))
    fields(report, dict(status='PASS', label='CP7_D1_E_SKU_PARENT_CATALOGUE', qualification_commit=HEAD,
        expected_case_count=1, observed_case_count=1, required_case_ids=[CASE], required_case_ids_pass=True,
        actual_catalogue_qualification_groups=1, actual_two_session_races=0, used_guard_business_witness_executed=False,
        full_final_composite_qualified=False, preuse_catalogue_qualified=True, cp6_restored=True,
        baseline_full22_all_rows_all_sequences_equal=True, baseline_advisors_equal=True, advisor_gate=True,
        restore_raw_public_equal=True, scheduler_quiet_before_baseline_restore=True, formal_CP7C_started=False,
        default_adopted=False, real_Auth_HTTP_qualified=False, **ZERO, **NO_GO), 'ROOT_DE_SKU_EXACT_CATALOGUE_ONLY_REPORT')
    require(not report.get('error') and not report.get('restore_error'), 'ROOT_DE_SKU_FIRST_FAILURE_MUST_NOT_BE_HIDDEN')
    exact(set(report['committed']), {CASE}, 'ROOT_DE_SKU_SINGLE_EXACT_GROUP')
    exact(report['native'], {}, 'ROOT_DE_SKU_NO_NATIVE_RESULTS')
    case = report['committed'][CASE]
    fields(case, dict(status='PASS', classification='ACTUAL_D1_E_SKU_INSTALL_PREUSE_CATALOGUE_ONLY',
        read_complete_noeffect=True, preuse_catalogue_qualified=True, used_guard_business_witness_executed=False,
        global_bridge_installed=False, S03_S05_installed=False, **ZERO, **NO_GO), 'ROOT_DE_SKU_ACTUAL_CATALOGUE_GROUP')
    fields(case['verification'], dict(status='EXACT_D1_E_SKU_INSTALLED_CATALOGUE_ONLY',
        older_verifiers_called_on_projected_catalogue=False, business_commands_executed=0,
        business_runtime_entry=None, **NO_GO), 'ROOT_DE_SKU_ACTUAL_TOP_VERIFIER')
    for name, status in [('D1', 'CREDIT_DE_EXACT_SOURCE_AND_ALL22'), ('E', 'CREDIT_E1_EXACT_SOURCE_AND_ALL22'),
                         ('SKU', 'SKU_PAIR_CONVERSION_EXACT_SOURCE_AND_ALL22')]:
        fields(case['actual_layer_proofs'][name], dict(status=status, actual_parent_verified_before_delta=True,
            projected_catalog=False, formal_acceptance_unchanged=True, **NO_GO), 'ROOT_DE_SKU_ACTUAL_LAYER:' + name)
    removal = report['focused_preuse_removal']
    fields(removal, dict(status='EXACT_D1_E_SKU_PREUSE_DELTA_RESTORE', used_guard_before_DDL=True,
        used_guard_business_witness_executed=False, actual_business_cases=0, production_go=False), 'ROOT_DE_SKU_PREUSE_REMOVAL')
    exact(set(removal['removed']), {'SKU', 'E', 'D1'}, 'ROOT_DE_SKU_ALL_THREE_REMOVED')
    for name, prefix in [('D1', 'CREDIT_DE'), ('E', 'CREDIT_E1'), ('SKU', 'SKU_PAIR_CONVERSION')]:
        fields(removal['removed'][name], dict(status=prefix + '_EXACT_PREUSE_DELTA_RESTORE', used_guard_before_DDL=True),
               'ROOT_DE_SKU_LAYER_REMOVAL:' + name)
    fields(report['baseline_restore'], dict(exit=1, error_count=19, unexplained=[], only_pg_cron_errors=True,
        database_owner_acl_and_settings_preserved=True), 'ROOT_DE_SKU_COMPLETE_BASELINE_RESTORE')
    fields(report['baseline_role_cleanup'], dict(baseline_roles_exact=True), 'ROOT_DE_SKU_COMPLETE_ROLE_RESTORE')
    exact(report['restore_components'], dict(erp_platform_auth_schema_acl=True,
        all_public_catalog_members_and_row_hashes=True, erp_public_auth_function_definitions_owners_acls=True),
        'ROOT_DE_SKU_COMPLETE_RESTORE_COMPONENTS')
    fields(package, dict(status='ALL_STAGES_INSTALLED', mode='install', primary_unchanged=True,
        auth_users_before=0, auth_users_after=0, production_go=False, release_evidence=False,
        gate={key: True for key in ('installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')}),
        'ROOT_DE_SKU_ALL_FIVE_PACKAGE_GATES_AND_AUTH')
    fields(package['run_identity'], dict(tool_head=HEAD, github_sha=HEAD, run_id='41032035497', run_attempt='1',
        workflow='CP7 A D1 E SKU actual parent catalogue and preuse restoration', job='p21', event='push',
        production_go=False, release_evidence=False, mode='install'), 'ROOT_DE_SKU_ACTUAL_PACKAGE_IDENTITY')
    fields(package['writer_runtime'], dict(status='PASS', **NO_GO), 'ROOT_DE_SKU_PACKAGE_RUNTIME')
    fields(files, dict(status='ALL_FILES_INSTALLED', production_go=False, release_evidence=False), 'ROOT_DE_SKU_PACKAGE_FILES')
    keys = ['A' + chr(n) for n in range(ord('C'), ord('Z') + 1)] + ['B' + chr(n) for n in range(ord('A'), ord('F') + 1)]
    exact(files['files'], [dict(key=key, status='PASS') for key in keys], 'ROOT_DE_SKU_ALL_PACKAGE_FILE_STAGES')
    fields(restore, dict(status='RESTORED_IDENTICAL', production_go=False, release_evidence=False,
        checks=dict(restore_errors_only_pg_cron=True, catalog_explained=True, data_identical=True,
                    engine_answer_present=True, engine_equal=True)), 'ROOT_DE_SKU_BACKUP_RESTORE_DRILL')
    exact(restore['catalog']['differ'], {}, 'ROOT_DE_SKU_DRILL_CATALOG_DIFFERENCE')
    exact(restore['data']['differ'], {}, 'ROOT_DE_SKU_DRILL_DATA_DIFFERENCE')
    fields(restore['engine'], dict(equal=True, source_status='READY', restored_status='READY'), 'ROOT_DE_SKU_DRILL_ENGINE')
    source_proof = source(g, report['source_declaration'])
    cc = pure_module(g, 'root_exact_de_sku_context_catalog', NS + 'context_catalog.py')
    inventory = json_bytes(g.read(NS + 'CONTEXT_INVENTORY.json'))
    metadata = catalogue(case, cc, inventory)
    previous = sys.modules.get('context_catalog'); sys.modules['context_catalog'] = cc
    try:
        gate = pure_module(g, 'root_exact_de_sku_result_gate', NS + 'result_gate.py')
        recomputed = gate.checked(report, package, HEAD)
    finally:
        if previous is None:
            del sys.modules['context_catalog']
        else:
            sys.modules['context_catalog'] = previous
    recomputed['originals'] = {name: RAW_PINS[name] for name in (MAIN, PACKAGE)}
    exact(recomputed, docs[GATE], 'ROOT_DE_SKU_STANDALONE_FINAL_GATE_RECOMPUTATION_DIFFERS')
    return dict(status='ROOT_VERIFIED_ACTUAL_D1_E_SKU_PARENT_CATALOGUE_PREUSE_RESTORE_ALL5',
        classification='ACTUAL_INSTALLATION_CATALOGUE_ONLY_NOT_BUSINESS_OR_PHASE_AUTHORITY',
        head=HEAD, tree=TREE, run_id='41032035497', job_id=123983810324, artifact_id=12967889554,
        archive=ZIP_PIN, archive_members=126, archive_CRC_ok=True, originals=RAW_PINS,
        standalone_original_result_gate_recomputed=True, source=source_proof, actual_metadata=metadata,
        actual_catalogue_groups=1, actual_context_tables=55, actual_function_hook_rows=8,
        preuse_three_layer_inverse_and_reinstall=True, complete_outer_all22_rows_ALL_sequences_roles_CP6_advisors=True,
        package_all_five_gates=True, Auth_users_before=0, Auth_users_after=0,
        actual_two_session_races=0, used_guard_business_witness_executed=False,
        global_bridge_qualified=False, writer_trigger_FK_closure_qualified=False,
        active_context_or_phase_authority_qualified=False, business_owning_hooks_qualified=False,
        S03_S05_installed=False, full_final_composite_qualified=False, default_adopted=False,
        accepted_transactions_reexecuted=False, formal_total_unchanged='5/16', **ZERO, **NO_GO)


def intake(root, archive):
    with original_zip(archive, ZIP_PIN, 126) as z:
        docs = read_originals(z)
    with GitBytes(root, HEAD, TREE) as g:
        value = checked(g, docs)
    value['intake_scripts'] = script_pins('intake_s05.py', 'intake_de_sku_parent.py')
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-root', 'archive', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    save(intake(args.source_root, args.archive), args.output)
