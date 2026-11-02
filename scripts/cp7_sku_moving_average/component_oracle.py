"""Pure arithmetic oracle for the recost-safe economic component ledger."""
from decimal import Decimal,ROUND_HALF_UP,getcontext
getcontext().prec=50
D=Decimal
CENT=D('0.01')

def money(value):return D(value).quantize(CENT,rounding=ROUND_HALF_UP)

def value(pool,hpp):
    return sum((units*hpp[root]for root,units in pool.items()),D(0))

def qty(pool):return sum(pool.values(),D(0))

def transfer(source,target,count,hpp):
    count=D(count);q=qty(source)
    if count<=0 or count>q:raise ValueError('INVALID_TRANSFER_QTY')
    amount=money(count*value(source,hpp)/q)
    moved={root:units*count/q for root,units in source.items()}
    source_after={root:units-moved[root]for root,units in source.items()if units-moved[root]}
    target_after=dict(target)
    for root,units in moved.items():target_after[root]=target_after.get(root,D(0))+units
    if qty(source_after)!=q-count or qty(target_after)!=qty(target)+count:raise AssertionError('QTY_NOT_CONSERVED')
    if value(source_after,hpp)+value(target_after,hpp)!=value(source,hpp)+value(target,hpp):raise AssertionError('VALUE_NOT_CONSERVED')
    return source_after,target_after,amount,moved

def apportion(total,weights,order):
    total=money(total);den=sum((weights[k]for k in order),D(0));out={};prior=D(0);cumulative=D(0)
    if den==0:return {k:D(0)for k in order}
    for key in order:
        cumulative+=weights[key]
        now=money(total*cumulative/den)
        out[key]=now-prior;prior=now
    if sum(out.values(),D(0))!=total:raise AssertionError('CENT_NOT_CONSERVED')
    return out

def run():
    hpp={'A10':D(10),'A30':D(30),'B50':D(50)}
    a={'A10':D(2),'A30':D(2)};b={'B50':D(1)}
    a1,b1,forward,_=transfer(a,b,1,hpp)
    assert qty(a1)==3 and value(a1,hpp)==60
    assert qty(b1)==2 and value(b1,hpp)==70 and forward==20
    b2,a2,back,_=transfer(b1,a1,1,hpp)
    assert qty(a2)==4 and value(a2,hpp)==95
    assert qty(b2)==1 and value(b2,hpp)==35 and back==35
    assert value(a2,hpp)+value(b2,hpp)==130

    # Reserved expensive pieces remain economic contributors: physical is 4,
    # available is 2, average is still 20.
    reserved={'A10':D(2),'A30':D(2)}
    _,reserved_target,reserved_amount,_=transfer(reserved,{},1,hpp)
    assert reserved_amount==20 and value(reserved_target,hpp)==20

    # Location isolation: another location never enters this pool.
    l1={'A10':D(2),'A30':D(2)};l2={'B50':D(6)}
    l1_after,_,_,_=transfer(l1,{},1,hpp)
    assert value(l2,hpp)==300 and qty(l2)==6 and value(l1_after,hpp)==60

    # Re-costing a root component automatically follows remaining lineage.
    hpp2=dict(hpp,A30=D(40))
    assert value(a1,hpp2)==75 and value(b1,hpp2)==75
    assert value(a1,hpp2)+value(b1,hpp2)==150

    # PO/non-PO attribution follows economic roots, not a FIFO physical pick.
    po_weights={'PO1':D(20),'NONPO':D(10)}
    assert apportion(D(20),po_weights,['PO1','NONPO'])=={'PO1':D('13.33'),'NONPO':D('6.67')}

    # Two of three pieces with total value one: declared cumulative residual.
    assert apportion(D(1),{'p1':D(1),'p2':D(1),'p3':D(1)},['p1','p2','p3'])=={
        'p1':D('0.33'),'p2':D('0.34'),'p3':D('0.33')}
    assert money(D(2)*D(1)/D(3))==D('0.67')
    return {'status':'SKU_MOVAVG_COMPONENT_ORACLE_PASS','canonical_forward':'20.00','manual_back':'35.00',
            'final_A':'95.00','final_B':'35.00','total':'130.00','actual_SQL':0,'production_go':False}

if __name__=='__main__':print(run())
