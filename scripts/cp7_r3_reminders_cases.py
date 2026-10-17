"""R3-03 (owner D16-1): the Reminder menu (admin-reminders) on real data.

Native, race and real-Auth HTTP cases for scripts/cp7-src/manual-reminders/facade.sql (cp7_reminders_bundle.py), spliced
into the CP17 harness through cp7_r3_cases.py, plus the browser fixture operations of cp7_r3_reminders_browser.mjs.
The facade checks the catalog keys settings.reminder.view / settings.reminder.manage and then calls the accepted Native
own-user reminder functions (v2.6.13). Oracles read the Native rows directly (erp.manual_reminders, the reminder rows of
erp.audit_logs, the boundary snapshot that hashes every erp table), never the facade's answer alone: a write changes exactly
the reminder row, its audit row and the Native idempotency row; a resend with the same request id answers the same and
changes nothing; a stale version, another user's reminder, a missing key and a role the Native actor rule refuses all leave
the boundary unchanged. Every actor is a fresh app user (master.role_actor), so its reminder list starts empty.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
import json,re,threading,uuid
import psycopg
import cp7_snapshot_cases as auth
import cp7_master_cases as master
b=auth.b
refused=auth.refused

NATIVE=['CP17_R3_03_REMINDERS_CREATE_EDIT_NATIVE_ROW_AND_AUDIT','CP17_R3_03_REMINDERS_DONE_REOPEN_CANCEL_NATIVE_ROW_AND_AUDIT',
        'CP17_R3_03_REMINDERS_SAME_REQUEST_REPLAYS_IDENTICALLY','CP17_R3_03_REMINDERS_STALE_VERSION_REFUSED',
        'CP17_R3_03_REMINDERS_OTHER_USER_INVISIBLE_AND_NOT_WRITABLE','CP17_R3_03_REMINDERS_DENIED_WITHOUT_KEYS',
        'CP17_R3_03_REMINDERS_NATIVE_ROLE_RULE_KEPT','CP17_R3_03_REMINDERS_READ_FILTERS_PAGING_DUE_WIB',
        'CP17_R3_03_REMINDERS_WINDOW_BEYOND_200_SAID','CP17_R3_03_REMINDERS_FIELDS_REFUSED_UNCHANGED',
        'CP17_R3_03_REMINDERS_FACADE_CLOSED_NO_OWN_WRITES']
RACES=['CP17_RACE_R3_03_REMINDERS_TWO_TABS_EDIT_ONE_WINS','CP17_RACE_R3_03_REMINDERS_DONE_AND_CANCEL_ONE_WINS',
       'CP17_RACE_R3_03_REMINDERS_SAME_REQUEST_TWO_TABS_ONE_WRITE']
HTTP=['CP17_HTTP_R3_03_REMINDERS_OWNER_JOURNEY','CP17_HTTP_R3_03_REMINDERS_ADMIN_AND_LIMITED_ROLES']
BROWSER=['CP17_BROWSER_R3_03_REMINDERS_DESKTOP','CP17_BROWSER_R3_03_REMINDERS_MOBILE']
FUNCTIONS=('erp_cp7_get_reminders_v1','erp_cp7_save_reminder_v1')
FILTERS=('ACTIVE','OPEN','DONE','CANCELLED','ALL')
# The erp tables a Native reminder write may change: the row, its audit row, its idempotency row.
TOUCHED=['audit_logs','idempotency_requests','manual_reminders']
WIB=timezone(timedelta(hours=7))

def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]
def cp17():
    import cp7_cp17_fix_cases as m
    return m
def unchanged(cur,before,what):cp17().unchanged(cur,before,what)

# ---------------------------------------------------------------- the facade as the screen calls it
def get(cur,subject,query=None):
    auth.actor(cur,subject)
    r=one(cur,'select public.erp_cp7_get_reminders_v1(%s::jsonb)',(json.dumps({} if query is None else query),));b.api.admin(cur);return r
def save(cur,subject,action,payload,expected=None,key=None):
    auth.actor(cur,subject)
    r=one(cur,'select public.erp_cp7_save_reminder_v1(%s,%s::jsonb,%s,%s)',
          (action,json.dumps(payload),str(key or uuid.uuid4()),None if expected is None else str(expected)))
    b.api.admin(cur);return r
def now(cur):b.api.admin(cur);return one(cur,'select statement_timestamp()')
def at_wib(day,hour,minute=0):return datetime(day.year,day.month,day.day,hour,minute,tzinfo=WIB)
def wib_today(cur):return now(cur).astimezone(WIB).date()
def iso(value):return value if isinstance(value,str) else value.astimezone(WIB).isoformat(timespec='seconds')
def body(due,title='CP17 R3-03 telepon laundry',note='Tanyakan kiriman susulan',priority='NORMAL',module='Laundry',rid=None):
    return dict(id=rid,title=title,note=note,due_at=iso(due),priority=priority,module=module)
def owner(cur):return master.role_actor(cur,'OWNER')
def app_user(cur,subject):b.api.admin(cur);return str(one(cur,'select id from erp.app_users where auth_user_id=%s',(subject,)))

# ---------------------------------------------------------------- independent oracles (Native rows, read as admin)
ROW="""select r.id::text,r.owner_user_id::text,r.title,r.note,r.due_at,r.priority,r.module,r.status,r.completed_at,r.completed_by::text,
  r.cancelled_at,r.cancelled_by::text,r.cancellation_reason,r.created_by::text,r.updated_by::text,r.last_client_request_id::text,r.row_version
  from erp.manual_reminders r"""
COLS=('id','owner','title','note','due_at','priority','module','status','completed_at','completed_by','cancelled_at','cancelled_by','reason',
      'created_by','updated_by','last_request','row_version')
def row(cur,rid):
    b.api.admin(cur);x=cur.execute(ROW+' where r.id=%s',(rid,)).fetchone();return None if x is None else dict(zip(COLS,x))
def own_rows(cur,subject):
    b.api.admin(cur)
    return [dict(zip(COLS,x)) for x in cur.execute(ROW+' join erp.app_users u on u.id=r.owner_user_id where u.auth_user_id=%s order by r.created_at,r.id',
                                                    (subject,)).fetchall()]
def audits(cur,rid):
    """The Native audit rows of one reminder in write order: (action, reason, row_version, changed_by, content redacted)."""
    b.api.admin(cur)
    return [tuple(x) for x in cur.execute("""select a.action,a.change_reason,(a.new_data->>'row_version')::bigint,a.changed_by::text,
        (a.new_data->>'content_redacted')::boolean from erp.audit_logs a where a.entity_type='manual_reminders' and a.entity_id=%s
        order by (a.new_data->>'row_version')::bigint""",(rid,)).fetchall()]
def counts_of(cur,subject):
    b.api.admin(cur)
    o,d,c=cur.execute("""select count(*)filter(where r.status='OPEN'),count(*)filter(where r.status='DONE'),count(*)filter(where r.status='CANCELLED')
        from erp.manual_reminders r join erp.app_users u on u.id=r.owner_user_id where u.auth_user_id=%s""",(subject,)).fetchone()
    return dict(open=o,done=d,cancelled=c)
def order_of(cur,subject,filter):
    """The oracle's own list order (the Native contract: OPEN, DONE, CANCELLED; URGENT, NORMAL, LOW; due for OPEN else last change; id)."""
    statuses={'ACTIVE':['OPEN','DONE'],'OPEN':['OPEN'],'DONE':['DONE'],'CANCELLED':['CANCELLED'],'ALL':['OPEN','DONE','CANCELLED']}[filter]
    b.api.admin(cur)
    return [x[0] for x in cur.execute("""select r.id::text from erp.manual_reminders r join erp.app_users u on u.id=r.owner_user_id
        where u.auth_user_id=%s and r.status=any(%s) order by case r.status when 'OPEN' then 0 when 'DONE' then 1 else 2 end,
        case r.priority when 'URGENT' then 0 when 'NORMAL' then 1 else 2 end,case when r.status='OPEN' then r.due_at else r.updated_at end,r.id""",
        (subject,statuses)).fetchall()]
