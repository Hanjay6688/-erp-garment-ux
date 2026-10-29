"""Recover ONE immutable archive as two raw consecutive transport parts.

Read-only GitHub GETs only. No ERP/DB imports, financial acceptance or arbitrary
download argument. Token and redirect URLs remain inside gh's environment/I/O.
"""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BRANCH = 'astra-a/continuation3-originals-split-20261030'
PIN = {
    'repository': 'Hanjay6688/-erp-garment-ux',
    'run_id': 40958135976,
    'run_attempt': 1,
    'workflow_path': '.github/workflows/cp7-credit-d1-current-parent-continuation3.yml',
    'head_branch': 'astra-a/credit-d1-current-parent-continuation3-20261030',
    'head_sha': 'cde78b2cc82e0a286174098458dab9815fdfd072',
    'tree_sha': '915103541d247f544c4492db25953b4268d9c2e3',
    'job_id': 123743552217,
    'job_name': 'D1 continuation3 above exact current Native13; complete restore',
    'artifact_id': 12937065328,
    'artifact_name': 'cp7-a-credit-d1-current-parent-continuation3-1',
    'archive_bytes': 671127620,
    'archive_sha256': '609ebff9739f359d39239d0e502aad20d4613f5a037a4e0e83f31b04b4b7652e',
    'part_bytes': [335563810, 335563810],
}
FILES = ('split.py', 'test_split.py', 'README.md')
WORKFLOW = '.github/workflows/cp7-continuation3-originals-split.yml'
MANIFEST_NAME = 'CONTINUATION3_ORIGINALS_SPLIT.json'
PART_NAMES = ('original-artifact.zip.part-001', 'original-artifact.zip.part-002')
TRANSPORT_NAMES = tuple('cp7-d1-continuation3-original-12937065328-part-' + n for n in ('001', '002'))


class Refused(Exception):
    """Only constant, non-sensitive diagnostic codes may be exposed."""


def require(condition, code):
    if not condition:
        raise Refused(code)


def admit_source():
    doc = json.loads((HERE / 'SOURCE.json').read_bytes())
    require(doc['contract'] == 'cp7.readonly-originals-split-preparation.v1'
            and doc['source_original'] == PIN and doc['execution_branch'] == BRANCH
            and doc['new_financial_execution_credit'] == 0, 'SOURCE_BINDING_CHANGED')
    expected = {str((HERE / name).relative_to(ROOT)) for name in FILES} | {WORKFLOW}
    require(set(doc['files']) == expected, 'SOURCE_FILE_SET_CHANGED')
    for name, digest in doc['files'].items():
        require(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, 'SOURCE_FILE_BYTES_CHANGED')


def admit_metadata(run, commit, job, artifact):
    """Do not retain raw API documents: they can contain download URLs."""
    require(type(run['id']) is int and run['id'] == PIN['run_id']
            and type(run['run_attempt']) is int and run['run_attempt'] == PIN['run_attempt']
            and run['head_sha'] == PIN['head_sha'] and run['head_branch'] == PIN['head_branch']
            and run['path'] == PIN['workflow_path'] and run['status'] == 'completed'
            and run['conclusion'] == 'success'
            and run['repository']['full_name'] == PIN['repository'], 'RUN_IDENTITY_OR_SUCCESS_CHANGED')
    require(commit['sha'] == PIN['head_sha'] and commit['tree']['sha'] == PIN['tree_sha'], 'SOURCE_TREE_CHANGED')
    require(type(job['id']) is int and job['id'] == PIN['job_id']
            and type(job['run_id']) is int and job['run_id'] == PIN['run_id']
            and job['name'] == PIN['job_name'] and job['status'] == 'completed'
            and job['conclusion'] == 'success', 'JOB_IDENTITY_OR_SUCCESS_CHANGED')
    require(type(artifact['id']) is int and artifact['id'] == PIN['artifact_id']
            and artifact['name'] == PIN['artifact_name'] and artifact['expired'] is False
            and type(artifact['size_in_bytes']) is int and artifact['size_in_bytes'] == PIN['archive_bytes']
            and artifact['digest'] == 'sha256:' + PIN['archive_sha256']
            and type(artifact['workflow_run']['id']) is int
            and artifact['workflow_run']['id'] == PIN['run_id']
            and artifact['workflow_run']['head_sha'] == PIN['head_sha'], 'ARTIFACT_IDENTITY_OR_DIGEST_CHANGED')


def gh_env():
    env = os.environ.copy()
    require(bool(env.get('GH_TOKEN')), 'READONLY_GH_TOKEN_REQUIRED')
    env.pop('GH_DEBUG', None)
    env['GH_PROMPT_DISABLED'] = '1'
    return env


def gh_command(path):
    return ['gh', 'api', '--hostname', 'github.com', 'repos/' + PIN['repository'] + '/' + path]


def get_metadata(path, env):
    result = subprocess.run(gh_command(path), env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, check=False)
    require(result.returncode == 0, 'METADATA_GET_FAILED')
    return json.loads(result.stdout)


