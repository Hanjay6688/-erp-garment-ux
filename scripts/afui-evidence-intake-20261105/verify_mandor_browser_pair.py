"""Verify the pinned browser pair archive using the established Afui read-only path."""

import gzip
import json
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from retain import api, copy_stream, metadata, require, save
from verify_terminal import GATES, bounded_diagnostic, exact, member_pins, pin, strict


REPO = 'Hanjay6688/-erp-garment-ux'
RUN = 42752853455
JOB = 129620303386
HEAD = 'e63c758990f54dbec4e635ecf3d53c6e80b03041'
TREE = 'c7634a3a39254c08894ea1ba5ea0f1b8fc2c7b7a'
OWNER_TOOL_HEAD = 'a0e7d5616a0ac470876409d31c41388159f17692'
BRANCH = 'astra-a/mandor-shop-native9-on-unified-20261103'
JOB_NAME = 'Mandor desktop then mobile with actual Auth and full cleanup'
ARTIFACT = 'mandor-browser-pair-1'
DESKTOP = 'MANDOR_BROWSER_DESKTOP_NORMAL_PAYROLL_LOST_REPLY_SAME_UUID_TWO_TABS_RELEASE'
MOBILE = 'MANDOR_BROWSER_MOBILE390_NORMAL_PAYROLL_STALE_INPUT_FRESH_READ_RELEASE'
OUTPUT = 'mandor-browser-pair-terminal-receipts'
BOUNDARY = ('baseline_full22_all_rows_all_sequences_equal', 'restore_raw_public_equal',
            'cp6_restored', 'baseline_advisors_equal', 'advisor_gate', 'used_guard_refused_before_DDL')
HANDOFF_TABLES = {'cp7_mandor_shop.allocations', 'cp7_mandor_shop.allocation_events',
                  'cp7_mandor_shop.requests', 'cp7_mandor_shop.deduction_links',
                  'erp.payroll_deductions', 'erp.payroll_settlements'}


