"""OW-08a Native cases: report readiness after actual OW04 customer credit.

Credit is created and used only through the retained OW04 owning writers
(return, APPLY, UNDO, refund). Each case runs in its own savepoint. Explicit
corruption is privileged, inside a nested savepoint, and always rolled back.
The original (pre-OW-08a) readers are run side by side on the same state.
"""
from decimal import Decimal as D
import time
import uuid

import cp7_ow04_consumer_fixture as fixture
import native_basic_cases as basic

native=fixture.native
IDS=('OW08A_NO_CREDIT_STATE_UNCHANGED',
     'OW08A_CREDIT_ISSUED_AND_APPLIED_READY',
     'OW08A_REFUND_READY',
     'OW08A_APPLY_UNDO_READY',
     'OW08A_REAL_DIFFERENCES_STILL_CAUGHT',
     'OW08A_UNPROVEN_CREDIT_BLOCKS_WITHOUT_ERROR')
AR=('V2620H_CUSTOMER_AR_BY_CUSTOMER_MISMATCH','V2620H_CUSTOMER_AR_STATUS_MISMATCH','V268_AR_GL_SUBLEDGER_MISMATCH')
UNPROVEN='CP7_CUSTOMER_CREDIT_REPORT_UNPROVEN'
ORIGINALS=None  # set by the probe: the exact pre-OW-08a definitions it replaced
AS_OWNER=None   # set by the probe: the verified predecessor role switch


def rows(cur):
    native.b.api.admin(cur)
    return {r[0]:(r[1],int(r[2]))for r in cur.execute(
        'select check_name,severity,issue_count from erp.run_v268_financial_report_checks()').fetchall()}


def critical(found):
    return {k:v[1]for k,v in found.items()if v[0]=='CRITICAL'and v[1]>0}


def ar(found):
    return {k:found[k][1]for k in AR}


def original_rows(cur):
    """The same state read by the exact replaced definitions, then restored."""
    name='ow08a_original_'+uuid.uuid4().hex
    cur.execute('savepoint '+name)
    try:
        with AS_OWNER(cur,'postgres'):
            for definition in ORIGINALS.values():cur.execute(definition,prepare=False)
        started=time.perf_counter();found=rows(cur);elapsed=time.perf_counter()-started
        return found,elapsed
    finally:
        cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);native.b.api.admin(cur)


def timed(cur):
    started=time.perf_counter();found=rows(cur)
    return found,time.perf_counter()-started


def side_by_side(cur):
    new,new_s=timed(cur);old,old_s=original_rows(cur)
    assert new[UNPROVEN]==('CRITICAL',0),new[UNPROVEN]
    differing=sorted(k for k in set(new)|set(old)if k!=UNPROVEN and new.get(k)!=old.get(k))
    return new,old,differing,dict(new_seconds=round(new_s,3),original_seconds=round(old_s,3))


def tamper(cur,label,statement,args,table):
    """Privileged corruption: direct first; owner-disabled user triggers only if refused."""
    name='ow08a_tamper_'+uuid.uuid4().hex
    cur.execute('savepoint '+name)
    try:
        cur.execute(statement,args);return 'DIRECT'
    except Exception:
        cur.execute('rollback to savepoint '+name)
        cur.execute('alter table '+table+' disable trigger user')
        cur.execute(statement,args)
        cur.execute('alter table '+table+' enable trigger user')
        return 'USER_TRIGGERS_DISABLED_FOR_ONE_STATEMENT'
    finally:
        cur.execute('release savepoint '+name)


