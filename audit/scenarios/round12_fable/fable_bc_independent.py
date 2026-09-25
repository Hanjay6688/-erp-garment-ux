"""Fable BC T1 independent rerun (round 12) on the writer's tool head (product 27e1a05). Label T1_FAMILY / AUDITOR_SCENARIO, never release evidence.
Runs the writer's own BC PLAN unchanged (44 cases, before and after) and appends Fable cases whose oracles come from the contract and
Fable's pre-code C6 oracles (out/fable_c6_75_oracles_pre_code.md), written without adopting the writer's expected values:
  FAB:BC_FILL_BEFORE_RECEIPT_REFUSED    M:5020 A ("backdated transfer tidak mengubah ... secara semu") + no negative stock at any date: a service-post
                                        fill dated before the warehouse receipt is refused; warehouse and post stock unchanged.
  FAB:BC_USE_EXCEEDS_POST_REFUSED       ACC-D01 family fail-closed: internal use of 25 from a post holding 20 is refused atomically; exactly 20 is
                                        accepted (post 0); one more is refused. No silent capping.
  FAB:BC_INVALID_QTY_FORMS_REFUSED      M:5023 C (PCS authoritative, whole): qty '0', '-5', '1.5', 'abc', '1e2', '' on FILL_POST are refused; nothing moves.
  FAB:BC_DOUBLE_REVERSE_REFUSED         M §6.3 linked inverse: reverse restores stock and books exactly; a second reversal of the same document is refused.
  FAB:V265_V255_BODY_FINGERPRINT        F1/F2 source fingerprints from pg_proc in both phases: sha256 of run_v265 (and of it with the BC predicate reverted)
                                        and of run_v255; compared offline (v265 must differ only by the manual-price predicate; v255 identical).
Phase before: the four service cases are NO_ROUTE (no facade); the fingerprint case runs in both phases.
This script changes no product, SQL or writer checkout file.
"""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import argparse,hashlib,sys,uuid
import psycopg
sys.path.insert(0,str((Path.cwd().parent/'auditor'/'scripts').resolve()))
import cp6_bc_probe as bc
D=Decimal;api=bc.api
BC_PRED="(m.material_type='ACCESSORY' and i.accessory_price_version_id is null and i.manual_retail_unit_price is null)"
BASE_PRED="(m.material_type='ACCESSORY' and i.accessory_price_version_id is null)"

def attempt(cur,fn):
    result,error=bc.r1.peer.attempt(cur,fn);return result,error
def stocks(cur,fx):
    return {k:str(bc.stock(cur,fx['material'],fx[k])) for k in ('main','SERVICE_POST') if k in fx}

def fab_fill_before_receipt(cur,today):
    fx=bc.fixture(cur,today)
    if not bc.bc_installed(cur):return bc.no_route(cur,lambda:bc.fill(cur,fx,10,fx['received']-timedelta(days=1)))
    before=stocks(cur,fx);b0=bc.ledger(cur)
    result,error=attempt(cur,lambda:bc.fill(cur,fx,10,fx['received']-timedelta(days=1)))
    after=stocks(cur,fx)
    return bc.verdict(dict(refused=error is not None,stock_unchanged=after==before,books_unchanged=bc.delta(b0,bc.ledger(cur))=={}),refusal=error,result=result,stock=after)

def fab_use_exceeds_post(cur,today):
    fx=bc.fixture(cur,today);d=today-timedelta(days=2)
    if not bc.bc_installed(cur):return bc.no_route(cur,lambda:bc.fill(cur,fx,20,d))
    bc.fill(cur,fx,20,d)
    s1=stocks(cur,fx)
    r_over,e_over=attempt(cur,lambda:bc.use(cur,fx,fx['SERVICE_POST'],[(25,d+timedelta(days=1),10,'FACTORY_USE')]))
    s2=stocks(cur,fx)
    r_exact,e_exact=attempt(cur,lambda:bc.use(cur,fx,fx['SERVICE_POST'],[(20,d+timedelta(days=1),11,'FACTORY_USE')]))
    s3=stocks(cur,fx)
    r_one,e_one=attempt(cur,lambda:bc.use(cur,fx,fx['SERVICE_POST'],[(1,d+timedelta(days=1),12,'FACTORY_USE')]))
    s4=stocks(cur,fx)
    return bc.verdict(dict(post_holds_20=s1.get('SERVICE_POST','').startswith('20'),over_refused=e_over is not None,over_left_post_unchanged=s2==s1,
                           exact_accepted=e_exact is None,post_zero_after_exact=D(s3.get('SERVICE_POST','-1'))==0,one_more_refused=e_one is not None,
                           nothing_after_refusal=s4==s3),refusals=dict(over=e_over,one=e_one),stock=dict(s1=s1,s2=s2,s3=s3,s4=s4))

