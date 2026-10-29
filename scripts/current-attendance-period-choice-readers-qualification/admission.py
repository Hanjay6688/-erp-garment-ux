"""Local/source/fresh11 admission only. No connection, DB, Auth or runner."""
from pathlib import Path
import ast
import hashlib
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OWN_FILES=('admission.py','cases.py','test_plan.py','README.md')
PRODUCT_FILES=tuple('scripts/cp7_attendance_period_choice/'+name for name in(
 'choice.sql','readers.sql','native_delta.py','catalog_contract.py','NEW_CATALOG_IDENTITIES.json','composition.py','installer_ddl.py',
 'SOURCE_DERIVED_NATIVE_ABI.json','WIRE_CONTRACT.md','READER_WIRE_CONTRACT.md','evidence/READER15_FROZEN13_SOURCE_BINDING.json'))+(
 'scripts/current-attendance-period-choice-qualification/cases.py',
 'scripts/current-attendance-period-choice-qualification/SOURCE.json')
FROZEN_ORIGINAL11_SHA='15fe990cccb82ff4c1dcd9ca40dc17fe93ac26a3a359a37361e6d8780b1f16e2'


def ids(path):
    for node in ast.parse(Path(path).read_text()).body:
        if isinstance(node,ast.Assign)and any(isinstance(target,ast.Name)and target.id=='IDS'for target in node.targets):
            return tuple(ast.literal_eval(node.value))
    raise ValueError('S03_READER_CASE_IDS_MISSING')


def sources(root=ROOT,path=HERE/'SOURCE.json'):
    data=json.loads(Path(path).read_bytes())
    if(data['version']!='cp7.s03.reader-native3-after-financial11.v1'or data['status']!='PREPARED'
       or data['production_go']is not False or data['independent_acceptance']is not False):raise ValueError('S03_READER_PREPARATION_REQUIRED')
    expected=dict(existing_captures=15,Native_functions=12,private_functions=3,Native_clones=2,
        original_financial_Native_cases=11,additional_reader_Native_cases=3,total_prepared_Native_cases=14,actual_Native_credit=0)
    if data['counts']!=expected or any(type(v)is not int for v in data['counts'].values()):raise ValueError('S03_READER_EXACT_COUNTS_REQUIRED')
    if set(data['product_files'])!=set(PRODUCT_FILES)or set(data['own_files'])!=set(OWN_FILES):raise ValueError('S03_READER_EXACT_SOURCE_FILES_REQUIRED')
    for name,expected_sha in data['product_files'].items():
        if hashlib.sha256((Path(root)/name).read_bytes()).hexdigest()!=expected_sha:raise ValueError('S03_READER_PRODUCT_SOURCE_CHANGED:'+name)
    for name,expected_sha in data['own_files'].items():
        if hashlib.sha256((Path(path).parent/name).read_bytes()).hexdigest()!=expected_sha:raise ValueError('S03_READER_OWN_SOURCE_CHANGED:'+name)
    original=Path(root)/'scripts/current-attendance-period-choice-qualification/cases.py'
    if hashlib.sha256(original.read_bytes()).hexdigest()!=FROZEN_ORIGINAL11_SHA:raise ValueError('S03_READER_OLD_FINANCIAL_ORACLES_CHANGED')
    original_ids=ids(original);reader_ids=ids(Path(path).parent/'cases.py')
    if(len(original_ids)!=11 or len(reader_ids)!=3 or len(set(reader_ids))!=3
       or tuple(data['original11_case_ids'])!=original_ids or tuple(data['additional_reader_case_ids'])!=reader_ids):raise ValueError('S03_READER_EXACT_CASE_IDS_REQUIRED')
    return data


def admit(fresh_original11):
    data=sources();expected=set(data['original11_case_ids'])
    counts=fresh_original11['counts'];cases=fresh_original11['cases']
    if(fresh_original11['status']!='PASS'or tuple(fresh_original11['planned_case_ids'])!=tuple(data['original11_case_ids'])
       or fresh_original11['complete_boundary_restored']is not True
       or set(cases)!=expected or any(case['status']!='PASS'for case in cases.values())
       or type(counts.get('PASS'))is not int or counts['PASS']!=11
       or any(type(value)is not int or value<0 for value in counts.values())or sum(counts.values())!=11):
        raise ValueError('S03_READER_FRESH_UNCHANGED_FINANCIAL11_REQUIRED')
    return dict(status='S03_READER_PREPARED_SOURCES_AND_FRESH_FINANCIAL11_ADMITTED',
        existing_function_captures=15,Native_financial_cases_passed=11,additional_reader_cases_prepared=3,
        total_target_Native_cases=14,additional_Native_credit_before_execution=0,
        per_case_full_sequence_restoration_claim=False,production_go=False,independent_acceptance=False)
