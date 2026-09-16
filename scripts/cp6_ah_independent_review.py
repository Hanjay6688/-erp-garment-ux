#!/usr/bin/env python3
"""Independent AH business checks on unchanged candidate and disposable data."""
from pathlib import Path
from datetime import timedelta
from decimal import Decimal
import json, os, subprocess, sys, traceback, uuid
sys.path.insert(0, str(Path.cwd() / 'scripts'))
import psycopg
import cp6_v2620ah_runtime as runtime
import cp6_v2620ah_family as writer
import cp6_ag_residual_review as returns
import cp6_aa_invoice_partial_audit as production
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot

HEAD='965ceac45ef15ddc19c178d87a3606adffcf53a6'
TREE='183a0c2af8ba201e3754e9db77fe47501c196f4d'
ROOT=Path('cp6-proof/independent-ah')
actors,base,prior,peer=writer.actors,writer.base,writer.prior,writer.peer

def save(name, value):
    ROOT.mkdir(parents=True,exist_ok=True)
    (ROOT/(name+'.json')).write_text(json.dumps(value,indent=2,default=str)+'\n')

class DraftReady(Exception): pass

def work_draft(cur, day, rate):
    """Stop the existing physical production fixture at its ordinary work draft.

    Only the new master rate is supplied by this fixture; all production SQL
    remains the original candidate. No posted state or function is modified.
    """
    f=production.estimated_receipt(cur,day)
    captured={}
    class DraftCursor:
        def __getattr__(self,name):return getattr(cur,name)
        def execute(self,query,params=None,**kwargs):
            text=str(query)
            if 'insert into erp.po_work_component_snapshots(' in text:
                assert 'values(%s,%s,%s,1,0,%s)' in text
                query=text.replace('values(%s,%s,%s,1,0,%s)','values(%s,%s,%s,1,%s,%s)')
                params=(*params[:3],rate,params[3])
                captured.update(snapshot=params[0],po=params[1],component=params[2],rate=rate)
            if 'insert into erp.work_completion_events(' in text:
                captured.update(completion=params[0],group=params[4])
                peer.ordinary(cur)
            if 'insert into erp.work_completion_lines(' in text:peer.ordinary(cur)
            if 'select erp.post_work_completion(' in text:raise DraftReady()
            return cur.execute(query,params,**kwargs)
    try:production.partial_production(DraftCursor(),f)
    except DraftReady:pass
    else:raise AssertionError('Fixture did not stop at the work draft')
    assert {'snapshot','po','component','rate','completion','group'}<=set(captured)
    actors.admin(cur)
    amount=cur.execute('select qty_completed,qty_payable,rate_snapshot,amount_payable from erp.work_completion_lines where completion_id=%s',(captured['completion'],)).fetchall()
    assert amount==[(10,10,rate,rate*10)],amount
    return captured

def work_state(cur, completion):
    actors.admin(cur)
    return base.one(cur,"""select jsonb_build_object('header',to_jsonb(h),
      'lines',(select jsonb_agg(to_jsonb(l)||jsonb_build_object('snapshot_po',s.po_id,'snapshot_component',s.work_component_id,'snapshot_rate',s.rate_per_pcs_snapshot))
        from erp.work_completion_lines l join erp.po_work_component_snapshots s on s.id=l.po_component_snapshot_id where l.completion_id=h.id),
      'journal',(select jsonb_agg(to_jsonb(j)) from erp.journal_entries j where j.source_type='WORK_COMPLETION' and j.source_id=h.id),
      'journal_lines',(select jsonb_agg(to_jsonb(l)) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.source_type='WORK_COMPLETION' and j.source_id=h.id))
      from erp.work_completion_events h where h.id=%s""",(completion,))

def qualified_work_control(cur,f):
    actors.admin(cur);before=actors.boundary(cur);cur.execute('savepoint normal_work_control')
    result=peer.operation(cur,'select erp.post_work_completion(%s)',(f['completion'],))
    returns.success(result);state=work_state(cur,f['completion'])
    assert state['header']['status']=='POSTED' and len(state['journal'])==1,state
    assert sum(Decimal(str(x['debit'])) for x in state['journal_lines'])==10*f['rate'],state
    cur.execute('rollback to savepoint normal_work_control;release savepoint normal_work_control')
    actors.admin(cur);assert actors.boundary(cur)==before
    return dict(operation=result,state=state)