def fab_invalid_qty_forms(cur,today):
    fx=bc.fixture(cur,today);d=today-timedelta(days=2)
    if not bc.bc_installed(cur):return bc.no_route(cur,lambda:bc.fill(cur,fx,'0',d))
    before=stocks(cur,fx);b0=bc.ledger(cur);out={}
    for form in ('0','-5','1.5','abc','1e2',''):
        result,error=attempt(cur,lambda form=form:bc.svc(cur,'FILL_POST',dict(from_location_id=fx['main'],to_location_id=fx['SERVICE_POST'],physical_at=bc.local_at(d,9),
                                              items=[dict(material_id=fx['material'],qty=form)],reason='FAB invalid qty')))
        out[form or '<empty>']=dict(refused=error is not None,message=((error or {}).get('message') or '')[:120],result=None if error else str(result)[:80])
    return bc.verdict(dict(all_refused=all(v['refused'] for v in out.values()),stock_unchanged=stocks(cur,fx)==before,books_unchanged=bc.delta(b0,bc.ledger(cur))=={}),forms=out)

def fab_double_reverse(cur,today):
    fx=bc.fixture(cur,today);d=today-timedelta(days=2)
    if not bc.bc_installed(cur):return bc.no_route(cur,lambda:bc.fill(cur,fx,20,d))
    s0=stocks(cur,fx);b0=bc.ledger(cur)
    f=bc.fill(cur,fx,20,d);s1=stocks(cur,fx)
    r1_,e1=attempt(cur,lambda:bc.reverse(cur,f['document_id']));s2=stocks(cur,fx)
    r2_,e2=attempt(cur,lambda:bc.reverse(cur,f['document_id']));s3=stocks(cur,fx)
    return bc.verdict(dict(fill_moved_20=s1!=s0,first_reverse_ok=e1 is None,stock_restored=s2==s0,books_restored=bc.delta(b0,bc.ledger(cur))=={},
                           second_reverse_refused=e2 is not None,nothing_after_second=s3==s2),refusal_second=e2,stock=dict(s0=s0,s1=s1,s2=s2,s3=s3))

def fab_fingerprint(cur,today):
    api.admin(cur)
    def src(name):
        return cur.execute("select p.prosrc from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='erp' and p.proname=%s",(name,)).fetchone()[0]
    v265=src('run_v265_gudang_write_integrity_checks');v255=src('run_v255_material_cost_integrity_checks')
    sha=lambda t:hashlib.sha256(t.encode()).hexdigest()
    return dict(status='PASS',bc_installed=bc.bc_installed(cur),v265_sha=sha(v265),v265_has_bc_predicate=BC_PRED in v265,v265_has_base_predicate=BASE_PRED in v265,
                v265_normalized_sha=sha(v265.replace(BC_PRED,BASE_PRED)),v255_sha=sha(v255),v265_len=len(v265),v255_len=len(v255))

FABLE=[('FAB:BC_FILL_BEFORE_RECEIPT_REFUSED','NO_ROUTE',fab_fill_before_receipt),
       ('FAB:BC_USE_EXCEEDS_POST_REFUSED','NO_ROUTE',fab_use_exceeds_post),
       ('FAB:BC_INVALID_QTY_FORMS_REFUSED','NO_ROUTE',fab_invalid_qty_forms),
       ('FAB:BC_DOUBLE_REVERSE_REFUSED','NO_ROUTE',fab_double_reverse),
       ('FAB:V265_V255_BODY_FINGERPRINT','PASS',fab_fingerprint)]

def main(phase):
    n=len(bc.PLAN);ids={k for k,_,_ in bc.PLAN}
    assert len(ids)==n,('BC_ORIGINAL_DUPLICATE_CASE_ID',n)
    print({'fable_bc_wrapper':True,'writer_plan_cases':n,'fable_cases':len(FABLE)},flush=True)
    for key,before,fn in FABLE:
        assert key not in ids
        bc.PLAN.append((key,before,fn))
    bc.run(phase)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=('before','after'),required=True);main(p.parse_args().phase)
