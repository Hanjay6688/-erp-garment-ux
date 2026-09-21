#!/usr/bin/env python3
"""Bounded AM SQL trial. Nothing is committed; not a full writer acceptance.

All business commands run as ordinary authenticated OWNER with existing EXECUTE
grants. Minimal synthetic masters and the accounting observer use the isolated
fixture administrator. No installed guard is disabled. SQL-only role/transport
coverage is explicit; fresh full business, HTTP and concurrency remain required.
"""
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import os
import subprocess
import traceback
import uuid

import psycopg
import cp6_foundation_qualification as f
import cp6_v2620am_runtime as runtime
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot

PG='postgresql://postgres:postgres@127.0.0.1:54322/postgres'
ADMIN=PG.replace('postgres:postgres@','supabase_admin:postgres@')
REPORT=Path('cp6-proof/writer-am/SQL_TRIAL.json')


def sql_body(path):
    source=path.read_text()
    start=source.index('begin;\n')+len('begin;\n')
    assert source.rstrip().endswith('commit;')
    return source[start:source.rindex('commit;')]


def install(cur):
    f.admin(cur)
    runtime.verify_predecessor(cur)
    cur.execute('set local role postgres')
    cur.execute(sql_body(runtime.MIGRATION),prepare=False)
    cur.execute('insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)',
        (runtime.STAMP,runtime.NAME,[runtime.MIGRATION.read_text()]))
    cur.execute('reset role')
    assert len(runtime.verified_successor(cur))==690
    cur.execute("set local timezone='Asia/Jakarta'")


def prepare(cur):
    f.OWNER=str(uuid.uuid4())
    cur.execute("insert into erp.app_users(auth_user_id,full_name,role,role_id,is_active) select %s,'Synthetic AM SQL owner','OWNER',id,true from erp.app_roles where role_code='OWNER'",(f.OWNER,))
    f.owner(cur)
    assert cur.execute('select erp.current_app_role()').fetchone()[0]=='OWNER'
    f.admin(cur)
    now,start=cur.execute("select clock_timestamp(),date_trunc('day',clock_timestamp())").fetchone()
    assert (now-start).total_seconds()>10
    closed=cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]
    assert closed is None or closed<now.date()
    f.MASTER=dict(start=start,pcs=cur.execute("select unit_code from erp.uom_definitions where upper(unit_code)='PCS' and dimension='COUNT'").fetchone()[0],
        supplier=cur.execute("insert into erp.suppliers(supplier_code,supplier_name) values(%s,'Synthetic AM supplier') returning id",(f.tag(),)).fetchone()[0],
        **{'t'+str(i):start+(now-start)*q for i,q in enumerate((.2,.4,.6,.8))})


def totals(cur,mat):
    f.admin(cur)
    return cur.execute('select location_id,sum(qty_signed),sum(qty_signed*unit_cost_snapshot) from erp.material_stock_movements where material_id=%s group by location_id order by location_id',(mat,)).fetchall()


def fixture(cur,fabric=False):
    source,dest=f.locations(cur)
    mat=f.material(cur,'FABRIC' if fabric else 'OTHER')
    receipt=f.purchase(cur,mat,source,100,10,f.MASTER['t0'],rolls=1 if fabric else 0)
    f.purchase(cur,mat,source,100,20,f.MASTER['t2'],rolls=1 if fabric else 0)
    roll=None
    if fabric:
        roll=cur.execute('select r.id from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where i.purchase_id=%s',(receipt,)).fetchone()[0]
    return mat,source,dest,roll


def make(cur,mat,source,dest,qtys,roll=None,backdate=False):
    payload=dict(transfer_number=f.tag(),from_location_id=source,to_location_id=dest,
        physical_at=f.MASTER['t1'] if backdate else f.MASTER['t3'],change_reason='AM complete physical transfer',
        items=[dict(material_id=mat,roll_id=roll,qty=q) for q in qtys])
    return f.call(cur,'erp.save_material_transfer_draft_v2',f.encode(payload),uuid.uuid4(),None)


