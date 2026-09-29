"""Predeclared P04 PostgreSQL kernel oracles; not ERP posting/adapter acceptance."""
from copy import deepcopy
import json
import cp7_snapshot_cases as p02
import cp6_bf_probe as bf


def refs(k):return [dict(kind='PREDECLARED_KERNEL_ORACLE',id=k,revision='1')]
def graph():
    pools=[dict(key='A',size_id='31',input_pcs='60',origin='CUTTING',ownership='COMPANY',refs=refs('A')),
           dict(key='B',size_id='XS',input_pcs='40',origin='CUTTING',ownership='COMPANY',refs=refs('B'))]
    nodes=[dict(key=k,pool_key=p,stage=s,refs=refs(k)) for k,p,s in (
      ('A-sew','A','SEWING_ACTIVE'),('A-out','A','LAUNDRY_OUTSTANDING'),('A-qc','A','AWAIT_QC'),
      ('A-fg','A','FG'),('A-bs','A','BS'),('A-rework','A','REWORK'),('A-rewash','A','REWASH'),('B-sew','B','SEWING_UNRESOLVED'))]
    g=dict(contract_version='cp7.wip-graph.v1',snapshot_id='O15-100PCS',complete=True,pools=pools,nodes=nodes,events=[])
    for p,src,dst,q in [('A',None,'A-sew',60),('B',None,'B-sew',40),('A','A-sew','A-out',40),
       ('A','A-out','A-qc',30),('A','A-qc','A-fg',15),('A','A-qc','A-bs',5)]:event(g,p,src,dst,q)
    return g

def event(g,p,src,dst,q,reverse=None):
    key='e'+str(len(g['events'])+1)
    g['events'].append(dict(key=key,pool_key=p,from_node=src,to_node=dst,qty_pcs=str(q),
      ordinal=str(len(g['events'])+1),reverses_key=reverse,refs=refs(key)))

def call(cur,name,*args):
    bf.b.api.admin(cur)
    # Explicit closed kernel names, never an arbitrary function from user input.
    sql={'reconcile':'select cp7_wip.reconcile(%s::jsonb)',
      'match':'select cp7_wip.match_target(%s::jsonb,%s::jsonb)',
      'allocate':'select cp7_wip.check_allocations(%s::jsonb,%s::jsonb)',
      'eta':'select cp7_wip.remaining_eta(%s::timestamptz,%s::timestamptz,%s::jsonb)'}[name]
    return cur.execute(sql,tuple(json.dumps(x) if isinstance(x,(dict,list)) else x for x in args)).fetchone()[0]

def check(cur,fn,code):return p02.refused(cur,fn,code)

def total(r,key):return sum(int(x[key]) for x in r['totals'])
def quantities(r):return {x['key']:int(x['remaining_pcs']) for x in r['positions']}

