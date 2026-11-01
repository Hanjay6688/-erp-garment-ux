"""Exact Root-validated old financial4; invariant reuse supplies no fresh cases."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ROOT_HEAD='8efe21a9211b9ee2a617a37b7ff69233499e3a61'
ROOT_TREE='591c92b8b71f30271ee1c232cdc3b3422aaf7a77'
ROOT_PATH='docs/cp7/d17-14/ow15/CURRENT_PERMANENT23E_ROOT_RETAINED4_20261102.json'
ROOT_PIN={'bytes':7661,'sha256':'2d63531df996ff6e5fb9400ec2a0dc4a4e47283750f8c560e435819b54abf3af'}
ORIGIN_HEAD='23e3e77d6dddd48a98d31c35822d637db2cee528'
ORIGIN_TREE='0637e2f69fc24cd2a98260210e9c358222ae992b'
RUN=41346386747
JOB=124966984224
ARTIFACT=13101464593
ARCHIVE={'bytes':48925129,'sha256':'95d7ccbe4be056c27968ba0c2c312dcce16a0608c3cca0406aa796535a09fa44','members':134}
NS='scripts/current-final-s03-sku-s05-preparation/'


def typed():
    spec=importlib.util.spec_from_file_location('retained_permanent4_strict_typed_json',ROOT/'scripts/current-s03-sku-s05-composite-qualification/parents.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def receipt(raw=None):
    p=typed();raw=(HERE/'ROOT_RETAINED4.json').read_bytes()if raw is None else raw
    p.exact(pin(raw),ROOT_PIN,'EXACT_ROOT_RETAINED_FINANCIAL4_RECEIPT_BYTES')
    value=p.strict(raw)
    p.fields(value,dict(status='ROOT_RETAINED_PERMANENT_FINANCIAL4_NOT_AGGREGATE_PASS',
        head=ORIGIN_HEAD,tree=ORIGIN_TREE,run_id=RUN,job_id=JOB,artifact_id=ARTIFACT,archive=ARCHIVE,
        retained_Native_cases=4,actual_new_Native_cases=0,actual_new_browser_cases=0,
        retained_cases_are_not_fresh=True,package_all_five=False,complete6_qualified=False,
        retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,
        actual_outer_restoration_verified=True,actual_backup_restore_verified=True,
        actual_primary_unchanged=True,actual_advisors_equal=True,actual_Auth_and_browser_copy_cleanup=True,
        failed_worker_reaped=True,source_invariant_reuse_required=True,
        all_five_new_package_gates_still_required=True,production_go=False,independent_acceptance=False),
        'EXACT_ACTUAL_ROOT_FINANCIAL4_WITH_UNQUALIFIED_BROWSER2')
    p.exact(pin((HERE/'persistent_financial.py').read_bytes()),value['financial_callback_source'],
        'ALL_ORIGINAL_PERMANENT_FINANCIAL_CALLBACK_SOURCE_BYTES_UNCHANGED')
    return value


def invariant_sources(graph):
    value=receipt();p=typed()
    p.exact(pin(canonical(graph)),value['qualified_complete_sources'],'ENTIRE_ACTUAL_PRODUCT_GRAPH_EQUALS_RETAINED4')
    p.exact(pin(canonical(graph['financial_parent'])),value['qualified_financial_sources'],
        'ENTIRE_FINANCIAL_GRAPH_EQUALS_RETAINED4')
    return dict(status='ROOT_VALIDATED_FINANCIAL4_RETAINED_BY_COMPLETE_SOURCE_IDENTITY',
        root_head=ROOT_HEAD,root_tree=ROOT_TREE,root_path=ROOT_PATH,root_receipt=ROOT_PIN,
        original_head=ORIGIN_HEAD,original_tree=ORIGIN_TREE,original_run_id=RUN,original_job_id=JOB,
        artifact_id=ARTIFACT,archive=ARCHIVE,original_native=value['originals']['CP7_PERMANENT_S05_S03_FINANCIAL_NATIVE4.json'],
        retained_Native_cases=4,retained_case_ids=value['retained_case_ids'],missing_case_ids=value['missing_case_ids'],
        actual_new_Native_cases=0,retained_cases_are_not_fresh=True,financial_groups_rerun=False,
        qualified_complete_sources=value['qualified_complete_sources'],source_invariant_reuse=True,
        retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,
        all_five_new_package_gates_still_required=True,production_go=False,independent_acceptance=False)


def original_admission():
    value=typed().strict((ROOT/'cp6-proof/t3/PERMANENT_RETAINED4_ORIGINAL_ADMISSION.json').read_bytes())
    expected=dict(status='EXACT_FAILED_CANONICAL_FINANCIAL4_ORIGINALS_ADMITTED_NOT_RERUN',
        root_receipt=ROOT_PIN,original_head=ORIGIN_HEAD,original_run_id=RUN,original_job_id=JOB,
        artifact_id=ARTIFACT,archive=ARCHIVE,
        original_native=receipt()['originals']['CP7_PERMANENT_S05_S03_FINANCIAL_NATIVE4.json'],
        retained_Native_cases=4,actual_new_Native_cases=0,financial_groups_rerun=False,
        retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,
        production_go=False,independent_acceptance=False)
    typed().exact(value,expected,'EXACT_ORIGINAL_ARCHIVE_ADMISSION_BEFORE_REUSE')
    return value


def release_source(conn,cur):
    info=conn.info
    if(info.host not in('127.0.0.1','localhost')or info.port!=54322 or info.dbname!='cp6_rollback'
        or type(info.backend_pid)is not int or info.backend_pid<=0):
        raise ValueError('PERMANENT_FOCUSED_EXACT_OWN_LOCAL_SOURCE_CONNECTION_REQUIRED')
    pid=info.backend_pid;conn.rollback()
    try:cur.close()
    finally:conn.close()
    if cur.closed is not True or conn.closed is not True:
        raise ValueError('PERMANENT_FOCUSED_OWN_SOURCE_RELEASE_BEFORE_BROWSER_COPY_REQUIRED')
    return dict(phase='AFTER_PERMANENT_INSTALL_BEFORE_COMMITTED_WITNESS_AND_BROWSER_COPY',
        database='cp6_rollback',backend_pid=pid,cursor_closed=True,connection_closed=True,
        foreign_backends_terminated=0,actual_Native_case_credit=0)


def routes():
    """Recover every original byte of the small browser-only caller successor."""
    p=typed();record=p.strict((HERE/'FOCUSED_BROWSER2_ORIGIN.json').read_bytes())
    p.fields(record,dict(origin_head=ORIGIN_HEAD,origin_tree=ORIGIN_TREE,
        financial_callback_source_changed=False,product_SQL_or_reader_changed=False,
        retained_Native_cases=4,fresh_browser_cases=2,actual_ERP_cases=0),
        'EXACT_BROWSER_ONLY_FOCUSED_SUCCESSOR_DECLARATION')
    for name,item in record['files'].items():
        before=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',ORIGIN_HEAD+':'+name])
        p.exact(pin(before),item['original'],'EXACT_FOCUSED_CALLER_ORIGINAL:'+name)
        text=before.decode()
        for change in item['changes']:
            p.exact(text.count(change['before']),change['count'],'EXACT_COUNTED_FOCUSED_CALLER_ROUTE:'+name)
            text=text.replace(change['before'],change['after'],change['count'])
        actual=(ROOT/name).read_bytes();p.exact(text.encode(),actual,'ONLY_DECLARED_FOCUSED_CALLER_ROUTES:'+name)
        p.exact(pin(actual),item['derived'],'EXACT_FOCUSED_CALLER_DERIVED:'+name)
        for change in reversed(item['changes']):
            p.exact(text.count(change['after']),change['count'],'EXACT_FOCUSED_ROUTE_INVERSE:'+name)
            text=text.replace(change['after'],change['before'],change['count'])
        p.exact(text.encode(),before,'EVERY_ORIGINAL_CALLER_BYTE_RECOVERED:'+name)
    return dict(status='EXACT_REVERSIBLE_BROWSER_ONLY_SUCCESSOR_ROUTES',files=len(record['files']),
        all_original_bytes_recovered=True,actual_ERP_cases=0)
