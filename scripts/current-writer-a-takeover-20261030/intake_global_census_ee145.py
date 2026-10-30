"""Read-only ee145 source preparation and exact first-failure intake.

There is deliberately no successful-capture acceptance route. This Original
failed before its supplemental Original and final gate existed. A successor
needs its own exact public source and acquired Original byte identities.
"""
from hashlib import sha256
from pathlib import PurePosixPath
from types import ModuleType
import argparse
import ast
import json

from intake_common import (GitBytes, exact, fields, json_bytes, original_zip,
                           pin, require, save, script_pins)
from intake_de_sku_parent import (HEAD as BCE, TREE as BCE_TREE, NS as PARENT,
                                 source as bce_source)

HEAD = 'ee14592920c331d84d354a24b4b6b4a9f49f91d1'
TREE = '4f1173e9454548d44fc2c88c0bc628445df57027'
BASE = '80fab765938f8feaff151cd35fdb7923df987f23'
BASE_TREE = '9161822776b958a60cbe845f7a56d96c31db3dc5'
NS = 'scripts/current-de-sku-global-census-qualification/'
HELPER = 'scripts/current-global-actual-writer-census-qualification/'
WORKFLOW = '.github/workflows/cp7-de-sku-global-census.yml'
WORKFLOW_NAME = 'CP7 A D1 E SKU global writer metadata and full restoration'
CASE = 'D1_E_SKU_GLOBAL_WRITER_CENSUS_SOURCE_ONLY'
MAIN = 'CP7_D1_E_SKU_GLOBAL_CENSUS.json'
PACKAGE = 'T3_PACKAGE_INSTALL.json'
FILES = 'T3_PACKAGE_FILES_INSTALL.json'
DRILL = 'T3_BACKUP_RESTORE_DRILL.json'
RETENTION = 'GLOBAL_CENSUS_ORIGINAL_RETENTION.json'
COPY = 'SKU_COST_ARTIFACT_COPY_RECEIPT.json'
SUPPLEMENT = 'GLOBAL_ACTUAL_WRITER_SUPPLEMENT.json'
GATE = 'DE_SKU_GLOBAL_CENSUS_GATE.json'
ERROR = 'GLOBAL_CENSUS_DUPLICATE_SUPPLEMENT_IDENTITY:dependencies'
ZIP_PIN = dict(bytes=3990236, sha256='59d4ce7398bdcfd2cc3603ca487ea40eb171e1426070fe67f273ac5d0dcc174a')
RAW_PINS = {
    MAIN: dict(bytes=828201, sha256='170957fde933e1afc97f95e20d7cfe700d2b7a8f06c406210f7b4f2832472fb8'),
    PACKAGE: dict(bytes=360442, sha256='14c67466babccb2bf82b3b13909e16437d0cf1da62718ccfd390281617ed31ac'),
    FILES: dict(bytes=1806, sha256='14007d43dd9b8e1acfa2b91e35d59047f553b248e2fc06e8362e8ad813003ba7'),
    DRILL: dict(bytes=1470, sha256='b09c70d038ea024e1db9841a6f3da2788b212621b13302e9319ef6ff03c4a326'),
    RETENTION: dict(bytes=1153, sha256='1899f07ad715f0cf2c07a1b4ef8b28dc6f9e71b14d866cd8460a1188c7dcc9bd'),
    COPY: dict(bytes=224, sha256='07dc6c85c6eda4950fe4674c83a5b6ef0688217de4af2c35fa3291ae291a3340'),
}
NO_GO = dict(production_go=False, independent_acceptance=False)
CLOSED = dict(runtime_entry=None, actual_Native_credit=0, **NO_GO)
GROUPS = ('schemas', 'relations', 'columns', 'functions', 'roles', 'memberships',
    'foreign_keys', 'triggers', 'view_relation_dependencies', 'inheritance',
    'database_authority', 'default_privileges', 'effective_schema_privileges',
    'effective_table_privileges', 'effective_function_privileges',
    'effective_sequence_privileges', 'effective_explicit_column_privileges',
    'effective_database_privileges', 'dependencies')


class BlobPath:
    """Read-only path adapter for pure derivation functions, backed by Git."""
    def __init__(self, g, name=''):
        self.g, self.name = g, name

    def __truediv__(self, name):
        return BlobPath(self.g, str(PurePosixPath(self.name) / name))

    def __str__(self):
        return str(self.g.root / self.name)

    def read_bytes(self):
        return self.g.read(self.name)

    def read_text(self):
        return self.read_bytes().decode()


