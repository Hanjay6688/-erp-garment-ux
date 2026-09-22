"""Period allocation acceptance: real sewing, partial FG, sale, recost and inverse."""
from datetime import timedelta
from decimal import Decimal as D
import json,uuid
import cp6_pocket_fabric_trial as pocket
import cp6_initial_import_receipt_trial as receipts
from cp6_initial_import_advance_trial import ledger


def mutex(a,cur,url,connect):
    before=a.actors.boundary(cur)
    with connect(url) as other,other.cursor() as peer:
        assert peer.execute("select pg_try_advisory_xact_lock(hashtextextended('POCKET_HPP_PERIOD_V1',0))").fetchone()[0]
        error=a.inherited.refused(cur,lambda:cur.execute('select erp.pocket_period_lock_v1()'))
        assert error['message'].startswith('POCKET_PERIOD_BUSY:'),error
        other.rollback()
    cur.execute('savepoint pocket_mutex_check')
    cur.execute('select erp.pocket_period_lock_v1()')
    cur.execute('rollback to savepoint pocket_mutex_check');cur.execute('release savepoint pocket_mutex_check')
    assert a.actors.boundary(cur)==before
    return dict(status='PASS',boundary_restored=True,second_session_conflict_refused=True,retry_after_release=True)


def preview(a,cur,start,end):
    a.ordinary(cur)
    value=cur.execute('select public.erp_preview_pocket_fabric_period_v1(%s,%s)',(start,end)).fetchone()[0]
    a.admin(cur);return value


def production(a,cur,today,special=False):
    p=a.production;old=p.CONTRACTOR
    try:
        if special:
            contractor=uuid.uuid4()
            cur.execute("insert into erp.contractors(id,contractor_code,contractor_name,contractor_type,attendance_required) values(%s,%s,'Special pocket fixture','MANDOR',false)",(contractor,'PKT-'+contractor.hex[:12]))
            current=cur.execute('select id from erp.contractor_hpp_policy_versions where contractor_id=%s and effective_from<=%s and (effective_to is null or effective_to>=%s) order by effective_from desc limit 1',(contractor,today-timedelta(days=8),today-timedelta(days=8))).fetchone()
            a.ordinary(cur)
            cur.execute('select public.erp_set_contractor_hpp_policy_v1(%s::jsonb,%s,%s)',(json.dumps(dict(contractor_id=str(contractor),effective_from=str(today-timedelta(days=8)),is_special=True,attendance_required=False,reason='Special contractor fixture')),uuid.uuid4(),current[0] if current else None))
            a.admin(cur)
            p.CONTRACTOR=str(contractor)
        f=receipts.fixture(a,cur,today,True,qty='10',cost='10');row=receipts.finalize(a,cur,f)
        graph=dict(material=row['material_id'],purchase=row['purchase_id'],item=row['purchase_item_id'],roll=row['roll_id'],location=row['location_id'],purchase_day=today-timedelta(days=8))
        a.admin(cur);cur.execute('grant usage on schema erp to authenticated')
        class DraftCursor:
            def __getattr__(self,name):return getattr(cur,name)
            def execute(self,query,params=None,**kwargs):
                if 'insert into erp.work_completion_events(' in str(query) or 'insert into erp.work_completion_lines(' in str(query):receipts.calendar.peer.ordinary(cur)
                return cur.execute(query,params,**kwargs)
        p.partial_production(DraftCursor(),graph)
        a.admin(cur);cur.execute('revoke usage on schema erp from authenticated')
        return graph
    finally:p.CONTRACTOR=old


def fixture(a,cur,today,special=False,with_output=True):
    graph=production(a,cur,today,special) if with_output else None
    r=pocket.fixture(a,cur,today);payload=pocket.payload(a,cur,r,today)
    out=pocket.call(a,cur,'POST',payload)
    start,end=today-timedelta(days=7),today-timedelta(days=5)
    v=preview(a,cur,start,end)
    p=dict(period_start=str(start),period_end=str(end),expected_revision=v['revision'],reason='Equal pocket allocation by sewn output')
    return dict(graph=graph,roll=r,out=out,preview=v,payload=p,start=start,end=end)


def state(a,cur,ident):
    return next(p for p in pocket.read(a,cur)['periods'] if p['id']==str(ident))


