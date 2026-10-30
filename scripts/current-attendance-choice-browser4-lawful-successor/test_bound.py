"""Bound source/input controls. All models are local; Native/Auth/browser credit0."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import ast
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('s03_bound_control_' + name, HERE / (name + '.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


inputs, fetch = load('accepted_inputs'), load('fetch_originals')


class QualifiedSourceControls(unittest.TestCase):
    def test_all475_physical_routes_and_canonical_runtime_are_real_exact_bytes(self):
        cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
        receipt, raw = inputs.static(ROOT, HERE, cfg)
        self.assertEqual(len(raw), 6)
        self.assertEqual(receipt['head'], inputs.HEAD)
        physical = json.loads((HERE / 'QUALIFIED_SOURCE_INPUTS.json').read_bytes())
        self.assertEqual(len(physical['files']), 475)
        self.assertEqual(sum(row['kind'] == 'PROOF_ONLY_NOT_IMPORTED_AS_EXECUTING_BACKEND'
            for row in physical['files'].values()), 214)
        for name in [*cfg['backend_binding']['runtime_files'], inputs.BOOTSTRAP]:
            self.assertEqual(physical['files'][name]['physical_path'], name) if name in physical['files'] else None

    def test_old425_projection_missing_extra_or_changed_canonical_map_refuse(self):
        original = json.loads((HERE / 'CONFIG.json').read_bytes())
        for kind in ('old425', 'missing', 'extra', 'changed'):
            cfg = deepcopy(original); files = cfg['backend_binding']['full_current_qualifier_source_files']
            if kind == 'old425': cfg['backend_binding']['full_current_qualifier_source_files'] = dict(list(files.items())[:425])
            elif kind == 'missing': files.pop(next(iter(files)))
            elif kind == 'extra': files['scripts/unknown.py'] = {'bytes': 1, 'sha256': 'a' * 64}
            else: files[next(iter(files))]['sha256'] = 'a' * 64
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'COMPLETE475_CANONICAL_MAP_REQUIRED'):
                inputs.static(ROOT, HERE, cfg)

    def test_retained_proof_copy_cannot_substitute_executing_runtime(self):
        cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
        physical = json.loads((HERE / 'QUALIFIED_SOURCE_INPUTS.json').read_bytes())
        name = next(iter(cfg['backend_binding']['runtime_files']))
        physical['files'][name].update(kind='PROOF_ONLY_NOT_IMPORTED_AS_EXECUTING_BACKEND',
            physical_path=str(HERE.relative_to(ROOT)) + '/qualified-parent3c0/' + name)
        target = HERE / 'QUALIFIED_SOURCE_INPUTS.json'; read = Path.read_bytes
        with patch.object(Path, 'read_bytes', lambda path: json.dumps(physical).encode() if path == target else read(path)):
            with self.assertRaisesRegex(ValueError, 'PROOF_COPY_CANNOT_EXECUTE_AS_RUNTIME'):
                inputs.static(ROOT, HERE, cfg)

    def test_installer15_plus2_verify_is_before_copy_or_fixture(self):
        tree = ast.parse((HERE / 'component.py').read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'actual_browser')
        text = ast.unparse(function)
        self.assertLess(text.index('native_delta.patched'), text.index('product.verify'))
        self.assertLess(text.index('product.verify'), text.index('bridge = load'))
        self.assertIn('set(state[\'originals\']) != set(native_delta.SIGNATURES)', text)
        self.assertIn("state['clones'] != native_delta.clones(state['originals'])", text)

    def test_only_declared_preparation_changes_preserve_all_e09c_business_bytes(self):
        for relative in ('cases.mjs', 'fixture.py', 'test_oracles.mjs', 'test_lawful_oracles.mjs',
                'helper-source/lawful_fixture.py', 'helper-source/business.py', 'helper-source/CALLBACK_CHANGES.json'):
            name = str(HERE.relative_to(ROOT)) + '/' + relative
            expected = subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), 'show',
                'e09c6512932de81777e661275d18bb232b2d2ee3:' + name])
            current = (ROOT / name).read_bytes()
            changes = []
            if relative == 'cases.mjs':
                changes = [(b' let f,serial=0', b' let f=null,serial=0')]
            elif relative == 'fixture.py':
                changes = [
                    (b"        if scenario == 'MOBILE390':\n", b"        if scenario == 'MOBILE390':\n"
                     b"            # Select a vacant cohort before any posted fixture exists. Desktop\n"
                     b"            # payroll/choice history remains present and must never enter P2.\n"
                     b"            expected_output = f.quiet_days(cur, today, 1)[0]\n"
                     b"            f.hp.set_closed(cur, expected_output - timedelta(days=1))\n"),
                    (b"finish_fixture(cur, today, label='S03-BROWSER4-FINISHED')",
                     b"finish_fixture(cur, expected_output + timedelta(days=5), label='S03-BROWSER4-FINISHED')"),
                    (b'            if len(days) != 1:', b'            if days != [(expected_output,)]:')]
            for before, after in changes:
                self.assertEqual(expected.count(before), 1)
                self.assertEqual(current.count(after), 1)
                current = current.replace(after, before, 1)
            self.assertEqual(current, expected, name)


class ImmutableArtifactControls(unittest.TestCase):
    def metadata(self):
        run = dict(id=inputs.RUN, head_sha=inputs.HEAD, status='completed', conclusion='success', run_attempt=1,
            path='.github/workflows/cp7-s03-lawful-fixture-native14.yml')
        job = dict(id=inputs.JOB, run_id=inputs.RUN, head_sha=inputs.HEAD, status='completed', conclusion='success')
        artifact = dict(id=inputs.ARTIFACT, expired=False, name='cp7-a-s03-lawful-fixture-native14-1',
            workflow_run=dict(id=inputs.RUN, head_sha=inputs.HEAD), size_in_bytes=inputs.ARCHIVE['bytes'],
            digest='sha256:' + inputs.ARCHIVE['sha256'])
        return run, job, artifact

    def test_exact_fixed_metadata_is_only_transport_admission(self):
        self.assertIsNone(fetch.validate_metadata(*self.metadata()))
        self.assertEqual(fetch.REPO, 'repos/Hanjay6688/-erp-garment-ux')

    def test_wrong_run_attempt_head_job_workflow_artifact_size_digest_or_expiry_refuses(self):
        cases = ((0, 'id', 1), (0, 'head_sha', 'a' * 40), (0, 'run_attempt', 2),
            (0, 'path', 'different.yml'), (0, 'conclusion', 'failure'),
            (1, 'id', 1), (1, 'run_id', 1), (1, 'head_sha', 'a' * 40), (1, 'status', 'in_progress'),
            (2, 'id', 1), (2, 'name', 'other'), (2, 'expired', True),
            (2, 'size_in_bytes', inputs.ARCHIVE['bytes'] - 1), (2, 'digest', 'sha256:' + 'a' * 64),
            (2, 'workflow_run', dict(id=1, head_sha=inputs.HEAD)))
        for index, key, value in cases:
            metadata = self.metadata(); metadata[index][key] = value
            with self.subTest(index=index, key=key), self.assertRaisesRegex(ValueError, 'IMMUTABLE_RUN_JOB_ARTIFACT_METADATA_REQUIRED'):
                fetch.validate_metadata(*metadata)

    def test_wrong_archive_refuses_before_any_source_or_output_access(self):
        with patch.object(fetch.inputs, 'static', side_effect=AssertionError('NO_SOURCE_OR_OUTPUT_ACCESS')):
            with self.assertRaisesRegex(ValueError, 'EXACT_ORIGINAL_ARCHIVE_REQUIRED'):
                fetch.materialize(b'LOCAL_CORRUPT_ZIP_CONTROL', 'ROOT_VERIFIED_LOCAL_REPLAY_NO_GET')


class GeneratedSixInputControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='s03_bound_six_model_')
        self.root = Path(self.temp.name); self.here = self.root / 'model'
        self.expected = {inputs.PREFIX + 'LOCAL_MODEL_' + str(i) + '.json':
            {'bytes': 2, 'sha256': sha256(b'{}').hexdigest()} for i in range(6)}
        self.record = dict(classification='LOCAL_PRODUCER_MODEL_NOT_ACTUAL_ORIGINAL', producer_files={'model': 'fixed'},
            acquisition='ROOT_VERIFIED_LOCAL_REPLAY_NO_GET')
        self.static = patch.object(inputs, 'static', return_value=({}, self.expected)); self.static.start()
        self.producer = patch.object(inputs, 'input_receipt', return_value=self.record); self.producer.start()

    def tearDown(self):
        self.producer.stop(); self.static.stop(); self.temp.cleanup()

    def materialize(self):
        for name in self.expected:
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'{}')
        (self.root / inputs.RECEIPT).write_text(json.dumps(self.record))

    def test_absent_static_phase_has_no_original_or_case_credit(self):
        names, proof = inputs.present(self.root, self.here, {})
        self.assertFalse(names); self.assertIs(proof['actual_originals_admitted'], False)
        with self.assertRaisesRegex(ValueError, 'SIX_ACTUAL_ORIGINALS_NOT_MATERIALIZED'):
            inputs.present(self.root, self.here, {}, required=True)

    def test_exact_six_and_specific_producer_model_accepts_without_case_credit(self):
        self.materialize()
        inherited_ci = os.environ.get('GITHUB_ACTIONS')
        # This positive case models a local archive replay. The separate CI
        # control below must still reject the same receipt in GitHub Actions.
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'false'}):
            names, proof = inputs.present(self.root, self.here, {}, required=True)
        self.assertEqual(os.environ.get('GITHUB_ACTIONS'), inherited_ci)
        self.assertEqual(names, set(self.expected) | {inputs.RECEIPT})
        self.assertEqual(proof['new_Native_Auth_browser_credit'], 0)

    def test_partial_mixed_unknown_and_changed_raw_refuse(self):
        self.materialize(); name = next(iter(self.expected)); path = self.root / name
        saved = path.read_bytes()
        try:
            path.unlink()
            with self.assertRaisesRegex(ValueError, 'PARTIAL_MIXED_OR_UNKNOWN_RAW_INPUTS'):
                inputs.present(self.root, self.here, {})
        finally: path.write_bytes(saved)
        extra = self.root / (inputs.PREFIX + 'foreign.json')
        try:
            extra.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'PARTIAL_MIXED_OR_UNKNOWN_RAW_INPUTS'):
                inputs.present(self.root, self.here, {})
        finally: extra.unlink(missing_ok=True)
        try:
            path.write_bytes(b'{"changed":true}')
            with self.assertRaisesRegex(ValueError, 'EXACT_INPUT_BYTES_REQUIRED'):
                inputs.present(self.root, self.here, {})
        finally: path.write_bytes(saved)

    def test_changed_stage_or_producer_refuses(self):
        self.materialize(); path = self.root / inputs.RECEIPT
        path.write_text(json.dumps(dict(self.record, producer_files={'model': 'wrong'})))
        with self.assertRaisesRegex(ValueError, 'INPUT_STAGE_OR_PRODUCER_CHANGED'):
            inputs.present(self.root, self.here, {})

    def test_CI_refuses_local_replay_receipt(self):
        self.record.update(acquisition='ROOT_VERIFIED_LOCAL_REPLAY_NO_GET'); self.materialize()
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true'}):
            with self.assertRaisesRegex(ValueError, 'CI_REQUIRES_IMMUTABLE_ARTIFACT_GET'):
                inputs.present(self.root, self.here, {})

    def test_leaf_and_ancestor_symlinks_refuse_and_restore(self):
        self.materialize(); path = self.root / inputs.RECEIPT; saved = path.read_bytes()
        held = self.root / 'HELD_RECEIPT.json'; held.write_bytes(saved)
        try:
            path.unlink(); path.symlink_to(held)
            self.assertTrue(path.is_symlink())
            with self.assertRaisesRegex(ValueError, 'INPUT_SYMLINK:' + inputs.RECEIPT):
                inputs.present(self.root, self.here, {})
        finally:
            path.unlink(missing_ok=True); path.write_bytes(saved)
        self.assertFalse(path.is_symlink()); self.assertEqual(path.read_bytes(), saved)
        folder = self.root / inputs.PREFIX; held_directory = self.root / 'HELD_RAW_DIRECTORY'
        try:
            folder.rename(held_directory); folder.symlink_to(held_directory, target_is_directory=True)
            self.assertTrue(folder.is_symlink())
            with self.assertRaisesRegex(ValueError, 'INPUT_SYMLINK:' + inputs.PREFIX.rstrip('/')):
                inputs.present(self.root, self.here, {})
        finally:
            if folder.is_symlink(): folder.unlink()
            if held_directory.exists(): held_directory.rename(folder)
        self.assertFalse(folder.is_symlink()); self.assertTrue(folder.is_dir())
        self.assertEqual((folder / 'INPUT_RECEIPT.json').read_bytes(), saved)


if __name__ == '__main__':
    unittest.main(verbosity=2)