class Derivations:
    """Execute only four exact, source-string-producing modules; no ERP import."""
    ALLOWED = {NS + 'derive.py', NS + 'producer_profiles.py',
               HELPER + 'runner_patch.py', PARENT + 'derive.py'}

    def __init__(self, g):
        self.g, self.cache = g, {}

    def load(self, name, path):
        require(type(path) is BlobPath and path.g is self.g
                and path.name in self.ALLOWED, 'ROOT_GLOBAL_PURE_DERIVATION_PATH_REQUIRED')
        if path.name not in self.cache:
            module = ModuleType(name)
            module.__file__ = str(path)
            exec(compile(self.g.read(path.name), str(path), 'exec'), module.__dict__)
            module.ROOT = BlobPath(self.g)
            module.HERE = BlobPath(self.g, str(PurePosixPath(path.name).parent))
            module.load = self.load
            self.cache[path.name] = module
        return self.cache[path.name]


def source_queries(raw):
    """Read SQL string assignments without importing capture.py or running SQL."""
    values = {}

    def value(node):
        if type(node) is ast.Constant and type(node.value) is str:
            return node.value
        if type(node) is ast.Name:
            return values[node.id]
        if type(node) is ast.BinOp and type(node.op) is ast.Add:
            return value(node.left) + value(node.right)
        if type(node) is ast.Dict:
            return {value(k): value(v) for k, v in zip(node.keys, node.values)}
        raise ValueError('ROOT_GLOBAL_NONLITERAL_QUERY_SOURCE_REFUSED')

    for node in ast.parse(raw).body:
        if type(node) is not ast.Assign or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if type(target) is ast.Name and target.id in (
                'CONTRACT', 'SCOPE', 'RELATION', 'RELATION_SCOPE', 'FUNCTION_SCOPE', 'QUERIES'):
            values[target.id] = value(node.value)
        elif type(target) is ast.Subscript and type(target.value) is ast.Name and target.value.id == 'QUERIES':
            key = value(target.slice)
            require(key not in values['QUERIES'], 'ROOT_GLOBAL_DUPLICATE_QUERY_SOURCE')
            values['QUERIES'][key] = value(node.value)
    exact(tuple(values['QUERIES']), GROUPS, 'ROOT_GLOBAL_EXACT_19_QUERY_GROUPS')
    return values['QUERIES']


