"""Read the exact root-admitted SKU Original before any ERP runtime import.

The checked-in prerequisite is deliberately pending. Only intake of the
terminal current run may supply its archive, receipt and Original byte pins.
This reader cannot turn source checks or earlier partial runs into SKU27.
"""
from hashlib import sha256
from pathlib import Path
import json
import math
import os
import zipfile

HERE = Path(__file__).resolve().parent
HEAD = 'e9256772579f387df77dde949f8ea619cbd86856'
TREE = '8de422523afa42c20d85e830749ed232b7edc6b9'
RUN = 41109346033
CASE = 'SKU_NATIVE7_COST5_RACES3_PERMISSION_WAITS7_RECOVERY_BUSY1_AUTH_BROWSER4'
MAIN = 'CP7_SKU_MANAGED_RECOVERY_NATIVE27.json'
NATIVE = 'CP7_SKU_PAIR_CONVERSION_NATIVE7.json'
COST = 'CP7_SKU_GROUP_COST_NATIVE5.json'
PACKAGE = 'T3_PACKAGE_INSTALL.json'
RESTORE = 'T3_BACKUP_RESTORE_DRILL.json'
GATES = dict(installed=True, primary_unchanged=True, backup_restore_drill=True, security_advisors=True, writer_runtime=True)


def strict(raw):
    def pairs(rows):
        out = {}
        for key, value in rows:
            if key in out: raise ValueError('S05_DUPLICATE_ORIGINAL_KEY: '+key)
            out[key] = value
        return out
    def invalid(value): raise ValueError('S05_NONFINITE_ORIGINAL: '+value)
    def number(value):
        result = float(value)
        if not math.isfinite(result): invalid(value)
        return result
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid, parse_float=number)


def pinned(raw, expected):
    if expected != dict(bytes=len(raw), sha256=sha256(raw).hexdigest()):
        raise ValueError('S05_EXACT_ROOT_ADMITTED_ORIGINAL_BYTES_REQUIRED')
    return strict(raw)


def specification():
    value = strict((HERE/'SKU27_PREREQUISITE.json').read_bytes())
    if value['head'] != HEAD or value['tree'] != TREE or value['run_id'] != RUN:
        raise ValueError('S05_ONLY_CURRENT_SKU27_RUN_MAY_QUALIFY_PARENT')
    return value


def admitted():
    spec = specification()
    if (spec['status'] != 'ROOT_VERIFIED_CURRENT_SKU27_ALL5'
            or spec['complete27_qualified'] is not True or spec['package_all_five'] is not True):
        raise ValueError('S05_WAIT_FOR_ACTUAL_ROOT_INTAKE_OF_CURRENT_SKU27_AND_ALL5')
    receipt = pinned(Path(os.environ['S05_SKU27_ROOT_INTAKE']).read_bytes(), spec['root_intake_receipt'])
    if any(receipt.get(key) != value for key, value in dict(head=HEAD, tree=TREE, run_id=RUN,
            complete27_qualified=True, package_all_five=True, prior_runs_aggregated=False).items()):
        raise ValueError('S05_ROOT_INTAKE_COMPLETE_SINGLE_CURRENT_RUN_REQUIRED')
    path = Path(os.environ['S05_SKU27_ORIGINAL'])
    raw = path.read_bytes()
    if dict(bytes=len(raw), sha256=sha256(raw).hexdigest()) != spec['archive']:
        raise ValueError('S05_EXACT_TERMINAL_SKU27_ARCHIVE_REQUIRED')
    del raw
    with zipfile.ZipFile(path) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError('S05_DUPLICATE_ARCHIVE_MEMBER')
        docs = {name: pinned(archive.read(name), spec['originals'][name]) for name in (MAIN, NATIVE, COST, PACKAGE, RESTORE)}
    main = docs[MAIN]
    if (main.get('status') != 'PASS' or main.get('qualification_commit') != HEAD
            or main.get('required_case_ids') != [CASE] or main.get('required_case_ids_pass') is not True
            or set(main.get('committed', {})) != {CASE}):
        raise ValueError('S05_COMPLETE_ACTUAL_SKU27_OUTER_REQUIRED')
    part = main['committed'][CASE]
    if part.get('status') != 'PASS' or part.get('business_counts') != {'PASS': 27}:
        raise ValueError('S05_COMPLETE_SINGLE_RUN27_REQUIRED')
    for label, name, count in [('fresh_base_native7', NATIVE, 7), ('fresh_cost_native5', COST, 5)]:
        actual = part[label]['native']
        if actual != docs[name] or actual.get('status') != 'PASS' or actual.get('counts') != {'PASS': count}:
            raise ValueError('S05_SAME_RUN_NATIVE_ORIGINALS_REQUIRED')
    callbacks, browser = part['fresh_callbacks11']['concurrency'], part['fresh_real_Auth_browser4']['browser']
    for group, key, count in [(callbacks, 'races', 11), (browser, 'cases', 4)]:
        if (group.get('status') != 'RUN_COMPLETE' or group.get('counts') != {'PASS': count}
                or len(group.get(key, {})) != count or any(r.get('status') != 'PASS' for r in group[key].values())
                or group.get('database_remaining') != 0 or group.get('business_day_retried')
                or group.get('business_day_first_attempt')):
            raise ValueError('S05_ALL_CURRENT_CALLBACKS_AND_BROWSER_ONE_ATTEMPT_REQUIRED')
    if (browser.get('real_auth') is not True or browser.get('jwt_signed_by_runtime') is not False
            or browser.get('auth_counts', {}).get('restored') is not True or browser.get('auth_cleanup_failures') != []
            or browser.get('session_leaks') or browser.get('cleanup_failures') or browser.get('console_errors') != 0
            or browser.get('host_exit') != 0 or browser.get('host_status') != 'RUN_COMPLETE'):
        raise ValueError('S05_SKU_AUTH_AND_BROWSER_CLEANUP_REQUIRED')
    if any(main.get(key) is not True for key in ('baseline_full22_all_rows_all_sequences_equal',
            'restore_raw_public_equal', 'cp6_restored', 'baseline_advisors_equal', 'advisor_gate', 'used_guard_refused_before_DDL')):
        raise ValueError('S05_SKU_COMPLETE_OUTER_RESTORE_REQUIRED')
    package = docs[PACKAGE]
    if (package.get('gate') != GATES or package['run_identity']['tool_head'] != HEAD
            or package['run_identity']['github_sha'] != HEAD or package['run_identity']['run_id'] != str(RUN)
            or package['run_identity']['run_attempt'] != '1' or docs[RESTORE].get('status') != 'RESTORED_IDENTICAL'):
        raise ValueError('S05_CURRENT_SKU_ALL5_PACKAGE_AND_BACKUP_REQUIRED')
    return dict(status='EXACT_ROOT_VERIFIED_CURRENT_SKU27_ORIGINAL_ADMITTED', head=HEAD, tree=TREE, run_id=RUN,
        archive=spec['archive'], root_intake_receipt=spec['root_intake_receipt'], originals=spec['originals'],
        current_installation=main['source_declaration']['current_installation'], retained_case_credit=27,
        fresh_case_credit=0, prior_runs_aggregated=False, production_go=False, independent_acceptance=False)