def due_state(x,at):
    if x['status']!='OPEN':return None
    today=at.astimezone(WIB).date();day=x['due_at'].astimezone(WIB).date()
    return 'OVERDUE' if x['due_at']<=at else 'TODAY' if day==today else 'TOMORROW' if day==today+timedelta(days=1) else 'LATER'
def due_of(cur,subject,at):
    states=[due_state(x,at) for x in own_rows(cur,subject) if x['status']=='OPEN']
    return dict(overdue=states.count('OVERDUE'),today=states.count('TODAY'),tomorrow=states.count('TOMORROW'),complete=len(states)<=200)
def changed(before,after):
    """The erp tables whose rows differ (the boundary snapshot hashes every erp table); nothing outside erp may move."""
    outside={k:before[k]==after[k] for k in before if k!='erp'}
    assert all(outside.values()),('CP17_R3_03_OUTSIDE_ERP_CHANGED',outside)
    return sorted(k for k in set(before['erp'])|set(after['erp']) if before['erp'].get(k)!=after['erp'].get(k))
def as_actor(cur,claims,sql,args=()):
    """A call with hand-made JWT claims (no subject, or a non-authenticated role)."""
    b.api.admin(cur);cur.execute("select set_config('request.jwt.claim.sub','',true)")
    cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(claims),));cur.execute('set local session authorization authenticated')
    r=one(cur,sql,args);b.api.admin(cur);return r
def native_as(cur,subject,sql,args=()):
    """The accepted Native function called directly as the actor, inside a savepoint that is always rolled back."""
    auth.actor(cur,subject);cur.execute('savepoint r303_native')
    try:return one(cur,sql,args)
    finally:cur.execute('rollback to savepoint r303_native');b.api.admin(cur)
def custom_actor(cur,keys):
    """An active app user of a fresh custom role holding the given catalog keys (isolation fixture)."""
    b.api.admin(cur);role,subject=uuid.uuid4(),str(uuid.uuid4())
    cur.execute("insert into erp.app_roles(id,role_code,role_name,is_system,is_protected,is_active)values(%s,%s,%s,false,false,true)",
                (role,'R303_'+role.hex[:12].upper(),'CP17 R3-03 '+role.hex))
    for key in keys:cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)',(role,key))
    cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)values(%s,%s,'CP17 R3-03 custom',%s,%s,true)",
                (uuid.uuid4(),subject,'R303_'+role.hex[:12].upper(),role))
    return subject
def grant(cur,role_code,keys):
    b.api.admin(cur)
    for key in keys:
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key)select id,%s from erp.app_roles where role_code=%s on conflict do nothing",(key,role_code))
def role_keys(cur,role_code):
    b.api.admin(cur)
    return sorted(x[0] for x in cur.execute("""select p.permission_key from erp.app_role_permissions p join erp.app_roles r on r.id=p.role_id
        where r.role_code=%s and p.permission_key like 'settings.reminder.%%'""",(role_code,)).fetchall())


