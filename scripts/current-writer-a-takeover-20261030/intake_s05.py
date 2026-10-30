"""Root intake of exact S05 Native10 Originals; no database/business execution."""
from collections import Counter
from datetime import datetime
from hashlib import sha256
import argparse
import ast
import json
import re

from intake_common import (GitBytes, exact, fields, json_bytes, original_zip,
                           originals, pin, require, save, script_pins)

HEAD = '519d1760a3bad06a346b3d4b3cc0203664615634'
TREE = '15ccd8c9b5eb796724cfb39e3b4c8415f9c952bf'
BASE = '52eedc88e9aa2cd7470894c1f38ff9eb22f9cc60'
BASE_TREE = 'df8970c1c19d19b17c6a870d30adc535170725cc'
NS = 'scripts/current-s05-wib-owner-fixture-successor-qualification/'
WORKFLOW = '.github/workflows/cp7-current-s05-wib-owner-fixture-successor.yml'
CASE = 'S05_NATIVE10_AND_SEPARATE_COMMITTED_USED_INVERSE'
MAIN = 'CP7_S05_ACCESSORY_STANDARD_NATIVE10.json'
CASES = 'CP7_S05_ACCESSORY_STANDARD_NATIVE10_CASES.json'
PACKAGE = 'T3_PACKAGE_INSTALL.json'
FILES = 'T3_PACKAGE_FILES_INSTALL.json'
RESTORE = 'T3_BACKUP_RESTORE_DRILL.json'
ZIP_PIN = dict(bytes=2151338, sha256='43dc919acad9880afe6be8a9ba1aaa550503558f473e0b27ac699e8c8bd78854')
RAW_PINS = {
    MAIN: dict(bytes=4435195, sha256='be272d5c07c891a9e4ae795c95ec446c727e9a84ad8d90eccbee2507085825eb'),
    CASES: dict(bytes=232514, sha256='7b13beaa9d369398a2e6c3762d9649303e92e6c835aba8b476a5d51842f3d79a'),
    PACKAGE: dict(bytes=360428, sha256='089b8531e8d0686a9476f756ee51e865fc06a52de5c298b2b8b96efbcd37a663'),
    FILES: dict(bytes=1806, sha256='14007d43dd9b8e1acfa2b91e35d59047f553b248e2fc06e8362e8ad813003ba7'),
    RESTORE: dict(bytes=1470, sha256='2494d6eb768bf8ab8f0d8c1541c56a522970d7dd1d8a3059fc0b0d69d8f8bb69'),
}
IDS = (
    'S05_NATIVE_CATEGORY_VARIANTS_PO', 'S05_NATIVE_HISTORICAL_BOM',
    'S05_NATIVE_LATE_INVOICE_COST_REVISIONS', 'S05_NATIVE_ZERO_REIMBURSEMENT',
    'S05_NATIVE_EMPTY_AND_NO_OUTPUT', 'S05_NATIVE_WIB_COHORTS',
    'S05_NATIVE_NOTE_DRAFT_INVERSE', 'S05_NATIVE_QC_INVERSE',
    'S05_NATIVE_REWORK_NONE_RECORDED_RECIPIENT', 'S05_NATIVE_CURRENT_ACCESS_PRIVATE_ACL',
)
CALLBACK_SHA = 'e025be1280630dfb89f62261163194ce072b6f6ad6d909b56ff6c82f75778e98'
NO_CREDIT = dict(production_go=False, independent_acceptance=False)