def cancel(a,cur,ident):
    s=state(a,cur,ident)
    return pocket.call(a,cur,'CANCEL_PERIOD',dict(id=str(ident),expected_revision=s['revision'],reason='Cancel allocation, preserve warehouse outflow'))


def reported_effects(a,cur,today):
    s=receipts.rpc(a,cur,'get_owner_financial_snapshot_v2',today-timedelta(days=8),today,today)
    assert D(str(s['financial_position']['balance_difference']))==0
    return {**{k:D(str(s['financial_position'][f])) for k,f in [('MATERIAL_INVENTORY','material_inventory'),('WIP','wip_inventory'),('FG_INVENTORY','fg_inventory')]},
            'COGS':D(str(s['performance']['cogs_gl'])),'OTHER_EXPENSE':D(str(s['performance']['operating_and_other_expense']))}


def truth(cur):
    pocket.truth(cur)
    rows=cur.execute("select check_name,issue_count from erp.run_v267_financial_truth_checks() where check_name like 'AP_PERIOD_POCKET_%'").fetchall()
    assert len(rows)==4 and all(v==0 for _,v in rows),rows
    for po, in cur.execute('select distinct po_id from erp.pocket_period_destinations').fetchall():
        cur.execute('select erp.assert_po_hpp_target_book_v2620e(%s)',(po,))


def lifecycle(a,cur,today,special=False,closed=False):
    cur.execute("set local timezone='Pacific/Kiritimati'" if closed else "set local timezone='UTC'")
    f=fixture(a,cur,today,special);v=f['preview'];assert (v['amount'],v['quantity'],v['per_piece'],v['can_post'])==('11.25','10','1.125000',True),v
    before=ledger(cur);base=pocket.effects(cur);report_base=reported_effects(a,cur,today);stock=pocket.read(a,cur,f['roll']['code'])['rolls'][0]['qty']
    if closed:receipts.rpc(a,cur,'close_accounting_through',today-timedelta(days=1),'Close allocation economic date')
    key=uuid.uuid4();posted=pocket.call(a,cur,'POST_PERIOD',f['payload'],key);ident=posted['id'];assert posted['status']=='ACTIVE'
    boundary=a.actors.boundary(cur);assert pocket.call(a,cur,'POST_PERIOD',f['payload'],key)==posted and a.actors.boundary(cur)==boundary
    after=pocket.effects(cur)
    expected=dict(OTHER_EXPENSE=D('-11.25'),WIP=D('5.62'),FG_INVENTORY=D('3.38'),COGS=D('2.25'),MATERIAL_INVENTORY=D(0))
    assert {k:after[k]-base[k] for k in expected}==expected,(after,base)
    reported=reported_effects(a,cur,today);assert {k:reported[k]-report_base[k] for k in expected}==expected
    assert pocket.read(a,cur,f['roll']['code'])['rolls'][0]['qty']==stock;truth(cur)
    dates=cur.execute("select e.economic_date,j.transaction_date from erp.pocket_period_events e join erp.journal_entries j on j.id=e.journal_entry_id where e.pool_id=%s and e.kind='POST'",(ident,)).fetchone()
    assert dates==(f['end'],today if closed else f['end']),dates
    original=cur.execute('select to_jsonb(p) from erp.pocket_periods p where id=%s',(ident,)).fetchone()[0]
    old_revision=state(a,cur,ident)['revision']
    prior_journals={r[0] for r in cur.execute('select id from erp.journal_entries').fetchall()}
    invoice=receipts.post_invoice(a,cur,receipts.invoice(a,cur,today,f['roll'],20,'3'))
    fresh=[r for r in cur.execute('select id,source_type,economic_date,transaction_date from erp.journal_entries').fetchall() if r[0] not in prior_journals]
    assert {'POCKET_HPP_PERIOD','PO_HPP_GL_SYNC'}<={r[1] for r in fresh},fresh
    assert all(e==today-timedelta(days=2) and b==(today if closed else e) for _,_,e,b in fresh),fresh
    assert state(a,cur,ident)['current_amount']=='15.00';after=pocket.effects(cur)
    assert {k:after[k]-base[k] for k in ['OTHER_EXPENSE','WIP','FG_INVENTORY','COGS']}==dict(OTHER_EXPENSE=D('-11.25'),WIP=D('7.50'),FG_INVENTORY=D('4.50'),COGS=D('3.00'))
    reported=reported_effects(a,cur,today)
    assert all(reported[k]-report_base[k]==after[k]-base[k] for k in reported)
    err=a.inherited.refused(cur,lambda:pocket.call(a,cur,'CANCEL_PERIOD',dict(id=ident,expected_revision=old_revision,reason='Old value')))
    assert 'STALE_VERSION' in err['message'];truth(cur)
    cancel(a,cur,ident);assert state(a,cur,ident)['current_amount']=='0.00'
    assert all(pocket.effects(cur)[k]==base[k] for k in ['WIP','FG_INVENTORY','COGS']);truth(cur)
    receipts.rpc(a,cur,'reverse_material_supplier_invoice_v2',invoice['supplier_invoice_id'],'Restore pocket benchmark',uuid.uuid4(),invoice['row_version'])
    assert ledger(cur)==before
    assert reported_effects(a,cur,today)==report_base
    assert cur.execute('select to_jsonb(p) from erp.pocket_periods p where id=%s',(ident,)).fetchone()[0]==original
    assert pocket.read(a,cur,f['roll']['code'])['rolls'][0]['qty']==stock
    fresh=preview(a,cur,f['start'],f['end']);assert fresh['can_post']
    next_post=pocket.call(a,cur,'POST_PERIOD',dict(f['payload'],expected_revision=fresh['revision']))
    cancel(a,cur,next_post['id']);assert ledger(cur)==before;truth(cur)
    return dict(status='PASS',special_included=special,closed=closed,sewn=10,fg_on_hand=3,sold=2,unfinished=5,stock_unchanged=True,
                source_expense='11.25',corrected_source='15.00',all_accounts_restored=True,reallocation_after_cancel=True,
                report_reconciled=True,all_invoice_recost_legs_use_invoice_date=True)


