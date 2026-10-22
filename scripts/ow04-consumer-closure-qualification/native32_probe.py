"""Rerun the original Native26 plus six frozen pending-validation controls."""
from hashlib import sha256
from pathlib import Path
import gzip,importlib.util,json,lzma,subprocess,sys,traceback

sys.dont_write_bytecode=True
if sys.argv[1:]:raise SystemExit('Closure qualification accepts no arguments')
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path[:0]=[str(REPO/'scripts'),str(REPO/'scripts/ow04-payment-positive-qualification')]
import native26_probe as retained
import psycopg
from cp7_catalog_state import exact_public_catalog
from cp6_t3_aligned_install import advisors,advisor_delta
spec=importlib.util.spec_from_file_location('ow04_pending_validation_cases',HERE/'native_cases.py')
business=importlib.util.module_from_spec(spec);spec.loader.exec_module(business)
spec=importlib.util.spec_from_file_location('ow04_pending_validation_timing',REPO/'scripts/ow04-payment-current-browser-qualification/diagnostics.py')
timing=importlib.util.module_from_spec(spec);spec.loader.exec_module(timing)
control=retained.control
product,previous,native,package,core,p09=retained.product,retained.previous,retained.native,retained.package,retained.core,retained.p09
IDS=retained.IDS+business.IDS
LABEL='CP7_OW04_CONSUMER_CLOSURE_NATIVE32'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'


def admitted():
    source=json.loads((HERE/'SOURCE.json').read_bytes())
    assert source['base_candidate']=='be346bedec1b462769fbf2aeb19270da1d4c82dd'
    assert source['product_sources']==product.sources()
    for path,digest in source['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('CLOSURE_SOURCE_CHANGED',path)
    changed=subprocess.check_output(['git','-C',str(REPO),'diff','--name-only',source['base_candidate'],'HEAD',
        '--','scripts','src','supabase','tests','.github/workflows'],text=True).splitlines()
    assert set(changed)<=set(source['files'])|{'scripts/ow04-consumer-closure-qualification/SOURCE.json'},changed
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--','scripts','src','supabase','tests','.github/workflows'],text=True).strip()
    assert sha256((HERE/'EXPECTED.json').read_bytes()).hexdigest()==business.EXPECTED_SHA256
    for path,digest in source['unchanged_expectations'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest
    raw=lzma.decompress((REPO/'docs/cp7/d17-14/ow04/payment-native26-527ed740-pass/CP7_OW04_PAYMENT_SOURCE_NATIVE26_POSITIVE.json.xz').read_bytes())
    assert sha256(raw).hexdigest()=='4f2e6a3ec2d325d2b10a00abc823e1177a1c4e9dbbaa0445a397966d7dddab91'
    old=json.loads(raw)
    assert old['status']=='PASS'and old['native']['counts']=={'PASS':26}
    assert set(old['native']['cases'])==set(retained.IDS)
    assert len(IDS)==len(set(IDS))==32
    assert business.expected()['expected_native_count']==32
    return source


def cases(cur,today):return retained.cases(cur,today)+business.cases(cur,today)


def timing_cases(cur,today):
    def observe():
        cur.execute("set local track_functions='all'")
        return timing.one_case(cur,today,0)
    return [(timing.IDS[0],observe)]


def run():
    binding=admitted()
    report=dict(label=LABEL,status='INCOMPLETE',expected_case_count=32,required_case_ids=list(IDS),
        candidate_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        source_declaration=binding,current_financial_sources=product.sources(),
        previous_Native26_is_current_acceptance=False,retained26_actually_rerun=True,
        diagnostic_observations_not_additional_feature_cases=True,
        Auth_HTTP_browser_races_restore_not_qualified_on_changed_source=True,
        formal_CP7C_started=False,production_go=False,feature_complete=False,hosted=False)
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
            if report['native'].get('status')=='PASS':
                report['isolated_timing_observations']=native.strict_group(LABEL+'_TIMING',timing_cases,control.verify)
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
        diagnostic=report.get('isolated_timing_observations',{})
        report['timing_observation_pass']=diagnostic.get('status')=='PASS'and diagnostic.get('counts')=={'PASS':1}
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass'] \
         and group.get('status')=='PASS'and group.get('counts')=={'PASS':32}and group.get('database_remaining',0)==0 \
         and report['timing_observation_pass']:
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','expected_case_count','observed_case_count',
            'cp6_restored','advisor_gate','timing_observation_pass','error','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)


if __name__=='__main__':
    admitted()
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
