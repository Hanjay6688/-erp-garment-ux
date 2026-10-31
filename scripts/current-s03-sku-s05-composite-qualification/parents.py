"""Exact root-admitted current parent Originals, before ERP imports."""
from pathlib import Path
from hashlib import sha256
from functools import lru_cache
import json,math,os,zipfile

HERE=Path(__file__).resolve().parent
HEADS={'SKU':('090b85d3fcb738d3e694d4329d306f199a686eb8','e04831b441bed987cd72ff738cf2a06a7c0ef0ae',41167734749),
       'S03':('3c0c5defe55e48cf6f221c868594dd6676d17170','ca20c918201b455ad09df489829b83b9e6afea95',40983410165)}
MAINS={'SKU':'CP7_SKU_MANAGED_RECOVERY_NATIVE27.json','S03':'CP7_S03_ATTENDANCE_CHOICE_NATIVE14.json'}
GATES=dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=True)


def strict(raw):
    def pairs(rows):
        result={}
        for key,value in rows:
            if key in result:raise ValueError('JOIN_DUPLICATE_ORIGINAL_KEY:'+key)
            result[key]=value
        return result
    def invalid(value):raise ValueError('JOIN_NONFINITE_ORIGINAL:'+value)
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)
    def finite(item):
        if type(item)is float and not math.isfinite(item):invalid(str(item))
        if type(item)is dict:
            for child in item.values():finite(child)
        elif type(item)is list:
            for child in item:finite(child)
    finite(value);return value


def exact(actual,expected,label):
    if type(actual)is not type(expected):raise ValueError('JOIN_PARENT_TYPE:'+label)
    if type(expected)is dict:
        if set(actual)!=set(expected):raise ValueError('JOIN_PARENT_KEYS:'+label)
        for key,value in expected.items():exact(actual[key],value,label+'/'+key)
    elif type(expected)is list:
        if len(actual)!=len(expected):raise ValueError('JOIN_PARENT_LENGTH:'+label)
        for a,b in zip(actual,expected):exact(a,b,label)
    elif actual!=expected:raise ValueError('JOIN_PARENT_VALUE:'+label)


def fields(actual,expected,label):
    for key,value in expected.items():
        if key not in actual:raise ValueError('JOIN_PARENT_FIELD_MISSING:'+label+'/'+key)
        exact(actual[key],value,label+'/'+key)


def pinned(raw,expected,label):
    exact(dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),expected,label)
    return strict(raw)


def specification():
    value=strict((HERE/'PREREQUISITES.json').read_bytes())
    if value['status']!='ROOT_VERIFIED_CURRENT_SKU27_AND_QUALIFIED_S03_NATIVE14_ALL5':
        raise ValueError('JOIN_EXACT_SKU27_AND_QUALIFIED_S03_NATIVE14_ROOT_INTAKE_REQUIRED')
    for kind,(head,tree,run)in HEADS.items():
        fields(value[kind],dict(head=head,tree=tree,run_id=run),'EXACT_CURRENT_'+kind)
        if any(value[kind].get(key)is None for key in('archive','artifact_id','originals','root_receipt')):
            raise ValueError('JOIN_COMPLETE_CURRENT_PARENT_SPECIFICATION_REQUIRED:'+kind)
    return value


