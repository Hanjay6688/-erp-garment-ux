"""Check the exact terminal Afui archive without provisioning or executing ERP."""
from hashlib import file_digest, sha256
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import json
import os
import re
import stat

from retain import api, copy_stream, metadata, require, save

REPOSITORY = 'Hanjay6688/-erp-garment-ux'
RUN = 42178605233
JOB = 127762728439
HEAD = '8e5a0511c0f5a68ea5fcc1cf2649d36703d119ac'
TREE = 'c72147b650123a1faa38a8ce99144e690cb395d3'
BRANCH = 'astra-a/afui-good-nonpayable-20261102'
OWNER = 'Afui Native9 Auth2 session2 browser2; complete restoration'
CANONICAL = 'cp7-afui-good-nonpayable-full15-1'
MAIN = 'CP7_AFUI_GOOD_NONPAYABLE_FULL15.json'
NATIVE = 'CP7_AFUI_GOOD_NONPAYABLE_FULL15_NATIVE9.json'
GATE = 'AFUI_FINAL_GATE.json'
INSTALL = 'T3_PACKAGE_INSTALL.json'
RESTORE = 'T3_BACKUP_RESTORE_DRILL.json'
WORKER = 'AFUI_RUNTIME_SUPERVISION.json'
ADOPTION_FILES = (MAIN, NATIVE, GATE, INSTALL, RESTORE, WORKER)
COUNTS = dict(actual_Native_cases=9, actual_Auth_HTTP_cases=2,
              actual_two_session_races=2, actual_browser_cases=2)
GATES = dict(installed=True, primary_unchanged=True, backup_restore_drill=True,
             security_advisors=True, writer_runtime=True)
BOUNDARY = ('baseline_full22_all_rows_all_sequences_equal', 'restore_raw_public_equal',
            'cp6_restored', 'baseline_advisors_equal')


def exact(actual, expected, label):
    for key, value in expected.items():
        require(type(actual.get(key)) is type(value) and actual[key] == value, label + ':' + key)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'AFUI_DUPLICATE_ORIGINAL_JSON_FIELD')
        result[key] = value
    return result


def reject_constant(_):
    raise ValueError('AFUI_NONFINITE_ORIGINAL_JSON_NUMBER')


def strict(raw):
    return json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def member_pins(bundle):
    pins, names = {}, set()
    for info in bundle.infolist():
        path = PurePosixPath(info.filename)
        mode = stat.S_IFMT(info.external_attr >> 16)
        require(info.filename not in names and path.parts and not path.is_absolute()
                and '..' not in path.parts and path.as_posix() == info.filename.rstrip('/')
                and '\\' not in info.filename and mode in (0, stat.S_IFREG, stat.S_IFDIR),
                'AFUI_UNSAFE_OR_DUPLICATE_ZIP_MEMBER')
        names.add(info.filename)
        if info.is_dir():
            require(info.file_size == info.CRC == 0, 'AFUI_NONEMPTY_DIRECTORY_ZIP_MEMBER')
            continue
        with bundle.open(info) as stream:
            digest = file_digest(stream, 'sha256').hexdigest()
        pins[info.filename] = dict(bytes=info.file_size, sha256=digest, crc32=f'{info.CRC:08x}')
    require(bool(pins), 'AFUI_FINAL_ARTIFACT_EMPTY')
    return pins


def bounded_diagnostic(value):
    if value is None:
        return None
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=True, sort_keys=True)
    value = re.sub(r'\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b', '[redacted token]', value)
    value = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[redacted email]', value)
    value = re.sub(r'https?://[^\s"<>]+', '[redacted URL]', value)
    value = re.sub(r'\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b', '[fixture identifier]', value)
    return value[:10000]


def failure_diagnostics(bundle, main):
    errors = []
    for info in bundle.infolist():
        if info.file_size > 256 * 1024 or not re.fullmatch(
                r'AFUI_(DESKTOP|MOBILE390)_[A-F0-9]{32}_(FIRST|CLEANUP)_FAILURE\.json', info.filename):
            continue
        raw = bundle.read(info)
        row = strict(raw)
        errors.append(dict(name=info.filename, original=pin(raw),
                           error=bounded_diagnostic(row.get('error', row.get('primary_error'))),
                           completed_checkpoints=sorted(row['progress']) if isinstance(row.get('progress'), dict) else []))
    return dict(status='AFUI_REDACTED_TERMINAL_DIAGNOSTIC_FROM_EXACT_ORIGINAL', source_run=RUN,
                main_error=bounded_diagnostic((main or {}).get('error')), browser_errors=errors)


