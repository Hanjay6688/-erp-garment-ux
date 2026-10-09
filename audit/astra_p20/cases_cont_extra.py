"""Own additional source-return, payroll identities, closed period and priority examples."""
import copy,json,uuid
from decimal import Decimal as D
import cases_business as b
import cases_cont_money as cont
import cp7_supplier_return_cases as ret
import cp7_roster_cases as roster
import cp7_attendance_write_cases as attendance
import cp7_note_correction_cases as notes
import cp7_wip_cases as wip
from cases_stage import admin,wrap,check,refusal

def cases(cur,today):
    def returned():
        f=ret.fixture(cur,today,True,qty='13',price='7.31');g=ret.fixture(cur,today,True,qty='11',price='7.31')
        d,p=ret.save(cur,f,'5');d=ret.post(cur,f,d);inputs=dict(material=f['material'],purchases=[f['receipt']['purchase_id'],g['receipt']['purchase_id']]);before=ret.credit.state(cur,inputs)
        check([D(x) for x in before['ap']]==[D('58.48'),D('80.41')] and ret.amounts(cur,f)[2]==8,'Physical five-unit return creates exact36.55credit',state=before)
        cf=dict(ret=d['return_id'],purchases=inputs['purchases']);move=ret.credit.payload(cur,cf,[(g['receipt']['purchase_id'],'36.55')]);key=uuid.uuid4();one=ret.credit.call(cur,move,key);two=ret.credit.call(cur,move,key);after=ret.credit.state(cur,inputs)
        check([D(x) for x in after['ap']]==[D('95.03'),D('43.86')],'Explicit credit belongs to selected other invoice',state=after)
        check(after['ledger']==before['ledger'] and after['values']==before['values'] and two['replayed'],'Moving/replaying existing credit creates no fresh stock or money')
        denied=refusal(cur,lambda:ret.reverse(cur,f,d));check(denied['refused'],'Cannot reverse physical source while its credit is used')
        ret.credit.call(cur,ret.credit.payload(cur,cf,[]));check(ret.credit.state(cur,inputs)==before,'Releasing credit restores exact prior AP allocation')
        ret.reverse(cur,f,d);check(ret.amounts(cur,f)[:3]==(D('95.03'),D(0),D(13)),'Inverse restores thirteen original pieces and AP')
        return dict(returned_units=5,credit='36.55',before_AP=before['ap'],after_AP=after['ap'],inverse_AP='95.03',inverse_qty=13,dependency_refusal=denied)

    def same_name():
        f=attendance.review.fixture(cur,today);admin(cur);cur.execute('update erp.contractors set attendance_required=true where id=%s',(f['contractor'],));ids=[];codes=[]
        for i,rate in enumerate(('23.17','31.29')):
            code='AS-RINA-'+uuid.uuid4().hex[:8];codes.append(code)
            made=roster.save(cur,'CREATE_WORKER',f,today,roster.initial(f,today,worker_name='Rina',worker_code=code,initial_daily_rate=rate));ids.append(made['worker_id'])
        check(len(set(ids))==2,'Same display name does not merge two worker identities')
        f['workers']=ids;doc=attendance.document(f,today);before=b.gl(cur)
        preview=attendance.command(cur,'PREVIEW',attendance.envelope(cur,f,today,doc))
        check(D(preview['estimated_amount'])==D('38.815'),'23.17 full-day plus31.29 half-day exact before cents',preview=preview)
        saved=attendance.save(cur,f,today,doc);attendance.act(cur,'POST',f,today,saved['period_id']);records=attendance.records(cur,saved['period_id'])
        check({r[1] for r in records}==set(ids) and len(records)==2,'Each mark remains attached to its code/ID',records=records)
        check(b.gl(cur)==before,'Attendance recording does not independently pay wages')
        s=attendance.s;pid=f['payroll'];s.act(cur,'PREPARE',s.doc(cur,pid));reviewed=s.doc(cur,pid)
        check(D(reviewed['labor_total'])==6000 and D(reviewed['attendance_total'])==D('38.82') and D(reviewed['net_payable'])==D('6038.82'),'Payroll adds explicit attendance amount, keeps prior work distinct',payroll=reviewed)
        key=uuid.uuid4();out=s.act(cur,'APPROVE',reviewed,key);delta=b.delta(before,b.gl(cur));expected={b.account(cur,'LABOR_COST'):D('38.82'),b.account(cur,'CONTRACTOR_PAYABLE'):D('-38.82')}
        check(delta==expected,'Exactly38.82 expense accrued once',delta=delta)
        check(s.act(cur,'APPROVE',reviewed,key)==out and b.delta(before,b.gl(cur))==expected,'Replay does not accrue identical-name workers twice')
        code_rows=cur.execute('select id::text,worker_code,worker_name from erp.contractor_workers where id=any(%s::uuid[]) order by worker_code',(ids,)).fetchall()
        check({r[1] for r in code_rows}==set(codes) and all(r[2]=='Rina' for r in code_rows),'Both original codes/name retained')
        return dict(workers=code_rows,records=records,exact_attendance='38.815',posted_attendance='38.82',work='6000',net='6038.82',journal_delta=delta)

    def closed():
        f=b.production(cur,today);f['sale_at']=b.prod.at(f['production_day'],16).isoformat();notes.posted(cur,f,'13','29.91');b.returns.payments.pay(cur,f,'137.03')
        f['allocations']=b.returns.read(cur,f)['page']['rows'];p,v=b.returns.payload(cur,f,qty='4',refund='119.64');b.cmd.command(cur,'RETURN',p,v)
        original=f['sale'];old_dates=cur.execute('select id::text,economic_date,transaction_date from erp.journal_entries where source_id=%s order by id',(original,)).fetchall()
        closed=f['production_day'];b.procurement.aa.prior.set_open_period(cur,closed);seen={x[0] for x in cur.execute('select id::text from erp.journal_entries').fetchall()};before=b.gl(cur)
        p,v=notes.edit(cur,f,qty='12');out=notes.correct(cur,p,v);f['sale']=out['sale_id'];dates=cur.execute('select id::text,economic_date,transaction_date from erp.journal_entries order by id').fetchall();new=[x for x in dates if x[0] not in seen]
        check(old_dates==cur.execute('select id::text,economic_date,transaction_date from erp.journal_entries where source_id=%s order by id',(original,)).fetchall(),'Original journal dates never rewritten')
        check(new and all(x[2]>closed for x in new) and any(x[1]==closed for x in new),'Closed economic-day correction posts GL after close while retaining economic attribution',new_dates=new,closed=closed)
        check(cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]==closed,'Correction never reopens closed book')
        check(b.fg_qty(cur,f)==33 and D(b.returns.source.read(cur,f)['detail']['financial']['open_balance'])==D('102.25'),'12sold minus4returned =8net; paid137.03 leaves102.25')
        expected={b.account(cur,'AR_CUSTOMER'):D('-29.91'),b.account(cur,'SALES_REVENUE'):D('29.91'),b.account(cur,'FG_INVENTORY'):D('16.46'),b.account(cur,'COGS'):D('-16.46')}
        check(b.delta(before,b.gl(cur))==expected,'Closed-day correction releases exactly one original16.46piece',delta=b.delta(before,b.gl(cur)))
        return dict(closed=closed,new_dates=new,FG=33,AR='102.25',journal_delta=expected)

    def priority():
        refs=lambda k:[dict(kind='ASTRA_PRIORITY_FIXTURE',id=k,revision='1')]
        graph=dict(contract_version='cp7.wip-graph.v1',snapshot_id='AS-C17',complete=True,pools=[dict(key='pool',size_id='L',input_pcs='17',origin='CUTTING',ownership='COMPANY',refs=refs('pool'))],nodes=[dict(key='sew',pool_key='pool',stage='SEWING_ACTIVE',refs=refs('sew'))],events=[dict(key='first',pool_key='pool',from_node=None,to_node='sew',qty_pcs='17',ordinal='1',reverses_key=None,refs=refs('first'))])
        positions=wip.call(cur,'reconcile',graph);positions=wip.call(cur,'yield',positions,[dict(position_key='sew',eligible_input_pcs='17',numerator='1',denominator='1',basis='ASSUMED',assumption_id='AS-C-own17',refs=refs('yield'))])
        source=dict(key='sew',quality='COMPLETE',size_id='L',confirmed_target=None,constraints=[],refs=copy.deepcopy(positions['positions'][0]['refs']))
        targets=[dict(key=k,size_id='L',need_pcs='11',deadline='2026-10-11T00:00:00Z',risk_at='2026-10-10T00:00:00Z',helps_at='2026-10-09T00:00:00Z',production_status='ACTIVE',refs=refs(k)) for k in ['B','A']]
        matching=dict(snapshot_id='AS-C17',sources=[source],targets=[dict(key=k,size_id='L',constraints=[],refs=refs(k)) for k in ['B','A']])
        p=dict(contract_version='cp7.allocation-input.v1',snapshot_id='AS-C17',scope_id='ALL17',scenario_id='AS-C-priority',complete_scope=True,positions=positions,matching=matching,etas=[dict(position_key='sew',at='2026-10-09T00:00:00Z',refs=refs('eta'))],targets=targets,capacity_pcs='17',refs=refs('scenario'))
        def call(v):admin(cur);return cur.execute('select cp7_baseline.allocate(%s::jsonb)',(json.dumps(v),)).fetchone()[0]
        out=call(p);alloc={x['target_key']:D(x['allocated_good_pcs']) for x in out['rows']}
        check(alloc==dict(A=D(11),B=D(6)),'Stable ID breaks exact priority tie against input order',output=out)
        reverse=copy.deepcopy(p);reverse['targets'].reverse();reverse['matching']['targets'].reverse();again=call(reverse)
        check(again['rows']==out['rows'] and again['allocation']==out['allocation'],'Input order cannot change allocation')
        earlier=copy.deepcopy(p);earlier['targets'][0]['deadline']='2026-10-10T00:00:00Z';soon=call(earlier)
        check({x['target_key']:D(x['allocated_good_pcs']) for x in soon['rows']}==dict(B=D(11),A=D(6)),'Real earlier deadline outranks stable-ID tie',output=soon)
        unknown=copy.deepcopy(p);unknown['targets'][0]['risk_at']=None;review=call(unknown)
        check(any(x['target_key']=='B' for x in review['review_queue']) and all(x['target_key']!='B' for x in review['allocation']['allocation']['edges']),'Unknown timing retained for review, never allocated as safe',output=review)
        return dict(scope='PRIVATE_KERNEL_NOT_NATIVE_PLAN_POST',tie=alloc,earlier_deadline=soon['rows'],unknown=review['review_queue'],input_pcs=17)

    actor=[x for x in cont.cases(cur,today) if x[0]=='AS20C-04-ACTOR']
    return actor+[wrap('AS20C-11-RETURN',returned),wrap('AS20C-18-ROSTER',same_name),wrap('AS20C-09-CLOSED',closed),wrap('AS20C-22-TIE',priority)]