@lru_cache(maxsize=2)
def original(kind,path,stat_identity,spec_json):
    # Cached within one process, keyed by file identity and frozen specification.
    spec=strict(spec_json);path=Path(path)
    raw=path.read_bytes();exact(dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),spec['archive'],'EXACT_'+kind+'_ARCHIVE');del raw
    receipt_spec=spec['root_receipt'];receipt=pinned((HERE/receipt_spec['path']).read_bytes(),
        {key:receipt_spec[key]for key in('bytes','sha256')},kind+'_ROOT_RECEIPT')
    fields(receipt,dict(head=spec['head'],tree=spec['tree'],run_id=spec['run_id'],package_all_five=True,
        prior_runs_aggregated=False,production_go=False,independent_acceptance=False),kind+'_ROOT_ACTUAL_ADMISSION')
    fields(receipt,dict(complete27_qualified=True)if kind=='SKU'else dict(complete_native14_qualified=True),kind+'_COMPLETE_PARENT')
    with zipfile.ZipFile(path)as archive:
        if len(archive.namelist())!=spec['members']or len(set(archive.namelist()))!=spec['members']:
            raise ValueError('JOIN_EXACT_PARENT_ARCHIVE_MEMBERS_REQUIRED:'+kind)
        docs={name:pinned(archive.read(name),expected,kind+'/'+name)for name,expected in spec['originals'].items()}
    main=docs[MAINS[kind]];package=docs['T3_PACKAGE_INSTALL.json'];restore=docs['T3_BACKUP_RESTORE_DRILL.json']
    fields(main,dict(status='PASS',qualification_commit=spec['head'],required_case_ids_pass=True,
        baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,cp6_restored=True,
        baseline_advisors_equal=True,advisor_gate=True,used_guard_refused_before_DDL=True,
        production_go=False,independent_acceptance=False),kind+'_ACTUAL_PASS_AND_RESTORE')
    exact(package['gate'],GATES,kind+'_ALL5');fields(package['run_identity'],dict(tool_head=spec['head'],github_sha=spec['head'],
        run_id=str(spec['run_id']),run_attempt='1'),kind+'_EXACT_RUN')
    fields(restore,dict(status='RESTORED_IDENTICAL'),kind+'_COMPLETE_BACKUP')
    if len(main['committed'])!=1:raise ValueError('JOIN_ONE_CURRENT_PARENT_COMPONENT_REQUIRED:'+kind)
    part=next(iter(main['committed'].values()));fields(part,dict(status='PASS'),kind+'_CURRENT_COMPONENT')
    if kind=='SKU':
        browser=part['fresh_real_Auth_browser4']['browser']
        fields(browser,dict(status='RUN_COMPLETE',counts={'PASS':4},real_auth=True,jwt_signed_by_runtime=False,
            host_status='RUN_COMPLETE',host_exit=0,database_remaining=0,console_errors=0,auth_cleanup_failures=[],
            session_leaks=[],auth_counts=dict(before=[0,0,0,0],after=[0,0,0,0],restored=True)),kind+'_REAL_AUTH_BROWSER4_AND_CLEANUP')
        if browser.get('cleanup_failures')or browser.get('business_day_retried')or browser.get('business_day_first_attempt'):
            raise ValueError('JOIN_SINGLE_PARENT_ATTEMPT_AND_CLEANUP_REQUIRED:'+kind)
    else:
        fields(main,dict(actual_Native_cases=14,actual_business_cases=14,actual_browser_cases=0),'S03_RETAINED_NATIVE14_ONLY')
        fields(part,dict(actual_Native_cases=14,both_groups_same_actual_installation=True,
            reader3_requires_actual_fresh_original11=True,combined_strict14_fabricated=False,
            used_guard_refused_before_DDL=True),'S03_STRICT11_PLUS3_AND_REAL_USED_GUARD')
        for key,name in [('native','CP7_S03_ATTENDANCE_CHOICE_NATIVE11_CASES.json'),
                         ('reader_native3','CP7_S03_ATTENDANCE_CHOICE_READER_NATIVE3_CASES.json')]:
            exact(part[key],docs[name],'S03_EXACT_RAW_'+key)
        exact(part['used_inverse_refusal_before'],part['used_inverse_refusal_after'],'S03_USED_GUARD_NO_EFFECT')
    return dict(status='EXACT_CURRENT_ROOT_ADMITTED_PARENT_ORIGINAL',kind=kind,head=spec['head'],tree=spec['tree'],
        run_id=spec['run_id'],artifact_id=spec['artifact_id'],archive=spec['archive'],root_receipt=receipt_spec,
        current_installation=main['source_declaration']['current_installation'],fresh_composite_case_credit=0,
        production_go=False,independent_acceptance=False)


def admitted():
    spec=specification();result={}
    for kind in HEADS:
        path=Path(os.environ['JOIN_'+kind+'_ORIGINAL'])
        if path.is_symlink():raise ValueError('JOIN_PARENT_ORIGINAL_SYMLINK_FORBIDDEN')
        info=path.stat();identity=(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
        result[kind]=original(kind,str(path),identity,json.dumps(spec[kind],sort_keys=True))
    return result
