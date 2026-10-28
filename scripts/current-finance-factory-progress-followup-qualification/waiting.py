"""Read-only qualification watch; real progress, terminal states and finite wait."""
from time import monotonic,sleep

JOBS="select request_id::text,state,units_done,unit_count,plan_final,unit_attempts,failure_code from cp7_analysis_stage.jobs where request_id=any(%s::uuid[])order by request_id"
CAPTURE='select state,units_done,units_total,failure_code from cp7_finance_capture.captures where id=%s'


def observe(cur,requests,capture,report,*,now=monotonic,pause=sleep,total=900,stall=150,poll=2):
    assert len(requests)==len(set(requests))==2
    started=now();last={};changed_at={};frames=[];legacy=None
    proof=dict(read_only=True,qualification_observation_only=True,total_limit_seconds=total,
        no_progress_limit_seconds=stall,legacy_limit_seconds=300,extended_past_legacy_limit=False,
        frames=frames,manual_steps=0,minute_schedule_changed=False,ordinary_statement_limits_changed=False)
    report['factory_progress_observation']=proof
    while True:
        rows=cur.execute(JOBS,(requests,)).fetchall()
        finance=cur.execute(CAPTURE,(capture,)).fetchone()
        assert {row[0]for row in rows}==set(requests),'FACTORY_PROGRESS_EXPECTED_TWO_JOBS'
        assert finance is not None,'FACTORY_PROGRESS_CAPTURE_REQUIRED'
        elapsed=now()-started;frame={};states=[]
        for request,state,done,count,final,attempts,failure in rows:
            assert 0<=done<=count,'FACTORY_PROGRESS_COUNTER_INVALID'
            assert state in('RUNNING','DONE'),'FACTORY_PROGRESS_JOB_TERMINAL_FAILURE'
            frame[request]=(state,done,count,final);states.append((request,state))
        financial,done,count,failure=finance
        assert 0<=done<=count,'FACTORY_PROGRESS_FINANCE_COUNTER_INVALID'
        assert financial in('RUNNING','READY'),'FACTORY_PROGRESS_FINANCE_TERMINAL_FAILURE'
        frame['finance']=(financial,done,count)
        for key,current in frame.items():
            if key in last:assert current[1]>=last[key][1],'FACTORY_PROGRESS_COUNTER_REGRESSED'
            if key not in last or current!=last[key]:changed_at[key]=now()
        if frame!=last:
            frames.append(dict(elapsed_seconds=round(elapsed,3),jobs={k:list(v)for k,v in frame.items()}))
        proof.update(elapsed_seconds=round(elapsed,3),observed_job_states=dict(states),observed_finance_state=financial)
        if elapsed>=300 and legacy is None:
            legacy=dict(elapsed_seconds=round(elapsed,3),jobs={k:list(v)for k,v in frame.items()})
            proof.update(legacy_cutoff_observation=legacy,extended_past_legacy_limit=True)
        if elapsed>=total:
            proof['status']='TOTAL_OBSERVATION_LIMIT';raise AssertionError('FACTORY_PROGRESS_TOTAL_OBSERVATION_LIMIT')
        if all(state=='DONE'for _,state in states)and financial=='READY':
            proof.update(status='TERMINAL_DONE_AND_READY',actual_terminal_states_observed=True)
            return states,financial
        stalled=[key for key,current in frame.items()if current[0]=='RUNNING'and now()-changed_at[key]>=stall]
        if stalled:
            proof.update(status='NO_PROGRESS_LIMIT',stalled=stalled)
            raise AssertionError('FACTORY_PROGRESS_NO_PROGRESS_LIMIT')
        last=frame;pause(poll)
