"""Exact failed58c8: retain both attempts and all raw boundaries, no27 credit."""
from pathlib import Path
import argparse
import json
import zipfile

from intake_common import GitBytes, fields, exact, pin, require
from intake_sku27 import group, literal, raw_evidence, strict, MAIN, NATIVE, COST, PACKAGE, CASE, NS

HEAD = '58c8e1535c6b5296f07ca41d5eb90cb28ed2872c'
TREE = '500e0326b140e7e5d7a59b3824a2243334937ed3'
ARCHIVE = dict(bytes=81653650, sha256='dc5c8221b77ecb241e1b5661c124b9c9a577b03254687bdeb471478ad998dcef')


def main():
    parser = argparse.ArgumentParser()
    for name in ('source', 'archive', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    git = GitBytes(args.source, HEAD, TREE)
    exact(pin(args.archive.read_bytes()), ARCHIVE, 'EXACT_58C8_ARCHIVE')
    with zipfile.ZipFile(args.archive) as z:
        require(len(z.namelist()) == len(set(z.namelist())) == 152 and z.testzip() is None, 'EXACT_58C8_CRC_MEMBERS')
        names = (MAIN, NATIVE, COST, PACKAGE, 'T3_BACKUP_RESTORE_DRILL.json')
        docs = {name: strict(z.read(name)) for name in names}
        main = docs[MAIN]
        fields(main, dict(qualification_commit=HEAD, status='INCOMPLETE', required_case_ids=[CASE],
            required_case_ids_pass=False, baseline_full22_all_rows_all_sequences_equal=True,
            restore_raw_public_equal=True, cp6_restored=True, baseline_advisors_equal=True,
            advisor_gate=True, production_go=False, independent_acceptance=False), 'FAILED_58C8_OUTER')
        exact(set(main['committed']), {CASE}, 'ONE_COMBINED_CASE')
        part = main['committed'][CASE]
        native_ids = list(literal(git, 'scripts/current-sku-pair-conversion-qualification/cases.py', 'IDS'))
        cost_ids = list(literal(git, 'scripts/current-sku-group-cost-qualification/cases.py', 'IDS')) + list(literal(git, NS+'recovery_cases.py', 'IDS'))
        callback_ids = list(literal(git, 'scripts/current-sku-pair-conversion-qualification/races.py', 'IDS')) + list(literal(git, 'scripts/current-sku-pair-conversion-qualification/auth_waits.py', 'IDS')) + list(literal(git, NS+'recovery_sessions.py', 'IDS'))
        exact(part['fresh_base_native7']['native'], docs[NATIVE], 'SAME_RUN_RAW_NATIVE7')
        exact(part['fresh_cost_native5']['native'], docs[COST], 'SAME_RUN_RAW_COST5')
        group(docs[NATIVE], native_ids); group(docs[COST], cost_ids)
        callbacks = part['fresh_callbacks11']
        fields(callbacks, dict(status='INCOMPLETE'), 'CALLER_REFUSED_DUPLICATE_COPY_COUNT')
        require('fresh_real_Auth_browser4' not in part, 'BROWSER_NOT_STARTED')
        require(len(callbacks['copy_catalog_admissions']) == 22, 'EXACT_TWO_ELEVEN_COPY_ATTEMPTS')
        second = callbacks['concurrency']; first = second['business_day_first_attempt']
        fields(first, dict(status='INCOMPLETE', counts={'PASS': 2, 'INCOMPLETE': 9}, database_remaining=0), 'FIRST_ATTEMPT')
        fields(second, dict(status='RUN_COMPLETE', counts={'PASS': 11}, business_day_retried=True, database_remaining=0), 'SECOND_ATTEMPT_NOT_COMPLETE27')
        for attempt in (first, second):
            exact(set(attempt['races']), set(callback_ids), 'EXACT_ELEVEN_IDS_EACH_ATTEMPT')
            for case in attempt['races'].values():
                fields(case, dict(session_leaks=[]), 'NO_CALLBACK_SESSION_LEAK')
                if case['status'] != 'PASS':
                    fields(case, dict(status='INCOMPLETE', status_before_rollover='PASS',
                        business_day_rollover=True, error='AUDITOR_BUSINESS_DAY_ROLLOVER'), 'FIRST_ROLLOVER_STAYS_FAILED')
                fields(case['installed_baseline_restoration'], dict(all22_all_rows_all_sequences_roles_exact=True,
                    complete_database_dump_restored=True, cp6_restored=True, advisors_equal=True,
                    selected_table_cleanup=False), 'EACH_COPY_COMPLETE_RESTORE')
        exact(docs[PACKAGE]['gate'], dict(installed=True, primary_unchanged=True,
            backup_restore_drill=True, security_advisors=True, writer_runtime=False), 'FAILED_FIFTH_GATE')
        fields(docs[PACKAGE]['run_identity'], dict(tool_head=HEAD, github_sha=HEAD,
            run_id='41086555559', run_attempt='1'), 'EXACT_RUN')
        require('current-sku-pair-concurrency-qualification/runner.py' in main['traceback'] and
                'AssertionError' in main['traceback'], 'ACTUAL_CALLER_FAILURE')
        raw = raw_evidence(z, part, expected_noeffect=20)
        receipt = dict(status='EXACT_58C8_TWO_ATTEMPTS_FAILURE_AND_RAW_BOUNDARIES_VERIFIED',
            head=HEAD, tree=TREE, run_id=41086555559, job_id=124169121755, artifact_id=12997219671,
            archive=ARCHIVE, crc_members=152, originals={name: pin(z.read(name)) for name in names},
            raw_evidence=raw, Native7=True, cost5=True, first_attempt_counts=first['counts'],
            second_attempt_counts=second['counts'], admitted_and_restored_copies=22,
            browser_started=False, complete27_qualified=False, package_gates=docs[PACKAGE]['gate'],
            outer_restore_receipts=True, outer_raw_before_after_not_serialized=True,
            first_failure=main['traceback'], prior_partial_results_aggregated=False,
            production_go=False, independent_acceptance=False)
    args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(dict(status=receipt['status'], raw_noeffect_censuses=20,
        cost_sequence_prefixes=5, complete27_qualified=False)))


if __name__ == '__main__':
    main()
