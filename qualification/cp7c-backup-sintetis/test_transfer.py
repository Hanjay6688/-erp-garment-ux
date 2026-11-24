"""Run synthetic backup integrity tests on a fresh, simulated object store."""

import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import boto3
from botocore.exceptions import ClientError
from moto import mock_aws

from transfer_fixture import transfer


@mock_aws
class TransferTests(unittest.TestCase):
    def setUp(self):
        guard = patch('socket.socket.connect', side_effect=AssertionError('Network access during fixture test'))
        guard.start()
        self.addCleanup(guard.stop)
        self.s3 = boto3.client('s3', region_name='us-east-1',
                               aws_access_key_id='synthetic', aws_secret_access_key='synthetic')
        self.bucket = 'drill-backup'
        self.s3.create_bucket(Bucket=self.bucket)
        self.data = b'synthetic encrypted archive fixture'
        self.sha = hashlib.sha256(self.data).hexdigest()
        self.manifest = dict(candidate='face0000', ciphertext_sha256=self.sha,
                             ciphertext_bytes=len(self.data), object_filename='manual.cp7')
        self.key = f'cp7c/face0000/{self.sha}.cp7'
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / 'download.cp7'

    def stage(self, key='manual.cp7', data=None):
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=self.data if data is None else data)

    def run_transfer(self, mode, **kwargs):
        return transfer(self.s3, self.bucket, self.manifest, mode, **kwargs)

    def test_dashboard_upload_and_independent_download(self):
        self.stage()
        self.assertEqual(self.run_transfer('publish')['result'], 'UPLOADED_AND_DOWNLOADED')
        self.assertEqual(self.run_transfer('verify', output=self.out)['sha256'], self.sha)
        self.assertEqual(self.out.read_bytes(), self.data)
        with patch.object(self.s3, 'put_object', side_effect=AssertionError('retry wrote again')):
            self.assertEqual(self.run_transfer('publish')['result'], 'VERIFIED_EXISTING')

    def test_direct_local_upload(self):
        self.out.write_bytes(self.data)
        self.assertEqual(self.run_transfer('publish', source=self.out)['result'], 'UPLOADED_AND_DOWNLOADED')
        self.assertEqual(self.run_transfer('verify')['bytes'], len(self.data))

    def test_corrupt_input_never_published(self):
        with patch.object(self.s3, 'put_object', wraps=self.s3.put_object) as put:
            for value in (self.data + b'x', b'x' * len(self.data)):
                self.stage(data=value)
                put.reset_mock()
                with self.assertRaises(ValueError):
                    self.run_transfer('publish')
                put.assert_not_called()

    def test_conflicting_destination_preserved(self):
        bad = b'x' * len(self.data)
        self.stage(self.key, bad)
        self.stage()
        with self.assertRaises(ValueError):
            self.run_transfer('publish')
        self.assertEqual(self.s3.get_object(Bucket=self.bucket, Key=self.key)['Body'].read(), bad)

    def test_competing_writer_is_verified(self):
        self.stage()
        real_put = self.s3.put_object

        def raced_put(**kwargs):
            self.assertEqual(kwargs['IfNoneMatch'], '*')
            real_put(Bucket=self.bucket, Key=self.key, Body=self.data)
            return real_put(**kwargs)

        with patch.object(self.s3, 'put_object', side_effect=raced_put):
            result = self.run_transfer('publish')
        self.assertEqual(result['result'], 'VERIFIED_CONCURRENT_UPLOAD')
        self.assertEqual(result['sha256'], self.sha)

    def test_verify_only_and_existing_local_file(self):
        self.stage()
        with self.assertRaises(ClientError):
            self.run_transfer('verify', output=self.out)
        self.assertFalse(self.out.exists())
        self.stage(self.key)
        self.out.write_bytes(b'prior download')
        with self.assertRaises(FileExistsError):
            self.run_transfer('verify', output=self.out)
        self.assertEqual(self.out.read_bytes(), b'prior download')

    def test_access_denied_is_not_absence(self):
        denied = ClientError({'Error': {'Code': 'AccessDenied'}, 'ResponseMetadata': {'HTTPStatusCode': 403}}, 'GetObject')
        with patch.object(self.s3, 'get_object', side_effect=denied), patch.object(self.s3, 'put_object') as put:
            with self.assertRaises(ClientError):
                self.run_transfer('publish')
            put.assert_not_called()

    def test_interrupted_download_leaves_no_output(self):
        self.stage(self.key)
        response = {'Body': io.BytesIO(self.data[:-1]), 'ContentLength': len(self.data), 'ETag': 'fixture'}
        with patch.object(self.s3, 'get_object', return_value=response), self.assertRaises(ValueError):
            self.run_transfer('verify', output=self.out)
        self.assertFalse(self.out.exists())

    def test_round_trip_100_mb_generated_on_runner(self):
        source = Path(self.temp.name) / 'synthetic-input.bin'
        block = b'1234567890' * 100_000
        expected_hash = hashlib.sha256()
        with source.open('wb') as writer:
            for _ in range(100):
                writer.write(block)
                expected_hash.update(block)
        self.manifest.update(ciphertext_sha256=expected_hash.hexdigest(), ciphertext_bytes=100_000_000)
        published = self.run_transfer('publish', source=source)
        self.assertEqual(published['result'], 'UPLOADED_AND_DOWNLOADED')
        fetched = self.run_transfer('verify', output=self.out)
        self.assertEqual(fetched['bytes'], 100_000_000)
        with self.out.open('rb') as reader:
            self.assertEqual(hashlib.file_digest(reader, 'sha256').hexdigest(), expected_hash.hexdigest())


if __name__ == '__main__':
    unittest.main()