def cases(cur,today):
    def o15():
        r=call(cur,'reconcile',graph())
        assert r['status']=='COMPLETE' and [total(r,x) for x in ['input_pcs','wip_pcs','fg_pcs','bs_pcs']]==[100,80,15,5],r
        assert quantities(r)=={'A-sew':20,'A-out':10,'A-qc':10,'A-fg':15,'A-bs':5,'A-rework':0,'A-rewash':0,'B-sew':40}
        return dict(status='PASS',expected=dict(input=100,wip=80,fg=15,bs=5),actual={x:total(r,x+'_pcs') for x in ('input','wip','fg','bs')})
    def negative():
        g=graph();event(g,'A','A-out','A-qc',11)
        r=call(cur,'reconcile',g)
        assert r['status']=='CONFLICT' and r['reason']=='NEGATIVE_PREFIX' and 'positions' not in r
        return dict(status='PASS',negative_prefix_not_clamped=True)
    def extra_input():
        g=graph();event(g,'A',None,'A-qc',30)
        r=call(cur,'reconcile',g);assert r['reason']=='INPUT_EXCEEDS_ORIGIN' and 'positions' not in r
        g=graph();g['events'][0]['qty_pcs']='59';g['events']=g['events'][:2]
        r=call(cur,'reconcile',g);assert r['status']=='UNKNOWN' and r['reason']=='ORIGIN_NOT_FULLY_ACCOUNTED'
        return dict(status='PASS',second_document_not_fresh_supply=True,missing_origin_not_zero=True)
    def rework():
        g=graph();event(g,'A','A-bs','A-rework',5)
        during=call(cur,'reconcile',g);assert [total(during,x) for x in ['input_pcs','wip_pcs','fg_pcs','bs_pcs']]==[100,85,15,0]
        event(g,'A','A-rework','A-fg',3);event(g,'A','A-rework','A-bs',2)
        r=call(cur,'reconcile',g);assert [total(r,x) for x in ['input_pcs','wip_pcs','fg_pcs','bs_pcs']]==[100,80,18,2]
        return dict(status='PASS',denominator_unchanged=100,good_return=3,bs_remaining=2)
    def rewash():
        g=graph();event(g,'A','A-qc','A-rewash',10);event(g,'A','A-rewash','A-out',10)
        event(g,'A','A-out','A-qc',10)
        r=call(cur,'reconcile',g);assert quantities(r)==quantities(call(cur,'reconcile',graph()))
        return dict(status='PASS',redispatch_is_same_pool=True,return_cycle_does_not_add_supply=True)
    def reversals():
        g=graph();event(g,'A','A-qc','A-out',30,'e4')
        assert call(cur,'reconcile',g)['reason']=='NEGATIVE_PREFIX'
        g=graph();event(g,'A','A-bs','A-qc',5,'e6');event(g,'A','A-fg','A-qc',15,'e5');event(g,'A','A-qc','A-out',30,'e4')
        r=call(cur,'reconcile',g);assert quantities(r)['A-out']==40 and total(r,'wip_pcs')==100
        event(g,'A','A-qc','A-out',30,'e4');check(cur,lambda:call(cur,'reconcile',g),'CP7_WIP_REVERSAL')
        return dict(status='PASS',downstream_must_unwind_first=True,duplicate_reversal_denied=True)
    def lineage():
        g=graph();event(g,'A','A-sew','B-sew',1);check(cur,lambda:call(cur,'reconcile',g),'CP7_WIP_LINEAGE')
        g=graph();g['events'].append(deepcopy(g['events'][-1]));check(cur,lambda:call(cur,'reconcile',g),'CP7_WIP_EVENT')
        g=graph();g['nodes'].append(deepcopy(g['nodes'][0]));check(cur,lambda:call(cur,'reconcile',g),'CP7_WIP_NODE')
        return dict(status='PASS',cross_size_pool_denied=True,duplicate_fact_denied=True)
    def partial():
        g=graph();g['complete']=False
        r=call(cur,'reconcile',g);assert r['status']=='UNKNOWN' and 'totals' not in r
        g=graph();g['pools'][0]['input_pcs']=60;check(cur,lambda:call(cur,'reconcile',g),'CP7_WIP_PCS')
        g=graph();g['pools'][0]['invoice_amount']='0';check(cur,lambda:call(cur,'reconcile',g),'CP7_WIP_FIELDS')
        return dict(status='PASS',partial_not_empty_or_zero=True,numeric_transport_and_money_extra_denied=True)
    def ownership():
        g=graph();g['pools'][0]['ownership']='CUSTOMER';g['nodes'][7]['stage']='HOLD'
        r=call(cur,'reconcile',g);assert not any(x['eligible_company_wip'] for x in r['positions'])
        assert total(r,'withheld_pcs')==40 and total(r,'input_pcs')==100
        return dict(status='PASS',custody_not_company_supply=True,hold_retained_not_available=True)
    def matching():
        s=dict(key='A-sew',quality='COMPLETE',size_id='31',confirmed_target=None,constraints=[],refs=refs('source'))
        t=dict(key='root-A:31',size_id='31',constraints=[],refs=refs('target'))
        assert call(cur,'match',s,t)['match']=='CANDIDATE_MATCH'
        s['confirmed_target']=t['key'];assert call(cur,'match',s,t)['match']=='CONFIRMED_TARGET'
        t['size_id']='XS';assert call(cur,'match',s,t)['match']=='INCOMPATIBLE';t['size_id']='31'
        s['constraints']=[dict(field='finish',value='spray',required=True,basis='HINT')]
        t['constraints']=[dict(field='finish',value='spray',required=True,basis='FACT')]
        assert call(cur,'match',s,t)['match']=='NEEDS_CHECK'
        s['constraints'][0].update(basis='FACT',value='snow');assert call(cur,'match',s,t)['match']=='INCOMPATIBLE'
        s['quality']='PARTIAL';assert call(cur,'match',s,t)['match']=='UNKNOWN'
        return dict(status='PASS',tariff_hint_not_confirmation=True,required_unknown_needs_check=True,optional_empty_not_rejected=True)
    def allocate():
        r=call(cur,'reconcile',graph())
        def edge(k,target,q):return dict(key=k,position_key='A-sew',target_key=target,size_id='31',input_pcs=str(q),projected_good_pcs=str(q),match='CANDIDATE_MATCH',refs=refs(k))
        a=dict(scenario_id='S1',scope_id='ALL-A-B',complete_scope=True,edges=[edge('1','brand-A',15),edge('2','brand-B',10)])
        result=call(cur,'allocate',r,a);assert result['status']=='INFEASIBLE' and result['violations'][0]['excess_pcs']=='5'
        a['edges']=[edge('1','brand-A',20)];assert call(cur,'allocate',r,a)['status']=='FEASIBLE'
        b=deepcopy(a);b['scenario_id']='alternative';assert call(cur,'allocate',r,b)['status']=='FEASIBLE'
        a['complete_scope']=False;assert call(cur,'allocate',r,a)['status']=='UNKNOWN'
        a['filter']='brand-A';check(cur,lambda:call(cur,'allocate',r,a),'CP7_WIP_FIELDS')
        return dict(status='PASS',shared_remaining_20_not_40=True,hidden_scope_not_reset=True,alternatives_not_summed=True)
    def timing():
        work=[dict(stage='QC',remaining_minutes='90',basis='CONFIRMED_PLAN',assumption_id=None,calendar_version='QC-calendar-v1',
          windows=[{'start':'2026-09-29T09:00:00+07:00','end':'2026-09-29T10:00:00+07:00'},
                   {'start':'2026-09-30T09:00:00+07:00','end':'2026-09-30T10:00:00+07:00'}],refs=refs('QC'))]
        r=call(cur,'eta','2026-09-29T09:00:00+07:00','2026-09-29T17:00:00+07:00',work)
        assert r['eta']=='2026-09-30T02:30:00+00:00' and not r['on_time'] and len(r['remaining_stages'])==1,r
        work[0]['remaining_minutes']=None;u=call(cur,'eta','2026-09-29T09:00:00+07:00','2026-09-30T17:00:00+07:00',work)
        assert u['status']=='UNKNOWN' and u['eta'] is None and u['on_time'] is None
        work[0].update(remaining_minutes='90',basis='ASSUMED',assumption_id='manual-ETA-1')
        r=call(cur,'eta','2026-09-29T09:00:00+07:00','2026-09-30T17:00:00+07:00',work)
        assert r['status']=='CONDITIONAL' and r['assumption_ids']==['manual-ETA-1']
        return dict(status='PASS',remaining_qc_only=True,closed_hours_not_worked=True,unknown_not_on_time=True,assumption_explicit=True)
    def large():
        g=graph();g['pools']=g['pools'][:1];g['nodes']=g['nodes'][:1];g['events']=g['events'][:1]
        g['pools'][0]['input_pcs']=g['events'][0]['qty_pcs']='9007199254740993'
        r=call(cur,'reconcile',g);assert r['positions'][0]['remaining_pcs']=='9007199254740993'
        return dict(status='PASS',integer_precision_above_javascript_safe_range=True)
    def private():
        before=bf.b.boundary.snapshot(cur)
        g=graph();p02.actor(cur)
        check(cur,lambda:(p02.actor(cur),cur.execute('select cp7_wip.reconcile(%s::jsonb)',(json.dumps(g),))), 'permission denied for schema cp7_wip')
        bf.b.api.admin(cur);cur.execute('set local role cp7_capture')
        assert cur.execute('select cp7_wip.reconcile(%s::jsonb)',(json.dumps(g),)).fetchone()[0]['status']=='COMPLETE'
        cur.execute('reset role');assert before==bf.b.boundary.snapshot(cur)
        return dict(status='PASS',api_cannot_invoke_normalized_kernel=True,compute_can_read_only=True)
    return [('P04_'+name,fn) for name,fn in [('O15_CONSERVATION',o15),('NEGATIVE_PREFIX',negative),('INPUT_UNIQUENESS',extra_input),
      ('REWORK_DENOMINATOR',rework),('REWASH_CYCLE',rewash),('REVERSAL_DEPENDENCIES',reversals),('LINEAGE_SIZE_DUPLICATE',lineage),
      ('PARTIAL_MALFORMED',partial),('OWNERSHIP_HOLD',ownership),('HARD_MATCHING',matching),('SHARED_POOL',allocate),
      ('REMAINING_ETA',timing),('EXACT_INTEGER',large),('PRIVATE_KERNEL_ACL',private)]]