def work_case(mode):
    def run(cur,day):
        first=work_draft(cur,day,Decimal('1.25'))
        controls=[qualified_work_control(cur,first)]
        if mode=='NORMAL':return dict(status='CONTROL_PASS',controls=controls)
        second=work_draft(cur,day,Decimal('2.50'))
        controls.append(qualified_work_control(cur,second))
        if mode=='HEADER_PO':
            query='update erp.work_completion_events set po_id=%s,cutting_group_id=%s where id=%s'
            params=(second['po'],second['group'],first['completion'])
        elif mode=='LINE_PARENT':
            query='update erp.work_completion_lines set completion_id=%s where completion_id=%s'
            params=(second['completion'],first['completion'])
        else:raise AssertionError(mode)
        actors.admin(cur);before=actors.boundary(cur)
        changed=peer.operation(cur,query,params)
        if changed['refused']:
            actors.admin(cur)
            assert actors.boundary(cur)==before
            assert changed['error']['sqlstate']=='P0001',changed
            return dict(status='CONTROL_PASS',controls=controls,refusal=changed)
        assert changed['changed']==1,changed
        actors.admin(cur);before_post=actors.boundary(cur)
        posted=peer.operation(cur,'select erp.post_work_completion(%s)',(first['completion'],))
        if posted['refused']:
            actors.admin(cur);assert actors.boundary(cur)==before_post
            assert posted['error']['sqlstate']=='P0001',posted
            return dict(status='CONTROL_PASS',controls=controls,change=changed,refusal=posted)
        state=work_state(cur,first['completion'])
        broken=[l for l in state['lines'] if l['snapshot_po']!=state['header']['po_id'] or l['snapshot_component']!=l['work_component_id']]
        assert mode=='HEADER_PO' and state['header']['status']=='POSTED' and broken,state
        today=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")
        report=peer.confidence(cur,today)
        return dict(status='BUG_PROVEN',family='WORK_DRAFT_SOURCE_REVALIDATION',controls=controls,
          change=changed,posting=posted,state=state,report=report,
          expected='A posted work line must use the component/rate snapshot of its current PO; either reject or require rebuilding the draft lines before posting.',
          original_candidate_unchanged=True,synthetic_detector_control=False)
    return run

def independent_return(destination,grade):
    def run(cur,day):
        f=returns.posted_fixture(cur,day);f['ordinary_draft_creation']=True
        dest=base.LOCATION if destination=='SAME' else f['second_location']
        rid=returns.create_return(cur,day,f,dest,grade,(1,1))
        posted=peer.operation(cur,'select erp.post_sales_return(%s)',(rid,));returns.success(posted)
        actors.admin(cur)
        observed=cur.execute("""select m.location_id,m.quality_grade,sum(m.qty_signed),sum(m.qty_signed*m.unit_hpp_snapshot)
          from erp.fg_stock_movements m join erp.sales_return_items i on i.id=m.source_id
          where i.return_id=%s and m.source_type='SALES_RETURN_ITEM' and m.movement_type='SALE_RETURN'
          group by m.location_id,m.quality_grade""",(rid,)).fetchall()
        assert observed==[(uuid.UUID(str(dest)),grade,2,Decimal('2.50'))],observed
        net=base.one(cur,'select erp.sale_net_total(%s)',(f['sale']['sale_id'],));assert net==Decimal('20'),net
        assert peer.confidence(cur,day)['data_confidence']['status']=='READY'
        reversed=peer.operation(cur,"select erp.reverse_sales_return(%s,'Independent AH two-line correction')",(rid,));returns.success(reversed)
        actors.admin(cur);assert base.one(cur,'select erp.sale_net_total(%s)',(f['sale']['sale_id'],))==Decimal('60')
        today=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")
        report=peer.confidence(cur,today);assert report['data_confidence']['status']=='READY',report
        return dict(status='CONTROL_PASS',receipt=observed,net_after_return=net,reversal=reversed,report=report)
    return run

