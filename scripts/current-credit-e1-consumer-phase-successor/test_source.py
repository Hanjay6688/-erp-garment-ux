"""Offline countercontrols. No actual DB/Native/network or public authority."""
from pathlib import Path
from hashlib import sha256
import ast, importlib.util, json, re, socket, subprocess, sys, tempfile, unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('e_phase_closed_source_check', HERE/'check.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class SourceControls(unittest.TestCase):
    def test_exact_two_leaf_derivation_and_no_other_profile_changes(self):
        result = check.derivation()
        self.assertEqual(result['graph_ABI_substitutions'], 3)
        self.assertEqual(result['new_private_functions'], 1)
        self.assertTrue(result['all_other_profile_bodies_exact'])

    def test_existing_installer_discovers_exact_private_stable_helper(self):
        path = check.ROOT/'scripts/cp7_credit_correction_de/e_composition.py'
        tree = ast.parse(path.read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'sql_functions')
        values = {'HERE': path.parent, 'SQL': tuple('note_carry/'+name for name in
                  ('01_facts.sql', '02_plan.sql', '03_readers.sql', '04_basis.sql',
                   '05_effect.sql', '06_owning.sql', '07_profile_closure.sql')), 're': re}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), values)
        catalog = values['sql_functions']()
        self.assertEqual(len(catalog), 38)
        self.assertEqual(catalog['cp7_credit_note_carry_de.consumer_status_refresh_allowed_v1(uuid,jsonb,text)'], (True, 's'))
        self.assertEqual(len(catalog)+3, 41)  # Same three private Native copies.

    def test_closed_gate_before_database_network_or_product_import(self):
        cfg = json.loads((HERE/'CONFIG.json').read_bytes())
        with patch.object(socket, 'socket', side_effect=AssertionError('NETWORK_FORBIDDEN')):
            with self.assertRaisesRegex(ValueError, 'E_PHASE_FRESH_NATIVE17_NOT_QUALIFIED'):
                check.require_execution(cfg)
        self.assertFalse(any(n.startswith(('psycopg', 'asyncpg', 'cp7_credit_correction_de')) for n in sys.modules))

    def test_binding_a_pass_does_not_invent_a_runner(self):
        cfg = json.loads((HERE/'CONFIG.json').read_bytes())
        cfg['accepted_native17'] = {'status': 'PASS'}
        with self.assertRaisesRegex(ValueError, 'E_PHASE_ROOT_NEW_QUALIFIER_REQUIRED'):
            check.require_execution(cfg)

    def test_relative_path_and_regular_file_contract(self):
        with tempfile.TemporaryDirectory(prefix='ephase-regular-') as temporary:
            root = Path(temporary)
            (root/'source.sql').write_text('select 1;')
            self.assertEqual(check.regular(root, 'source.sql'), root/'source.sql')
            for name in ('../source.sql', '/source.sql', 'a/../source.sql'):
                with self.assertRaisesRegex(ValueError, 'INVALID_RELATIVE_SOURCE'):
                    check.regular(root, name)

    def test_same_bytes_symlink_leaf_is_not_a_source(self):
        with tempfile.TemporaryDirectory(prefix='ephase-leaf-') as temporary:
            root = Path(temporary)
            (root/'real').write_text('same bytes')
            (root/'source').symlink_to(root/'real')
            with self.assertRaisesRegex(ValueError, 'SOURCE_SYMLINK'):
                check.regular(root, 'source')

    def test_symlink_ancestor_is_not_a_source(self):
        with tempfile.TemporaryDirectory(prefix='ephase-parent-') as temporary:
            root = Path(temporary)
            (root/'real').mkdir()
            (root/'real/source').write_text('same bytes')
            (root/'linked').symlink_to(root/'real', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'SOURCE_SYMLINK'):
                check.regular(root, 'linked/source')

    def test_real_whole_caller_rejects_unknown_source_and_postrestore_passes(self):
        target = HERE/'UNDECLARED_SOURCE_COUNTER.py'
        self.assertFalse(target.exists())
        try:
            target.write_text('raise RuntimeError("must never import unknown source")\n')
            with self.assertRaisesRegex(ValueError, 'UNKNOWN_SOURCE_OR_RECEIPT'):
                check.check()
        finally:
            target.unlink(missing_ok=True)
        self.assertEqual(check.check()['status'], 'CLOSED_EXACT_PUBLIC_SOURCE_TRANSITION_ONLY')

    def test_real_whole_caller_rejects_known_leaf_symlink_and_restores(self):
        target = HERE/'CONFIG.json'
        raw, mode = target.read_bytes(), target.stat().st_mode
        with tempfile.TemporaryDirectory(prefix='ephase-known-leaf-', dir=check.ROOT.parent) as temporary:
            donor = Path(temporary)/'same-config.json'
            donor.write_bytes(raw)
            try:
                target.unlink()
                target.symlink_to(donor)
                with self.assertRaisesRegex(ValueError, 'SOURCE_SYMLINK'):
                    check.check()
            finally:
                target.unlink(missing_ok=True)
                target.write_bytes(raw)
                target.chmod(mode)
        self.assertEqual(sha256(target.read_bytes()).hexdigest(), sha256(raw).hexdigest())
        self.assertEqual(check.check()['status'], 'CLOSED_EXACT_PUBLIC_SOURCE_TRANSITION_ONLY')

    def test_real_whole_caller_rejects_ancestor_symlink_and_restores(self):
        target = HERE/'evidence/retained_8be4'
        with tempfile.TemporaryDirectory(prefix='ephase-known-parent-', dir=check.ROOT.parent) as temporary:
            donor = Path(temporary)/'retained_8be4'
            target.rename(donor)
            try:
                target.symlink_to(donor, target_is_directory=True)
                with self.assertRaisesRegex(ValueError, 'SOURCE_SYMLINK'):
                    check.check()
            finally:
                target.unlink(missing_ok=True)
                donor.rename(target)
        self.assertEqual(check.check()['status'], 'CLOSED_EXACT_PUBLIC_SOURCE_TRANSITION_ONLY')

    def test_cli_unknown_flag_stays_refused(self):
        result = subprocess.run([sys.executable, '-B', str(HERE/'check.py'), '--unknown'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('unrecognized arguments', result.stderr)

    def test_cli_runtime_is_closed_before_product_import(self):
        result = subprocess.run([sys.executable, '-B', str(HERE/'check.py'), '--runtime'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('E_PHASE_FRESH_NATIVE17_NOT_QUALIFIED', result.stderr)
        self.assertNotIn('psycopg', result.stderr)


if __name__ == '__main__':
    unittest.main()
