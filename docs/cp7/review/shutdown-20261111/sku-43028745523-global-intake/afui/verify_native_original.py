"""Verify one retained Afui Native Original; never qualify the owning package.

The caller obtains artifact metadata from the canonical connected GitHub API.
This local reader checks those supplied pins, complete bytes and the exact
current pure boundary verifier. It makes no network requests or DB calls.
"""
from hashlib import file_digest, sha256
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path, PurePosixPath
from types import CodeType, FunctionType
import argparse
import ast
import importlib.util
import json
import re
import stat
import subprocess
import zipfile

SOURCE_TREE = 'ef194e421402ae1e45625e2d57f58c848ef9e08f'
GROUP = 'CP7_AFUI_GOOD_NONPAYABLE_FULL15_NATIVE9'
ORDINARY = {
    'NONPAYABLE_NATIVE_POSITIVE_HPP_ZERO_REIMBURSEMENT_FROZEN_HISTORY_AND_REPLAY': True,
    'NONPAYABLE_NATIVE_EXPLICIT_NORMAL_POLICY_REIMBURSEMENT_REGRESSION': False,
    'NONPAYABLE_NATIVE_NORMAL_PICKUP_SPECIAL_GOOD_PHYSICAL_DATE': True,
    'NONPAYABLE_NATIVE_SPECIAL_PICKUP_NORMAL_GOOD_PHYSICAL_DATE': False,
}


def require(value, message):
    if not value:
        raise ValueError(message)


