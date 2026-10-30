"""Verify the exact ae837 successor and recover every previous byte.

Only two prepare reads acquire UTC scopes. No business writer, monetary oracle,
callback, helper source, or previous current-rights declaration is changed.
"""
from hashlib import sha256
from pathlib import Path
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENT = 'ae83782c5dc0701f3b5325375a743b2a08e4ce3d'
FILES = ('fixture.py', 'rights_delta.py', 'test_bound.py', 'test_current_rights.py', 'README.md')
READS = (
    "            ordinary_before_native = r['lawful'].finished_facts(cur, g, core=core)\n",
    "            ordinary_journal = f.one(cur, 'select to_jsonb(j)from erp.journal_entries j join erp.attendance_hpp_pools p on p.post_journal_entry_id=j.id where p.id=%s', (normal['pool_id'],))\n",
)
CHANGES = [dict(before=line, after='            with snapshot_utc(cur, f):\n    ' + line, count=1) for line in READS]
UNCHANGED = ('cases.mjs', 'evidence.mjs', 'helper-source/lawful_fixture.py', 'HELPER_SOURCE.json',
    'CURRENT_RIGHTS_DELTA.json', 'retained-4d968/fixture.py', 'retained-4d968/cases.mjs',
    'retained-4d968/ADAPTATIONS.json', 'FIRST_84A9_FAILURE.json', 'FIRST_4D968_FAILURE.json')


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def verify(root=ROOT, here=HERE):
    plan = json.loads((here / 'ORDINARY_SNAPSHOT_DELTA.json').read_bytes())
    if (plan['contract'] != 'cp7.s03.browser4.ordinary-snapshot-utc-successor.v1'
            or plan['parent_commit'] != PARENT or tuple(row['name'] for row in plan['files']) != FILES
            or tuple(plan['unchanged']) != UNCHANGED or plan['fixture_read_scopes'] != 2):
        raise ValueError('S03_ORDINARY_EXACT_SUCCESSOR_REQUIRED')
    git = lambda *args: subprocess.check_output(['/usr/bin/git', '-C', str(root), *args],
        env=dict(os.environ, GIT_NO_LAZY_FETCH='1'))
    prefix = str(HERE.relative_to(ROOT)) + '/'
    if git('rev-parse', PARENT + '^{tree}').decode().strip() != plan['parent_tree']:
        raise ValueError('S03_ORDINARY_EXACT_PUBLIC_PARENT_REQUIRED')
    total = 0
    for row in plan['files']:
        old = (here / 'retained-ae837' / row['name']).read_bytes(); current = (here / row['name']).read_bytes()
        if old != git('show', PARENT + ':' + prefix + row['name']) or pin(old) != row['before'] or pin(current) != row['after']:
            raise ValueError('S03_ORDINARY_EXACT_SOURCE_REQUIRED:' + row['name'])
        if row['name'] == 'fixture.py' and row['changes'] != CHANGES:
            raise ValueError('S03_ORDINARY_ONLY_TWO_READ_SCOPES_REQUIRED')
        value = old.decode()
        for change in row['changes']:
            if change['count'] != 1 or not change['before'] or value.count(change['before']) != 1:
                raise ValueError('S03_ORDINARY_FORWARD_ANCHOR_REQUIRED')
            value = value.replace(change['before'], change['after'], 1)
        if value.encode() != current:
            raise ValueError('S03_ORDINARY_EXACT_DERIVATION_REQUIRED')
        for change in reversed(row['changes']):
            if not change['after'] or value.count(change['after']) != 1:
                raise ValueError('S03_ORDINARY_REVERSE_ANCHOR_REQUIRED')
            value = value.replace(change['after'], change['before'], 1)
        if value.encode() != old:
            raise ValueError('S03_ORDINARY_PREVIOUS_BYTES_REQUIRED')
        total += len(row['changes'])
    if total != plan['counted_changes']:
        raise ValueError('S03_ORDINARY_DELTA_COUNT_CHANGED')
    for name, expected in plan['unchanged'].items():
        raw = (here / name).read_bytes()
        if pin(raw) != expected or raw != git('show', PARENT + ':' + prefix + name):
            raise ValueError('S03_ORDINARY_FROZEN_CALLBACK_HELPER_OR_MANIFEST_CHANGED:' + name)
    return dict(fixture_read_scopes=2, counted_changes=total, previous_bytes_restored=True,
        all_four_callbacks_exact=True, financial_oracles_and_helper_exact=True,
        current_rights_declaration_exact=True, business_writer_timezone_unchanged=True,
        actual_browser_credit=0, production_go=False)


def parent_fixture(root=ROOT, here=HERE):
    verify(root, here)
    return (here / 'retained-ae837/fixture.py').read_bytes()


if __name__ == '__main__':
    print(json.dumps(verify()))
