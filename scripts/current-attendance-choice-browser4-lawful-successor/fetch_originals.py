"""Immutable approved artifact only; no ERP/DB or arbitrary download endpoint."""
from pathlib import Path
from hashlib import sha256
import argparse
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('s03_browser4_exact_accepted_inputs', HERE / 'accepted_inputs.py')
inputs = importlib.util.module_from_spec(spec); spec.loader.exec_module(inputs)
REPO = 'repos/Hanjay6688/-erp-garment-ux'


def api(path):
    # Neither tokens nor signed redirect URLs are printed or persisted.
    return subprocess.check_output(['gh', 'api', REPO + path])


def validate_metadata(run, job, artifact):
    if (run.get('id') != inputs.RUN or run.get('head_sha') != inputs.HEAD
            or run.get('status') != 'completed' or run.get('conclusion') != 'success'
            or run.get('run_attempt') != 1
            or run.get('path') != '.github/workflows/cp7-s03-lawful-fixture-native14.yml'
            or job.get('id') != inputs.JOB or job.get('run_id') != inputs.RUN
            or job.get('head_sha') != inputs.HEAD or job.get('status') != 'completed'
            or job.get('conclusion') != 'success'
            or artifact.get('id') != inputs.ARTIFACT or artifact.get('expired') is not False
            or artifact.get('name') != 'cp7-a-s03-lawful-fixture-native14-1'
            or artifact.get('workflow_run', {}).get('id') != inputs.RUN
            or artifact.get('workflow_run', {}).get('head_sha') != inputs.HEAD
            or artifact.get('size_in_bytes') != inputs.ARCHIVE['bytes']
            or artifact.get('digest') != 'sha256:' + inputs.ARCHIVE['sha256']):
        raise ValueError('S03_BOUND_IMMUTABLE_RUN_JOB_ARTIFACT_METADATA_REQUIRED')


def materialize(rawzip, acquisition):
    if dict(bytes=len(rawzip), sha256=sha256(rawzip).hexdigest()) != inputs.ARCHIVE:
        raise ValueError('S03_BOUND_EXACT_ORIGINAL_ARCHIVE_REQUIRED')
    cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
    _, rawfiles = inputs.static(ROOT, HERE, cfg)
    destination = ROOT / inputs.PREFIX
    if destination.exists() or destination.is_symlink():
        # Replays must preserve all first bytes; no partial directory repair.
        inputs.present(ROOT, HERE, cfg, required=True)
        return dict(status='EXACT_FIRST_SIX_ORIGINAL_BYTES_PRESERVED', new_Native_Auth_browser_credit=0)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Atomic publication after all byte/hash/path/CRC checks. Staging is kept
    # outside the checkout, so source admission can never waive a partial tree.
    staging = Path(tempfile.mkdtemp(prefix='s03_actual14_six_originals_', dir=os.environ.get('RUNNER_TEMP')))
    try:
        with zipfile.ZipFile(io.BytesIO(rawzip)) as archive:
            members = archive.infolist()
            if len(members) != 119 or len({item.filename for item in members}) != 119 or archive.testzip() is not None:
                raise ValueError('S03_BOUND_EXACT119_ORIGINAL_MEMBERS_CRC_REQUIRED')
            for item in members:
                path = Path(item.filename)
                if path.is_absolute() or '..' in path.parts or '\\' in item.filename or item.is_dir():
                    raise ValueError('S03_BOUND_ORIGINAL_ARCHIVE_PATH_REQUIRED')
            for relative, expected in rawfiles.items():
                name = relative[len(inputs.PREFIX):]
                if name not in archive.namelist():
                    raise ValueError('S03_BOUND_EXACT_SELECTED_RAW_MEMBER_REQUIRED:' + name)
                value = archive.read(name)
                if dict(bytes=len(value), sha256=sha256(value).hexdigest()) != expected:
                    raise ValueError('S03_BOUND_ACTUAL_RAW_MEMBER_BYTES_CHANGED:' + name)
                (staging / name).write_bytes(value)
        record = inputs.input_receipt(ROOT, HERE, acquisition)
        (staging / 'INPUT_RECEIPT.json').write_text(json.dumps(record, indent=2) + '\n')
        staging.rename(destination)
        inputs.present(ROOT, HERE, cfg, required=True)
    finally:
        if staging.exists(): shutil.rmtree(staging)
    return dict(status='IMMUTABLE_ARCHIVE_AND_SIX_ACTUAL_RAW_ORIGINALS_MATERIALIZED',
        raw_inputs=6, archive_sha256=inputs.ARCHIVE['sha256'], acquisition=acquisition,
        new_Native_Auth_browser_credit=0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root-verified-local-replay', type=Path)
    args = parser.parse_args(argv)
    if args.root_verified_local_replay is not None:
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            raise ValueError('S03_BOUND_LOCAL_REPLAY_IS_NOT_CI_ARTIFACT_GET')
        # The local bytes must still equal the one immutable approved archive.
        result = materialize(args.root_verified_local_replay.read_bytes(), 'ROOT_VERIFIED_LOCAL_REPLAY_NO_GET')
    else:
        run = json.loads(api('/actions/runs/' + str(inputs.RUN)))
        job = json.loads(api('/actions/jobs/' + str(inputs.JOB)))
        artifact = json.loads(api('/actions/artifacts/' + str(inputs.ARTIFACT)))
        validate_metadata(run, job, artifact)
        result = materialize(api('/actions/artifacts/' + str(inputs.ARTIFACT) + '/zip'), 'IMMUTABLE_GITHUB_ARTIFACT')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
