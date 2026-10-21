"""One new real product browser source-resolution journey, not Native reruns."""
from hashlib import sha256
from pathlib import Path
import gzip
import json
import lzma
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

sys.dont_write_bytecode = True
if sys.argv[1:]:
    raise SystemExit('Source inverse UI qualification accepts no arguments')
HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get('ERP_REPO', HERE.parents[1])).resolve()
sys.path[:0] = [str(REPO/'scripts'), str(REPO/'scripts/ow04-consumer-qualification')]
import consumer_transport_probe as transport
import cp7_consumer_owning_install as product

package, core, p09 = transport.package, transport.core, transport.p09
previous, consumer, modes = transport.predecessor, transport.consumer, transport.modes
IDS = ('OW04_SOURCE_REFUND_UNDO_RETURN_REVERSE_MOBILE',)
PRODUCT = ('src/SalesCreditDependencies.tsx','src/SalesReturnPanel.tsx','src/lib/clientError.ts')
HARNESS = tuple('scripts/ow04-source-inverse-ui-qualification/'+p for p in
    ('EXPECTED.json','source_probe.py','source_fixture.py','browser_cases.mjs'))
WORKFLOW = '.github/workflows/cp7-ow04-source-inverse-ui.yml'
OUT = product.ROOT/'cp6-proof/t3/CP7_OW04_SOURCE_INVERSE_UI1.json'
STATE = None


