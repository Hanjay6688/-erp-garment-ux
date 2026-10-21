"""Actual Native20 on the complete isolated payment-correction owner.

Retain every original consumer/refund18 case, add two monetary cases frozen
before Native execution, and prove complete unused removal. No hosted access.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import traceback

if sys.argv[1:]:
    raise SystemExit('Payment source qualification accepts no arguments')
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path[:0]=[str(REPO/'scripts'),str(REPO/'scripts/cp7_customer_credit/consumer')]
sys.argv.extend(['--signed-source','--credit-dependencies','--native-fractional-hpp'])
import cp7_full_ow04_probe as previous
import cp7_payment_source_owning_install as product
import native_consumer_cases as retained
import psycopg
from cp7_catalog_state import exact_public_catalog
from cp6_t3_aligned_install import advisors,advisor_delta

spec=importlib.util.spec_from_file_location('ow04_payment_source_native_cases',HERE/'native_cases.py')
business=importlib.util.module_from_spec(spec)
spec.loader.exec_module(business)
core,native,package,p09=previous.core,previous.native,previous.package,previous.p09
LABEL='CP7_OW04_PAYMENT_SOURCE_NATIVE20'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
STATE=None


def declared():
    source=json.loads((HERE/'SOURCE.json').read_bytes())
    assert source['base_candidate']=='922a874d366105b27e3e75c64965e88fc3063e87'
    assert source['product_sources']==product.sources()
    for path,expected in source['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==expected,('PAYMENT_SOURCE_DECLARED_FILE_CHANGED',path)
    paths=subprocess.check_output(['git','-C',str(REPO),'diff','--name-only',source['base_candidate'],'HEAD',
        '--','scripts','src','supabase','tests','.github/workflows/cp7-ow04-payment-source.yml'],text=True).splitlines()
    assert set(paths)<=set(source['files'])|{'scripts/ow04-payment-source-qualification/SOURCE.json'},paths
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',
        'scripts/cp7_payment_source_owning_install.py','scripts/cp7_customer_credit/payment_correction',
        'scripts/ow04-payment-source-qualification','.github/workflows/cp7-ow04-payment-source.yml'],text=True).strip()
    assert len(business.IDS)==20 and len(retained.IDS)==18
    assert business.GOLD['original_basic9_sha256']==business.fixture.EXPECTED_SHA256
    assert business.GOLD['original_refund9_sha256']==business.refund.EXPECTED_SHA256
    return source


@contextmanager
def product_catalog(cur):
    business.native.b.api.admin(cur)
    with product.catalog._catalog(cur):
        actual=dict(cur.execute(product.catalog.QUERIES['schemas']).fetchall())['erp']
    expected=STATE['installed_catalog']['schemas']['erp']
    if actual==expected:
        yield
        return
    extra=['authenticated','postgres','USAGE',False]
    assert expected[0]==actual[0]=='postgres'and extra not in expected[1]
    assert sorted(actual[1])==sorted(expected[1]+[extra]),'NATIVE_TEST_SCHEMA_DELTA_NOT_EXACT_DECLARED_USAGE'
    cur.execute('revoke usage on schema erp from authenticated')
    try:
        yield
    finally:
        cur.execute('grant usage on schema erp to authenticated')


def verify(cur):
    if STATE is None:raise ValueError('PAYMENT_SOURCE_INSTALLATION_REQUIRED')
    with product_catalog(cur):
        return product.verify(cur,STATE)


def held_state(cur):
    business.native.b.api.admin(cur)
    return dict(rows=product.base.private_rows(cur),boundary=package.boundary.snapshot(cur),
        functions=p09.functions(cur),catalog=product.catalog._catalog_rows(cur))


def refuse_used(cur):
    before=held_state(cur)
    assert before['rows']!=STATE['seeded_private_rows']
    with product_catalog(cur):
        try:product.rollback_preuse(cur,STATE)
        except ValueError as error:assert str(error)==product.predecessor.USED_ERROR,str(error)
        else:raise AssertionError('USED_PAYMENT_SOURCE_INSTALLATION_REMOVED')
        product.verify(cur,STATE)
    assert held_state(cur)==before,'USED_PAYMENT_SOURCE_REMOVAL_REFUSAL_CHANGED_DATA_OR_CATALOG'
    return dict(refused=True,canonical_error=product.predecessor.USED_ERROR,whole_state_unchanged=True,
        refusal_before_any_uninstall=True)


def cases(cur,today):
    return business.cases(cur,today,refuse_used)


def run():
    global STATE
    declaration=declared()
    report=dict(label=LABEL,status='INCOMPLETE',expected_case_count=20,required_case_ids=list(business.IDS),
        candidate_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        source_declaration=declaration,literal_expectations=business.GOLD,
        original_retained_consumer_refund_case_count=18,new_owning_correction_case_count=2,
        Native90_rerun=False,current42_rerun=False,real_Auth_HTTP_browser_races_qualified=False,
        whole_OW04_complete=False,formal_CP7C_started=False,production_go=False,hosted=False)
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
            STATE=product.install(cur)
            report['complete_installed_verification']=product.verify(cur,STATE)
            report['actual_predecessor_verified_before_extension']=STATE['predecessor_proof_before_extension']
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            conn.commit();installed=True
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        with exact_public_catalog(native,retain_raw=True)as catalog:
            report['native']=native.strict_group(LABEL,cases,verify)
        report['native_public_catalog_comparison']=catalog
    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    report['complete_preuse_removal']=product.rollback_preuse(cur,STATE)
                    conn.commit()
                    report['cp6_restored']=previous.restore_state.prove(cur,before,package.boundary.snapshot,
                        core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7'])
                report['advisor_disposition']=core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate']=report['advisor_disposition']['gate']
            except Exception as error:
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        group=report.get('native',{})
        report['observed_case_count']=sum(group.get('counts',{}).values())
        report['required_case_ids_pass']=set(group.get('cases',{}))==set(business.IDS)
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass'] \
         and group.get('status')=='PASS'and group.get('counts')=={'PASS':20}and group.get('database_remaining',0)==0:
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','expected_case_count','observed_case_count',
            'cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)


if __name__=='__main__':
    declared()
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
