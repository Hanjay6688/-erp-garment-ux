"""Local source/API/proof-parser doubles only; never Native/Auth/browser credit."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import patch
from types import ModuleType
import ast
import gzip
import json
import os
import tempfile
import unittest
import yaml
import sys
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name):
    spec = spec_from_file_location('s03_browser4_local_' + name, HERE / (name + '.py'))
    value = module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


binder, derive, gate = load('proof_binder'), load('derive'), load('result_gate')


def native_double():
    original, readers = list(binder.ORIGINAL11_IDS), list(binder.READER3_IDS)
    section = lambda ids: dict(status='PASS', counts={'PASS': len(ids)}, planned_case_ids=ids,
        cases={key: {'status': 'PASS'} for key in ids}, complete_boundary_restored=True)
    used = dict(actual_all22={str(i): {} for i in range(22)}, full_data_and_sequences={
        'cp7_attendance_choice.decisions_v1': [1, 'explicit-double'],
        'cp7_attendance_choice.allocations_v1': [1, 'explicit-double'], 'sequence:explicit_double': ['3', True]})
    runtime = {'scripts/cp7_attendance_period_choice/' + name: 'a' * 64 for name in
        ('choice.sql', 'native_delta.py', 'catalog_contract.py', 'NEW_CATALOG_IDENTITIES.json', 'composition.py', 'readers.sql', 'installer_ddl.py')}
    report = dict(status='PASS', label='EXPLICIT_LOCAL_DOUBLE_NOT_ACTUAL_ORIGINAL', qualification_commit='c' * 40,
        actual_Native_cases=14, actual_browser_cases=0, actual_Auth_HTTP_cases=0, actual_two_session_races=0,
        committed={'explicit_double': {'status': 'PASS', 'used_guard_refused_before_DDL': True,
            'native11': section(original), 'reader3': section(readers), 'before': used, 'after': deepcopy(used)}},
        sources={'whole_actual_installation': {'files': runtime, 'predecessor': {'classification': 'EXPLICIT_SOURCE_DOUBLE'}}},
        current_qualification=dict(actual_authored_files=118, exact_runtime_files=7, captured_originals=15, private_clones=2, groups=[11, 3]))
    report.update({name: True for name in binder.RESTORE_FLAGS})
    package = dict(status='ALL_STAGES_INSTALLED', gate={key: True for key in binder.PACKAGE_GATES})
    binding = dict(actual_case_count=14, qualifying_commit='c' * 40, qualifying_tree='d' * 40, run_id='123', job_id='456',
        original11_ids=original, reader3_ids=readers, outer_label=report['label'], component_path=['committed', 'explicit_double'],
        strict_sections=[{'path': ['committed', 'explicit_double', 'native11'], 'ids': original},
                         {'path': ['committed', 'explicit_double', 'reader3'], 'ids': readers}],
        used_before_path=['committed', 'explicit_double', 'before'], used_after_path=['committed', 'explicit_double', 'after'],
        files_required_values=[{'path': ['status'], 'value': 'EXPLICIT_FILES_DOUBLE'}],
        restoration_required_values=[{'path': ['status'], 'value': 'EXPLICIT_RESTORE_DOUBLE'}],
        current_installation_path=['sources', 'whole_actual_installation'], runtime_files=runtime,
        current_qualification_path=['current_qualification'])
    return (report, package, {'status': 'EXPLICIT_FILES_DOUBLE'}, {'status': 'EXPLICIT_RESTORE_DOUBLE'},
        deepcopy(report['committed']['explicit_double']['native11']),
        deepcopy(report['committed']['explicit_double']['reader3']), binding)


def browser_double():
    def row(key):
        width = 390 if key == gate.IDS[1] else 1440
        return dict(status='PASS', classification='EXPLICIT_LOCAL_PARSER_DOUBLE_NOT_ACTUAL_BROWSER',
            actual_normal_App_real_Auth_public_RPC=True, fixture_screen_creation_claim=False,
            actual_Native_cases=0, actual_Auth_HTTP_cases=0, actual_two_session_races=0,
            shots=['cp6-proof/t3/EXPLICIT_LOCAL_DOUBLE.png'], contrasts=[{'width': {'viewport': width, 'page': width},
                'measured': [{'ratio': 4.5}]}], console_evidence={'unexpected': [], 'page_errors': []})
    browser = dict(status='PASS', counts={'PASS': 4}, planned_case_ids=list(gate.IDS),
        cases={key: row(key) for key in gate.IDS}, database_remaining=0, cleanup_failures=[],
        auth_counts={'restored': True}, console_errors=0, session_leaks=[], real_auth=True,
        jwt_signed_by_runtime=False, test_only_usage_grant=False)
    component = dict(status='PASS', actual_browser_cases=4, browser=browser,
        actual_captured_originals=15, actual_Native_clones=2, product_sources_override=False,
        frozen_UI_root_backend_replaced=False, actual_backend_runtime_files={str(i): 'EXPLICIT_DOUBLE' for i in range(7)},
        copy_catalog_admissions=[{'all22_groups_equal_original_install': True}],
        actual_browser_host_originals=[{'classification': 'EXPLICIT_METADATA_DOUBLE_NO_ACTUAL_RAW'}])
    report = dict(status='PASS', label=gate.LABEL, committed={gate.CASE: component},
        actual_browser_cases=4, actual_Native_cases=0, actual_Auth_HTTP_cases=0, actual_two_session_races=0)
    report.update({key: True for key in (*binder.RESTORE_FLAGS, 'real_Auth_browser_claim')})
    package = dict(status='ALL_STAGES_INSTALLED', gate={key: True for key in binder.PACKAGE_GATES})
    return report, package


class ProofAndSourceControls(unittest.TestCase):
    def test_frozen_config_cannot_execute(self):
        config = json.loads((HERE / 'retained-preparation/CONFIG.json').read_bytes())
        self.assertIsNone(config['backend_binding'])
        self.assertIsNone(config['accepted_originals'])
        self.assertIs(config['actual_execution_authorized'], False)

    def test_closed_admission_reaches_no_ERP_import(self):
        guard = load('source_guard')
        with patch.object(guard, 'check', return_value={'config': json.loads((HERE / 'retained-preparation/CONFIG.json').read_bytes())}):
            with self.assertRaisesRegex(ValueError, 'CLOSED_REQUIRES_EXACT_BACKEND14'):
                guard.admitted()

    def test_actual_whole_source_is_checked_without_private_ui_git(self):
        guard = load('source_guard')
        result = guard.check()
        self.assertEqual(result['status'], 'SOURCE_PASS')
        tree = ast.parse((HERE / 'source_guard.py').read_text())
        self.assertNotIn('abdbc306', ast.unparse(tree))

    def test_every_frozen_UI_mount_and_source38_byte_matches_public_endpoint(self):
        declaration = json.loads((HERE / 'SOURCE.json').read_bytes())
        self.assertEqual(len(declaration['frozen_public_UI_paths']), 82)
        self.assertIn('scripts/current-attendance-choice-mount-ui/SOURCE.json', declaration['frozen_public_UI_paths'])
        self.assertEqual(len(declaration['physical_UI8_baseline']), 8)
        self.assertIs(declaration['old_frozen_mount16_reexecuted_against_expanded_HEAD'], False)
        self.assertIs(declaration['private_abdbc_Git_required'], False)
        self.assertIs(declaration['UI_alias_is_runtime_prerequisite'], False)

    def test_inherited_source_pin_never_authorizes_out_of_scope_edit_or_untracked_input(self):
        guard = load('source_guard');run = subprocess.check_output
        declaration = json.loads((HERE / 'SOURCE.json').read_bytes())
        inherited = 'scripts/cp7_snapshot_cases.py'
        self.assertIn(inherited, {row['path'] for row in declaration['files']})
        self.assertNotIn(inherited, declaration['allowed_current_delta'])
        for field in ('changed', 'untracked'):
            def observed_command_double(args, **kwargs):
                result = run(args, **kwargs)
                condition = args[-3:] == (['diff', '--name-only', declaration['public_base_commit']] if field == 'changed'
                    else ['ls-files', '--others', '--exclude-standard'])
                return result + inherited + '\n' if condition else result
            with self.subTest(field=field), patch.object(guard.subprocess, 'check_output', side_effect=observed_command_double):
                with self.assertRaisesRegex(ValueError, 'UNDECLARED_CURRENT_WHOLE_SOURCE_DELTA'):guard.check()

    def test_materialized_historical_inputs_remain_exact28_and_corrupt_bytes_refuse(self):
        guard = load('source_guard')
        declaration = json.loads((HERE / 'SOURCE.json').read_bytes())
        inputs = declaration['exact_untracked_inputs']
        self.assertEqual(len(inputs), 28)
        self.assertEqual({Path(name).suffix for name in inputs}, {'.gz', '.yml'})
        target = ROOT / next(iter(inputs))
        exists, read = Path.exists, Path.read_bytes
        def present_double(path):return True if path == target else exists(path)
        def corrupt_double(path):return b'EXPLICIT_LOCAL_CORRUPT_ORIGINAL_DOUBLE' if path == target else read(path)
        with patch.object(Path, 'exists', present_double), patch.object(Path, 'read_bytes', corrupt_double):
            with self.assertRaisesRegex(ValueError, 'EXACT_HISTORICAL_INPUT_CHANGED'):guard.check()

    def test_prepared_backend_seven_files_and_wire_never_substitute_actual_acceptance(self):
        prepared = json.loads((HERE / 'PREPARED_BACKEND.json').read_bytes())
        self.assertEqual(prepared['public_commit'], '73ad6d323099e1d5384a94477043c01db8989106')
        self.assertEqual(len(prepared['runtime_files']), 7)
        self.assertEqual({Path(row['path']).name for row in prepared['runtime_files']},
            {'choice.sql', 'readers.sql', 'native_delta.py', 'catalog_contract.py',
             'NEW_CATALOG_IDENTITIES.json', 'composition.py', 'installer_ddl.py'})
        self.assertIsNone(prepared['accepted_originals'])
        self.assertIs(prepared['actual_backend14_qualified'], False)
        self.assertEqual(prepared['actual_Native_Auth_browser'], 0)
        wire = {Path(row['path']).name: row['sha256'] for row in prepared['wire_and_prepared_reader_source']}
        self.assertEqual(wire['WIRE_CONTRACT.md'], '931e62848f6861e24190e76cb0efbd8aa032cb514bf0f0b5af362d62cbe12bbd')
        self.assertEqual(wire['READER_WIRE_CONTRACT.md'], '977a973fc9d641dc8699bc445ed2c73167aee403a1a78f666fc34e9c5be4cb6c')

    def test_selected_runtime7_and_real_package_entry_are_exact_without_ERP_import(self):
        loader = load('backend_runtime')
        mapping = json.loads((HERE / 'RUNTIME_SOURCE.json').read_bytes())
        expected = {name: pin['sha256'] for name, pin in mapping['runtime_files'].items()}
        route = loader.retained(expected)
        self.assertEqual(route['component_root'], HERE / 'runtime-backend7')
        self.assertEqual(route['runtime_files'], expected)
        for mutation in ('unknown', 'missing', 'changed'):
            wrong = dict(expected)
            if mutation == 'unknown':wrong['scripts/cp7_attendance_period_choice/unknown.sql'] = 'a' * 64
            elif mutation == 'missing':wrong.pop('scripts/cp7_attendance_period_choice/readers.sql')
            else:wrong['scripts/cp7_attendance_period_choice/readers.sql'] = 'a' * 64
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, 'EXACT_SELECTED_ACTUAL_RUNTIME7_REQUIRED'):
                loader.retained(wrong)

    def test_null_gate_and_ambient_old_package_refuse_before_any_actual_import(self):
        loader = load('backend_runtime')
        mapping = json.loads((HERE / 'RUNTIME_SOURCE.json').read_bytes())
        files = {name: pin['sha256'] for name, pin in mapping['runtime_files'].items()}
        with patch.object(loader, 'import_module', side_effect=AssertionError('ERP_IMPORT_FORBIDDEN_IN_LOCAL_CONTROL')):
            with self.assertRaisesRegex(ValueError, 'ACTUAL_ADMISSION_BEFORE_BACKEND_IMPORT'):
                with loader.actual_backend({}):pass
            old = ModuleType(loader.PACKAGE);old.__file__ = str(ROOT / 'scripts/cp7_attendance_period_choice/__init__.py')
            proof = dict(status='EXACT_ACTUAL_BACKEND14_AND_ALL5_ORIGINALS_ADMITTED', actual_parent_Native_cases=14,
                current_installation={'files': files})
            with patch.dict(sys.modules, {loader.PACKAGE: old}):
                with self.assertRaisesRegex(ValueError, 'CACHED_NONCURRENT_BACKEND_IMPORT_REFUSED'):
                    with loader.actual_backend(proof):pass

    def test_loader_restores_modules_path_argv_on_success_and_failure_using_import_double(self):
        loader = load('backend_runtime')
        mapping = json.loads((HERE / 'RUNTIME_SOURCE.json').read_bytes())
        files = {name: pin['sha256'] for name, pin in mapping['runtime_files'].items()}
        installation = {'files': files, 'classification': 'EXPLICIT_IMPORT_DOUBLE_NO_REAL_ERP'}
        proof = dict(status='EXACT_ACTUAL_BACKEND14_AND_ALL5_ORIGINALS_ADMITTED', actual_parent_Native_cases=14,
            current_installation=installation)
        def import_double(name):
            route = loader.retained(files)
            for item in (loader.PACKAGE, *(loader.PACKAGE + '.' + file[:-3] for file in loader.NAMES if file.endswith('.py'))):
                module = ModuleType(item);module.__file__ = str(route['package'] / ('__init__.py' if item == loader.PACKAGE else item.rsplit('.', 1)[1] + '.py'))
                sys.modules[item] = module
            sys.modules[name].sources = lambda: installation
            sys.modules['S03_EXPLICIT_LOCAL_IMPORT_DOUBLE'] = ModuleType('S03_EXPLICIT_LOCAL_IMPORT_DOUBLE')
            return sys.modules[name]
        for failed in (False, True):
            before_modules, before_path, before_argv = dict(sys.modules), list(sys.path), sys.argv
            with patch.object(loader, 'import_module', side_effect=import_double):
                try:
                    with loader.actual_backend(proof) as product:
                        self.assertEqual(product.sources(), installation)
                        self.assertEqual(sys.path[0], str(HERE / 'runtime-backend7/scripts'))
                        sys.argv.append('EXPLICIT_LOCAL_BODY_CHANGE')
                        if failed:raise ValueError('EXPLICIT_BODY_FAILURE')
                except ValueError as error:
                    self.assertTrue(failed);self.assertEqual(str(error), 'EXPLICIT_BODY_FAILURE')
            self.assertEqual(sys.modules, before_modules)
            self.assertEqual(sys.path, before_path)
            self.assertIs(sys.argv, before_argv)

    def test_canonical118_metadata_is_correspondence_only_and_rejects_one_changed_author_pin(self):
        prepared = json.loads((HERE / 'PREPARED_AUTHOR_BINDING.json').read_bytes())
        author = prepared['author_binding'];runtime = author['runtime_files']
        raw_config = (HERE / 'retained-source-metadata/PREPARED_NATIVE14_CONFIG.json').read_bytes()
        raw_source = (HERE / 'retained-source-metadata/PREPARED_NATIVE14_SOURCE.json').read_bytes()
        self.assertEqual(sha256(raw_config).hexdigest(), prepared['qualifier_config']['sha256'])
        self.assertEqual(sha256(raw_source).hexdigest(), prepared['qualifier_source']['sha256'])
        config, source = json.loads(raw_config), json.loads(raw_source)
        self.assertEqual(binder.check_qualified_metadata(config, source, prepared, runtime),
            {'exact_public_authored_files': 118, 'exact_actual_runtime_files': 7})
        first = next(iter(author['files']));source['files'][first]['sha256'] = 'a' * 64
        with self.assertRaisesRegex(ValueError, 'CANONICAL_PUBLIC_AUTHOR118_SOURCE_BINDING_CHANGED'):
            binder.check_qualified_metadata(config, source, prepared, runtime)

    def test_synthetic_positive_checks_parser_only(self):
        report, package, files, restoration, native11, reader3, binding = native_double()
        result = binder.checked(report, package, files, restoration, native11, reader3, binding)
        self.assertEqual(result['actual_parent_Native_cases'], 14)
        self.assertIs(result['fresh_parent_cases_claim'], False)
        # Never write this synthetic object to CONFIG, retained/ or a source declaration.
        self.assertIsNone(json.loads((HERE / 'retained-preparation/CONFIG.json').read_bytes())['accepted_originals'])

    def test_two_strict_groups_cannot_be_folded_or_relabelled(self):
        for mutation in ('fold', 'rename', 'missing'):
            report, package, files, restoration, native11, reader3, binding = native_double()
            if mutation == 'fold':
                binding['strict_sections'] = [{'path': ['committed', 'explicit_double', 'native11'], 'ids': binding['original11_ids'] + binding['reader3_ids']}]
            elif mutation == 'rename':
                binding['reader3_ids'][0] = 'INVENTED'
            else:
                report['committed']['explicit_double']['reader3']['cases'].pop(binding['reader3_ids'][0])
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                binder.checked(report, package, files, restoration, native11, reader3, binding)

    def test_actual_failure_missing_restore_package_or_run_never_admits(self):
        for mutation in ('status', 'native0', 'restore', 'package', 'commit', 'used_data', 'six_runtime', 'old_capture13'):
            report, package, files, restoration, native11, reader3, binding = native_double()
            if mutation == 'status':report['status'] = 'INCOMPLETE'
            elif mutation == 'native0':report['actual_Native_cases'] = 0
            elif mutation == 'restore':report['cp6_restored'] = False
            elif mutation == 'package':package['gate']['writer_runtime'] = False
            elif mutation == 'commit':report['qualification_commit'] = 'e' * 40
            elif mutation == 'used_data':report['committed']['explicit_double']['after']['full_data_and_sequences']['sequence:explicit_double'][0] = '4'
            elif mutation == 'old_capture13':report['current_qualification']['captured_originals'] = 13
            else:binding['runtime_files'].pop('scripts/cp7_attendance_period_choice/installer_ddl.py')
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                binder.checked(report, package, files, restoration, native11, reader3, binding)

    def test_separate_strict_group_original_bytes_cannot_be_replaced_by_embedded_claim(self):
        for name in ('native11', 'reader3'):
            values = list(native_double())
            original = values[4 if name == 'native11' else 5]
            original['classification'] = 'DIFFERENT_LOCAL_DOUBLE_BYTES'
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'SEPARATE_STRICT_GROUP_ORIGINAL_CHANGED'):
                binder.checked(*values)

    def test_catalog_environment_restores_even_if_original_retention_raises(self):
        component = load('component')
        key = 'S03_BROWSER_EXPECTED_CATALOG_SHA256'
        for previous in (None, 'caller-original-digest'):
            with patch.dict(os.environ, {}, clear=False):
                if previous is None:os.environ.pop(key, None)
                else:os.environ[key] = previous
                with self.assertRaisesRegex(ValueError, 'EXPLICIT_RETENTION_DOUBLE_FAILURE'):
                    with component.actual_catalog_environment('actual-installation-double'):
                        self.assertEqual(os.environ[key], 'actual-installation-double')
                        raise ValueError('EXPLICIT_RETENTION_DOUBLE_FAILURE')
                self.assertEqual(os.environ.get(key), previous)

    def test_workflow_is_exact_bounded_child_with_no_ERP_GET_or_DB_before_proof_gate(self):
        workflow = load('workflow')
        parent = yaml.safe_load((ROOT / workflow.PARENT).read_text())
        actual = yaml.safe_load((ROOT / workflow.WORKFLOW).read_text())
        self.assertEqual(actual, workflow.derive(parent))
        steps = actual['jobs']['p21']['steps']
        self.assertTrue(steps[0]['uses'].startswith('actions/checkout@'))
        self.assertEqual(steps[1]['run'], 'python3 -B ' + workflow.NAMESPACE + '/source_guard.py --require-actual')
        self.assertEqual(actual['on']['push']['branches'], [workflow.BRANCH])
        self.assertEqual(actual['jobs']['p21']['if'], "github.ref == 'refs/heads/" + workflow.BRANCH + "'")
        self.assertEqual(actual['jobs']['p21']['env']['AUDITOR_UI_MODE'], 'DISPOSABLE')
        names = [step.get('name', '') for step in steps]
        self.assertLess(names.index('Admit entire current source and exact actual backend14 graph before database'),
            names.index('Start disposable database'))
        self.assertIn('--check-actual-source', steps[names.index('Admit entire current source and exact actual backend14 graph before database')]['run'])

    def test_workflow_preserves_every_unselected_full_engine_and_restore_step(self):
        workflow = load('workflow')
        original = yaml.safe_load((ROOT / workflow.PARENT).read_text())
        actual = yaml.safe_load((ROOT / workflow.WORKFLOW).read_text())
        changed_names = {'Admit exact backend3194 parent and declared vendor delta before database',
            'Run fresh Native7 then actual race3 AuthHTTP1 and complete restoration',
            'Preserve exact original JSON report bytes in a bounded compressed log receipt'}
        actual_steps = actual['jobs']['p21']['steps']
        for step in original['jobs']['p21']['steps']:
            if step.get('name') in changed_names or step.get('uses', '').startswith('actions/upload-artifact@'):
                continue
            with self.subTest(name=step.get('name', step.get('uses'))):
                self.assertEqual(actual_steps.count(step), 1)
        old_job, new_job = deepcopy(original['jobs']['p21']), deepcopy(actual['jobs']['p21'])
        for job in (old_job, new_job):
            job.pop('steps');job.pop('name');job.pop('if', None);job['env'].pop('AUDITOR_UI_MODE', None)
        self.assertEqual(old_job, new_job)
        for key in ('permissions',):self.assertEqual(actual[key], original[key])

    def test_seven_exact_selections_reverse_to_full_original_engine(self):
        raw = (ROOT / 'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        text, proof = derive.derive(raw)
        self.assertEqual(proof['counted_changes'], 7)
        compile(text, 'private-browser-engine-no-execution', 'exec')
        for before, after in reversed(derive.REPLACEMENTS):
            self.assertEqual(text.count(after), 1)
            text = text.replace(after, before, 1)
        self.assertEqual(text.encode(), raw)

    def test_zero_browser_outer_count_cannot_survive_derivation(self):
        raw = (ROOT / 'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        text, _ = derive.derive(raw)
        self.assertIn("report['actual_browser_cases']=cases[runner.CASE]['actual_browser_cases']", text)
        self.assertIn("report['actual_business_cases']=4\n            report['real_Auth_browser_claim']=True", text)
        self.assertNotIn("report['actual_Native_cases']=14", text)

    def test_missing_or_duplicate_anchor_is_refused(self):
        raw = (ROOT / 'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        anchor = derive.REPLACEMENTS[0][0].encode()
        for value in (raw.replace(anchor, b'', 1), raw + anchor):
            with self.assertRaisesRegex(ValueError, 'EXACT_VENDOR_ANCHOR_REQUIRED'):
                derive.derive(value)

    def test_fixtures_and_callbacks_close_before_any_db_or_get(self):
        fixture = ast.parse((HERE / 'fixture.py').read_text())
        runtime = next(n for n in fixture.body if isinstance(n, ast.FunctionDef) and n.name == 'runtime')
        self.assertIn('.admitted()', ast.unparse(runtime.body[0]))
        component = ast.parse((HERE / 'component.py').read_text())
        exercise = next(n for n in component.body if isinstance(n, ast.FunctionDef) and n.name == 'exercise')
        self.assertIn('.admitted()', ast.unparse(exercise.body[0]))
        source = (HERE / 'cases.mjs').read_text()
        self.assertIn("export async function cases(ui,today){return planned(ui,today,()=>fixture('admit'))}", source)
        self.assertIn('export async function planned(ui,today,admit){await admit();return', source)
        for forbidden in ('page.routeFromHAR', 'setSession(', 'session_replication_role', 'INSERT INTO erp.journal_entries'):
            self.assertNotIn(forbidden, source)

    def test_native_setup_retains_raw_acl_and_complete22_assertions(self):
        source = (HERE / 'fixture.py').read_text()
        self.assertIn("select nspacl::text from pg_namespace", source)
        self.assertIn('S03_BROWSER4_FIXTURE_RAW_SCHEMA_ACL_CHANGED', source)
        self.assertIn('S03_BROWSER4_FIXTURE_ALL22_CHANGED', source)
        self.assertIn('S03_BROWSER4_FIRST_EVIDENCE_MUST_NOT_BE_OVERWRITTEN', source)
        self.assertNotIn('setval(', source)
        self.assertNotIn('session_replication_role', source)

    def test_browser_terminal_positive_is_parser_double_not_execution(self):
        report, package = browser_double()
        result = gate.checked(report, package)
        self.assertEqual(result['qualified_actual_browser_cases'], 4)
        self.assertEqual((result['actual_Native_cases'], result['actual_Auth_HTTP_cases'], result['actual_two_session_races']), (0, 0, 0))

    def test_terminal_counts_are_typed_and_never_fold_retained_native14(self):
        for key, value in (('actual_browser_cases', True), ('actual_browser_cases', 4.0),
                ('actual_Native_cases', 14), ('actual_Auth_HTTP_cases', 1), ('actual_two_session_races', 1)):
            report, package = browser_double();report[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                gate.checked(report, package)

    def test_each_browser_id_full_restore_auth_cleanup_and_full22_copy_are_mandatory(self):
        for mutation in ('missing_id', 'restore', 'cleanup', 'auth', 'console', 'copy', 'package', 'host_original'):
            report, package = browser_double()
            component = report['committed'][gate.CASE]
            if mutation == 'missing_id':component['browser']['cases'].pop(gate.IDS[0])
            elif mutation == 'restore':report['baseline_full22_all_rows_all_sequences_equal'] = False
            elif mutation == 'cleanup':component['browser']['database_remaining'] = 1
            elif mutation == 'auth':component['browser']['auth_counts']['restored'] = False
            elif mutation == 'console':component['browser']['console_errors'] = 1
            elif mutation == 'copy':component['copy_catalog_admissions'][0]['all22_groups_equal_original_install'] = False
            elif mutation == 'host_original':component['actual_browser_host_originals'] = []
            else:package['gate']['writer_runtime'] = False
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                gate.checked(report, package)

    def test_terminal_requires_strict390_no_one_px_waiver_real_proof_and_contrast45(self):
        for mutation in ('one_px', 'too_low', 'nan', 'no_measurement', 'private_console', 'native_credit', 'missing_auth_proof'):
            report, package = browser_double();row = report['committed'][gate.CASE]['browser']['cases'][gate.IDS[1]]
            if mutation == 'one_px':row['contrasts'][0]['width']['page'] = 391
            elif mutation == 'too_low':row['contrasts'][0]['measured'][0]['ratio'] = 4.49
            elif mutation == 'nan':row['contrasts'][0]['measured'][0]['ratio'] = float('nan')
            elif mutation == 'no_measurement':row['contrasts'] = []
            elif mutation == 'private_console':row['console_evidence']['unexpected'] = ['error-double']
            elif mutation == 'native_credit':row['actual_Native_cases'] = 1
            else:row['actual_normal_App_real_Auth_public_RPC'] = False
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):gate.checked(report, package)

    def test_host_original_digest_and_case_objects_are_checked_using_explicit_tempfile_double(self):
        report, _ = browser_double();component = report['committed'][gate.CASE]
        host = dict(classification='EXPLICIT_LOCAL_TEMPFILE_DOUBLE_NOT_BROWSER_EVIDENCE',
            phase='S03_CHOICE_MOUNTED4', ui_mode='DISPOSABLE', status='RUN_COMPLETE', planned=list(gate.IDS),
            cases=deepcopy(component['browser']['cases']), real_auth=True, product_responses_mocked=False,
            blocked_requests=0, auth_cleanup_failures=[], console_errors=[])
        with tempfile.TemporaryDirectory(prefix='s03-browser4-parser-double-') as directory:
            root = Path(directory);folder = root / 'cp6-proof/t3';folder.mkdir(parents=True)
            name = 'S03_BROWSER4_HOST_ORIGINAL_cp6-auditor-browser-EXPLICIT_DOUBLE.json.gz'
            def put(value):
                raw = json.dumps(value).encode();packed = gzip.compress(raw, mtime=0);(folder / name).write_bytes(packed)
                component['actual_browser_host_originals'] = [dict(name=name, raw_bytes=len(raw), raw_sha256=sha256(raw).hexdigest(),
                    gzip_bytes=len(packed), gzip_sha256=sha256(packed).hexdigest())]
            put(host)
            self.assertEqual(gate.host_originals(root, component), {'retained_actual_host_originals': 1, 'exact_final_host_cases_equal': True})
            (folder / name).write_bytes(gzip.compress(b'{}', mtime=0))
            with self.assertRaisesRegex(ValueError, 'ORIGINAL_BYTES_CHANGED'):gate.host_originals(root, component)
            different = deepcopy(host);different['cases'][gate.IDS[0]]['classification'] = 'CHANGED_DOUBLE';put(different)
            with self.assertRaisesRegex(ValueError, 'EXACT_FINAL_HOST_ORIGINAL_REQUIRED'):gate.host_originals(root, component)

    def test_independent_dated_source_oracle_retains_both_axes_and_later_inverse(self):
        fixture = load('fixture')
        first, later = date(2026, 10, 1), date(2026, 10, 30)
        data = [[('line-double', Decimal('1000.03'), first, first)], [(-100003, first, first)], [(100003, later, later)], [], []]
        class Cursor:
            def execute(self, query, args):self.rows = data.pop(0);return self
            def fetchall(self):return self.rows
        result = fixture.dated_wip(Cursor(), {'payroll': 'payroll-double'}, None)
        self.assertEqual({row['axis'] for row in result}, {'ECONOMIC', 'BOOK'})
        self.assertEqual({(row['date'], row['available_cents']) for row in result}, {('2026-10-01', '0'), ('2026-10-30', '100003')})

    def test_independent_dated_source_oracle_refuses_either_axis_before_original(self):
        fixture = load('fixture')
        first, later = date(2026, 10, 1), date(2026, 10, 2)
        for economic, book in ((later, first), (first, later)):
            data = [[('line-double', Decimal('1000.03'), economic, book)], [(-100003, first, first)], [], [], []]
            class Cursor:
                def execute(self, query, args):self.rows = data.pop(0);return self
                def fetchall(self):return self.rows
            with self.subTest(economic=economic, book=book), self.assertRaisesRegex(ValueError, 'NEGATIVE_DATED_SOURCE_WIP'):
                fixture.dated_wip(Cursor(), {'payroll': 'payroll-double'}, None)


if __name__ == '__main__':
    unittest.main(verbosity=2)
