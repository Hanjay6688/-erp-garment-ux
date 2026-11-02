"""Exact completed FREE3 originals; reuse never becomes fresh case credit."""
from pathlib import Path
from hashlib import sha256,file_digest
import importlib.util,json,os

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ROOT_HEAD='3a26a27530525e0407be996e6ee2cbabe3314076'
ROOT_TREE='f9d56f07f1d2ca329b658cde8afabe75d04cd240'
ROOT_PATH='docs/cp7/d17-14/ow15/FREE41_AD986_ROOT_RETAINED3_20261102.json'
ROOT_PIN={'bytes':9721,'sha256':'7ddda623e3417b3c04d0db2d7f7ce309718a2128c0dfc4fa22f8d7ee0edeb375'}
ORIGIN_HEAD='ad986b9a9d432f2ffac2b961710c3852c6c2ef90'
ORIGIN_TREE='80bc5471330b89497991ba1e67615287b01e59c1'
RUN=41388877929
JOB=125095681990
ARTIFACT=13119648673
ARCHIVE={'bytes':28320283,'sha256':'8827d2262f51781fd7f3be977192ba7f315ee9d5b94444546121b723a9dbdc9d','members':127}
RAW='CP7_CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3_CASES.json'
NATIVE_SOURCE_PIN={'bytes':17601,'sha256':'ef17c94216892f2a40681eac8372a0bd1e6fddc52e7dbd5f3868a85145734792'}


def typed():
    spec=importlib.util.spec_from_file_location('retained_FREE3_original_strict_json',
        ROOT/'scripts/current-s03-sku-s05-composite-qualification/parents.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def receipt():
    p=typed();raw=(HERE/'ROOT_RETAINED3.json').read_bytes()
    p.exact(pin(raw),ROOT_PIN,'FREE3_EXACT_ROOT_RETENTION_RECEIPT_BYTES')
    value=p.strict(raw)
    p.fields(value,dict(status='ROOT_RETAINED_FREE3_NOT_AGGREGATE_PASS',head=ORIGIN_HEAD,tree=ORIGIN_TREE,
        run_id=RUN,job_id=JOB,artifact_id=ARTIFACT,archive=ARCHIVE,retained_Native_cases=3,
        actual_new_Native_cases=0,actual_new_browser_cases=0,retained_cases_are_not_fresh=True,
        retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,
        package_all_five=False,complete3_qualified=False,actual_outer_restoration_verified=True,
        actual_backup_restore_verified=True,actual_primary_unchanged=True,actual_advisors_equal=True,
        failed_worker_reaped=True,missing_committed_use_and_inverse_refusal=True,
        missing_error='FREE_DATE_NATIVE_ORIGINAL_ACTIVE_OWNER_REQUIRED_WITHOUT_PROMOTION',
        source_invariant_reuse_required=True,all_five_new_package_gates_still_required=True,
        production_go=False,independent_acceptance=False),'FREE3_ORIGINAL_FAILED_RUN_AND_MISSING_WITNESS_RETAINED')
    p.exact(pin((HERE/'native_free.py').read_bytes()),NATIVE_SOURCE_PIN,
        'FREE3_ALL_THREE_BUSINESS_CASE_BODIES_AND_FIXTURE_BINDING_UNCHANGED')
    return value


def invariant_sources(graph):
    value=receipt();typed().exact(pin(canonical(graph)),value['qualified_complete_DE_FREE_date_sources'],
        'FREE3_ENTIRE_ACTUAL_PRODUCT_GRAPH_EQUALS_COMPLETED_ORIGINAL_CASES')
    return dict(status='ROOT_VALIDATED_FREE3_RETAINED_BY_COMPLETE_SOURCE_IDENTITY',root_head=ROOT_HEAD,
        root_tree=ROOT_TREE,root_path=ROOT_PATH,root_receipt=ROOT_PIN,original_head=ORIGIN_HEAD,
        original_tree=ORIGIN_TREE,original_run_id=RUN,original_job_id=JOB,artifact_id=ARTIFACT,
        archive=ARCHIVE,original_native=value['originals'][RAW],retained_Native_cases=3,
        actual_new_Native_cases=0,retained_cases_are_not_fresh=True,financial_groups_rerun=False,
        retained_case_ids=value['retained_case_ids'],qualified_complete_DE_FREE_date_sources=value['qualified_complete_DE_FREE_date_sources'],
        source_invariant_reuse=True,retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,
        all_five_new_package_gates_still_required=True,production_go=False,independent_acceptance=False)


def original_admission():
    p=typed();value=p.strict((ROOT/'cp6-proof/t3/FREE3_RETAINED_ORIGINAL_ADMISSION.json').read_bytes())
    expected=dict(status='EXACT_FAILED_CANONICAL_FREE3_ORIGINALS_ADMITTED_NOT_RERUN',root_receipt=ROOT_PIN,
        original_head=ORIGIN_HEAD,original_run_id=RUN,original_job_id=JOB,artifact_id=ARTIFACT,archive=ARCHIVE,
        original_native=receipt()['originals'][RAW],retained_Native_cases=3,actual_new_Native_cases=0,
        financial_groups_rerun=False,retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,
        production_go=False,independent_acceptance=False)
    p.exact(value,expected,'FREE3_EXACT_ORIGINAL_CANONICAL_ADMISSION_BEFORE_REUSE');return value


def original_native(graph):
    proof=invariant_sources(graph);original_admission();p=typed();path=ROOT/'cp6-proof/t3'/RAW
    with path.open('rb')as stream:digest=file_digest(stream,'sha256').hexdigest()
    p.exact(dict(bytes=path.stat().st_size,sha256=digest),proof['original_native'],
        'FREE3_EXACT_COMPLETE_STRICT_NATIVE_ORIGINAL_BYTES_NO_REWRITE')
    return p.strict(path.read_bytes())