def cases(cur,today):
    def unchanged():
        with native.isolated(cur):
            new,old,differing,timing=side_by_side(cur)
            assert differing==[],differing
            return dict(status='PASS',critical_now=critical(new),identical_to_original_except_new_zero_check=True,
                check_rows=len(new),timing=timing)

    def applied():
        with native.isolated(cur):
            before=critical(rows(cur))
            assert before=={},('BASE_NOT_READY',before)
            pair=fixture.prepare(cur,today,'CREDIT')
            issued,old_issued,differing_issued,_=side_by_side(cur)
            assert critical(issued)=={},critical(issued)
            first,_,_=basic.apply(cur,pair,'80.00');second,_,_=basic.apply(cur,pair,'120.00')
            profile=fixture.profiles(cur,pair)
            assert profile['target']['U']=='200.00'and profile['target']['AR']=='300.00'and profile['source']['available_credit']=='0.00',profile
            after,old_after,differing_after,timing=side_by_side(cur)
            assert critical(after)=={},critical(after)
            assert any(old_after[k][1]>0 for k in AR),('ORIGINAL_READERS_DID_NOT_REPRODUCE_BLOCK',ar(old_after))
            assert set(differing_after)<=set(AR),differing_after
            return dict(status='PASS',profile=profile,critical_after_issue=critical(issued),critical_after_two_uses=critical(after),
                original_readers_after_issue=ar(old_issued),original_readers_after_uses=ar(old_after),
                only_three_AR_checks_differ=differing_after,timing=timing)

    def refund():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today,'REFUND')
            after,old,differing,timing=side_by_side(cur)
            assert critical(after)=={},critical(after)
            assert set(differing)<=set(AR),differing
            return dict(status='PASS',profile=fixture.profiles(cur,pair),critical=critical(after),original_readers=ar(old),timing=timing)

    def undo():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today,'CREDIT')
            first,_,_=basic.apply(cur,pair,'80.00')
            envelope=basic.review(cur,basic.payload(pair,'UNDO',original=first['consumption_event_id']))
            undone=basic.command(cur,envelope,uuid.uuid4())
            assert undone['amount']=='-80.00'
            profile=fixture.profiles(cur,pair)
            assert profile['target']['U']=='0.00'and profile['target']['AR']=='500.00'and profile['source']['available_credit']=='200.00',profile
            after,old,differing,timing=side_by_side(cur)
            assert critical(after)=={},critical(after)
            return dict(status='PASS',profile=profile,critical=critical(after),original_readers=ar(old),timing=timing)

    def caught():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today,'CREDIT');basic.apply(cur,pair,'80.00')
            assert critical(rows(cur))=={}
            target=pair['target']['sale'];customer=pair['target']['customer']
            observed={}
            # 1. Header says fully paid while E=80 of 500.
            name='ow08a_status';cur.execute('savepoint '+name)
            how=tamper(cur,'status',"update erp.sales_headers set status='PAID' where id=%s",(target,),'erp.sales_headers')
            found=rows(cur);observed['status']=dict(how=how,ar=ar(found),unproven=found[UNPROVEN][1])
            assert found['V2620H_CUSTOMER_AR_STATUS_MISMATCH'][1]>=1,observed
            cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name)
            # 2. One cent more on the target customer's AR GL line (balanced journal).
            line,other=cur.execute("""select a.id,b.id from erp.journal_entries j
              join erp.journal_lines a on a.journal_entry_id=j.id and a.customer_id=%s and a.debit>0
               and a.account_id=%s
              join erp.journal_lines b on b.journal_entry_id=j.id and b.credit>0
              where j.source_type='SALE'and j.source_id=%s and j.reversal_of_id is null order by b.id limit 1""",(customer,pair['ar']['target'],target)).fetchone()
            name='ow08a_gl';cur.execute('savepoint '+name)
            how=tamper(cur,'gl','update erp.journal_lines set debit=debit+0.01 where id=%s',(line,),'erp.journal_lines')
            tamper(cur,'gl','update erp.journal_lines set credit=credit+0.01 where id=%s',(other,),'erp.journal_lines')
            found=rows(cur);observed['gl']=dict(how=how,ar=ar(found),unproven=found[UNPROVEN][1])
            assert found['V2620H_CUSTOMER_AR_BY_CUSTOMER_MISMATCH'][1]>=1,observed
            cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name)
            assert critical(rows(cur))=={},'TAMPER_NOT_ROLLED_BACK'
            return dict(status='PASS',observed=observed,state_ready_again_after_rollback=True)

    def unproven():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today,'CREDIT');basic.apply(cur,pair,'80.00')
            assert critical(rows(cur))=={}
            link=cur.execute("""select cj.part_id,cj.journal_id from cp7_credit.component_journals cj
              join cp7_credit.component_parts q on q.id=cj.part_id join cp7_credit.recognition_components cc on cc.id=q.component_id
              join cp7_credit.recognition_plans rp on rp.id=cc.plan_id join cp7_credit.cohorts c on c.id=rp.cohort_id
              where c.id=%s order by cj.part_id limit 1""",(pair['initial_result']['credit_id'],)).fetchone()
            name='ow08a_unproven';cur.execute('savepoint '+name)
            how=tamper(cur,'unproven','delete from cp7_credit.component_journals where part_id=%s and journal_id=%s',link,'cp7_credit.component_journals')
            error=None;cur.execute('savepoint ow08a_core_probe')
            try:native.b.api.admin(cur);cur.execute('select erp._cp7_current_credit_adjustment(%s)',(pair['target']['sale'],))
            except Exception as e:error=getattr(getattr(e,'diag',None),'message_primary',None)or str(e)
            cur.execute('rollback to savepoint ow08a_core_probe');cur.execute('release savepoint ow08a_core_probe')
            assert error,'CORE_DID_NOT_REFUSE_UNPROVEN_PROFILE'
            found=rows(cur)
            assert found[UNPROVEN][1]>=1,found[UNPROVEN]
            observed=dict(how=how,core_error=error,unproven=found[UNPROVEN][1],ar=ar(found),critical=critical(found))
            cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name)
            assert critical(rows(cur))=={}
            return dict(status='PASS',observed=observed,report_returned_rows_instead_of_error=True)

    result=list(zip(IDS,(unchanged,applied,refund,undo,caught,unproven)))
    assert tuple(k for k,_ in result)==IDS
    return result
