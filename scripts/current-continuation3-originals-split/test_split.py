"""Meaningful bounded-stream/closed-metadata controls. No network or DB."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import split as s


def archive():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_STORED) as z:
        z.writestr('Original.json', b'{"Native":"unmodified", "count":3}')
        z.writestr('FULL_ROWS.bin', bytes(range(251)) * 3)
    return buffer.getvalue()


def small_pin(data):
    pin = deepcopy(s.PIN)
    first = len(data) // 2
    pin.update(archive_bytes=len(data), archive_sha256=hashlib.sha256(data).hexdigest(),
               part_bytes=[first, len(data) - first])
    return pin


def metadata():
    run = dict(id=s.PIN['run_id'], run_attempt=s.PIN['run_attempt'], head_sha=s.PIN['head_sha'],
        head_branch=s.PIN['head_branch'], path=s.PIN['workflow_path'], status='completed',
        conclusion='success', repository={'full_name': s.PIN['repository']})
    commit = dict(sha=s.PIN['head_sha'], tree={'sha': s.PIN['tree_sha']})
    job = dict(id=s.PIN['job_id'], run_id=s.PIN['run_id'], name=s.PIN['job_name'],
               status='completed', conclusion='success')
    artifact = dict(id=s.PIN['artifact_id'], name=s.PIN['artifact_name'], expired=False,
        size_in_bytes=s.PIN['archive_bytes'], digest='sha256:' + s.PIN['archive_sha256'],
        workflow_run={'id': s.PIN['run_id'], 'head_sha': s.PIN['head_sha']},
        archive_download_url='https://do-not-retain.invalid/signed-secret')
    return [run, commit, job, artifact]


class Process:
    def __init__(self, data, returncode=0):
        self.stdout = io.BytesIO(data)
        self.returncode = returncode
        self.finished = False
        self.killed = False

    def wait(self):
        self.finished = True
        return self.returncode

    def poll(self):
        return self.returncode if self.finished else None

    def kill(self):
        self.killed = True
        self.finished = True


class BoundedStream(io.BytesIO):
    def __init__(self, data):
        super().__init__(data)
        self.requested = []

    def read(self, size=-1):
        assert 0 < size <= 17, 'unbounded or oversized read'
        self.requested.append(size)
        # Deliberate short reads, including a block crossing the part boundary.
        return super().read(min(size, 11))


class SplitTransport(unittest.TestCase):
    def test_real_ZIP_short_reads_boundary_hashes_offsets_order_and_CRC(self):
        data = archive()
        pin = small_pin(data)
        stream = BoundedStream(data)
        with tempfile.TemporaryDirectory() as tmp:
            parts = s.split_stream(stream, Path(tmp), expected_bytes=len(data),
                expected_sha256=pin['archive_sha256'], part_sizes=pin['part_bytes'], block_bytes=17)
            raw = [(Path(tmp) / name).read_bytes() for name in s.PART_NAMES]
            self.assertEqual(raw[0], data[:pin['part_bytes'][0]])
            self.assertEqual(raw[1], data[pin['part_bytes'][0]:])
            self.assertEqual([p['offset'] for p in parts], [0, pin['part_bytes'][0]])
            self.assertEqual([p['bytes'] for p in parts], pin['part_bytes'])
            self.assertEqual([p['sha256'] for p in parts], [hashlib.sha256(b).hexdigest() for b in raw])
            self.assertEqual(hashlib.sha256(b''.join(raw)).hexdigest(), pin['archive_sha256'])
            self.assertNotEqual(hashlib.sha256(b''.join(reversed(raw))).hexdigest(), pin['archive_sha256'])
            with zipfile.ZipFile(io.BytesIO(b''.join(raw))) as original:
                self.assertIsNone(original.testzip())
                self.assertEqual(original.read('Original.json'), b'{"Native":"unmodified", "count":3}')
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), sorted(s.PART_NAMES))
        self.assertGreater(len(stream.requested), 20)

    def test_invalid_geometry_refuses_before_creating_a_part(self):
        for sizes, block in (([1], 8), ([0, 2], 8), ([True, 1], 8), ([1, 1], 0), ([1, 2], 8)):
            with self.subTest(sizes=sizes, block=block), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(s.Refused, 'INVALID_SPLIT_GEOMETRY'):
                    s.split_stream(io.BytesIO(b'ab'), Path(tmp), expected_bytes=2,
                        expected_sha256=hashlib.sha256(b'ab').hexdigest(), part_sizes=sizes, block_bytes=block)
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_short_extra_and_same_size_corrupt_stream_are_not_original(self):
        data = b'abcdefghijk'
        for payload, code in ((data[:-1], 'ARCHIVE_TOO_SHORT'), (data + b'x', 'ARCHIVE_TOO_LONG'),
                              (b'x' + data[1:], 'ARCHIVE_SHA256_CHANGED')):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(s.Refused, code):
                    s.split_stream(io.BytesIO(payload), Path(tmp), expected_bytes=len(data),
                        expected_sha256=hashlib.sha256(data).hexdigest(), part_sizes=[5, 6], block_bytes=3)
                self.assertFalse((Path(tmp) / s.MANIFEST_NAME).exists())

    def test_every_bound_run_tree_workflow_job_attempt_and_artifact_fact_refuses_change(self):
        s.admit_metadata(*metadata())
        changes = ((0, ('id',), 1), (0, ('run_attempt',), 2), (0, ('head_sha',), '0' * 40),
            (0, ('head_branch',), 'main'), (0, ('path',), 'other.yml'), (0, ('status',), 'in_progress'),
            (0, ('conclusion',), 'failure'), (0, ('repository', 'full_name'), 'other/repo'),
            (1, ('sha',), '0' * 40), (1, ('tree', 'sha'), '0' * 40), (2, ('id',), 1),
            (2, ('run_id',), 1), (2, ('name',), 'other'), (2, ('status',), 'queued'),
            (2, ('conclusion',), 'failure'), (3, ('id',), 1), (3, ('name',), 'other'),
            (3, ('expired',), True), (3, ('expired',), 0), (3, ('size_in_bytes',), 3),
            (3, ('digest',), 'sha256:' + '0' * 64), (3, ('workflow_run', 'id'), 1),
            (3, ('workflow_run', 'head_sha'), '0' * 40))
        for doc_index, keys, value in changes:
            docs = deepcopy(metadata())
            target = docs[doc_index]
            for key in keys[:-1]:
                target = target[key]
            target[keys[-1]] = value
            with self.subTest(doc=doc_index, key=keys), self.assertRaises(s.Refused):
                s.admit_metadata(*docs)

    def test_recover_publishes_exact_two_parts_and_URL_free_manifest_only_after_full_success(self):
        data = archive()
        process = Process(data)
        with tempfile.TemporaryDirectory() as tmp, patch.object(s, 'PIN', small_pin(data)), \
             patch.object(s.subprocess, 'Popen', return_value=process) as popen:
            output = Path(tmp) / 'new'
            manifest = s.recover(output, {'GH_TOKEN': 'test-secret'})
            self.assertEqual(set(p.name for p in output.iterdir()), {*s.PART_NAMES, s.MANIFEST_NAME})
            self.assertEqual(json.loads((output / s.MANIFEST_NAME).read_bytes()), manifest)
            text = json.dumps(manifest)
            self.assertNotIn('https:', text)
            self.assertNotIn('test-secret', text)
            self.assertNotIn('archive_download_url', text)
            self.assertFalse(manifest['financial_acceptance'])
            self.assertEqual(manifest['new_ERP_DB_Native_Auth_browser_execution_credit'], 0)
            args, options = popen.call_args
            self.assertEqual(args[0], s.gh_command('actions/artifacts/12937065328/zip'))
            self.assertEqual(options['stderr'], subprocess.DEVNULL)
            self.assertTrue(process.stdout.closed)

    def test_failed_download_digest_short_or_exitcode_removes_every_partial_file(self):
        data = archive()
        for payload, returncode in ((data[:-1], 0), (b'x' + data[1:], 0), (data, 22)):
            process = Process(payload, returncode)
            with self.subTest(returncode=returncode, length=len(payload)), tempfile.TemporaryDirectory() as tmp, \
                 patch.object(s, 'PIN', small_pin(data)), patch.object(s.subprocess, 'Popen', return_value=process):
                destination = Path(tmp) / 'new'
                with self.assertRaises(s.Refused):
                    s.recover(destination, {})
                self.assertFalse(destination.exists())
                self.assertTrue(process.stdout.closed)
                self.assertTrue(process.finished)

    def test_existing_output_is_not_overwritten_or_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / s.MANIFEST_NAME
            path.write_bytes(b'prior evidence')
            with patch.object(s.subprocess, 'Popen') as popen, self.assertRaisesRegex(s.Refused, 'OUTPUT_MUST_BE_NEW'):
                s.recover(Path(tmp), {})
            popen.assert_not_called()
            self.assertEqual(path.read_bytes(), b'prior evidence')

    def test_main_metadata_mismatch_blocks_archive_GET_and_all_writes(self):
        docs = metadata()
        docs[0]['path'] = 'wrong.yml'
        with patch.dict(s.os.environ, {'GITHUB_REPOSITORY': s.PIN['repository'],
                'GITHUB_REF': 'refs/heads/' + s.BRANCH}), patch.object(s, 'admit_source'), \
             patch.object(s, 'gh_env', return_value={}), patch.object(s, 'get_metadata', side_effect=docs), \
             patch.object(s, 'recover') as recover, self.assertRaises(s.Refused):
            s.main(['/not-created'])
        recover.assert_not_called()

    def test_main_arbitrary_source_arguments_and_unrelated_execution_ref_refuse_before_GET(self):
        for args, ref in ((['https://not-allowed.invalid', '/tmp/x'], 'refs/heads/' + s.BRANCH),
                          (['/tmp/x'], 'refs/heads/main')):
            with self.subTest(args=args, ref=ref), patch.dict(s.os.environ,
                    {'GITHUB_REPOSITORY': s.PIN['repository'], 'GITHUB_REF': ref}), \
                 patch.object(s, 'get_metadata') as get, self.assertRaises(s.Refused):
                s.main(args)
            get.assert_not_called()

    def test_child_debug_disabled_and_metadata_errors_never_expose_stderr(self):
        with patch.dict(s.os.environ, {'GH_TOKEN': 'fixture-secret', 'GH_DEBUG': 'api'}):
            env = s.gh_env()
        self.assertNotIn('GH_DEBUG', env)
        self.assertEqual(env['GH_TOKEN'], 'fixture-secret')
        with patch.object(s.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1,
                stdout=b'', stderr=b'https://secret.invalid')) as run:
            with self.assertRaisesRegex(s.Refused, '^METADATA_GET_FAILED$'):
                s.get_metadata('actions/runs/' + str(s.PIN['run_id']), env)
            self.assertEqual(run.call_args.kwargs['stderr'], subprocess.DEVNULL)

    def test_source_binding_and_three_separate_compression_zero_uploads(self):
        s.admit_source()
        text = (s.ROOT / s.WORKFLOW).read_text()
        self.assertEqual(text.count('uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'), 3)
        self.assertEqual(text.count('compression-level: 0'), 3)
        self.assertIn('  contents: read\n  actions: read\n', text)
        self.assertIn('timeout-minutes: 20', text)
        self.assertNotIn('secrets.', text)
        self.assertEqual(text.count('name: cp7-d1-continuation3-original-12937065328-part-'), 2)
        self.assertIn('if-no-files-found: error', text)


if __name__ == '__main__':
    unittest.main()
