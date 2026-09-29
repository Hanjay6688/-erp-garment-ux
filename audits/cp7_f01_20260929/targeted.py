"""Resolve only two auditor-probe assumptions; keep prior 29 PASS unchanged."""
from pathlib import Path
import sys,json,traceback,hashlib,gzip
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import probe
r=probe.runner
import cp7_p00_catalogue as catalogue

def run():
    report=dict(label='AUD_F01_TARGETED_FOLLOWUP',status='INCOMPLETE',production_go=False,
        preceding_run=36512993335,source_sha256=hashlib.sha256(r.bundle.bundle().encode()).hexdigest())
    installed=False
    try:
        with r.psycopg.connect(r.package.boundary.ADMIN) as conn,conn.cursor() as cur:
            r.bf.verified(cur);before=r.package.boundary.snapshot(cur);public_before=r.native.public_state(cur);conn.rollback()
            cur.execute(r.bundle.bundle(),prepare=False);conn.commit();installed=True;r.verify(cur);conn.rollback()
        with_cp7=r.advisors(r.package.boundary.PG)
        names={'AUD_F01_OPS_NO_FINANCE_EXECUTION','AUD_F01_FULL_EFFECTIVE_ACL'}
        report['native']=r.native.strict_group('AUD_F01_TARGETED',lambda cur,today:[(k,fn) for k,fn in probe.cases(cur,today) if k in names],r.verify)
    except Exception as exc:report.update(error=str(exc),traceback=traceback.format_exc())
    finally:
        if installed:
            with r.psycopg.connect(r.package.boundary.ADMIN) as conn,conn.cursor() as cur:
                cur.execute('drop owned by cp7_capture cascade;drop role cp7_capture',prepare=False);conn.commit()
                report['cp6_restored']=r.package.boundary.snapshot(cur)==before and r.native.public_state(cur)==public_before
                conn.rollback();r.bf.verified(cur);conn.rollback()
            baseline=r.advisors(r.package.boundary.PG)
            report['advisor_delta']=r.advisor_delta(baseline,with_cp7)
            delta=report['advisor_delta']
            report['advisor_gate']=delta['status']=='NO_NEW_FINDINGS' or (delta['status']=='REVIEW_REQUIRED' and all(
                (f.get('name'),f.get('level'),(f.get('metadata') or {}).get('schema'))==('rls_enabled_no_policy','INFO','cp7_private') for f in delta.get('added',[])))
        # Independently recapture P00 under its read-only controls, and compare
        # semantic source bodies rather than ephemeral OIDs or dump formatting.
        if not report.get('error') and report.get('cp6_restored'):
            try:
                actual=catalogue.capture(r.package.boundary.ADMIN)
                prior=json.loads(gzip.decompress((ROOT/'docs/cp7/evidence/p00/CP7_P00_CATALOGUE.json.gz').read_bytes()))
                def digest_map(obj):return {f['signature']:f['definition_sha256'] for f in obj['functions']}
                assert digest_map(actual)==digest_map(prior),'P00_EFFECTIVE_FUNCTION_DRIFT'
                assert actual['read_only_write_refusal_sqlstate']=='25006'
                report['p00_recapture']=dict(status='PASS',functions=len(actual['functions']),relations=len(actual['relations']),triggers=len(actual['triggers']),matching_function_definitions=True,write_refusal='25006')
            except Exception as exc:report['p00_recapture']=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
        n=report.get('native',{})
        ok=not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') and n.get('status')=='PASS' and n.get('counts')=={'PASS':2} and report.get('p00_recapture',{}).get('status')=='PASS'
        report['status']='PASS' if ok else 'INCOMPLETE'
        out=ROOT/'cp6-proof/t3/CP7_F01_TARGETED.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps(dict(f01_targeted={k:report.get(k) for k in ('status','source_sha256','cp6_restored','advisor_gate','p00_recapture','error')},native_counts=n.get('counts')),default=str),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False)

if __name__=='__main__':
    r.package._writer_runtime=lambda browser_mode=False:run()
    r.package.run('install')
