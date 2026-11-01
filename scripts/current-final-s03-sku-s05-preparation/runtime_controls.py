"""Exact reuse of the proved process owner; no new ERP qualification."""
from pathlib import Path
from hashlib import sha256
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def verify():
    declaration = json.loads((HERE/'SUPERVISION_DERIVATIONS.json').read_bytes())
    originals = {}
    for name, row in declaration['files'].items():
        original = subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), 'show',
            row['source_commit']+':'+row['source_path']])
        if len(original) != row['original_bytes'] or sha256(original).hexdigest() != row['original_sha256']:
            raise ValueError('PERMANENT_SUPERVISION_FROZEN_SOURCE_CHANGED:'+name)
        value = original.decode()
        for change in row['changes']:
            if value.count(change['before']) != change['count']:
                raise ValueError('PERMANENT_SUPERVISION_EXACT_CHANGE_REQUIRED:'+name)
            value = value.replace(change['before'], change['after'], change['count'])
        current = (ROOT/name).read_bytes()
        if value.encode() != current or sha256(current).hexdigest() != row['derived_sha256']:
            raise ValueError('PERMANENT_SUPERVISION_UNDECLARED_CHANGE:'+name)
        for change in reversed(row['changes']):
            if value.count(change['after']) != change['count']:
                raise ValueError('PERMANENT_SUPERVISION_UNIQUE_REVERSE_REQUIRED:'+name)
            value = value.replace(change['after'], change['before'], change['count'])
        if value.encode() != original:
            raise ValueError('PERMANENT_SUPERVISION_ORIGINAL_NOT_RECOVERED:'+name)
        originals[name] = original.decode()
    return dict(status='PERMANENT_SUPERVISION_EXACT_REUSE_SOURCE_PASS',
        prior_workflow=originals['.github/workflows/cp7-final-s03-sku-s05.yml'],
        unchanged_process_engine=True, own_probe_and_receipt_routes=True,
        job_seconds=21600, work_seconds=19800, restoration_reserve_seconds=1200,
        artifact_reserve_seconds=600, actual_case_credit=0)
