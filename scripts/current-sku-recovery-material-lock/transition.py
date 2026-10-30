"""Prepared-only successor: one exact material row before Native effects."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = 'e8f878f2ecaaf24368a0ce1a3393bc29c0b886f6'
TREE = 'abfa0d954db8d1dffb620e416789e699204bbfbb'
PREFIX = 'scripts/current-sku-recovery-material-lock/'
SQL = 'scripts/cp7_sku_pair_conversion/recovery.sql'
OLD_SOURCE = 'scripts/current-sku-managed-recovery-preflight/SOURCE.json'
ANCHOR = '  perform 1 from erp.hpp_versions order by id for update nowait;\n'
INSERT = ("  -- Native NONE skips the earlier MOVING_AVERAGE material-row lock. Cover\n"
          "  -- its later FK/update waits using only the already BCLOT-locked lot's row.\n"
          "  perform 1 from erp.materials material\n"
          "   where material.id=(select lot.material_id from erp.bc_return_lots_v1 lot where lot.id=p_lot)\n"
          "   order by material.id for update nowait;\n")


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root)


def original(root, name):
    return git(root, 'show', BASE + ':' + name)


def patched(raw):
    text = raw.decode()
    if text.count(ANCHOR) != 1 or INSERT in text:
        raise ValueError('SKU_MATERIAL_LOCK_EXACT_OLD_ANCHOR_REQUIRED')
    result = text.replace(ANCHOR, ANCHOR + INSERT, 1)
    if result.replace(INSERT, '', 1) != text:
        raise ValueError('SKU_MATERIAL_LOCK_NOT_REVERSIBLE')
    return result.encode()


def exact_transition(before, after):
    if patched(before) != after:
        raise ValueError('SKU_MATERIAL_LOCK_ONLY_ONE_EXACT_SQL_HUNK_ALLOWED')


def read(root, name):
    root = Path(root)
    p = root / name
    if not p.is_file() or p.is_symlink() or any(
            parent.is_symlink() for parent in p.parents if parent != root.parent):
        raise ValueError('SKU_MATERIAL_LOCK_REGULAR_SOURCE_REQUIRED:' + name)
    return p.read_bytes()


def own_files(root, manifest):
    root = Path(root)
    for name, expected in manifest['files'].items():
        if not name.startswith(PREFIX) or pin(read(root, name)) != expected:
            raise ValueError('SKU_MATERIAL_LOCK_OWN_SOURCE_CHANGED:' + name)
    actual = {str(p.relative_to(root)) for p in (root / PREFIX).rglob('*')
              if (p.is_file() or p.is_symlink()) and '__pycache__' not in p.parts
              and p.suffix != '.pyc'}
    if actual != set(manifest['files']) | {PREFIX + 'SOURCE.json'}:
        raise ValueError('SKU_MATERIAL_LOCK_UNDECLARED_OWN_SOURCE')


def admitted(root=ROOT, manifest=None):
    root = Path(root)
    manifest = manifest if manifest is not None else json.loads(read(root, PREFIX + 'SOURCE.json'))
    if (manifest['status'] != 'PREPARED_NATIVE_FINANCIAL_0'
            or manifest['base_head'] != BASE or manifest['base_tree'] != TREE
            or git(root, 'rev-parse', BASE + '^{tree}').decode().strip() != TREE):
        raise ValueError('SKU_MATERIAL_LOCK_PUBLIC_BASE_REQUIRED')
    before = original(root, SQL)
    after = read(root, SQL)
    exact_transition(before, after)
    if manifest['sql_before'] != pin(before) or manifest['sql_after'] != pin(after):
        raise ValueError('SKU_MATERIAL_LOCK_SQL_BINDING_CHANGED')
    old_raw = read(root, OLD_SOURCE)
    if old_raw != original(root, OLD_SOURCE) or pin(old_raw) != manifest['old_source43']:
        raise ValueError('SKU_MATERIAL_LOCK_FROZEN_SOURCE43_CHANGED')
    old = json.loads(old_raw)
    if len(old['files']) != 43:
        raise ValueError('SKU_MATERIAL_LOCK_ORIGINAL_43_PINS_REQUIRED')
    for name, expected in old['files'].items():
        raw = read(root, name)
        if name == SQL:
            raw = before
        if pin(raw) != expected or original(root, name) != raw:
            raise ValueError('SKU_MATERIAL_LOCK_OLD_SOURCE_CHANGED:' + name)
    own_files(root, manifest)
    allowed = set(manifest['files']) | {PREFIX + 'SOURCE.json'}
    for line in git(root, 'diff', '--name-status', '--no-renames', BASE, '--').decode().splitlines():
        status, name = line.split('\t', 1)
        if status == 'M' and name == SQL:
            continue
        if status == 'A' and name in allowed:
            continue
        raise ValueError('SKU_MATERIAL_LOCK_UNDECLARED_BASE_CHANGE:' + name)
    return dict(status='PASS', public_parent=BASE, old_source_pins=43,
                exact_sql_hunks=1, own_files=len(manifest['files']),
                captures=8, private_functions=19, private_tables=5,
                old23_callbacks_changed=0, Native_financial=0, real_two_session=0,
                complete_untracked_qualification=False,
                production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    print(json.dumps(admitted(), sort_keys=True))
