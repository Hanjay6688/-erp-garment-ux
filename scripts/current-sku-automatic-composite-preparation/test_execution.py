"""Local Git/filesystem execution controls; no accepted Root or ERP execution."""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util
import json
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('automatic_execution_control_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


execution = load('execution')
workflow = load('workflow')


class ExecutionControls(unittest.TestCase):
    def test_closed_real_gates_precede_every_financial_helper_derivation(self):
        for kind in execution.PINS:
            with self.subTest(kind=kind), patch.object(execution, 'derive') as derive:
                with self.assertRaisesRegex(ValueError, 'CURRENT_PARENT_AND_FULL_NATIVE_LIFECYCLE_PENDING'):
                    execution.helper(kind, admitted=True)
                derive.assert_not_called()
        self.assertTrue(all(getattr(execution.runtime.admission, key) is None
                            for key in execution.runtime.admission.GATES))

    def test_all_retained_helpers_recover_exact_bytes_and_refuse_mutation(self):
        for kind in execution.PINS:
            with self.subTest(kind=kind):
                text, proof = execution.derive(kind)
                self.assertTrue(proof['complete_original_recovered'])
                self.assertEqual(proof['actual_ERP_cases'], 0)
                with self.assertRaisesRegex(ValueError, 'EXACT_RETAINED_EXECUTION_HELPER_REQUIRED'):
                    execution.derive(kind, text.encode())
        fetch, _ = execution.helper('fetch')
        _, proof = fetch.derive('MANDOR')
        self.assertTrue(proof['terminal_run_job_attempt_head_archive_SHA_size_CRC_and_paths_unchanged'])
        self.assertEqual(set(fetch.KINDS), {'MANDOR'})
        supervisor, _ = execution.helper('supervisor')
        text, proof = supervisor.derive()
        self.assertTrue(proof['real_360_330_20_10_budgets_unchanged'])
        self.assertIn("str(HERE/'qualification.py')", text)
        self.assertIn('SKU_CURRENT_PARENT_MONEY_AUTOMATIC_RUNTIME_SUPERVISION.json', text)
        self.assertIn('SKU_CURRENT_AUTOMATIC_JOB_START_MONOTONIC', text)
        self.assertNotIn('money_current_parent_runtime.py', text)

    def test_fourth_real_worktree_refuses_dirty_wrong_identity_and_symlink(self):
        module, _ = execution.helper('materialize')
        with TemporaryDirectory() as directory:
            root = Path(directory) / 'own';root.mkdir()
            def git(*args):
                return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE).decode().strip()
            git('init', '--quiet')
            (root / 'explicit_local_source_model.txt').write_text('No ERP acceptance\n')
            git('add', '.')
            git('-c', 'user.name=Local source control', '-c', 'user.email=source-control@example.invalid',
                'commit', '--quiet', '-m', 'Explicit local worktree model')
            head, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
            module.ROOT = root
            result = module.one('qualified-sku-automatic', head, tree)
            self.assertTrue(result['created']);self.assertEqual(result['git_fetches'], 0)
            self.assertFalse(module.one('qualified-sku-automatic', head, tree)['created'])
            automatic = root.parent / 'qualified-sku-automatic'
            (automatic / 'explicit_local_source_model.txt').write_text('changed\n')
            with self.assertRaisesRegex(ValueError, 'FROZEN_SOURCE_CHANGED'):
                module.one('qualified-sku-automatic', head, tree)
            with self.assertRaisesRegex(ValueError, 'EXACT_ACCEPTED_COMMIT_AND_TREE_REQUIRED'):
                module.one('qualified-sku-automatic', head, '0' * 40)
            (root.parent / 'qualified-sku-money').symlink_to(automatic, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'FIXED_REGULAR_WORKTREE_PATH'):
                module.one('qualified-sku-money', head, tree)
            with self.assertRaisesRegex(ValueError, 'FIXED_REGULAR_WORKTREE_PATH'):
                module.one('arbitrary-output', head, tree)

    def test_four_tree_retention_streams_full_originals_and_preserves_conflict(self):
        module, _ = execution.helper('artifacts')
        exact_file_helpers = module.helpers()
        module.helpers = lambda: exact_file_helpers
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            own = root / 'own/cp6-proof/t3';own.mkdir(parents=True)
            module.ROOT = root / 'own';module.OWN = own
            module.MANIFEST = own / 'MODEL_PREREQUISITES.json'
            module.RETAINED = own / 'MODEL_FROZEN_EXECUTION'
            module.runtime = SimpleNamespace(actual_inputs=lambda: ('explicit local model only',))
            original = (b'complete original bytes, including non-JSON output\x00' * 70000)
            (own / 'source.bin').write_bytes(original)
            for folder in module.FOLDERS:
                (root / folder).mkdir()
            report = module.prepare()
            self.assertEqual(report['frozen_trees'], 4)
            for index, folder in enumerate(module.FOLDERS):
                parent = root / folder / 'cp6-proof/t3'
                self.assertEqual(sha256((parent / 'source.bin').read_bytes()).digest(), sha256(original).digest())
                nested = parent / 'COMPLETE_CASE_STDOUT';nested.mkdir()
                (nested / 'first.jsonl').write_bytes(original + str(index).encode())
            target = module.RETAINED / module.FOLDERS[-1] / 'COMPLETE_CASE_STDOUT/first.jsonl'
            target.parent.mkdir(parents=True);target.write_bytes(b'first conflicting output must survive')
            original_read = Path.read_bytes
            def bounded_read(path):
                if path.name in ('source.bin', 'first.jsonl'):
                    raise AssertionError('Full Original must use streamed hashes/copies')
                return original_read(path)
            with patch.object(Path, 'read_bytes', bounded_read):
                with self.assertRaisesRegex(ValueError, 'EXISTING_BYTES_CONFLICT'):
                    module.retain()
            self.assertEqual(target.read_bytes(), b'first conflicting output must survive')
            self.assertFalse((own / 'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_FROZEN_EXECUTION_RECEIPT.json').exists())
            # This is an explicit local model. Removing only its deliberately
            # conflicting fixture lets the unchanged retention code finish.
            target.unlink()
            with patch.object(Path, 'read_bytes', bounded_read):
                result = module.retain()
            self.assertEqual(result['retained_files'], 4)
            self.assertEqual(result['missing_baseline_files'], 0)
            for index, folder in enumerate(module.FOLDERS):
                saved = module.RETAINED / folder / 'COMPLETE_CASE_STDOUT/first.jsonl'
                self.assertEqual(saved.read_bytes(), original + str(index).encode())
            receipt = json.loads((own / 'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_FROZEN_EXECUTION_RECEIPT.json').read_bytes())
            self.assertFalse(receipt['JSON_or_row_projection'])
            self.assertFalse(receipt['files_overwritten'])

    def test_failed_admission_retention_still_works_and_symlinks_are_rejected(self):
        module, _ = execution.helper('artifacts')
        exact_file_helpers = module.helpers()
        module.helpers = lambda: exact_file_helpers
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            own = root / 'own/cp6-proof/t3';own.mkdir(parents=True)
            module.ROOT = root / 'own';module.OWN = own
            module.MANIFEST = own / 'MODEL_PREREQUISITES.json';module.RETAINED = own / 'MODEL_RETAINED'
            with patch.object(execution.runtime, 'actual_inputs', side_effect=AssertionError('Retention cannot require financial admission')):
                self.assertEqual(module.retain()['status'], 'CURRENT_PARENT_EXECUTION_NOT_PREPARED')
            module.runtime = SimpleNamespace(actual_inputs=lambda: ('explicit local model only',))
            (own / 'escape').symlink_to(root / 'outside')
            with self.assertRaisesRegex(ValueError, 'PATH_OR_SYMLINK'):
                module.prepare()

    def test_large_receipt_files_are_streamed_and_first_receipt_is_immutable(self):
        module, _ = execution.helper('receipts')
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            report = root / (execution.runtime.LABEL + '.json')
            data = b'full Original remains a file\n' * 120000
            report.write_bytes(data)
            original_read = Path.read_bytes
            def bounded_read(path):
                if path == report:
                    raise AssertionError('Receipt must hash the Original as a stream')
                return original_read(path)
            with patch.object(Path, 'read_bytes', bounded_read):
                receipt = module.receipts(root)
                self.assertEqual(module.receipts(root), receipt)
                self.assertEqual(receipt['originals'][report.name], dict(bytes=len(data), sha256=sha256(data).hexdigest()))
                self.assertEqual(receipt['actual_case_credit'], 0)
                report.write_bytes(data + b'changed')
                with self.assertRaisesRegex(ValueError, 'FIRST_RECEIPT_CHANGED'):
                    module.receipts(root)

    def test_argument_scope_restores_original_object_even_after_failure(self):
        original, contents = sys.argv, list(sys.argv)
        with self.assertRaisesRegex(RuntimeError, 'explicit local model'):
            with execution.arguments(['--allow-database-stop']):
                self.assertEqual(sys.argv[1:], ['--allow-database-stop'])
                raise RuntimeError('explicit local model')
        self.assertIs(sys.argv, original);self.assertEqual(sys.argv, contents)

    def test_reviewed_81_step_template_stays_inactive_and_accidental_activation_is_closed(self):
        text, proof = workflow.derive()
        self.assertEqual(text.encode(), workflow.TEMPLATE.read_bytes())
        self.assertEqual(proof['unchanged_steps'], 67)
        self.assertEqual(proof['total_steps'], 81)
        self.assertEqual(proof['retained_steps'], 79)
        self.assertEqual(proof['added_browser_prerequisite_steps'], 2)
        self.assertEqual(proof['frozen_source_trees'], 4)
        self.assertFalse(workflow.ACTIVE.exists())
        self.assertEqual(workflow.check()['workflow_dispatches'], 0)
        with TemporaryDirectory() as directory:
            model_root = Path(directory)
            active = model_root / workflow.ACTIVE.relative_to(workflow.ROOT)
            active.parent.mkdir(parents=True);active.write_text(text)
            with patch.object(workflow, 'ROOT', model_root), patch.object(workflow, 'ACTIVE', active):
                with self.assertRaisesRegex(ValueError, 'CURRENT_PARENT_AND_FULL_NATIVE_LIFECYCLE_PENDING'):
                    workflow.check()


if __name__ == '__main__':
    unittest.main()