def strict(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('NONFINITE_JSON_NUMBER:' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def source(repo, relative):
    path = repo / relative
    require(path.is_file() and not any(part.is_symlink() for part in (path, *path.parents)), 'REGULAR_PINNED_SOURCE_REQUIRED')
    raw = path.read_bytes()
    expected = subprocess.check_output(['git', '-C', str(repo), 'show', SOURCE_TREE + ':' + relative])
    require(raw == expected, 'EXACT_FROZEN_VERIFIER_SOURCE_REQUIRED:' + relative)
    return raw


def native_ids(repo):
    result = []
    for name, field in (('native_cases.py', 'FIRST_IDS'), ('native_inverse_cases.py', 'IDS'), ('native_sales_cases.py', 'IDS')):
        tree = ast.parse(source(repo, 'scripts/cp7_accessory_nonpayable/' + name))
        nodes = [node.value for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == field for target in node.targets)]
        require(len(nodes) == 1, 'ONE_PINNED_NATIVE_CASE_DECLARATION_REQUIRED')
        result.extend(ast.literal_eval(nodes[0]))
    require(len(result) == len(set(result)) == 9, 'EXACT_NINE_NATIVE_CASE_IDENTITIES_REQUIRED')
    return result


def ordinary_economics(repo, row):
    if row['case'] not in ORDINARY:
        return dict(rechecked_here=False, reason='Distinct case-specific lifecycle oracle remains in the complete Original')
    raw = source(repo, 'scripts/cp7_accessory_nonpayable/native_fixture.py')
    compiled = compile(raw, 'whole_pinned_native_fixture_compiler_context', 'exec', dont_inherit=True)
    codes = [code for code in compiled.co_consts if isinstance(code, CodeType) and code.co_name == 'require_economics']
    require(len(codes) == 1, 'ONE_ORIGINAL_PURE_ECONOMIC_ORACLE_REQUIRED')
    check = FunctionType(codes[0], dict(Decimal=Decimal, ROUND_HALF_UP=ROUND_HALF_UP), 'require_economics')
    nonpayable = ORDINARY[row['case']]
    require(row['physical_GOOD_date_basis'] is True and row['explicit_fresh_mandor_and_dated_policy'] is True
            and row['Native_fixture_constructor_code_unchanged'] is True, 'UNCHANGED_ACTUAL_NATIVE_DATE_CONSTRUCTOR_REQUIRED')
    values = [row['actual_initial'], row['actual_replay']]
    history = row.get('later_policy_history')
    if history is not None:
        require(history['exact_history_unchanged'] is True, 'POSTED_HISTORY_MUST_REMAIN_EXACT')
        values.append(history['after'])
    require(all(value == values[0] for value in values), 'REPLAY_AND_LATER_HISTORY_MUST_BE_IDENTICAL')
    for value in values:
        check(value, row['fixture'], nonpayable=nonpayable, hpp='20')
    first = values[0]
    require(len(first['entitlements']) == (0 if nonpayable else 1), 'EXACT_ENTITLEMENT_COUNT_REQUIRED')
    snapshot = first['snapshots'][0]['snapshot']
    return dict(rechecked_here=True, original_oracle_source=dict(bytes=len(raw), sha256=sha256(raw).hexdigest()),
                nonpayable_at_physical_GOOD=nonpayable, actual_HPP=str(snapshot['total_hpp_cost']),
                actual_reimbursement=str(snapshot['total_reimbursement']), entitlements=len(first['entitlements']),
                actual_journal=first['booked'], accessory_stock=str(first['accessory_stock']),
                replay_and_any_later_history_exact=True)


def verify(archive, metadata, repo, *, run, attempt, head, day):
    require(type(run) is int and run > 0 and attempt == 1 and re.fullmatch('[a-f0-9]{40}', head), 'EXACT_FIRST_OWNING_RUN_IDENTITY_REQUIRED')
    require(re.fullmatch(r'\d{4}-\d{2}-\d{2}', day), 'EXACT_REAL_PLANNED_BUSINESS_DAY_REQUIRED')
    require(archive.is_file() and not any(part.is_symlink() for part in (archive, *archive.parents)), 'REGULAR_ORIGINAL_ZIP_REQUIRED')
    require(metadata['workflow_run']['id'] == run and metadata['workflow_run']['head_sha'] == head
            and metadata['expired'] is False and type(metadata['id']) is int, 'EXACT_API_ARTIFACT_OWNING_RUN_AND_HEAD_REQUIRED')
    with archive.open('rb') as stream:
        archive_pin = dict(bytes=archive.stat().st_size, sha256=file_digest(stream, 'sha256').hexdigest())
    require(archive_pin['bytes'] == metadata['size_in_bytes']
            and 'sha256:' + archive_pin['sha256'] == metadata['digest'], 'EXACT_API_ARCHIVE_SIZE_AND_SHA_REQUIRED')
    with zipfile.ZipFile(archive) as z:
        entries = z.infolist()
        require(len(entries) == 2 and len({item.filename for item in entries}) == 2, 'ONE_COMPLETE_ORIGINAL_AND_MANIFEST_ONLY')
        for item in entries:
            name = PurePosixPath(item.filename)
            require(len(name.parts) == 1 and name.name not in ('.', '..') and not name.is_absolute()
                    and '\\' not in item.filename and not item.is_dir()
                    and not stat.S_ISLNK(item.external_attr >> 16), 'ZIP_PATH_OR_SYMLINK_REFUSED')
        require(z.testzip() is None, 'COMPLETE_ZIP_CRC_REQUIRED')
        manifest = strict(z.read('MANIFEST.json'))
        expected = dict(classification='INCOMPLETE_RUN_ORIGINAL_ONLY_NOT_ACCEPTANCE', qualification_commit=head,
                        github_run_id=str(run), github_run_attempt=str(attempt), actual_case_credit=0,
                        full_restore_verified=False, production_go=False)
        for key, value in expected.items():
            require(type(manifest.get(key)) is type(value) and manifest[key] == value, 'EXACT_FIRST_ATTEMPT_MANIFEST_REQUIRED:' + key)
        member = manifest['original_name']
        require(re.fullmatch('[a-f0-9]{64}\\.jsonl', member) and member in z.namelist(), 'COMPLETE_NATIVE_JSONL_ORIGINAL_REQUIRED')
        require(metadata['name'] == 'afui-original-' + str(run) + '-' + str(attempt) + '-' + member[:-6], 'EXACT_DURABLE_ARTIFACT_NAME_REQUIRED')
        with z.open(member) as stream:
            original_pin = dict(bytes=z.getinfo(member).file_size, sha256=file_digest(stream, 'sha256').hexdigest())
        require(manifest['original'] == original_pin, 'EXACT_COMPLETE_NATIVE_ORIGINAL_SIZE_AND_SHA_REQUIRED')
        row = strict(z.read(member))
    require(row['group'] == GROUP and row['case'] in native_ids(repo), 'EXACT_CURRENT_NATIVE_GROUP_AND_CASE_REQUIRED')
    require(member[:-6] == sha256((row['group'] + '\0' + row['case']).encode()).hexdigest(), 'EXACT_ORIGINAL_GROUP_CASE_FILENAME_REQUIRED')
    require(row['status'] == 'PASS', 'ORIGINAL_CASE_DID_NOT_PASS')
    for key, value in dict(full_boundary_restored=True, public_schema_unchanged=True,
                           new_financial_findings={}, full_outer_restore_and_all5_required=True,
                           actual_Auth_HTTP_credit=0, actual_browser_credit=0, actual_two_session_credit=0,
                           production_go=False, independent_acceptance=False).items():
        require(type(row.get(key)) is type(value) and row[key] == value, 'EXACT_NATIVE_CASE_RESULT_REQUIRED:' + key)
    require(row['business_day'] == dict(planned=day, before=day, after=day), 'ONE_REAL_BUSINESS_DAY_REQUIRED')
    require(row['session_leaks'] == dict(advisory_locks=0, advisory_lock_keys=[], other_sessions=[]), 'NO_NATIVE_SESSION_OR_LOCK_LEAK_REQUIRED')
    relative = 'scripts/cp7_accessory_nonpayable/case_boundary.py'
    verifier_raw = source(repo, relative)
    spec = importlib.util.spec_from_file_location('retained_Afui_pure_Native_boundary', repo / relative)
    validator = importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)
    boundary = row['actual_full22_case_boundary']
    proof = validator.validate(boundary, case_id=row['case'], result=row)
    require(boundary['verification'] == proof, 'COMPLETE_RAW_BOUNDARY_MUST_REPRODUCE_ITS_RECORDED_VERIFICATION')
    economics = ordinary_economics(repo, row)
    return dict(classification='ONE_NATIVE_PASS_ORIGINAL_VERIFIED_COMPLETE_OWNING_QUALIFICATION_STILL_REQUIRED',
                run_id=run, run_attempt=attempt, qualification_commit=head, artifact_id=metadata['id'],
                archive=archive_pin, complete_original=original_pin, complete_original_name=member,
                case=row['case'], group=row['group'], business_day=day, original_status=row['status'],
                complete_boundary_verification=proof, verifier_source=dict(tree=SOURCE_TREE, path=relative,
                    bytes=len(verifier_raw), sha256=sha256(verifier_raw).hexdigest()),
                archive_pin_matches_supplied_API_metadata=True, API_metadata_not_fetched_by_this_local_reader=True,
                full_run_15_all5_outer_restore_and_reaped_worker_verified=False,
                ordinary_economics=economics,
                verified_Native_originals=1, financial_acceptance_credit=0, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--api-metadata', type=Path, required=True)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--run', type=int, required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--day', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.archive, strict(args.api_metadata.read_bytes()), args.repo,
                    run=args.run, attempt=1, head=args.head, day=args.day)
    with args.output.open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))
