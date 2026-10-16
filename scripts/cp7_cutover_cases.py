"""Owner D15-5 (Fable FABLE-011): the official cutover date and the server floor for new operational rows.

Native, race and real-Auth HTTP cases for scripts/cp7-src/cutover/cutover.sql, spliced into the CP17 r2 harness. The owner's
tests: the date boundary (exactly on the date and the day before), the opening-balance path (import at the official date,
late invoice on an opening receipt, settlement after cutover, nothing counted twice), failure in the middle of a command
(nothing stays), and resending (same UUID, same answer; a refused request stays refused).
Oracles: the latest date the owner may choose is computed here from the books with the owner's list of official paths;
dates, balances and stock are read from the Native rows (journal_entries, stock movements, import tables), never from the
facade's answer alone. The CI database already holds operational history, so the boundary is that history's own first
day; committed cases (two tabs, HTTP) end by moving the official date back to 2000-01-03, which no later fixture predates.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from decimal import Decimal as D
import json,threading,uuid
import psycopg
import cp7_snapshot_cases as auth
import cp7_cutting_correction_cases as cut
import cp7_master_cases as master
import cp7_misc_cases as misc
import cp7_misc_correction_cases as misc_fix
import cp6_bb_probe as bbp
b=auth.b
refused=auth.refused

NATIVE=['CP17_R2_D15_5_CUTOVER_SET_BOUNDARY_AND_HISTORY','CP17_R2_D15_5_CUTOVER_DAY_BOUNDARY_JOURNAL_AND_STOCK',
        'CP17_R2_D15_5_CUTOVER_OPENING_PATH_LATE_INVOICE_SETTLEMENT','CP17_R2_D15_5_CUTOVER_FAILURE_MIDWAY_LEAVES_NOTHING',
        'CP17_R2_D15_5_CUTOVER_RESEND_SAME_UUID']
RACES=['CP17_RACE_R2_D15_5_CUTOVER_TWO_TABS_SAME_VERSION','CP17_RACE_R2_D15_5_CUTOVER_SET_VS_POST_DAY_BEFORE']
HTTP=['CP17_HTTP_R2_D15_5_CUTOVER']
BROWSER=['CP17_BROWSER_R2_D15_5_CUTOVER_DESKTOP','CP17_BROWSER_R2_D15_5_CUTOVER_MOBILE']
FUNCTIONS=('erp_cp7_get_cutover_v1','erp_cp7_set_cutover_v1')
# The official paths the owner named (opening/migration postings, inverses of rows already in the books).
OFFICIAL=('OPENING\\_%','INITIAL\\_IMPORT\\_%','BB\\_%','BD\\_OPENING\\_%','BE\\_OPENING\\_%','JOURNAL_REVERSAL','CENT\\_INVERSE:%',
          '%\\_TIME\\_NEUTRAL','RECEIPT_FIX_INVOICE_REVERSAL_DATE')
RESET=date(2000,1,3)

def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]
def prod():return cut.cutting.qc.physical.b.chain.production
def ws(cur,subject):
    auth.actor(cur,subject);r=one(cur,'select public.erp_cp7_get_cutover_v1()');b.api.admin(cur);return r
def put(cur,subject,day,version,reason='Tanggal mulai pakai aplikasi',key=None):
    auth.actor(cur,subject)
    r=one(cur,'select public.erp_cp7_set_cutover_v1(%s::jsonb,%s)',(json.dumps(dict(action='SET',expected_version=version,cutover_date=str(day),reason=reason)),str(key or uuid.uuid4())))
    b.api.admin(cur);return r
def owner(cur):return master.role_actor(cur,'OWNER')
def latest(cur):
    """The oracle's own latest allowed date: the first day of the operational history and of the import batches."""
    b.api.admin(cur);pats=list(OFFICIAL)
    op=one(cur,"""select min(d) from(
        select j.economic_date d from erp.journal_entries j where j.reversal_of_id is null and j.status<>'REVERSED' and not(j.source_type like any(%s))
        union all select(m.physical_at at time zone 'Asia/Jakarta')::date from erp.material_stock_movements m where m.reversal_of_id is null
          and not(m.source_type like any(%s)) and not exists(select 1 from erp.material_stock_movements r where r.reversal_of_id=m.id)
        union all select(f.physical_at at time zone 'Asia/Jakarta')::date from erp.fg_stock_movements f where f.reversal_of_id is null
          and not(f.source_type like any(%s)) and not exists(select 1 from erp.fg_stock_movements r where r.reversal_of_id=f.id))x""",(pats,pats,pats))
    batch=one(cur,"select min((cutover_at at time zone 'Asia/Jakarta')::date) from erp.migration_batches")
    return min(d for d in (op,batch) if d is not None),op,batch
