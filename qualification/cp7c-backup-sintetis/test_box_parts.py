"""Exercise the Box size rule with rclone and local, generated binary objects."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


PROFILE = Path(__file__).with_name('box-250mb.conf')
LIMIT = 250_000_000


def write_fixture(path, size):
    digest = hashlib.sha256()
    with path.open('wb') as writer:
        offset = 0
        while offset < size:
            # Consecutive parts carry different data, so swapping them changes SHA-256.
            block = bytes([(offset // 1_000_000) % 251]) * min(1_000_000, size - offset)
            writer.write(block)
            digest.update(block)
            offset += len(block)
    return digest.hexdigest()


class BoxPartsTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)
        self.physical = self.root / 'store' / 'ERP-Backup' / 'gladi'
        self.physical.mkdir(parents=True)
        self.input = self.root / 'source.bin'
        self.download = self.root / 'returned.bin'
        self.remote = 'boxbackup:gladi/sample.bin'
        self.env = dict(os.environ, RCLONE_CONFIG_BOX_TYPE='alias',
                        RCLONE_CONFIG_BOX_REMOTE=str(self.root / 'store'))
        # Only the underlying Box connection is simulated. The chunker reads the real profile.
        self.cli = ['rclone', '--config', str(PROFILE), '--retries', '1', '--low-level-retries', '1']

    def rclone(self, *args):
        return subprocess.run(self.cli + list(args), env=self.env, capture_output=True, text=True, check=True)

    def upload(self, size):
        expected = write_fixture(self.input, size)
        self.rclone('copyto', '--immutable', '--checksum', str(self.input), self.remote)
        return expected

    def sizes(self):
        return {path.name: path.stat().st_size for path in self.physical.iterdir()}

    def fetch(self, expected, size):
        self.rclone('copyto', self.remote, str(self.download))
        self.assertEqual(self.download.stat().st_size, size)
        with self.download.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        self.assertEqual(actual, expected)

    def test_existing_small_unsegmented_archive(self):
        expected = write_fixture(self.physical / 'sample.bin', 100_003)
        self.fetch(expected, 100_003)

    def test_just_below_and_at_limit_are_single_objects(self):
        for size in (LIMIT - 1, LIMIT):
            with self.subTest(size=size):
                expected = self.upload(size)
                self.assertEqual(self.sizes(), {'sample.bin': size})
                self.fetch(expected, size)
                self.download.unlink()
                self.rclone('deletefile', self.remote)

    def test_one_byte_above_limit(self):
        size = LIMIT + 1
        expected = self.upload(size)
        physical = self.sizes()
        header = json.loads((self.physical / 'sample.bin').read_bytes())
        self.assertEqual((header['size'], header['nchunks']), (size, 2))
        self.assertLess(physical.pop('sample.bin'), 1024)
        self.assertEqual(physical, {'sample.bin.rclone_chunk.001': LIMIT, 'sample.bin.rclone_chunk.002': 1})
        self.fetch(expected, size)

    def test_600mb_round_trip_retry_and_logical_retention(self):
        size = 600_000_000
        expected = self.upload(size)
        before = self.sizes()
        self.assertEqual([before[f'sample.bin.rclone_chunk.{i:03d}'] for i in (1, 2, 3)],
                         [250_000_000, 250_000_000, 100_000_000])
        self.assertEqual(len(before), 4)
        self.assertLess(before['sample.bin'], 1024)
        self.rclone('copyto', '--immutable', '--checksum', str(self.input), self.remote)
        self.assertEqual(self.sizes(), before)
        self.input.unlink()
        self.assertEqual(self.rclone('lsf', '--files-only', 'boxbackup:gladi').stdout.splitlines(), ['sample.bin'])
        self.fetch(expected, size)
        self.rclone('deletefile', self.remote)
        self.assertEqual(self.sizes(), {})

    def test_missing_part_fails_download(self):
        self.upload(LIMIT + 19)
        (self.physical / 'sample.bin.rclone_chunk.001').unlink()
        with self.assertRaises(subprocess.CalledProcessError):
            self.rclone('copyto', self.remote, str(self.download))
        self.assertFalse(self.download.exists())

    def test_same_size_corruption_fails_download(self):
        self.upload(LIMIT + 19)
        part = self.physical / 'sample.bin.rclone_chunk.002'
        part.write_bytes(b'X' * part.stat().st_size)
        with self.assertRaises(subprocess.CalledProcessError):
            self.rclone('copyto', self.remote, str(self.download))
        self.assertFalse(self.download.exists())


if __name__ == '__main__':
    unittest.main()
