"""Offline retained-parent admission. No DB, Auth, runner or network creation."""
from pathlib import Path
import gzip,hashlib,json

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
RETAINED=ROOT/'docs/cp7/d17-14/ow08/vendor-combined41c-pass'
HEAD='41caaaed02c0d89b122ecf1ff221f6647141c335'
WIRE_SHA='931e62848f6861e24190e76cb0efbd8aa032cb514bf0f0b5af362d62cbe12bbd'
OWN_FILES=tuple('scripts/cp7_attendance_period_choice/'+name for name in(
 'choice.sql','native_delta.py','catalog_contract.py','NEW_CATALOG_IDENTITIES.json','composition.py',
 'WIRE_CONTRACT.md','SOURCE_DERIVED_NATIVE_ABI.json','local.test.ts','local_fixture.sql','local_catalog.py','render_local.py','test_source.py'))+tuple(
 'scripts/current-attendance-period-choice-qualification/'+name for name in('admission.py','fixtures.py','cases.py','test_plan.py'))
COUNTS=dict(existing_native=12,existing_private_facade=1,captured_originals=13,private_native_clones=2,
 prepared_native=11,actual_s03_native=0,actual_s03_real_Auth=0,actual_s03_browser=0)
NATIVE_IDS=(
 'S03_NATIVE_OWNER_FIELDS_READ_FULL_NO_EFFECT',
 'S03_NATIVE_EXPENSE_APPROVAL_ONCE_PAID_E05_REOPEN',
 'S03_NATIVE_TWO_EXACT_PERIODS_CENTS_AND_NATIVE_HPP',
 'S03_NATIVE_P2_PAYROLL_POOL_COEXIST_AND_POLICY_FENCES',
 'S03_NATIVE_OWNING_CANCEL_LATE_OUTPUT_AND_RESTORATION_FLOOR',
 'S03_NATIVE_BOTH_CORRECTIONS_LINKED_INVERSES_NO_RECOGNITION',
 'S03_NATIVE_STALE_REVIEW_UUID_RECOVERY_AND_APPEND_ONLY',
 'S03_NATIVE_CLOSED_SOURCE_OPEN_OUTPUT_AND_CLOSED_CORRECTION',
 'S03_NATIVE_ZERO_OUTPUT_SUCCESSOR_POLICY_RETAINS_OLD_INFO',
 'S03_NATIVE_FINISHED_PO_FG_COGS_COST_AND_CANCEL_EXACT',
 'S03_NATIVE_OLD_ACCRUAL_LATER_BOOK_REOPEN_DATE_FLOOR',
)
PINS={
 'CP7_VENDOR_RECEIVABLE_COMBINED11.json':(3485711,'04e00f42862ddfec8346d41d4d6a2d6a285f041127cccf09d973ca929b307ea0','91bab345d1b41ca7fa8f57fab97a407377a2588b0d7298f57bb47ee01d3daade'),
 'T3_PACKAGE_INSTALL.json':(360420,'48fc54072b4f3122d89f6a45faa93f0e8ebd05ecfde0b9370def8202755e0f43','9c651a5d5a38370a2f5f19f30543821ab8333eb267936b34681e9a27784bc2cb'),
 'T3_BACKUP_RESTORE_DRILL.json':(1470,'c81b67bf21c5b6d5a32107d6fdfb861024b98c276b825f9f2b626d36f07307dd','430e1a3396f479a756d457495dbf8aa7819a99b2ca49a3908391becfb64cc9ce'),
 'T3_PACKAGE_FILES_INSTALL.json':(1806,'14007d43dd9b8e1acfa2b91e35d59047f553b248e2fc06e8362e8ad813003ba7','a1c8a1ca1ae654997ead274c2d51fa04a6b55916b9b23f4339741c81760083e7'),
}

