"""Local sealing of two scoped read sites plus explicit source-binding changes."""
from hashlib import sha256
from pathlib import Path
import difflib
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def changes(old, current):
    a, b = old.decode().splitlines(keepends=True), current.decode().splitlines(keepends=True)
    return [dict(before=''.join(a[group[0][1]:group[-1][2]]), after=''.join(b[group[0][3]:group[-1][4]]), count=1)
        for group in difflib.SequenceMatcher(None, a, b, autojunk=False).get_grouped_opcodes(3)]


def main():
    if os.environ.get('CI'):
        raise ValueError('S03_ORDINARY_LOCAL_SEAL_ONLY')
    spec = importlib.util.spec_from_file_location('s03_ordinary_snapshot_seal', HERE / 'ordinary_snapshot_delta.py')
    delta = importlib.util.module_from_spec(spec); spec.loader.exec_module(delta)
    git = lambda *args: subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), *args],
        env=dict(os.environ, GIT_NO_LAZY_FETCH='1'))
    rows = []
    for name in delta.FILES:
        old = (HERE / 'retained-ae837' / name).read_bytes(); current = (HERE / name).read_bytes()
        if old != git('show', delta.PARENT + ':' + str((HERE / name).relative_to(ROOT))):
            raise ValueError('S03_ORDINARY_RETAINED_PARENT_CHANGED')
        rows.append(dict(name=name, before=delta.pin(old), after=delta.pin(current),
            changes=delta.CHANGES if name == 'fixture.py' else changes(old, current)))
    plan = dict(contract='cp7.s03.browser4.ordinary-snapshot-utc-successor.v1', parent_commit=delta.PARENT,
        parent_tree=git('rev-parse', delta.PARENT + '^{tree}').decode().strip(), files=rows,
        counted_changes=sum(len(row['changes']) for row in rows), fixture_read_scopes=2,
        unchanged={name: delta.pin((HERE / name).read_bytes()) for name in delta.UNCHANGED},
        evidence='evidence/ORDINARY_SNAPSHOT_ACTUAL4D_SCAN.json', actual_browser_credit=0,
        prior_public_run_preserved=dict(run_id=41044533553, job_id=124025266832,
            status_at_preparation='ACTIVE_NOT_CANCELLED_OR_REPLACED'), production_go=False)
    (HERE / 'ORDINARY_SNAPSHOT_DELTA.json').write_text(json.dumps(plan, indent=2) + '\n')
    raw = (HERE / 'retained-ae837/ADAPTATIONS.json').read_bytes()
    if raw != git('show', delta.PARENT + ':' + str((HERE / 'ADAPTATIONS.json').relative_to(ROOT))):
        raise ValueError('S03_ORDINARY_PREVIOUS_ADAPTATIONS_CHANGED')
    inherited = json.loads(raw)
    for row in inherited['files']:
        if row['derived'] == str((HERE / 'fixture.py').relative_to(ROOT)):
            old, current = (ROOT / row['parent']).read_bytes(), (HERE / 'fixture.py').read_bytes()
            if len(old) != row['parent_bytes'] or sha256(old).hexdigest() != row['parent_sha256']:
                raise ValueError('S03_ORDINARY_ORIGINAL_FROZEN_PARENT_CHANGED')
            row.update(derived_sha256=sha256(current).hexdigest(), changes=changes(old, current))
    inherited['counted_changes'] = sum(len(row['changes']) for row in inherited['files'])
    (HERE / 'ADAPTATIONS.json').write_text(json.dumps(inherited, indent=2) + '\n')
    print(json.dumps(delta.verify()))


if __name__ == '__main__':
    main()