def verify_archive(path, identity, job):
    with ZipFile(path) as bundle:
        members = member_pins(bundle)
        by_name = {PurePosixPath(name).name: name for name in members}
        require(len(by_name) == len(members), 'MANDOR_PAIR_UNIQUE_MEMBER_BASENAMES')

        def report(name):
            return strict(bundle.read(by_name[name])) if name in by_name else None

        owning = report('MANDOR_BROWSER_PAIR_FOCUSED_OWNING.json')
        worker = report('MANDOR_BROWSER_PAIR_FOCUSED_WORKER.json')
        gate = report('MANDOR_BROWSER_PAIR_FOCUSED_GATE.json')
        backup = report('T3_BACKUP_RESTORE_DRILL.json')
        package = report('T3_PACKAGE_INSTALL.json')
        browser = report('MANDOR_BROWSER2_ORIGINAL.json')
        restored = bool(backup and backup['status'] == 'RESTORED_IDENTICAL' and backup['checks']
                        and all(check is True for check in backup['checks'].values())
                        and backup['data']['differ'] == {})
        reaped = bool(worker and worker.get('process_tree_empty') is True
                      and worker.get('process_group_empty') is True and worker.get('orphaned_child') is False)
        receipt = dict(status='MANDOR_BROWSER_PAIR_TERMINAL_ORIGINAL_BYTES_VERIFIED',
                       **identity, all_member_crc_verified=True, members=members,
                       backup_restored=restored, worker_reaped=reaped,
                       formal_case_credit=0, ERP_commands_executed=0)
        if identity['conclusion'] != 'success':
            receipt['first_failed_step'] = next((s for s in job['steps']
                if s['conclusion'] in ('failure', 'cancelled', 'timed_out', 'action_required')), None)
            receipt['owning_error'] = bounded_diagnostic((owning or {}).get('error'))
            receipt['browser_errors'] = {key: bounded_diagnostic(row.get('error'))
                for key, row in (browser or {}).get('cases', {}).items() if row['status'] != 'PASS'}
            receipt['boundary'] = {key: (owning or {}).get(key) for key in BOUNDARY}
            receipt['five_gates'] = (package or {}).get('gate')
            return receipt

        completed = {step['number']: step['conclusion'] for step in job['steps']}
        require(all(completed.get(number) == 'success' for number in (78, 79, 80, 81)),
                'MANDOR_PAIR_ACTUAL_BROWSER_GATE_RESTORE_AND_UPLOAD_STEPS')
        require(restored and reaped and owning and worker and gate and package and browser,
                'MANDOR_PAIR_ALL_TERMINAL_ORIGINALS')
        exact(owning, dict(status='PASS', diagnostic_only=True, formal_case_credit=0,
                          actual_business_cases=2, actual_browser_cases=2, actual_Native_cases=0,
                          actual_Auth_HTTP_cases=0, actual_two_session_races=0, **dict.fromkeys(BOUNDARY, True)),
              'MANDOR_PAIR_OWNING_ORIGINAL')
        exact(worker, dict(status='WORKER_COMPLETED_AND_REAPED', worker_exit=0, deadline_reached=False,
                          external_signal=None, signals=[], head=HEAD, run_id=str(RUN), attempt=1),
              'MANDOR_PAIR_WORKER')
        exact(gate, dict(status='BROWSER_PAIR_PASS', head=HEAD, run_id=str(RUN), attempt=1,
                        legacy_tool_head=OWNER_TOOL_HEAD, diagnostic_only=True, formal_case_credit=0,
                        actual_browser_cases=2, full_restoration=True, five_package_gates=True,
                        primary_Auth_counts_restored=True, production_go=False, independent_acceptance=False),
              'MANDOR_PAIR_GATE')
        require(package['gate'] == GATES, 'MANDOR_PAIR_ACTUAL_FIVE_PACKAGE_GATES')
        exact(package['run_identity'], dict(tool_head=OWNER_TOOL_HEAD, github_sha=HEAD, run_id=str(RUN),
                                           run_attempt='1', job='browser_prerequisites_only'), 'MANDOR_PAIR_PACKAGE')
        require(browser['planned_case_ids'] == [DESKTOP, MOBILE] and set(browser['cases']) == {DESKTOP, MOBILE}
                and browser['real_auth'] is True and browser['auth_counts']['restored'] is True
                and browser['database_remaining'] == 0, 'MANDOR_PAIR_EXACT_AUTH_JOURNEY')
        desktop, mobile = (browser['cases'][case] for case in (DESKTOP, MOBILE))
        for row in (desktop, mobile):
            exact(row, dict(status='PASS', real_Auth=True, product_responses_mocked=False),
                  'MANDOR_PAIR_ACTUAL_TRANSACTIONS')
            require(len(row['complete_census_proofs']) == 4, 'MANDOR_PAIR_FULL_OBSERVATION_PAIRS')
            exact(row['actual_release'], dict(status=200), 'MANDOR_PAIR_RELEASE_RESPONSE')
            exact(row['actual_release']['body'], dict(action='RELEASE'), 'MANDOR_PAIR_ACTUAL_RELEASE')
        replay = desktop['journey']['exact_second_tab_replay']
        exact(replay, dict(status=200, request=desktop['actual_first_request'], body=desktop['actual_first_reply']),
              'MANDOR_PAIR_EXACT_DESKTOP_REPLAY')
        stale = mobile['journey']['actual_stale_response']
        exact(stale, dict(status=400), 'MANDOR_PAIR_REAL_MOBILE_STALE_REFUSAL')
        exact(stale['body'], dict(code='P0001', message='CP7_MANDOR_SHOP_REVIEW_CHANGED'),
              'MANDOR_PAIR_EXPECTED_STALE_TOKEN')
        require(len(owning['committed']) == 1, 'MANDOR_PAIR_ONE_COMMITTED_COMPONENT')
        part = next(iter(owning['committed'].values()))
        for key in ('browser2_original', 'browser_fixture_original', 'browser_state_original',
                    'browser_state_cache_original'):
            reference = part[key]
            exact(members[by_name[reference['name']]], {field: reference[field] for field in ('bytes', 'sha256')},
                  'MANDOR_PAIR_RETAINED_OWNER_SOURCE_PIN')
        for name, reference in gate['original_observations'].items():
            exact(members[by_name[name]], dict(bytes=reference['gzip_bytes'], sha256=reference['gzip_sha256']),
                  'MANDOR_PAIR_RETAINED_CENSUS')
        for screenshot in gate['screenshots']:
            exact(members[by_name[screenshot['name']]], {key: screenshot[key] for key in ('bytes', 'sha256')},
                  'MANDOR_PAIR_RETAINED_SCREENSHOT')
        handoff = gate['browser_handoff']
        exact(handoff, dict(desktop_case_id=DESKTOP, mobile_case_id=MOBILE,
                            desktop_after=desktop['complete_census_proofs'][-1]['original_after'],
                            mobile_before=mobile['complete_census_proofs'][0]['original_before'],
                            released_allocation_id=desktop['actual_first_reply']['allocation_id']),
              'MANDOR_PAIR_ORIGINAL_CHAIN')
        observed = []
        for reference in (handoff['desktop_after'], handoff['mobile_before']):
            require(gate['original_observations'][reference['name']] == reference, 'MANDOR_PAIR_CHAIN_CENSUS_LINK')
            raw = gzip.decompress(bundle.read(by_name[reference['name']]))
            exact(pin(raw), {key: reference[key] for key in ('bytes', 'sha256')}, 'MANDOR_PAIR_CHAIN_RAW_CENSUS')
            observed.append(strict(raw))
        left, right = observed
        require(desktop['source'] == mobile['source'] and desktop['business_day'] == mobile['business_day']
                and all(left[key] == right[key] for key in ('invoice', 'allocation_states', 'deductions', 'payroll')),
                'MANDOR_PAIR_SAME_ENTRY_STATE')
        require(set(handoff['unchanged_tables']) == HANDOFF_TABLES
                and all(left['full_data_and_sequences'][key] == right['full_data_and_sequences'][key]
                        for key in handoff['unchanged_tables']), 'MANDOR_PAIR_IMMUTABLE_REQUESTS_PRESERVED')
        require(any(row['allocation_id'] == handoff['released_allocation_id'] and row['state'] == 'RELEASED'
                    for row in right['allocation_states']), 'MANDOR_PAIR_RELEASE_PRESENT_BEFORE_MOBILE')
        return dict(receipt, actual_browser_passes=[DESKTOP, MOBILE], five_gates=package['gate'],
                    primary_Auth_restored=True, boundary=dict.fromkeys(BOUNDARY, True), browser_handoff=handoff)


