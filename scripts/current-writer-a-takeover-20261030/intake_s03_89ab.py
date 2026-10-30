"""Read exact89ab failed Originals; explicitly retain incomplete Auth restoration."""
from pathlib import Path
import argparse
import gzip
import json
import zipfile

from intake_common import GitBytes, fields, exact, pin, require, json_bytes

HEAD = '89ab76595424fa55cda3923fbe4499b7b7abf16b'
TREE = 'db63154b4beda614863b665970e0ea0c14d3c754'
ARCHIVE = dict(bytes=325434628, sha256='72885264769d57c0bd0970410808dc4a26429b07a8c970d8e39eec9623703452')
MAIN = 'CP7_S03_MOUNTED_FULL_APP_BROWSER4.json'
CASE = 'S03_MOUNTED_FULL_APP_AUTH_BROWSER4'
NS = 'scripts/current-attendance-choice-browser4-lawful-successor/'


def main():
    parser = argparse.ArgumentParser()
    for name in ('source', 'archive', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    git = GitBytes(args.source, HEAD, TREE)
    exact(pin(args.archive.read_bytes()), ARCHIVE, 'EXACT_89AB_ARCHIVE')
    with zipfile.ZipFile(args.archive) as z:
        require(len(z.namelist()) == len(set(z.namelist())) == 180 and z.testzip() is None, 'EXACT_89AB_CRC_MEMBERS')
        names = [MAIN, 'T3_PACKAGE_INSTALL.json', 'S03_BROWSER4_FINAL_GATE.json']
        docs = {name: json_bytes(z.read(name)) for name in names}
        report, package, gate = (docs[name] for name in names)
        fields(report, dict(status='INCOMPLETE', qualification_commit=HEAD,
            required_case_ids=[CASE], required_case_ids_pass=False,
            baseline_full22_all_rows_all_sequences_equal=True, restore_raw_public_equal=True,
            cp6_restored=True, baseline_advisors_equal=True, advisor_gate=True,
            production_go=False, independent_acceptance=False), 'FAILED_89AB_CLONE_RESTORE_RECEIPTS')
        exact(set(report['committed']), {CASE}, 'S03_ONE_COMPONENT')
        component = report['committed'][CASE]; browser = component['browser']
        fields(browser, dict(status='INCOMPLETE', host_exit=1, host_status='INCOMPLETE',
            error='AUDITOR_BROWSER_HOST_INCOMPLETE', users_created=None,
            cleanup_failures=True, session_leaks=[], database_remaining=0,
            auth_counts={'before': [0, 0, 0, 0], 'after': [2, 2, 4, 4], 'restored': False}),
            'ACTUAL_FAILED_PRIMARY_AUTH_CLEANUP')
        ids = browser['planned_case_ids']; require(len(ids) == len(set(ids)) == 4, 'EXACT_BROWSER4_PLAN')
        exact(list(browser['cases']), ids[:2], 'ONLY_TWO_CASES_REACHED')
        fields(browser['cases'][ids[0]], dict(status='PASS', actual_normal_App_real_Auth_public_RPC=True), 'DESKTOP_OBSERVED_PASS')
        fields(browser['cases'][ids[1]], dict(status='INCOMPLETE', error='AUDITOR_BROWSER_CASE_TIMEOUT',
            timeout_ms=2700000, business_day_rollover=True), 'MOBILE_TIMEOUT_STAYS_FAILED')
        fields(package, dict(auth_users_before=0, auth_users_after=2, primary_unchanged=False), 'PRIMARY_NOT_RESTORED')
        exact(package['gate'], dict(installed=True, primary_unchanged=False, backup_restore_drill=True,
            security_advisors=True, writer_runtime=False), 'EXACT_THREE_OF_FIVE_GATES')
        fields(package['run_identity'], dict(tool_head=HEAD, github_sha=HEAD,
            run_id='41080255432', run_attempt='1'), 'EXACT_RUN')
        fields(gate, dict(status='INCOMPLETE', qualified_actual_browser_cases=0,
            error='S03_BROWSER4_ACTUAL_OUTER_PASS_REQUIRED'), 'GATE_REFUSES_ACCEPTANCE')
        host_receipts = component['actual_browser_host_originals']
        require(len(host_receipts) == 1, 'ONE_HOST_ORIGINAL')
        host_pin = host_receipts[0]; packed = z.read(host_pin['name']); raw = gzip.decompress(packed)
        exact(pin(packed), dict(bytes=host_pin['gzip_bytes'], sha256=host_pin['gzip_sha256']), 'HOST_GZIP_PIN')
        exact(pin(raw), dict(bytes=host_pin['raw_bytes'], sha256=host_pin['raw_sha256']), 'HOST_RAW_PIN')
        host = json_bytes(raw); exact(host['cases'], browser['cases'], 'OUTER_EMBEDS_EXACT_HOST_CASES')
        fields(host, dict(status='INCOMPLETE', stage='CASES', planned=ids, real_auth=True,
            product_responses_mocked=False), 'HOST_STOPPED_BEFORE_CLEANUP_FINISH')
        require('users_created' not in host and 'missing' not in host, 'HOST_FINAL_SAVE_NOT_REACHED')
        names.append(host_pin['name'])
        snapshots = sorted((i for i in z.infolist() if i.filename.startswith('S03_B4_MOBILE390_')
                            and i.filename.endswith('_FULL_STATE.json.gz')), key=lambda i: i.filename)
        require(len(snapshots) == 31 and '_031_BEFORE_POOL_READ_' in snapshots[-1].filename,
                'EXACT_LAST_MOBILE_OBSERVATION')
        source = git.read(NS + 'cases.mjs')
        exact(pin(source)['sha256'], browser['script_sha256'], 'EXECUTED_EXACT_PUBLIC_CALLBACK_SOURCE')
        receipt = dict(status='EXACT_89AB_FAILED_ORIGINALS_AND_INCOMPLETE_PRIMARY_RESTORE_VERIFIED',
            head=HEAD, tree=TREE, run_id=41080255432, job_id=124147137480, artifact_id=12995817396,
            archive=ARCHIVE, crc_members=180, originals={name: pin(z.read(name)) for name in names},
            observed_browser_counts={'PASS': 1, 'INCOMPLETE': 1, 'NOT_REACHED': 2},
            actual_case_qualification_credit=0, browser4_qualified=False,
            clone_full_restore_source_bound_receipts=True, outer_raw_before_after_not_serialized=True,
            primary_Auth_restored=False, Auth_counts=browser['auth_counts'], package_gates=package['gate'],
            mobile_snapshot_count=31, last_snapshot=snapshots[-1].filename,
            whole_mobile_case_not_complete=True, production_go=False, independent_acceptance=False)
    args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(dict(status=receipt['status'], browser4_qualified=False, primary_Auth_restored=False)))


if __name__ == '__main__':
    main()