def roundtrip(cur,qtys,*,fabric=False,backdate=False,original=False):
    mat,source,dest,roll=fixture(cur,fabric)
    before=f.stock(cur,mat);journal=f.gl(cur)
    draft=make(cur,mat,source,dest,qtys,roll,backdate)
    key=uuid.uuid4()
    args=(draft['material_transfer_id'],key,draft['row_version'],'AM repeatable exact transfer')
    posted=f.call(cur,'erp.post_material_transfer_v2',*args)
    assert posted['movement_count']==2*len(qtys)
    after=f.stock(cur,mat)
    if not original:
        assert after['qty']==200 and after['value']==3000 and after['average']==15,after
    before_replay=snapshot(cur)
    assert f.call(cur,'erp.post_material_transfer_v2',*args)==posted
    assert snapshot(cur)==before_replay
    reversed=f.call(cur,'erp.reverse_material_transfer_v2',draft['material_transfer_id'],
        'AM linked full inverse',uuid.uuid4(),posted['row_version'])
    observed=totals(cur,mat)
    expected=sorted([(source,Decimal(200),Decimal(3000)),(dest,Decimal(0),Decimal(0))])
    assert reversed['status']=='REVERSED'
    assert f.gl(cur)==journal
    if not original:assert observed==expected,dict(actual=observed,expected=expected)
    return dict(status='BUG_PROVEN' if observed!=expected else 'CONTROL_PASS',
        qtys=qtys,fabric=fabric,backdate=backdate,expected_by_location=expected,
        actual_by_location=observed,exact_replay=True,journal_unchanged=True)


def delete_draft(cur,original=False):
    mat,source,dest,_=fixture(cur)
    draft=make(cur,mat,source,dest,[10])
    before=f.stock(cur,mat)
    args=(f.encode(dict(id=draft['material_transfer_id'],action='DELETE',change_reason='AM unused draft removal')),uuid.uuid4(),draft['row_version'])
    result,error=f.attempt(cur,lambda:f.call(cur,'erp.save_material_transfer_draft_v2',*args))
    assert f.stock(cur,mat)==before
    if error:
        assert original and 'Material transfer not found' in error['message'],error
        return dict(status='BUG_PROVEN',refusal=error,ledger_unchanged=True)
    assert result['status']=='DELETED'
    assert not cur.execute('select 1 from erp.material_transfers where id=%s',(draft['material_transfer_id'],)).fetchone()
    boundary=snapshot(cur)
    assert f.call(cur,'erp.save_material_transfer_draft_v2',*args)==result
    assert snapshot(cur)==boundary
    return dict(status='CONTROL_PASS',replay_exact=True,ledger_unchanged=True)


def multi_material(cur,qtys):
    # A transfer has one row per material/roll. Do not bypass that constraint
    # to manufacture an impossible repeated-line roundtrip.
    source,dest=f.locations(cur)
    materials=[f.material(cur) for _ in qtys]
    for mat in materials:
        f.purchase(cur,mat,source,100,10,f.MASTER['t0'])
        f.purchase(cur,mat,source,100,20,f.MASTER['t2'])
    journal=f.gl(cur)
    draft=f.transfer(cur,source,dest,list(zip(materials,qtys)),f.MASTER['t1'])
    posted=f.post_transfer(cur,draft)
    assert posted['movement_count']==2*len(qtys)
    for mat in materials:
        state=f.stock(cur,mat)
        assert state['qty']==200 and state['value']==3000 and state['average']==15,state
    result=f.call(cur,'erp.reverse_material_transfer_v2',draft['material_transfer_id'],
        'AM whole multi-material inverse',uuid.uuid4(),posted['row_version'])
    assert result['status']=='REVERSED' and f.gl(cur)==journal
    for mat in materials:
        assert totals(cur,mat)==sorted([(source,Decimal(200),Decimal(3000)),(dest,Decimal(0),Decimal(0))])
    return dict(status='CONTROL_PASS',distinct_material_count=len(materials),qtys=qtys,
        complete_movement_count=posted['movement_count'],all_location_values_restored=True)


