"""Source/phase mutation controls only; synthetic doubles receive no ERP credit."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
import ast
import importlib.util
import json
import unittest
import yaml

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


a = load('census_successor_control_admission', 'admission.py')
d = load('census_successor_control_deriver', 'derive.py')
w = load('census_successor_control_workflow', 'workflow.py')
p = load('census_successor_control_profiles', 'producer_profiles.py')


class SourceControls(unittest.TestCase):
    def test_actual_whole_parent_source_and_additive_seal(self):
        proof = a.preflight(require_clean=False)
        self.assertEqual(proof['parent_files'], 13892)
        self.assertFalse(proof['old_frozen_guards_edited'])
        self.assertIsNone(proof['runtime_entry'])

    def test_public_helper_tree_and_canonical_bce_are_unchanged(self):
        self.assertEqual(a.git('rev-parse', a.BASE + '^{tree}').decode().strip(), a.BASE_TREE)
        names = a.git('diff', '--name-only', a.BCE, a.BASE).decode().splitlines()
        self.assertEqual(len(names), 16)
        self.assertTrue(all(name.startswith(a.HELPER) for name in names))

    def test_source_mode_and_same_byte_symlink_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory); path = root / 'scope/code.py'; path.parent.mkdir(); path.write_bytes(b'exact\n')
            expected = dict(a.pin(path.read_bytes()), mode='100644')
            a.checked('scope/code.py', expected, root)
            path.chmod(0o755)
            with self.assertRaisesRegex(ValueError, 'MODE_CHANGED'): a.checked('scope/code.py', expected, root)
            path.chmod(0o644); path.parent.rename(root / 'moved'); (root / 'scope').symlink_to(root / 'moved', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'SOURCE_LINK'): a.checked('scope/code.py', expected, root)

    def test_source_mutated_bytes_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory); path = root / 'code.py'; path.write_bytes(b'original\n')
            expected = dict(a.pin(path.read_bytes()), mode='100644'); path.write_bytes(b'changed\n')
            with self.assertRaisesRegex(ValueError, 'BYTES_CHANGED'): a.checked('code.py', expected, root)

    def test_malformed_paths_and_duplicate_keys_refused(self):
        for name in (None, 1, '', '../code.py', '/code.py', './code.py', 'a\\b.py'):
            with self.subTest(name=name), self.assertRaises(ValueError): a.regular(name)
        for raw in ('{"credit":0,"credit":false}', '{"credit":NaN}'):
            with self.assertRaises(ValueError): a.document(raw)

    def test_unknown_output_rejected_before_old_reader_import(self):
        with patch.object(a, 'load', side_effect=AssertionError('old module imported')):
            with self.assertRaisesRegex(ValueError, 'UNKNOWN_UNTRACKED_SOURCE_BEFORE_IMPORT'):
                a.outputs({'scripts/new_unreviewed_writer.py'})

    def test_known_output_symlink_refused_before_old_reader_import(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('scripts/current-workflow-history-isolation/ARCHIVE.json', a.NS + 'SKU_GENERATED_RECEIPTS.json'):
                target = root / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes((ROOT / name).read_bytes())
            actual = root / 'source'; actual.write_text('{}')
            link = root / 'cp6-proof/t3/T3_PACKAGE_INSTALL.json'; link.parent.mkdir(parents=True); link.symlink_to(actual)
            with patch.object(a, 'load', side_effect=AssertionError('old module imported')):
                with self.assertRaisesRegex(ValueError, 'SOURCE_LINK'): a.outputs({str(link.relative_to(root))}, root)

    def test_credit_boolean_or_promoted_flags_rejected_before_parent_reads(self):
        cfg = a.document((HERE / 'SOURCE.json').read_bytes())
        for key, values in {'actual_Native_credit': (False, True, 1, '0'), 'production_go': (True, 0, None),
                            'independent_acceptance': (True, 0, None), 'runtime_entry': ('open',)}.items():
            for value in values:
                bad = deepcopy(cfg); bad[key] = value
                with self.subTest(key=key, value=value), patch.object(a, 'document', return_value=bad), \
                     patch.object(a, 'immutable_parent', side_effect=AssertionError('parent traversal reached')):
                    with self.assertRaisesRegex(ValueError, 'METADATA_ONLY_SOURCE_REQUIRED'): a.preflight(require_clean=False)

    def test_full_parent_bytes_are_verified_before_old_or_profile_imports(self):
        with patch.object(a, 'immutable_parent', side_effect=ValueError('immutable parent mutation')), \
             patch.object(a, 'load', side_effect=AssertionError('import before immutable parent')):
            with self.assertRaisesRegex(ValueError, 'immutable parent mutation'): a.preflight(require_clean=False)

    def test_explicit_producer_transition_preserves_all_other_policy(self):
        raw = (ROOT / w.NEW).read_bytes()
        for filename in p.FILES:
            old = a.document((ROOT / p.PARENT / filename).read_bytes()); new = p.derive(old, filename, raw)
            self.assertEqual(new['producer_files'].pop(p.WORKFLOW), a.pin(raw))
            if filename == 'LATER_GENERATED_RECEIPTS.json':
                self.assertEqual(new['package_workflow_name'], p.NAME); new['package_workflow_name'] = old['package_workflow_name']
            self.assertEqual(new, old)


class DerivationControls(unittest.TestCase):
    def test_complete_outer_restore_and_stream_guard_unchanged(self):
        text, proof = d.engine(); old = (ROOT / d.OLD).read_text()
        start = '    finally:\n        if before is not None and pre_dumped:'; end = "        cases=report['committed']"
        self.assertEqual(text[text.index(start):text.index(end)], old[old.index(start):old.index(end)])
        start = '\ndef run():\n'; end = "\n\nif __name__=='__main__':"
        self.assertEqual(text[text.index(start):text.index(end)], old[old.index(start):old.index(end)])
        self.assertEqual(proof['successor']['counted_changes'], 4)
        self.assertIn('conn.commit();installed=True', text)
        self.assertIn('FIRST_FINANCE_DELTA', text); self.assertIn('FINANCE_DELTA_PREUSE_INVERSE', text)
        self.assertIn('SECOND_FINANCE_DELTA', text)
        self.assertEqual(text.count("report['actual_Native_cases']=0"), 1)

    def test_runner_first_sql_and_bracket_keep_old_snapshots(self):
        text, proof = d.runner()
        self.assertEqual(proof['successor']['counted_changes'], 4)
        self.assertLess(text.index('begin_readonly(conn,cur)'), text.index("cur.execute('select current_database()')"))
        self.assertLess(text.index('require_current_preuse(before,state)'), text.index('census_capture.capture('))
        self.assertLess(text.index('census_capture.capture('), text.index('after=dict(catalog='))
        self.assertLess(text.index('if before!=after:'), text.index('census_integration.finish('))
        self.assertIn("report['read_before']=before", text)
        self.assertIn('actual_layer_catalogues=state[\'installed_layer_catalogues\']', text)
        self.assertNotIn("census_integration=load('global_actual_census_integration',", text)

    def test_counted_derivation_rejects_changed_or_ambiguous_anchors(self):
        for source in ('unknown', 'anchor anchor'):
            with self.assertRaisesRegex(ValueError, 'ANCHOR_CHANGED'): d.replace_exact(source, (('anchor', 'successor'),), 'test')

    def test_integration_only_one_reversible_sql_representation_fix(self):
        text, proof = d.integration(); old = (ROOT / d.HELPER / 'integration.py').read_text()
        self.assertEqual(proof['counted_changes'], 1)
        self.assertEqual(text.replace("SELECT pg_catalog.set_config('search_path','',true)", "SET LOCAL search_path = ''"), old)

    def test_exact_derived_readonly_first_statement_and_correct_empty_path(self):
        text, _ = d.integration(); module = ModuleType('local_transaction_double')
        module.__file__ = str(ROOT / d.HELPER / 'integration.py'); exec(compile(text, module.__file__, 'exec'), module.__dict__)
        conn = SimpleNamespace(autocommit=False, info=SimpleNamespace(host='127.0.0.1', port=54322,
            transaction_status=module.TransactionStatus.IDLE)); calls = []
        class Cursor:
            connection = conn
            def execute(self, sql): calls.append(sql); return self
            def fetchone(self): return ('cp6_rollback', 'postgres', 'on', 'read committed', '', 'UTC')
        result = module.begin_readonly(conn, Cursor())
        self.assertEqual(calls[:3], ['SET TRANSACTION ISOLATION LEVEL READ COMMITTED READ ONLY',
            "SELECT pg_catalog.set_config('search_path','',true)", "SET LOCAL TimeZone = 'UTC'"])
        self.assertFalse(result['transaction_writes'])
        conn.info.transaction_status = module.TransactionStatus.INTRANS; calls.clear()
        with self.assertRaisesRegex(ValueError, 'FRESH_NONAUTOCOMMIT'): module.begin_readonly(conn, Cursor())
        self.assertEqual(calls, [])

    def test_full_inherited_gate_keeps_all5_and_all22_and_requires_original(self):
        text, proof = d.gate()
        self.assertEqual(proof['successor']['counted_changes'], 5)
        for anchor in ('DE_SKU_COMPLETE_ALL5_REQUIRED','DE_SKU_COMPLETE_OUTER_REQUIRED:',
                       'DE_SKU_ACTUAL_CATALOGUE_ROWS_SEQUENCES_CHANGED','DE_SKU_COMPLETE22_CATALOGUE_GROUPS_REQUIRED',
                       'DE_SKU_COMPLETE_EFFECTIVE_ROLE_PRIVILEGE_MATRIX_REQUIRED','census_integration.validate_case(case,'):
            self.assertIn(anchor, text)
        self.assertIn('original_directory=args.directory', text)

    def test_gate_metadata_credit_and_closed_flags_cannot_use_python_bool_equality(self):
        text, _ = d.gate()
        # Evaluate only the new early gate preconditions. Deliberately stop
        # before every inherited actual-catalogue requirement; no mock PASS.
        tree = ast.parse(text); fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'checked')
        prefix = fn.body[:7]
        self.assertEqual(len(prefix), 7)
        case = dict(production_go=False, independent_acceptance=False, used_guard_business_witness_executed=False,
            global_bridge_installed=False, S03_S05_installed=False, actual_business_cases=0, actual_Native_cases=0,
            actual_Auth_HTTP_cases=0, actual_browser_cases=0)
        report = dict(production_go=False, independent_acceptance=False, actual_catalogue_qualification_groups=1, committed={d.CASE:case})
        package = dict(production_go=False, release_evidence=False, auth_users_before=0, auth_users_after=0)
        def require(ok, message):
            if not ok: raise ValueError(message)
        def run(r, p):
            exec(compile(ast.Module(body=prefix, type_ignores=[]), '<gate-prefix-only-no-qualification>', 'exec'),
                 dict(report=r, package=p, CASE=d.CASE, require=require))
        run(report, package)
        for key in ('production_go', 'independent_acceptance'):
            bad = deepcopy(report); bad[key] = 0
            with self.assertRaisesRegex(ValueError, 'CLOSED_FLAGS'): run(bad, package)
        bad = deepcopy(report); bad['actual_catalogue_qualification_groups'] = True
        with self.assertRaisesRegex(ValueError, 'TYPED_METADATA_GROUP'): run(bad, package)
        for key in ('auth_users_before', 'auth_users_after'):
            bad = deepcopy(package); bad[key] = False
            with self.assertRaisesRegex(ValueError, 'TYPED_AUTH_ZERO'): run(report, bad)
        for key in ('actual_business_cases','actual_Native_cases','actual_Auth_HTTP_cases','actual_browser_cases'):
            bad = deepcopy(report); bad['committed'][d.CASE][key] = False
            with self.assertRaisesRegex(ValueError, 'CASE_TYPED_ZERO'): run(bad, package)


class WorkflowControls(unittest.TestCase):
    def test_exact_workflow_and_first_admission_precedes_old_imports(self):
        old = yaml.safe_load((ROOT / w.OLD).read_bytes()); new = yaml.safe_load((ROOT / w.NEW).read_bytes())
        self.assertEqual(new, w.derive(old)); self.assertEqual(len(new['jobs']['p21']['steps']), 72)
        steps = new['jobs']['p21']['steps']; self.assertEqual(steps[0], old['jobs']['p21']['steps'][0])
        self.assertEqual(steps[1]['run'], 'python3 -B ' + w.NS + '/check.py')
        self.assertEqual(steps[2], old['jobs']['p21']['steps'][1])
        self.assertEqual(new['permissions'], old['permissions'])
        self.assertFalse(new['concurrency']['cancel-in-progress'])

    def test_disposable_source_checkout_product_refs_and_restoration_steps_unchanged(self):
        old = yaml.safe_load((ROOT / w.OLD).read_bytes()); new = w.derive(old)
        changed = {step['name'] for step in new['jobs']['p21']['steps'] if step not in old['jobs']['p21']['steps'] and 'name' in step}
        self.assertEqual(len(changed), 7)
        for step in old['jobs']['p21']['steps']:
            if step.get('name') in ('Select exact qualified prerequisite heads','Materialize every exact frozen source from one full checkout',
                'Start disposable database','Rebuild to v2.6.20, align with hosted, continue the frozen path to AB',
                'Provision isolated rollback authority','Clone the aligned AB state for install','Remove disposable database'):
                self.assertIn(step, new['jobs']['p21']['steps'])

    def test_new_metadata_original_never_stdout_and_always_artifact_retained(self):
        value = yaml.safe_load((ROOT / w.NEW).read_bytes()); steps = value['jobs']['p21']['steps']
        retention = next(step for step in steps if step.get('name', '').startswith('Retain exact Original byte identities'))
        self.assertEqual(retention['run'], 'python -B ' + w.NS + '/retain.py')
        self.assertNotIn('base64', (HERE / 'retain.py').read_text())
        artifact = steps[-1]; self.assertEqual(artifact['if'], 'always()')
        self.assertIn('auditor/cp6-proof/t3', artifact['with']['path'])
        runtime = next(step for step in steps if '--metadata-runtime' in step.get('run', ''))
        self.assertEqual(runtime['working-directory'], 'writer')

    def test_probe_early_admission_precedes_first_old_source_context_import(self):
        tree = ast.parse((HERE / 'probe.py').read_bytes()); main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        code = ast.unparse(main)
        self.assertLess(code.index('early()'), code.index('source_context.py'))
        self.assertNotIn("'--runtime'", (HERE / 'probe.py').read_text())

    def test_original_retention_preserves_bytes_and_partial_failure(self):
        retain = load('global_census_control_retention', 'retain.py')
        with TemporaryDirectory() as directory:
            path = Path(directory) / retain.NAMES[1]; raw = b'{"sensitive-metadata-body":"retained only"}\n'; path.write_bytes(raw)
            value = retain.retain(directory)
            self.assertEqual(value['files'][path.name], a.pin(raw)); self.assertEqual(path.read_bytes(), raw)
            self.assertTrue(value['missing_required']); self.assertFalse(value['metadata_or_data_bodies_printed'])
            path.unlink(); path.symlink_to(HERE / 'admission.py')
            with self.assertRaisesRegex(ValueError, 'SYMLINK'): retain.retain(directory)


if __name__ == '__main__': unittest.main()
