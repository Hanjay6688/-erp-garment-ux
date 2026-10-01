"""Stop the unchanged disposable frozen bootstrap at the actual hosted v2.6.20.

The owner qualification then installs A..AB and the accepted AC..BF package.
No bootstrap or alignment script may be run against hosted.
"""
from pathlib import Path
import json,os
import cp6_t3_aligned_chain as chain
import cp6_g01_baseline as baseline

def main():
    assert os.environ.get('PGURL')=='postgresql://postgres:postgres@127.0.0.1:54322/postgres'
    out=Path(__file__).resolve().parents[1]/'cp6-proof/t3/ALIGNED_CHAIN.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    status=chain.run(str(out),baseline.STOP)
    record=json.loads(out.read_text())
    assert status==0 and record['steps'][-1]['name']==baseline.STOP and record['hosted_fingerprint']['equal']
    # The frozen helper's generic non-AC label says AB even for a custom stop.
    # Bind this receipt to the actual last executed step, not that label.
    record.update(status='PASS_ALIGNED_CHAIN_TO_V2620',actual_successor='v2.6.20',ab_installed=False,hosted_executed=False)
    out.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ('status','actual_successor','ab_installed','hosted_executed')}),flush=True)
if __name__=='__main__':main()
