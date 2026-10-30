"""Exact Root-qualified14 ZIP/SIX producer. No ERP or database imports.

The ZIP lives outside the checkout. Six raw files are bounded immutable inputs,
never source declarations or invented PASS receipts. Partial stages fail closed.
"""
from hashlib import sha256
from pathlib import Path, PurePosixPath
import argparse
import os
import shutil
import stat
import subprocess
import tempfile
import zipfile
from midnight_common import ROOT, HERE, NS, canonical, document, exact, regular
import midnight_gate as gate
import parent_binding as binding

ARCHIVE = dict(artifact_id=12947563874, bytes=8472775,
    sha256='567e64545493d4806fa613b1306b4fe8c2f70a2ebb327fc60b709737813e5a60',
    expected_members=119, selected_root_names=binding.RAW_NAMES)


def configuration(root=ROOT, cfg=None):
    cfg = document(regular(root, NS + 'CONFIG.json').read_bytes()) if cfg is None else cfg
    parent, _ = gate.selected(cfg)
    if canonical(cfg.get('accepted_parent14_archive')) != canonical(ARCHIVE):
        raise ValueError('MIDNIGHT_EXACT_ROOT_QUALIFIED14_ARCHIVE_REQUIRED')
    if cfg.get('root_qualification_receipt') != dict(path=binding.ROOT_RECEIPT, **binding.ROOT_RECEIPT_PIN):
        raise ValueError('MIDNIGHT_EXACT_ROOT_QUALIFICATION_RECEIPT_PIN_REQUIRED')
    return parent['originals']


def present_pins(root=ROOT, cfg=None, *, required=False):
    expected = configuration(root, cfg)
    present = {}
    # Check every ancestor, including an empty/absent stage with a linked parent.
    for item in expected.values():
        target = Path(root)
        for part in PurePosixPath(item['path']).parts:
            target = target / part
            if target.is_symlink():
                raise ValueError('MIDNIGHT_SOURCE_SYMLINK:' + item['path'])
        if target.exists():
            raw = regular(root, item['path']).read_bytes()
            exact(raw, item['raw'])
            present[item['path']] = item['raw']
    if present and len(present) != 6:
        raise ValueError('MIDNIGHT_PARTIAL_ACCEPTED14_SIX_RAW_STAGE_REFUSED')
    if required and len(present) != 6:
        raise ValueError('MIDNIGHT_EXACT_ACCEPTED14_SIX_RAW_STAGE_REQUIRED')
    return present


def external_regular(path):
    path = Path(path).absolute()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise ValueError('MIDNIGHT_ARCHIVE_SYMLINK_REFUSED')
    if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('MIDNIGHT_REGULAR_QUALIFIED14_ARCHIVE_REQUIRED')
    return path


def verify_archive(archive, root=ROOT, cfg=None):
    expected = configuration(root, cfg)
    archive = external_regular(archive)
    exact(archive.read_bytes(), {key: ARCHIVE[key] for key in ('bytes', 'sha256')})
    selected = {}
    with zipfile.ZipFile(archive) as source:
        members = source.infolist()
        if len(members) != ARCHIVE['expected_members'] or len({m.filename for m in members}) != len(members):
            raise ValueError('MIDNIGHT_QUALIFIED14_EXACT119_UNIQUE_ZIP_MEMBERS_REQUIRED')
        for member in members:
            name = PurePosixPath(member.filename)
            mode = member.external_attr >> 16
            if (name.is_absolute() or '..' in name.parts or '\\' in member.filename
                    or str(name) != member.filename or stat.S_ISLNK(mode)):
                raise ValueError('MIDNIGHT_QUALIFIED14_UNSAFE_ZIP_MEMBER')
        # Exact top-level names prevent a retained-parent basename collision.
        for key, name in ARCHIVE['selected_root_names'].items():
            info = source.getinfo(name)
            pin = expected[key]['raw']
            if info.is_dir() or info.file_size != pin['bytes']:
                raise ValueError('MIDNIGHT_QUALIFIED14_SELECTED_RAW_SIZE_REQUIRED:' + name)
            digest = sha256(); count = 0
            with source.open(info) as stream:
                for chunk in iter(lambda: stream.read(65536), b''):
                    digest.update(chunk); count += len(chunk)
            if dict(bytes=count, sha256=digest.hexdigest()) != pin:
                raise ValueError('MIDNIGHT_QUALIFIED14_SELECTED_RAW_HASH_REQUIRED:' + name)
            selected[key] = dict(member=name, path=expected[key]['path'], **pin)
    return selected


def stage(archive, root=ROOT, cfg=None):
    root = Path(root)
    selected = verify_archive(archive, root, cfg)
    existing = present_pins(root, cfg)
    if len(existing) == 6:
        return dict(status='EXACT_EXISTING_SIX_RAW_INPUTS_VERIFIED', originals=selected)
    # Prepare all SIX outside the source namespace before exposing any of them.
    with tempfile.TemporaryDirectory(prefix='midnight-qualified14-six-') as name:
        prepared = Path(name)
        with zipfile.ZipFile(archive) as source:
            for key, item in selected.items():
                with source.open(item['member']) as src, (prepared / key).open('xb') as dst:
                    shutil.copyfileobj(src, dst, 65536)
                exact((prepared / key).read_bytes(), dict(bytes=item['bytes'], sha256=item['sha256']))
        folder = root / NS / 'accepted-parent14'
        folder.mkdir(exist_ok=True)
        for key, item in selected.items():
            destination = root / item['path']
            if destination.exists() or destination.is_symlink():
                raise ValueError('MIDNIGHT_NO_REPLACE_EXISTING_ACCEPTED14_INPUT:' + item['path'])
            # Exclusive regular creation: never overwrite a racing leaf/link.
            with (prepared / key).open('rb') as src, destination.open('xb') as dst:
                shutil.copyfileobj(src, dst, 65536)
    present_pins(root, cfg, required=True)
    return dict(status='EXACT_QUALIFIED14_SIX_RAW_INPUTS_STAGED', originals=selected)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    select = parser.add_mutually_exclusive_group(required=True)
    select.add_argument('--archive', type=Path)
    select.add_argument('--get', action='store_true')
    args = parser.parse_args(argv)
    configuration()  # NULL/foreign identity refuses before any GET/ERP/DB.
    import source_check
    source_check.check()  # All actual source bytes/modes before producer work.
    if args.get:
        with tempfile.TemporaryDirectory(prefix='midnight-qualified14-original-') as name:
            target = Path(name) / 'ORIGINAL.zip'
            raw = subprocess.check_output(['gh', 'api',
                'repos/Hanjay6688/-erp-garment-ux/actions/artifacts/12947563874/zip'])
            exact(raw, {key: ARCHIVE[key] for key in ('bytes', 'sha256')})
            target.write_bytes(raw)
            result = stage(target)
    else:
        result = stage(args.archive)
    source_check.check(require_bound=True)
    print(canonical(dict(result, actual_Native_cases=0, production_go=False)))


if __name__ == '__main__':
    main()