def control(cur):b.api.admin(cur);return cur.execute('select version,cutover_date from cp7_cutover.control where singleton_id=1').fetchone()
def reset(cur,subject):
    """Committed cases end with the official date moved back to 2000-01-03 (moving earlier is always allowed)."""
    v,d=control(cur)
    if d!=RESET:put(cur,subject,RESET,v,'CP17 kembali ke tanggal awal sesudah uji')
def receipt_at(cur,physical_at,label):
    """A posted estimated receipt of 10 at its own raw warehouse, at physical_at, through the Native purchase writers."""
    p=prod();p.admin(cur);p.zone(cur,'Asia/Jakarta');p.prior.set_open_period(cur,date.fromisoformat(physical_at[:10])-timedelta(days=1))
    material=p.prior.clone_material(cur,'cutover-'+label);loc=uuid.uuid4()
    cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active)values(%s,%s,'CP17 cutover gudang','RAW_MATERIAL_WAREHOUSE',true)",
                (loc,'CUTO-'+loc.hex[:20]))
    draft=p.rpc(cur,'erp.save_material_purchase_draft_v2',dict(purchase_number='CP17-CUTO-'+str(uuid.uuid4()),supplier_id=p.prior.BASE_SUPPLIER,location_id=loc,
        physical_at=physical_at,change_reason='CP17 D15-5 penerimaan',lines=[dict(material_id=material,qty=10,unit_price=10,price_state='ESTIMATED',
        price_source='MANUAL_ESTIMATE',rolls=[dict(roll_number='CP17-CUTO-ROLL-'+str(uuid.uuid4()),qty=10)])]))
    cur.execute('select erp.post_material_purchase_v2(%s,%s,%s,%s)',(uuid.UUID(draft['purchase_id']),uuid.uuid4(),int(draft['row_version']),'CP17 D15-5 penerimaan'))
    b.api.admin(cur)
    return dict(material=str(material),location=str(loc),stock=one(cur,'select coalesce(sum(qty_signed),0) from erp.material_stock_movements where material_id=%s and location_id=%s',(material,loc)))
def income(f,amount,physical_at):
    p=misc.save_payload(f,'OTHER_INCOME',amount);p['physical_at']=physical_at;return p
def misc_journals(cur,ident):
    b.api.admin(cur);return [list(r) for r in cur.execute("select economic_date::text,status,source_type from erp.journal_entries where source_id=%s order by posting_at,id",(ident,)).fetchall()]