def duplicate_lines(cur,qtys):
    mat,source,dest,_=fixture(cur)
    _,error=f.attempt(cur,lambda:make(cur,mat,source,dest,qtys))
    assert error and error['sqlstate']=='23505' and 'uq_material_transfer_item' in error['message'],error
    return dict(status='CONTROL_PASS',qtys=qtys,existing_unique_rule_preserved=True,refusal=error)


def chain_reverse(cur,return_to_middle):
    source,middle=f.locations(cur);last,_=f.locations(cur);mat=f.material(cur)
    f.purchase(cur,mat,source,100,10,f.MASTER['t0'])
    first=f.post_transfer(cur,f.transfer(cur,source,middle,[(mat,100)],f.MASTER['t1']))
    f.post_transfer(cur,f.transfer(cur,middle,last,[(mat,50)],f.MASTER['t2']))
    if return_to_middle:
        f.post_transfer(cur,f.transfer(cur,last,middle,[(mat,50)],f.MASTER['t3']))
    _,error=f.attempt(cur,lambda:f.call(cur,'erp.reverse_material_transfer_v2',first['material_transfer_id'],
        'AM dependent physical source cannot disappear',uuid.uuid4(),first['row_version']))
    assert error and ('negative' in error['message'].lower() or 'insufficient' in error['message'].lower()),error
    if return_to_middle:assert 'NEGATIVE_LOCATION_ROLL_HISTORY' in error['message'],error
    return dict(status='CONTROL_PASS',current_destination_stock_restored=return_to_middle,
        dependent_source_refused_atomically=True,refusal=error)


def edit_draft(cur):
    mat,source,dest,_=fixture(cur)
    draft=make(cur,mat,source,dest,[10])
    edited=f.call(cur,'erp.save_material_transfer_draft_v2',f.encode(dict(id=draft['material_transfer_id'],
        change_reason='AM current draft qty20',items=[dict(material_id=mat,qty=20)])),uuid.uuid4(),draft['row_version'])
    _,error=f.attempt(cur,lambda:f.post_transfer(cur,draft))
    assert error and 'STALE_VERSION' in error['message'],error
    posted=f.post_transfer(cur,edited)
    amount=cur.execute("select sum(qty_signed) from erp.material_stock_movements where source_type='MATERIAL_TRANSFER' and source_id=%s and location_id=%s",(posted['material_transfer_id'],dest)).fetchone()[0]
    assert amount==20
    return dict(status='CONTROL_PASS',stale_refusal=error,latest_posted_qty=amount)


def invalid_number(cur,value):
    mat,source,dest,_=fixture(cur)
    before=f.stock(cur,mat)
    draft,error=f.attempt(cur,lambda:make(cur,mat,source,dest,[value]))
    if not error:_,error=f.attempt(cur,lambda:f.post_transfer(cur,draft))
    assert error and f.stock(cur,mat)==before,error
    return dict(status='CONTROL_PASS',value=value,refusal=error,ledger_unchanged=True)


def role_control(cur,direct=False):
    mat,source,dest,_=fixture(cur);draft=make(cur,mat,source,dest,[10])
    if direct:
        def operation():
            f.owner(cur)
            cur.execute('update erp.material_transfer_items set qty=20 where transfer_id=%s',(draft['material_transfer_id'],))
        _,error=f.attempt(cur,operation)
        assert error and error['sqlstate']=='42501',error
    else:
        original=f.OWNER
        try:
            f.OWNER=str(uuid.uuid4())
            _,error=f.attempt(cur,lambda:f.post_transfer(cur,draft))
        finally:f.OWNER=original
        assert error,error
    return dict(status='CONTROL_PASS',refusal=error,existing_authority_unchanged=True)


