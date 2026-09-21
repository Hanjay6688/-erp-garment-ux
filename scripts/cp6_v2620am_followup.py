#!/usr/bin/env python3
"""Bounded AM transfer/invoice follow-up with explicit unchanged-product reuse."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import zipfile

BASE = 'bf05659d4f8e99d0332215772d658417e4233cc8'
TREE = 'e5ac4db612e5c9097daf0c6a446abeafffc29cd2'
ARTIFACT = 10668124130
DIGEST = '299684058ecb0e3f03c8ab18a374f4d944848268d4462348e89c89e8036fd4cc'
ROOT = Path('cp6-proof/writer-am')
SOURCE = Path(__file__).resolve().parents[1]
ALLOWED = {
    '.github/workflows/cp6-final-boundary-audit.yml',
    'scripts/cp6_v2620am_transfer_crossflow.py',
    'scripts/cp6_v2620am_followup.py',
    'scripts/cp6_disposable_ui_scope.py',
    'docs/evidence/cp6-disposable-ui-source-pins.json',
    'docs/cp6-frontend-recovery.md',
}


def save(name, data):
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')


def source_boundary():
    git = lambda *a: subprocess.check_output(['git', '-C', str(SOURCE), *a], text=True).strip()
    assert git('rev-parse', BASE + '^{tree}') == TREE
    assert git('merge-base', BASE, 'HEAD') == BASE
    assert not git('diff', '--name-only', 'HEAD')
    changed = set(git('diff', '--name-only', BASE, 'HEAD').splitlines())
    assert changed <= ALLOWED, changed - ALLOWED
    head, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
    assert head == os.environ['CP6_RUNTIME_HEAD']
    assert tree == os.environ['CP6_RUNTIME_TREE']
    return dict(head=head, tree=tree, changed=sorted(changed),
                product_sql_oracles_controller_byte_identical=True)


def reuse(path):
    boundary = source_boundary()
    raw = Path(path).read_bytes()
    assert len(raw) == 64497485 and hashlib.sha256(raw).hexdigest() == DIGEST
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None and len(z.namelist()) == 355
        assert all(not n.startswith('/') and '..' not in Path(n).parts for n in z.namelist())
        read = lambda name: json.loads(z.read('candidate/cp6-proof/' + name))
        final = read('writer-am/FINAL_GATE.json')
        assert final['status'] == 'WRITER_PASS_AFFECTED_AM_FAMILY'
        assert (final['head'], final['tree']) == (BASE, TREE)
        assert final['production_go'] is False and final['independent_acceptance'] is False
        assert final['global_status'] == 'CP6_HOLD' and final['exact_restore'] and final['cleanup']
        gate = read('writer-am/WRITER_GATE.json')
        assert gate['status'] == 'WRITER_GROUPS_COMPLETE_RESTORE_PENDING'
        assert len(gate['results']) == 19
        reused = {}
        for name, result in gate['results'].items():
            assert result['expected'] == result['actual'] == read(name)['status'], name
            reused[name] = dict(classification='REUSED_EVIDENCE', original_status=result['actual'],
                                original_head=BASE, original_tree=TREE)
        business = read('writer-am/BUSINESS.json')
        assert business['counts'] == dict(PASS=179, CONTROL_PASS=39, BUG_PROVEN=0,
            GAP_PROVEN=0, DATE_POLICY_REVIEW_REQUIRED=12, INCOMPLETE=0, FAIL=0)
        assert len(business['cases']) == len(set(business['planned_case_ids'])) == 230
        assert set(business['cases']) == set(business['planned_case_ids'])
        assert business['reused_evidence'] == {}
        assert read('writer-am/VALUES.json')['counts'] == dict(PASS=65, BUG_PROVEN=0, GAP_PROVEN=0, INCOMPLETE=0)
        assert read('AM_MAINTENANCE_ROLLBACK/manifest.json')['completed_case_count'] == 20
        assert len(read('writer-am/transfer-concurrency/manifest.json')['cases']) == 12
        assert read('final-audit/HTTP.json')['status'] == 'PASS'
        reused['final-audit/HTTP.json'] = dict(classification='REUSED_EVIDENCE', original_status='PASS', original_head=BASE)
        reused['writer-am/FINAL_GATE.json'] = dict(classification='REUSED_EVIDENCE', original_status=final['status'], original_head=BASE)
    report = dict(status='REUSE_ADMITTED_UNCHANGED_PRODUCT', source=boundary,
                  artifact_id=ARTIFACT, artifact_sha256=DIGEST, full_run=35663140263,
                  full_head=BASE, full_tree=TREE, groups=reused,
                  full_business_reexecuted=False, maintenance20_reexecuted=False,
                  http_ui_reexecuted=False, historical460_reexecuted=False,
                  fresh_required=['SQL_TRIAL_34', 'TRANSFER_CROSSFLOW_8', 'EXACT_RESTORE_CHAIN', 'PHYSICAL_CLEANUP'],
                  global_status='CP6_HOLD', independent_acceptance=False, production_go=False)
    save('FOLLOWUP_REUSE', report)
    return report


def seal():
    boundary = source_boundary()
    read = lambda name: json.loads((Path('cp6-proof') / name).read_text())
    incoming = read('writer-am/FOLLOWUP_REUSE.json')
    assert incoming['status'] == 'REUSE_ADMITTED_UNCHANGED_PRODUCT' and incoming['source'] == boundary
    bridge = read('writer-am/TRANSFER_CROSSFLOW.json')
    assert bridge['status'] == 'WRITER_PASS' and bridge['counts'] == dict(CONTROL_PASS=8, BUG_PROVEN=0, INCOMPLETE=0)
    assert (bridge['head'], bridge['tree']) == (boundary['head'], boundary['tree'])
    assert len(bridge['cases']) == 8 and all(c['boundary_restored'] for c in bridge['cases'].values())
    assert all(bridge[k] for k in ('boundary_restored', 'catalog_unchanged', 'schema_usage_restored'))
    trial = read('writer-am/SQL_TRIAL.json')
    assert trial['status'] == 'SQL_TRIAL_COMPLETE_FULL_ACCEPTANCE_PENDING'
    assert trial['counts'] == dict(CONTROL_PASS=31, BUG_PROVEN=3, INCOMPLETE=0)
    assert len(trial['cases']) == 34 and len(trial['planned_successor_cases']) == 26
    assert all(trial[k] for k in ('exact_sql_restore', 'full_initial_boundary_restored', 'schema_usage_restored', 'initial_al_runtime_restored'))
    assert read('writer-am/ADVISORS_AFTER.json')['status'] == 'PASS_REVIEWED_SECURITY_DELTA'
    restore = read('writer-am/EXACT_AL_RESTORE.json')
    assert restore['status'] == 'PASS' and restore['full_boundary_exact']
    assert (restore['functions'], restore['tables']) == (533, 227)
    refusals = read('writer-am/ROLLBACK_REFUSALS.json')['cases']
    assert len(refusals) == 8 and all(c['status'] == 'PASS' and c['boundary_restored'] for c in refusals.values())
    ah = read('independent-ai/EXACT_RESTORE.json')
    assert ah['status'] == 'PASS_REVIEWED_SCOPE' and ah['full_boundary_exact']
    assert (ah['functions'], ah['tables'], ah['auth_users'], ah['app_users']) == (533, 223, 0, 0)
    cleanup = Path('cp6-proof/independent-ai/PHYSICAL_CLEANUP.txt').read_text()
    assert 'status=PASS' in cleanup and 'remaining_database_container=0' in cleanup
    result = dict(status='WRITER_PASS_AM_TRANSFER_INVOICE_FOLLOWUP', source=boundary,
                  fresh_transfer_invoice_cases=8, fresh_trial_cases=34, exact_restore=True, cleanup=True,
                  reused_full_run=35663140263, reused_full_artifact=ARTIFACT,
                  date_policy_hold=12, global_status='CP6_HOLD', independent_acceptance=False, production_go=False)
    save('FOLLOWUP_FINAL_GATE', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--reuse')
    group.add_argument('--seal', action='store_true')
    args = parser.parse_args()
    result = reuse(args.reuse) if args.reuse else seal()
    print(json.dumps({k: v for k, v in result.items() if k != 'groups'}))