def cases(cur,today):
    import cp7_cp17_fix_cases as cp17
    def set_boundary():
        o=owner(cur);L,op,batch=latest(cur);w=ws(cur,o)
        assert (w['version'],w['current'],w['history'],w['latest_allowed'],w['can_set'])==(0,None,[],str(L),True),w
        assert (w['earliest_operational'] or {}).get('date')==(op and str(op)) and (w['earliest_import'] or {}).get('date')==(batch and str(batch)),w
        before=b.boundary.snapshot(cur)
        code='CP7_CUTOVER_OPERATIONAL_BEFORE' if op==L else 'CP7_CUTOVER_IMPORT_BEFORE'
        one_day_late=refused(cur,lambda:put(cur,o,L+timedelta(days=1),0),code)
        cp17.unchanged(cur,before,'cutover one day after the first operational day');assert control(cur)==(0,None)
        key=uuid.uuid4();r=put(cur,o,L,0,'Mulai pakai aplikasi di Enteng',key)
        assert (r['version'],r['cutover_date'],r['previous_date'])==(1,str(L),None) and control(cur)==(1,L),r
        assert put(cur,o,L,0,'Mulai pakai aplikasi di Enteng',key)==r
        refused(cur,lambda:put(cur,o,L-timedelta(days=1),0,'Mulai pakai aplikasi di Enteng',key),'CP7_CUTOVER_REQUEST_CHANGED')
        refused(cur,lambda:put(cur,o,L-timedelta(days=1),0),'CP7_CUTOVER_STALE')
        refused(cur,lambda:put(cur,o,L,1),'CP7_CUTOVER_NO_CHANGE')
        refused(cur,lambda:put(cur,o,date(1999,12,31),1),'CP7_CUTOVER_DATE')
        adm,gud=master.role_actor(cur,'ADMIN'),master.role_actor(cur,'GUDANG')
        assert ws(cur,adm)['can_set'] is False
        refused(cur,lambda:put(cur,adm,L-timedelta(days=2),1),'CP7_CUTOVER_DENIED')
        refused(cur,lambda:ws(cur,gud),'CP7_CUTOVER_DENIED')
        r2=put(cur,o,L-timedelta(days=5),1,'Tanggal dibetulkan lebih awal')
        assert (r2['version'],r2['cutover_date'],r2['previous_date'])==(2,str(L-timedelta(days=5)),str(L))
        w=ws(cur,o);assert w['current']['cutover_date']==str(L-timedelta(days=5)) and [h['version'] for h in w['history']]==[2,1]
        b.api.admin(cur)
        refused(cur,lambda:cur.execute("update cp7_cutover.history set reason='diubah' where version=1"),'CP7_CUTOVER_HISTORY_IMMUTABLE')
        refused(cur,lambda:cur.execute('delete from cp7_cutover.control'),'CP7_CUTOVER_HISTORY_IMMUTABLE')
        assert one(cur,'select count(*) from cp7_cutover.history')==2
        return dict(status='PASS',latest_allowed=str(L),first_operational_day=str(op),first_import_cutover=str(batch),one_day_late_refused=one_day_late,
                    set_on_the_first_day=True,same_uuid_same_answer=True,changed_payload_refused=True,stale_refused=True,admin_reads_not_sets=True,
                    gudang_denied=True,moved_earlier_with_history=[str(L),str(L-timedelta(days=5))],history_immutable=True)
    def day_boundary():
        o=owner(cur);L,_,_=latest(cur);put(cur,o,L,0,'Mulai pakai aplikasi di Enteng')
        f=misc.fixture(cur,today)
        on=misc.command(cur,'POST',misc.intent(misc.command(cur,'SAVE',income(f,'11.11',f'{L}T00:00:00+07:00'))))
        assert [j[:2] for j in misc_journals(cur,on['transaction_id'])]==[[str(L),'POSTED']],misc_journals(cur,on['transaction_id'])
        before=b.boundary.snapshot(cur)
        day_before=f'{L-timedelta(days=1)}T23:59:59+07:00'
        journal=refused(cur,lambda:misc.command(cur,'POST',misc.intent(misc.command(cur,'SAVE',income(f,'22.22',day_before)))),'CP7_CUTOVER_BEFORE')
        assert str(L-timedelta(days=1)) in journal and str(L) in journal,journal
        cp17.unchanged(cur,before,'misc income on the day before cutover')
        r=receipt_at(cur,f'{L}T00:00:00+07:00','on');assert D(r['stock'])==10,r
        before=b.boundary.snapshot(cur)
        stock=refused(cur,lambda:receipt_at(cur,day_before,'before'),'CP7_CUTOVER_BEFORE')
        cp17.unchanged(cur,before,'receipt on the day before cutover')
        return dict(status='PASS',cutover=str(L),income_at_00_00_on_the_day_posted=True,income_at_23_59_59_day_before_refused=journal,
                    receipt_at_00_00_on_the_day_posted=True,receipt_day_before_refused=stock)
    def opening_path():
        o=owner(cur);L,_,_=latest(cur);put(cur,o,L,0,'Mulai pakai aplikasi di Enteng')
        early=refused(cur,lambda:bbp.api.call(cur,'CREATE',dict(batch_code='CUTO'+uuid.uuid4().hex[:10],cutover_date=str(L-timedelta(days=1)))),'CP7_CUTOVER_IMPORT_DATE')
        rows=bbp.p03_rows(L);gl0=bbp.gl(cur)
        batch,code,cutover=bbp.post_batch(cur,today,rows,cutover_days=(today-L).days,prefix='CUTO');assert cutover==L
        b.api.admin(cur)
        supplier,cash=cur.execute('select s.id,c.id from erp.suppliers s cross join erp.cash_accounts c where s.supplier_code=%s and c.cash_account_code=%s',(code,code)).fetchone()
        item,receipt_date,cutover_date=cur.execute("""select l.purchase_item_id,h.receipt_date,h.cutover_date from erp.initial_import_receipt_lines l
            join erp.initial_import_receipt_headers h on h.purchase_id=l.purchase_id where h.batch_id=%s""",(batch,)).fetchone()
        # The original receipt date stays in the import table; the opening rows post on the official date.
        assert (receipt_date,cutover_date)==(L-timedelta(days=20),L),(receipt_date,cutover_date)
        assert one(cur,"select min(economic_date) from erp.journal_entries where source_type like 'OPENING%%' and source_id in(select id from erp.opening_balance_headers where migration_batch_id=%s)",(batch,))==L
        balance=one(cur,"""select b.id from erp.initial_import_financial_sources f join erp.opening_subledger_balances b on b.opening_item_id=f.opening_item_id
            where f.batch_id=%s and f.balance_type='SUPPLIER_PAYABLE'""",(batch,))
        imported=bbp.p03_state(cur,item)
        assert (imported['qty'],imported['posted'],imported['match'],imported['unit_cost'],imported['grni'],imported['native_ap'])==(10,4,'PARTIAL',D('2.200000'),D('12.00'),0),imported
        # Late invoice on the opening receipt, dated after cutover: posts on its path, closes GRNI once, AP once (no double count).
        row=dict(supplier_id=str(supplier),purchase_item_id=str(item))
        posted=bbp.receipt_trial.post_invoice(bbp.api,cur,bbp.receipt_trial.invoice(bbp.api,cur,today,row,'6','2.25',date=today-timedelta(days=2)))
        invoiced=bbp.p03_state(cur,item)
        assert (invoiced['grni'],invoiced['native_ap'],invoiced['match'],invoiced['unit_cost'])==(0,D('13.50'),'MATCHED',D('2.350000')),invoiced
        b.api.admin(cur)
        assert one(cur,"select min(economic_date) from erp.journal_entries where source_id=%s",(posted['supplier_invoice_id'],))>=L
        # Settlement of the AP invoiced before cutover: refused before cutover by its own path, posts after it, paid once.
        settle=lambda day:bbp.act(cur,'OPENING_SETTLEMENT',batch,operation='SETTLE',balance_id=str(balance),amount='7.00',effective_date=str(day),
                                   cash_account_id=str(cash),reason='CP17 D15-5 pelunasan saldo awal')
        before_settle=refused(cur,lambda:settle(L-timedelta(days=1)),'BB_OSS_DATE_OUT_OF_RANGE')
        settle(L+timedelta(days=1));b.api.admin(cur)
        assert one(cur,'select original_amount-settled_amount from erp.opening_subledger_balances where id=%s',(balance,))==0
        # Correction of the old document on its path: reversing the late invoice restores the opening state exactly.
        bbp.receipt_trial.rpc(bbp.api,cur,'reverse_material_supplier_invoice_v2',posted['supplier_invoice_id'],'CP17 D15-5 balik invoice terlambat',uuid.uuid4(),posted['row_version'])
        reversed_state=bbp.p03_state(cur,item)
        assert (reversed_state['grni'],reversed_state['unit_cost'],reversed_state['match'])==(D('12.00'),D('2.200000'),'PARTIAL'),reversed_state
        assert bbp.detectors_ok(cur) is True
        return dict(status='PASS',cutover=str(L),import_before_cutover_refused=early,original_receipt_date_kept=str(receipt_date),opening_on_cutover=True,
                    late_invoice_after_cutover_posted=posted['supplier_invoice_id'],grni_and_ap_once=True,settlement_before_cutover_refused=before_settle,
                    settled_after_cutover_once=True,old_document_correction_on_its_path=True,detectors_clean=True,gl_moved=bbp.moved(gl0,bbp.gl(cur)))
    def failure_midway():
        o=owner(cur);L,_,_=latest(cur);put(cur,o,L,0,'Mulai pakai aplikasi di Enteng')
        f=misc.fixture(cur,today)
        old=misc.command(cur,'POST',misc.intent(misc.command(cur,'SAVE',income(f,'30.01',f'{L}T08:00:00+07:00'))))
        before=b.boundary.snapshot(cur);private=misc_fix.private_state(cur);journals=misc_journals(cur,old['transaction_id'])
        # The correction reverses the original (allowed) and posts its replacement on the day before cutover (refused):
        # the whole command rolls back, the original stays posted, nothing private is left.
        p=misc_fix.payload(f,old,'30.01');p['replacement']['physical_at']=f'{L-timedelta(days=1)}T08:00:00+07:00'
        detail=refused(cur,lambda:misc_fix.correct(cur,p),'CP7_CUTOVER_BEFORE')
        cp17.unchanged(cur,before,'misc correction moved before cutover')
        assert misc_fix.private_state(cur)==private and misc_journals(cur,old['transaction_id'])==journals
        assert misc.native_document(cur,old['transaction_id'])['status']=='POSTED'
        # The same correction kept on the cutover day is accepted.
        p=misc_fix.payload(f,old,'25.01');r=misc_fix.correct(cur,p);misc_fix.check(cur,f,old,r)
        return dict(status='PASS',cutover=str(L),inverse_then_refused_replacement_left_nothing=detail,original_still_posted=True,
                    lawful_correction_on_the_day_posted=r['transaction_id'])
    def resend():
        o=owner(cur);L,_,_=latest(cur)
        late=uuid.uuid4();first=refused(cur,lambda:put(cur,o,L+timedelta(days=1),0,key=late),'CP7_CUTOVER_')
        again=refused(cur,lambda:put(cur,o,L+timedelta(days=1),0,key=late),'CP7_CUTOVER_');assert again==first and control(cur)==(0,None)
        key=uuid.uuid4();r=put(cur,o,L,0,key=key);assert put(cur,o,L,0,key=key)==r and one(cur,'select count(*) from cp7_cutover.history')==1
        f=misc.fixture(cur,today);saved=misc.command(cur,'SAVE',income(f,'12.34',f'{L-timedelta(days=1)}T09:00:00+07:00'))
        k=uuid.uuid4();before=b.boundary.snapshot(cur)
        a1=refused(cur,lambda:misc.command(cur,'POST',misc.intent(saved),key=k),'CP7_CUTOVER_BEFORE')
        a2=refused(cur,lambda:misc.command(cur,'POST',misc.intent(saved),key=k),'CP7_CUTOVER_BEFORE')
        assert a1==a2;cp17.unchanged(cur,before,'refused post resent')
        ok=misc.command(cur,'SAVE',income(f,'12.35',f'{L}T09:00:00+07:00'));k2=uuid.uuid4()
        p1=misc.command(cur,'POST',misc.intent(ok),key=k2);p2=misc.command(cur,'POST',misc.intent(ok),key=k2)
        assert p1==p2 and len(misc_journals(cur,ok['transaction_id']))==1
        return dict(status='PASS',refused_set_resent_refused_again=first,set_resent_same_answer=True,refused_post_resent_refused_again=a1,
                    posted_resent_same_answer_one_journal=True)
    named=[set_boundary,day_boundary,opening_path,failure_midway,resend]
    assert len(named)==len(NATIVE)
    return list(zip(NATIVE,named))