def admit_prepared_sources(root=ROOT,manifest_path=HERE/'SOURCE.json'):
    """Exact own reviewed files only; never normalize a changed source graph."""
    manifest=json.loads(Path(manifest_path).read_bytes())
    if(manifest.get('version')!='cp7.s03.prepared-native11.v1'
       or manifest.get('status')!='PREPARED'
       or 'accepted_current_S03_Native_original'not in manifest
       or manifest['accepted_current_S03_Native_original']is not None
       or manifest.get('independent_acceptance')is not False
       or manifest.get('production_go')is not False):raise ValueError('S03_PREPARED_CLAIMS_REQUIRED')
    counts=manifest.get('counts',{})
    if counts!=COUNTS or any(type(v)is not int for v in counts.values()):raise ValueError('S03_PREPARED_EXACT_COUNTS_REQUIRED')
    if tuple(manifest.get('Native_case_ids',()))!=NATIVE_IDS:raise ValueError('S03_PREPARED_EXACT_NATIVE11_IDS_REQUIRED')
    files=manifest.get('files',{})
    if set(files)!=set(OWN_FILES):raise ValueError('S03_PREPARED_EXACT_FILES_REQUIRED')
    for name in OWN_FILES:
        if hashlib.sha256((Path(root)/name).read_bytes()).hexdigest()!=files[name]:raise ValueError('S03_PREPARED_SOURCE_CHANGED:'+name)
    wire='scripts/cp7_attendance_period_choice/WIRE_CONTRACT.md'
    if files[wire]!=WIRE_SHA or manifest.get('wire_base')!='7e91ec5e6':raise ValueError('S03_PREPARED_WIRE_CHANGED')
    if(manifest.get('runtime_parent_commit')!=HEAD
       or manifest.get('retained_parent_original_sha256')!=PINS['CP7_VENDOR_RECEIVABLE_COMBINED11.json'][1]):raise ValueError('S03_PREPARED_PARENT_CHANGED')
    return manifest

def read_original(name,retained=RETAINED):
    size,raw_sha,gzip_sha=PINS[name];compressed=(retained/(name+'.gz')).read_bytes()
    if hashlib.sha256(compressed).hexdigest()!=gzip_sha:raise ValueError('S03_PARENT_GZIP_CHANGED:'+name)
    raw=gzip.decompress(compressed)
    if len(raw)!=size or hashlib.sha256(raw).hexdigest()!=raw_sha:raise ValueError('S03_PARENT_RAW_CHANGED:'+name)
    return json.loads(raw)

def admit_documents(original,package,current_parent_sources):
    if(original['qualification_commit']!=HEAD or original['status']!='PASS'
       or original['actual_Native_cases']!=7 or original['actual_two_session_races']!=3
       or original['actual_Auth_HTTP_cases']!=1 or original['actual_browser_cases']!=0):raise ValueError('S03_PARENT_EXACT_7_3_1_REQUIRED')
    if any(type(original[key])is not int for key in('actual_Native_cases','actual_two_session_races','actual_Auth_HTTP_cases','actual_browser_cases')):raise ValueError('S03_PARENT_EXACT_INTEGER_COUNTS_REQUIRED')
    for field in('cp6_restored','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal','advisor_gate','used_guard_refused_before_DDL','required_case_ids_pass'):
        if original[field]is not True:raise ValueError('S03_PARENT_GATE_REQUIRED:'+field)
    group=original['committed']['VENDOR_RECEIVABLE_NATIVE7_RACES3_AUTH1']
    native=group['fresh_native7']['native']['cases']
    expected=original['source_declaration']['qualification']['Native_case_ids']
    if len(expected)!=7 or set(native)!=set(expected)or any(r['status']!='PASS'for r in native.values()):raise ValueError('S03_PARENT_EXACT_NATIVE7_IDS_REQUIRED')
    # The exact frozen package's status vocabulary is ALL_STAGES_INSTALLED;
    # all five mandatory boolean gates remain required (no truthy coercion).
    gates=('installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime')
    if(package['status']!='ALL_STAGES_INSTALLED'or set(package['gate'])!=set(gates)
       or any(package['gate'][key]is not True for key in gates)):raise ValueError('S03_PARENT_PACKAGE5_REQUIRED')
    canonical=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)
    if canonical(current_parent_sources)!=canonical(original['source_declaration']['current_installation']):raise ValueError('S03_PARENT_RUNTIME_SOURCE_CHANGED')
    return dict(status='RETAINED_VENDOR41C_ADMITTED',backend_commit=HEAD,
        original_sha256=PINS['CP7_VENDOR_RECEIVABLE_COMBINED11.json'][1],
        historical_native=7,historical_races=3,historical_real_Auth_HTTP=1,historical_browser=0,
        S03_new_qualification_credit=0,production_go=False,independent_acceptance=False)

def admit(current_parent_sources):
    prepared=admit_prepared_sources()
    docs={name:read_original(name)for name in PINS}
    result=admit_documents(docs['CP7_VENDOR_RECEIVABLE_COMBINED11.json'],docs['T3_PACKAGE_INSTALL.json'],current_parent_sources)
    result['prepared_S03_sources']=prepared
    return result

if __name__=='__main__':
    import sys
    sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'scripts'))
    from cp7_attendance_period_choice import composition
    print(json.dumps(admit(composition.predecessor.sources()),indent=2))