def source(g, actual=None):
    cfg_raw = g.read(NS + 'SOURCE.json'); cfg = json_bytes(cfg_raw)
    fields(cfg, dict(base=BASE, base_tree=BASE_TREE, original_catalogue_source=BCE,
        classification='READ_ONLY_GLOBAL_WRITER_METADATA_WITH_FULL_INHERITED_RESTORATION',
        metadata_only_entry=NS + 'probe.py --metadata-runtime', **CLOSED), 'ROOT_GLOBAL_SOURCE_SCOPE')
    baseline = g.entries(BASE)
    exact(g.git('rev-parse', BASE + '^{tree}').decode().strip(), BASE_TREE, 'ROOT_GLOBAL_BASE_TREE')
    exact(len(baseline), 13892, 'ROOT_GLOBAL_WHOLE_PARENT_COUNT')
    for name, entry in baseline.items():
        exact(g.tree.get(name), entry, 'ROOT_GLOBAL_PARENT_BLOB_OR_MODE_CHANGED:' + name)
    exact(len(cfg['files']), 16, 'ROOT_GLOBAL_SOURCE16')
    declared = set(cfg['files']) | {NS + 'SOURCE.json'}
    require(all(name.startswith(NS) or name == WORKFLOW for name in declared), 'ROOT_GLOBAL_SOURCE_NAMESPACE_ESCAPE')
    exact(set(g.tree) - set(baseline), declared, 'ROOT_GLOBAL_EXACT_17_ADDITIVE_PATHS')
    for name, expected in cfg['files'].items():
        g.verify_pin(name, expected)
        exact(expected['mode'], '100644', 'ROOT_GLOBAL_OWN_SOURCE_MODE')
    exact(g.tree[NS + 'SOURCE.json']['mode'], '100644', 'ROOT_GLOBAL_SEAL_MODE')
    integration_seal = json_bytes(g.read(HELPER + 'INTEGRATION_VALIDATION.json'))
    fields(integration_seal, dict(classification='WRITER_LOCAL_CLOSED_SUPPLEMENT_INTEGRATION_PREPARATION',
        parent_source_head=BCE, actual_supplement_capture_executed=False, canonical_parent_changed=False,
        global_hooks_opened=False, **CLOSED), 'ROOT_GLOBAL_HELPER_SEAL_SCOPE')
    exact(len(integration_seal['files']), 15, 'ROOT_GLOBAL_HELPER_SEALED15')
    exact({name for name in g.tree if name.startswith(HELPER)},
        {HELPER + name for name in integration_seal['files']} | {HELPER + 'INTEGRATION_VALIDATION.json'},
        'ROOT_GLOBAL_EXACT_HELPER16_PATHS')
    for name, expected in integration_seal['files'].items():
        require('/' not in name, 'ROOT_GLOBAL_HELPER_PIN_NOT_BASENAME')
        g.verify_pin(HELPER + name, expected)
    parent_pins = json_bytes(g.read(HELPER + 'INTEGRATION_SOURCE.json'))
    fields(parent_pins, dict(exact_parent=BCE, canonical_sources_modified=False,
        actual_runtime_integration_executed=False, **CLOSED), 'ROOT_GLOBAL_PARENT_PIN_SCOPE')
    exact(len(parent_pins['files']), 15, 'ROOT_GLOBAL_EXACT_PARENT_SOURCE15')
    for name, expected in parent_pins['files'].items():
        exact(g.verify_pin(name, expected), g.read(name, BCE), 'ROOT_GLOBAL_EXACT_BCE_PARENT_PIN')
    # The earlier local receipt remains history; its old pins apply to that
    # exact helper commit, never to the subsequently expanded helper source.
    history = json_bytes(g.read(HELPER + 'VALIDATION.json'))
    old_head = integration_seal['previous_helper_commit']
    for name, expected in history['files'].items():
        exact(pin(g.read(HELPER + name, old_head)),
            {key: expected[key] for key in ('bytes', 'sha256')}, 'ROOT_GLOBAL_HISTORICAL_HELPER_PIN')
    exact(g.read(HELPER + 'VALIDATION.json'), g.read(HELPER + 'VALIDATION.json', old_head),
          'ROOT_GLOBAL_HISTORICAL_HELPER_SEAL_REWRITTEN')
    pure = Derivations(g)
    deriver = pure.load('root_global_exact_deriver', BlobPath(g, NS + 'derive.py'))
    generated = {}; proofs = {}
    for kind in ('engine', 'runner', 'gate', 'integration'):
        generated[kind], proofs[kind] = getattr(deriver, kind)()
    exact(proofs, cfg['derivations'], 'ROOT_GLOBAL_ALL_REVERSIBLE_DERIVATIONS')
    for kind in ('runner', 'gate'):
        exact(proofs[kind]['inherited'], integration_seal['derivative_proofs'][kind],
              'ROOT_GLOBAL_INHERITED_DERIVATION_SEAL')
    profiles = pure.load('root_global_exact_profiles', BlobPath(g, NS + 'producer_profiles.py'))
    transitions = {}
    for filename in profiles.FILES:
        expected = profiles.derive(json_bytes(g.read(PARENT + filename)), filename, g.read(WORKFLOW))
        exact(json_bytes(g.read(NS + filename)), expected, 'ROOT_GLOBAL_EXACT_PRODUCER_PROFILE:' + filename)
        transitions[filename] = dict(new_workflow_producer=True,
            changed_package_workflow_name=filename == 'LATER_GENERATED_RECEIPTS.json', old_readers_unchanged=True)
    stage = actual.get('actual_stage_sources') if actual is not None else None
    if actual is not None:
        fields(actual, dict(status='EXACT_WHOLE_80FAB_TREE_PLUS_BOUNDED_METADATA_SUCCESSOR',
            parent_files=13892, successor_files=16, profile_transitions=transitions,
            old_frozen_guards_edited=False, old_source_manifests_resealed=False,
            old_runtime_qualification_inferred=False,
            metadata_only_entry=NS + 'probe.py --metadata-runtime', **CLOSED), 'ROOT_GLOBAL_ACTUAL_SOURCE_ADMISSION')
    # Independently verify every transitive bce source pin against immutable
    # bce Git. This is a source check, not a claim of a fresh bce execution.
    with GitBytes(g.root, BCE, BCE_TREE) as bce:
        for name, entry in bce.tree.items():
            exact(g.tree.get(name), entry, 'ROOT_GLOBAL_BCE_SOURCE_CHANGED:' + name)
        bce_cfg = json_bytes(bce.read(PARENT + 'SOURCE.json'))
        if stage is None:
            # --check-source has no actual report. The stage's declaration is
            # not invented: extract sources() through the exact source reader
            # only when a real Original supplies it during failure intake.
            for name, expected in bce_cfg['files'].items():
                bce.verify_pin(name, expected)
            bce_proof = dict(source_files=41, actual_stage_source_maps_checked=False)
        else:
            bce_proof = bce_source(bce, dict(status='EXACT_C397_PLUS_PUBLIC_PHASE2_D1_E_SKU_CATALOGUE_SUCCESSOR',
                unchanged_parent_files=13834, exact_public_imports=22, source_files=41,
                old_source_manifests_resealed=False, old_catalogue_projections=False,
                actual_business_cases=0, actual_Native_cases=0, business_runtime_entry=None,
                actual_stage_sources=stage, **NO_GO))
    queries = source_queries(g.read(HELPER + 'capture.py'))
    # Preserve the complete finally block, including failure handling and output.
    original_engine = g.read('scripts/current-vendor-receivable-qualification/probe.py').decode()
    marker = '    finally:\n        if before is not None and pre_dumped:'
    before_tail = original_engine.split(marker, 1)[1].split("        drill.docker('rm'", 1)[0]
    after_tail = generated['engine'].split(marker, 1)[1].split("        drill.docker('rm'", 1)[0]
    exact(after_tail, before_tail, 'ROOT_GLOBAL_FULL_OUTER_RESTORE_FINALLY_CHANGED')
    runner = generated['runner']; engine = generated['engine']; integration = generated['integration']
    require(engine.index('conn.commit();installed=True') < engine.index("'ISOLATED_DIAGNOSTICS'"),
            'ROOT_GLOBAL_METADATA_MUST_FOLLOW_COMMITTED_INSTALL')
    require(runner.index('census_integration.begin_readonly(conn,cur)') < runner.index("cur.execute('select current_database()')")
            < runner.index('proof=stage.verify(cur,state)') < runner.index('require_current_preuse(before,state)')
            < runner.index('census_capture.capture(') < runner.index('persist_original(')
            < runner.index("report['read_before']=before"), 'ROOT_GLOBAL_READONLY_CAPTURE_ORDER')
    require("cur.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED READ ONLY')" in integration
        and "cur.execute(\"SELECT pg_catalog.set_config('search_path','',true)\")" in integration,
        'ROOT_GLOBAL_EXACT_READONLY_SETUP')
    return dict(status='SOURCE_PREPARED_ONLY_NOT_ACTUAL_SUPPLEMENT_QUALIFICATION', head=HEAD, tree=TREE,
        base=BASE, base_tree=BASE_TREE, manifest=pin(cfg_raw), inherited_files_and_modes=13892,
        additive_paths=17, own_pinned_files=16, helper_current_pins=15,
        historical_helper_pins=len(history['files']), exact_bce_parent_pins=15,
        profile_transitions=transitions, bce_transitive_source=bce_proof,
        derivations=proofs, derived_source_pins={key: pin(value.encode()) for key, value in generated.items()},
        complete_outer_restore_finally_pin=pin(before_tail.encode()),
        declared_supplement_groups=list(GROUPS), declared_query_pins={key: pin(value.encode()) for key, value in queries.items()},
        committed_install_then_fresh_read_committed_read_only_source=True,
        actual_supplemental_Original_required=True, success_acceptance_route_implemented=False,
        raw_ACL_null_and_empty_source_distinct=True,
        source_checks_execute_no_SQL=True, old_manifests_resealed=False, **CLOSED)


