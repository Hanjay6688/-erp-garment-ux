"""Exact reversible ACCESS successor, bound to the actual refused 4d policy.

Source verification grants no Native, Auth, browser, race or acceptance credit.
"""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENT = '4d968a42e793a77c2dbcbe06dd79c524f18fa0f5'
POLICY_SHA256 = '7154b9c0290767446bc3ee6aea7b22a9a8a81caeddc0226d5effefd729d7b8f8'
SIGNATURES = {
    'cp7_attendance_choice.access_v1(boolean)', 'erp.current_app_role()',
    'erp.has_permission(text)', 'erp.guard_protected_role()',
    'erp.guard_last_active_owner()', 'erp.save_app_user_v2(jsonb,uuid,bigint)',
    'public.erp_save_app_user_v3(jsonb,uuid,bigint)', 'erp._idempotency_actor_key()',
}


def policy(here=HERE):
    raw = (here / 'retained-4d968/POLICY_FUNCTIONS.json').read_bytes()
    if sha256(raw).hexdigest() != POLICY_SHA256:
        raise ValueError('S03_BROWSER4_ACTUAL_POLICY_SOURCE_CHANGED')
    value = json.loads(raw)
    if (value['contract'] != 'cp7.s03.actual-4d-access-policy.v1'
            or value['run_id'] != 41033738459 or value['artifact_id'] != 12969123916
            or set(value['functions']) != SIGNATURES):
        raise ValueError('S03_BROWSER4_EXACT_ACTUAL_POLICY_IDENTITY_REQUIRED')
    return {name: row[0] for name, row in value['functions'].items()}


def callbacks(before, after):
    # Whole setup and all three financial callbacks are byte exact. ACCESS's
    # delayed period, logout and fresh actor controls retain every old byte.
    begin = 'async function desktop('
    old_end, new_end = 'async function access(', 'async function currentRole('
    if before[:before.index(old_end)] != after[:after.index(new_end)]:
        raise ValueError('S03_BROWSER4_THREE_FINANCIAL_CALLBACKS_CHANGED')
    delay = ' // Preserve any unresolved old actor envelope;'
    progress = ' x.progress.access='
    fresh = ' // The delayed-response page is now the genuine login screen;'
    catch = ' }catch(e){if(delayedSession)'
    for start, end in ((delay, progress), (fresh, catch)):
        if before[before.index(start):before.index(end)] != after[after.index(start):after.index(end)]:
            raise ValueError('S03_BROWSER4_DELAYED_PERIOD_LOGOUT_FRESH_ACTOR_CHANGED')
    return dict(whole_financial_callbacks=3, whole_setup_unchanged=True,
        delayed_period_logout_fresh_actor_exact=True, financial_sha256=sha256(
            before[before.index(begin):before.index(old_end)].encode()).hexdigest())


def verify(root=ROOT, here=HERE):
    spec = importlib.util.spec_from_file_location('s03_history_before_rights', here / 'history_delta.py')
    history = importlib.util.module_from_spec(spec); spec.loader.exec_module(history)
    plan = json.loads((here / 'CURRENT_RIGHTS_DELTA.json').read_bytes())
    if (plan['contract'] != 'cp7.s03.browser4.current-rights-successor.v1'
            or plan['parent_commit'] != PARENT or plan['policy_sha256'] != POLICY_SHA256
            or [row['name'] for row in plan['files']] != ['fixture.py', 'cases.mjs']):
        raise ValueError('S03_BROWSER4_EXACT_CURRENT_RIGHTS_DELTA_REQUIRED')
    git = lambda *parts: subprocess.check_output(['/usr/bin/git', '-C', str(root), *parts],
        env=dict(os.environ, GIT_NO_LAZY_FETCH='1'))
    if git('rev-parse', PARENT + '^{tree}').decode().strip() != plan['parent_tree']:
        raise ValueError('S03_BROWSER4_CURRENT_RIGHTS_PUBLIC_PARENT_CHANGED')
    total = 0
    for item in plan['files']:
        name = item['name']; old = (here / 'retained-4d968' / name).read_bytes()
        current = history.previous(name, root=root, here=here)
        if name == 'fixture.py':
            spec = importlib.util.spec_from_file_location('s03_ordinary_snapshot_before_rights', HERE / 'ordinary_snapshot_delta.py')
            ordinary = importlib.util.module_from_spec(spec); spec.loader.exec_module(ordinary)
            current = ordinary.parent_fixture(root, here)
        if (old != git('show', PARENT + ':' + str((HERE / name).relative_to(ROOT)))
                or item['before'] != dict(bytes=len(old), sha256=sha256(old).hexdigest())
                or item['after'] != dict(bytes=len(current), sha256=sha256(current).hexdigest())):
            raise ValueError('S03_BROWSER4_CURRENT_RIGHTS_EXACT_SOURCE_REQUIRED:' + name)
        value = old.decode()
        for change in item['changes']:
            if not change['before'] or change['count'] != 1 or value.count(change['before']) != 1:
                raise ValueError('S03_BROWSER4_CURRENT_RIGHTS_FORWARD_ANCHOR_REQUIRED')
            value = value.replace(change['before'], change['after'], 1)
        if value.encode() != current:
            raise ValueError('S03_BROWSER4_CURRENT_RIGHTS_EXACT_DERIVATION_REQUIRED')
        for change in reversed(item['changes']):
            if not change['after'] or value.count(change['after']) != 1:
                raise ValueError('S03_BROWSER4_CURRENT_RIGHTS_REVERSE_ANCHOR_REQUIRED')
            value = value.replace(change['after'], change['before'], 1)
        if value.encode() != old:
            raise ValueError('S03_BROWSER4_CURRENT_RIGHTS_OLD_CALLBACK_RESTORE_REQUIRED')
        total += len(item['changes'])
    if total != plan['counted_changes']:
        raise ValueError('S03_BROWSER4_CURRENT_RIGHTS_COUNT_CHANGED')
    proof = callbacks((here / 'retained-4d968/cases.mjs').read_text(), history.previous('cases.mjs', root=root, here=here).decode())
    if proof != plan['unchanged_callbacks']:
        raise ValueError('S03_BROWSER4_CURRENT_RIGHTS_CALLBACK_PROOF_CHANGED')
    policy(here)
    return dict(counted_changes=total, all_4d_bytes_restored=True, **proof,
        actual_browser_credit=0, view_only_Owner_representable=False, product_policy_changed=False)


if __name__ == '__main__':
    print(json.dumps(verify()))
