"""Local source sealing only; keeps the 4d and all older retained inputs exact."""
from hashlib import sha256
from pathlib import Path
import difflib
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def changes(before, after):
    a, b = before.decode().splitlines(keepends=True), after.decode().splitlines(keepends=True)
    return [dict(before=''.join(a[group[0][1]:group[-1][2]]),
        after=''.join(b[group[0][3]:group[-1][4]]), count=1)
        for group in difflib.SequenceMatcher(None, a, b, autojunk=False).get_grouped_opcodes(3)]


def main():
    if os.environ.get('CI'):
        raise ValueError('S03_BROWSER4_CURRENT_RIGHTS_SEAL_IN_CI_FORBIDDEN')
    spec = importlib.util.spec_from_file_location('s03_rights_delta_seal', HERE / 'rights_delta.py')
    delta = importlib.util.module_from_spec(spec); spec.loader.exec_module(delta)
    delta.policy()
    git = lambda *args: subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), *args],
        env=dict(os.environ, GIT_NO_LAZY_FETCH='1'))
    pin = lambda raw: dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
    rows = []
    for name in ('fixture.py', 'cases.mjs'):
        old = (HERE / 'retained-4d968' / name).read_bytes(); new = (HERE / name).read_bytes()
        if old != git('show', delta.PARENT + ':' + str((HERE / name).relative_to(ROOT))):
            raise ValueError('S03_BROWSER4_RETAINED_4D_SOURCE_CHANGED')
        rows.append(dict(name=name, before=pin(old), after=pin(new), changes=changes(old, new)))
    plan = dict(contract='cp7.s03.browser4.current-rights-successor.v1', parent_commit=delta.PARENT,
        parent_tree=git('rev-parse', delta.PARENT + '^{tree}').decode().strip(),
        policy_sha256=delta.POLICY_SHA256, files=rows, counted_changes=sum(len(row['changes']) for row in rows),
        unchanged_callbacks=delta.callbacks((HERE / 'retained-4d968/cases.mjs').read_text(), (HERE / 'cases.mjs').read_text()),
        view_only_Owner_representable=False, actual_view_only_Owner_credit=0,
        actual_new_browser_credit=0, product_policy_changed=False,
        boundary='Full no-effect census starts AFTER the authorized real public Owner-to-ADMIN transition and its exact replay.',
        first_failure='FIRST_4D968_FAILURE.json')
    (HERE / 'CURRENT_RIGHTS_DELTA.json').write_text(json.dumps(plan, indent=2) + '\n')
    retained = (HERE / 'retained-4d968/ADAPTATIONS.json').read_bytes()
    if retained != git('show', delta.PARENT + ':' + str((HERE / 'ADAPTATIONS.json').relative_to(ROOT))):
        raise ValueError('S03_BROWSER4_RETAINED_4D_ADAPTATIONS_CHANGED')
    inherited = json.loads(retained)
    for row in inherited['files']:
        if row['derived'] in {str((HERE / name).relative_to(ROOT)) for name in ('fixture.py', 'cases.mjs')}:
            old, new = (ROOT / row['parent']).read_bytes(), (ROOT / row['derived']).read_bytes()
            if len(old) != row['parent_bytes'] or sha256(old).hexdigest() != row['parent_sha256']:
                raise ValueError('S03_BROWSER4_OLDER_FROZEN_SOURCE_CHANGED')
            row.update(derived_sha256=sha256(new).hexdigest(), changes=changes(old, new))
    inherited['counted_changes'] = sum(len(row['changes']) for row in inherited['files'])
    (HERE / 'ADAPTATIONS.json').write_text(json.dumps(inherited, indent=2) + '\n')
    print(json.dumps(delta.verify()))


if __name__ == '__main__':
    main()