def refusals(a,cur,today,kind):
    f=fixture(a,cur,today,with_output=kind!='NO_OUTPUT');p=dict(f['payload'])
    if kind=='STALE_COST':receipts.post_invoice(a,cur,receipts.invoice(a,cur,today,f['roll'],20,'3'))
    elif kind=='FUTURE':p['period_end']=str(today+timedelta(days=1))
    elif kind=='REVERSED_RANGE':p['period_start']=str(today)
    elif kind=='TOO_LONG':p['period_start']=str(today-timedelta(days=400))
    elif kind=='EMPTY_REASON':p['reason']=' '
    elif kind=='OVERLAP':pocket.call(a,cur,'POST_PERIOD',p)
    elif kind=='NO_OUTPUT':assert f['preview']['can_post'] is False and f['preview']['quantity']=='0'
    elif kind=='EMPTY_PERIOD':
        p.update(period_start=str(today),period_end=str(today),expected_revision=preview(a,cur,today,today)['revision'])
    else:raise AssertionError(kind)
    before=ledger(cur);error=a.inherited.refused(cur,lambda:pocket.call(a,cur,'POST_PERIOD',p));assert ledger(cur)==before;truth(cur)
    assert error['sqlstate']!='42501',error
    return dict(status='PASS',refusal=kind,atomic=True)


