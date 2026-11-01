"""Local byte-integrity controls only; no network, ERP, or database runs."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util
import unittest
import warnings
import zipfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('canonical_archive_transport', HERE / 'archive_transport.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)


class TransportControls(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='cp7-archive-transport-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / 'source.zip'
        with zipfile.ZipFile(self.archive, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('report.json', '{"status":"SYNTHETIC_TRANSPORT_ONLY"}\n')
            raw = b''.join(sha256(str(index).encode()).digest() for index in range(120))
            archive.writestr('nested/original.bin', raw)
        self.expected = dict(repository=transport.REPOSITORY, head='1'*40, tree='2'*40,
            run_id=11, job_id=12, run_attempt=1, artifact_id=13, artifact_name='synthetic-only',
            archive=transport.pin(self.archive))
        self.directory = self.root / 'parts'
        self.chunk = (self.expected['archive']['bytes'] + 2) // 3
        self.output = self.root / 'restored.zip'

    def split(self):
        return transport.split_archive(self.archive, self.expected, self.directory, chunk_bytes=self.chunk)

    def test_roundtrip_keeps_complete_zip_and_member_bytes(self):
        manifest = self.split()
        self.assertEqual(len(manifest['parts']), 3)
        result = transport.join_archive(self.expected, manifest, self.directory, self.output)
        self.assertEqual(result['status'], 'EXACT_CANONICAL_ARCHIVE_REASSEMBLED')
        self.assertEqual(self.archive.read_bytes(), self.output.read_bytes())
        self.assertEqual(result['actual_case_credit'], 0)
        with zipfile.ZipFile(self.archive) as before, zipfile.ZipFile(self.output) as after:
            self.assertEqual(before.namelist(), after.namelist())
            for name in before.namelist():
                self.assertEqual(before.read(name), after.read(name))

    def test_wrong_digest_refuses_before_creating_parts(self):
        expected = deepcopy(self.expected)
        expected['archive']['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'CANONICAL_ARCHIVE'):
            transport.split_archive(self.archive, expected, self.directory)
        self.assertFalse(self.directory.exists())

    def test_unsafe_or_duplicate_member_refuses_before_creating_parts(self):
        for index, names in enumerate((('../escape',), ('/absolute',), ('a//b',), ('same', 'same'))):
            with self.subTest(names=names), warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                path = self.root / ('bad-'+str(index)+'.zip')
                with zipfile.ZipFile(path, 'w') as archive:
                    for name in names:
                        archive.writestr(name, 'synthetic')
                expected = deepcopy(self.expected)
                expected['archive'] = transport.pin(path)
                target = self.root / ('bad-parts-'+str(index))
                with self.assertRaisesRegex(ValueError, 'CANONICAL_MEMBER'):
                    transport.split_archive(path, expected, target)
                self.assertFalse(target.exists())

    def test_changed_missing_or_symlink_part_refuses_before_output(self):
        manifest = self.split()
        first = self.directory / 'original.part-0'
        original = first.read_bytes()
        first.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
        with self.assertRaisesRegex(ValueError, 'PART_BYTES_OR_SHA_CHANGED'):
            transport.join_archive(self.expected, manifest, self.directory, self.output)
        self.assertFalse(self.output.exists())
        first.unlink()
        with self.assertRaisesRegex(ValueError, 'REGULAR_PART_REQUIRED'):
            transport.join_archive(self.expected, manifest, self.directory, self.output)
        first.symlink_to(self.archive)
        with self.assertRaisesRegex(ValueError, 'REGULAR_PART_REQUIRED'):
            transport.join_archive(self.expected, manifest, self.directory, self.output)
        self.assertFalse(self.output.exists())

    def test_changed_identity_order_offset_and_typed_receipt_refuse(self):
        original = self.split()
        variants = []
        item = deepcopy(original); item['parts'].reverse(); variants.append(item)
        item = deepcopy(original); item['parts'][1]['offset'] += 1; variants.append(item)
        item = deepcopy(original); item['parts'][0]['index'] = False; variants.append(item)
        item = deepcopy(original); item['original']['run_attempt'] = True; variants.append(item)
        item = deepcopy(original); item['actual_case_credit'] = False; variants.append(item)
        item = deepcopy(original); item['zip_crc_valid'] = 1; variants.append(item)
        item = deepcopy(original); item['parts'][0]['name'] = '../escape'; variants.append(item)
        for item in variants:
            with self.subTest(item=item), self.assertRaises(ValueError):
                transport.join_archive(self.expected, item, self.directory, self.output)
            self.assertFalse(self.output.exists())

    def test_existing_output_is_preserved(self):
        manifest = self.split()
        self.output.write_bytes(b'KEEP_EXISTING')
        with self.assertRaises(FileExistsError):
            transport.join_archive(self.expected, manifest, self.directory, self.output)
        self.assertEqual(self.output.read_bytes(), b'KEEP_EXISTING')

    def test_network_metadata_must_be_terminal_and_exact_before_download(self):
        expected = self.expected
        run = dict(id=11, head_sha=expected['head'], run_attempt=1, status='completed',
            conclusion='success', repository=dict(full_name=transport.REPOSITORY))
        commit = dict(tree=dict(sha=expected['tree']))
        job = dict(id=12, run_id=11, head_sha=expected['head'], status='completed', conclusion='success')
        artifact = dict(id=13, name=expected['artifact_name'], expired=False,
            size_in_bytes=expected['archive']['bytes'], digest='sha256:'+expected['archive']['sha256'],
            workflow_run=dict(id=11, head_sha=expected['head']))
        snapshots = dict(run=run, commit=commit, job=job, artifact=artifact)
        variants = [('run', 'status', 'in_progress'), ('run', 'conclusion', 'failure'),
            ('run', 'head_sha', '3'*40), ('run', 'run_attempt', True),
            ('commit', 'tree', dict(sha='4'*40)), ('job', 'conclusion', 'failure'),
            ('job', 'run_id', 99), ('artifact', 'expired', True), ('artifact', 'id', 99),
            ('artifact', 'digest', 'sha256:'+'0'*64), ('artifact', 'size_in_bytes', 1),
            ('artifact', 'workflow_run', dict(id=99, head_sha=expected['head']))]

        def lookup(path, values):
            key = 'run' if path.startswith('actions/runs/') else 'job' if path.startswith('actions/jobs/') \
                else 'artifact' if path.startswith('actions/artifacts/') else 'commit'
            return values[key]

        for owner, key, value in variants:
            changed = deepcopy(snapshots); changed[owner][key] = value
            with self.subTest(owner=owner, key=key), patch.object(transport, 'api', side_effect=lambda p: lookup(p, changed)), \
                    patch.object(transport.subprocess, 'run') as download:
                with self.assertRaises(ValueError):
                    transport.fetch_and_split(expected, self.directory)
                download.assert_not_called()
                self.assertFalse((self.root / 'ORIGINAL.zip').exists())

        def deliver(command, *, stdout, check, timeout):
            self.assertEqual(command[-1], 'repos/'+transport.REPOSITORY+'/actions/artifacts/13/zip')
            self.assertTrue(check)
            self.assertEqual(timeout, 900)
            stdout.write(self.archive.read_bytes())

        with patch.object(transport, 'api', side_effect=lambda p: lookup(p, snapshots)), \
                patch.object(transport.subprocess, 'run', side_effect=deliver) as download:
            manifest = transport.fetch_and_split(expected, self.directory)
            download.assert_called_once()
            self.assertEqual(manifest['original'], expected)
            self.assertEqual(manifest['canonical_member_count'], 2)


if __name__ == '__main__':
    unittest.main()