def cases():
    result=[('WORK_'+mode,work_case(mode)) for mode in ('NORMAL','HEADER_PO','LINE_PARENT')]
    result += [('RETURN_'+destination+'_'+grade,independent_return(destination,grade)) for destination in ('SAME','OTHER') for grade in ('GRADE_A','GRADE_B','HOLD')]
    for name,fn in [('ALLOCATION_LIMIT',writer.allocation_limit),('SPLIT_DESTINATION',writer.split_destination),('SOURCE_REBIND',writer.source_rebind)]:
        def retained(cur,day,fn=fn):
            r=fn(cur,day);assert r['status']=='PASS';r['status']='CONTROL_PASS';r['retained_writer_oracle']=True;return r
        result.append((name,retained))
    return result

def run():
    git=lambda *a:subprocess.check_output(['git',*a],text=True).strip()
    assert (git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}'))==(HEAD,TREE)
    assert os.environ.get('PGURL')==peer.URL and os.environ.get('CP6_AH_INDEPENDENT_CONFIRM')=='postgres'
    runtime.verify_source_files()
    result=dict(status='INCOMPLETE',candidate_head=HEAD,candidate_tree=TREE,harness_head=os.environ['CP6_AUDIT_HARNESS_HEAD'],run_id=os.environ.get('GITHUB_RUN_ID'),cases={},production_go=False,http_ui_csv_reachability_proven=False)
    with psycopg.connect(peer.URL.replace('postgres:postgres@','supabase_admin:postgres@')) as conn,conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='180s';set local lock_timeout='8s'")
        assert len(runtime.verified_successor(cur))==690
        catalog=function_catalog(cur);untouched=actors.boundary(cur)
        save('AH_ORIGINAL_CATALOG',catalog);save('AH_ORIGINAL_BOUNDARY',snapshot(cur))
        usage=base.one(cur,"select has_schema_privilege('authenticated','erp','USAGE')");result['schema_usage_fixture_grant']=not usage
        if not usage:cur.execute('grant usage on schema erp to authenticated')
        cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=base.OPERATOR_AUTH,role='authenticated')),))
        base.load_fixture_foundation(cur);actors.admin(cur)
        day=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3)
        prior.set_open_period(cur,day-timedelta(days=5))
        save('WORK_CONSTRAINTS',cur.execute("select c.conrelid::regclass::text,c.conname,pg_get_constraintdef(c.oid) from pg_constraint c where c.conrelid in('erp.work_completion_lines'::regclass,'erp.work_completion_events'::regclass,'erp.po_work_component_snapshots'::regclass) order by 1,2").fetchall())
        for name,case in cases():
            actors.admin(cur);before=actors.boundary(cur);cur.execute('savepoint independent_case')
            try:record=case(cur,day)
            except Exception as exc:record=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
            finally:cur.execute('rollback to savepoint independent_case');actors.admin(cur);cur.execute('release savepoint independent_case')
            record['full_boundary_restored']=actors.boundary(cur)==before
            if not record['full_boundary_restored']:record['status']='INCOMPLETE'
            result['cases'][name]=record;save('RESULT',result)
            print(json.dumps(dict(case=name,status=record['status'],error=record.get('error'))),flush=True)
        actors.admin(cur);result['function_catalog_unchanged']=catalog==function_catalog(cur)
        conn.rollback();cur.execute("set local timezone='Asia/Jakarta'")
        result['unseeded_boundary_restored']=untouched==actors.boundary(cur)
        result['schema_usage_restored']=base.one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")==usage
        result['auth_users'],result['app_users']=cur.execute('select (select count(*) from auth.users),(select count(*) from erp.app_users)').fetchone()
        conn.rollback()
    result.update(controls=sum(c['status']=='CONTROL_PASS' for c in result['cases'].values()),bugs=sum(c['status']=='BUG_PROVEN' for c in result['cases'].values()),incomplete=sum(c['status']=='INCOMPLETE' for c in result['cases'].values()))
    if all(result[k] for k in ('function_catalog_unchanged','unseeded_boundary_restored','schema_usage_restored')) and result['auth_users']==result['app_users']==result['incomplete']==0:
        result['status']='BUG_PROVEN' if result['bugs'] else 'PASS_REVIEWED_SCOPE'
    save('RESULT',result);return result

if __name__=='__main__':
    try:result=run()
    except Exception as exc:
        result=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc(),production_go=False);save('RESULT',result)
    print(json.dumps({k:v for k,v in result.items() if k!='cases'}));raise SystemExit(0 if result['status']=='PASS_REVIEWED_SCOPE' else 1)