def races(tools,today):
    def two(fns):
        barrier=threading.Barrier(len(fns))
        def go(fn):
            with tools.connect()as conn,conn.cursor()as cur:
                barrier.wait(5)
                try:r=fn(cur);conn.commit();return('PASS',r)
                except psycopg.Error as e:conn.rollback();return('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=len(fns))as pool:return [x.result(60) for x in [pool.submit(go,fn) for fn in fns]]
    def setup():
        with tools.connect()as conn,conn.cursor()as cur:
            o=owner(cur);v,d=control(cur);L,_,_=latest(cur);conn.commit();return o,v,d,L
    def teardown(o):
        with tools.connect()as conn,conn.cursor()as cur:reset(cur,o);conn.commit()
    def two_tabs():
        o,v,_,L=setup()
        try:
            results=two([lambda cur:put(cur,o,L,v,'Tab satu'),lambda cur:put(cur,o,L-timedelta(days=1),v,'Tab dua')])
            assert sorted(x[0] for x in results)==['PASS','REFUSED'] and 'CP7_CUTOVER_STALE' in next(x[1] for x in results if x[0]=='REFUSED'),results
            won=next(x[1] for x in results if x[0]=='PASS')
            with tools.connect()as conn,conn.cursor()as cur:
                assert control(cur)==(v+1,date.fromisoformat(won['cutover_date'])) and one(cur,'select max(version) from cp7_cutover.history')==v+1
        finally:teardown(o)
        return dict(status='PASS',one_tab_won=won['cutover_date'],other_refused_stale=True,one_history_row=True)
    def set_vs_post():
        o,v,d,L=setup()
        with tools.connect()as conn,conn.cursor()as cur:f=misc.fixture(cur,today);conn.commit()
        with tools.connect()as conn,conn.cursor()as cur:saved=misc.command(cur,'SAVE',income(f,'5.55',f'{L-timedelta(days=1)}T10:00:00+07:00'));conn.commit()
        try:
            results=two([lambda cur:put(cur,o,L,v,'Mulai pakai aplikasi'),lambda cur:misc.command(cur,'POST',misc.intent(saved))])
            kinds=[x[0] for x in results]
            assert sorted(kinds)==['PASS','REFUSED'],results
            with tools.connect()as conn,conn.cursor()as cur:
                posted=[j for j in misc_journals(cur,saved['transaction_id']) if j[1]=='POSTED'];state=control(cur)
            if kinds[0]=='PASS':
                assert 'CP7_CUTOVER_BEFORE' in results[1][1] and posted==[] and state==(v+1,L),(results,posted,state)
            else:
                assert 'CP7_CUTOVER_OPERATIONAL_BEFORE' in results[0][1] and len(posted)==1 and state==(v,d),(results,posted,state)
        finally:teardown(o)
        return dict(status='PASS',winner='set' if kinds[0]=='PASS' else 'post',loser=next(x[1] for x in results if x[0]=='REFUSED')[:160],
                    never_both=True)
    return list(zip(RACES,[two_tabs,set_vs_post]))


def http_cases(http,today):
    def cutover():
        owner_user=http.login('OWNER','cp17-cutover');admin_user=http.login('ADMIN','cp17-cutover-admin')
        w=owner_user.rpc('erp_cp7_get_cutover_v1',{});assert w['status']==200 and w['body']['can_set'] is True,w
        v,L=w['body']['version'],date.fromisoformat(w['body']['latest_allowed'])
        body=dict(action='SET',expected_version=v,cutover_date=str(L),reason='Mulai pakai aplikasi lewat HTTP');key=str(uuid.uuid4())
        try:
            denied=admin_user.rpc('erp_cp7_set_cutover_v1',dict(p_payload=body,p_request=str(uuid.uuid4())));assert denied['status'] in(401,403) and 'CP7_CUTOVER_DENIED' in str(denied['body']),denied
            late=owner_user.rpc('erp_cp7_set_cutover_v1',dict(p_payload=dict(body,cutover_date=str(L+timedelta(days=1))),p_request=str(uuid.uuid4())))
            assert late['status']==400 and 'CP7_CUTOVER_' in str(late['body']),late
            r=owner_user.rpc('erp_cp7_set_cutover_v1',dict(p_payload=body,p_request=key));assert r['status']==200 and r['body']['cutover_date']==str(L),r
            again=owner_user.rpc('erp_cp7_set_cutover_v1',dict(p_payload=body,p_request=key));assert again['status']==200 and again['body']==r['body'],again
            changed=owner_user.rpc('erp_cp7_set_cutover_v1',dict(p_payload=dict(body,reason='Alasan lain lewat HTTP'),p_request=key))
            assert changed['status']==400 and 'CP7_CUTOVER_REQUEST_CHANGED' in str(changed['body']),changed
        finally:
            with http.connect()as conn,conn.cursor()as cur:reset(cur,owner(cur));conn.commit()
        return dict(status='PASS',real_Auth_owner_set=str(L),admin_refused=denied['status'],one_day_late_400=True,same_uuid_same_answer=True,changed_payload_400=True)
    return list(zip(HTTP,[cutover]))
