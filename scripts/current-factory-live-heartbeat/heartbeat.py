"""Capture real public liveness while the scheduler is still installed."""
from datetime import datetime,timezone

def capture(cur,requests,status,report):
    assert len(requests)==len(set(requests))==2
    proof=dict(phase='SCHEDULE_INSTALLED_BEFORE_UNINSTALL',jobs={},clock='UTC',manual_ticks=0)
    report['live_runner_observation']=proof
    for key in requests:
        observed_at=datetime.now(timezone.utc).isoformat()
        job=status(cur,key)
        proof['jobs'][key]=dict(observed_at=observed_at,state=job['state'],request_id=job['request_id'],run_id=job.get('run_id'),server_runner=job['server_runner'])
        assert job['request_id']==key,'FACTORY_LIVE_REQUEST_MISMATCH'
        assert job['state']=='DONE','FACTORY_NOT_DONE_WHILE_SCHEDULED'
        assert job['server_runner']['active']is True,'FACTORY_RUNNER_INACTIVE_WHILE_SCHEDULED'
    proof['status']='PASS'
    return proof