def admitted():
    native_path = REPO/'docs/cp7/d17-14/ow04/composed-current90-6f851c90-pass/CP7_OW04_COMPOSED_CURRENT_NATIVE90.json.xz'
    raw = lzma.decompress(native_path.read_bytes())
    assert sha256(raw).hexdigest() == 'a6149331588110e92229625475f9d3f77a09df74fda369af33a3ebc92ded0ae1'
    native = json.loads(raw)
    assert native['status'] == 'PASS' and native['native']['counts'] == {'PASS':90}
    assert native['candidate_commit'] == '6f851c90c999d226fe4e28038b5851c90f77d726'
    assert native['composed_sources'] == product.sources(), 'QUALIFIED_COMPLETE_FINANCIAL_SOURCE_CHANGED'
    assert native['cp6_restored'] and native['advisor_gate'] and native['required_case_ids_pass']
    current_path = REPO/'docs/cp7/d17-14/ow04/consumer-current42-da6a5454-pass/CP7_OW04_CONSUMER_CURRENT42.json.gz'
    raw42 = gzip.decompress(current_path.read_bytes())
    assert sha256(raw42).hexdigest() == '80d14cca672c860ffa9260011aeb83c7891cc6a5a3b3becb2afe8e2636b5aeed'
    current = json.loads(raw42)
    assert current['status'] == 'PASS' and current['observed_case_count'] == current['expected_case_count'] == 42
    assert current['consumer_sources'] == consumer.sources()
    assert current['cp6_restored'] and current['advisor_gate'] and current['actual_product_browser_loopback_proven']
    for kind,n in (('native',18),('retained_http',14),('races',2),('http',4),('browser',4)):
        assert current[kind]['counts'] == {'PASS':n}
    declaration = json.loads((HERE/'EXPECTED.json').read_bytes())
    assert tuple(declaration['case_ids']) == IDS and declaration['expected_count'] == 1
    source = json.loads((HERE/'SOURCE.json').read_bytes())
    expected = set(PRODUCT)|set(HARNESS)|{WORKFLOW}
    assert set(source['files']) == expected
    for path, digest in source['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest() == digest, path
    changed = transport.git('diff','--name-only','36309f8fbf5c0281ae51749f11ab9017a5875ef7','HEAD',
        '--','src','scripts','supabase','tests',WORKFLOW).splitlines()
    assert set(changed) <= expected|{'scripts/ow04-source-inverse-ui-qualification/SOURCE.json'}, changed
    assert not transport.git('status','--porcelain','--',*PRODUCT,'scripts/ow04-source-inverse-ui-qualification',WORKFLOW)
    return dict(classification='EXACT_SAME_ACTUAL_NATIVE90_CURRENT42_FINANCIAL_SOURCE_NEW_GUIDED_UI',
        Native90_reused_candidate=native['candidate_commit'],current42_reused_candidate=current['candidate_commit'],
        Native90_rerun=False,current42_rerun=False,financial_SQL_changed=False,
        original_primary_reports_verified=True,files=source['files'],
        declaration_sha256=sha256((HERE/'EXPECTED.json').read_bytes()).hexdigest())


def verify_copy(cur):
    if STATE is None:
        raise ValueError('SOURCE_UI_COMPOSED_INSTALLATION_REQUIRED')
    # The copied DB has its own administrative database identity/ACL. Retain
    # the actual current consumer's complete pg_proc/private/raw-census proof;
    # the primary install/removal also run the complete22-group verifier.
    return consumer.verify(cur, STATE['consumer'])


def run():
    global STATE
    binding = admitted()
    assert os.environ.get('AUDITOR_UI_MODE') == 'ENTENG'
    report = dict(label='CP7_OW04_SOURCE_INVERSE_UI1',status='INCOMPLETE',
        expected_case_count=1,required_case_ids=list(IDS),candidate_commit=transport.git('rev-parse','HEAD'),
        source_binding=binding,Native90_rerun=False,current42_rerun=False,
        scope='REAL_PRODUCT_MOBILE_REFUND_NAMED_UNDO_THEN_SOURCE_RETURN_INVERSE',
        production_go=False,formal_CP7C_started=False,feature_complete=False,independent_acceptance=False,hosted=False)
    installed = False
    try:
        with transport.psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
            p09.wip.policy.bf.verified(cur)
            before = previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
            STATE = product.install(cur)
            report['complete_installed_verification'] = product.verify(cur,STATE)
            report['verified_predecessor_info_manifest'] = core.predecessor_info_manifest(cur)
            conn.commit()
            installed = True
        report['advisors_with_product'] = transport.advisors(package.boundary.PG)
        hosts_before = set(Path(tempfile.gettempdir()).glob('cp6-auditor-browser-*'))
        report['browser'] = modes.run_browser(HERE/'browser_cases.mjs',verify_copy,'ow04_source_inverse_ui1')
        hosts = []
        for directory in sorted(set(Path(tempfile.gettempdir()).glob('cp6-auditor-browser-*'))-hosts_before):
            path = directory/'BROWSER.json'
            if not path.is_file():
                continue
            raw = path.read_bytes()
            target = OUT.parent/('SOURCE_INVERSE_BROWSER_HOST_'+str(len(hosts)+1)+'.json')
            shutil.copyfile(path,target)
            hosts.append(dict(receipt=target.name,sha256=sha256(raw).hexdigest(),report=json.loads(raw)))
        report['actual_browser_hosts'] = hosts
        report['actual_product_loopback_proven'] = any(h['report'].get('ui_mode') == 'ENTENG'
            and h['report'].get('real_auth') is True and h['report'].get('product_responses_mocked') is False
            and h['report'].get('enteng_requests_answered_by_loopback',0)>0
            and set(h['report'].get('cases',{})) == set(IDS)
            and all(v['status'] == 'PASS' for v in h['report']['cases'].values()) for h in hosts)
    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        report['frontend_source_unchanged'] = all(sha256((REPO/path).read_bytes()).hexdigest() == value for path,value in binding['files'].items())
        if installed:
            try:
                with transport.psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
                    report['complete_composed_preuse_removal'] = product.rollback_preuse(cur,STATE)
                    conn.commit()
                    report['cp6_restored'] = previous.restore_state.prove(cur,before,package.boundary.snapshot,
                        core.predecessor.public_state,p09.functions,report)
                    conn.rollback()
                    p09.wip.policy.bf.verified(cur)
                    conn.rollback()
                report['advisor_delta'] = transport.advisor_delta(transport.advisors(package.boundary.PG),report['advisors_with_product'])
                report['advisor_disposition'] = core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate'] = report['advisor_disposition']['gate']
            except Exception as error:
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        group = report.get('browser',{})
        report['observed_case_count'] = sum(group.get('counts',{}).values())
        if not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') \
            and report['frontend_source_unchanged'] and report.get('actual_product_loopback_proven') \
            and group.get('status') in ('PASS','RUN_COMPLETE') and not group.get('error') \
            and group.get('counts') == {'PASS':1} and set(group.get('cases',{})) == set(IDS) \
            and group.get('real_auth') is True and group.get('jwt_signed_by_runtime') is False \
            and group.get('test_only_usage_grant') is False and group.get('database_remaining',1) == 0 \
            and group.get('auth_counts',{}).get('restored') is True and not group.get('cleanup_failures') \
            and not group.get('auth_cleanup_failures') and group.get('host_exit') == 0 \
            and group.get('host_status') == 'RUN_COMPLETE':
            report['status'] = 'PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k) for k in ('label','status','expected_case_count','observed_case_count',
            'cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)


if __name__ == '__main__':
    admitted()
    package._writer_runtime = lambda browser_mode=False:run()
    package.run('install')
