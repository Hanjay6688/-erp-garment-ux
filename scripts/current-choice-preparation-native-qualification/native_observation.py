"""Native observation adapters; no product, permission or timeout changes."""
from copy import deepcopy
from pathlib import Path
import ast,inspect
import cp7_ow12b_choice_preparation_cases as B
plan,call,work=B.plan,B.call,B.work


def check_ready_get(cur,f,result,actual):
    # Independently reconstruct the signed advisory key, including backend PID.
    # STEP holds its xact lock until this Native case rolls back. GET exposes
    # that real lock even after READY; separate HTTP transactions do not retain it.
    own,foreign=cur.execute("""
        select count(*) filter(where pid=pg_backend_pid()),
               count(*) filter(where pid<>pg_backend_pid())
        from pg_catalog.pg_locks
        where locktype='advisory' and granted and mode='ExclusiveLock' and objsubid=1
          and database=(select oid from pg_catalog.pg_database where datname=current_database())
          and ((classid::bigint<<32)|objid::bigint)=
              pg_catalog.hashtextextended('CP7:FROZEN_CHOICE_PREP:'||%s::text,0)
    """,(f['row']['id'],)).fetchone()
    assert (own,foreign)==(1,0),('CHOICE_READY_NATIVE_LOCK_MISMATCH',own,foreign)
    assert result['state']=='READY' and result['worker_active'] is False,result
    expected=dict(result,worker_active=True)
    assert actual==expected,('CHOICE_READY_GET_EXACT_MISMATCH',actual,expected)
    return dict(own_transaction_locks=own,foreign_transaction_locks=foreign,
                STEP_worker_active=False,GET_worker_active=True,all_other_fields_exact=True)


def check_claims(before,after,effective_before,effective_after):
    # run_next explicitly uses coalesce(prior_value,'') for each custom GUC.
    # Keep that explicit empty representation in the raw observations; require
    # exact non-null values AND auth.uid/jwt parity, never ignore a claim column.
    assert len(before)==len(after)==3
    expected=tuple('' if value is None else value for value in before)
    assert tuple(after)==expected,('CHOICE_RUNNER_RAW_CLAIMS_CHANGED',before,after,expected)
    assert effective_before==effective_after,('CHOICE_RUNNER_EFFECTIVE_IDENTITY_CHANGED',effective_before,effective_after)
    return dict(raw_before=list(before),raw_after=list(after),
        initially_undefined_to_empty=[i for i,value in enumerate(before) if value is None],
        all_nonnull_caller_values_exact=True,effective_auth_uid_jwt_equal=True)


def ready(cur,f,observed):
 # Reuse timings already collected by the real staged driver. No additional
 # reads or compiler calls for instrumentation. These are unit-call durations
 # (including fixture actor/setup overhead), not whole-analysis wall time.
 calls=deepcopy(f['calls']);assert calls
 by_stage={}
 for row in calls:
  group=by_stage.setdefault(row['stage'],dict(calls=0,total_millis=0,slowest_millis=0))
  group['calls']+=1;group['total_millis']+=row['ms'];group['slowest_millis']=max(group['slowest_millis'],row['ms'])
 for group in by_stage.values():group['total_millis']=round(group['total_millis'],3)
 observed.setdefault('completed_analysis_unit_timings',[]).append(dict(
  source_request=f['key'],run_id=f['done']['run_id'],targets=f['pages']['targets_total'],
  units_done=f['done']['units_done'],unit_count=f['done']['unit_count'],calls=calls,by_stage=by_stage,
  unit_calls_total_millis=round(sum(row['ms']for row in calls),3),
  includes_fixture_role_setup_overhead=True,whole_analysis_wall_time=False,
  added_database_calls=0,total8s_gate=False))
 before=plan.staged.job_row(cur,f['key'],f['subject'])
 first=call(cur,'request',f,observed);assert first['state']=='QUEUED'
 assert call(cur,'request',f,observed)==first and call(cur,'get',f,observed)==first
 result=call(cur,'step',f,observed);assert result['state']=='READY'
 assert work(cur,f)['payload']['inputs']==f['expected']
 assert call(cur,'step',f,observed)==result
 actual=call(cur,'get',f,observed)
 observed.setdefault('READY_same_transaction_lock',[]).append(check_ready_get(cur,f,result,actual))
 assert plan.staged.job_row(cur,f['key'],f['subject'])==before
 return result


def verify_ready_source():
    original=inspect.getsource(B.ready).strip()
    old=" assert call(cur,'step',f,observed)==result and call(cur,'get',f,observed)==result\n"
    new=" assert call(cur,'step',f,observed)==result\n actual=call(cur,'get',f,observed)\n observed.setdefault('READY_same_transaction_lock',[]).append(check_ready_get(cur,f,result,actual))\n"
    assert original.count(old)==1,'RETAINED_B_READY_ANCHOR_CHANGED'
    expected=ast.parse(original.replace(old,new))
    assert ast.dump(expected)==ast.dump(ast.parse(inspect.getsource(ready).strip())),'RETAINED_B_READY_ASSERTIONS_CHANGED'
    return dict(original_B_ready_body_retained=True,changed_GET_lock_assertions=1,
                separate_HTTP_replay_contract_unchanged=True)
