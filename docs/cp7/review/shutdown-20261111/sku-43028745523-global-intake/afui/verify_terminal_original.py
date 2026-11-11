"""Verify the terminal Afui archive against the same GitHub run and job."""
from hashlib import file_digest, sha256
from pathlib import Path, PurePosixPath
import argparse
import json
import stat
import zipfile

from verify_native_original import require, strict

BRANCH = 'astra-a/afui-good-nonpayable-20261102'
CURRENT_HEAD = 'fd797083eab093d9dc97f2d52ca61dc37812b437'
CURRENT_TREE = '02a8812e9eae2272a976d1dbd1e21aff8c022467'
OWNING_JOB = 'Afui Native9 Auth2 session2 browser2; complete restoration'
MAIN = 'CP7_AFUI_GOOD_NONPAYABLE_FULL15.json'
GATE = 'AFUI_FINAL_GATE.json'
RESTORE = 'T3_BACKUP_RESTORE_DRILL.json'
PACKAGE = 'T3_PACKAGE_INSTALL.json'
SUPERVISION = 'AFUI_RUNTIME_SUPERVISION.json'
COUNTS = dict(actual_Native_cases=9, actual_Auth_HTTP_cases=2,
              actual_two_session_races=2, actual_browser_cases=2)
GATES = dict(installed=True, primary_unchanged=True, backup_restore_drill=True,
             security_advisors=True, writer_runtime=True)
BOUNDARY = ('baseline_full22_all_rows_all_sequences_equal', 'restore_raw_public_equal',
            'cp6_restored', 'baseline_advisors_equal')


def fields(value, expected, label):
    for key, item in expected.items():
        require(type(value.get(key)) is type(item) and value[key] == item, label + ':' + key)


def files(archive, artifact):
    require(archive.is_file() and not archive.is_symlink(), 'AFUI_REGULAR_ORIGINAL_ZIP_REQUIRED')
    with archive.open('rb') as stream:
        pin = dict(bytes=archive.stat().st_size, sha256=file_digest(stream, 'sha256').hexdigest())
    require(pin['bytes'] == artifact['size_in_bytes'] and 'sha256:' + pin['sha256'] == artifact['digest'],
            'AFUI_EXACT_API_ARCHIVE_BYTES_REQUIRED')
    return pin


def member_pins(bundle):
    pins, seen = {}, set()
    for info in bundle.infolist():
        path = PurePosixPath(info.filename)
        mode = stat.S_IFMT(info.external_attr >> 16)
        require(info.filename not in seen and path.parts and not path.is_absolute() and '..' not in path.parts
                and path.as_posix() == info.filename.rstrip('/') and '\\' not in info.filename
                and mode in (0, stat.S_IFREG, stat.S_IFDIR), 'AFUI_UNSAFE_OR_DUPLICATE_ZIP_MEMBER')
        seen.add(info.filename)
        if info.is_dir():
            require(info.file_size == info.CRC == 0, 'AFUI_NONEMPTY_DIRECTORY_ZIP_MEMBER')
            continue
        with bundle.open(info) as stream:
            digest = file_digest(stream, 'sha256').hexdigest()
        pins[info.filename] = dict(bytes=info.file_size, sha256=digest, crc32=f'{info.CRC:08x}')
    require(bool(pins), 'AFUI_FINAL_ARTIFACT_EMPTY')
    return pins


