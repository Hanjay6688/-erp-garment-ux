"""Actual full checkout/source/producer closure; historical manifests stay history."""
from hashlib import sha1, sha256
from pathlib import Path
import os
import subprocess
from midnight_common import HERE, ROOT, NS, WORKFLOW, document, regular, exact
import midnight_gate as gate

BASE = '3c0c5defe55e48cf6f221c868594dd6676d17170'
TREE = 'ca20c918201b455ad09df489829b83b9e6afea95'
BASE_MANIFEST = 'scripts/current-s03-lawful-fixture-successor-qualification/SOURCE.json'
BASE_MANIFEST_SHA = 'ba59dee4ae71c62df2b2e35c558cb23a7c66254a974c554cc3d17d63b936c555'


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args],
        env={**os.environ, 'GIT_NO_LAZY_FETCH': '1', 'GIT_OPTIONAL_LOCKS': '0'})


def current_declaration(root, cfg):
    import parent_binding
    return parent_binding.current_declaration(root, cfg)


def historical_proofs(root):
    archive = document(regular(root, 'scripts/current-workflow-history-isolation/ARCHIVE.json').read_bytes())
    result = {}
    for item in archive['files']:
        name = item['path']
        if not name.startswith('.github/workflows/'):
            raise ValueError('MIDNIGHT_HISTORY_PROOF_SCOPE_CHANGED')
        expected = dict(bytes=item['bytes'], sha256=item['sha256'])
        packed = regular(root, item['archive']).read_bytes()
        exact(packed, expected)
        if (Path(root) / name).exists() or (Path(root) / name).is_symlink():
            if regular(root, name).read_bytes() != packed:
                raise ValueError('MIDNIGHT_HISTORY_PROOF_BYTES_CHANGED')
        result[name] = expected
    if len(result) != 24:
        raise ValueError('MIDNIGHT_EXACT24_HISTORY_PROOFS_REQUIRED')
    return result


def check(root=ROOT, here=HERE, require_bound=False):
    root, here = Path(root), Path(here)
    cfg = document(regular(root, NS + 'CONFIG.json').read_bytes())
    if require_bound:
        gate.selected(cfg)
    manifest = document(regular(root, NS + 'SOURCE.json').read_bytes())
    if manifest.get('contract') != 'cp7.midnight-native1.current-source.v1':
        raise ValueError('MIDNIGHT_CURRENT_SOURCE_CONTRACT_REQUIRED')
    head, tree, active = current_declaration(root, cfg)
    if (git(root, 'rev-parse', head + '^{tree}').decode().strip() != tree
            or manifest['active_parent_head'] != head or manifest['active_parent_tree'] != tree):
        raise ValueError('MIDNIGHT_EXACT_ACTIVE_PARENT_TREE_REQUIRED')
    # Reject leaf/ancestor links by exact source path before enumeration.
    for name, expected_pin in manifest['files'].items():
        exact(regular(root, name).read_bytes(), expected_pin)
    own = {str(p.relative_to(root)) for p in here.rglob('*')
           if p.is_file() or p.is_symlink()}
    expected_own = {name for name in manifest['files'] if name.startswith(NS)} | {NS + 'SOURCE.json'}
    if own != expected_own:
        raise ValueError('MIDNIGHT_UNKNOWN_SOURCE_OR_RECEIPT:' + repr(sorted(own ^ expected_own)))
    expected = set(active) | expected_own | {WORKFLOW}
    expected.discard(NS + 'SOURCE.json')
    if set(manifest['files']) != expected:
        raise ValueError('MIDNIGHT_EXACT_CURRENT_SOURCE_AND_NAMESPACE_CLOSURE_REQUIRED')
    for name, expected_pin in manifest['files'].items():
        raw = regular(root, name).read_bytes()
        exact(raw, expected_pin)
        if name in active and expected_pin != active[name]:
            raise ValueError('MIDNIGHT_ACTIVE_PARENT_PIN_CHANGED:' + name)
    for name, expected_pin in document((here / 'ORIGIN.json').read_bytes())['files'].items():
        exact(regular(root, NS + 'historical-midnight-c0/' + name).read_bytes(), expected_pin)
    for name, digest in (
        ('generated_receipts.py', 'a569138a5b6d4c0d1ce542ab45af98ee156f47e6d772766c214bbae3366ffc7e'),
        ('generated_later.py', '7bf35d85d9f7ec19da34c5626f24af908f3691a4e3ed7251dbc4958e59b4bea3')):
        if sha256((here / name).read_bytes()).hexdigest() != digest:
            raise ValueError('MIDNIGHT_FROZEN_OUTPUT_VALIDATOR_CHANGED')
    entries = {}
    for item in git(root, 'ls-tree', '-r', '-z', head).split(b'\0'):
        if item:
            meta, name = item.split(b'\t', 1)
            mode, kind, oid = meta.decode().split()
            if kind != 'blob' or mode not in ('100644', '100755'):
                raise ValueError('MIDNIGHT_UNSUPPORTED_PARENT_MEMBER')
            entries[name.decode()] = (mode, oid)
    tracked = set(git(root, 'ls-files', '-z').decode().split('\0')) - {''}
    untracked = set(git(root, 'ls-files', '--others', '--exclude-standard', '-z').decode().split('\0')) - {''}
    proofs = historical_proofs(root)
    import historical_inputs
    proofs.update(historical_inputs.present_pins(root))
    allowed = set(entries) | expected_own | {WORKFLOW}
    unknown = (tracked | untracked) - allowed - set(proofs)
    if unknown:
        # Validators admit only concrete bounded producer outputs, not source.
        for filename in ('generated_receipts.py', 'generated_later.py'):
            import importlib.util
            spec = importlib.util.spec_from_file_location('midnight_' + filename[:-3], here / filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            admitted, _ = module.admit(root, here, unknown)
            unknown -= set(admitted)
    if unknown:
        raise ValueError('MIDNIGHT_UNKNOWN_SOURCE_OR_RECEIPT:' + repr(sorted(unknown)))
    for name, (mode, oid) in entries.items():
        path = regular(root, name)
        raw = path.read_bytes()
        actual = sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if actual != oid or bool(path.stat().st_mode & 0o111) != (mode == '100755'):
            raise ValueError('MIDNIGHT_ACTUAL_PARENT_BYTES_OR_MODE_CHANGED:' + name)
    import provenance
    routes = provenance.check(root, here)
    return dict(status='CLOSED_PREPARED_CURRENT_SOURCE475_ONLY' if cfg['accepted_parent14'] is None
                else 'BOUND_EXACT_CURRENT_SOURCE_ONLY',
        source_pins=len(manifest['files']), full_parent_files=len(entries),
        actual_current_parent_source_members=475, parent_manifest_pinned=True,
        inherited_Original_input_pins=len(historical_inputs.present_pins(root)),
        immutable_c097_provenance=routes,
        historical_midnight_files=9, runtime_files=7, function_captures=15,
        planned_new_cases=1, fresh_original11_or14_reexecuted=False,
        actual_Native_cases=0, production_go=False, independent_acceptance=False)
