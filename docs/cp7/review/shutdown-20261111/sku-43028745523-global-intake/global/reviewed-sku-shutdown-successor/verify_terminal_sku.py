"""Extract the complete Global input catalogue from a genuine owning SKU Original."""
from hashlib import sha256
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys
import zipfile

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / 'afui'))
from verify_terminal_original import BOUNDARY, GATES, fields, files, member_pins, require, strict

from reviewed_sku_source import add_cli, from_cli, verify_source, verify_cumulative_mandor

BRANCH = 'astra-a/sku-current-parent-money-automatic-native25-20261105'
AREA = 'scripts/current-sku-automatic-composite-preparation/'
PARENT = AREA + 'MANDOR17_PARENT_ROOT_ACTUAL_INTAKE.json'
WORKFLOW = '.github/workflows/cp7-sku-current-parent-money-automatic-native25.yml'
CASE = 'CURRENT_MANDOR_PARENT_SKU_MONEY_AUTOMATIC_NATIVE25_BROWSER2_AND_USED_INVERSE'
MAIN = 'CP7_SKU_CURRENT_PARENT_MONEY_AUTOMATIC_QUALIFICATION.json'
NATIVE = 'CP7_SKU_CURRENT_PARENT_MONEY_AUTOMATIC_NATIVE25.json'
PREFLIGHT = 'CP7_SKU_CURRENT_PARENT_MONEY_AUTOMATIC_NATIVE25_PREFLIGHT.json'
BROWSER = 'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_BROWSER2.json'
GATE = 'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_FINAL_GATE.json'
PACKAGE = 'T3_PACKAGE_INSTALL.json'
BACKUP = 'T3_BACKUP_RESTORE_DRILL.json'
SUPERVISOR = 'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_RUNTIME_SUPERVISION.json'
CATALOGUE = 'SKU_GLOBAL_PARENT_ACTUAL_FULL25.json'
COUNTS = dict(actual_Native_cases=25, actual_Auth_HTTP_cases=0, actual_two_session_races=0, actual_browser_cases=2)
READERS = {
    'composition.py': dict(bytes=21891, sha256='aa5139dcc0a87445e4fbecd1af0aca9cdf70b9e53b5a6be523aebe86d38029e4'),
    'catalogue_profile.py': dict(bytes=4607, sha256='e34234eab2e4c36f8c63742a504569f954957241c0cbc679e9b420d12218b19e'),
}
CATALOGUE_GROUPS = frozenset(('aggregates', 'casts', 'columns', 'constraints', 'database_authority',
    'default_privileges', 'enums', 'event_triggers', 'extensions', 'functions', 'indexes', 'inheritance',
    'languages', 'memberships', 'operators', 'policies', 'relations', 'roles', 'rules', 'schemas',
    'sequence_ownership', 'sequences', 'triggers', 'type_implementation', 'types'))


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def catalogue(raw, observation, head, run):
    fields(observation, dict(status='ACTUAL_FULL25_SKU_CATALOGUE_OBSERVED', head=head,
                              run_id=str(run), attempt=1, original=dict(name=CATALOGUE, **pin(raw)),
                              readers=READERS, actual_ERP_case_credit=0, complete_input_review=False,
                              production_go=False), 'GLOBAL_ACTUAL_OWNING_SKU_CATALOGUE')
    groups = strict(raw)
    require(set(groups) == CATALOGUE_GROUPS and all(type(rows) is list and all(type(row) is list
            and len(row) == 2 and type(row[0]) is str for row in rows) for rows in groups.values()),
            'GLOBAL_EXACT_FULL25_NATIVE_KEY_VALUE_ROWS_REQUIRED')
    for name, rows in groups.items():
        require(len({row[0] for row in rows}) == len(rows), 'GLOBAL_DUPLICATE_CATALOGUE_IDENTITY:' + name)
    require(all(groups[key] for key in ('functions', 'relations', 'roles', 'operators', 'casts', 'languages')),
            'GLOBAL_CURRENT_COMBINED_CATALOGUE_REQUIRED')
    fingerprint = observation['fingerprint']
    fields(fingerprint, dict(contract='cp7.global-catalogue-fingerprint.v1', groups=25,
                             counts={name: len(rows) for name, rows in groups.items()}), 'GLOBAL_EXACT_FULL25_FINGERPRINT')
    require(re.fullmatch('[a-f0-9]{64}', fingerprint['sha256']) is not None, 'GLOBAL_PG_FINGERPRINT_SHA_REQUIRED')
    return dict(original=observation['original'], fingerprint=fingerprint, exact_query_sources=READERS)


