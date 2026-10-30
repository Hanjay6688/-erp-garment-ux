"""Exact additive source check; no imports of ERP/DB/browser runtime."""
from hashlib import sha1, sha256
from pathlib import Path
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = 'e4915c0b7b8b3cd04293ef8289317ae93cf46597'
BASE_TREE = '1e27c59bdbf0094b2e9142e4afa15c7df7a3c034'
PREFIX = 'scripts/current-s05-sku-composition-qualification/'


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def entries(root, revision):
    out = {}
    for row in git(root, 'ls-tree', '-rz', revision).split(b'\0'):
        if not row:
            continue
        info, name = row.split(b'\t', 1)
        mode, kind, oid = info.decode().split()
        if kind != 'blob':
            raise ValueError('S05_SKU_NONBLOB_SOURCE_REQUIRED')
        out[name.decode()] = (mode, oid)
    return out


def physical(path):
    if path.is_symlink():
        raw, mode = os.fsencode(os.readlink(path)), '120000'
    else:
        raw = path.read_bytes()
        mode = '100755' if path.stat().st_mode & 0o111 else '100644'
    return mode, sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def preflight(root=ROOT, *, require_clean=True):
    root = Path(root)
    pins = json.loads((root/PREFIX/'SOURCE.json').read_bytes())
    retained = json.loads((root/PREFIX/'RETAINED.json').read_bytes())
    if pins['base'] != BASE or pins['base_tree'] != BASE_TREE:
        raise ValueError('S05_SKU_EXACT_UNIFIED_SOURCE_PARENT_REQUIRED')
    if git(root, 'rev-parse', BASE+'^{tree}').decode().strip() != BASE_TREE:
        raise ValueError('S05_SKU_BASE_TREE_REQUIRED')
    if (retained['head'] != '519d1760a3bad06a346b3d4b3cc0203664615634'
            or retained['tree'] != '15ccd8c9b5eb796724cfb39e3b4c8415f9c952bf'
            or git(root, 'rev-parse', retained['head']+'^{tree}').decode().strip() != retained['tree']):
        raise ValueError('S05_SKU_EXACT_QUALIFIED_FIXTURE_SOURCE_REQUIRED')
    allowed = set(retained['files']) | {name for name in pins['files'] if name.startswith(PREFIX)} | {PREFIX+'SOURCE.json'}
    base = entries(root, BASE)
    current = entries(root, 'HEAD')
    if any(current.get(name) != entry or physical(root/name) != entry for name, entry in base.items()):
        raise ValueError('S05_SKU_BASE_FILE_OR_MODE_CHANGED')
    if set(current)-set(base)-allowed:
        raise ValueError('S05_SKU_UNDECLARED_TRACKED_ADDITION')
    if require_clean:
        if git(root, 'status', '--porcelain', '--untracked-files=no').strip():
            raise ValueError('S05_SKU_CLEAN_COMMITTED_SOURCE_REQUIRED')
        if set(current) != set(base) | allowed:
            raise ValueError('S05_SKU_COMPLETE_COMMITTED_ADDITIONS_REQUIRED')
    for name, expected in pins['files'].items():
        if sha256((root/name).read_bytes()).hexdigest() != expected:
            raise ValueError('S05_SKU_SOURCE_PIN_CHANGED: '+name)
    qualified_files = entries(root, retained['head'])
    for name, expected in retained['files'].items():
        raw = (root/name).read_bytes()
        if len(raw) != expected['bytes'] or sha256(raw).hexdigest() != expected['sha256']:
            raise ValueError('S05_SKU_RETAINED_HELPER_CHANGED: '+name)
        if physical(root/name) != qualified_files.get(name):
            raise ValueError('S05_SKU_RETAINED_HELPER_NOT_519D: '+name)
    composition = json.loads((root/'scripts/cp7_s05_sku_composition/SOURCE.json').read_bytes())
    for name, expected in composition['files'].items():
        if sha256((root/name).read_bytes()).hexdigest() != expected:
            raise ValueError('S05_SKU_EXISTING_COMPOSITION_CHANGED: '+name)
    return dict(status='S05_SKU_ADDITIVE_NATIVE_COMPONENT_SOURCE_ONLY',
        base=BASE, base_tree=BASE_TREE, unchanged_base_files=len(base),
        exact_qualified_519d_helpers=len(retained['files']),
        unchanged_existing_S05_pins=len(composition['files']),
        exact_pinned_sources=len(pins['files']), clean_committed=require_clean,
        actual_SKU27_prerequisite_admitted=False,
        current_combined_Native_browser_cases=0,
        production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    print(json.dumps(preflight(), indent=2))