def cases(cur,today):
    def create_edit():
        s=owner(cur);uid=app_user(cur,s);day=wib_today(cur)+timedelta(days=1);due=at_wib(day,9)
        before=b.boundary.snapshot(cur);key=uuid.uuid4()
        r=save(cur,s,'SAVE',body(due,priority='URGENT'),key=key)
        after=b.boundary.snapshot(cur)
        assert changed(before,after)==TOUCHED,changed(before,after)
        assert after['erp']['manual_reminders']['count']==before['erp']['manual_reminders']['count']+1
        assert (r['kind'],r['action'],r['status'],r['row_version'],r['created'],r['request_id'])==('COMMITTED_OUTCOME','SAVE','OPEN',1,True,str(key)),r
        x=row(cur,r['reminder_id'])
        assert (x['owner'],x['created_by'],x['updated_by'],x['title'],x['note'],x['due_at'],x['priority'],x['module'],x['status'],x['row_version'],x['last_request'])==\
            (uid,uid,uid,'CP17 R3-03 telepon laundry','Tanyakan kiriman susulan',due,'URGENT','Laundry','OPEN',1,str(key)),x
        assert audits(cur,x['id'])==[('INSERT','Manual reminder create',1,uid,True)],audits(cur,x['id'])
        # Edit: the same row, version 2, one UPDATE audit row.
        due2=at_wib(day,14,30);key2=uuid.uuid4();before=b.boundary.snapshot(cur)
        e=save(cur,s,'SAVE',body(due2,title='CP17 R3-03 telepon laundry Intan',note='',priority='LOW',module='Laundry Intan',rid=x['id']),expected=1,key=key2)
        after=b.boundary.snapshot(cur)
        assert changed(before,after)==TOUCHED and after['erp']['manual_reminders']['count']==before['erp']['manual_reminders']['count'],changed(before,after)
        assert (e['action'],e['status'],e['row_version'],e['created'],e['reminder_id'])==('SAVE','OPEN',2,False,x['id']),e
        y=row(cur,x['id'])
        assert (y['title'],y['note'],y['due_at'],y['priority'],y['module'],y['row_version'],y['last_request'],y['updated_by'])==\
            ('CP17 R3-03 telepon laundry Intan','',due2,'LOW','Laundry Intan',2,str(key2),uid),y
        assert audits(cur,x['id'])==[('INSERT','Manual reminder create',1,uid,True),('UPDATE','Manual reminder edit',2,uid,True)],audits(cur,x['id'])
        # Native keeps the private text out of the shared audit log.
        leak=one(cur,"""select count(*) from erp.audit_logs a where a.entity_type='manual_reminders' and a.entity_id=%s
            and (coalesce(a.old_data::text,'')||coalesce(a.new_data::text,'')||coalesce(a.change_reason,'')) ilike '%%telepon%%'""",(x['id'],))
        assert leak==0,leak
        w=get(cur,s,dict(filter='OPEN'))
        assert [(i['id'],i['row_version'],i['title'])for i in w['items']]==[(x['id'],2,'CP17 R3-03 telepon laundry Intan')] and w['counts']==counts_of(cur,s),w
        return dict(status='PASS',create=dict(tables_changed=TOUCHED,row_version=1,audit='INSERT create'),edit=dict(row_version=2,audit='UPDATE edit'),
                    owner_is_actor=True,audit_text_redacted=True,read_back=True)

    def lifecycle():
        s=owner(cur);uid=app_user(cur,s);due=at_wib(wib_today(cur)+timedelta(days=2),8)
        rid=save(cur,s,'SAVE',body(due))['reminder_id'];steps=[]
        def step(action,payload,expected,status,version,audit):
            before=b.boundary.snapshot(cur);o=save(cur,s,action,payload,expected=expected)
            assert changed(before,b.boundary.snapshot(cur))==TOUCHED,action
            assert (o['action'],o['status'],o['row_version'],o['reminder_id'],o['created'])==(action,status,version,rid,False),o
            x=row(cur,rid);assert (x['status'],x['row_version'],x['updated_by'])==(status,version,uid),x
            assert audits(cur,rid)[-1]==('UPDATE','Manual reminder '+audit,version,uid,True),audits(cur,rid)
            steps.append([action,status,version]);return x
        x=step('DONE',dict(id=rid),1,'DONE',2,'complete');assert x['completed_at'] is not None and x['completed_by']==uid,x
        x=step('UNDONE',dict(id=rid),2,'OPEN',3,'reopen');assert x['completed_at'] is None and x['completed_by'] is None,x
        step('DONE',dict(id=rid),3,'DONE',4,'complete')
        before=b.boundary.snapshot(cur)
        not_open=refused(cur,lambda:save(cur,s,'SAVE',body(due,title='Diubah sesudah selesai',rid=rid),expected=4),'CP7_REMINDERS_NOT_OPEN')
        unchanged(cur,before,'edit of a DONE reminder')
        x=step('CANCEL',dict(id=rid,reason='  Sudah ditelepon langsung  '),4,'CANCELLED',5,'cancel')
        assert (x['reason'],x['cancelled_by'])==('Sudah ditelepon langsung',uid) and x['cancelled_at'] is not None and x['completed_at'] is not None,x
        before=b.boundary.snapshot(cur);final={}
        for action,payload,code in (('DONE',dict(id=rid),'CP7_REMINDERS_CANCELLED'),('UNDONE',dict(id=rid),'CP7_REMINDERS_CANCELLED'),
                                    ('CANCEL',dict(id=rid,reason='Batal sekali lagi'),'CP7_REMINDERS_CANCELLED'),('SAVE',body(due,rid=rid),'CP7_REMINDERS_NOT_OPEN')):
            final[action]=refused(cur,lambda:save(cur,s,action,payload,expected=5),code)
        # No delete: the facade has no such action and the Native guard refuses a hard delete by anyone.
        no_action=refused(cur,lambda:save(cur,s,'DELETE',dict(id=rid),expected=5),'CP7_REMINDERS_FIELDS')
        no_delete=refused(cur,lambda:cur.execute('delete from erp.manual_reminders where id=%s',(rid,)),'cannot be deleted')
        unchanged(cur,before,'a cancelled reminder is final')
        active=get(cur,s,dict(filter='ACTIVE'));gone=get(cur,s,dict(filter='CANCELLED'))
        assert active['items']==[] and [(i['id'],i['status'],i['cancellation_reason'],i['due_state'])for i in gone['items']]==[(rid,'CANCELLED','Sudah ditelepon langsung',None)],gone
        return dict(status='PASS',steps=steps,edit_done_refused=not_open,cancelled_final=final,delete_action_refused=no_action,hard_delete_refused=no_delete,
                    audit_actions=[a[1] for a in audits(cur,rid)])

    def replay():
        s=owner(cur);due=at_wib(wib_today(cur)+timedelta(days=1),10);k=[uuid.uuid4() for _ in range(5)];out={}
        first=save(cur,s,'SAVE',body(due),key=k[0]);rid=first['reminder_id']
        def again(name,action,payload,expected,key,answer):
            before=b.boundary.snapshot(cur);r=save(cur,s,action,payload,expected=expected,key=key)
            unchanged(cur,before,'resend '+name);assert r==answer,(name,r,answer);out[name]=r['row_version']
        again('create','SAVE',body(due),None,k[0],first)
        edit=save(cur,s,'SAVE',body(due,title='Diubah sekali',rid=rid),expected=1,key=k[1]);again('edit','SAVE',body(due,title='Diubah sekali',rid=rid),1,k[1],edit)
        done=save(cur,s,'DONE',dict(id=rid),expected=2,key=k[2]);again('done','DONE',dict(id=rid),2,k[2],done)
        back=save(cur,s,'UNDONE',dict(id=rid),expected=3,key=k[3]);again('reopen','UNDONE',dict(id=rid),3,k[3],back)
        gone=save(cur,s,'CANCEL',dict(id=rid,reason='Tidak perlu lagi'),expected=4,key=k[4]);again('cancel','CANCEL',dict(id=rid,reason='Tidak perlu lagi'),4,k[4],gone)
        # Long after, the first request still answers what it answered: one row, one write per request.
        again('create after cancel','SAVE',body(due),None,k[0],first)
        assert len(own_rows(cur,s))==1 and [a[0] for a in audits(cur,rid)]==['INSERT','UPDATE','UPDATE','UPDATE','UPDATE'],audits(cur,rid)
        before=b.boundary.snapshot(cur)
        other_payload=refused(cur,lambda:save(cur,s,'SAVE',body(due,title='Isi lain'),key=k[0]),'CP7_REMINDERS_REQUEST_CHANGED')
        other_writer=refused(cur,lambda:save(cur,s,'CANCEL',dict(id=rid,reason='Tidak perlu lagi'),expected=2,key=k[2]),'CP7_REMINDERS_REQUEST_CHANGED')
        same_writer=refused(cur,lambda:save(cur,s,'UNDONE',dict(id=rid),expected=2,key=k[2]),'CP7_REMINDERS_REQUEST_CHANGED')
        unchanged(cur,before,'request id used with other content')
        return dict(status='PASS',same_answer_no_change=out,one_row=True,audit_rows=5,
                    reused_id=dict(other_payload=other_payload,other_writer=other_writer,same_writer_other_value=same_writer))

    def stale():
        s=owner(cur);due=at_wib(wib_today(cur)+timedelta(days=1),11)
        rid=save(cur,s,'SAVE',body(due))['reminder_id'];save(cur,s,'SAVE',body(due,title='Tab A menang',rid=rid),expected=1)
        before=b.boundary.snapshot(cur);out={}
        for action,payload in (('SAVE',body(due,title='Tab B kalah',rid=rid)),('DONE',dict(id=rid)),('UNDONE',dict(id=rid)),('CANCEL',dict(id=rid,reason='Tab B membatalkan'))):
            out[action]=refused(cur,lambda:save(cur,s,action,payload,expected=1),'CP7_REMINDERS_STALE')
        out['AHEAD']=refused(cur,lambda:save(cur,s,'DONE',dict(id=rid),expected=3),'CP7_REMINDERS_STALE')
        unchanged(cur,before,'stale version')
        x=row(cur,rid);assert (x['title'],x['row_version'],x['status'])==('Tab A menang',2,'OPEN'),x
        return dict(status='PASS',stale_refused=out,row=dict(title=x['title'],row_version=2))

    def other_user():
        a=owner(cur);c=master.role_actor(cur,'ADMIN');due=at_wib(wib_today(cur)+timedelta(days=1),9)
        ra=save(cur,a,'SAVE',body(due,title='Milik owner'))['reminder_id'];rc=save(cur,c,'SAVE',body(due,title='Milik admin'))['reminder_id']
        wa=get(cur,a,dict(filter='ALL'));wc=get(cur,c,dict(filter='ALL'))
        assert [i['id'] for i in wa['items']]==[ra] and [i['id'] for i in wc['items']]==[rc],(wa['items'],wc['items'])
        assert wa['counts']==counts_of(cur,a)=={'open':1,'done':0,'cancelled':0} and wc['counts']==counts_of(cur,c),(wa['counts'],wc['counts'])
        before=b.boundary.snapshot(cur);out={}
        for action,payload in (('SAVE',body(due,title='Diubah orang lain',rid=ra)),('DONE',dict(id=ra)),('UNDONE',dict(id=ra)),('CANCEL',dict(id=ra,reason='Dibatalkan orang lain'))):
            out[action]=refused(cur,lambda:save(cur,c,action,payload,expected=1),'CP7_REMINDERS_NOT_FOUND')
        unchanged(cur,before,"another user's reminder")
        x=row(cur,ra);assert (x['title'],x['row_version'],x['status'])==('Milik owner',1,'OPEN'),x
        return dict(status='PASS',each_sees_only_own=True,writes_on_other=out,row_unchanged=True)

    def denied():
        s=master.role_actor(cur,'ADMIN');q=master.role_actor(cur,'PRODUKSI_QC');due=at_wib(wib_today(cur)+timedelta(days=1),9)
        assert role_keys(cur,'PRODUKSI_QC')==[],role_keys(cur,'PRODUKSI_QC')
        rid=save(cur,s,'SAVE',body(due))['reminder_id']
        role=one(cur,"select id from erp.app_roles where role_code='ADMIN'")
        b.api.admin(cur);cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='settings.reminder.manage'",(role,))
        w=get(cur,s,dict(filter='OPEN'));assert w['can_manage'] is False and [i['id'] for i in w['items']]==[rid],w
        before=b.boundary.snapshot(cur);writes={}
        for label,action,payload,expected in (('CREATE','SAVE',body(due),None),('EDIT','SAVE',body(due,title='Tanpa hak',rid=rid),1),('DONE','DONE',dict(id=rid),1),
                                              ('CANCEL','CANCEL',dict(id=rid,reason='Tanpa hak kelola'),1)):
            writes[label]=refused(cur,lambda:save(cur,s,action,payload,expected=expected),'CP7_REMINDERS_DENIED')
        unchanged(cur,before,'no manage key')
        # Native alone would let this ADMIN complete the reminder: the refusal is the catalog key the facade adds.
        native=native_as(cur,s,'select public.erp_set_my_reminder_done_v1(%s,true,%s,1)',(rid,str(uuid.uuid4())))
        assert native['status']=='DONE' and row(cur,rid)['status']=='OPEN',native
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='settings.reminder.view'",(role,))
        before=b.boundary.snapshot(cur)
        read=refused(cur,lambda:get(cur,s),'CP7_REMINDERS_DENIED')
        no_subject=refused(cur,lambda:as_actor(cur,dict(role='authenticated'),"select public.erp_cp7_get_reminders_v1('{}'::jsonb)"),'CP7_REMINDERS_DENIED')
        anon_claim=refused(cur,lambda:as_actor(cur,dict(sub=s,role='anon'),"select public.erp_cp7_get_reminders_v1('{}'::jsonb)"),'CP7_REMINDERS_DENIED')
        keyless=dict(read=refused(cur,lambda:get(cur,q),'CP7_REMINDERS_DENIED'),write=refused(cur,lambda:save(cur,q,'SAVE',body(due)),'CP7_REMINDERS_DENIED'))
        unchanged(cur,before,'no view key, no subject, no key at all')
        return dict(status='PASS',admin_without_manage=dict(read_ok=True,can_manage=False,writes=writes,native_alone_would_write=True),
                    admin_without_view=read,no_subject=no_subject,anon_claim=anon_claim,produksi_qc=keyless)

    def role_rule():
        due=at_wib(wib_today(cur)+timedelta(days=1),9)
        auditor=master.role_actor(cur,'AUDITOR_VIEW_ONLY');grant(cur,'AUDITOR_VIEW_ONLY',('settings.reminder.view','settings.reminder.manage'))
        custom=custom_actor(cur,('settings.reminder.view','settings.reminder.manage'));staff=master.role_actor(cur,'STAFF')
        b.api.admin(cur);staff_active=one(cur,"select is_active from erp.app_roles where role_code='STAFF'")
        before=b.boundary.snapshot(cur);out={}
        # Both hold both catalog keys, so only the Native actor rule (OWNER/ADMIN/STAFF) can refuse them; it stays refused.
        for name,subject in (('AUDITOR_VIEW_ONLY',auditor),('CUSTOM_ROLE_WITH_KEYS',custom)):
            out[name]=dict(read=refused(cur,lambda:get(cur,subject),'CP7_REMINDERS_ROLE_DENIED'),
                           create=refused(cur,lambda:save(cur,subject,'SAVE',body(due)),'CP7_REMINDERS_ROLE_DENIED'),
                           native_list=refused(cur,lambda:native_as(cur,subject,"select public.erp_list_my_reminders_v1('ALL',1)"),'nternal ERP'),
                           native_save=refused(cur,lambda:native_as(cur,subject,'select public.erp_save_my_reminder_v1(%s::jsonb,%s,null)',
                                                                    (json.dumps(body(due)),str(uuid.uuid4()))),'nternal ERP'))
        # The legacy STAFF role is inactive in the catalog, so the access row itself is not allowed.
        if staff_active is False:out['STAFF_INACTIVE']=refused(cur,lambda:get(cur,staff),'CP7_REMINDERS_DENIED')
        unchanged(cur,before,'role refused by the Native actor rule')
        assert all(own_rows(cur,x)==[] for x in (auditor,custom,staff))
        return dict(status='PASS',refused=out)

    def read_view():
        s=owner(cur);n0=now(cur);today_=n0.astimezone(WIB).date();ids={}
        plan=(('overdue',n0-timedelta(hours=2),'URGENT'),('soon',n0+timedelta(minutes=10),'NORMAL'),('tomorrow',at_wib(today_+timedelta(days=1),9),'LOW'),
              ('later',at_wib(today_+timedelta(days=3),9),'URGENT'),('done',at_wib(today_+timedelta(days=1),11),'NORMAL'),('cancel',at_wib(today_+timedelta(days=4),9),'LOW'))
        for name,due,priority in plan:ids[name]=save(cur,s,'SAVE',body(due,title='R303 '+name,priority=priority))['reminder_id']
        save(cur,s,'DONE',dict(id=ids['done']),expected=1);save(cur,s,'CANCEL',dict(id=ids['cancel'],reason='Tidak jadi dipakai'),expected=1)
        seen={}
        for f in FILTERS:
            w=get(cur,s,dict(filter=f,limit=100));at=datetime.fromisoformat(w['read_at'])
            order=order_of(cur,s,f)
            assert [i['id'] for i in w['items']]==order,(f,[i['title'] for i in w['items']])
            assert (w['filter'],w['page']['total'],w['page']['window'],w['page']['beyond_window'],w['page']['next_offset'],w['page']['shown'])==(f,len(order),len(order),0,None,len(order)),w['page']
            assert w['today']==at.astimezone(WIB).date().isoformat() and w['counts']==counts_of(cur,s) and w['due']==due_of(cur,s,at),(w['today'],w['counts'],w['due'])
            for i in w['items']:
                x=row(cur,i['id'])
                assert (i['status'],i['row_version'],i['title'],datetime.fromisoformat(i['due_at']),i['due_state'])==(x['status'],x['row_version'],x['title'],x['due_at'],due_state(x,at)),(i,x)
            assert w['business_DML'] is False and w['can_manage'] is True and w['contract_version']=='cp7.reminders-workspace.v1'
            seen[f]=[i['title'] for i in w['items']]
        pages=[get(cur,s,dict(filter='ALL',limit=2,offset=o)) for o in (0,2,4)]
        assert [i['id'] for p in pages for i in p['items']]==order_of(cur,s,'ALL')
        assert [p['page']['next_offset'] for p in pages]==[2,4,None] and [p['page']['shown'] for p in pages]==[2,2,2]
        past=get(cur,s,dict(filter='ALL',limit=2,offset=10));assert past['items']==[] and past['page']['shown']==0 and past['page']['next_offset'] is None
        default=get(cur,s);assert (default['filter'],default['page']['limit'],default['page']['offset'])==('ACTIVE',50,0),default['page']
        before=b.boundary.snapshot(cur);bad={}
        for label,q in (('unknown key',dict(filter='ALL',sort='due')),('filter',dict(filter='LATE')),('limit 0',dict(limit=0)),('limit 101',dict(limit=101)),
                        ('offset 200',dict(offset=200)),('limit text',dict(limit='5')),('offset negative',dict(offset=-1)),('fraction',dict(limit=2.5)),
                        ('filter null',dict(filter=None)),('array',[])):
            bad[label]=refused(cur,lambda:get(cur,s,q),'CP7_REMINDERS_QUERY')
        unchanged(cur,before,'query refusals')
        return dict(status='PASS',lists=seen,due_states={k:due_state(row(cur,v),now(cur)) for k,v in ids.items()},paging='3 pages of 2 = ALL in Native order',
                    query_refusals=sorted(bad))

    def window():
        s=owner(cur);due=at_wib(wib_today(cur)+timedelta(days=5),9)
        for n in range(201):save(cur,s,'SAVE',body(due+timedelta(minutes=n),title=f'R303 jendela {n:03d}'))
        order=order_of(cur,s,'OPEN');assert len(order)==201
        head=get(cur,s,dict(filter='OPEN',limit=100));tail=get(cur,s,dict(filter='OPEN',limit=100,offset=100));last=get(cur,s,dict(filter='OPEN',limit=100,offset=199))
        assert tail['page']=={'limit':100,'offset':100,'total':201,'shown':100,'window':200,'window_limit':200,'next_offset':None,'beyond_window':1},tail['page']
        assert head['page']['next_offset']==100 and last['page']['shown']==1 and [i['id'] for i in last['items']]==order[199:200]
        assert [i['id'] for i in head['items']+tail['items']]==order[:200] and order[200] not in {i['id'] for i in head['items']+tail['items']}
        assert head['due']=={'overdue':0,'today':0,'tomorrow':0,'complete':False} and head['counts']=={'open':201,'done':0,'cancelled':0},head['due']
        return dict(status='PASS',open=201,window=200,beyond_window_said=1,due_count_marked_incomplete=True,hidden_is_last_in_native_order=True)

    def fields():
        s=owner(cur);due=at_wib(wib_today(cur)+timedelta(days=1),9);rid=save(cur,s,'SAVE',body(due))['reminder_id']
        before=b.boundary.snapshot(cur);bad={}
        for label,action,payload,expected in (
                ('unknown action','ARCHIVE',dict(id=rid),1),('extra key','SAVE',dict(body(due),color='merah'),None),
                ('missing key','SAVE',{k:v for k,v in body(due).items() if k!='module'},None),('blank title','SAVE',body(due,title='   '),None),
                ('title 201','SAVE',body(due,title='x'*201),None),('note 4001','SAVE',body(due,note='n'*4001),None),
                ('blank module','SAVE',body(due,module='  '),None),('module 81','SAVE',body(due,module='m'*81),None),
                ('priority','SAVE',body(due,priority='HIGH'),None),('due without offset','SAVE',body('2026-10-18T09:00:00'),None),
                ('due not a date','SAVE',body('2026-13-45T09:00:00+07:00'),None),('number field','SAVE',dict(body(due),priority=1),None),
                ('create with expected','SAVE',body(due),1),('edit without expected','SAVE',body(due,rid=rid),None),
                ('id missing','DONE',dict(id=None),1),('id not uuid','DONE',dict(id='bukan-uuid'),1),('expected zero','DONE',dict(id=rid),'0'),
                ('expected text','DONE',dict(id=rid),'satu'),('reason short','CANCEL',dict(id=rid,reason='   ok   '),1),
                ('reason missing','CANCEL',dict(id=rid),1),('reason 1001','CANCEL',dict(id=rid,reason='r'*1001),1),('payload list','DONE',[rid],1)):
            bad[label]=refused(cur,lambda:save(cur,s,action,payload,expected=expected),'CP7_REMINDERS_FIELDS')
        bad['request missing']=refused(cur,lambda:(auth.actor(cur,s),one(cur,'select public.erp_cp7_save_reminder_v1(%s,%s::jsonb,null,%s)',('DONE',json.dumps(dict(id=rid)),'1'))),
                                       'CP7_REMINDERS_FIELDS')
        unchanged(cur,before,'field refusals')
        x=row(cur,rid);assert (x['row_version'],x['status'])==(1,'OPEN'),x
        return dict(status='PASS',refused=sorted(bad),count=len(bad))

    def closed():
        import cp7_reminders_bundle as rb
        b.api.admin(cur);proof=rb.verify(cur)
        defs={x[0]:x[1] for x in cur.execute("""select p.oid::regprocedure::text,lower(pg_get_functiondef(p.oid)) from pg_proc p join pg_namespace n on n.oid=p.pronamespace
            where n.nspname='cp7_reminders' or p.oid in('public.erp_cp7_get_reminders_v1(jsonb)'::regprocedure,'public.erp_cp7_save_reminder_v1(text,jsonb,uuid,text)'::regprocedure)""").fetchall()}
        assert len(defs)==7,sorted(defs)
        for sig,text in defs.items():
            assert not re.search(r'\b(insert\s+into|update\s+[a-z_]+\.[a-z_]+\s+set|delete\s+from|truncate|copy\s)',text),('CP7_REMINDERS_OWN_WRITE',sig)
        writers=sorted(set(re.findall(r'public\.(erp_[a-z_]*my_reminders?[a-z_]*_v1)\(',defs['cp7_reminders.native_write(text,uuid,jsonb,uuid,bigint)'])))
        assert writers==['erp_cancel_my_reminder_v1','erp_save_my_reminder_v1','erp_set_my_reminder_done_v1'],writers
        reads=sorted(set(re.findall(r'\berp\.([a-z_]+)\b(?!\s*\()',' '.join(defs.values()))))
        assert reads==['idempotency_requests'],reads
        s=owner(cur);before=b.boundary.snapshot(cur)
        private=refused(cur,lambda:(auth.actor(cur,s),one(cur,"select cp7_reminders.workspace('{}'::jsonb)")),'permission denied')
        unchanged(cur,before,'private schema from the browser role')
        return dict(status='PASS',bundle=proof,own_writes=0,native_writers=writers,native_tables_read=reads,private_schema_closed=private)

    named=[create_edit,lifecycle,replay,stale,other_user,denied,role_rule,read_view,window,fields,closed]
    assert len(named)==len(NATIVE)
    return list(zip(NATIVE,named))


