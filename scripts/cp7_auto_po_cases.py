"""Owner D15-6 (Sol SOL-R1-002): Buat Potongan makes its Production Order when the cutting is posted.

Native, race and real-Auth HTTP cases for scripts/cp7-src/cutting-correction/auto-po.sql, spliced into the CP17 r2 harness.
Oracles read the Native rows directly (production_orders, cutting_groups, material_stock_movements, the business boundary
snapshot), never the facade's answer alone. Owner's tests: posting (PO and cutting in one transaction), resend with the same
UUID (same answer, no second PO or stock), failure in the middle (no PO left, its number not used up, nothing moved), and
drafts (no PO, stock or journal).
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json,threading,uuid
import psycopg
import cp7_snapshot_cases as auth
import cp7_cutting_correction_cases as cut
import cp7_master_cases as master
b=auth.b
refused=auth.refused

NATIVE=['CP17_R2_D15_6_AUTO_PO_POST_ONE_TRANSACTION','CP17_R2_D15_6_AUTO_PO_SAME_UUID_SAME_ANSWER','CP17_R2_D15_6_AUTO_PO_FAILURE_MIDWAY_LEAVES_NOTHING',
        'CP17_R2_D15_6_AUTO_PO_DRAFT_NO_STOCK_NO_FINANCE','CP17_R2_D15_6_AUTO_PO_ACCESS_RIGHTS','CP17_R2_D15_6_AUTO_PO_THEN_BAGI_POTONGAN_AND_SEWING']
RACES=['CP17_RACE_R2_D15_6_AUTO_PO_SAME_ROLL_TWO_TABS','CP17_RACE_R2_D15_6_AUTO_PO_SAME_UUID_TWO_TABS']
HTTP=['CP17_HTTP_R2_D15_6_AUTO_PO']
BROWSER=['CP17_BROWSER_R2_D15_6_AUTO_PO_DESKTOP','CP17_BROWSER_R2_D15_6_AUTO_PO_MOBILE']
FUNCTIONS=('erp_cp7_get_cutting_auto_po_v1','erp_cp7_save_cutting_auto_po_v1')
REASON='CP17 D15-6 potongan dengan PO otomatis'

def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]
def prod():return cut.cutting.qc.physical.b.chain.production
def base():return cut.cutting.qc.physical.base
def workspace(cur,q=None,subject=None):
    auth.actor(cur,subject);r=one(cur,'select public.erp_cp7_get_cutting_auto_po_v1(%s::jsonb)',(json.dumps(q or {}),));b.api.admin(cur);return r
def command(cur,body,key=None,subject=None):
    auth.actor(cur,subject);r=one(cur,'select public.erp_cp7_save_cutting_auto_po_v1(%s::jsonb,%s)',(json.dumps(body),str(key or uuid.uuid4())));b.api.admin(cur);return r
def receipt(cur,today):
    """A posted estimated receipt of one roll (10) at its own raw warehouse (the Native writers), as the other CP17 cases."""
    f=prod().estimated_receipt(cur,today);b.api.admin(cur);return f
def cutting(f,qty=10,pieces=10,at=None):
    p=prod();day=f['purchase_day']+timedelta(days=1)
    return dict(pattern_id=str(p.PATTERN),source_location_id=str(f['location']),cut_at=(at or p.at(day,8)).isoformat(),notes=None,
        size_slots=[dict(slot_no=1,size_id=str(base().SIZE),drawing_no=1)],
        rolls=[dict(roll_id=str(f['roll']),qty_issued=qty,qty_consumed=qty,qty_reported_remaining=0,yields=[dict(slot_no=1,qty_pcs=pieces)])])
def post_body(f,draft=None,version=None,**kw):
    return dict(action='POST',draft_id=draft,expected_version=version,model_id=str(prod().MODEL),cutting=cutting(f,**kw),change_reason=REASON)
def prefix(cur,at):return 'PO-'+one(cur,"select to_char(%s::timestamptz at time zone 'Asia/Jakarta','YYMMDD')",(at,))+'-'
def next_number(cur,pre):
    """The oracle's own next free number of that day: count of that day's numbers + 1, then the first free one."""
    b.api.admin(cur);n=one(cur,'select count(*) from erp.production_orders where po_number like %s',(pre+'%',))+1
    while one(cur,'select count(*) from erp.production_orders where po_number=%s',(pre+'%03d'%n,)):n+=1
    return pre+'%03d'%n
def po_state(cur,number):
    b.api.admin(cur)
    row=cur.execute("""select o.id::text,o.status,o.current_stage,o.model_id::text,o.target_qty_pcs,o.contractor_id,o.created_by is not null,o.is_legacy,
        (select count(*) from erp.cutting_groups g where g.po_id=o.id),(select count(*) from erp.cutting_groups g where g.po_id=o.id and g.material_issue_posted)
        from erp.production_orders o where o.po_number=%s""",(number,)).fetchone()
    return None if row is None else dict(id=row[0],status=row[1],stage=row[2],model=row[3],target=row[4],contractor=row[5],created_by=row[6],legacy=row[7],groups=row[8],posted=row[9])
def roll_stock(cur,f):
    b.api.admin(cur);return one(cur,'select coalesce(sum(qty_signed),0) from erp.material_stock_movements where roll_id=%s and location_id=%s',(f['roll'],f['location']))
def po_count(cur):b.api.admin(cur);return one(cur,'select count(*) from erp.production_orders')


def cases(cur,today):
    import cp7_cp17_fix_cases as cp17
    def post_once():
        f=receipt(cur,today);body=post_body(f);expected=next_number(cur,prefix(cur,body['cutting']['cut_at']))
        assert po_state(cur,expected) is None and roll_stock(cur,f)==10
        r=command(cur,body)
        assert r['po_number']==expected and r['total_pieces']==10 and r['material_issue_posted'] is True and r['draft_id'] is None,r
        s=po_state(cur,expected)
        assert s and (s['id'],s['status'],s['stage'],s['model'],s['target'],s['contractor'],s['created_by'],s['legacy'],s['groups'],s['posted'])==(
            r['po_id'],'CUTTING','CUTTING',str(prod().MODEL),10,None,True,False,1,1),s
        assert one(cur,'select po_id::text from erp.cutting_groups where id=%s',(r['cutting_group_id'],))==r['po_id']
        assert roll_stock(cur,f)==0
        b.api.admin(cur);assert one(cur,"select count(*) from cp7_cutting_correction.auto_po_history where po_id=%s and action='POST'",(r['po_id'],))==1
        return dict(status='PASS',po_number=r['po_number'],po_status='CUTTING',cutting=r['group_number'],pieces=10,roll_left=0,one_history_row=True)
    def same_uuid():
        f=receipt(cur,today);body=post_body(f);key=uuid.uuid4();before=po_count(cur)
        r=command(cur,body,key);again=command(cur,body,key)
        assert again==r and po_count(cur)==before+1 and roll_stock(cur,f)==0
        refused(cur,lambda:command(cur,dict(body,change_reason=REASON+' lain'),key),'CP7_AUTO_PO_REQUEST_CHANGED')
        assert po_count(cur)==before+1 and roll_stock(cur,f)==0
        b.api.admin(cur);assert one(cur,"select count(*) from erp.cutting_groups where po_id=%s",(r['po_id'],))==1
        return dict(status='PASS',same_uuid_same_answer=r['po_number'],one_po=True,stock_moved_once=True,changed_payload_refused=True)
    def failure_midway():
        f=receipt(cur,today);body=post_body(f);pre=prefix(cur,body['cutting']['cut_at']);expected=next_number(cur,pre)
        before=b.boundary.snapshot(cur);pos=po_count(cur);reqs=one(cur,'select count(*) from cp7_cutting_correction.auto_po_requests')
        # The facade creates the PO, then the Native writer refuses the cutting (more fabric than the roll holds): nothing stays.
        refused(cur,lambda:command(cur,post_body(f,qty=11)),'SELECTED_ROLL_IS_NOT_AVAILABLE_AT_SOURCE_LOCATION')
        # The Native writer refuses a cutting time in the future after the PO insert too.
        future=prod().at(today+timedelta(days=2),8)
        refused(cur,lambda:command(cur,post_body(f,at=future)),'cannot be in the future')
        # Refused before the PO: a size outside the model.
        bad=post_body(f);b.api.admin(cur)
        other=str(one(cur,"select s.id from erp.sizes s where s.is_active and not exists(select 1 from erp.product_model_sizes m where m.model_id=%s and m.size_id=s.id) limit 1",(prod().MODEL,)) or uuid.uuid4())
        bad['cutting']['size_slots'][0]['size_id']=other
        refused(cur,lambda:command(cur,bad),'CP7_AUTO_PO_SIZE')
        cp17.unchanged(cur,before,'auto PO refusals');assert po_count(cur)==pos and po_state(cur,expected) is None and roll_stock(cur,f)==10
        b.api.admin(cur);assert one(cur,'select count(*) from cp7_cutting_correction.auto_po_requests')==reqs
        r=command(cur,body)
        assert r['po_number']==expected and roll_stock(cur,f)==0,(r,expected)
        return dict(status='PASS',native_refusal_after_po_insert_leaves_no_po=True,future_time_refused=True,size_outside_model_refused=True,
                    boundary_unchanged=True,number_not_used_up=expected)
    def draft_no_effect():
        f=receipt(cur,today);body=post_body(f);before=b.boundary.snapshot(cur);pos=po_count(cur)
        d=command(cur,dict(action='SAVE_DRAFT',draft_id=None,expected_version=None,model_id=body['model_id'],cutting=body['cutting']))
        assert d['row_version']==1;cp17.unchanged(cur,before,'auto PO draft');assert po_count(cur)==pos and roll_stock(cur,f)==10
        w=workspace(cur,dict(draft_id=d['draft_id']))
        assert d['draft_id'] in [x['id'] for x in w['drafts']] and w['selected_draft']['cutting']==body['cutting'] and w['selected_draft']['pattern']['id']==str(prod().PATTERN)
        assert [r['roll_id'] for r in w['selected_draft']['rolls']]==[str(f['roll'])]
        changed=dict(body['cutting'],notes='Catatan draf diubah')
        d2=command(cur,dict(action='SAVE_DRAFT',draft_id=d['draft_id'],expected_version=1,model_id=body['model_id'],cutting=changed))
        assert d2['row_version']==2;cp17.unchanged(cur,before,'auto PO draft edit')
        refused(cur,lambda:command(cur,dict(action='SAVE_DRAFT',draft_id=d['draft_id'],expected_version=1,model_id=body['model_id'],cutting=body['cutting'])),'CP7_AUTO_PO_STALE_DRAFT')
        r=command(cur,dict(post_body(f,draft=d['draft_id'],version=2),cutting=changed))
        assert r['draft_id']==d['draft_id'] and po_state(cur,r['po_number'])['posted']==1
        b.api.admin(cur);assert cur.execute('select status,posted_po_id::text from cp7_cutting_correction.auto_po_drafts where id=%s',(d['draft_id'],)).fetchone()==('POSTED',r['po_id'])
        refused(cur,lambda:command(cur,dict(action='DELETE',draft_id=d['draft_id'],expected_version=3)),'CP7_AUTO_PO_DRAFT_NOT_FOUND')
        assert d['draft_id'] not in [x['id'] for x in workspace(cur)['drafts']]
        return dict(status='PASS',draft_no_po_no_stock_no_journal=True,draft_versions=2,stale_draft_refused=True,draft_posted_once=r['po_number'],posted_draft_closed=True)
    def access():
        gud,aud,qc=master.role_actor(cur,'GUDANG'),master.role_actor(cur,'AUDITOR_VIEW_ONLY'),master.role_actor(cur,'PRODUKSI_QC')
        refused(cur,lambda:workspace(cur,subject=gud),'CP7_AUTO_PO_DENIED')
        w=workspace(cur,subject=aud);assert w['can_draft'] is False and w['can_post'] is False
        f=receipt(cur,today);body=post_body(f);pos=po_count(cur)
        refused(cur,lambda:command(cur,body,subject=aud),'CP7_AUTO_PO_DENIED')
        refused(cur,lambda:command(cur,dict(action='SAVE_DRAFT',draft_id=None,expected_version=None,model_id=body['model_id'],cutting=body['cutting']),subject=aud),'CP7_AUTO_PO_DENIED')
        assert po_count(cur)==pos
        r=command(cur,body,subject=qc);assert po_state(cur,r['po_number'])['posted']==1
        b.api.admin(cur)
        sigs=[x[0] for x in cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where (n.nspname='public' and p.proname like 'erp_cp7_%%auto_po%%') or (n.nspname='cp7_cutting_correction' and p.proname like 'auto_po%%')").fetchall()]
        assert len(sigs)==6 and not any(cur.execute("select has_function_privilege('anon',%s::regprocedure,'EXECUTE')",(sig,)).fetchone()[0] for sig in sigs),sigs
        return dict(status='PASS',no_cutting_view_no_read=True,view_only_reads_not_writes=True,production_staff_posts=r['po_number'],anon_executes_nothing=True)
    def downstream():
        f=receipt(cur,today);r=command(cur,post_body(f));p=prod();day=f['purchase_day']+timedelta(days=1)
        mandor=master.create(cur,'MANDOR',master.mandor_fields('MDR-'+master.tag(),master.wib(day-timedelta(days=30))))['id']
        g=dict(group=r['cutting_group_id'],po=r['po_id'],mandor=mandor,at=lambda h,minute=0:p.at(day,h,minute),day=day)
        cp17.native_pickup(cur,g['group'],mandor,g['at'](9))
        s=po_state(cur,r['po_number']);assert (s['status'],s['stage'],s['contractor'] is not None)==('SEWING','SEWING',True),s
        cp17.work_rates(cur,g)
        w=cp17.sewing_workspace(cur,g);assert w['eligible'],w['blockers']
        cp17.sewing_command(cur,w,qty=10,at=g['at'](10),reason='Setoran jahit PO otomatis')
        assert cp17.sewn_ready(cur,dict(group=g['group']))[0]==10
        return dict(status='PASS',auto_po=r['po_number'],bagi_potongan_assigns_mandor=True,po_sewing=True,sewing_recorded=10)
    named=[post_once,same_uuid,failure_midway,draft_no_effect,access,downstream]
    assert len(named)==len(NATIVE)
    return list(zip(NATIVE,named))


def races(tools,today):
    def two(fn,payloads):
        barrier=threading.Barrier(len(payloads))
        def send(p):
            with tools.connect()as conn,conn.cursor()as cur:
                barrier.wait(5)
                try:r=fn(cur,p);conn.commit();return('PASS',r)
                except psycopg.Error as e:conn.rollback();return('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=len(payloads))as pool:return [x.result(60) for x in [pool.submit(send,p) for p in payloads]]
    def setup():
        with tools.connect()as conn,conn.cursor()as cur:f=receipt(cur,today);pos=po_count(cur);conn.commit();return f,pos
    def same_roll():
        f,pos=setup();body=post_body(f)
        results=two(lambda cur,k:command(cur,body,k),[uuid.uuid4(),uuid.uuid4()])
        assert sorted(x[0] for x in results)==['PASS','REFUSED'],results
        won=next(x[1] for x in results if x[0]=='PASS')
        with tools.connect()as conn,conn.cursor()as cur:
            assert po_count(cur)==pos+1 and roll_stock(cur,f)==0 and po_state(cur,won['po_number'])['posted']==1
        return dict(status='PASS',one_po=won['po_number'],other_tab_refused=next(x[1] for x in results if x[0]=='REFUSED')[:120],stock_moved_once=True)
    def same_uuid():
        f,pos=setup();body=post_body(f);key=uuid.uuid4()
        results=two(lambda cur,k:command(cur,body,k),[key,key])
        assert [x[0] for x in results]==['PASS','PASS'] and results[0][1]==results[1][1],results
        with tools.connect()as conn,conn.cursor()as cur:assert po_count(cur)==pos+1 and roll_stock(cur,f)==0
        return dict(status='PASS',same_answer=results[0][1]['po_number'],one_po=True,stock_moved_once=True)
    return list(zip(RACES,[same_roll,same_uuid]))


def http_cases(http,today):
    def auto_po():
        owner=http.login('OWNER','cp17-auto-po')
        w=owner.rpc('erp_cp7_get_cutting_auto_po_v1',dict(p_query={}));assert w['status']==200 and w['body']['can_post'] is True,w
        with http.connect()as conn,conn.cursor()as cur:f=receipt(cur,today);pos=po_count(cur);conn.commit()
        body=post_body(f);key=str(uuid.uuid4())
        r=owner.rpc('erp_cp7_save_cutting_auto_po_v1',dict(p_payload=body,p_request=key));assert r['status']==200 and r['body']['material_issue_posted'] is True,r
        again=owner.rpc('erp_cp7_save_cutting_auto_po_v1',dict(p_payload=body,p_request=key));assert again['status']==200 and again['body']==r['body'],again
        changed=owner.rpc('erp_cp7_save_cutting_auto_po_v1',dict(p_payload=dict(body,change_reason=REASON+' lain'),p_request=key))
        assert changed['status']==400 and 'CP7_AUTO_PO_REQUEST_CHANGED' in str(changed['body']),changed
        with http.connect()as conn,conn.cursor()as cur:
            assert po_count(cur)==pos+1 and roll_stock(cur,f)==0 and po_state(cur,r['body']['po_number'])['status']=='CUTTING'
        return dict(status='PASS',real_Auth_post=r['body']['po_number'],same_uuid_same_answer=True,changed_payload_400=True)
    return list(zip(HTTP,[auto_po]))
