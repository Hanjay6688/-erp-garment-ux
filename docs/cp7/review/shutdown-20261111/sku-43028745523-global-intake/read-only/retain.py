"""Read-only export of one completed Afui run; never imports ERP or uses SQL."""
from hashlib import sha256, file_digest
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
import gzip
import base64
import json
import os
import sys
import stat
import urllib.error
import urllib.request
import zipfile

REPO = 'Hanjay6688/-erp-garment-ux'
RUN = 42145552785
JOB = 127656036594
ARTIFACT = 13483831055
HEAD = 'f17ac6cc13cffe10a32deca1c04ff63d220285fe'
SIZE = 2491971627
DIGEST = '0fe537044952c67ae6b28acc1551836bc3c05ed357d1fe4c90e34b8491d8859c'
PART_BYTES = 209715200
SELECTED = frozenset(('CP7_AFUI_GOOD_NONPAYABLE_FULL15.json', 'AFUI_RUNTIME_SUPERVISION.json',
    'AFUI_DURABLE_RUNTIME.json', 'AFUI_DURABLE_PREFLIGHT.json', 'AFUI_FINAL_GATE.json',
    'AFUI_BROWSER_SETTINGS_STATE.json', 'AFUI_BROWSER_NATIVE_PREREQUISITE.json',
    'T3_PACKAGE_INSTALL.json', 'T3_BACKUP_RESTORE_DRILL.json', 'T3_PACKAGE_FILES_INSTALL.json'))


def require(value, reason):
    if not value:
        raise ValueError(reason)


def pin(path):
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size, sha256=file_digest(stream, 'sha256').hexdigest())


def save(path, value):
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api(route):
    require(route.startswith('/repos/' + REPO + '/actions/'), 'FIXED_REPOSITORY_ACTIONS_READ_ONLY_API')
    request = urllib.request.Request('https://api.github.com' + route,
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'FixedAfuiEvidenceIntake'})
    try:
        return urllib.request.build_opener(NoRedirect).open(request, timeout=60)
    except urllib.error.HTTPError as error:
        if error.code == 302:
            location = error.headers['Location'];parsed = urlsplit(location)
            require(parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password,
                    'HTTPS_ARCHIVE_REDIRECT_REQUIRED')
            # No authenticated request or Authorization header crosses hosts.
            return urllib.request.urlopen(urllib.request.Request(location, headers={'User-Agent': 'FixedAfuiEvidenceIntake'}), timeout=60)
        raise ValueError('GITHUB_READ_HTTP_STATUS_' + str(error.code)) from None


def metadata(route, target):
    with api(route) as response:
        raw = response.read(4 * 1024 * 1024 + 1)
    require(len(raw) <= 4 * 1024 * 1024, 'BOUNDED_CANONICAL_METADATA_REQUIRED')
    with target.open('xb') as stream:
        stream.write(raw)
    return json.loads(raw)


def copy_stream(source, target, maximum=None):
    count, digest = 0, sha256()
    while True:
        chunk = source.read(4 * 1024 * 1024)
        if not chunk:
            return dict(bytes=count, sha256=digest.hexdigest())
        count += len(chunk)
        require(maximum is None or count <= maximum, 'ORIGINAL_BYTE_LIMIT_EXCEEDED')
        target.write(chunk);digest.update(chunk)


