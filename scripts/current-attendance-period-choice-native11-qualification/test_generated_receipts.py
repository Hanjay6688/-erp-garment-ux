"""Actual first CI metadata plus directed local receipt doubles, no DB."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util
import json
import unittest
import uuid
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('s03_directed_generated_receipt_controls', HERE / 'generated_receipts.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
CFG = json.loads((HERE / helper.CONTRACT).read_bytes())
ARCHIVE = HERE / 'retained-a577/PREDB_FIRST_ARTIFACT.zip'


def actual():
    with zipfile.ZipFile(ARCHIVE) as archive:
        return {('cp6-proof/t3/' + name): archive.read(name) for name in archive.namelist()
                if not name.endswith('/') and name != 'S03_NATIVE11_FINAL_GATE.json'}


class ReceiptControls(unittest.TestCase):
    def setUp(self):
        values = actual()
        name, raw = next((n, r) for n, r in values.items() if '/ARTIFACT_FETCH/' in n)
        self.example = json.loads(raw)
        self.request = uuid.uuid4().hex
        self.stem = helper.PREFIX + self.request

    def write(self, root, relative, value):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(value if isinstance(value, bytes) else (json.dumps(value) + '\n').encode())
        return relative

    def admit(self, root, names, cfg=None):
        # Declared contract double for local schema tests, never source/Native credit.
        with patch.object(helper, 'contract', return_value=deepcopy(CFG if cfg is None else cfg)):
            return helper.admit(root, HERE, names)

    def success(self, attempt=1):
        value = deepcopy(self.example)
        value.update(attempt=attempt, exit_code=0, http_status=None, retry=False, delay_seconds=None,
                     recorded_at_utc='2026-10-30T00:00:03+00:00')
        return value

    def failure(self, root, attempt=1, http=502, artifact=None):
        value = deepcopy(self.example)
        stdout = b'LOCAL_PARTIAL_NOT_FORWARDED'
        stderr = ('gh: local declared failure (HTTP ' + str(http) + ')\n').encode()
        value.update(artifact_id=artifact or value['artifact_id'], attempt=attempt, exit_code=1,
                     http_status=http if http in (502, 503, 504) else None,
                     retry=http in (502, 503, 504) and attempt < 3,
                     delay_seconds=(2, 5)[attempt - 1] if http in (502, 503, 504) and attempt < 3 else None,
                     stdout_bytes=len(stdout), stdout_sha256=sha256(stdout).hexdigest(),
                     stderr_bytes=len(stderr), stderr_sha256=sha256(stderr).hexdigest(),
                     recorded_at_utc='2026-10-30T00:00:0' + str(attempt) + '+00:00')
        base = self.stem + '-' + str(attempt)
        return {self.write(root, base + '.json', value), self.write(root, base + '.stdout.txt', stdout),
                self.write(root, base + '.stderr.txt', stderr)}

    def test_real_first101_metadata_passes_real_frozen_producer_pins_without_original_substitution(self):
        names = actual()
        accepted, receipt = helper.admit(ROOT, HERE, names)
        self.assertEqual(set(accepted), set(names))
        self.assertEqual((receipt['files'], receipt['artifact_requests'], receipt['artifact_attempts']), (101, 100, 100))
        self.assertIsNone(receipt['expected_total_request_count'])
        self.assertTrue(receipt['authoritative_Original_readers_unchanged'])

    def test_changed_producer_bytes_are_refused(self):
        original = helper.pin
        first = next(iter(CFG['producer_files']))
        def observed(root, relative, **kwargs):
            return dict(bytes=1, sha256='0' * 64) if relative == first else original(root, relative, **kwargs)
        with patch.object(helper, 'pin', side_effect=observed):
            with self.assertRaisesRegex(ValueError, 'FROZEN_PRODUCER_CHANGED'):
                helper.contract(ROOT, HERE)

    def test_zero_receipts_is_not_a_fixed100_requirement(self):
        with TemporaryDirectory() as directory:
            accepted, summary = self.admit(Path(directory), [])
            self.assertEqual(accepted, {})
            self.assertEqual(summary['artifact_requests'], 0)

    def test_arbitrary_source_or_unknown_receipt_name_has_no_allowance(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            names = {self.write(root, 'cp6-proof/t3/evil.py', b'import os\n'),
                     self.write(root, helper.PREFIX + 'arbitrary.json', dict(source='evil.py'))}
            accepted, _ = self.admit(root, names)
            self.assertEqual(accepted, {})
            self.assertEqual(names - set(accepted), names)

    def test_frozen_worktree_changed_head_or_extra_metadata_or_false_integer_refuses(self):
        for mutate in (lambda v: v['inputs'][0].update(head='0' * 40),
                       lambda v: v.update(source_module='evil.py'), lambda v: v.update(network_fetches=False)):
            with TemporaryDirectory() as directory:
                root = Path(directory)
                value = deepcopy(CFG['frozen_worktree_document']);mutate(value)
                self.write(root, helper.FROZEN, value)
                with self.assertRaisesRegex(ValueError, 'FROZEN_WORKTREE'):
                    self.admit(root, [helper.FROZEN])

    def test_leaf_and_ancestor_symlinks_refuse(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / 'outside.json';raw.write_text(json.dumps(self.success()))
            name = self.stem + '-1.json';target = root / name;target.parent.mkdir(parents=True)
            target.symlink_to(raw)
            with self.assertRaisesRegex(ValueError, 'SYMLINK'):
                self.admit(root, [name])
            target.unlink();target.parent.rmdir()
            folder = root / 'elsewhere';folder.mkdir();(folder / target.name).write_bytes(raw.read_bytes())
            target.parent.symlink_to(folder, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'SYMLINK'):
                self.admit(root, [name])

    def test_unknown_artifact_extra_field_and_wrong_zip_hash_refuse(self):
        for mutate in (lambda v: v.update(artifact_id=1), lambda v: v.update(source='evil.py'),
                       lambda v: v.update(stdout_sha256='0' * 64), lambda v: v.update(partial_stdout_forwarded=True),
                       lambda v: v.update(delay_seconds=2.0)):
            with TemporaryDirectory() as directory:
                root = Path(directory);value = self.success();mutate(value)
                name = self.write(root, self.stem + '-1.json', value)
                with self.assertRaisesRegex(ValueError, 'ARTIFACT'):
                    self.admit(root, [name])

    def test_duplicate_json_key_refuses(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            name = self.write(root, self.stem + '-1.json', b'{"artifact_id":1,"artifact_id":2}')
            with self.assertRaisesRegex(ValueError, 'DUPLICATE_JSON_KEY'):
                self.admit(root, [name])

    def test_two_transient_failures_then_third_success_preserves_failed_streams(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            names = self.failure(root, 1, 502) | self.failure(root, 2, 503)
            names.add(self.write(root, self.stem + '-3.json', self.success(3)))
            accepted, receipt = self.admit(root, names)
            self.assertEqual(set(accepted), names)
            self.assertEqual((receipt['artifact_requests'], receipt['artifact_attempts']), (1, 3))

    def test_failed_stream_tamper_or_missing_retry_completion_refuses(self):
        with TemporaryDirectory() as directory:
            root = Path(directory);names = self.failure(root)
            with self.assertRaisesRegex(ValueError, 'REQUEST_INCOMPLETE'):
                self.admit(root, names)
            names.add(self.write(root, self.stem + '-2.json', self.success(2)))
            (root / (self.stem + '-1.stdout.txt')).write_bytes(b'CHANGED')
            with self.assertRaisesRegex(ValueError, 'FAILED_STREAM_HASH'):
                self.admit(root, names)

    def test_optional_frozen_AC_bootstrap_terminal_failure_only(self):
        with TemporaryDirectory() as directory:
            root = Path(directory);names = self.failure(root, http=404, artifact=10392910720)
            accepted, _ = self.admit(root, names)
            self.assertEqual(set(accepted), names)
        with TemporaryDirectory() as directory:
            root = Path(directory);names = self.failure(root, http=404)
            with self.assertRaisesRegex(ValueError, 'REQUEST_INCOMPLETE'):
                self.admit(root, names)

    def test_success_cannot_keep_unaccounted_stream_or_unbounded_duplicate_requests(self):
        with TemporaryDirectory() as directory:
            root = Path(directory);name = self.write(root, self.stem + '-1.json', self.success())
            stream = self.write(root, self.stem + '-1.stdout.txt', b'UNEXPECTED')
            with self.assertRaisesRegex(ValueError, 'SUCCESS_STREAM_MUST_BE_REMOVED'):
                self.admit(root, [name, stream])
        with TemporaryDirectory() as directory:
            root = Path(directory);value = self.success();bound = CFG['artifacts'][str(value['artifact_id'])]['max_requests_per_admission']
            names = {self.write(root, helper.PREFIX + uuid.uuid4().hex + '-1.json', value) for _ in range(bound + 1)}
            with self.assertRaisesRegex(ValueError, 'REQUEST_COUNT_BOUND'):
                self.admit(root, names)


if __name__ == '__main__':
    unittest.main()
