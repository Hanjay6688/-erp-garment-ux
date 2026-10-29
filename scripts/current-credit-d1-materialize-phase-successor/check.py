"""Exact four-token materialize successor + retained local proof. No runtime/DB."""
from hashlib import sha256
from pathlib import Path
import gzip,json,os,re,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE='d902e4d2e65cf5b382af1ab041120611f9a61078'
MAT='scripts/cp7_credit_correction_de/materialize.sql'
BEFORE='f0bd81d3a80ad1f465ee5cc424b63009776fb65b9f6a23cbaae80ea331a8e4a4'
AFTER='206c18b517aef54ddc5757fd156a6c7d8d4a2c3240f62779773a4fff74fe6154'
EDITS=(('y jsonb;phase text;','y jsonb;support_phase text;'),
       ('foreach phase in array','foreach support_phase in array'),
       ("case when phase='BEFORE'","case when support_phase='BEFORE'"),
       ("values(plan,x->>'id',phase,","values(plan,x->>'id',support_phase,"))
OTHER=('review.sql','facts.sql','owning.sql','proof.sql','posting.sql','closure.sql','native_delta.py','composition.py')


def original(relative):
    return subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+relative],env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))


def derivation(before,current):
    if sha256(before).hexdigest()!=BEFORE:raise ValueError('MATERIALIZE_EXACT_D902_SOURCE_REQUIRED')
    expected=before.decode()
    for old,new in EDITS:
        if expected.count(old)!=1:raise ValueError('MATERIALIZE_FOUR_EXACT_ANCHORS_REQUIRED')
        expected=expected.replace(old,new,1)
    if current!=expected.encode()or sha256(current).hexdigest()!=AFTER:raise ValueError('MATERIALIZE_ONLY_FOUR_IDENTIFIER_RENAMES_ALLOWED')
    def functions(raw):
        return {m.group(1):m.group(0)for m in re.finditer(rb'create function\s+([\w.]+)\([^$]*?as \$\$.*?\$\$;',raw,re.S|re.I)}
    old,new=functions(before),functions(current)
    if set(old)!=set(new)or len(old)!=3:raise ValueError('MATERIALIZE_EXACT_THREE_FUNCTIONS_REQUIRED')
    for name in (b'cp7_credit_correction_de.finish_v1',b'cp7_credit_correction_de.dispatch_v1'):
        if old[name]!=new[name]:raise ValueError('MATERIALIZE_FINISH_DISPATCH_MUST_REMAIN_BYTE_EXACT')
    return {'before_sha256':BEFORE,'after_sha256':AFTER,'substitutions':4,'unchanged_functions':['finish_v1','dispatch_v1']}


def checked():
    source=json.loads((HERE/'SOURCE.json').read_bytes())
    for path,pin in source['files'].items():
        raw=(ROOT/path).read_bytes()
        if len(raw)!=pin['bytes']or sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('LOCAL_PHASE_SOURCE_CHANGED:'+path)
    before=(HERE/'evidence/BEFORE_materialize.sql').read_bytes()
    if before!=original(MAT):raise ValueError('MATERIALIZE_RETAINED_BEFORE_NOT_PUBLIC_D902')
    proof=derivation(before,(ROOT/MAT).read_bytes())
    for name in OTHER:
        path='scripts/cp7_credit_correction_de/'+name
        if (ROOT/path).read_bytes()!=original(path):raise ValueError('MATERIALIZE_OTHER_BUSINESS_LEAF_CHANGED:'+path)
    # Entire old cases/qualifier/workflow and native fixture remain untouched.
    paths=['scripts/cp7_credit_correction_de/cases.py','scripts/cp7_credit_correction_de/native_fixture.py']
    paths+=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',BASE,'scripts/current-credit-de-native-qualification','.github/workflows/cp7-credit-de-native.yml'],env=dict(os.environ,GIT_NO_LAZY_FETCH='1')).decode().splitlines()
    for path in paths:
        if (ROOT/path).read_bytes()!=original(path):raise ValueError('MATERIALIZE_FROZEN_CASE_QUALIFIER_OR_WORKFLOW_CHANGED:'+path)
    receipts=json.loads((HERE/'evidence/LOCAL_RECEIPTS.json').read_bytes())
    for entry in receipts['entries']:
        encoded=(ROOT/entry['path']).read_bytes();raw=gzip.decompress(encoded)
        if len(encoded)!=entry['gzip_bytes']or sha256(encoded).hexdigest()!=entry['gzip_sha256']or len(raw)!=entry['raw_bytes']or sha256(raw).hexdigest()!=entry['raw_sha256']:
            raise ValueError('MATERIALIZE_RETAINED_LOCAL_RECEIPT_CHANGED')
    last=json.loads(gzip.decompress((HERE/'evidence/LOCAL_RUNTIME_THIRD.json.gz').read_bytes()))
    if last['status']!='PASS_LOCAL_TYPED_RUNTIME_ONLY'or last['Native_executions']!=0 or len(last['cases'])!=5:raise ValueError('MATERIALIZE_COMPLETE_LOCAL_PROOF_REQUIRED')
    for row in last['cases']:
        if row['full_local_rows_catalog22_sequences_sessions_restored']is not True or len(row['before']['catalog'])!=22 or row['before']!=row['after_rollback']:
            raise ValueError('MATERIALIZE_LOCAL_ERROR_OR_SUCCESS_BOUNDARY_CHANGED')
    if last['cases'][0]['error']['code']!='42702':raise ValueError('MATERIALIZE_ORIGINAL_42702_MUST_REMAIN')
    for row in last['cases'][1:3]:
        if row['status']!='PASS_LOCAL_TYPED_RUNTIME'or row['observed']['phase']!='MATERIALIZED':raise ValueError('MATERIALIZE_FULL_RETURN_PATH_REQUIRED')
    strict=gzip.decompress((HERE/'evidence/D902_NATIVE13_CASES.json.gz').read_bytes())
    if len(strict)!=48745 or sha256(strict).hexdigest()!='42935b84f18e96b77fa796402d71a009af596718cedf69ec6950f3bf2a7b6678':raise ValueError('MATERIALIZE_ORIGINAL_D902_RAW_CHANGED')
    actual=json.loads(strict)
    if actual['counts']!={'INCOMPLETE':9,'PASS':4}or len(actual['cases'])!=13:raise ValueError('MATERIALIZE_D902_INCOMPLETE_NOT_A_PREREQUISITE')
    for row in actual['cases'].values():
        if not row['full_boundary_restored']or row['session_leaks']['advisory_locks']!=0 or row['session_leaks']['other_sessions']!=[]:raise ValueError('MATERIALIZE_D902_BOUNDARY_CHANGED')
    return dict(status='PASS_EXACT_FOUR_IDENTIFIER_SOURCE_AND_LOCAL_TYPED_RUNTIME_ONLY',derivation=proof,source_pins=len(source['files']),
        other_business_leaves_exact=8,frozen_case_fixture_qualifier_workflow_files_exact=len(paths),
        local_typed_runtime_controls=5,original_Native_counts={'PASS':4,'INCOMPLETE':9},
        original_Native13_usable_prerequisite=False,new_actual_Native_cases=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(checked(),indent=2))
