"""Writer-only exact historical-observation source transition; never run in CI."""
from hashlib import sha256
from pathlib import Path
import difflib
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENT = '30ee9874d049632050faf53b299a0cd8a11fe9f6'
NAMES = ('fixture.py', 'cases.mjs', 'rights_delta.py', 'ordinary_snapshot_delta.py', 'probe.py',
         'derive_successor.py', 'ADAPTATIONS.json', 'workflow.py', 'README.md', 'workflow.yml',
         'test_bound.py', 'test_contract.py', 'test_current_rights.py', 'test_ordinary_snapshot.py', 'test_oracles.mjs',
         'inherited-output-validation/GENERATED_RECEIPTS.json',
         'inherited-output-validation/LATER_GENERATED_RECEIPTS.json')


def changes(old, current):
    a, b = old.decode().splitlines(keepends=True), current.decode().splitlines(keepends=True)
    return [dict(before=''.join(a[g[0][1]:g[-1][2]]), after=''.join(b[g[0][3]:g[-1][4]]), count=1)
            for g in difflib.SequenceMatcher(None, a, b, autojunk=False).get_grouped_opcodes(3)]


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def main():
    if os.environ.get('CI'):
        raise ValueError('S03_HISTORY_WRITER_LOCAL_FREEZE_ONLY')
    git = lambda *a: subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), *a],
                                            env=dict(os.environ, GIT_NO_LAZY_FETCH='1'))
    workflow = '.github/workflows/cp7-current-s03-browser4-lawful.yml'
    for name in NAMES[-2:]:
        value = json.loads((HERE / 'retained-30ee' / name).read_bytes())
        value['producer_files'][workflow] = pin((ROOT / workflow).read_bytes())
        (HERE / name).write_text(json.dumps(value, indent=2) + '\n')
    plan = json.loads((HERE / 'retained-30ee/ADAPTATIONS.json').read_bytes())
    for row in plan['files']:
        old, current = (ROOT / row['parent']).read_bytes(), (ROOT / row['derived']).read_bytes()
        if pin(old) != dict(bytes=row['parent_bytes'], sha256=row['parent_sha256']):
            raise ValueError('S03_HISTORY_FROZEN_FIRST_BROWSER_SOURCE_CHANGED')
        row.update(derived_sha256=sha256(current).hexdigest(), changes=changes(old, current))
    plan['counted_changes'] = sum(len(r['changes']) for r in plan['files'])
    (HERE / 'ADAPTATIONS.json').write_text(json.dumps(plan, indent=2) + '\n')
    rows = []
    for name in NAMES:
        path = '.github/workflows/cp7-current-s03-browser4-lawful.yml' if name == 'workflow.yml' else str((HERE / name).relative_to(ROOT))
        old, current = (HERE / 'retained-30ee' / name).read_bytes(), (ROOT / path).read_bytes()
        if old != git('show', PARENT + ':' + path):
            raise ValueError('S03_HISTORY_EXACT_30EE_PREIMAGE_REQUIRED:' + name)
        rows.append(dict(name=name, path=path, before=pin(old), after=pin(current), changes=changes(old, current)))
    runtime = json.loads((HERE / 'RUNTIME_SOURCE.json').read_bytes())
    names = [*runtime['runtime_files'], runtime['package_entry']['path'],
             str((HERE / 'helper-source/lawful_fixture.py').relative_to(ROOT)),
             str((HERE / 'ORDINARY_SNAPSHOT_DELTA.json').relative_to(ROOT)),
             str((HERE / 'CURRENT_RIGHTS_DELTA.json').relative_to(ROOT)),
             'scripts/current-attendance-period-choice-qualification/cases.py']
    unchanged = {n: pin((ROOT / n).read_bytes()) for n in names}
    for name in unchanged:
        if (ROOT / name).read_bytes() != git('show', PARENT + ':' + name):
            raise ValueError('S03_HISTORY_NATIVE_OR_FROZEN_ORACLE_CHANGED:' + name)
    value = dict(contract='cp7.s03.cancelled-history-observation.v1', parent_commit=PARENT,
        parent_tree=git('rev-parse', PARENT + '^{tree}').decode().strip(), files=rows,
        unchanged=unchanged, first_failure='FIRST_30EE_CANCELLED_HISTORY_FAILURE.json',
        historical_authority='FIRST_SUCCESSFUL_NATIVE_VALIDATED_ACTIVE_OBSERVATION',
        fresh_complete_browser4_required=True, actual_browser_credit=0,
        full_outer_restore_required=True, production_go=False)
    (HERE / 'CANCELLED_HISTORY_DELTA.json').write_text(json.dumps(value, indent=2) + '\n')
    spec = importlib.util.spec_from_file_location('s03_history_writer_check', HERE / 'history_delta.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    print(json.dumps(module.verify(), sort_keys=True))


if __name__ == '__main__':
    main()
