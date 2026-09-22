"""Bound a new regression harness to the complete, unchanged qualified AR tree."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

import cp6_ar_build as ar
import cp6_successor_specs as specs

BASE = '0d53bd46d7da7f7c937263f2a2ab8a45e059b9fc'
BASE_TREE = 'bd7b915cc9afa9c1a7696fd32f649430c59d9ea2'
QUALIFIED_AR = '8f1a6ecceda40cb2b7b551d307bd6425b4899a24'
QUALIFIED_TREE = 'a2d8f107244dae36a6a8d1fc10b4f987a4ca95d1'
ALLOWED = {
    '.github/workflows/cp6-successor-qualification.yml',
    'scripts/cp6_successor_scope.py',
    'scripts/cp6_successor_specs.py',
    'scripts/cp6_successor_regression.py',
    'docs/evidence/cp6-successor-oracles.json',
    'docs/cp6-successor-qualification.md',
}
OUT = Path('cp6-proof/successor')


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def verify():
    assert git('rev-parse', BASE+'^{tree}') == BASE_TREE
    assert git('rev-parse', QUALIFIED_AR+'^{tree}') == QUALIFIED_TREE
    assert git('diff', '--name-only', QUALIFIED_AR, BASE) == 'docs/cp6-ar-opening-overlap.md'
    assert git('merge-base', BASE, 'HEAD') == BASE
    assert not git('rev-list', '--merges', BASE+'..HEAD')
    assert not git('diff', '--name-only', 'HEAD'), 'DIRTY_TRACKED_SOURCE'
    changed = set(git('diff', '--name-only', BASE, 'HEAD').splitlines())
    assert changed == ALLOWED, sorted(changed ^ ALLOWED)
    assert not git('diff', '--name-only', '--diff-filter=MDRTCUXB', BASE, 'HEAD'), 'INHERITED_SOURCE_CHANGED'
    head, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
    assert os.environ.get('GITHUB_SHA', head) == head, 'EXACT_NATIVE_CHECKOUT_REQUIRED'
    p = specs.pins()
    _, _, before, after, _ = ar.model()
    assert len(after['functions']) == 648 and len(after['objects']) == 7148
    report = dict(status='SOURCE_ADMITTED', head=head, tree=tree, frozen_ar_head=BASE,
                  qualified_ar_head=QUALIFIED_AR, qualified_ar_tree=QUALIFIED_TREE,
                  changed=sorted(changed),
                  source_sha256={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in sorted(changed)},
                  oracle_sha256=p['oracle_sha256'],
                  all_inherited_sources_unchanged=True, product_source_unchanged=True,
                  historical_guards_unchanged=True, production_go=False,
                  hosted_migration_installed=False, independent_acceptance=False)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'SOURCE.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    result = verify()
    print(json.dumps(dict(status=result['status'], head=result['head'], tree=result['tree'], global_status='CP6_HOLD')))