def read_originals(z):
    docs = {}
    for name, expected in RAW_PINS.items():
        raw = z.read(name)
        exact(pin(raw), expected, 'ROOT_GLOBAL_EXACT_RAW_ORIGINAL:' + name)
        docs[name] = json_bytes(raw)
    require(SUPPLEMENT not in z.namelist() and GATE not in z.namelist(),
            'ROOT_GLOBAL_FIRST_FAILURE_MUST_HAVE_NO_SUPPLEMENT_OR_GATE')
    return docs


def failure(docs):
    report, package, files, drill, retained = (docs[name] for name in (MAIN, PACKAGE, FILES, DRILL, RETENTION))
    fields(report, dict(label=MAIN[:-5], status='INCOMPLETE', qualification_commit=HEAD,
        expected_case_count=1, observed_case_count=1, required_case_ids=[CASE], required_case_ids_pass=False,
        error=ERROR, committed={CASE: dict(status='INCOMPLETE')}, native={},
        scheduler_quiet_before_baseline_restore=True,
        baseline_full22_all_rows_all_sequences_equal=True, restore_raw_public_equal=True,
        cp6_restored=True, baseline_advisors_equal=True, advisor_gate=True,
        formal_CP7C_started=False, real_Auth_browser_claim=False, full_OW11_acceptance=False,
        actual_cron_claim=False, factory3600_claim=False, full_parent_inverse_repeated=False,
        focused_preuse_delta_only=True, **NO_GO), 'ROOT_GLOBAL_EXACT_FIRST_FAILURE')
    require('restore_error' not in report and 'restore_traceback' not in report,
            'ROOT_GLOBAL_RESTORATION_ERROR_MUST_NOT_BE_HIDDEN')
    require(ERROR in report['traceback'], 'ROOT_GLOBAL_FIRST_FAILURE_TRACE_REQUIRED')
    require(not any(key in report for key in ('read_before', 'read_after', 'global_writer_supplemental_reference',
            'global_writer_supplemental_noeffect', 'global_writer_read_transaction')),
            'ROOT_GLOBAL_NO_FABRICATED_COMPLETED_READ_BRACKET')
    for key in ('actual_catalogue_qualification_groups', 'actual_Native_cases', 'actual_business_cases',
                'actual_Auth_HTTP_cases', 'actual_browser_cases', 'actual_two_session_races'):
        require(key not in report, 'ROOT_GLOBAL_FAILED_RUN_MUST_NOT_ACQUIRE_CREDIT:' + key)
    fields(report['complete_installed_verification'], dict(status='EXACT_D1_E_SKU_INSTALLED_CATALOGUE_ONLY',
        older_verifiers_called_on_projected_catalogue=False, business_commands_executed=0,
        business_runtime_entry=None, **NO_GO), 'ROOT_GLOBAL_COMPLETE_INSTALL_VERIFIER')
    removal = report['focused_preuse_removal']
    fields(removal, dict(status='EXACT_D1_E_SKU_PREUSE_DELTA_RESTORE', used_guard_before_DDL=True,
        used_guard_business_witness_executed=False, actual_business_cases=0, production_go=False),
        'ROOT_GLOBAL_ACTUAL_PREUSE_RESTORE')
    exact(set(removal['removed']), {'D1', 'E', 'SKU'}, 'ROOT_GLOBAL_ALL_THREE_PREUSE_INVERSES')
    for layer, prefix in [('D1', 'CREDIT_DE'), ('E', 'CREDIT_E1'), ('SKU', 'SKU_PAIR_CONVERSION')]:
        fields(removal['removed'][layer], dict(status=prefix + '_EXACT_PREUSE_DELTA_RESTORE', used_guard_before_DDL=True),
               'ROOT_GLOBAL_PREUSE_LAYER:' + layer)
    fields(report['baseline_restore'], dict(exit=1, error_count=19, unexplained=[], only_pg_cron_errors=True,
        database_owner_acl_and_settings_preserved=True, platform_schema_authority_restored=['graphql', 'graphql_public']),
        'ROOT_GLOBAL_FULL_BASELINE_RESTORE')
    fields(report['baseline_role_cleanup'], dict(baseline_roles_exact=True), 'ROOT_GLOBAL_EXACT_ROLE_RESTORE')
    exact(report['restore_components'], dict(erp_platform_auth_schema_acl=True,
        all_public_catalog_members_and_row_hashes=True, erp_public_auth_function_definitions_owners_acls=True),
        'ROOT_GLOBAL_FULL_CP6_PUBLIC_AUTH_RESTORE')
    fields(report['exact_streaming_data_validation'], dict(status='PASS_REAL_BASELINE_EQUALITY_ONLY',
        prior_large_regression_repeated=False), 'ROOT_GLOBAL_FULL_ROW_STREAM_GUARD')
    fields(report['streaming_data_source_guard'], dict(old_jsonb_array_text_hash_algorithm_unchanged=True,
        namespace_table_selection_authority_GUC_and_all_sequences_unchanged=True, excluded_tables_added=0,
        rows_or_fields_skipped=0, qualified_role_oracles_unchanged=True), 'ROOT_GLOBAL_ROW_SEQUENCE_COVERAGE_UNWEAKENED')
    fields(report['advisor_disposition'], dict(status='VERIFIED_PRIVATE_DEFAULT_DENY_INFO', unexplained=[], gate=True),
           'ROOT_GLOBAL_ADVISOR_DISPOSITION')
    fields(package, dict(status='ALL_STAGES_INSTALLED', mode='install', primary_unchanged=True,
        auth_users_before=0, auth_users_after=0, production_go=False, release_evidence=False,
        backup_restore_drill='RESTORED_IDENTICAL', gate=dict(installed=True, primary_unchanged=True,
        backup_restore_drill=True, security_advisors=True, writer_runtime=False)), 'ROOT_GLOBAL_PACKAGE_EXACT_FOUR_OF_FIVE')
    fields(package['writer_runtime'], dict(status='INCOMPLETE', full_OW11_acceptance=False,
        schema_profile='HOSTED_USAGE_UNCHANGED', **NO_GO), 'ROOT_GLOBAL_WRITER_RUNTIME_REMAINS_INCOMPLETE')
    fields(package['run_identity'], dict(tool_head=HEAD, github_sha=HEAD, run_id='41044419248', run_attempt='1',
        workflow=WORKFLOW_NAME, job='p21', event='push', mode='install', production_go=False, release_evidence=False),
        'ROOT_GLOBAL_EXACT_RUN_IDENTITY')
    fields(files, dict(status='ALL_FILES_INSTALLED', production_go=False, release_evidence=False), 'ROOT_GLOBAL_PACKAGE_FILES')
    keys = ['A' + chr(n) for n in range(ord('C'), ord('Z') + 1)] + ['B' + chr(n) for n in range(ord('A'), ord('F') + 1)]
    exact(files['files'], [dict(key=key, status='PASS') for key in keys], 'ROOT_GLOBAL_COMPLETE_PACKAGE_FILE_STAGES')
    fields(drill, dict(status='RESTORED_IDENTICAL', source='cp6_rollback', target='cp6_restore_drill',
        production_go=False, release_evidence=False, checks=dict(restore_errors_only_pg_cron=True,
        catalog_explained=True, data_identical=True, engine_answer_present=True, engine_equal=True)),
        'ROOT_GLOBAL_BACKUP_RESTORE_DRILL')
    fields(drill['restore'], dict(exit=0, error_count=0, unexplained=[], errors=[]), 'ROOT_GLOBAL_DRILL_RESTORE_ERRORS')
    exact(drill['catalog']['differ'], {}, 'ROOT_GLOBAL_DRILL_ALL_CATALOGUE_DIFFERENCES')
    exact(drill['data']['differ'], {}, 'ROOT_GLOBAL_DRILL_ALL_DATA_DIFFERENCES')
    fields(drill['engine'], dict(equal=True, source_status='READY', restored_status='READY'), 'ROOT_GLOBAL_DRILL_ENGINE')
    exact(drill['data']['tables'], 407, 'ROOT_GLOBAL_FULL_BASELINE_TABLE_COUNT')
    expected_retention = dict(status='ORIGINAL_BYTE_IDENTITIES_ONLY_NOT_QUALIFICATION',
        files={name: RAW_PINS[name] for name in (MAIN, PACKAGE, DRILL, FILES, COPY)},
        missing_required=[GATE, SUPPLEMENT], full_raw_files_retained_by_artifact=True,
        metadata_or_data_bodies_printed=False, **CLOSED)
    exact(retained, expected_retention, 'ROOT_GLOBAL_HONEST_MISSING_ORIGINALS_RECEIPT')
    phases = report['stage_timings']
    exact([(row['phase'], row['state']) for row in phases], [
        ('SOURCE_ADMISSION', 'COMPLETED'), ('BASELINE_ADVISORS', 'COMPLETED'), ('BASELINE_DUMP', 'COMPLETED'),
        ('EXACT_VENDOR_PARENT_INSTALL', 'COMPLETED'), ('FIRST_FINANCE_DELTA', 'COMPLETED'),
        ('FINANCE_DELTA_PREUSE_INVERSE', 'COMPLETED'), ('SECOND_FINANCE_DELTA', 'COMPLETED'),
        ('ISOLATED_DIAGNOSTICS', 'FAILED'), ('BASELINE_RESTORE', 'COMPLETED')], 'ROOT_GLOBAL_EXACT_FIRST_FAILURE_PHASES')
    return dict(first_error=ERROR, report_status='INCOMPLETE', actual_case_status='INCOMPLETE',
        first_failure_preserved=True, restoration_error_present=False,
        committed_case_ids=[CASE], diagnostic_read_bracket_completed=False,
        separate_supplemental_Original_exists=False, final_all5_gate_Original_exists=False,
        observed_successful_metadata_groups=0, progress_count_is_qualification=False,
        used_guard_business_witness_executed=False,
        preuse_inverse_layers=['SKU', 'E', 'D1'], reinstall_before_diagnostics=True,
        baseline_full22_all_rows_ALL_sequences_equal_assertion=True,
        baseline_roles_exact_assertion=True, raw_public_CP6_Auth_restore_assertions=True,
        baseline_advisors_equal_assertion=True, advisor_gate=True,
        restoration_basis='EXACT_ORIGINAL_REPORT_ASSERTIONS_AND_UNCHANGED_FULL_OUTER_RESTORE_SOURCE',
        raw_baseline_and_final_snapshots_retained=False,
        outer_raw_snapshot_equality_independently_recomputed=False,
        standalone_drill_status='RESTORED_IDENTICAL', standalone_drill_tables=407,
        package_gates=package['gate'], package_all_five_gates=False,
        Auth_users_before=0, Auth_users_after=0,
        source_admission_generated_output_proofs=report['source_declaration']['generated_output_proofs'])


