"""Use the release installer unchanged and replace only its test callback."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import cp6_t3_package_run as package
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))

def runtime(browser_mode=False):
    assert not browser_mode
    import cp6_bf_probe as bf
    import cp6_auditor_runner as runner
    import cp6_auditor_modes as modes
    import probe
    groups=dict(native=runner.strict_group('INDEPENDENT_ACCEPTANCE_CP6',probe.cases,bf.verified))
    groups['races']=modes.run_races(probe,bf.verified,'independent_acceptance')
    status='PASS' if all(x.get('status') in ('PASS','RUN_COMPLETE') and set(x.get('counts',{}))=={'PASS'}
        and x['counts']['PASS']>0 and x.get('database_remaining',0)==0 for x in groups.values()) else 'INCOMPLETE'
    result=dict(label='INDEPENDENT_ACCEPTANCE_CP6',status=status,independent_acceptance=False,
        groups={k:{field:v.get(field) for field in ('status','counts','database_remaining','error','cleanup')} for k,v in groups.items()})
    print(json.dumps(result,default=str),flush=True)
    return result

package._writer_runtime=runtime
if __name__=='__main__':package.run('install')