def races(tools,today):
    def two(fn,args):
        barrier=threading.Barrier(len(args))
        def go(a):
            with tools.connect()as conn,conn.cursor()as cur:
                barrier.wait(5)
                try:r=fn(cur,a);conn.commit();return('PASS',r)
                except psycopg.Error as e:conn.rollback();return('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=len(args))as pool:return [x.result(60) for x in [pool.submit(go,a) for a in args]]
    def setup():
        with tools.connect()as conn,conn.cursor()as cur:
            s=owner(cur);due=at_wib(today+timedelta(days=1),9);rid=save(cur,s,'SAVE',body(due))['reminder_id'];conn.commit()
        return s,due,rid
    def state(rid):
        with tools.connect()as conn,conn.cursor()as cur:return row(cur,rid),audits(cur,rid)
    def edit_twice():
        s,due,rid=setup();titles=['Tab A mengubah','Tab B mengubah']
        results=two(lambda cur,t:save(cur,s,'SAVE',body(due,title=t,rid=rid),expected=1)['row_version'],titles)
        assert sorted(x[0] for x in results)==['PASS','REFUSED'] and 'CP7_REMINDERS_STALE' in next(x[1] for x in results if x[0]=='REFUSED'),results
        winner=titles[[x[0] for x in results].index('PASS')];x,a=state(rid)
        assert (x['title'],x['row_version'])==(winner,2) and [y[0] for y in a]==['INSERT','UPDATE'],(x,a)
        return dict(status='PASS',two_tabs=results,winner=winner,one_update=True)
    def done_and_cancel():
        s,due,rid=setup()
        results=two(lambda cur,a:save(cur,s,a,dict(id=rid) if a=='DONE' else dict(id=rid,reason='Tab kedua membatalkan'),expected=1)['status'],['DONE','CANCEL'])
        assert sorted(x[0] for x in results)==['PASS','REFUSED'] and 'CP7_REMINDERS_STALE' in next(x[1] for x in results if x[0]=='REFUSED'),results
        won=next(x[1] for x in results if x[0]=='PASS');x,a=state(rid)
        assert (x['status'],x['row_version'])==(won,2) and [y[0] for y in a]==['INSERT','UPDATE'],(x,a)
        return dict(status='PASS',two_tabs=results,final=won,one_update=True)
    def same_request():
        s,due,rid=setup();key=uuid.uuid4()
        results=two(lambda cur,_:save(cur,s,'DONE',dict(id=rid),expected=1,key=key),[1,2])
        assert [x[0] for x in results]==['PASS','PASS'] and results[0][1]==results[1][1],results
        x,a=state(rid);assert (x['status'],x['row_version'],x['last_request'])==('DONE',2,str(key)) and [y[0] for y in a]==['INSERT','UPDATE'],(x,a)
        return dict(status='PASS',two_tabs_same_id=[r[1]['row_version'] for r in results],same_answer=True,one_write=True)
    return list(zip(RACES,[edit_twice,done_and_cancel,same_request]))


def http_cases(http,today):
    def call(user,name,args):
        r=user.rpc(name,args);return r['status'],r['body']
    def journey():
        o=http.login('OWNER','cp17-r3-03-reminders');due=iso(at_wib(today+timedelta(days=1),9))
        st,w=call(o,'erp_cp7_get_reminders_v1',dict(p_query=dict(filter='ALL')))
        assert st==200 and w['items']==[] and w['counts']=={'open':0,'done':0,'cancelled':0},(st,w)
        p=dict(id=None,title='CP17 HTTP pengingat',note='Lewat PostgREST',due_at=due,priority='URGENT',module='Laundry');key=str(uuid.uuid4())
        st,c=call(o,'erp_cp7_save_reminder_v1',dict(p_action='SAVE',p_payload=p,p_request=key,p_expected=None));assert st==200 and c['created'] is True,(st,c)
        st,again=call(o,'erp_cp7_save_reminder_v1',dict(p_action='SAVE',p_payload=p,p_request=key,p_expected=None));assert st==200 and again==c,(st,again)
        rid=c['reminder_id'];steps=[]
        def write(action,payload,expected,version,status):
            st,r=call(o,'erp_cp7_save_reminder_v1',dict(p_action=action,p_payload=payload,p_request=str(uuid.uuid4()),p_expected=str(expected)))
            assert st==200 and (r['row_version'],r['status'])==(version,status),(action,st,r)
            with http.connect()as conn,conn.cursor()as cur:x=row(cur,rid)
            assert (x['row_version'],x['status'])==(version,status),x;steps.append([action,version,status])
        write('SAVE',dict(p,id=rid,title='CP17 HTTP pengingat diubah'),1,2,'OPEN')
        st,stale=call(o,'erp_cp7_save_reminder_v1',dict(p_action='SAVE',p_payload=dict(p,id=rid,title='Tab lama'),p_request=str(uuid.uuid4()),p_expected='1'))
        assert st>=400 and 'CP7_REMINDERS_STALE' in json.dumps(stale),(st,stale)
        write('DONE',dict(id=rid),2,3,'DONE');write('UNDONE',dict(id=rid),3,4,'OPEN');write('CANCEL',dict(id=rid,reason='Sudah selesai lewat telepon'),4,5,'CANCELLED')
        with http.connect()as conn,conn.cursor()as cur:
            rows=own_rows(cur,o.auth_user_id);a=audits(cur,rid)
        assert len(rows)==1 and rows[0]['title']=='CP17 HTTP pengingat diubah' and rows[0]['reason']=='Sudah selesai lewat telepon' and len(a)==5,(rows,a)
        st,w=call(o,'erp_cp7_get_reminders_v1',dict(p_query=dict(filter='CANCELLED')))
        assert st==200 and [(i['id'],i['cancellation_reason'])for i in w['items']]==[(rid,'Sudah selesai lewat telepon')],(st,w)
        anon=http.anon_rpc('erp_cp7_get_reminders_v1',dict(p_query={}));assert anon['status']>=400,anon
        return dict(status='PASS',real_Auth=True,created_once_same_answer=True,steps=steps,stale_refused=True,audit_rows=5,anon_status=anon['status'])
    def roles():
        o=http.login('OWNER','cp17-r3-03-rem-owner');a=http.login('ADMIN','cp17-r3-03-rem-admin')
        aud=http.login('AUDITOR_VIEW_ONLY','cp17-r3-03-rem-auditor');qc=http.login('PRODUKSI_QC','cp17-r3-03-rem-qc')
        with http.connect()as conn,conn.cursor()as cur:
            grant(cur,'AUDITOR_VIEW_ONLY',('settings.reminder.view',));keys=dict(auditor=role_keys(cur,'AUDITOR_VIEW_ONLY'),qc=role_keys(cur,'PRODUKSI_QC'));conn.commit()
        assert 'settings.reminder.manage' not in keys['auditor'] and keys['qc']==[],keys
        due=iso(at_wib(today+timedelta(days=1),10))
        def create(user,title):
            st,r=call(user,'erp_cp7_save_reminder_v1',dict(p_action='SAVE',p_payload=dict(id=None,title=title,note='',due_at=due,priority='NORMAL',module='Operasional'),
                                                           p_request=str(uuid.uuid4()),p_expected=None));assert st==200,(st,r);return r['reminder_id']
        ro=create(o,'Milik owner HTTP');ra=create(a,'Milik admin HTTP')
        st,w=call(a,'erp_cp7_get_reminders_v1',dict(p_query=dict(filter='ALL')));assert st==200 and [i['id'] for i in w['items']]==[ra] and w['can_manage'] is True,(st,w)
        st,other=call(a,'erp_cp7_save_reminder_v1',dict(p_action='DONE',p_payload=dict(id=ro),p_request=str(uuid.uuid4()),p_expected='1'))
        assert st>=400 and 'CP7_REMINDERS_NOT_FOUND' in json.dumps(other),(st,other)
        refusals={}
        for name,user,code_read,code_write in (('AUDITOR_VIEW_ONLY',aud,'CP7_REMINDERS_ROLE_DENIED','CP7_REMINDERS_DENIED'),('PRODUKSI_QC',qc,'CP7_REMINDERS_DENIED','CP7_REMINDERS_DENIED')):
            st1,r1=call(user,'erp_cp7_get_reminders_v1',dict(p_query={}))
            st2,r2=call(user,'erp_cp7_save_reminder_v1',dict(p_action='SAVE',p_payload=dict(id=None,title='Coba',note='',due_at=due,priority='NORMAL',module='Operasional'),
                                                           p_request=str(uuid.uuid4()),p_expected=None))
            assert st1>=400 and code_read in json.dumps(r1) and st2>=400 and code_write in json.dumps(r2),(name,st1,r1,st2,r2)
            refusals[name]=dict(read=[st1,code_read],write=[st2,code_write])
        with http.connect()as conn,conn.cursor()as cur:
            assert own_rows(cur,aud.auth_user_id)==[] and own_rows(cur,qc.auth_user_id)==[]
            x=row(cur,ro);assert (x['row_version'],x['status'])==(1,'OPEN'),x
        return dict(status='PASS',admin_sees_only_own=True,admin_on_owner_row='NOT_FOUND',limited=refusals,catalog_keys=keys)
    return list(zip(HTTP,[journey,roles]))


# ---------------------------------------------------------------- browser fixture operations (cp7_cp17_fix_browser_fixture.py)
def browser_state(cur,p):
    """Fixture r303_reminders_state: the Native rows of one browser user's reminders, read as admin, never from the facade."""
    out=[]
    for x in own_rows(cur,p['auth_user_id']):
        out.append(dict(id=x['id'],title=x['title'],note=x['note'],due_wib=x['due_at'].astimezone(WIB).strftime('%Y-%m-%dT%H:%M'),priority=x['priority'],
                        module=x['module'],status=x['status'],row_version=x['row_version'],completed=x['completed_at'] is not None,
                        cancelled=x['cancelled_at'] is not None,reason=x['reason'],last_request=x['last_request'],audits=len(audits(cur,x['id']))))
    b.api.admin(cur);return dict(rows=out)
def browser_roles(cur,p):
    """Fixture r303_reminders_roles: the limited roles of the browser cases. AUDITOR_VIEW_ONLY holds the view key (seeded with every
    view key; made sure here) and not the manage key; PRODUKSI_QC holds no reminder key."""
    grant(cur,'AUDITOR_VIEW_ONLY',('settings.reminder.view',))
    out=dict(auditor=role_keys(cur,'AUDITOR_VIEW_ONLY'),produksi_qc=role_keys(cur,'PRODUKSI_QC'));b.api.admin(cur);return out
