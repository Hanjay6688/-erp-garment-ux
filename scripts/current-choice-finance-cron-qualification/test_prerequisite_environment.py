import json
from pathlib import Path
import tempfile
import unittest
from hashlib import sha256
from prerequisite_environment import bindings


class PrerequisiteEnvironment(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.original = self.repo / 'native6.json'
        self.original.write_bytes(b'{"status":"PASS","proof":"exact"}')
        self.proof = dict(bytes=self.original.stat().st_size, sha256=sha256(self.original.read_bytes()).hexdigest())
        self.env = {'TRANSPORT_NATIVE6': str(self.original)}
        for name, variable in [('current-progress-finance-ui-browser-qualification', 'UI_NATIVE6'), ('current-choice-preparation-transport-qualification', 'TRANSPORT_NATIVE6')]:
            folder = self.repo / 'scripts' / name
            folder.mkdir(parents=True)
            (folder / 'CONFIG.json').write_text(json.dumps(dict(choice_variable=variable)))
            (folder / 'SOURCE.json').write_text(json.dumps(dict(actual_predecessor=self.proof)))

    def test_ci_only_transport_environment_binds_ui(self):
        self.assertEqual(bindings(self.repo, self.env), {'UI_NATIVE6': str(self.original)})

    def test_missing_transport_environment_refused(self):
        with self.assertRaises(KeyError):
            bindings(self.repo, {})

    def test_changed_original_refused(self):
        self.original.write_bytes(b'{"status":"FAIL","proof":"exact"}')
        with self.assertRaisesRegex(AssertionError, 'HASH_CHANGED'):
            bindings(self.repo, self.env)

    def test_different_prerequisite_refused(self):
        path = self.repo / 'scripts/current-progress-finance-ui-browser-qualification/SOURCE.json'
        path.write_text(json.dumps(dict(actual_predecessor={**self.proof, 'bytes': 9})))
        with self.assertRaisesRegex(AssertionError, 'PREREQUISITE_MISMATCH'):
            bindings(self.repo, self.env)

    def test_conflicting_ui_binding_refused(self):
        other = self.repo / 'other.json'
        other.write_bytes(b'{}')
        with self.assertRaisesRegex(AssertionError, 'DIFFERENT_BYTES'):
            bindings(self.repo, {**self.env, 'UI_NATIVE6': str(other)})


if __name__ == '__main__':
    unittest.main()