def main():
    binding = strict(Path(__file__).with_name('terminal_mandor_pair_binding.json').read_bytes())
    archive, artifact_id, conclusion = binding['archive'], binding['artifact_id'], binding['conclusion']
    require(type(artifact_id) is int and artifact_id > 0 and type(archive['bytes']) is int
            and archive['bytes'] > 0 and conclusion in ('success', 'failure', 'cancelled', 'timed_out'),
            'MANDOR_PAIR_REAL_TERMINAL_BINDING_REQUIRED')
    route = f'/repos/{REPO}/actions/'
    with TemporaryDirectory(prefix='mandor-pair-original-') as directory:
        work = Path(directory)
        run = metadata(route + f'runs/{RUN}', work / 'run.json')
        job = metadata(route + f'jobs/{JOB}', work / 'job.json')
        artifact = metadata(route + f'artifacts/{artifact_id}', work / 'artifact.json')
        exact(run, dict(id=RUN, head_branch=BRANCH, head_sha=HEAD, status='completed',
                        run_attempt=1, conclusion=conclusion), 'MANDOR_PAIR_TERMINAL_RUN')
        exact(run['head_commit'], dict(tree_id=TREE), 'MANDOR_PAIR_TERMINAL_TREE')
        exact(job, dict(id=JOB, name=JOB_NAME, run_id=RUN, head_sha=HEAD, status='completed',
                        run_attempt=1, conclusion=conclusion), 'MANDOR_PAIR_OWNING_JOB')
        exact(artifact, dict(id=artifact_id, name=ARTIFACT, expired=False, size_in_bytes=archive['bytes'],
                             digest='sha256:' + archive['sha256']), 'MANDOR_PAIR_CANONICAL_ARTIFACT')
        exact(artifact['workflow_run'], dict(id=RUN, head_sha=HEAD), 'MANDOR_PAIR_SAME_RUN_ARTIFACT')
        target = work / 'canonical.zip'
        with api(route + f'artifacts/{artifact_id}/zip') as source, target.open('xb') as stream:
            require(copy_stream(source, stream, archive['bytes']) == archive, 'MANDOR_PAIR_EXACT_ARCHIVE_BYTES')
        receipt = verify_archive(target, dict(run=RUN, job=JOB, attempt=1, head=HEAD, tree=TREE,
            artifact_id=artifact_id, archive=archive, conclusion=conclusion), job)
    out = Path(OUTPUT)
    out.mkdir()
    save(out / 'TERMINAL_RECEIPT.json', receipt)
    print(json.dumps({key: receipt[key] for key in ('status', 'run', 'job', 'conclusion',
        'artifact_id', 'archive', 'all_member_crc_verified', 'backup_restored', 'worker_reaped')}),
        flush=True)


if __name__ == '__main__':
    main()
