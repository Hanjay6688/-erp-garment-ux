"""INTERNAL WRITER PROPOSAL, not installed ERP code or Native evidence.
Expected fixtures are declared before the planner. All amounts are exact cents.
A source event is an immutable journal contribution with its actual two dates.
The proposed return-book floor must be proven by a real posting boundary; this
model does not authorize moving any existing source journal or an open period.
"""
from decimal import Decimal
import json


def event(key, kind, amount, economic, book):
    return dict(key=key, kind=kind, amount=amount, economic=economic, book=book)


# Literal oracles written before the algorithm. Dates abbreviate 2026-10-DD.
CASES = [
    dict(name='A_future_cash', before=[event('sale','NET','1000',18,18), event('pay','FUNDING','1000',20,20)],
         added=event('return','NET','-200',19,19), expected=[('200',20,20)], balances={19:('800','0'),20:('0','200')}),
    dict(name='B_split_cash', before=[event('sale','NET','1000',18,18),event('payA','FUNDING','900',18,18),event('payB','FUNDING','100',20,20)],
         added=event('return','NET','-200',19,19), expected=[('100',19,19),('100',20,20)], balances={19:('0','100'),20:('0','200')}),
    dict(name='reopened_full', before=[event('sale','NET','1000',18,18),event('pay','FUNDING','1000',18,20)],
         added=event('return','NET','-200',19,19),expected=[('200',19,20)],
         economic={19:('0','200'),20:('0','200')},book={19:('800','0'),20:('0','200')}),
    dict(name='reopened_split', before=[event('sale','NET','1000',18,18),event('payA','FUNDING','900',18,20),event('payB','FUNDING','100',20,20)],
         added=event('return','NET','-200',19,19),expected=[('100',19,20),('100',20,20)],
         economic={19:('0','100'),20:('0','200')},book={19:('800','0'),20:('0','200')}),
    dict(name='crossing_funding_book_order',before=[event('sale','NET','1000',17,17),event('payA','FUNDING','900',18,21),event('payB','FUNDING','100',19,19)],
         added=event('return','NET','-200',20,20),expected=[('200',20,21)],
         economic={20:('0','200'),21:('0','200')},book={20:('700','0'),21:('0','200')}),
    dict(name='funding_reversal_already_recorded',before=[event('sale','NET','1000',18,18),event('payA','FUNDING','900',18,18),
          event('payB','FUNDING','100',18,18),event('reverseB','FUNDING','-100',20,20)],
         added=event('return','NET','-200',19,19),expected=[('200',19,19),('-100',20,20)],
         balances={19:('0','200'),20:('0','100')}),
    dict(name='sale_book_floor_bound',before=[event('sale','NET','1000',18,20),event('pay','FUNDING','900',18,20)],
         added=event('return','NET','-200',19,20),expected=[('100',19,20)],
         economic={19:('0','100'),20:('0','100')},book={19:('0','0'),20:('0','100')}),
    dict(name='sale_book_floor_missing_refused',before=[event('sale','NET','1000',18,20),event('pay','FUNDING','900',18,20)],
         added=event('return','NET','-200',19,19),expected_error='SOURCE_NET_BEFORE_SALE'),
    dict(name='crossing600_400_funding',before=[event('sale','NET','1000',17,17),event('payA','FUNDING','600',18,22),event('payB','FUNDING','400',20,20)],
         added=event('return','NET','-200',19,19),expected=[('200',20,22)],
         economic={19:('200','0'),20:('0','200'),22:('0','200')},book={19:('800','0'),20:('400','0'),22:('0','200')}),
    dict(name='signed_without_reversals',before=[event('sale','NET','1000',17,17),event('earlierReturn','NET','-600',17,17),
         event('payA','FUNDING','600',18,20),event('payB','FUNDING','400',19,19)],
         added=event('return','NET','-200',17,17),expected=[('200',18,20),('200',19,19),('-200',19,20)]),
    dict(name='zero_current_nonempty_recognition',before=[event('sale','NET','1000',18,18),event('pay','FUNDING','1000',18,18),
         event('reversePay','FUNDING','-1000',20,20)],added=event('return','NET','-200',19,19),
         expected=[('200',19,19),('-200',20,20)],balances={19:('0','200'),20:('800','0')}),
    dict(name='other_return_boundary',before=[event('sale','NET','1000',18,18),event('pay','FUNDING','900',18,18),event('earlierEnteredReturn','NET','-100',20,20)],
         added=event('return','NET','-200',19,19),expected=[('100',19,19),('100',20,20)],balances={19:('0','100'),20:('0','200')}),
    dict(name='cohort_joint_capacity',before=[event('sale','NET','1000',17,17),event('payA','FUNDING','900',18,18),event('payB','FUNDING','100',21,21),
         event('earlierEnteredReturn','NET','-100',20,22)],added=event('return','NET','-200',19,19),
         expected=[('100',19,19),('100',20,22),('100',21,21),('-100',21,22)]),
    dict(name='unpaid',before=[event('sale','NET','1000',18,18)],added=event('return','NET','-200',19,19),
         expected=[],balances={19:('800','0'),20:('800','0')}),
    dict(name='exact_cents',before=[event('sale','NET','1000.01',18,18),event('pay','FUNDING','900.01',18,18)],
         added=event('return','NET','-200.01',19,19),expected=[('100.01',19,19)],balances={19:('0','100.01')}),
]