# These are source-producer bindings, never a search for a matching hash.
# The duplicated reader-stream directory is deliberately not an alternative.
CONTRACT_DIRS = {
    'cp7.current-consistent-finance-private-opening.v2': 'current-finance-factory-progress-followup-qualification',
    'cp7.current-consistent-single-check-finance.v1': 'current-finance-combined-composition',
    'cp7.current-choice-readonly-finance-qualification.v1': 'current-finance-readonly-integration-qualification',
    'cp7.current-AB-public-frozen-progress.v1': 'cp7_current_analysis_progress',
    'cp7.current-versioned-performance-two-function-delta.v1': 'cp7_current_versioned_performance',
    'cp7.current-frozen-official-finance-private.v1': 'cp7_current_frozen_finance',
    'cp7.current-frozen-public-official-finance.v1': 'cp7_current_frozen_public',
}
FILESET_DIRS = {
    ('incoming.sql', 'native_delta.py', 'composition.py'): 'cp7_credit_incoming',
    ('multi.sql', 'native_delta.py', 'composition.py'): 'cp7_credit_multi',
    ('remaining.sql', 'native_delta.py', 'composition.py'): 'cp7_credit_remaining',
    ('followups.sql', 'native_delta.py', 'composition.py'): 'cp7_credit_followups',
    ('unknown_wash.sql', 'native_delta.py', 'composition.py'): 'cp7_laundry_unknown_wash',
    ('hpp_close.sql', 'native_delta.py', 'composition.py'): 'cp7_hpp_close',
    ('native_delta.py', 'composition.py'): 'cp7_ow09_lists',
    ('finance_capture.sql', 'report_compare.sql', 'native_delta.py', 'composition.py'): 'cp7_finance_capture',
    ('report_credit.sql', 'native_delta.py', 'composition.py'): 'cp7_report_credit',
    ('guidance.sql', 'native_delta.py', 'composition.py'): 'cp7_contractor_guidance',
    ('fg_correction.sql', 'native_delta.py', 'composition.py'): 'cp7_fg_correction_source',
    ('kasbon_source.sql', 'native_delta.py', 'composition.py'): 'cp7_kasbon_source',
    ('transfer.sql', 'correction.sql', 'read.sql', 'native_delta.py', 'composition.py'): 'cp7_supplier_transfer',
}


