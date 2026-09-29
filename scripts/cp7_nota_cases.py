"""Selected-card Nota oracles: source entitlement, native allocation, retry and isolation."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
import json,threading,time,uuid
import psycopg
import cp7_nota_source_cases as source
import cp6_bf_combined_probe as combined
auth,b,fg,book=source.auth,source.b,source.fg,source.book

def facts(cur):
    # Full movement/HPP/journal rows, with only the P10 book presentation rank
    # excluded. Canonical UTC prevents different connection TimeZones changing
    # JSON timestamp spellings and masquerading as a business mutation.
    zone=cur.execute('show timezone').fetchone()[0]
    try:
        cur.execute("select set_config('TimeZone','UTC',true)")
        return book.facts(cur)
    finally:cur.execute("select set_config('TimeZone',%s,true)",(zone,))

def read(cur,section='NOTES',subject=None,**query):
    auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_nota_workspace_v1(%s,%s)',(section,json.dumps(query))).fetchone()[0];b.api.admin(cur);return r
def command(cur,action,p,version=None,key=None,subject=None):
    auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_save_nota_v1(%s,%s,%s,%s)',(action,json.dumps(p),key or uuid.uuid4(),None if version is None else str(version))).fetchone()[0];b.api.admin(cur);return r
def payload(cur,f,today,**extra):
    cards=read(cur,'SOURCES',contractor_id=f['contractor'])['page']['rows']
    return dict(contractor_id=f['contractor'],note_date=str(today),period_start=str(today),period_end=str(today),notes='Nota selected native components',cards=[dict(card_key=c['card_key'],source_token=c['source_token']) for c in cards],**extra)
def act(cur,action,n,key=None,subject=None):
    return command(cur,action,dict(id=n['note_id'],change_reason='Reviewed selected source components'),n['row_version'],key,subject)
def note(cur,n,subject=None):return read(cur,subject=subject,id=n['note_id'])['page']['rows'][0]
def seed_header(cur,f,start,end):
    pid=uuid.uuid4();cur.execute('insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end) values(%s,%s,%s,%s,%s)',(pid,'P12-CONTROL-'+pid.hex,f['contractor'],start,end));return str(pid)
def native_allocate(cur,pid,line,qty):
    v=cur.execute('select row_version from erp.payroll_settlements where id=%s',(pid,)).fetchone()[0]
    b.chain.production.owner(cur);cur.execute('select erp.merge_eligible_work_into_payroll_v2(%s,%s,%s,%s)',(pid,json.dumps([dict(source_type=line['source_type'],source_id=line['source_id'],qty=qty)]),uuid.uuid4(),v));b.api.admin(cur)

def cases(cur,today):
    def lifecycle():
        f=source.repair(cur,today);source.ax.post(cur,source.ax.repair_payload(f,1));p=payload(cur,f,today);before=book.facts(cur)
        n=command(cur,'SAVE',p);d=note(cur,n);assert d['status']=='DRAFT' and len(d['cards'])==2 and Decimal(d['amount'])==6000
        assert cur.execute('select count(*) from erp.payroll_work_items i join erp.payroll_settlements p on p.id=i.payroll_id where p.contractor_id=%s',(f['contractor'],)).fetchone()[0]==0 and book.facts(cur)==before
        auth.refused(cur,lambda:command(cur,'SAVE',p),'CP7_NOTA_CARD_IN_OTHER_DRAFT')
        key=uuid.uuid4();posted=act(cur,'POST',n,key);assert act(cur,'POST',n,key)==posted
        d=note(cur,posted);assert d['status']=='POSTED' and d['payroll_status']=='CALCULATED' and Decimal(d['amount'])==6000
        assert cur.execute('select labor_total,net_payable,settled_at from erp.payroll_settlements where id=%s',(posted['payroll_id'],)).fetchone()==(Decimal(6000),Decimal(6000),None)
        assert cur.execute('select count(*),sum(qty_payable),sum(amount) from erp.payroll_work_items where payroll_id=%s',(posted['payroll_id'],)).fetchone()==(2,3,Decimal(6000))
        assert read(cur,'SOURCES',contractor_id=f['contractor'])['page']['total']=='0' and cur.execute('select count(*) from cp7_payroll.card_claims').fetchone()[0]==0
        assert book.facts(cur)==before
        auth.refused(cur,lambda:act(cur,'POST',posted),'CP7_NOTA_LOCKED')
        return dict(status='PASS',two_receipt_cards_one_contractor=True,ordinary_header_creation_and_native_merge=True,expected_labor='6000',components_qty=3,posting_not_payment=True,exact_replay_once=True,no_duplicate_fg_hpp_journal=True)
    def draft_edit_void():
        f=source.repair(cur,today);p=payload(cur,f,today);n=command(cur,'SAVE',p);d=note(cur,n)
        assert read(cur,'SOURCES',contractor_id=f['contractor'])['page']['rows'][0]['claimed_by_note']==n['note_id']
        updated=command(cur,'SAVE',dict(p,id=n['note_id'],notes='Changed review note'),n['row_version'])
        auth.refused(cur,lambda:command(cur,'SAVE',dict(p,id=n['note_id']),n['row_version']),'CP7_NOTA_STALE_VERSION')
        void=act(cur,'VOID',updated);assert note(cur,void)['status']=='VOID' and note(cur,void)['cards']==d['cards']
        assert read(cur,'SOURCES',contractor_id=f['contractor'])['page']['rows'][0]['claimed_by_note'] is None
        next_note=command(cur,'SAVE',p);assert next_note['note_id']!=n['note_id']
        return dict(status='PASS',draft_edit_exact_version=True,void_retains_snapshot_and_releases_card=True,no_payroll_reservation_from_draft=True)
    def target_append():
        f=source.repair(cur,today,1);n=command(cur,'SAVE',payload(cur,f,today));posted=act(cur,'POST',n)
        source.ax.post(cur,source.ax.repair_payload(f,1));p=payload(cur,f,today,target_payroll_id=posted['payroll_id']);n2=command(cur,'SAVE',p)
        options=read(cur,'PAYROLLS',contractor_id=f['contractor'],limit=1);assert options['page']['rows'][0]['id']==posted['payroll_id']
        b.chain.production.owner(cur);cur.execute('select erp.recalculate_payroll(%s)',(posted['payroll_id'],));b.api.admin(cur)
        before=book.facts(cur);auth.refused(cur,lambda:act(cur,'POST',n2),'CP7_NOTA_PAYROLL_TARGET_CHANGED');assert book.facts(cur)==before
        n2=command(cur,'SAVE',dict(p,id=n2['note_id']),n2['row_version']);p2=act(cur,'POST',n2)
        assert p2['payroll_id']==posted['payroll_id'] and cur.execute('select labor_total from erp.payroll_settlements where id=%s',(posted['payroll_id'],)).fetchone()[0]==4000
        assert read(cur,contractor_id=f['contractor'])['page']['total']=='2'
        return dict(status='PASS',two_notes_append_to_one_explicit_payroll=True,expected_labor='4000',concurrent_target_edit_requires_review=True)
    def stale_source():
        f=source.repair(cur,today);p=payload(cur,f,today);n=command(cur,'SAVE',p);line=note(cur,n)['cards'][0]['lines'][0]
        other=seed_header(cur,f,today+timedelta(days=1),today+timedelta(days=7));native_allocate(cur,other,line,1)
        before=book.facts(cur);count=cur.execute('select count(*) from erp.payroll_settlements').fetchone()[0]
        auth.refused(cur,lambda:act(cur,'POST',n),'CP7_NOTA_SOURCE_CHANGED')
        assert note(cur,n)['status']=='DRAFT' and cur.execute('select count(*) from erp.payroll_settlements').fetchone()[0]==count and book.facts(cur)==before
        return dict(status='PASS',external_native_partial_allocation_invalidates_card=True,new_header_and_allocation_roll_back_together=True)
    def exact_and_access():
        f=source.repair(cur,today);p=payload(cur,f,today);other=source.repair(cur,today);before=book.facts(cur)
        auth.refused(cur,lambda:command(cur,'SAVE',dict(p,contractor_id=other['contractor'])),'CP7_NOTA_DIFFERENT_CONTRACTOR')
        auth.refused(cur,lambda:command(cur,'SAVE',dict(p,cards=p['cards']*2)),'CP7_NOTA_EXACT_CARD')
        auth.refused(cur,lambda:command(cur,'SAVE',dict(p,cards=[dict(p['cards'][0],rate='1')])),'CP7_NOTA_EXACT_CARD')
        subject,role=source.procurement.custom(cur,('production.fg_handoff.view','production.fg_handoff.post'))
        n=command(cur,'SAVE',p,subject=subject);ops=note(cur,n,subject)
        assert not {'rate','amount','remaining_amount'}.intersection(source.keys(ops))
        key=uuid.uuid4();posted=act(cur,'POST',n,key,subject);assert not {'rate','amount','remaining_amount'}.intersection(source.keys(note(cur,posted,subject)))
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.fg_handoff.post'",(role,));auth.refused(cur,lambda:act(cur,'POST',n,key,subject),'CP7_NOTA_WRITE_DENIED')
        assert book.facts(cur)==before
        for who in ('anon','authenticated','service_role','cp7_capture'):assert not cur.execute("select has_schema_privilege(%s,'cp7_payroll','USAGE')",(who,)).fetchone()[0]
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege('cp7_nota_write',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
        assert not cur.execute("select has_column_privilege('cp7_payroll_header','erp.payroll_settlements','labor_total','INSERT,UPDATE') or has_table_privilege('cp7_payroll_header','erp.payroll_work_items','INSERT,UPDATE,DELETE')").fetchone()[0]
        return dict(status='PASS',forged_incomplete_duplicate_and_other_contractor_refused=True,operational_post_no_money=True,current_permission_before_cached_replay=True,command_no_erp_dml=True,header_only_identity_insert_and_row_lock=True)
    def cancel_release():
        f=source.repair(cur,today);n=command(cur,'SAVE',payload(cur,f,today));posted=act(cur,'POST',n);before=book.facts(cur);snapshot=note(cur,posted)['cards']
        b.chain.production.owner(cur);cur.execute('select erp.cancel_unpaid_payroll(%s,%s)',(posted['payroll_id'],'Native release of selected Nota allocation'));b.api.admin(cur)
        d=note(cur,posted);assert d['status']=='POSTED' and d['payroll_status']=='REVERSED' and d['cards']==snapshot and read(cur,'SOURCES',contractor_id=f['contractor'])['page']['rows'][0]['remaining_amount']=='4000.00'
        next_note=command(cur,'SAVE',payload(cur,f,today));act(cur,'POST',next_note);assert book.facts(cur)==before
        return dict(status='PASS',native_cancel_releases_source=True,posted_note_history_retained=True,new_note_can_allocate_released_entitlement=True,no_second_labor_accrual=True)
    def ordinary_rework():
        f=combined.fixture(cur,today);wash=combined.wash(cur,f,range(4),11);combined.finish(cur,f,[wash],range(4),13,bs={3:2})
        bs=b.one(cur,"select id::text from erp.bs_cases where po_id=%s and product_id=%s and status='OPEN'",f['po'],f['roots'][3])
        b.chain.bs_action(cur,'CLASSIFY_BS',dict(bs_case_id=bs,cause_source='UNKNOWN',components=[dict(work_component_id=combined.prod.COMPONENT,completed_before_bs_qty=0)],change_reason='Two components not earned before BS'),b.chain.version(cur,'bs_cases',bs))
        component=b.one(cur,'select id::text from erp.bs_case_components where bs_case_id=%s and work_component_id=%s',bs,combined.prod.COMPONENT)
        bom=b.one(cur,'select erp.resolve_rework_accessory_bom_v1(%s,%s)::text',bs,f['when'](15))
        made=b.chain.bs_action(cur,'SAVE_REWORK',dict(rework_number='P12-RW-'+uuid.uuid4().hex[:10],bs_case_id=bs,destination_type='CONTRACTOR',contractor_id=combined.prod.CONTRACTOR,vendor_id=None,qty_sent=2,physical_sent_at=f['when'](15).isoformat(),status='IN_PROGRESS',return_fg_location_id=combined.base.LOCATION,accessory_bom_version_id=bom,accessory_bom_item_ids=[],change_reason='Actual mandor repairs two source components',components=[dict(bs_case_component_id=component,qty_performed=2)]));rid=made['result']['rework_order_id']
        assert not [c for c in read(cur,'SOURCES',contractor_id=combined.prod.CONTRACTOR)['page']['rows'] if c['source_type']=='REWORK']
        b.chain.bs_action(cur,'COMPLETE_REWORK',dict(rework_order_id=rid,qty_good=2,qty_bs=0,completed_at=f['when'](16).isoformat(),return_fg_location_id=combined.base.LOCATION,change_reason='Two repaired pieces completed'),b.chain.version(cur,'rework_orders',rid))
        card=[c for c in read(cur,'SOURCES',contractor_id=combined.prod.CONTRACTOR)['page']['rows'] if c['origin_id']==rid][0]
        assert card['source_type']=='REWORK' and card['bs_case_id']==bs and card['lines'][0]['remaining_qty']=='2' and Decimal(card['lines'][0]['rate'])==30 and Decimal(card['remaining_amount'])==60,card
        p=dict(contractor_id=combined.prod.CONTRACTOR,note_date=str(today),period_start=str(today),period_end=str(today),cards=[dict(card_key=card['card_key'],source_token=card['source_token'])]);before=book.facts(cur);n=command(cur,'SAVE',p);posted=act(cur,'POST',n)
        assert cur.execute('select labor_total from erp.payroll_settlements where id=%s',(posted['payroll_id'],)).fetchone()[0]==60 and book.facts(cur)==before
        return dict(status='PASS',ordinary_completed_contractor_rework=True,no_card_before_completion=True,newly_payable_components=2,native_rate='30',labor='60',not_all_regular_work_auto_populated=True)
    return [('P12_NOTA_'+k,fn) for k,fn in [('SAVE_POST_REPLAY',lifecycle),('DRAFT_EDIT_VOID',draft_edit_void),('TARGET_APPEND',target_append),('STALE_SOURCE',stale_source),('EXACT_ACCESS',exact_and_access),('CANCEL_RELEASE',cancel_release),('ORDINARY_REWORK',ordinary_rework)]]

def races(tools,today):
    def claims():
        with tools.connect() as conn,conn.cursor() as cur:f=source.repair(cur,today);p=payload(cur,f,today);conn.commit()
        gate=threading.Barrier(2)
        def send():
            with tools.connect() as conn,conn.cursor() as cur:
                gate.wait()
                try:r=command(cur,'SAVE',p);conn.commit();return ('PASS',r)
                except psycopg.Error as e:conn.rollback();return ('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=2) as pool:r=list(pool.map(lambda _:send(),range(2)))
        assert sorted(x[0] for x in r)==['PASS','REFUSED'],r
        with tools.connect() as conn,conn.cursor() as cur:assert cur.execute('select count(*) from cp7_payroll.notes').fetchone()[0]==1 and cur.execute('select count(*) from cp7_payroll.card_claims').fetchone()[0]==1
        return dict(status='PASS',two_concurrent_drafts_one_card_one_winner=True,no_partial_losing_note=True)
    def replay():
        with tools.connect() as conn,conn.cursor() as cur:f=source.repair(cur,today);n=command(cur,'SAVE',payload(cur,f,today));conn.commit()
        key=uuid.uuid4();gate=threading.Barrier(2)
        def send():
            with tools.connect() as conn,conn.cursor() as cur:gate.wait();r=act(cur,'POST',n,key);conn.commit();return r
        with ThreadPoolExecutor(max_workers=2) as pool:r=list(pool.map(lambda _:send(),range(2)))
        assert r[0]==r[1]
        with tools.connect() as conn,conn.cursor() as cur:assert cur.execute('select count(*),sum(amount) from erp.payroll_work_items where payroll_id=%s',(r[0]['payroll_id'],)).fetchone()==(1,Decimal(4000))
        return dict(status='PASS',concurrent_post_same_uuid_exact_outcome=True,one_native_header_allocation=True)
    def revoke():
        with tools.connect() as conn,conn.cursor() as cur:
            f=source.repair(cur,today);n=command(cur,'SAVE',payload(cur,f,today));subject,role=source.procurement.custom(cur,('production.fg_handoff.view','production.fg_handoff.post'));conn.commit()
        with tools.connect() as holder,holder.cursor() as h:
            h.execute('select id from cp7_payroll.notes where id=%s for update',(n['note_id'],))
            def send():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:act(cur,'POST',n,subject=subject);conn.commit();return 'UNEXPECTED_SUCCESS'
                    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(send);blocked=False;deadline=time.monotonic()+8
                try:
                    with tools.connect(autocommit=True) as inspect,inspect.cursor() as c:
                        while time.monotonic()<deadline:
                            c.execute('select pg_stat_clear_snapshot()');blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and pid<>pg_backend_pid())").fetchone()[0]
                            if blocked:break
                            time.sleep(.03)
                        assert blocked,'EXPECTED_NOTE_ROW_WAIT';c.execute('update erp.app_users set is_active=false where auth_user_id=%s',(subject,))
                finally:holder.rollback()
                result=future.result(30)
        assert 'ACCESS' in result or 'DENIED' in result,result
        with tools.connect() as conn,conn.cursor() as cur:assert note(cur,n)['status']=='DRAFT' and cur.execute('select count(*) from erp.payroll_settlements where contractor_id=%s',(f['contractor'],)).fetchone()[0]==0
        return dict(status='PASS',current_access_after_actual_note_lock_wait=True,no_partial_header_or_post=True)
    return [('P12_NOTA_RACE_CLAIM',claims),('P12_NOTA_RACE_REPLAY',replay),('P12_NOTA_RACE_REVOKE',revoke)]

def http_cases(http,today):
    def flow():
        ops=http.login('ADMIN','p12-nota-ops')
        with http.connect() as conn,conn.cursor() as cur:
            f=source.repair(cur,today);p=payload(cur,f,today);before=facts(cur);role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
            zone=cur.execute('show timezone').fetchone()[0];raw=[]
            for test_zone in ('Asia/Jakarta','UTC','America/Los_Angeles'):
                cur.execute("select set_config('TimeZone',%s,true)",(test_zone,));raw.append(book.facts(cur));assert facts(cur)==before
            cur.execute("select set_config('TimeZone',%s,true)",(zone,))
            cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
            for perm in ('production.fg_handoff.view','production.fg_handoff.post'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,perm))
            conn.commit()
        args=dict(p_action='SAVE',p_payload=p,p_request=str(uuid.uuid4()),p_expected=None);assert http.anon_rpc('erp_cp7_save_nota_v1',args)['status'] in(401,403)
        r=ops.rpc('erp_cp7_save_nota_v1',args);assert r['status']==200,r;n=r['body']
        args=dict(p_action='POST',p_payload=dict(id=n['note_id'],change_reason='Reviewed HTTP source components'),p_request=str(uuid.uuid4()),p_expected=n['row_version'])
        r=ops.rpc('erp_cp7_save_nota_v1',args);assert r['status']==200,r;assert ops.rpc('erp_cp7_save_nota_v1',args)['body']==r['body']
        d=ops.rpc('erp_cp7_get_nota_workspace_v1',dict(p_section='NOTES',p_query=dict(id=n['note_id'])));assert d['status']==200 and not {'rate','amount','remaining_amount'}.intersection(source.keys(d['body']))
        with http.connect() as conn,conn.cursor() as cur:
            after=facts(cur);assert after==before,dict(before=before,after=after,changed=[k for k in before if before[k]!=after[k]])
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(ops.auth_user_id,));conn.commit()
        assert ops.rpc('erp_cp7_save_nota_v1',args)['status']==403
        return dict(status='PASS',real_auth_http_save_post_replay=True,operational_writer_no_money_fields=True,current_deactivation_denies_replay=True,full_stock_hpp_journal_facts_unchanged=True,canonical_snapshot_invariant_across_three_timezones=True,legacy_snapshot_zone_spellings_differ=len({json.dumps(x,sort_keys=True) for x in raw})>1)
    return [('P12_NOTA_HTTP',flow)]
