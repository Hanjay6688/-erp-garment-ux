"""Bind twelve verified cases to two exact recovered terminal receipts."""

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

from . import p20_evidence


ORIGINAL = {
    'run': 43989835658,
    'attempt': 1,
    'artifact': 14291469964,
    'runner': 'a7bad3397f2fd9a13677a85bd7bdc01059bc43c5',
    'bytes': 5389,
    'sha256': '98f02e83983c0ea5e6b265dcc8a62844270ace980b033f9c52b947d13d9cf1c7',
    'member_sha256': 'effc882aadb89e52bad43961adf39f9c8577993d2c692e707380345c33100fb5',
}
FOLLOWUP = {
    'run': 44006936125,
    'attempt': 1,
    'artifact': 14297807273,
    'runner': '64857b57a47c15250b625958c1c85fd69ca28f41',
    'bytes': 3759,
    'sha256': '1a894bb4337fe3e73f58e6cf66c988a4f5e9b31dbc48ea6c70d20926ca99568c',
    'member_sha256': '42cd36d3ac72072afaaaceaf448daf75570593a015377a771bf3790a1e63afa8',
}
FOLLOWUP_CASES = ('P20_OW07_POSITIVE_CLOSE', 'P20_AUTH_CASH_01_02', 'P20_SALE_SERIES_BROWSER')
RETAINED_CASES = tuple(case for case in p20_evidence.CASES if case not in p20_evidence.REMAINING_CASES)
ORIGINAL_CASES = tuple(case for case in RETAINED_CASES if case not in FOLLOWUP_CASES)
require = p20_evidence.need


def original_name(source):
    return f"p20-auditor-original-{source['run']}.zip"


def read_receipt(scratch, source, version, passed, worker_artifact):
    path = Path(scratch) / original_name(source)
    require(not path.is_symlink() and path.is_file() and path.stat().st_size == source['bytes'],
            'AUDITOR_P20_PRIOR_ARCHIVE_REQUIRED')
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == source['sha256'], 'AUDITOR_P20_PRIOR_ARCHIVE_DIGEST_CHANGED')
    with ZipFile(BytesIO(raw)) as archive:
        member = 'CP7_GLOBAL_INSTALLED_FINAL.json'
        require(archive.namelist() == [member] and archive.testzip() is None,
                'AUDITOR_P20_PRIOR_ARCHIVE_INVALID')
        receipt_bytes = archive.read(member)
    require(sha256(receipt_bytes).hexdigest() == source['member_sha256'],
            'AUDITOR_P20_PRIOR_RECEIPT_DIGEST_CHANGED')
    receipt = json.loads(receipt_bytes)
    require(receipt['contract'] == f'cp7.audit.p20.codex.a752.v{version}'
            and receipt['status'] == 'INCOMPLETE'
            and receipt['runner'] == dict(repository=p20_evidence.REPO, event='workflow_dispatch',
                pr=None, base=None, head=source['runner'], merge=source['runner'],
                candidate_sha=p20_evidence.PRODUCT, run_id=source['run'], run_attempt=source['attempt'])
            and receipt['successor'] == dict(head=p20_evidence.PRODUCT, tree=p20_evidence.PRODUCT_TREE)
            and receipt['auditor_sources']['oracle']['sha256'] == p20_evidence.FROZEN['oracle']
            and receipt['auditor_sources']['manifest']['sha256'] == p20_evidence.FROZEN['manifest']
            and receipt['production_go'] is receipt['independent_acceptance'] is False,
            'AUDITOR_P20_PRIOR_CANDIDATE_OR_ORACLE_CHANGED')
    archive_receipts = receipt['p20_checkpoint_archive']['receipts']
    require(all(receipt['checks'][key] is True for key in
                ('preflight', 'candidate', 'package_identity', 'full_restore', 'transport', 'issuer_baseline'))
            and all(receipt['workflow'][key] == 'success' for key in ('cleanup', 'preflight', 'stack', 'transport'))
            and archive_receipts['worker-exit']['artifact_id'] == worker_artifact
            and receipt['verified_real_auth_actors'] == 2, 'AUDITOR_P20_PRIOR_RESTORE_OR_CLEANUP_UNVERIFIED')
    cases = receipt['p20_cases']
    require(receipt['actual_Global_cases'] == len(passed) and tuple(receipt['passed_case_ids']) == passed
            and {key for key, case in cases.items() if case['status'] == 'PASS'} == set(passed)
            and all(archive_receipts['case-' + key]['status'] == 'UPLOADED' for key in passed),
            'AUDITOR_P20_PRIOR_CASE_SET_CHANGED')
    return receipt


def retained(scratch):
    initial = read_receipt(scratch, ORIGINAL, 1, ORIGINAL_CASES, 14291578603)
    followup = read_receipt(scratch, FOLLOWUP, 2, FOLLOWUP_CASES, 14296994960)
    previous_scope = (*FOLLOWUP_CASES, *p20_evidence.REMAINING_CASES)
    require(followup['retained_audited_P20'] == dict(**ORIGINAL, case_ids=list(ORIGINAL_CASES), repeated=False)
            and tuple(followup['planned_case_ids']) == tuple(followup['executed_case_ids']) == previous_scope
            and len(ORIGINAL_CASES) == 9 and len(RETAINED_CASES) == 12,
            'AUDITOR_P20_PRIOR_AUDIT_LINEAGE_CHANGED')
    observed = {key: initial['p20_cases'][key] for key in ORIGINAL_CASES}
    observed.update((key, followup['p20_cases'][key]) for key in FOLLOWUP_CASES)
    return observed


def provenance():
    return dict(originals=[dict(**ORIGINAL, case_ids=list(ORIGINAL_CASES)),
                           dict(**FOLLOWUP, case_ids=list(FOLLOWUP_CASES))],
                case_ids=list(RETAINED_CASES), repeated=False)
