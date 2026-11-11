"""Produce a review draft only; does not write .github or dispatch anything."""
from copy import deepcopy
import argparse
import json
from pathlib import Path
import yaml

ORIGINAL_BLOB = '066c325ea655347bc2bfe43efc274c7f68bf7c94'
REVIEW_PATH = 'docs/cp7/review/shutdown-20261111/checkpoint.py'
BOUNDARY_NAME = 'Start disposable database'


def derive(raw):
    from hashlib import sha1
    if sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != ORIGINAL_BLOB:
        raise ValueError('EXACT_6AEB_WORKFLOW_REQUIRED')
    original = yaml.safe_load(raw)
    result = deepcopy(original)
    steps = result['jobs']['p21']['steps']
    positions = [i for i, step in enumerate(steps) if step.get('name') == BOUNDARY_NAME]
    if len(positions) != 1:
        raise ValueError('ONE_DATABASE_START_REQUIRED')
    position = positions[0]
    additions = [
        dict(name='Write diagnostic source checkpoint before Native25',
             run='set -euo pipefail\npython -B auditor/' + REVIEW_PATH +
                 ' --source auditor --output "$RUNNER_TEMP/cp7-source-checkpoint/CP7_DIAGNOSTIC_CHECKPOINT.json"\n'),
        dict(name='Persist diagnostic checkpoint before long runtime',
             uses='actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02',
             with_={'name': 'cp7-sku-admission-checkpoint-${{ github.run_id }}-${{ github.run_attempt }}',
                    'path': '${{ runner.temp }}/cp7-source-checkpoint/CP7_DIAGNOSTIC_CHECKPOINT.json',
                    'retention-days': 30, 'if-no-files-found': 'error'}),
    ]
    additions[1]['with'] = additions[1].pop('with_')
    steps[position:position] = additions
    # Remove the additions and require exact structured identity of every old step/setting.
    unchanged = deepcopy(result)
    del unchanged['jobs']['p21']['steps'][position:position+2]
    if unchanged != original:
        raise ValueError('EXISTING_QUALIFICATION_OR_RECOVERY_CHANGED')
    return yaml.safe_dump(result, sort_keys=False), dict(
        status='REVIEW_ONLY_NOT_ACTIVE', original_workflow_blob=ORIGINAL_BLOB,
        old_steps=len(original['jobs']['p21']['steps']), new_steps=len(steps),
        all_existing_steps_unchanged=True, actual_case_credit=0,
        manifest_rebinding_required=True, activation_permitted=False,
        note='Current workflow.py --check must refuse this draft until its derivation and source manifest are explicitly rebound.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('original', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if '.github' in args.output.parts or args.output.suffix not in ('.txt', '.review'):
        raise ValueError('REVIEW_TEXT_OUTPUT_ONLY')
    text, receipt = derive(args.original.read_bytes())
    with args.output.open('x') as target:
        target.write(text)
    print(json.dumps(receipt, sort_keys=True))
