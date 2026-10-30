"""Writer-only source freeze; runtime never rewrites admission."""
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import transition as t


def bind():
    if os.environ.get('CI'):
        raise ValueError('SKU_MATERIAL_LOCK_CI_CANNOT_FREEZE')
    files = {}
    for path in sorted(t.HERE.rglob('*')):
        if (not path.is_file() or path == t.HERE / 'SOURCE.json'
                or '__pycache__' in path.parts or path.suffix == '.pyc'):
            continue
        if path.is_symlink():
            raise ValueError('SKU_MATERIAL_LOCK_FREEZE_SYMLINK')
        files[str(path.relative_to(t.ROOT))] = t.pin(path.read_bytes())
    local_paths = ['scripts/cp7_sku_pair_conversion/recovery_local/' + name for name in
                   ['check.mjs', 'fixture.sql', 'NATIVE_UNCHANGED.json', 'NATIVE_PROFILE_CATALOG.json']]
    value = dict(status='PREPARED_NATIVE_FINANCIAL_0', base_head=t.BASE, base_tree=t.TREE,
                 sql_before=t.pin(t.original(t.ROOT, t.SQL)), sql_after=t.pin((t.ROOT/t.SQL).read_bytes()),
                 old_source43=t.pin((t.ROOT/t.OLD_SOURCE).read_bytes()),
                 local_originals={name:t.pin(t.original(t.ROOT,name)) for name in local_paths},
                 files=files, exact_SQL_hunks=1, unchanged_captures=8,
                 unchanged_private_functions=18, private_function_count=19,
                 changed_private_bodies=['cp7_sku_conversion.recovery_preflight_v1'],
                 unchanged_private_tables=5,
                 unchanged_original_callbacks=23, planned_total_actual_cases=27,
                 added_material_locks='Only valuation material from already BCLOT-locked return lot; NOWAIT.',
                 existing_MOVING_native_wait='Preserved before preflight; command is not globally no-wait.',
                 real_NONE_material_holder_required=True, Native_financial=0,
                 real_two_session=0, default_adoption=False, production_go=False,
                 independent_acceptance=False)
    (t.HERE/'SOURCE.json').write_text(json.dumps(value,indent=2)+'\n')
    return t.admitted()


if __name__ == '__main__':
    if sys.argv[1:] != ['--writer-freeze']:
        raise ValueError('SKU_MATERIAL_LOCK_WRITER_FREEZE_ONLY')
    print(json.dumps(bind(),sort_keys=True))
