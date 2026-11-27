"""Recheck the six archived Afui15 originals without uploading their contents."""

import argparse
from hashlib import file_digest, sha256
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parent
PARENT = ROOT / 'current-mandor-shop-native-qualification'
REPOSITORY = 'Hanjay6688/-erp-garment-ux'
CHUNK_BYTES = 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', f'repos/{REPOSITORY}/{path}']))


def parent_receipt():
    sys.path.insert(0, str(PARENT))
    from admission import parent

    return parent((PARENT / 'AFUI15_PARENT_ROOT_ACTUAL_INTAKE.json').read_bytes())


def verify_github(parent):
    run_id, job_id, artifact_id = (parent[name] for name in ('run_id', 'job_id', 'artifact_id'))
    run = api(f'actions/runs/{run_id}')
    job = api(f'actions/jobs/{job_id}')
    artifact = api(f'actions/artifacts/{artifact_id}')
    require((run['id'], run['head_sha'], run['run_attempt'], run['status'], run['conclusion'])
            == (run_id, parent['head'], 1, 'completed', 'success'), 'Afui run changed')
    require((job['id'], job['run_id'], job['head_sha'], job['status'], job['conclusion'])
            == (job_id, run_id, parent['head'], 'completed', 'success'), 'Afui job changed')
    require((artifact['id'], artifact['expired'], artifact['size_in_bytes'], artifact['digest'],
             artifact['workflow_run']['id'], artifact['workflow_run']['head_sha'])
            == (artifact_id, False, parent['archive']['bytes'], 'sha256:' + parent['archive']['sha256'],
                run_id, parent['head']), 'Afui artifact metadata changed')


def verify_archive(path, parent):
    expected = parent['archive']
    require(path.stat().st_size == expected['bytes'], 'Afui ZIP size differs')
    with path.open('rb') as stream:
        require(file_digest(stream, 'sha256').hexdigest() == expected['sha256'], 'Afui ZIP hash differs')
    originals = parent['originals']
    verified = {}
    with ZipFile(path) as archive:
        members = archive.infolist()
        names = {member.filename for member in members}
        require(len(names) == len(members) == expected['members'], 'Afui ZIP member count differs')
        require(originals.keys() <= names, 'Afui ZIP is missing an original')
        for member in members:
            name = member.filename
            member_path = PurePosixPath(name)
            require(not member_path.is_absolute() and '..' not in member_path.parts
                    and str(member_path) == name and '\\' not in name
                    and not stat.S_ISLNK(member.external_attr >> 16), 'Unsafe Afui ZIP member')
            pin = originals.get(name)
            if pin:
                require(member.file_size == pin['bytes'], 'Afui original size differs: ' + name)
            digest = sha256()
            with archive.open(member) as stream:
                while chunk := stream.read(CHUNK_BYTES):  # Reading to EOF validates each member CRC.
                    if pin:
                        digest.update(chunk)
            if pin:
                require(digest.hexdigest() == pin['sha256'], 'Afui original hash differs: ' + name)
                verified[name] = pin
    return verified


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('receipt', type=Path)
    args = parser.parse_args()
    parent = parent_receipt()
    verify_github(parent)
    with args.archive.open('xb') as download:
        subprocess.run(['gh', 'api', f'repos/{REPOSITORY}/actions/artifacts/{parent["artifact_id"]}/zip'],
                       stdout=download, check=True)
    originals = verify_archive(args.archive, parent)
    with args.receipt.open('x') as receipt:
        json.dump({'head': parent['head'], 'run_id': parent['run_id'], 'job_id': parent['job_id'],
                   'artifact_id': parent['artifact_id'], 'archive': parent['archive'],
                   'originals_verified': originals, 'fresh_erp_cases': 0, 'production_go': False}, receipt, indent=2)
        receipt.write('\n')


if __name__ == '__main__':
    main()
