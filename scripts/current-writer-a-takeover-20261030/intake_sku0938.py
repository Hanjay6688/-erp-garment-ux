"""Retain exact failed0938 and its raw no-effect evidence; never qualify27."""
from pathlib import Path
import argparse
import json
import zipfile

from intake_common import GitBytes, fields, exact, pin, require
from intake_sku27 import group, literal, raw_evidence, strict, MAIN, NATIVE, COST, PACKAGE, CASE, NS

HEAD = '0938b693dee868ba74323f4ff61db70efdd11e89'
TREE = '0e0ebd209fbea1b63c9283c02ffb4ce6cfb1e87f'
ARCHIVE = dict(bytes=73310874, sha256='b8f58b099ad12ff208e05dfaec8dc38472886e8a946b80033b8fd5b8d2d65dc1')


def main():
    parser = argparse.ArgumentParser()
    for name in ('source', 'archive', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    git = GitBytes(args.source, HEAD, TREE)
    exact(pin(args.archive.read_bytes()), ARCHIVE, 'EXACT_0938_ARCHIVE')
    with zipfile.ZipFile(args.archive) as z:
        require(len(z.namelist()) == 171 and len(set(z.namelist())) == 171 and z.testzip() is None, 'EXACT_0938_CRC_MEMBERS')
        names = (MAIN, NATIVE, COST, PACKAGE, 'T3_BACKUP_RESTORE_DRILL.json')
        docs = {name: strict(z.read(name)) for name in names}
        main = docs[MAIN]
        fields(main, dict(qualification_commit=HEAD, status='INCOMPLETE', required_case_ids=[CASE],
            required_case_ids_pass=False, baseline_full22_all_rows_all_sequences_equal=True,
            restore_raw_public_equal=True, cp6_restored=True, baseline_advisors_equal=True,
            advisor_gate=True, production_go=False, independent_acceptance=False), 'FAILED_0938_OUTER')
        exact(set(main['committed']), {CASE}, 'ONE_COMBINED_CASE')
        part = main['committed'][CASE]
        native_ids = list(literal(git, 'scripts/current-sku-pair-conversion-qualification/cases.py', 'IDS'))
        cost_ids = list(literal(git, 'scripts/current-sku-group-cost-qualification/cases.py', 'IDS')) + list(literal(git, NS+'recovery_cases.py', 'IDS'))
        exact(part['fresh_base_native7']['native'], docs[NATIVE], 'SAME_RUN_RAW_NATIVE7')
        exact(part['fresh_cost_native5']['native'], docs[COST], 'SAME_RUN_RAW_COST5')
        group(docs[NATIVE], native_ids); group(docs[COST], cost_ids)
        callbacks = part['fresh_callbacks11']
        fields(callbacks, dict(status='PASS', full_installed_copy_restores=11), 'CALLBACKS11')
        exact(callbacks['concurrency']['counts'], {'PASS': 11}, 'EXACT_CALLBACK_COUNTS')
        for case in callbacks['concurrency']['races'].values():
            fields(case, dict(status='PASS', session_leaks=[]), 'CALLBACK_PASS')
            fields(case['installed_baseline_restoration'], dict(all22_all_rows_all_sequences_roles_exact=True,
                complete_database_dump_restored=True, cp6_restored=True, advisors_equal=True,
                selected_table_cleanup=False), 'COPY_COMPLETE_RESTORE')
        browser = part['fresh_real_Auth_browser4']['browser']
        fields(browser, dict(status='INCOMPLETE', counts={'INCOMPLETE': 4}, real_auth=True,
            jwt_signed_by_runtime=False, host_status='RUN_COMPLETE', users_created=4,
            auth_cleanup_failures=[], session_leaks=[], cleanup_failures=False, database_remaining=0,
            auth_counts=dict(before=[0, 0, 0, 0], after=[0, 0, 0, 0], restored=True)), 'FAILED_BROWSER_CLEANUP')
        needles = ('Expected: enabled', 'Batalkan CP6-E-S29-', 'CP7_FRESH_ACCESS_REQUIRED', 'CP7_FRESH_ACCESS_REQUIRED')
        require(len(browser['cases']) == 4, 'BROWSER_EXACT4')
        for case, needle in zip(browser['cases'].values(), needles):
            fields(case, dict(status='INCOMPLETE'), 'BROWSER_NOT_PASS')
            require(needle in case['error'], 'CAPTURED_FIRST_FAILURE')
        exact(docs[PACKAGE]['gate'], dict(installed=True, primary_unchanged=True,
            backup_restore_drill=True, security_advisors=True, writer_runtime=False), 'FAILED_FIFTH_GATE')
        fields(docs[PACKAGE]['run_identity'], dict(tool_head=HEAD, github_sha=HEAD,
            run_id='41070902168', run_attempt='1'), 'EXACT_RUN')
        raw = raw_evidence(z, part)
        receipt = dict(status='EXACT_0938_FIRST_FAILURE_AND_RAW_BOUNDARIES_VERIFIED', head=HEAD, tree=TREE,
            run_id=41070902168, job_id=124114405860, artifact_id=12989469942, archive=ARCHIVE, crc_members=171,
            originals={name: pin(z.read(name)) for name in names}, raw_evidence=raw,
            same_run_observed_counts=dict(PASS=23, INCOMPLETE=4), complete27_qualified=False,
            first_errors={name: value['error'] for name, value in browser['cases'].items()},
            package_gates=docs[PACKAGE]['gate'], outer_restore_receipts=True,
            outer_raw_before_after_not_serialized=True, prior_partial_results_aggregated=False,
            production_go=False, independent_acceptance=False)
    args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(dict(status=receipt['status'], raw_noeffect_censuses=14, cost_sequence_prefixes=5, complete27_qualified=False)))


if __name__ == '__main__':
    main()
