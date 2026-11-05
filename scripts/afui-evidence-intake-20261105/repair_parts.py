"""Repackage only the two already retained segments the connector timed out on."""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import json

from retain import REPO, RUN, ARTIFACT, SIZE, DIGEST, api, copy_stream, metadata, original_context, require, save

INTAKE = 42093272706
INTAKE_HEAD = '2a839c36f19b3958c0414915dc3bebc3ca145528'
MANIFEST_SHA = 'ae234c4cc900aae41475e3839aada81579f105137fe54f4bf7d71eeb333d31b8'
WRAPPERS = {
    1: (13445334165, 'fec3011e8494ce587c3c36c9ef83a544fc108e01c06e62c409a11885e3614dbf'),
    4: (13445888500, 'e4ee0faa79f45315d993020ba67a0eb130dcea2a7ec7120fca1b858e60e18de0'),
}
WRAPPER_BYTES = 419435763
SUBPART_BYTES = 200 * 1024 * 1024


def split_wrapper(path, destination, number, wrapper_id, wrapper_pin):
    with ZipFile(path) as bundle:
        original_manifest = bundle.read('INTAKE_MANIFEST.json')
        require(sha256(original_manifest).hexdigest() == MANIFEST_SHA, 'EXACT_ORIGINAL_TRANSPORT_MANIFEST_REQUIRED')
        manifest = json.loads(original_manifest)
        require(manifest['complete_archive'] == {'bytes': SIZE, 'sha256': DIGEST}
                and manifest['source_run_id'] == RUN and manifest['source_artifact_id'] == ARTIFACT,
                'REPAIR_SOURCE_ORIGINAL_IDENTITY_MISMATCH')
        parent = manifest['parts'][number - 1]
        require(parent['number'] == number and parent['bytes'] == 2 * SUBPART_BYTES
                and len(bundle.namelist()) == 2 and set(bundle.namelist()) == {parent['name'], 'INTAKE_MANIFEST.json'},
                'EXACT_SPLITTABLE_TRANSPORT_MEMBER_REQUIRED')
        whole = sha256()
        slices = []
        directories = []
        with bundle.open(parent['name']) as source:
            for half in (1, 2):
                directory = destination / f'part-{number:03d}-slice-{half}'
                directory.mkdir(parents=True)
                directories.append(directory)
                filename = f'AFUI_COMPLETE_ORIGINAL_PART_{number:03d}_SLICE_{half}.bin'
                digest, remaining = sha256(), SUBPART_BYTES
                with (directory / filename).open('xb') as output:
                    while remaining:
                        raw = source.read(min(remaining, 4 * 1024 * 1024))
                        require(bool(raw), 'REPAIR_SOURCE_SLICE_TRUNCATED')
                        remaining -= len(raw)
                        digest.update(raw)
                        whole.update(raw)
                        output.write(raw)
                slices.append(dict(half=half, name=filename, bytes=SUBPART_BYTES, sha256=digest.hexdigest()))
            require(source.read(1) == b'' and whole.hexdigest() == parent['sha256'], 'REPAIR_EXACT_ORIGINAL_PART_REQUIRED')
    receipt = dict(source_run=RUN, source_artifact=ARTIFACT, original_intake=INTAKE, wrapper_id=wrapper_id,
                   exact_wrapper=wrapper_pin, original_part=parent, slices=slices, original_member_crc_verified=True)
    for directory in directories:
        (directory / 'INTAKE_MANIFEST.json').write_bytes(original_manifest)
        save(directory / 'REPAIR_MANIFEST.json', receipt)
    return receipt


def main():
    root = Path('afui-evidence-intake-20261105/repair')
    with TemporaryDirectory() as temp:
        temporary = Path(temp)
        original_context(temporary, temporary)
        intake = metadata(f'/repos/{REPO}/actions/runs/{INTAKE}', temporary / 'INTAKE_RUN.json')
        require(intake['id'] == INTAKE and intake['head_sha'] == INTAKE_HEAD and intake['run_attempt'] == 1
                and intake['status'] == 'completed' and intake['conclusion'] == 'success', 'EXACT_COMPLETED_INTAKE_RUN_REQUIRED')
        receipts = []
        for number, (artifact, digest) in WRAPPERS.items():
            route = f'/repos/{REPO}/actions/artifacts/{artifact}'
            row = metadata(route, temporary / f'WRAPPER_{number}.json')
            expected = dict(bytes=WRAPPER_BYTES, sha256=digest)
            require(row['id'] == artifact and row['name'] == f'afui-{RUN}-exact-part-{number:03d}'
                    and row['size_in_bytes'] == expected['bytes'] and row['digest'] == 'sha256:' + digest
                    and row['expired'] is False and row['workflow_run']['id'] == INTAKE
                    and row['workflow_run']['head_sha'] == INTAKE_HEAD, 'EXACT_ALREADY_RETAINED_WRAPPER_REQUIRED')
            source = temporary / f'{number}.zip'
            with api(route + '/zip') as incoming, source.open('xb') as output:
                actual = copy_stream(incoming, output, WRAPPER_BYTES)
            require(actual == expected, 'REPAIR_WRAPPER_BYTES_CHANGED')
            receipts.append(split_wrapper(source, root, number, artifact, expected))
    print(json.dumps(dict(status='EXACT_MISSING_TRANSPORT_PARTS_REPACKAGED', receipts=receipts, ERP_commands_executed=0)))


if __name__ == '__main__':
    main()