def cents(value):
    number=Decimal(value)
    if not number.is_finite() or number*100!=(number*100).to_integral_value():
        raise ValueError('EXACT_CENTS_REQUIRED')
    return int(number*100)


def text(value):
    return format(Decimal(value)/100,'f').rstrip('0').rstrip('.') if value%100 else str(value//100)


def overflow(events,e,b):
    visible=[x for x in events if x['economic']<=e and x['book']<=b]
    net=sum(cents(x['amount'])for x in visible if x['kind']=='NET')
    funding=sum(cents(x['amount'])for x in visible if x['kind']=='FUNDING')
    if net<0:raise ValueError('SOURCE_NET_BEFORE_SALE')
    if funding<0:raise ValueError('NEGATIVE_SOURCE_FUNDING')
    return max(0,funding-net)


def plan(before,added):
    after=before+[added]
    assert len({x['key']for x in after})==len(after)
    assert all(x['kind']in('NET','FUNDING')and x['book']>=x['economic']for x in after)
    economics=sorted({x['economic']for x in after});books=sorted({x['book']for x in after})
    # Difference between two FULL source projections; issued credit is never
    # counted as funding and is never subtracted a second time in this model.
    values={}
    components=[]
    for i,e in enumerate(economics):
        for j,b in enumerate(books):
            current=overflow(after,e,b)-overflow(before,e,b)
            assert current>=0, 'A new positive return cannot remove previously issued capacity'
            values[i,j]=current
            amount=current-values.get((i-1,j),0)-values.get((i,j-1),0)+values.get((i-1,j-1),0)
            if amount:
                assert b>=e, 'Book date must not precede the economic date'
                components.append(dict(amount=text(amount),economic=e,book=b))
    assert sum(cents(x['amount'])for x in components)==values[len(economics)-1,len(books)-1]
    for i,e in enumerate(economics):
        for j,b in enumerate(books):
            assert sum(cents(x['amount'])for x in components if x['economic']<=e and x['book']<=b)==values[i,j]
    return components


def balance(events,components,axis,day):
    raw=sum(cents(x['amount'])*(1 if x['kind']=='NET'else-1)for x in events if x[axis]<=day)
    issue=sum(cents(x['amount'])for x in components if x[axis]<=day)
    return text(raw+issue),text(issue)


def run():
    results=[]
    for c in CASES:
        try:components=plan(c['before'],c['added'])
        except ValueError as exc:
            assert str(exc)==c.get('expected_error'),(c['name'],str(exc))
            results.append(dict(name=c['name'],status='EXPECTED_REFUSAL',reason=str(exc)));continue
        assert 'expected_error'not in c,c['name']
        expected=[dict(amount=v,economic=e,book=b)for v,e,b in c['expected']]
        assert components==expected,(c['name'],components,expected)
        all_sources=c['before']+[c['added']]
        profiles={}
        for axis in('economic','book'):
            profiles[axis]={}
            for day,want in c.get(axis,c.get('balances',{})).items():
                observed=balance(all_sources,components,axis,day)
                assert observed==want,(c['name'],axis,day,observed,want)
                profiles[axis][day]=dict(AR=observed[0],issued_credit=observed[1])
        results.append(dict(name=c['name'],status='MODEL_MATCHES_LITERAL_EXPECTED',components=components,profiles=profiles))
    return dict(classification='INTERNAL_WRITER_TWO_AXIS_COMPONENT_PROPOSAL',source_candidate='754f387a04a6b81a8b750db24184444a41bec9df',
                native_executed=False,production_planner_implemented=False,source_journals_modified=False,results=results)


if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