def protections(a,cur,today):
    f=fixture(a,cur,today);posted=pocket.call(a,cur,'POST_PERIOD',f['payload']);ident=posted['id'];before=ledger(cur)
    h=next(h for h in pocket.read(a,cur)['history'] if h['id']==f['out']['id'])
    err=a.inherited.refused(cur,lambda:pocket.call(a,cur,'REVERSE',dict(id=h['id'],expected_version=h['row_version'],reason='Allocated source')))
    assert err['message']=='Batalkan alokasi periode sebelum membatalkan pengeluaran kain kantong',err
    p=pocket.payload(a,cur,f['roll'],today)
    err=a.inherited.refused(cur,lambda:pocket.call(a,cur,'POST',p));assert 'sebelum menambah pengeluaran' in err['message'],err
    e=cur.execute('select event_id from erp.pocket_period_destinations where pool_id=%s',(ident,)).fetchone()[0]
    version=cur.execute('select row_version from erp.sewing_terminal_events where id=%s',(e,)).fetchone()[0]
    err=a.inherited.refused(cur,lambda:cur.execute('select erp.reverse_sewing_terminal_v1(%s,%s,%s,%s)',(e,'Allocated denominator',uuid.uuid4(),version)))
    assert 'sebelum mengoreksi hasil jahit' in err['message'],err
    j=cur.execute('select journal_entry_id from erp.pocket_period_events where pool_id=%s',(ident,)).fetchone()[0]
    err=a.inherited.refused(cur,lambda:cur.execute('select erp.reverse_journal(%s,%s)',(j,'Unlinked inverse')))
    assert 'melalui periode asal' in err['message'],err
    err=a.inherited.refused(cur,lambda:cur.execute('update erp.pocket_periods set denominator=1 where id=%s',(ident,)))
    assert 'Riwayat alokasi periode tetap' in err['message'],err
    assert ledger(cur)==before;truth(cur)
    cancel(a,cur,ident)
    pocket.call(a,cur,'REVERSE',dict(id=h['id'],expected_version=h['row_version'],reason='Source after cancelling allocation'))
    assert pocket.read(a,cur,f['roll']['code'])['rolls'][0]['qty']=='20.000000';truth(cur)
    return dict(status='PASS',source_inverse_blocked=True,denominator_inverse_blocked=True,generic_journal_inverse_blocked=True,immutable=True)


def denied(a,cur,today):
    f=fixture(a,cur,today);key=uuid.uuid4();pocket.call(a,cur,'POST_PERIOD',f['payload'],key)
    backup=uuid.uuid4()
    cur.execute("insert into auth.users(id,aud,role,email) values(%s,'authenticated','authenticated',%s)",(backup,'pool-backup-'+backup.hex+'@example.test'))
    cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active) select gen_random_uuid(),%s,'Pool backup owner','OWNER',id,true from erp.app_roles where role_code='OWNER'",(backup,))
    cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(a.base.OPERATOR_AUTH,))
    a.inherited.refused(cur,lambda:preview(a,cur,f['start'],f['end']))
    a.inherited.refused(cur,lambda:pocket.call(a,cur,'POST_PERIOD',f['payload'],key))
    return dict(status='PASS',revoked_actor_no_preview_or_cached_write=True)


def mixed_rounding(a,cur,today):
    normal=production(a,cur,today);special=production(a,cur,today,True)
    f=fixture(a,cur,today,with_output=False);assert f['preview']['quantity']=='20'
    before=ledger(cur);posted=pocket.call(a,cur,'POST_PERIOD',f['payload'])
    shares=cur.execute('select po_id,sum(erp.pocket_period_amount_v1(pool_id,preceding_qty,sewing_qty)) from erp.pocket_period_destinations where pool_id=%s group by po_id',(posted['id'],)).fetchall()
    assert {po for po,_ in shares}=={normal['po'],special['po']},shares
    assert sorted(v for _,v in shares)==[D('5.62'),D('5.63')],shares
    assert sum(v for _,v in shares)==D('11.25');truth(cur)
    cancel(a,cur,posted['id']);assert ledger(cur)==before;truth(cur)
    return dict(status='PASS',normal_and_special_included=True,total='11.25',shares=['5.62','5.63'],rounding_conserved=True,cancel_restores_all_accounts=True)


def cases(a,cur,today):
    return [('POCKET_PERIOD_LIFECYCLE:'+str(s)+':'+str(c),lambda s=s,c=c:lifecycle(a,cur,today,s,c)) for s in [False,True] for c in [False,True]]+[
      ('POCKET_PERIOD_REFUSAL:'+k,lambda k=k:refusals(a,cur,today,k)) for k in ['STALE_COST','FUTURE','REVERSED_RANGE','TOO_LONG','EMPTY_REASON','OVERLAP','NO_OUTPUT','EMPTY_PERIOD']]+[
      ('POCKET_PERIOD_PROTECTIONS',lambda:protections(a,cur,today)),('POCKET_PERIOD_AUTHORIZATION',lambda:denied(a,cur,today)),
      ('POCKET_PERIOD_MIXED_ROUNDING',lambda:mixed_rounding(a,cur,today))]
