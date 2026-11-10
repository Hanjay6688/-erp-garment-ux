"""Read-only canonical cumulative parent intake; no single-run substitution."""
from io import BytesIO
from pathlib import Path
import importlib.util
import json
import os
import subprocess
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
REPOSITORY = 'Hanjay6688/-erp-garment-ux'
READER_HEAD = 'cb87d3da9a4faf40de35aeb88c0ef9f07b2c5c3c'


def load():
    spec = importlib.util.spec_from_file_location('sku_cumulative_fetch_decision', HERE / 'cumulative_runtime.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inventory(adopter, originals_raw):
    archives = adopter.originals(originals_raw)
    result = {}
    with ZipFile(BytesIO(archives['MANDOR17_COMBINED_EVIDENCE_20261110.zip'])) as z:
        manifest = json.loads(z.read('MANDOR17_COMBINED_TECHNICAL_EVIDENCE.json'))
        for row in manifest['retained_group_originals']:
            raw = z.read('retained-group-originals/' + str(row['artifact_id']) + '.zip')
            result[row['artifact_id']] = dict(raw=raw, run=42660429648,
                head=manifest['old_run']['head'], pin=adopter.parent.pin(raw))
        raw = z.read('MANDOR_BROWSER_PAIR_READ_ONLY_RECEIPT.zip')
        result[13741144096] = dict(raw=raw, run=42770344036, head=READER_HEAD,
                                  pin=adopter.parent.pin(raw))
    return result


def validate_metadata(adopter, decision, records, artifacts):
    require = adopter.require
    runs = [decision['original_run'], decision['paired_browser_run'],
            dict(run=42770344036, job=129676405024, attempt=1, head=READER_HEAD, conclusion='success')]
    for row in runs:
        run, job = records['runs'][str(row['run'])], records['jobs'][str(row['job'])]
        require(run['id'] == row['run'] and run['status'] == 'completed'
                and run['conclusion'] == row['conclusion'] and run['head_sha'] == row['head']
                and run['run_attempt'] == row['attempt']
                and job['id'] == row['job'] and job['run_id'] == row['run']
                and job['status'] == 'completed' and job['conclusion'] == row['conclusion']
                and job['run_attempt'] == row['attempt'] and job['head_sha'] == row['head'],
                'SKU_CUMULATIVE_EXACT_ORIGINAL_TERMINAL_IDENTITY_REQUIRED')
    pair = decision['paired_browser_run']
    expected = {**artifacts, pair['artifact_id']: dict(pin=pair['archive'], run=pair['run'], head=pair['head'])}
    for identity, row in expected.items():
        actual = records['artifacts'][str(identity)]
        require(actual['id'] == identity and actual['expired'] is False
                and actual['size_in_bytes'] == row['pin']['bytes']
                and actual['digest'] == 'sha256:' + row['pin']['sha256']
                and actual['workflow_run']['id'] == row['run']
                and actual['workflow_run']['head_sha'] == row['head'],
                'SKU_CUMULATIVE_CANONICAL_ARTIFACT_METADATA_CHANGED')


def main(runtime):
    parent_raw, money_raw, plan_raw, _ = runtime.actual_inputs()
    adopter = load()
    decision = adopter.review_files(parent_raw, money_raw, plan_raw)
    artifacts = inventory(adopter, adopter.regular(HERE / adopter.ORIGINALS))
    def get(path):
        runtime.actual_inputs()
        return subprocess.check_output(['gh', 'api', 'repos/' + REPOSITORY + '/' + path])
    records = {key: {} for key in ('runs', 'jobs', 'artifacts')}
    for run_id, job_id in ((42660429648, 129310209330), (42752853455, 129620303386),
                           (42770344036, 129676405024)):
        records['runs'][str(run_id)] = json.loads(get('actions/runs/' + str(run_id)))
        records['jobs'][str(job_id)] = json.loads(get('actions/jobs/' + str(job_id)))
    for identity in (*artifacts, 13741014130):
        records['artifacts'][str(identity)] = json.loads(get('actions/artifacts/' + str(identity)))
    validate_metadata(adopter, decision, records, artifacts)
    target = Path(os.environ['RUNNER_TEMP']) / 'sku-cumulative-mandor-parent'
    target.mkdir(parents=True, exist_ok=True)
    adopter.require(not any(p.is_symlink() for p in (target, *target.parents)),
                    'SKU_CUMULATIVE_ARCHIVE_TARGET_MUST_BE_REGULAR')
    for identity, row in artifacts.items():
        path = target / (str(identity) + '.zip')
        if path.exists() or path.is_symlink():
            raw = adopter.regular(path)
        else:
            raw = get('actions/artifacts/' + str(identity) + '/zip')
        adopter.require(raw == row['raw'] and adopter.parent.pin(raw) == row['pin'],
                        'SKU_CUMULATIVE_CANONICAL_ORIGINAL_BYTES_CHANGED')
        with ZipFile(BytesIO(raw)) as archive:
            adopter.require(archive.testzip() is None and len(set(archive.namelist())) == len(archive.namelist()),
                            'SKU_CUMULATIVE_ORIGINAL_CRC_OR_MEMBERS_CHANGED')
        if not path.exists():
            with path.open('xb') as stream:
                stream.write(raw)
    # The large paired Original is verified by its exact read-only GitHub
    # receipt, all 29 CRCs and raw-member hashes, not by a reconstructed ZIP.
    value = dict(status='EXACT_CUMULATIVE_MANDOR_ORIGINALS_ADMITTED_NOT_SINGLE_RUN',
                 decision=adopter.parent.pin(adopter.parent.canonical(decision)),
                 original_run=decision['original_run'], paired_browser_run=decision['paired_browser_run'],
                 archive_verification=decision['archive_verification'],
                 downloaded_originals={str(k): v['pin'] for k, v in artifacts.items()},
                 live_metadata=records, source_root_unchanged=True, actual_SKU_cases=0,
                 independent_acceptance=False, production_go=False)
    out = runtime.ROOT / 'cp6-proof/t3/SKU_CURRENT_MANDOR17_ORIGINAL_ADMISSION.json'
    runtime.report_io.complete_originals().save_sorted(out, value, 'SKU_CUMULATIVE_FIRST_ADMISSION_CONFLICT')
    return value
