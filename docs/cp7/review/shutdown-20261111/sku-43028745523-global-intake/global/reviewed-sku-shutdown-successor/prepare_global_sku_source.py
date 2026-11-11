"""Prepare Global's exact repaired SKU source intake only after actual SKU27 proof.

No workflow is dispatched, no Global gate is set, and no database is accessed.
The source-only candidate review cannot supply a passing terminal receipt.
"""
import argparse
from hashlib import sha1
import json
from pathlib import Path

from derive_global_sku_fence import FULL_SCOPE_COUNT, PREPARED_COUNT, derive
from reviewed_sku_source import (CANDIDATE, CANDIDATE_TREE, DELTA, PREPARED, PREPARED_TREE,
                                 add_cli, from_cli, git, verify_cumulative_mandor, verify_source)
from verify_terminal_sku import CATALOGUE, catalogue, fields, pin, require, strict

GLOBAL_HEAD = 'c9248b8770ec8cfe0f7e2f2fd8da26c141ea67c5'
GLOBAL_TREE = '9b440dd1785344fdafa5d2d702a6dd8f1ee08622'
GLOBAL_SOURCE_PIN = dict(bytes=89796, sha256='794db88d865e844ec81043cf753aa116c2a1da7d86f03403c88e8db0ae623cf8')
SKU_BASE = '5f099fa6852c9088ab46daa0f1079a0f6a1f3185'
SKU_BASE_TREE = '3fd1bdb763a6d22a5aa455f5aea3a853b9782e4d'
AREA = 'scripts/current-global-sku-automatic-preparation/'
ROOT = AREA + 'SKU25_PARENT_ROOT_ACTUAL_INTAKE.json'
SOURCE = AREA + 'SOURCE.json'
CHECK = AREA + 'check_source.py'
WORKFLOW = '.github/workflows/cp7-global-current-source-unified.yml'


def read_regular(root, name):
    path = root / name
    require(path.is_file() and not path.is_symlink(), 'GLOBAL_EXACT_REGULAR_LOCAL_SOURCE_REQUIRED:' + name)
    return path.read_bytes()


def entries(repo, tree):
    result = {}
    for row in git(repo, 'ls-tree', '-rz', tree).split(b'\0'):
        if row:
            meta, name = row.split(b'\t', 1)
            mode, kind, blob = meta.decode().split()
            require(kind == 'blob' and mode in ('100644', '100755'), 'GLOBAL_EXACT_REGULAR_GIT_TREE_REQUIRED')
            name = name.decode()
            require(name not in result, 'GLOBAL_DUPLICATE_GIT_SOURCE_PATH')
            result[name] = dict(mode=mode, blob=blob)
    return result


def closed_source(checkout):
    require(git(checkout, 'rev-parse', 'HEAD', 'HEAD^{tree}').decode().splitlines() == [GLOBAL_HEAD, GLOBAL_TREE]
            and not git(checkout, 'status', '--porcelain')
            and all(not (checkout / name).exists() and not (checkout / name).is_symlink()
                    for name in (ROOT, WORKFLOW)), 'GLOBAL_REQUIRES_EXACT_CLEAN_CLOSED_SOURCE')
    raw = read_regular(checkout, SOURCE)
    require(pin(raw) == GLOBAL_SOURCE_PIN, 'GLOBAL_EXACT_CURRENT_CLOSED_MANIFEST_REQUIRED')
    manifest = strict(raw)
    require(manifest['runtime_entry'] is None and manifest['active_workflow_added'] is False
            and manifest['complete_actual_input_review'] is False and 'reviewed_current_SKU_source' not in manifest,
            'GLOBAL_ALL_EIGHT_GATES_STAY_CLOSED')
    fields(manifest['pending_current_SKU_preparation'],
           dict(base_head=SKU_BASE, base_tree=SKU_BASE_TREE, head=PREPARED, tree=PREPARED_TREE,
                actual_Root=None, actual_run=None, actual_job=None), 'GLOBAL_EXACT_CURRENT_CLOSED_SKU_PARENT')
    return manifest


