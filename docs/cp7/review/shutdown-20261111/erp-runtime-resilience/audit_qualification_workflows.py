"""Inventory exact workflow blobs without running CI or contacting a database."""
import argparse
from hashlib import sha1
import json
from pathlib import Path
import re

import yaml


DATABASE_START = re.compile(r'(?m)^[ \t]*(?:[A-Z_]+=[^\s]+[ \t]+)*supabase[ \t]+(?:db[ \t]+)?start(?:[ \t]|$)')


def true(value):
    return str(value).lower() == 'true'


def run_steps(workflow, name, blob):
    for job_id, job in workflow.get('jobs', {}).items():
        steps = job.get('steps', [])
        starts = [number for number, step in enumerate(steps, 1) if DATABASE_START.search(step.get('run', ''))]
        if not starts:
            continue
        start = starts[0]
        before = steps[:start-1]
        after = steps[start:]
        uploads = [(number, step) for number, step in enumerate(steps, 1)
                   if step.get('uses', '').startswith('actions/upload-artifact@')]
        checkpoints = [number for number, step in uploads if number < start and 'checkpoint' in str(step.get('with', {}).get('name', '')).lower()]
        final_uploads = [number for number, _ in uploads if number > start]
        guarded = [number for number, step in enumerate(steps, 1) if number > start
                   and '--allow-database-stop' in step.get('run', '') and 'supabase stop' in step.get('run', '')]
        cancel = [scope.get('concurrency', {}) for scope in (workflow, job)]
        yield dict(workflow=name, blob=blob, job=job_id, database_start_steps=starts,
                   pre_database_checkpoint_uploads=checkpoints, later_upload_steps=final_uploads,
                   unconditional_later_upload_steps=[number for number, step in uploads if number > start
                       and str(step.get('if', '')).strip().removeprefix('${{').removesuffix('}}').strip() == 'always()'],
                   guarded_database_stop_steps=guarded, static_cancel_in_progress=any(
                       isinstance(scope, dict) and true(scope.get('cancel-in-progress')) for scope in cancel),
                   post_start_continue_on_error=any(true(step.get('continue-on-error')) for step in after),
                   pre_start_stop_receipt=any('runtime_receipt' in step.get('run', '') and 'prepare' in step.get('run', '')
                                              for step in before))


def inspect(rows, blobs):
    jobs = []
    for row in rows:
        if not row['path'].endswith(('.yml', '.yaml')):
            continue
        raw = (blobs / row['sha']).read_bytes()
        assert len(raw) == row['size'] and sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest() == row['sha'], row['path']
        workflow = yaml.load(raw, Loader=yaml.BaseLoader)
        jobs.extend(run_steps(workflow, row['path'], row['sha']))
    return dict(workflow_definitions=len(rows), literal_database_start_jobs=len(jobs),
                jobs_with_pre_database_checkpoint=sum(bool(j['pre_database_checkpoint_uploads']) for j in jobs),
                jobs_with_guarded_stop=sum(bool(j['guarded_database_stop_steps']) for j in jobs),
                jobs_with_static_cancel=sum(j['static_cancel_in_progress'] for j in jobs),
                jobs=jobs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sku-tree', type=Path, required=True)
    parser.add_argument('--main-tree', type=Path, required=True)
    parser.add_argument('--blobs', type=Path, required=True)
    args = parser.parse_args()
    sku = json.loads(args.sku_tree.read_bytes())
    assert not sku['truncated']
    print(json.dumps(dict(sku_tree=sku['sha'], sku=inspect(sku['tree'], args.blobs),
                          main=inspect(json.loads(args.main_tree.read_bytes()), args.blobs)), indent=2))


if __name__ == '__main__':
    main()