def source(g, declaration):
    own = json_bytes(g.read(NS + 'SOURCE.json'))
    cfg = json_bytes(g.read(NS + 'CONFIG.json'))
    fields(own, dict(base_public_head=BASE, base_public_tree=BASE_TREE,
        original_callback_source_sha256=CALLBACK_SHA, original_callback_body_substitutions=0,
        private_case_scope_wrappers=2, private_dependency_bindings=['fixture', 'issue_note'],
        product_Native_reader_cost_FIFO_money_datecohort_oracle_changes=0,
        accepted_fresh_native10=None, fresh_required_Native_cases=10,
        extra_case_credit_for_negative_setup_or_committed_witness=0, **NO_CREDIT), 'ROOT_S05_OWN_SOURCE')
    fields(cfg['failed_52eed'], dict(counts={'PASS': 8, 'INCOMPLETE': 2}, usable_prerequisite=False),
           'ROOT_S05_PRIOR_FAILURE_MUST_NOT_BECOME_PREREQUISITE')
    fields(declaration, dict(Native_case_ids=list(IDS), failed52eed_is_success_prerequisite=False,
        failed_cdbdea_is_success_prerequisite=False, partial8_plus2_aggregation=False,
        fresh_runtime_credit_from_admission=0, retained_vendor11_reexecuted=False,
        Afui_positive_HPP_zero_reimbursement_actual_coverage=False, **NO_CREDIT), 'ROOT_S05_DECLARATION')
    for key in ('wib_owner_fixture_source', 'current_AC_fixture_source'):
        item = declaration[key]
        exact(item['source_qualification'], own, 'ROOT_S05_ACTUAL_OWN_MANIFEST:' + key)
        fields(item, dict(source_files=43, actual_Native_credit=0, database_calls=0, **NO_CREDIT),
               'ROOT_S05_SOURCE_ONLY_ADMISSION:' + key)
        historical = item['historical_current_AC_source']
        exact(historical['source_qualification'], json_bytes(g.read(
            'scripts/current-s05-current-ac-editor-qualification/SOURCE.json')),
            'ROOT_S05_FROZEN_CURRENT_AC242')
        exact(historical['inherited']['qualification'], json_bytes(g.read(
            'scripts/current-s05-lawful-master-dates-qualification/SOURCE.json')),
            'ROOT_S05_LAWFUL_SOURCE207')
    exact(declaration['qualification'], json_bytes(g.read(
        'scripts/current-s05-public-default-acl-qualification/SOURCE.json')), 'ROOT_S05_PUBLIC_ACL_SOURCE162')
    exact(len(own['files']), 43, 'ROOT_S05_SOURCE43_COUNT')
    raw_cases = g.read('scripts/cp7_accessory_standard_report/cases.py')
    exact(sha256(raw_cases).hexdigest(), CALLBACK_SHA, 'ROOT_S05_ORIGINAL_CALLBACK_BYTES_CHANGED')
    declarations = [node for node in ast.parse(raw_cases).body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'IDS' for target in node.targets)]
    require(len(declarations) == 1, 'ROOT_S05_SINGLE_DECLARED_IDS_REQUIRED')
    exact(list(ast.literal_eval(declarations[0].value)), list(IDS), 'ROOT_S05_GIT_IDS_CHANGED')

    # Check complete immutable public52eed tree, including executable modes.
    exact(g.git('rev-parse', BASE + '^{tree}').decode().strip(), BASE_TREE, 'ROOT_S05_BASE_TREE')
    baseline = g.entries(BASE)
    exact(len(baseline), 13642, 'ROOT_S05_COMPLETE_PUBLIC_SOURCE_COUNT')
    for name, entry in baseline.items():
        exact(g.tree.get(name), entry, 'ROOT_S05_PUBLIC_PARENT_BYTES_OR_MODE_CHANGED:' + name)
    added = {name for name in own['files'] if name.startswith(NS)} | {NS + 'SOURCE.json', WORKFLOW}
    exact(set(g.tree) - set(baseline), added, 'ROOT_S05_ONLY_DECLARED_ADDITIONS_REQUIRED')
    snapshot = sha256(json.dumps(baseline, sort_keys=True).encode()).hexdigest()
    for key in ('wib_owner_fixture_source', 'current_AC_fixture_source'):
        fields(declaration[key]['complete_public_source'], dict(source_pins=43, public_files=13642,
            public_bytes_modes_snapshot_sha256=snapshot, historical_source242_unchanged=True,
            historical_untracked_proofs=24, product_changes=0, original_callback_body_changes=0,
            actual_new_Native=0, production_go=False), 'ROOT_S05_ACTUAL_COMPLETE_PUBLIC_SOURCE')
    archive = json_bytes(g.read('scripts/current-workflow-history-isolation/ARCHIVE.json'))
    exact(len(archive['files']), 24, 'ROOT_S05_HISTORICAL_PROOF24')
    for item in archive['files']:
        raw = g.read(item['archive'])
        exact(pin(raw), {key: item[key] for key in ('bytes', 'sha256')}, 'ROOT_S05_HISTORICAL_PROOF_PIN')
        exact(raw, g.read(item['path'], archive['base_head']), 'ROOT_S05_HISTORICAL_GIT_PROOF_BYTES')

    # Bind relative files to producers and validate their exact import routes.
    routes = [
        ('scripts/cp7_vendor_receivable/composition.py', 'scripts/current-factory-initial-stage/composition.py'),
        ('scripts/current-factory-initial-stage/composition.py',
         'scripts/current-finance-factory-progress-followup-qualification/composition.py'),
        ('scripts/current-finance-factory-progress-followup-qualification/composition.py',
         'scripts/current-finance-combined-composition/composition.py'),
        ('scripts/current-finance-combined-composition/composition.py',
         'scripts/current-finance-readonly-integration-qualification/composition.py'),
    ]
    for producer, target in routes:
        require(target in g.read(producer).decode(), 'ROOT_S05_SOURCE_PRODUCER_ROUTE_CHANGED:' + producer)
    exact(CONTRACT_DIRS['cp7.current-consistent-finance-private-opening.v2'],
          routes[1][1].split('/')[1], 'ROOT_S05_OPENING_NAMESPACE_MUST_BE_ACTUAL_FACTORY_PARENT')
    exact(CONTRACT_DIRS['cp7.current-consistent-single-check-finance.v1'],
          routes[2][1].split('/')[1], 'ROOT_S05_COMBINED_NAMESPACE_MUST_BE_ACTUAL_OPENING_PARENT')
    exact(CONTRACT_DIRS['cp7.current-choice-readonly-finance-qualification.v1'],
          routes[3][1].split('/')[1], 'ROOT_S05_READONLY_NAMESPACE_MUST_BE_ACTUAL_COMBINED_PARENT')
    chain = list(FILESET_DIRS.values())
    # Every edge is an explicit predecessor import in the immutable producer.
    for current, previous in zip(chain, chain[1:]):
        require('from ' + previous + ' import composition as predecessor' in
                g.read('scripts/' + current + '/composition.py').decode(),
                'ROOT_S05_FINANCIAL_SOURCE_PREDECESSOR_CHANGED:' + current)
    bindings, occurrences, maps = {}, 0, 0

    def walk(value):
        nonlocal occurrences, maps
        if type(value) is dict:
            if 'files' in value and type(value['files']) is dict:
                files = value['files']; maps += 1
                relative = all('/' not in name for name in files)
                prefix = ''
                if relative:
                    directory = CONTRACT_DIRS.get(value.get('contract'))
                    if directory is None:
                        require(value.get('contract') is None, 'ROOT_S05_UNKNOWN_RELATIVE_SOURCE_CONTRACT')
                        directory = FILESET_DIRS.get(tuple(files))
                    require(directory is not None, 'ROOT_S05_UNBOUND_RELATIVE_SOURCE_FILES')
                    prefix = 'scripts/' + directory + '/'
                    producer = prefix + ('composition.py' if 'composition.py' in files else
                                         'installation.py' if 'installation.py' in files else '__init__.py')
                    require('def sources():' in g.read(producer).decode(), 'ROOT_S05_SOURCE_PRODUCER_REQUIRED')
                for name, expected in files.items():
                    bound = prefix + name
                    g.verify_pin(bound, expected)
                    bindings[(bound, sha256(g.read(bound)).hexdigest())] = True
                    occurrences += 1
            for item in value.values():
                walk(item)
        elif type(value) is list:
            for item in value:
                walk(item)

    walk(declaration)
    exact(occurrences, 1407, 'ROOT_S05_DECLARED_FILES_PIN_OCCURRENCES_CHANGED')
    exact(maps, 71, 'ROOT_S05_DECLARED_FILES_MAP_COUNT_CHANGED')
    exact(len(bindings), 417, 'ROOT_S05_UNIQUE_BOUND_SOURCE_PIN_COUNT_CHANGED')
    return dict(own_manifest=pin(g.read(NS + 'SOURCE.json')), complete_public_parent_files=13642,
        complete_public_parent_modes_and_blobs_equal=True, new_paths=len(added),
        historical_proof_inputs=24, declared_files_pin_occurrences=occurrences,
        declared_files_maps=maps, unique_bound_path_digest_pairs=len(bindings),
        relative_files_bound_by_producer_namespace=True, matching_hash_in_other_namespace_accepted=False,
        relative_source_namespaces=sorted(set(CONTRACT_DIRS.values()) | set(FILESET_DIRS.values())),
        non_files_values='Retained evidence/body/derived hashes keep their original classification; no extra file or case credit.')


