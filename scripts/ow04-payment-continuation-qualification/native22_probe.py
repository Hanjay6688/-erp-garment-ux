"""Retained20 plus the same two first-failing journeys on changed financial source.

All original20 are actually rerun. Both original first-failing journeys retain
their literal gold and additionally reject unowned header/payment mutations.
"""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import lzma
import subprocess
import sys
import traceback

sys.dont_write_bytecode=True
if sys.argv[1:]:raise SystemExit('Payment interoperability qualification accepts no arguments')
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path[:0]=[str(REPO/'scripts'),str(REPO/'scripts/cp7_customer_credit/consumer'),
    str(REPO/'scripts/ow04-payment-source-qualification')]
import source_probe as control
import psycopg
from cp7_catalog_state import exact_public_catalog
from cp6_t3_aligned_install import advisors,advisor_delta

spec=importlib.util.spec_from_file_location('ow04_payment_interop_native_cases',HERE/'native_cases.py')
business=importlib.util.module_from_spec(spec);spec.loader.exec_module(business)
product,previous,native,package,core,p09=control.product,control.previous,control.native,control.package,control.core,control.p09
IDS=tuple(control.business.IDS)+tuple(row['id']for row in business.expected()['cases'])
LABEL='CP7_OW04_PAYMENT_SOURCE_NATIVE22'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'


def admitted():
    source=json.loads((HERE/'SOURCE.json').read_bytes())
    assert source['base_candidate']=='1a591000e42b253ce9bdad0c99d6bf2397115e48'
    assert source['product_sources']==product.sources()
    for path,expected in source['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==expected,('NATIVE22_SOURCE_CHANGED',path)
    changed=subprocess.check_output(['git','-C',str(REPO),'diff','--name-only',source['base_candidate'],'HEAD',
        '--','scripts','src','supabase','tests','.github/workflows'],text=True).splitlines()
    assert set(changed)<=set(source['files'])|{'scripts/ow04-payment-continuation-qualification/SOURCE.json'},changed
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',
        'scripts/cp7_customer_credit/payment_correction','scripts/ow04-payment-continuation-qualification',
        '.github/workflows/cp7-ow04-payment-continuation.yml','.github/workflows/cp7-ow04-payment-source.yml'],text=True).strip()
    assert sha256((HERE/'EXPECTED_INTEROP2.json').read_bytes()).hexdigest()==business.EXPECTED_SHA256
    assert sha256((REPO/'scripts/ow04-payment-source-qualification/EXPECTED.json').read_bytes()).hexdigest()=='92c411cf225d7c54a53445f603fedfac8102ac6cbdce9fd9558b45d701f8d38c'
    raw=lzma.decompress((REPO/'docs/cp7/d17-14/ow04/payment-source-interop2-e9d04e7f-first-result/CP7_OW04_PAYMENT_SOURCE_INTEROP2.json.xz').read_bytes())
    assert sha256(raw).hexdigest()=='845074735b713b9457df2cfa3270bac1e78542f8096b8cd084dd20d683b740ec'
    first=json.loads(raw)
    assert first['status']=='INCOMPLETE'and first['native']['counts']=={'INCOMPLETE':2}
    assert all('CP7_CREDIT_CURRENT_SIGNED_SOURCE_CHANGED'in row['error']for row in first['native']['cases'].values())
    assert len(IDS)==22 and len(set(IDS))==22
    return source


def cases(cur,today):return control.business.cases(cur,today,control.refuse_used)+business.cases(cur,today)


def run():
    binding=admitted()
    report=dict(label=LABEL,status='INCOMPLETE',expected_case_count=22,required_case_ids=list(IDS),
        candidate_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        source_declaration=binding,actual_financial_sources=product.sources(),
        literal_expectations=business.expected(),retained20_rerun=True,previous_Native20_is_current_acceptance=False,formal_CP7C_started=False,
        real_Auth_HTTP_browser_races_qualified=False,production_go=False,feature_complete=False,hosted=False)
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
            control.STATE=product.install(cur)
            report['complete_installed_verification']=product.verify(cur,control.STATE)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            conn.commit();installed=True
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        with exact_public_catalog(native,retain_raw=True)as catalog:
            report['native']=native.strict_group(LABEL,cases,control.verify)
        report['native_public_catalog_comparison']=catalog
    except Exception as error:report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    report['complete_preuse_removal']=product.rollback_preuse(cur,control.STATE)
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
        report['required_case_ids_pass']=set(group.get('cases',{}))==set(IDS)
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass'] \
         and group.get('status')=='PASS'and group.get('counts')=={'PASS':22}and group.get('database_remaining',0)==0:
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','expected_case_count','observed_case_count',
            'cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)


if __name__=='__main__':
    admitted()
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