def intake(root, archive=None):
    if archive is None:
        with GitBytes(root, HEAD, TREE) as g:
            value = source(g)
    else:
        with original_zip(archive, ZIP_PIN, 126) as z:
            docs = read_originals(z)
        observed = failure(docs)
        with GitBytes(root, HEAD, TREE) as g:
            prepared = source(g, docs[MAIN]['source_declaration'])
        value = dict(status='ROOT_VERIFIED_EE145_FIRST_DEPENDENCY_FAILURE_AND_RESTORATION_ASSERTIONS_ONLY',
            classification='FAILED_ACTUAL_GLOBAL_CAPTURE_ZERO_SUPPLEMENTAL_QUALIFICATION',
            head=HEAD, tree=TREE, run_id='41044419248', job_id=124024866394, artifact_id=12973268705,
            archive=ZIP_PIN, archive_members=126, archive_CRC_ok=True, originals=RAW_PINS,
            source=prepared, observed=observed, actual_supplemental_groups_qualified=0,
            actual_business_cases=0, actual_Auth_HTTP_cases=0, actual_browser_cases=0, actual_two_session_races=0,
            actual_phase_authority_qualified=False, actual_complete_ERP_lock_graph_qualified=False,
            writer_or_phantom_lock_closed=False, permission_closure='UNKNOWN',
            duplicate_dependency_cause='UNDETERMINED_RAW_FAILED_QUERY_ROWS_NOT_RETAINED',
            dependency_query_or_identity_changed=False, success_intake_permitted=False,
            source_supplement_scope_is_not_actual_result=True, accepted_transactions_reexecuted=False,
            formal_total_unchanged='5/16', **CLOSED)
    value['intake_scripts'] = script_pins('intake_s05.py', 'intake_de_sku_parent.py', 'intake_global_census_ee145.py')
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True)
    parser.add_argument('--archive')
    parser.add_argument('--check-source', action='store_true')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    require(args.check_source != bool(args.archive), 'ROOT_GLOBAL_EXACTLY_ONE_SOURCE_OR_FIRST_FAILURE_MODE_REQUIRED')
    save(intake(args.source_root, args.archive), args.output)
