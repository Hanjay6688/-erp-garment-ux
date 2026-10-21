"""Real-Auth HTTP16 on the exact actual Native20 financial source.

Original14 consumer HTTP cases and two real owning payment corrections.
No Native20 rerun, browser, race, hosted or production qualification.
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
if sys.argv[1:]:raise SystemExit('Payment HTTP qualification accepts no arguments')
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path[:0]=[str(REPO/'scripts'),str(REPO/'scripts/cp7_customer_credit/consumer'),
    str(REPO/'scripts/ow04-payment-source-qualification'),str(REPO/'scripts/ow04-qualification'),
    str(REPO/'scripts/ow04-consumer-qualification')]
import source_probe as control
import psycopg
import cp6_auditor_modes as modes
from cp6_t3_aligned_install import advisors,advisor_delta

spec=importlib.util.spec_from_file_location('ow04_payment_source_http_cases',HERE/'http_cases.py')
business=importlib.util.module_from_spec(spec);spec.loader.exec_module(business)
product,previous,native,package,core,p09=control.product,control.previous,control.native,control.package,control.core,control.p09
IDS=business.IDS
LABEL='CP7_OW04_PAYMENT_SOURCE_HTTP16'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'


def admitted():
    binding=json.loads((HERE/'QUALIFIED_NATIVE20.json').read_bytes())
    path=REPO/binding['original_report'];raw=lzma.decompress(path.read_bytes())
    assert sha256(raw).hexdigest()==binding['original_report_sha256']
    accepted=json.loads(raw)
    assert accepted['candidate_commit']==binding['candidate_commit']=='f06570e045d720e9bd7806858b7dd08fb7e45522'
    assert accepted['status']=='PASS'and accepted['native']['counts']=={'PASS':20}
    assert accepted['expected_case_count']==accepted['observed_case_count']==20
    assert accepted['required_case_ids_pass']and accepted['cp6_restored']and accepted['advisor_gate']
    assert accepted['source_declaration']['product_sources']==product.sources(),'ACTUAL_NATIVE20_FINANCIAL_SOURCE_CHANGED'
    source=json.loads((HERE/'SOURCE.json').read_bytes())
    assert source['base_candidate']=='e9d04e7f23be149d8499f9ba649f07b29cfe396b'
    assert source['product_sources']==product.sources()
    for path,expected in source['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==expected,('HTTP_SOURCE_CHANGED',path)
    changed=subprocess.check_output(['git','-C',str(REPO),'diff','--name-only',source['base_candidate'],'HEAD',
        '--','scripts','src','supabase','tests','.github/workflows/cp7-ow04-payment-http.yml'],text=True).splitlines()
    assert set(changed)<=set(source['files'])|{'scripts/ow04-payment-http-qualification/SOURCE.json'},changed
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',
        'scripts/ow04-payment-http-qualification','.github/workflows/cp7-ow04-payment-http.yml'],text=True).strip()
    assert len(IDS)==16 and tuple(json.loads((HERE/'EXPECTED.json').read_bytes())['required_case_ids'])==IDS
    business.credit.expected()
    return binding


def verify(cur):return product.verify(cur,control.STATE)


def run():
    binding=admitted()
    report=dict(label=LABEL,status='INCOMPLETE',expected_case_count=16,required_case_ids=list(IDS),
        candidate_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        qualified_Native20_binding=binding,actual_financial_sources=product.sources(),
        literal_expectations=json.loads((HERE/'EXPECTED.json').read_bytes()),Native20_rerun=False,formal_CP7C_started=False,
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
        report['http']=modes.run_http(business,verify,'ow04_payment_source16')
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
        group=report.get('http',{})
        report['observed_case_count']=sum(group.get('counts',{}).values())
        report['required_case_ids_pass']=set(group.get('cases',{}))==set(IDS)
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass'] \
         and group.get('status')in('PASS','RUN_COMPLETE')and group.get('counts')=={'PASS':16}and group.get('database_remaining',1)==0 \
         and(group.get('auth_counts')or{}).get('restored')and not group.get('cleanup_failures'):
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','expected_case_count','observed_case_count',
            'cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)


if __name__=='__main__':
    admitted()
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