def verify(archive, artifact, run, job):
    head, run_id, job_id = run['head_sha'], run['id'], job['id']
    fields(run, dict(head_branch=BRANCH, run_attempt=1, status='completed'), 'AFUI_TERMINAL_RUN')
    fields(job, dict(head_sha=head, run_id=run_id, run_attempt=1, status='completed',
                     conclusion=run['conclusion']), 'AFUI_TERMINAL_OWNING_JOB')
    require(job['name'] == OWNING_JOB, 'AFUI_EXACT_OWNING_JOB')
    fields(artifact, dict(name='cp7-afui-good-nonpayable-full15-1', expired=False), 'AFUI_CANONICAL_ARTIFACT')
    fields(artifact['workflow_run'], dict(id=run_id, head_sha=head), 'AFUI_SAME_RUN_ARTIFACT')
    archive_pin = files(archive, artifact)
    with zipfile.ZipFile(archive) as bundle:
        zip_members = len(bundle.infolist())
        pins = member_pins(bundle)
        def report(name):
            return strict(bundle.read(name)) if name in pins else None
        owned, backup, package = report(SUPERVISION), report(RESTORE), report(PACKAGE)
        gate = report(GATE)
        main = report(MAIN)
    if owned is not None:
        fields(owned, dict(qualification_commit=head, github_run_id=str(run_id), github_run_attempt='1'),
               'AFUI_SAME_RUN_SUPERVISOR')
    if package is not None:
        fields(package['run_identity'], dict(tool_head=head, github_sha=head, run_id=str(run_id), run_attempt='1'),
               'AFUI_SAME_RUN_PACKAGE')
    if main is not None:
        fields(main, dict(qualification_commit=head), 'AFUI_SAME_RUN_MAIN')
    failed = next((step for step in job['steps']
                   if step.get('conclusion') in ('failure', 'cancelled', 'timed_out', 'action_required')), None)
    restored = bool(backup and backup['status'] == 'RESTORED_IDENTICAL' and backup.get('checks')
                    and all(v is True for v in backup['checks'].values()) and backup['data']['differ'] == {})
    reaped = bool(owned and owned.get('process_group_empty') is True
                  and owned.get('process_tree_empty') is True and owned.get('orphaned_child') is False)
    accepted = run['conclusion'] == 'success'
    result = dict(
        status='AFUI_TERMINAL_ORIGINAL_BYTES_VERIFIED', head=head, run=run_id, job=job_id, attempt=1,
        conclusion=run['conclusion'], artifact_id=artifact['id'], archive=archive_pin, zip_members=zip_members,
        all_member_crc_verified=True,
        members=pins, first_failed_step=failed, first_reported_error=(main or {}).get('error'),
        main_status=(main or {}).get('status'), actual_backup_restored_identical=restored, actual_worker_reaped=reaped,
        boundary={name: (main or {}).get(name) for name in BOUNDARY},
        actual_case_credit=0, production_go=False, independent_acceptance=False)
    if accepted:
        require(not failed and restored and reaped and gate and package and main, 'AFUI_TERMINAL_SUCCESS_EVIDENCE_REQUIRED')
        fields(gate, dict(status='CURRENT_AFUI_GOOD_NONPAYABLE_NATIVE9_HTTP2_SESSION2_BROWSER2_AND_ALL5_PASS',
                          head=head, actual_fresh_cases=15, **COUNTS), 'AFUI_FINAL_GATE')
        fields(main, dict(status='PASS', actual_business_cases=15, **COUNTS,
                          **dict.fromkeys(BOUNDARY, True)), 'AFUI_COMPLETE_MAIN')
        fields(owned, dict(status='WORKER_COMPLETED_AND_REAPED', worker_exit=0, deadline_reached=False,
                           job_budget_seconds=21600, work_budget_seconds=19800,
                           recovery_reserve_seconds=1200, artifact_reserve_seconds=600), 'AFUI_COMPLETE_OWNER')
        require(set(package['gate']) == set(GATES), 'AFUI_EXACT_FIVE_PACKAGE_GATES')
        fields(package['gate'], GATES, 'AFUI_ACTUAL_FIVE_PACKAGE_GATES')
        require(any(step['name'] == 'Require complete Afui15 and full restoration in the final packet gate'
                    and step['conclusion'] == 'success' for step in job['steps']), 'AFUI_OWNING_FINAL_GATE_MUST_HAVE_RUN')
        graph = main['source_declaration']['complete_sources']
        raw = json.dumps(graph, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        result.update(actual_case_credit=15, actual_all_five=True, actual_outer_restore=True,
                      qualified_Afui_good_nonpayable_sources=dict(bytes=len(raw), sha256=sha256(raw).hexdigest()))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('archive', 'artifact', 'run', 'job', 'receipt'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    value = verify(args.archive, *(strict(path.read_bytes()) for path in (args.artifact, args.run, args.job)))
    with args.receipt.open('x') as out:
        json.dump(value, out, indent=2, sort_keys=True)
        out.write('\n')
    keys = ('status', 'conclusion', 'artifact_id', 'actual_case_credit', 'actual_backup_restored_identical',
            'actual_worker_reaped', 'first_reported_error')
    print(json.dumps({key: value[key] for key in keys}, sort_keys=True))


if __name__ == '__main__':
    main()