def verify(source_zip, source_run, source_job, archive, artifact):
    outcome = source_run['conclusion']
    with ZipFile(source_zip) as bundle:
        members = member_pins(bundle)
        member_count = len(bundle.infolist())

        def report(name):
            return strict(bundle.read(name)) if name in members else None

        gate, package, backup, worker = map(report, (GATE, INSTALL, RESTORE, WORKER))
        main = report(MAIN)
        diagnostics = failure_diagnostics(bundle, main) if outcome != 'success' else None

    if worker is not None:
        exact(worker, dict(qualification_commit=HEAD, github_run_id=str(RUN), github_run_attempt='1'),
              'AFUI_SAME_RUN_SUPERVISOR')
    if package is not None:
        exact(package['run_identity'], dict(tool_head=HEAD, github_sha=HEAD, run_id=str(RUN), run_attempt='1'),
              'AFUI_SAME_RUN_PACKAGE')
    if main is not None:
        exact(main, dict(qualification_commit=HEAD), 'AFUI_SAME_RUN_MAIN')

    failed = next((step for step in source_job['steps']
                   if step.get('conclusion') in ('failure', 'cancelled', 'timed_out', 'action_required')), None)
    restored = bool(backup and backup['status'] == 'RESTORED_IDENTICAL' and backup.get('checks')
                    and all(value is True for value in backup['checks'].values()) and backup['data']['differ'] == {})
    reaped = bool(worker and worker.get('process_group_empty') is True
                  and worker.get('process_tree_empty') is True and worker.get('orphaned_child') is False)
    error = (main or {}).get('error')
    receipt = dict(status='AFUI_TERMINAL_ORIGINAL_BYTES_VERIFIED', head=HEAD, run=RUN, job=JOB, attempt=1,
                   conclusion=outcome, artifact_id=artifact, archive=archive, zip_members=member_count,
                   all_member_crc_verified=True, members=members, first_failed_step=failed,
                   first_reported_error_sha256=sha256(json.dumps(error, ensure_ascii=True, sort_keys=True).encode()).hexdigest()
                   if error is not None else None,
                   main_status=(main or {}).get('status'), actual_backup_restored_identical=restored,
                   actual_worker_reaped=reaped, boundary={key: (main or {}).get(key) for key in BOUNDARY},
                   actual_case_credit=0, production_go=False, independent_acceptance=False,
                   ERP_commands_executed=0)
    if outcome != 'success':
        receipt['failure_diagnostics'] = diagnostics
        receipt['package_gate_values'] = package.get('gate') if package is not None else None
        return receipt
    require(not failed and restored and reaped and gate and package and main, 'AFUI_TERMINAL_SUCCESS_EVIDENCE_REQUIRED')
    exact(gate, dict(status='CURRENT_AFUI_GOOD_NONPAYABLE_NATIVE9_HTTP2_SESSION2_BROWSER2_AND_ALL5_PASS',
                     head=HEAD, actual_fresh_cases=15, **COUNTS), 'AFUI_FINAL_GATE')
    exact(main, dict(status='PASS', actual_business_cases=15, **COUNTS, **dict.fromkeys(BOUNDARY, True)),
          'AFUI_COMPLETE_MAIN')
    exact(worker, dict(status='WORKER_COMPLETED_AND_REAPED', worker_exit=0, deadline_reached=False,
                       job_budget_seconds=21600, work_budget_seconds=19800,
                       recovery_reserve_seconds=1200, artifact_reserve_seconds=600), 'AFUI_COMPLETE_OWNER')
    require(set(package['gate']) == set(GATES), 'AFUI_EXACT_FIVE_PACKAGE_GATES')
    exact(package['gate'], GATES, 'AFUI_ACTUAL_FIVE_PACKAGE_GATES')
    require(any(step['name'] == 'Require complete Afui15 and full restoration in the final packet gate'
                and step['conclusion'] == 'success' for step in source_job['steps']), 'AFUI_OWNING_FINAL_GATE_MUST_HAVE_RUN')
    require(all(name in members for name in ADOPTION_FILES), 'AFUI_ALL_SIX_ADOPTION_ORIGINALS_REQUIRED')
    graph = json.dumps(main['source_declaration']['complete_sources'],
                       sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    receipt.update(actual_case_credit=15, actual_all_five=True, actual_outer_restore=True,
                   qualified_Afui_good_nonpayable_sources=pin(graph))
    return receipt


def save_root(out, receipt):
    receipt_raw = (out / 'TERMINAL_RECEIPT.json').read_bytes()
    originals = {name: {key: receipt['members'][name][key] for key in ('bytes', 'sha256')} for name in ADOPTION_FILES}
    root = dict(status='ROOT_VERIFIED_CURRENT_AFUI_GOOD_NONPAYABLE_FULL15_ALL5',
                head=HEAD, tree=TREE, run_id=RUN, job_id=JOB, artifact_id=receipt['artifact_id'],
                archive=dict(receipt['archive'], members=receipt['zip_members']), originals=originals,
                qualified_Afui_good_nonpayable_sources=receipt['qualified_Afui_good_nonpayable_sources'],
                **COUNTS, actual_business_cases=15, complete15_qualified=True, package_all_five=True,
                actual_outer_restore=True, prior_runs_aggregated=False, production_go=False,
                independent_acceptance=False, terminal_verification_receipt=pin(receipt_raw))
    save(out / 'AFUI15_PARENT_ROOT_ACTUAL_INTAKE.json', root)


def main():
    binding = strict(Path(__file__).with_name('terminal_8e5_binding.json').read_bytes())
    outcome, artifact = binding['conclusion'], binding['artifact_id']
    require(outcome in ('success', 'failure', 'cancelled', 'timed_out') and type(artifact) is int and artifact > 0,
            'AFUI_REAL_TERMINAL_BINDING_REQUIRED')
    expected_archive = binding['archive']
    require(type(expected_archive['bytes']) is int and expected_archive['bytes'] > 0,
            'AFUI_EXACT_ARCHIVE_SIZE_REQUIRED')
    out = Path('afui-8e5-terminal-receipts')
    out.mkdir()
    route = f'/repos/{REPOSITORY}/actions/'
    with TemporaryDirectory(prefix='afui-terminal-') as directory:
        work = Path(directory)
        run = metadata(route + f'runs/{RUN}', work / 'run.json')
        job = metadata(route + f'jobs/{JOB}', work / 'job.json')
        meta = metadata(route + f'artifacts/{artifact}', work / 'artifact.json')
        exact(run, dict(id=RUN, head_branch=BRANCH, head_sha=HEAD, status='completed',
                        run_attempt=1, conclusion=outcome), 'AFUI_EXACT_TERMINAL_RUN')
        exact(job, dict(id=JOB, name=OWNER, run_id=RUN, head_sha=HEAD, status='completed',
                        run_attempt=1, conclusion=outcome), 'AFUI_EXACT_TERMINAL_JOB')
        exact(meta, dict(id=artifact, name=CANONICAL, expired=False, size_in_bytes=expected_archive['bytes'],
                         digest='sha256:' + expected_archive['sha256']), 'AFUI_EXACT_CANONICAL_ARTIFACT')
        exact(meta['workflow_run'], dict(id=RUN, head_sha=HEAD), 'AFUI_SAME_RUN_ORIGINAL')
        source_zip = work / 'canonical.zip'
        with api(route + f'artifacts/{artifact}/zip') as source, source_zip.open('xb') as target:
            archive = copy_stream(source, target, expected_archive['bytes'])
        require(archive == expected_archive, 'AFUI_EXACT_CANONICAL_ZIP_HASH_REQUIRED')
        receipt = verify(source_zip, run, job, archive, artifact)

    save(out / 'TERMINAL_RECEIPT.json', receipt)
    keys = ('status', 'head', 'run', 'job', 'attempt', 'conclusion', 'artifact_id', 'archive', 'zip_members',
            'all_member_crc_verified', 'first_failed_step', 'main_status', 'actual_backup_restored_identical',
            'actual_worker_reaped', 'boundary', 'actual_case_credit', 'production_go', 'independent_acceptance',
            'ERP_commands_executed')
    print('AFUI_EXACT_TERMINAL ' + json.dumps({key: receipt[key] for key in keys}, separators=(',', ':')), flush=True)
    if receipt['actual_case_credit'] == 15:
        save_root(out, receipt)
        with Path(os.environ['GITHUB_OUTPUT']).open('a') as stream:
            stream.write('mandor=ready\n')


if __name__ == '__main__':
    main()