def split_stream(stream, directory, *, expected_bytes, expected_sha256, part_sizes, block_bytes=1024 * 1024):
    """Bounded memory; files are staged, never a third complete ZIP copy."""
    require(len(part_sizes) == 2 and all(type(n) is int and n > 0 for n in part_sizes)
            and sum(part_sizes) == expected_bytes and type(block_bytes) is int
            and block_bytes > 0, 'INVALID_SPLIT_GEOMETRY')
    whole = hashlib.sha256()
    hashes = [hashlib.sha256(), hashlib.sha256()]
    written = [0, 0]
    total = index = 0
    with ExitStack() as stack:
        outputs = [stack.enter_context((directory / name).open('xb')) for name in PART_NAMES]
        while True:
            block = stream.read(block_bytes)
            if not block:
                break
            require(type(block) is bytes and len(block) <= block_bytes, 'INVALID_STREAM_BLOCK')
            require(total + len(block) <= expected_bytes, 'ARCHIVE_TOO_LONG')
            whole.update(block)
            total += len(block)
            offset = 0
            while offset < len(block):
                size = min(len(block) - offset, part_sizes[index] - written[index])
                piece = block[offset:offset + size]
                outputs[index].write(piece)
                hashes[index].update(piece)
                written[index] += size
                offset += size
                if written[index] == part_sizes[index]:
                    index += 1
    require(total == expected_bytes and written == part_sizes, 'ARCHIVE_TOO_SHORT')
    require(whole.hexdigest() == expected_sha256, 'ARCHIVE_SHA256_CHANGED')
    return [dict(order=i + 1, filename=PART_NAMES[i], transport_artifact_name=TRANSPORT_NAMES[i],
                 offset=sum(part_sizes[:i]), bytes=written[i], sha256=hashes[i].hexdigest()) for i in range(2)]


def recover(destination, env):
    require(not destination.exists(), 'OUTPUT_MUST_BE_NEW')
    destination.mkdir(parents=True)
    process = None
    try:
        with TemporaryDirectory(prefix='.unverified-', dir=destination) as temporary:
            staged = Path(temporary)
            process = subprocess.Popen(gh_command('actions/artifacts/' + str(PIN['artifact_id']) + '/zip'),
                                       env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            try:
                parts = split_stream(process.stdout, staged, expected_bytes=PIN['archive_bytes'],
                                     expected_sha256=PIN['archive_sha256'], part_sizes=PIN['part_bytes'])
                require(process.wait() == 0, 'ARCHIVE_GET_FAILED')
            finally:
                process.stdout.close()
                if process.poll() is None:
                    process.kill()
                    process.wait()
            manifest = dict(contract='cp7.readonly-originals-consecutive-parts.v1',
                status='EXACT_ORIGINAL_ARCHIVE_SHA256_VERIFIED', source_original=PIN,
                reconstruction=dict(operation='concatenate raw part bytes in order; no headers or separators',
                    archive_bytes=PIN['archive_bytes'], archive_sha256=PIN['archive_sha256'],
                    original_archive_unchanged=True, parts=parts),
                transport_wrappers_are_not_original_archive=True,
                wrapper_digests_must_be_verified_before_extracting_exact_part=True,
                new_ERP_DB_Native_Auth_browser_execution_credit=0, financial_acceptance=False,
                production_go=False, independent_acceptance=False)
            (staged / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + '\n')
            for name in (*PART_NAMES, MANIFEST_NAME):
                (staged / name).rename(destination / name)
    except BaseException:
        # No manifest or partial part is admissible after any transport failure.
        for name in (*PART_NAMES, MANIFEST_NAME):
            (destination / name).unlink(missing_ok=True)
        destination.rmdir()
        raise
    return manifest


def main(argv):
    require(len(argv) == 1, 'ONLY_OUTPUT_DIRECTORY_ARGUMENT_ALLOWED')
    require(os.environ.get('GITHUB_REPOSITORY') == PIN['repository']
            and os.environ.get('GITHUB_REF') == 'refs/heads/' + BRANCH, 'EXECUTION_REPOSITORY_OR_BRANCH_CHANGED')
    admit_source()
    env = gh_env()
    docs = [get_metadata(path, env) for path in (
        'actions/runs/' + str(PIN['run_id']), 'git/commits/' + PIN['head_sha'],
        'actions/jobs/' + str(PIN['job_id']), 'actions/artifacts/' + str(PIN['artifact_id']))]
    admit_metadata(*docs)
    manifest = recover(Path(argv[0]), env)
    print(json.dumps(dict(status=manifest['status'], verified_archive_bytes=PIN['archive_bytes'],
                         consecutive_parts=2, new_financial_execution_credit=0)))


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Refused as error:
        print('ORIGINAL_SPLIT_REFUSED:' + str(error), file=sys.stderr)
        sys.exit(1)
    except Exception:
        # Never print external metadata, subprocess stderr, tokens or URLs.
        print('ORIGINAL_SPLIT_FAILED:NON_SENSITIVE_DIAGNOSTIC_ONLY', file=sys.stderr)
        sys.exit(1)