def verify(archive, artifact, run, job, repo, reviewed_mandor_root, reviewed):
    head, run_id, job_id = run['head_sha'], run['id'], job['id']
    fields(run, dict(id=reviewed['run_id'], head_sha=reviewed['head'], head_branch=BRANCH, event='push', path=WORKFLOW,
                     run_attempt=1, status='completed'), 'SKU_TERMINAL_RUN')
    fields(job, dict(id=reviewed['job_id'], head_sha=head, run_id=run_id, run_attempt=1, status='completed', conclusion=run['conclusion'],
                     name='Actual Mandor parent, full money and automatic Native25; complete restoration'), 'SKU_OWNING_JOB')
    fields(artifact, dict(name='cp7-sku-current-parent-money-automatic-native25-1', expired=False), 'SKU_CANONICAL_ARTIFACT')
    fields(artifact['workflow_run'], dict(id=run_id, head_sha=head, head_branch=BRANCH), 'SKU_SAME_RUN_ARTIFACT')
    archive_pin = files(archive, artifact)
    accepted = run['conclusion'] == 'success'
    with zipfile.ZipFile(archive) as bundle:
        pins = member_pins(bundle)
        archive_pin['members'] = len(bundle.infolist())
        main, gate, package, backup, owned = [strict(bundle.read(name)) if name in pins else None
                                             for name in (MAIN, GATE, PACKAGE, BACKUP, SUPERVISOR)]
        raw = bundle.read(CATALOGUE) if accepted and CATALOGUE in pins else None
    if main is not None:
        fields(main, dict(qualification_commit=head), 'SKU_SAME_RUN_MAIN')
    if owned is not None:
        fields(owned, dict(qualification_commit=head, github_run_id=str(run_id), github_run_attempt='1'), 'SKU_SAME_RUN_OWNER')
    if package is not None:
        fields(package['run_identity'], dict(tool_head=head, github_sha=head, run_id=str(run_id), run_attempt='1'), 'SKU_SAME_RUN_PACKAGE')
    restored = bool(backup and backup['status'] == 'RESTORED_IDENTICAL' and backup.get('checks')
                    and all(v is True for v in backup['checks'].values()) and backup['data']['differ'] == {})
    reaped = bool(owned and owned.get('process_group_empty') is True and owned.get('process_tree_empty') is True
                  and owned.get('orphaned_child') is False)
    failed = next((s for s in job['steps'] if s['conclusion'] in ('failure', 'cancelled', 'timed_out')), None)
    successful_steps = {step['name'] for step in job['steps'] if step['conclusion'] == 'success'}
    cleaned = 'Remove disposable database' in successful_steps
    receipt = dict(status='SKU_TERMINAL_ORIGINAL_BYTES_VERIFIED', head=head, run_id=run_id, job_id=job_id, attempt=1,
                   conclusion=run['conclusion'], artifact_id=artifact['id'], archive=archive_pin, members=pins,
                   all_member_crc_verified=True, first_failed_step=failed, first_reported_error=(main or {}).get('error'),
                   actual_outer_restore=restored, actual_worker_reaped=reaped, github_disposable_cleanup_success=cleaned,
                   actual_case_credit=0, production_go=False)
    if not accepted:
        return receipt, None, None
    require(not failed and restored and reaped and main and gate and package and raw and {NATIVE, BROWSER} <= set(pins),
            'SKU_NATIVE25_BROWSER2_ALL_FIVE_AND_CATALOGUE_REQUIRED')
    fields(main, dict(status='PASS', actual_business_cases=27, real_Auth_browser_claim=True,
                      **COUNTS, **dict.fromkeys(BOUNDARY, True)), 'SKU_ACTUAL_NATIVE25_BROWSER2')
    fields(gate, dict(status='CURRENT_MANDOR_PARENT_MONEY_AUTOMATIC_NATIVE25_BROWSER2_AND_ALL5_PASS',
                      head=head, run_id=str(run_id), package_all_five=True,
                      prior_parent_cases_not_counted_as_fresh=True, **COUNTS), 'SKU_ACTUAL_FINAL_GATE')
    gate_members = (MAIN, NATIVE, PREFLIGHT, BROWSER, PACKAGE, BACKUP, SUPERVISOR)
    require(set(gate_members) <= set(pins) and gate['originals'] == {
        name: {key: pins[name][key] for key in ('bytes', 'sha256')} for name in gate_members
    }, 'SKU_FINAL_GATE_MUST_BIND_EXACT_ORIGINALS')
    fields(owned, dict(status='WORKER_COMPLETED_AND_REAPED', worker_exit=0, deadline_reached=False,
                       external_signal=None, job_budget_seconds=21600, work_budget_seconds=19800,
                       recovery_reserve_seconds=1200, artifact_reserve_seconds=600), 'SKU_COMPLETE_OWNER')
    require(set(package['gate']) == set(GATES), 'SKU_EXACT_FIVE_PACKAGE_GATES_REQUIRED')
    fields(package['gate'], GATES, 'SKU_ACTUAL_FIVE_PACKAGE_GATES')
    require('Run current-parent money automatic Native25 and real browser2 once with owning restoration' in successful_steps,
            'SKU_GITHUB_FINAL_GATE_REQUIRED')
    require(cleaned, 'SKU_GITHUB_DISPOSABLE_CLEANUP_REQUIRED')

    def git(*args):
        return subprocess.check_output(['git', '--no-lazy-fetch', '-C', str(repo), *args])

    verify_source(repo, head, reviewed, reviewed_mandor_root)
    mandor = git('show', head + ':' + PARENT)
    require(mandor == reviewed_mandor_root and gate['parent_root'] == pin(mandor), 'SKU_SAME_REAL_MANDOR_ROOT_REQUIRED')
    parent_evidence = verify_cumulative_mandor(repo, head, mandor)
    observation = catalogue(raw, main['committed'][CASE]['Global_parent_catalogue'], head, run_id)
    originals = {name: {k: pins[name][k] for k in ('bytes', 'sha256')}
                 for name in (MAIN, NATIVE, BROWSER, GATE, PACKAGE, BACKUP, SUPERVISOR, CATALOGUE)}
    root = dict(status='ROOT_VERIFIED_CURRENT_SKU_NATIVE25_BROWSER2_ALL5', head=head,
                tree=git('rev-parse', head + '^{tree}').decode().strip(), run_id=run_id, job_id=job_id,
                artifact_id=artifact['id'], archive=archive_pin, originals=originals, mandor_root=pin(mandor),
                mandor_evidence_mode=parent_evidence['mode'], mandor_cumulative_decision=parent_evidence['decision'],
                qualified_combined_SKU_sources=main['source_declaration']['complete_combined_sources'],
                global_parent_catalogue=observation, **COUNTS, actual_business_cases=27,
                package_all_five=True, actual_outer_restore=True, prior_runs_aggregated=False,
                complete_global_input_review=False, production_go=False, independent_acceptance=False)
    receipt.update(actual_case_credit=27, actual_all_five=True, actual_parent_root=pin(mandor),
                   global_parent_catalogue=observation, root_pin=pin((json.dumps(root, indent=2) + '\n').encode()))
    return receipt, root, raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('archive', 'artifact', 'run', 'job', 'repo', 'reviewed-mandor-root', 'receipt', 'root', 'catalogue-output'):
        parser.add_argument('--' + name, type=Path, required=True)
    add_cli(parser)
    args = parser.parse_args()
    metadata = [strict(path.read_bytes()) for path in (args.artifact, args.run, args.job)]
    receipt, root, raw = verify(args.archive, *metadata, args.repo, args.reviewed_mandor_root.read_bytes(), from_cli(args))
    with args.receipt.open('x') as stream:
        stream.write(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    if root is not None:
        with args.catalogue_output.open('xb') as stream:
            stream.write(raw)
        with args.root.open('x') as stream:
            stream.write(json.dumps(root, indent=2) + '\n')
    print(json.dumps({k: receipt[k] for k in ('status', 'conclusion', 'actual_case_credit',
                                             'actual_outer_restore', 'actual_worker_reaped', 'first_reported_error')}))


if __name__ == '__main__':
    main()