def checkpoint(cur,qty):
    mat,source,dest,_=fixture(cur)
    f.post_transfer(cur,make(cur,mat,source,dest,[qty],backdate=True))
    before=f.stock(cur,mat)
    originals=cur.execute('select id,original_unit_cost_snapshot from erp.material_stock_movements where material_id=%s order by id',(mat,)).fetchall()
    # Internal cache helper, not a claim that an accounting period was closed.
    cur.execute('select erp.refresh_material_cost_checkpoint(%s,%s)',(mat,f.MASTER['start'].date()))
    cp=cur.execute('select stock_qty,moving_average_cost from erp.material_cost_checkpoints where material_id=%s',(mat,)).fetchone()
    assert cp==(200,15),cp
    cur.execute('select erp._recalculate_material_cost_core(%s,null,false)',(mat,))
    assert f.stock(cur,mat)==before
    assert cur.execute('select id,original_unit_cost_snapshot from erp.material_stock_movements where material_id=%s order by id',(mat,)).fetchall()==originals
    return dict(status='CONTROL_PASS',transfer_qty=qty,checkpoint=cp,original_snapshots_preserved=True,
        internal_cache_helper=True,accounting_close_lifecycle_proven=False)


def dirty_admission(cur,make_dirty):
    observed=make_dirty(cur)
    assert observed['status']=='BUG_PROVEN',observed
    _,error=f.attempt(cur,lambda:install(cur))
    assert error and 'AM_PREEXISTING_TRANSFER_OR_LOCATION_HISTORY_REVIEW_REQUIRED' in error['message'],error
    assert len(runtime.predecessor.verified_successor(cur))==690
    return dict(status='CONTROL_PASS',original=observed,install_refusal=error,atomic=True)