def fixture_observations(g, component):
    fixture = component['current_AC_editor_fixture']
    preflight = component['current_editor_preflight_observations']
    editor_rows = fixture['actual_observed_editor_rows']
    exact(len(preflight), 1, 'ROOT_S05_EXACT_EDITOR_PREFLIGHT_OBSERVATION')
    exact(len(editor_rows), 11, 'ROOT_S05_EXACT_EDITOR_FIXTURE_OBSERVATIONS')
    current = 'scripts/current-s05-current-ac-editor-qualification/'
    premise = json_bytes(g.read(current + 'CURRENT_AC_EDITOR_PREMISE.json'))
    definition = g.read(current + 'CURRENT_AC_EDITOR_DEFINITION.sql').decode()
    marker = re.search(r'\bAS\s+(\$[A-Za-z_0-9]*\$)', definition).group(1)
    body = definition.split(marker)[1]
    exact(sha256(body.encode()).hexdigest(), premise['current_prosrc_sha256'], 'ROOT_S05_CURRENT_EDITOR_SOURCE_BODY')
    for event in preflight + editor_rows:
        fields(event, dict(kind='ACTUAL_CURRENT_INSTALLED_EDITOR_ABI_OBSERVATION',
            signature='erp.save_accessory_bom_edit(uuid,jsonb,timestamp with time zone,text)',
            observed_owner='postgres', installed_parent_owner='postgres', admitted=True,
            observed_prosrc_sha256=premise['current_prosrc_sha256'], Native_case_credit=0),
            'ROOT_S05_ACTUAL_CURRENT_EDITOR')
        observed = event['observed_tuple']
        require(type(observed) is list and len(observed) == 3, 'ROOT_S05_EDITOR_EXACT_OBSERVED_TUPLE')
        observed_marker = re.search(r'\bAS\s+(\$[A-Za-z_0-9]*\$)', observed[0]).group(1)
        exact(observed[0].split(observed_marker)[1], body, 'ROOT_S05_ACTUAL_EDITOR_SOURCE_BODY_CHANGED')
        exact(observed[1:], ['postgres', premise['current_prosrc_sha256']], 'ROOT_S05_EDITOR_TUPLE_AUTHORITY')
        exact(sha256(observed[0].encode()).hexdigest(), event['observed_definition_sha256'], 'ROOT_S05_ACTUAL_EDITOR_DEFINITION_HASH')
        exact(event['observed_definition_sha256'], event['installed_parent_definition_sha256'], 'ROOT_S05_ACTUAL_EDITOR_PARENT_MATCH')
    fields(fixture, dict(all_original_ten_callback_bytes_financial_assertions_and_WIB_date_cohorts_unchanged=True,
        supported_WIB_seconds_fixture_transition_disclosed=True, new_Native_function_rewrites=0,
        actual_editor_observations_are_not_financial_case_credit=True, **NO_CREDIT), 'ROOT_S05_FIXTURE')
    fields(fixture['original_case_derivation'], dict(original_cases_sha256=CALLBACK_SHA,
        cases_source_substitutions=0, original_imported_module_mutated=False,
        callback_function_bodies_and_financial_assertions_byte_exact=True), 'ROOT_S05_CALLBACK_DERIVATION')
    fields(fixture['wib_owner_fixture_derivation'], dict(original_callback_source_SHA256=CALLBACK_SHA,
        raw_callback_body_substitutions=0, private_case_scope_wrappers=2,
        private_dependency_bindings=['fixture', 'issue_note'], original_imported_module_mutated=False,
        all_ten_original_money_quantity_and_date_cohort_assertions_unchanged=True,
        retained_current_AC_recipe_unchanged=True, Native_case_credit=0), 'ROOT_S05_WIB_OWNER_DERIVATION')
    observations = fixture['actual_wib_owner_fixture_observations']
    exact(len(observations), 8, 'ROOT_S05_EXACT_FIXTURE_OBSERVATIONS_REQUIRED')
    capture = observations[0]
    fields(capture, dict(kind='ACTUAL_FRESH_VERIFIED_PARENT_NATIVE_INPUT_CAPTURE',
        claimed_actual52eed_capture=False, Native_case_credit=0), 'ROOT_S05_FRESH_PARENT_CAPTURE')
    signatures = {'erp._idempotency_begin(text,uuid,text)', 'erp.guard_last_active_owner()',
                  'erp.guard_protected_role()', 'erp.save_accessory_issue_action_v1(text,jsonb,uuid)'}
    exact(set(capture['functions']), signatures, 'ROOT_S05_EXACT_CAPTURED_FUNCTIONS')
    historical = json_bytes(g.read(NS + 'evidence/ACTUAL_602_NATIVE_INPUTS.json'))
    for signature, item in capture['functions'].items():
        exact(sha256(item['definition'].encode()).hexdigest(), item['sha256'], 'ROOT_S05_CAPTURE_DEFINITION_DIGEST')
        if signature in historical['functions']:
            exact(item['definition'], historical['functions'][signature][0], 'ROOT_S05_ACTUAL_NATIVE_INPUT_CHANGED')
        else:
            # Compare exact function bodies; pg_get_functiondef formats DDL headers.
            sql = g.read('supabase/migrations/20260902104937_erp_v2_6_17_access_pattern_wip_control.sql').decode()
            tail = sql[sql.index('create function erp.guard_protected_role()'):]
            marker = re.search(r'\bas\s+(\$[A-Za-z_0-9]*\$)', tail, re.I).group(1)
            actual = item['definition']; actual_marker = re.search(r'\bAS\s+(\$[A-Za-z_0-9]*\$)', actual).group(1)
            exact(actual.split(actual_marker)[1], tail.split(marker)[1], 'ROOT_S05_PROTECTED_OWNER_ROLE_BODY_CHANGED')
    expected_refusals = [
        (1, 'ORIGINAL_FRACTIONAL_WIB_2', IDS[5], 'P0001', 'Waktu pengambilan wajib memakai tanggal dan jam WIB'),
        (3, 'ORIGINAL_FRACTIONAL_WIB_3', IDS[5], 'P0001', 'Waktu pengambilan wajib memakai tanggal dan jam WIB'),
        (5, 'LAST_ACTIVE_OWNER_UNCHANGED', IDS[9], '42501', 'LAST_ACTIVE_OWNER_PROTECTED'),
        (6, 'PROTECTED_OWNER_ROLE_UNCHANGED', IDS[9], '42501', 'PROTECTED_OWNER_ROLE_CANNOT_BE_CHANGED'),
    ]
    safe_refusals = []
    for index, label, case, state, message in expected_refusals:
        event = observations[index]
        fields(event, dict(kind='ACTUAL_NATIVE_FIXTURE_REFUSAL_NO_EFFECT', case_id=case, label=label,
            all22_catalog_equal=True, all_rows_and_every_sequence_equal=True,
            actual_parent_verified_before_and_after=True, Native_case_credit=0), 'ROOT_S05_ACTUAL_REFUSAL')
        exact(event['actual_error']['sqlstate'], state, 'ROOT_S05_REFUSAL_SQLSTATE')
        exact(event['actual_error']['message'].splitlines()[0], message, 'ROOT_S05_REFUSAL_ERROR')
        for key in ('before_catalog_sha256', 'before_data_sha256'):
            require(re.fullmatch('[0-9a-f]{64}', event[key]) is not None, 'ROOT_S05_REFUSAL_BOUNDARY_DIGEST')
        safe_refusals.append(dict(label=label, sqlstate=state, error=message, full_noeffect=True, extra_Native_credit=0))
    for index, qty, end in ((2, '2', False), (4, '3', True)):
        event = observations[index]
        fields(event, dict(kind='NATIVE_SUPPORTED_WIB_SECONDS_FIXTURE_POST', case_id=IDS[5], qty=qty,
            same_WIB_date_cohort=True, Native_parser_or_date_guard_changes=False, Native_case_credit=0),
            'ROOT_S05_SUPPORTED_WIB_POST')
        old, new = (datetime.fromisoformat(event[key]) for key in ('original_unsupported_value', 'actual_native_payload_value'))
        require(old.utcoffset().total_seconds() == new.utcoffset().total_seconds() == 25200,
                'ROOT_S05_WIB_OFFSET_CHANGED')
        exact(old.replace(microsecond=0), new, 'ROOT_S05_WIB_ONLY_SUPPORTED_SECONDS_TRANSITION')
        exact(old.date().isoformat(), event['physical_WIB_date'], 'ROOT_S05_WIB_COHORT_CHANGED')
        exact((old.hour, old.minute, old.second, old.microsecond),
              (23, 59, 59, 999999) if end else (0, 0, 0, 0), 'ROOT_S05_ORIGINAL_WIB_BOUNDARY_CHANGED')
    owner = observations[7]
    fields(owner, dict(kind='RETAINED_ADMINISTRATIVE_SECOND_OWNER_FIXTURE', case_id=IDS[9],
        active_owner_rows=2, fixture_helper='second_active_owner(existing_active_role)',
        new_grants_or_roles=False, Native_guard_or_trigger_changes=False, Native_case_credit=0), 'ROOT_S05_BACKUP_OWNER')
    require(owner['original_owner_auth'] != owner['backup_owner_auth'], 'ROOT_S05_DISTINCT_BACKUP_OWNER_REQUIRED')
    return safe_refusals


