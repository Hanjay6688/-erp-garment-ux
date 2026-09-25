"""Fable BC round 12, item 1: two-session races the writer's cp6_bc_modes.py does not cover, run in the auditor runtime (phase after = BC).
Oracles (contract M §6.3 linked inverse, M:5296 two-session family, no negative stock at any location/date), written before the run:
  FAB_RACE:USE_FROM_POST_VS_REVERSE_FILL  a post holds 5 (fill committed). Session 1 uses 5 from the post; session 2 reverses the fill.
      first commits -> the reversal is refused (stock at the post would go negative) and the post ends at 0 used, warehouse 2;
      first aborts  -> the reversal succeeds, warehouse back to 7, post 0. Never both.
  FAB_RACE:TWO_REVERSALS_SAME_FILL        two sessions reverse the same fill. first commits -> second refused BC_ALREADY_REVERSED; first aborts -> second succeeds.
      Either way exactly one reversal exists, warehouse 7, post 0.
  FAB_RACE:TWO_CREDITS_SAME_LOT           a note-return lot of 4 usable (policy CREDIT_UNPAID_ONLY, note unpaid). Two sessions credit 4 each.
      first commits -> second refused (credit exceeds the lot's usable), credited 4 once; first aborts -> second succeeds, credited 4 once.
Setup uses the writer's helper module (REUSED fixture code); oracles and verdicts are the auditor's. Detector findings are reported both with and
without the F2 row (D07 pending) and gate on the latter, stated openly.
"""
from datetime import timedelta
import json,uuid
import cp6_bc_probe as bcp
api=bcp.api;D=bcp.D

def _fx(tools,today,stock_qty=7):
    with tools.connect() as conn,conn.cursor() as cur:
        fx=bcp.fixture(cur,today,stock_qty=stock_qty);conn.commit()
    return fx
def _read(tools,fn):
    with tools.connect() as conn,conn.cursor() as cur:
        v=fn(cur);conn.rollback()
    return v
def _stocks(tools,fx):
    return _read(tools,lambda cur:{k:str(D(str(bcp.stock(cur,fx['material'],fx[k]))).quantize(D('0.000001'))) for k in ('main','SERVICE_POST')})
def _findings(tools):
    rows=_read(tools,bcp.findings)
    return dict(all=rows,without_f2={k:v for k,v in rows.items() if k!=bcp.STALE_F2})
def _fill_committed(tools,fx,day,qty=5):
    with tools.connect() as conn,conn.cursor() as cur:
        doc=bcp.fill(cur,fx,qty,day)['document_id'];conn.commit()
    return doc
def _verdict(name,commit,held,contention,outcome,expect_second_ok,state_ok,state,extra=None):
    second_ok=outcome.get('ok') is True
    ok=(second_ok==expect_second_ok) and state_ok
    return dict(status='PASS' if ok else 'FAIL',race=name,first_committed=commit,expected_second='SUCCEEDS' if expect_second_ok else 'REFUSED',
                held=str(held)[:300],contention=contention,second=outcome,state=state,**(extra or {}))

def use_vs_reverse(tools,today,commit):
    day=today-timedelta(days=1);fx=_fx(tools,today);doc=_fill_committed(tools,fx,day)
    def use(cur):return bcp.use(cur,fx,fx['SERVICE_POST'],[(5,day,10,'FACTORY_USE')])['document_id']
    def rev(cur):return bcp.reverse(cur,doc)['document_id']
    held,contention,outcome=tools.two_sessions(use,rev,commit)
    s=_stocks(tools,fx);f=_findings(tools)
    if commit:state_ok=s=={'main':'2.000000','SERVICE_POST':'0.000000'} and not f['without_f2']
    else:state_ok=s=={'main':'7.000000','SERVICE_POST':'0.000000'} and not f['without_f2']
    return _verdict('USE_FROM_POST_VS_REVERSE_FILL',commit,held,contention,outcome,expect_second_ok=not commit,state_ok=state_ok,state=dict(stock=s,findings=f))

def two_reversals(tools,today,commit):
    day=today-timedelta(days=1);fx=_fx(tools,today);doc=_fill_committed(tools,fx,day)
    def rev(cur):return bcp.reverse(cur,doc)['document_id']
    held,contention,outcome=tools.two_sessions(rev,rev,commit)
    s=_stocks(tools,fx);f=_findings(tools)
    n=_read(tools,lambda cur:bcp.one(cur,"select count(*) from erp.bc_documents_v1 where action='REVERSE' and payload->>'document_id'=%s",doc))
    state_ok=s=={'main':'7.000000','SERVICE_POST':'0.000000'} and int(n)==1 and not f['without_f2']
    refused_code=(outcome.get('message') or '')
    return _verdict('TWO_REVERSALS_SAME_FILL',commit,held,contention,outcome,expect_second_ok=not commit,state_ok=state_ok,
                    state=dict(stock=s,reversals=int(n),findings=f),extra=dict(second_refusal_has_code=('BC_ALREADY_REVERSED' in refused_code) if commit else None))

def two_credits(tools,today,commit):
    fx=_fx(tools,today,stock_qty=100);d=today-timedelta(days=4)
    with tools.connect() as conn,conn.cursor() as cur:
        _,item=bcp.note(cur,fx,10,'3.00',d)
        lot=bcp.receive(cur,fx,'NOTE_RETURN',day=d+timedelta(days=1),note_item_id=item,qty='4')['lot_ids'][0]
        bcp.inspect(cur,lot,bcp.local_at(d+timedelta(days=1),12),'Ani',usable=4)
        bcp.policy(cur,'ACC_DEC05',dict(mode='CREDIT_UNPAID_ONLY',credit_conditions=['USABLE']))
        conn.commit()
    at=bcp.local_at(d+timedelta(days=2),9)
    def cr(cur):return bcp.credit(cur,lot,'USABLE',4,at,fx['main'])['document_id']
    held,contention,outcome=tools.two_sessions(cr,cr,commit)
    st=_read(tools,lambda cur:{k:str(v) for k,v in bcp.lot_state(cur,lot).items()})
    f=_findings(tools)
    credited=D(st.get('credited','0'))
    state_ok=credited==4 and not f['without_f2']
    return _verdict('TWO_CREDITS_SAME_LOT',commit,held,contention,outcome,expect_second_ok=not commit,state_ok=state_ok,state=dict(lot=st,findings=f))

def races(tools,today):
    return [('FAB_RACE:USE_FROM_POST_VS_REVERSE_FILL_FIRST_COMMITS',lambda:use_vs_reverse(tools,today,True)),
            ('FAB_RACE:USE_FROM_POST_VS_REVERSE_FILL_FIRST_ABORTS',lambda:use_vs_reverse(tools,today,False)),
            ('FAB_RACE:TWO_REVERSALS_SAME_FILL_FIRST_COMMITS',lambda:two_reversals(tools,today,True)),
            ('FAB_RACE:TWO_REVERSALS_SAME_FILL_FIRST_ABORTS',lambda:two_reversals(tools,today,False)),
            ('FAB_RACE:TWO_CREDITS_SAME_LOT_FIRST_COMMITS',lambda:two_credits(tools,today,True)),
            ('FAB_RACE:TWO_CREDITS_SAME_LOT_FIRST_ABORTS',lambda:two_credits(tools,today,False))]