def run():
    assert os.environ['PGURL']==PG and os.environ['CP6_AI_INDEPENDENT_CONFIRM']=='postgres'
    runtime.verify_source_files()
    root=Path(__file__).resolve().parents[1]
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=root,text=True).strip()
    assert head==os.environ['CP6_RUNTIME_HEAD'] and tree==os.environ['CP6_RUNTIME_TREE']
    report=dict(status='INCOMPLETE',scope='AM_SINGLE_TRANSACTION_SQL_TRIAL',candidate_head=head,
        candidate_tree=tree,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        product_changes_committed_to_database=False,guards_disabled=False,
        full_business_acceptance=False,http_transport_proven=False,concurrency_proven=False,
        committed_maintenance_rollback_proven=False,production_go=False,cases={})
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    def save():REPORT.write_text(json.dumps(report,indent=2,default=str)+'\n')
    save()
    def case(cur,name,fn,wanted='CONTROL_PASS'):
        f.admin(cur);before=snapshot(cur);cur.execute('savepoint am_case')
        try:
            result=fn(cur)
            assert result['status']==wanted,result
        except Exception as exc:result=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
        finally:
            cur.execute('rollback to savepoint am_case');f.admin(cur);cur.execute('release savepoint am_case')
        result['transactional_boundary_restored']=snapshot(cur)==before
        if not result['transactional_boundary_restored']:result['status']='INCOMPLETE'
        report['cases'][name]=result;save()
        print(json.dumps(dict(case=name,status=result['status'],error=result.get('error'))),flush=True)
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        initial=catalog=usage=None
        try:
            cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
            assert len(runtime.predecessor.verified_successor(cur))==690
            initial,catalog=snapshot(cur),function_catalog(cur)
            usage=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
            if not usage:cur.execute('grant usage on schema erp to authenticated')
            report['temporary_schema_usage_grant']=not usage
            prepare(cur)
            original_specs=[('VALUE10',lambda c:f.neutral_transfer(c,10,True)),('VALUE100',lambda c:f.neutral_transfer(c,100,True)),
                ('INACTIVE_MIXED',lambda c:f.inactive_lines(c,'MIXED')),('INACTIVE_ALL',lambda c:f.inactive_lines(c,'ALL_INACTIVE')),
                ('LOCATION_HISTORY',lambda c:f.location_history(c,True))]
            for name,fn in original_specs:case(cur,'ORIGINAL_ADMISSION:'+name,lambda c,fn=fn:dirty_admission(c,fn))
            for q in (10,100):case(cur,'ORIGINAL_REVERSE_VALUE:'+str(q),lambda c,q=q:roundtrip(c,[q],original=True),'BUG_PROVEN')
            case(cur,'ORIGINAL_DRAFT_DELETE',lambda c:delete_draft(c,True),'BUG_PROVEN')
            before_install=snapshot(cur)
            install(cur)
            report['installed_objects']=690;save()
            specs=[('VALUE:'+str(q)+':'+str(b),lambda c,q=q,b=b:f.neutral_transfer(c,q,b)) for q,b in [(10,False),(10,True),(100,True)]]
            specs += [('LINES:'+m,lambda c,m=m:f.inactive_lines(c,m)) for m in ['ACTIVE_CONTROL','MIXED','ALL_INACTIVE']]
            specs += [('PREFIX:'+str(b),lambda c,b=b:f.location_history(c,b)) for b in [False,True]]
            specs += [('ROUND_TRIP:'+str(q),lambda c,q=q:roundtrip(c,q,backdate=True)) for q in [[10],[100]]]
            specs += [('MULTI_MATERIAL:'+str(q),lambda c,q=q:multi_material(c,q)) for q in [[10,10],[10,20]]]
            specs += [('DUPLICATE_LINES:'+str(q),lambda c,q=q:duplicate_lines(c,q)) for q in [[10,10],[10,20]]]
            specs += [('CHAIN_REVERSE:'+str(b),lambda c,b=b:chain_reverse(c,b)) for b in [False,True]]
            specs += [('FABRIC_ROLL',lambda c:roundtrip(c,[50],fabric=True,backdate=True)),('DRAFT_DELETE',delete_draft),('DRAFT_EDIT',edit_draft)]
            specs += [('INVALID:'+str(v),lambda c,v=v:invalid_number(c,v)) for v in [0,-1,'NaN']]
            specs += [('ROLE_UNMAPPED',role_control),('DIRECT_DRAFT_ROLE',lambda c:role_control(c,True))]
            specs += [('CHECKPOINT:'+str(q),lambda c,q=q:checkpoint(c,q)) for q in [10,100]]
            report['planned_successor_cases']=[n for n,_ in specs];save()
            for name,fn in specs:case(cur,'SUCCESSOR:'+name,fn)
            assert len(runtime.verified_successor(cur))==690
            f.admin(cur);cur.execute('set local role postgres')
            cur.execute(sql_body(runtime.ROLLBACK),prepare=False);cur.execute('reset role')
            cur.execute("set local timezone='Asia/Jakarta'")
            assert runtime.verify_predecessor(cur)
            report['exact_sql_restore']=snapshot(cur)==before_install
            assert report['exact_sql_restore']
        except Exception as exc:
            report['error']=str(exc);report['traceback']=traceback.format_exc()
        finally:
            conn.rollback();cur.execute("set local timezone='Asia/Jakarta'")
            report['full_initial_boundary_restored']=initial is not None and snapshot(cur)==initial and function_catalog(cur)==catalog
            report['schema_usage_restored']=usage is not None and cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==usage
            report['initial_al_runtime_restored']=len(runtime.predecessor.verified_successor(cur))==690
            conn.rollback()
    report['counts']={s:sum(r['status']==s for r in report['cases'].values()) for s in ['CONTROL_PASS','BUG_PROVEN','INCOMPLETE']}
    if not report.get('error') and not report['counts']['INCOMPLETE'] and all(report.get(k) for k in ['exact_sql_restore','full_initial_boundary_restored','schema_usage_restored','initial_al_runtime_restored']):
        report['status']='SQL_TRIAL_COMPLETE_FULL_ACCEPTANCE_PENDING'
    save();return report


if __name__=='__main__':
    outcome=run()
    print(json.dumps({k:v for k,v in outcome.items() if k not in ['cases','planned_successor_cases']}))
    raise SystemExit(0 if outcome['status']=='SQL_TRIAL_COMPLETE_FULL_ACCEPTANCE_PENDING' else 1)
