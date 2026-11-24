"""Transfer routines exercised only against the in-process storage simulator."""

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import tempfile

from botocore.exceptions import ClientError


def copy_verified(source, destination, manifest):
    expected = manifest['ciphertext_bytes']
    hashed = hashlib.sha256()
    count = 0
    with destination.open('wb') as out:
        while block := source.read(1024 * 1024):
            count += len(block)
            if count > expected:
                raise ValueError('Ukuran arsip melebihi tanda terima Writer A')
            out.write(block)
            hashed.update(block)
    if count != expected or hashed.hexdigest() != manifest['ciphertext_sha256']:
        raise ValueError('Ukuran atau SHA-256 arsip berbeda dari tanda terima Writer A')


def fetch_verified(client, bucket, key, path, manifest):
    response = client.get_object(Bucket=bucket, Key=key)
    with closing(response['Body']) as stream:
        if response['ContentLength'] != manifest['ciphertext_bytes']:
            raise ValueError('Ukuran objek R2 berbeda dari tanda terima Writer A')
        copy_verified(stream, path, manifest)
    return response['ETag']


def note(manifest, bucket, key, etag, outcome):
    return dict(utc=datetime.now(timezone.utc).isoformat(), candidate=manifest['candidate'],
                bucket=bucket, object=key, etag=etag, bytes=manifest['ciphertext_bytes'],
                sha256=manifest['ciphertext_sha256'], result=outcome, production_go=False)


def transfer(client, bucket, manifest, mode, source=None, output=None):
    key = f"cp7c/{manifest['candidate'][:8]}/{manifest['ciphertext_sha256']}.cp7"
    # Keeping the temp directory next to output permits exclusive publication by hard link.
    with tempfile.TemporaryDirectory(dir=output.parent if output else None) as work:
        downloaded = Path(work) / 'downloaded.cp7'
        try:
            etag = fetch_verified(client, bucket, key, downloaded, manifest)
            outcome = 'VERIFIED_EXISTING'
        except ClientError as error:
            missing_key = error.response['Error']['Code'] in ('NoSuchKey', '404', 'NotFound')
            if mode != 'publish' or not missing_key:
                raise
            staged = Path(work) / 'verified-input.cp7'
            if source:
                with source.open('rb') as stream:
                    copy_verified(stream, staged, manifest)
            else:
                fetch_verified(client, bucket, manifest['object_filename'], staged, manifest)
            try:
                with staged.open('rb') as stream:
                    client.put_object(Bucket=bucket, Key=key, Body=stream,
                                      ContentLength=manifest['ciphertext_bytes'],
                                      ContentType='application/octet-stream', IfNoneMatch='*')
                outcome = 'UPLOADED_AND_DOWNLOADED'
            except ClientError as conflict:
                if conflict.response['ResponseMetadata']['HTTPStatusCode'] not in (409, 412):
                    raise
                outcome = 'VERIFIED_CONCURRENT_UPLOAD'
            etag = fetch_verified(client, bucket, key, downloaded, manifest)
        if output:
            os.link(downloaded, output)  # refuse to replace an existing local archive
        return note(manifest, bucket, key, etag, outcome)