def prepare(receipt_raw, expected_receipt_sha256, root_raw, catalogue_raw, mandor_raw, reviewed, sku_repo, checkout):
    require(pin(receipt_raw)['sha256'] == expected_receipt_sha256, 'GLOBAL_REVIEWED_SKU_TERMINAL_RECEIPT_CHANGED')
    receipt, root = strict(receipt_raw), strict(root_raw)
    fields(receipt, dict(status='SKU_TERMINAL_ORIGINAL_BYTES_VERIFIED', head=CANDIDATE,
                         run_id=reviewed['run_id'], job_id=reviewed['job_id'], attempt=1,
                         conclusion='success', all_member_crc_verified=True, actual_case_credit=27,
                         actual_all_five=True, actual_outer_restore=True, actual_worker_reaped=True,
                         github_disposable_cleanup_success=True, root_pin=pin(root_raw)),
           'GLOBAL_REQUIRES_VERIFIED_NATIVE25_BROWSER2_AND_ALL5')
    fields(root, dict(status='ROOT_VERIFIED_CURRENT_SKU_NATIVE25_BROWSER2_ALL5', head=CANDIDATE,
                      tree=CANDIDATE_TREE, run_id=reviewed['run_id'], job_id=reviewed['job_id'],
                      artifact_id=receipt['artifact_id'], actual_Native_cases=25, actual_browser_cases=2,
                      actual_business_cases=27, package_all_five=True, actual_outer_restore=True,
                      prior_runs_aggregated=False, production_go=False, independent_acceptance=False,
                      complete_global_input_review=False, mandor_root=pin(mandor_raw),
                      mandor_evidence_mode='CUMULATIVE_15_PLUS_2'), 'GLOBAL_REQUIRES_EXACT_ACTUAL_SKU_ROOT')
    parent = verify_cumulative_mandor(sku_repo, root['head'], mandor_raw)
    require(root['mandor_cumulative_decision'] == parent['decision'], 'GLOBAL_EXACT_CUMULATIVE_MANDOR_DECISION_REQUIRED')
    observation = root['global_parent_catalogue']
    original_pin = pin(catalogue_raw)
    require(receipt['global_parent_catalogue'] == observation
            and observation['original'] == dict(name=CATALOGUE, **original_pin)
            and root['originals'][CATALOGUE] == original_pin
            and {key: receipt['members'][CATALOGUE][key] for key in original_pin} == original_pin,
            'GLOBAL_ACTUAL_FULL25_CANONICAL_CATALOGUE_REQUIRED')
    catalogue(catalogue_raw, dict(status='ACTUAL_FULL25_SKU_CATALOGUE_OBSERVED', head=root['head'],
              run_id=str(root['run_id']), attempt=1, original=observation['original'],
              readers=observation['exact_query_sources'], fingerprint=observation['fingerprint'],
              actual_ERP_case_credit=0, complete_input_review=False, production_go=False),
              root['head'], root['run_id'])
    direct = verify_source(sku_repo, root['head'], reviewed, mandor_raw)
    require(set(direct) == DELTA, 'GLOBAL_EXACT_REVIEWED_SKU_ADOPTION_AND_REPAIR_PATHS_REQUIRED')
    manifest = closed_source(checkout)
    require(git(sku_repo, 'rev-parse', SKU_BASE + '^{tree}').decode().strip() == SKU_BASE_TREE,
            'GLOBAL_EXACT_SKU_BASE_TREE_REQUIRED')
    before, after, global_tree = (entries(sku_repo, SKU_BASE_TREE), entries(sku_repo, CANDIDATE_TREE),
                                  entries(checkout, GLOBAL_TREE))
    old = manifest['pending_current_SKU_preparation']['files']
    scope = {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}
    require(len(old) == PREPARED_COUNT and len(scope) == FULL_SCOPE_COUNT and scope == set(old) | DELTA,
            'GLOBAL_REQUIRES_COMPLETE_OWNING_SKU_SOURCE_PATHS')
    copied, record = {}, {}
    for name in sorted(scope):
        require(name in after and global_tree.get(name) == (old[name]['after'] if name in old else before.get(name)),
                'GLOBAL_INHERITED_SOURCE_COLLISION:' + name)
        if name in DELTA:
            raw = git(sku_repo, 'show', CANDIDATE + ':' + name)
            copied[name] = raw
        else:
            raw = read_regular(checkout, name)
        oid = sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        require(oid == after[name]['blob'], 'GLOBAL_INHERITED_SKU_BYTES_CHANGED:' + name)
        record[name] = dict(before=before.get(name), after=after[name], pin=pin(raw))
        require(name in DELTA or record[name] == old[name], 'GLOBAL_UNCHANGED_CLOSED_SKU_PIN_REQUIRED:' + name)
    fence = read_regular(checkout, CHECK)
    require(manifest['files'][CHECK] == pin(fence), 'GLOBAL_CLOSED_SOURCE_FENCE_PIN_CHANGED')
    revised = derive(fence)
    manifest['files'].update({ROOT: pin(root_raw), CHECK: pin(revised)})
    manifest['reviewed_current_SKU_source'] = dict(base_head=SKU_BASE, base_tree=SKU_BASE_TREE,
        head=CANDIDATE, tree=CANDIDATE_TREE, actual_Root=pin(root_raw), actual_run=root['run_id'],
        actual_job=root['job_id'], actual_full25_catalogue=observation['original'],
        reviewed_owning_source=reviewed, files=record)
    return {**copied, ROOT: root_raw, CHECK: revised, SOURCE: (json.dumps(manifest, indent=2) + '\n').encode()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_cli(parser)
    for name in ('receipt', 'root', 'catalogue', 'mandor-root', 'sku-repo', 'global-checkout', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reviewed-receipt-sha256', required=True)
    a = parser.parse_args()
    overlay = prepare(a.receipt.read_bytes(), a.reviewed_receipt_sha256, a.root.read_bytes(),
                      a.catalogue.read_bytes(), a.mandor_root.read_bytes(), from_cli(a),
                      a.sku_repo.resolve(), a.global_checkout.resolve())
    a.output.mkdir()
    for name, raw in sorted(overlay.items()):
        dest = a.output / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as out:
            out.write(raw)
    print(json.dumps(dict(status='EXACT_GLOBAL_SKU_CUMULATIVE_SOURCE_REVIEW_ONLY', source_paths=len(overlay),
                          actual_complete_input_review=False, active_workflow_added=False,
                          actual_ERP_case_credit=0, files={name: pin(raw) for name, raw in sorted(overlay.items())})))


if __name__ == '__main__':
    main()