def checked(g, docs):
    main, group, package, files, restore = (docs[name] for name in (MAIN, CASES, PACKAGE, FILES, RESTORE))
    fields(main, dict(status='PASS', qualification_commit=HEAD, required_case_ids=[CASE],
        expected_case_count=1, observed_case_count=1, required_case_ids_pass=True,
        actual_Native_cases=10, actual_business_cases=10, actual_two_session_races=0,
        actual_Auth_HTTP_cases=0, actual_browser_cases=0, real_Auth_HTTP_qualified=False,
        combined_component_qualified=False, focused_factory_closure=False,
        full_combined_final_qualification=False, full_OW11_acceptance=False,
        performance_qualification=False, real_Auth_browser_claim=False, factory3600_claim=False,
        actual_cron_claim=False, default_adopted=False, formal_CP7C_started=False,
        used_guard_refused_before_DDL=True, scheduler_quiet_before_baseline_restore=True,
        baseline_full22_all_rows_all_sequences_equal=True, restore_raw_public_equal=True,
        cp6_restored=True, baseline_advisors_equal=True, advisor_gate=True, **NO_CREDIT), 'ROOT_S05_OUTER')
    exact(set(main['committed']), {CASE}, 'ROOT_S05_SINGLE_COMPONENT_REQUIRED')
    component = main['committed'][CASE]
    exact(component['native'], group, 'ROOT_S05_SEPARATE_CASES_MUST_EQUAL_EMBEDDED_GROUP')
    exact(component['strict_group_originals'], [dict(name=CASES, **RAW_PINS[CASES])], 'ROOT_S05_STRICT_ORIGINAL_RAW_PIN')
    fields(group, dict(status='PASS', counts={'PASS': 10}, planned_case_ids=list(IDS),
        final={name: 'PASS' for name in IDS}, missing=[], complete_boundary_restored=True, **NO_CREDIT), 'ROOT_S05_STRICT_GROUP')
    exact(list(group['cases']), list(IDS), 'ROOT_S05_EXACT_CASE_IDS_AND_ORDER')
    for (name, row), reads in zip(group['cases'].items(), (2, 2, 2, 1, 2, 6, 2, 2, 1, 6)):
        fields(row, dict(status='PASS', full_boundary_restored=True, public_schema_unchanged=True,
            all_reader_intervals_data_sequences_catalog_and_parent_equal=True,
            session_leaks=dict(advisory_locks=0, advisory_lock_keys=[], other_sessions=[]),
            full_family_acceptance=False, **NO_CREDIT), 'ROOT_S05_CASE:' + name)
        exact(len(row['actual_raw_reads']), reads, 'ROOT_S05_RAW_NATIVE_READ_COUNT:' + name)
    denials = [row['actual_error'] for row in group['cases'][IDS[9]]['actual_raw_reads'] if 'actual_error' in row]
    exact(len(denials), 4, 'ROOT_S05_FOUR_CURRENT_ACCESS_REFUSALS_REQUIRED')
    for refusal in denials:
        exact(refusal['sqlstate'], '42501', 'ROOT_S05_ACCESS_REFUSAL_SQLSTATE')
    expected_intervals = dict(zip(IDS, (1, 2, 2, 1, 2, 6, 2, 2, 1, 6)))
    expected_intervals.update(READER_INSTALL_AND_PREUSE_INVERSE=1, READER_REINSTALL_AND_INVERSE=1)
    exact(dict(Counter(row['case_id'] for row in component['reader_intervals'])), expected_intervals,
          'ROOT_S05_EXACT_27_READER_INTERVALS')
    for row in component['reader_intervals']:
        fields(row, dict(status='PASS', bounded_stage_uninstall_proved_all22_data_sequences_and_parent=True),
               'ROOT_S05_READER_INTERVAL')
        fields(row['actual_reader_verification'], dict(status='S05_EXACT_ADDITIVE_READER_ALL22',
            parent_verified_before_addition=True, parent_definitions_and_grants_unchanged=True,
            business_DML=False, **NO_CREDIT), 'ROOT_S05_ACTUAL_READER_VERIFICATION')
        fields(row['actual_installer_capability'], dict(status='S05_EXISTING_OUTER_SUPERUSER_ORIGINAL_DDL',
            outer_current_superuser=True, temporary_role_memberships=0, temporary_schema_grants=0,
            persistent_authority_change=False), 'ROOT_S05_READER_INSTALLER')
    fields(component['reader_preuse_reinstall'], dict(status='PASS', all22_data_sequences_parent_equal=True,
        phases=['INSTALL_AND_PREUSE_INVERSE', 'REINSTALL_AND_INVERSE'], new_business_DML=False), 'ROOT_S05_READER_PREUSE')
    fields(component, dict(status='PASS', actual_Native_cases=10, actual_two_session_races=0,
        actual_Auth_HTTP_cases=0, actual_browser_cases=0, used_guard_refused_before_DDL=True,
        report_business_DML=False, acceptance_requires_complete_outer_restore_and_all_five_package_gates=True,
        Afui_positive_HPP_zero_reimbursement_actual_coverage=False, **NO_CREDIT), 'ROOT_S05_COMPONENT')
    fields(component['separate_committed_business_witness'], dict(status='NATIVE_BUSINESS_COMMITTED',
        scope='OUTER_USED_INVERSE_WITNESS_NOT_REPORT_DML', Native10_case_credit=0, report_business_DML=False,
        actual_used_guard_error='VENDOR_RECEIVABLE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'), 'ROOT_S05_COMMITTED_USED_WITNESS')
    fields(main['baseline_restore'], dict(exit=1, error_count=19, unexplained=[], only_pg_cron_errors=True,
        database_owner_acl_and_settings_preserved=True), 'ROOT_S05_OUTER_RESTORE')
    fields(main['baseline_role_cleanup'], dict(baseline_roles_exact=True), 'ROOT_S05_ROLE_RESTORE')
    exact(main['restore_components'], dict(erp_platform_auth_schema_acl=True,
        all_public_catalog_members_and_row_hashes=True, erp_public_auth_function_definitions_owners_acls=True),
        'ROOT_S05_COMPLETE_RESTORE_COMPONENTS')
    exact(main['advisor_disposition']['gate'], True, 'ROOT_S05_ADVISORS_GATE')
    exact(main['advisor_disposition']['unexplained'], [], 'ROOT_S05_UNEXPLAINED_ADVISORS')
    fields(package, dict(mode='install', status='ALL_STAGES_INSTALLED', primary_unchanged=True,
        auth_users_before=0, auth_users_after=0, production_go=False, release_evidence=False,
        gate={name: True for name in ('installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')}),
        'ROOT_S05_ALL_FIVE_PACKAGE_GATES')
    fields(package['run_identity'], dict(tool_head=HEAD, github_sha=HEAD, run_id='41020627427', run_attempt='1',
        workflow='CP7 S05 lawful WIB and Owner fixture fresh Native10', job='p21', mode='install',
        event='push', release_evidence=False, production_go=False), 'ROOT_S05_ACTUAL_RUN_IDENTITY')
    fields(package['writer_runtime'], dict(status='PASS', **NO_CREDIT), 'ROOT_S05_PACKAGE_RUNTIME')
    fields(files, dict(status='ALL_FILES_INSTALLED', production_go=False, release_evidence=False), 'ROOT_S05_PACKAGE_FILES')
    keys = ['A' + chr(n) for n in range(ord('C'), ord('Z') + 1)] + ['B' + chr(n) for n in range(ord('A'), ord('F') + 1)]
    exact(files['files'], [dict(key=key, status='PASS') for key in keys], 'ROOT_S05_ALL_AC_TO_BF_FILES')
    fields(restore, dict(status='RESTORED_IDENTICAL', production_go=False, release_evidence=False,
        checks=dict(restore_errors_only_pg_cron=True, catalog_explained=True, data_identical=True,
                    engine_answer_present=True, engine_equal=True)), 'ROOT_S05_BACKUP_RESTORE_DRILL')
    exact(restore['catalog']['differ'], {}, 'ROOT_S05_DRILL_CATALOG_DIFFERENCE')
    fields(restore['data'], dict(tables=407, rows=1860), 'ROOT_S05_DRILL_FULL_DATA_COUNTS')
    exact(restore['data']['differ'], {}, 'ROOT_S05_DRILL_DATA_DIFFERENCE')
    fields(restore['engine'], dict(equal=True, source_status='READY', restored_status='READY'), 'ROOT_S05_DRILL_ENGINE')
    source_proof = source(g, main['source_declaration'])
    refusals = fixture_observations(g, component)
    return dict(status='ROOT_VERIFIED_NARROW_S05_NATIVE10_RAW_SOURCE_RESTORE_ALL5',
        classification='INTERNAL_WRITER_ROOT_INTAKE_NOT_FORMAL_INDEPENDENT_ACCEPTANCE',
        head=HEAD, tree=TREE, run_id='41020627427', job_id=123946877124, artifact_id=12965058954,
        archive_name='ERP_S05_Native10_519d_20261030.zip',
        private_Original_Library_file_id='libfile_1d18cbfeaf388191940a9e73f39f8122',
        archive=ZIP_PIN, archive_members=114, archive_CRC_ok=True, originals=RAW_PINS,
        actual_Native_cases=10, actual_Auth_HTTP_cases=0, actual_browser_cases=0, actual_two_session_races=0,
        actual_case_ids=list(IDS), strict_original_equals_embedded=True, actual_raw_native_reads=26,
        complete_reader_intervals=27, source=source_proof, original_callback_bytes_unchanged=True,
        actual_current_AC_editor_observations=12, editor_observation_extra_Native_credit=0,
        actual_fixture_refusal_controls=refusals, extra_case_credit_for_fixture_controls_or_witness=0,
        separate_committed_witness_and_used_inverse_noeffect=True, report_business_DML=False,
        full_outer_restore_all22_all_rows_ALL_sequences_roles_Auth_CP6_advisors=True,
        package_all_five_gates=True, Auth_users_before=0, Auth_users_after=0,
        prior_8_plus_2_aggregated=False, accepted_transactions_reexecuted=False,
        Afui_positive_HPP_zero_reimbursement_actual_coverage=False, UI5_qualified=False,
        full_S05_family_accepted=False, formal_total_unchanged='5/16', **NO_CREDIT)


def intake(root, archive):
    with original_zip(archive, ZIP_PIN, 114) as z:
        _, docs = originals(z, RAW_PINS)
    with GitBytes(root, HEAD, TREE) as g:
        value = checked(g, docs)
    value['intake_scripts'] = script_pins('intake_s05.py')
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-root', 'archive', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    save(intake(args.source_root, args.archive), args.output)
