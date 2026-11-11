"""Create a reviewed SKU source binding from actual terminal run/job metadata."""
from pathlib import Path
import argparse
import json

from reviewed_sku_source import CANDIDATE, CANDIDATE_TREE, PARENT, pin, require, source_candidate, strict
from verify_sku_read_only import BRANCH, JOB_NAME, OUTCOMES, WORKFLOW, fields


def validate_metadata(run, job, commit):
    require(all(type(row.get('id')) is int and row['id'] > 0 for row in (run, job)),
            'SKU_ACTUAL_TERMINAL_IDS_REQUIRED')
    fields(run, dict(head_sha=CANDIDATE, head_branch=BRANCH, path=WORKFLOW,
                     event='push', run_attempt=1, status='completed'), 'SKU_CURRENT_TERMINAL_RUN_REQUIRED')
    require(run.get('conclusion') in OUTCOMES, 'SKU_ACTUAL_TERMINAL_CONCLUSION_REQUIRED')
    fields(job, dict(run_id=run['id'], head_sha=CANDIDATE, run_attempt=1, status='completed',
                     conclusion=run['conclusion'], name=JOB_NAME), 'SKU_SAME_CURRENT_TERMINAL_JOB_REQUIRED')
    fields(commit, dict(sha=CANDIDATE), 'SKU_ACTUAL_GITHUB_COMMIT_REQUIRED')
    require(commit.get('tree', {}).get('sha') == CANDIDATE_TREE,
            'SKU_ACTUAL_GITHUB_CANDIDATE_TREE_REQUIRED')


def bind(repo, run_raw, job_raw, commit_raw):
    run, job, commit = map(strict, (run_raw, job_raw, commit_raw))
    validate_metadata(run, job, commit)
    proof = source_candidate(repo, CANDIDATE, (repo/PARENT).read_bytes())
    require([row['sha'] for row in commit.get('parents', [])] == proof['parents'],
            'SKU_ACTUAL_GITHUB_SINGLE_REVIEWED_PARENT_REQUIRED')
    reviewed = {key: proof[key] for key in ('head', 'tree', 'parents', 'files')}
    reviewed.update(run_id=run['id'], job_id=job['id'])
    receipt = dict(status='TERMINAL_SKU_SOURCE_BOUND_NOT_ACCEPTED', source=proof,
                   run_metadata=pin(run_raw), job_metadata=pin(job_raw), commit_metadata=pin(commit_raw),
                   actual_SKU_case_credit=0, requires_canonical_bytes_and_CRC=True, production_go=False)
    return reviewed, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'run', 'job', 'commit', 'output', 'source-receipt'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    reviewed, receipt = bind(args.repo.resolve(), *(p.read_bytes() for p in (args.run,args.job,args.commit)))
    raw = (json.dumps(reviewed,indent=2,sort_keys=True)+'\n').encode()
    with args.output.open('xb') as stream:stream.write(raw)
    with args.source_receipt.open('x') as stream:stream.write(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(status=receipt['status'], reviewed_manifest=pin(raw), actual_SKU_case_credit=0)))


if __name__ == '__main__':main()
