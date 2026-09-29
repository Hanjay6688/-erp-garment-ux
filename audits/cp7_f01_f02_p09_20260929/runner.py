"""Auditor adapter around frozen disposable install/restore harness, no SQL edits."""
import probe
import hashlib,json,os
from collections import Counter
import cp7_p09_procurement_probe as runner
import cp7_f02_regression_cases as fixed
import cp7_wip_cases as wip

original_native=runner.cases.cases
original_http=runner.cases.http_cases
def cases(cur,today):
    return probe.own_cases(cur,today)+[('WRITER_RETEST_'+k,f) for k,f in fixed.cases(cur,today)+wip.cases(cur,today)]+original_native(cur,today)
def http_cases(http,today):return probe.http_cases(http,today)+original_http(http,today)
runner.cases.cases=cases
runner.cases.http_cases=http_cases
runner.OUT=probe.ROOT/'cp6-proof/t3/CP7_F01_F02_P09_INDEPENDENT.json'

def run():
    result=runner.run()
    report=json.loads(runner.OUT.read_text())
    rows={}
    for key,group in report.items():
        if isinstance(group,dict):
            for collection in ('cases','races'):
                if isinstance(group.get(collection),dict):rows.update(group[collection])
    report.update(audit_candidate='ee8699829bc53799e5f840bb5490059e456fa81a',audit_checkpoint='e3ddcec94c4db2b6fe299cdadc82f50d57781bfc',
      audit_source_commit=os.environ.get('GITHUB_SHA'),blind_audit=False,product_source_changed=False,
      independent_counts=dict(Counter(v['status'] for k,v in rows.items() if k.startswith('AUD_'))),
      writer_rerun_counts=dict(Counter(v['status'] for k,v in rows.items() if not k.startswith('AUD_'))),
      oracle_sha256=hashlib.sha256((probe.ROOT/'audits/cp7_f01_f02_p09_20260929/ORACLE.md').read_bytes()).hexdigest())
    runner.OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
    print(json.dumps({k:report[k] for k in ('status','independent_counts','writer_rerun_counts','cp6_restored','advisor_gate') if k in report}),flush=True)
    return result
if __name__=='__main__':
    runner.package._writer_runtime=lambda browser_mode=False:run()
    runner.package.run('install')
