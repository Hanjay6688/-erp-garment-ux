"""R3-03 (owner D16-1, "selesain biar gausa sembunyiin"): the Pengaturan ERP screen (admin-settings) connected in the Enteng build.

Native, race and real-Auth HTTP cases for scripts/cp7-src/erp-settings/settings.sql (public.erp_cp7_get_erp_settings_v1, read
only) and for the two Native writers the screen calls exactly as the Aksesori and Laundry pages do
(public.erp_save_accessory_service_action_v1 / public.erp_save_laundry_bd_action_v1, action SET_POLICY, payload built like
src/erpSettingsContract.ts accessoryPolicyPayload / laundryPolicyPayload). Oracles read the Native rows directly
(erp.bc_policy_settings_v1, erp.bc_policy_setting_events_v1, erp.bd_policy_settings_v1, erp.bd_policy_setting_events_v1,
erp.audit_logs, erp.bd_requests_v1, erp.app_role_permissions, cp7_cutover.control/history) and the page texts from the TypeScript
sources (src/accessoryService.ts, src/laundryBd.ts, src/cp6Readiness.ts), never the facade's answer alone. The values the cases
set name no account, category or user: ACC-DEC01 {mode: BOTH_REAL_TIMELINES} (no posting depends on it) and LAU-DEC04
{sale_with_unknown_laundry: ALLOW_PENDING}; committed cases (two tabs, HTTP, browser) put both policies back to their earlier
status and value through the same Native writers.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timezone
from pathlib import Path
import json,re,threading,uuid
import psycopg
import cp7_snapshot_cases as auth
import cp7_master_cases as master
b=auth.b
refused=auth.refused
ROOT=Path(__file__).resolve().parents[1]

NATIVE=['CP17_R3_03_ERP_SETTINGS_FACADE_EQUALS_NATIVE','CP17_R3_03_ERP_SETTINGS_SET_CHANGES_ONLY_THAT_POLICY',
        'CP17_R3_03_ERP_SETTINGS_STALE_VERSION_REFUSED','CP17_R3_03_ERP_SETTINGS_NON_OWNER_REFUSED_BY_NATIVE',
        'CP17_R3_03_ERP_SETTINGS_DENIED_WITHOUT_VIEW','CP17_R3_03_ERP_SETTINGS_VALUES_HIDDEN_FROM_NON_ADMIN',
        'CP17_R3_03_ERP_SETTINGS_FACADE_PRIVATE_AND_READ_ONLY']
RACES=['CP17_RACE_R3_03_ERP_SETTINGS_TWO_TABS_ACCESSORY_POLICY','CP17_RACE_R3_03_ERP_SETTINGS_TWO_TABS_LAUNDRY_POLICY']
HTTP=['CP17_HTTP_R3_03_ERP_SETTINGS_OWNER_ADMIN_AUDITOR']
BROWSER=['CP17_BROWSER_R3_03_ERP_SETTINGS_DESKTOP','CP17_BROWSER_R3_03_ERP_SETTINGS_MOBILE']
REASON='CP17 R3-03 pengaturan dari layar'
FACADE='erp_cp7_get_erp_settings_v1'
KEYS={'ACCESSORY':('ACC-DEC01','ACC-DEC03','ACC-DEC04','ACC-DEC05','ACC-DEC06','ACC-DEC07','ERP-DEC02'),
      'LAUNDRY':('LAU-DEC01','LAU-DEC02','LAU-DEC03','LAU-DEC04','LAU-DEC05','LAU-DEC06')}
TABLES={'ACCESSORY':('erp.bc_policy_settings_v1','erp.bc_policy_setting_events_v1'),'LAUNDRY':('erp.bd_policy_settings_v1','erp.bd_policy_setting_events_v1')}
WRITER={'ACCESSORY':'erp_save_accessory_service_action_v1','LAUNDRY':'erp_save_laundry_bd_action_v1'}
FAMILY_OF={k:f for f,ks in KEYS.items() for k in ks}
# The values the cases set (the server normalizes them to exactly this) and the refusal each writer gives a non-owner.
VALUE={'ACC-DEC01':{'mode':'BOTH_REAL_TIMELINES'},'LAU-DEC04':{'sale_with_unknown_laundry':'ALLOW_PENDING'}}
OWNER_ONLY={'ACCESSORY':'BC_OWNER_ONLY','LAUNDRY':'BD_OWNER_ONLY'}
VIEW_KEY={'ACCESSORY':'warehouse.accessory.view','LAUNDRY':'production.laundry.view'}

def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]
def stamp(t):return t.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
def owner(cur):return master.role_actor(cur,'OWNER')

# ---------------------------------------------------------------- the screen's calls
def payload(key,operation,version,reason=REASON,value=None):
    """Exactly what the screen sends (src/erpSettingsContract.ts accessoryPolicyPayload / laundryPolicyPayload, copied from the
    Aksesori and Laundry pages): the accessory key with an underscore, the laundry key as shown; the version as text."""
    if FAMILY_OF[key]=='ACCESSORY':
        p=dict(policy_key=key.replace('-','_',1),operation=operation,expected_version=version,reason=reason.strip())
        if operation=='SET':p['value']=value
        return p
    p=dict(policy_key=key,operation=operation,expected_version=version,reason=reason.strip())
    if operation=='SET':p['value']=value
    return p
def send(cur,key,operation,version,subject,reason=REASON,value=None,request=None,body=None):
    auth.actor(cur,subject)
    r=one(cur,f'select public.{WRITER[FAMILY_OF[key]]}(%s,%s::jsonb,%s)',('SET_POLICY',json.dumps(body or payload(key,operation,version,reason,value)),str(request or uuid.uuid4())))
    b.api.admin(cur);return r
def read(cur,subject,role='authenticated'):
    auth.actor(cur,subject,role);w=one(cur,f'select public.{FACADE}()');b.api.admin(cur);return w
def policy(w,key):
    fam=next(f for f in w['families'] if f['family']==FAMILY_OF[key])
    return next(p for p in fam['policies'] if p['key']==key)

# ---------------------------------------------------------------- independent oracles
def native(cur,family):
    """One family straight from its Native tables: per key the setting row and every event (newest first)."""
    b.api.admin(cur);settings,events=TABLES[family];out={}
    for key,status,value,version,set_by,set_at,reason in cur.execute(f'select policy_key,status,value,version,set_by,set_at,reason from {settings} order by policy_key').fetchall():
        ev=cur.execute(f'select version,status,value,reason,set_at,set_by,request_id from {events} where policy_key=%s order by version desc',(key,)).fetchall()
        out[key.replace('_','-',1)]=dict(status=status,value=value,version=str(version),set_by=set_by,set_at=set_at,reason=reason,events=ev)
    return out
def both(cur):return dict(ACCESSORY=native(cur,'ACCESSORY'),LAUNDRY=native(cur,'LAUNDRY'))
def user_name(cur,user):
    if user is None:return None
    b.api.admin(cur);row=cur.execute('select full_name from erp.app_users where id=%s',(user,)).fetchone()
    return row[0] if row else 'Pengguna tidak dikenal'
def app_user(cur,subject):b.api.admin(cur);return one(cur,'select id from erp.app_users where auth_user_id=%s',(subject,))
def role_keys(cur,role_code):
    b.api.admin(cur)
    return {r[0] for r in cur.execute('select p.permission_key from erp.app_role_permissions p join erp.app_roles r on r.id=p.role_id where r.role_code=%s',(role_code,)).fetchall()}
def page_texts():
    """The texts the Aksesori and Laundry pages and their readiness summary show, read from their TypeScript sources."""
    def block(path,start):
        src=(ROOT/path).read_text();i=src.index(start);body=src[i:src.index('}',src.index('{',i))]
        return dict(re.findall(r"'([A-Z]{3}-DEC0\d)':\s*'([^']*)'",body))
    label={**block('src/accessoryService.ts','export const POLICY_LABEL'),**block('src/laundryBd.ts','export const LAU_POLICY_LABEL')}
    effect=block('src/cp6Readiness.ts','export const POLICY_EFFECT')
    src=(ROOT/'src/cp6Readiness.ts').read_text()
    choices=src[src.index('const OWNER_CHOICES'):src.index('export const POLICY_EFFECT')]
    status=src[src.index('export function policyStatus'):src.index('export function invoicePolicyMessage')]
    for phrase in('Ditetapkan di aplikasi','Sengaja tidak diaktifkan','Keputusan owner belum diterapkan','Perlu isian owner'):
        assert "'"+phrase+"'" in status,('CP17_R3_03_STATUS_TEXT_NOT_IN_PAGE',phrase)
    keys=set(KEYS['ACCESSORY'])|set(KEYS['LAUNDRY'])
    assert set(label)==keys and set(effect)==keys,('CP17_R3_03_PAGE_TEXTS',sorted(label),sorted(effect))
    return dict(label=label,effect=effect,owner_choice=set(re.findall(r"'([A-Z]{3}-DEC0\d)':\s*\{",choices)))
def status_text(key,status,texts):
    """src/cp6Readiness.ts policyStatus, the summary the Aksesori and Laundry pages show."""
    if status=='SET':return 'Ditetapkan di aplikasi'
    if key=='LAU-DEC05':return 'Sengaja tidak diaktifkan'
    return 'Keputusan owner belum diterapkan' if key in texts['owner_choice'] else 'Perlu isian owner'
def matches(cur,w,admin):
    """The facade equals the Native tables row by row and event by event; hidden fields are null for a non OWNER/ADMIN."""
    texts=page_texts();seen=0
    assert (w['contract_version'],w['business_DML'],w['can_see_values'],w['cutover_visible'])==('cp7.erp-settings.v1',False,admin,admin),w
    assert [f['family'] for f in w['families']]==['ACCESSORY','LAUNDRY']
    for fam in w['families']:
        if not fam['visible']:
            assert fam['policies'] is None and fam['can_set'] is False,fam;continue
        rows=native(cur,fam['family'])
        assert [p['key'] for p in fam['policies']]==list(KEYS[fam['family']]) and set(rows)==set(KEYS[fam['family']]),(fam['family'],sorted(rows))
        for p in fam['policies']:
            n=rows[p['key']];hide=lambda v:v if admin else None
            assert (p['status'],p['version'],p['set_at'])==(n['status'],n['version'],stamp(n['set_at'])),(p['key'],p,n)
            assert (p['value'],p['reason'],p['set_by'])==(hide(n['value']),hide(n['reason']),hide(user_name(cur,n['set_by']))),(p['key'],p)
            assert p['event_count']==len(n['events']),(p['key'],p['event_count'],len(n['events']))
            want=[dict(version=str(v),status=s,value=hide(val),reason=hide(r),set_at=stamp(t),set_by=hide(user_name(cur,by))) for v,s,val,r,t,by,_ in n['events'][:5]]
            assert p['events']==want,(p['key'],p['events'],want)
            assert (p['label'],p['status_text'],p['pending_effect'],p['owner_choice'])==(texts['label'][p['key']],status_text(p['key'],n['status'],texts),
                None if n['status']=='SET' else texts['effect'][p['key']],p['key'] in texts['owner_choice']),(p['key'],p)
            seen+=1
    if admin:
        b.api.admin(cur);version,day=cur.execute('select version,cutover_date from cp7_cutover.control where singleton_id=1').fetchone()
        hist=cur.execute('select recorded_at,app_user,reason from cp7_cutover.history where version=%s',(version,)).fetchone()
        assert w['cutover']==dict(version=version,cutover_date=None if day is None else str(day),set_at=None if hist is None else stamp(hist[0]),
            set_by=None if hist is None else user_name(cur,hist[1]),reason=None if hist is None else hist[2],change_on='Impor data awal'),w['cutover']
        choices(cur,w['choices'])
    else:assert w['cutover'] is None and w['choices'] is None,w
    return seen
def choices(cur,c):
    """Pick lists: each a bounded, ordered copy of the Native rows (at most 100 per account type / per list), with full counts."""
    b.api.admin(cur)
    accounts=cur.execute("select id::text,account_code,account_name,account_type from erp.chart_accounts where is_active and is_postable and account_type in('ASSET','EXPENSE','REVENUE') order by account_code,id").fetchall()
    per={};kept=[]
    for a in accounts:
        per[a[3]]=per.get(a[3],0)+1
        if per[a[3]]<=100:kept.append(dict(id=a[0],code=a[1],name=a[2],type=a[3]))
    assert c['accounts']==kept and c['accounts_total']==len(accounts),('CP17_R3_03_ACCOUNTS',len(c['accounts']),len(kept))
    cats=cur.execute('select id::text,category_name from erp.accessory_categories where is_active order by category_name,id').fetchall()
    users=cur.execute('select id::text,full_name from erp.app_users where is_active order by full_name,id').fetchall()
    zones=cur.execute('select z.location_id::text,l.location_code,l.location_name,z.zone_kind from erp.bc_accessory_zones_v1 z join erp.locations l on l.id=z.location_id order by l.location_name,z.location_id').fetchall()
    assert c['categories']==[dict(id=i,name=n) for i,n in cats[:100]] and c['categories_total']==len(cats)
    assert c['users']==[dict(id=i,name=n) for i,n in users[:100]] and c['users_total']==len(users)
    assert c['zones']==[dict(id=i,code=k,name=n,kind=z) for i,k,n,z in zones[:100]] and c['zones_total']==len(zones)
def bookkeeping(cur,request):
    """Native side rows of one SET_POLICY request: the audit row the accessory router writes, the request row the laundry router keeps."""
    b.api.admin(cur)
    return (one(cur,"select count(*) from erp.audit_logs where entity_type='bc_policy_settings_v1' and entity_id=%s",(request,)),
            one(cur,"select count(*) from erp.bd_requests_v1 where action='SET_POLICY' and request_id=%s",(request,)))

# ---------------------------------------------------------------- committed-case restore (two tabs, HTTP, browser)
def state_of(n):return dict(status=n['status'],value=n['value'])
def restore(cur,subject,key,prior,via=None):
    """Put one policy back to its earlier status and value through the same Native writer (the version moves on)."""
    n=native(cur,FAMILY_OF[key])[key]
    if (n['status'],n['value'])==(prior['status'],prior['value']):return n['version']
    op,val=('SET',prior['value']) if prior['status']=='SET' else ('CLEAR',None)
    if via:via(key,op,n['version'],val)
    else:send(cur,key,op,n['version'],subject,'CP17 R3-03 kembali ke keadaan sebelum uji',val)
    return native(cur,FAMILY_OF[key])[key]['version']


def cases(cur,today):
    import cp7_cp17_fix_cases as c
    def facade_equals_native():
        o=owner(cur)
        # Non-default state first, through the Native writers, so the equality covers set values, reasons, names and events.
        for key in VALUE:send(cur,key,'SET',native(cur,FAMILY_OF[key])[key]['version'],o,value=VALUE[key])
        w=read(cur,o);seen=matches(cur,w,True)
        assert seen==13 and all(f['can_set'] and f['visible'] for f in w['families']),[(f['family'],f['can_set']) for f in w['families']]
        for key in VALUE:
            p=policy(w,key);assert (p['status'],p['value'],p['set_by'],p['reason'])==('SET',VALUE[key],user_name(cur,app_user(cur,o)),REASON),p
        return dict(status='PASS',policies=seen,families=['ACCESSORY 7','LAUNDRY 6'],events_per_policy='last 5, newest first',
                    texts_equal_page_sources=True,cutover_equals_cp7_cutover=True,choices_bounded_and_equal=True)
    def set_only_that_policy():
        o=owner(cur);user=app_user(cur,o);out={}
        for key in VALUE:
            family=FAMILY_OF[key];before=both(cur);request=uuid.uuid4();assert bookkeeping(cur,request)==(0,0)
            version=before[family][key]['version']
            r=send(cur,key,'SET',version,o,value=VALUE[key],request=request)
            after=both(cur);n=after[family][key]
            assert (n['status'],n['value'],n['version'],n['set_by'],n['reason'])==('SET',VALUE[key],str(int(version)+1),user,REASON),n
            new=n['events'][0]
            assert len(n['events'])==len(before[family][key]['events'])+1 and new[:4]==(int(version)+1,'SET',VALUE[key],REASON) and new[5]==user and new[6]==request,new
            # Every other policy of both families, and its events, is unchanged.
            for fam in after:
                for k in after[fam]:
                    if k!=key:assert after[fam][k]==before[fam][k],('CP17_R3_03_OTHER_POLICY_CHANGED',k)
            books=bookkeeping(cur,request)
            assert books==((1,0) if family=='ACCESSORY' else (0,1)),books
            # The same request again (the screen's recovery): the same answer, nothing new.
            again=send(cur,key,'SET',version,o,value=VALUE[key],request=request)
            if family=='LAUNDRY':
                assert again.get('replayed') is True,again;again={k:v for k,v in again.items() if k!='replayed'}
            assert again==r and both(cur)==after and bookkeeping(cur,request)==books,(again,r)
            assert str(r['version'])==n['version'] and r['request_id']==str(request) and r['action']=='SET_POLICY',r
            # CLEAR through the same writer: back to pending without a value, one more event.
            send(cur,key,'CLEAR',n['version'],o)
            cleared=native(cur,family)[key]
            assert (cleared['status'],cleared['value'],cleared['version'],cleared['events'][0][1])==('PENDING_POLICY_VALUE',None,str(int(version)+2),'PENDING_POLICY_VALUE'),cleared
            w=read(cur,o);matches(cur,w,True)
            assert policy(w,key)['version']==cleared['version'] and policy(w,key)['status_text']!='Ditetapkan di aplikasi'
            out[key]=dict(set_version=n['version'],same_uuid_same_answer=True,cleared_version=cleared['version'])
        return dict(status='PASS',writers=WRITER,only_that_policy_and_one_event=True,other_12_unchanged=True,**out)
    def stale_refused():
        o=owner(cur);out={}
        for key in VALUE:
            family=FAMILY_OF[key];v=native(cur,family)[key]['version']
            send(cur,key,'SET',v,o,value=VALUE[key])
            before=b.boundary.snapshot(cur);rows=both(cur)
            stale=refused(cur,lambda:send(cur,key,'SET',v,o,value=VALUE[key]),'STALE_VERSION');c.unchanged(cur,before,'stale version '+key)
            # The version is compared as text, as the screen sends it; a number is refused the same way.
            number=refused(cur,lambda:send(cur,key,'SET',None,o,body=dict(payload(key,'SET',v,value=VALUE[key]),expected_version=int(v)+1)),'STALE_VERSION')
            c.unchanged(cur,before,'numeric version '+key);assert both(cur)==rows
            out[key]=dict(stale=stale,numeric_version=number)
        return dict(status='PASS',**out)
    def non_owner_refused():
        o=owner(cur);admin=master.role_actor(cur,'ADMIN');auditor=master.role_actor(cur,'AUDITOR_VIEW_ONLY')
        # ADMIN holds settings.erp.manage (and both read keys), so only its role can refuse it.
        keys=role_keys(cur,'ADMIN')
        assert {'settings.erp.view','settings.erp.manage','warehouse.accessory.view','production.laundry.view'}<=keys,sorted(keys)
        # A custom role holding settings.erp.manage too, not OWNER.
        manager=custom(cur,('settings.erp.view','settings.erp.manage','warehouse.accessory.view','production.laundry.view'))
        w=read(cur,admin);matches(cur,w,True)
        assert [f['can_set'] for f in w['families']]==[False,False],w['families']
        assert [f['can_set'] for f in read(cur,manager)['families']]==[False,False]
        for key in VALUE:send(cur,key,'SET',native(cur,FAMILY_OF[key])[key]['version'],o,value=VALUE[key])
        out={}
        for key in VALUE:
            family=FAMILY_OF[key];v=native(cur,family)[key]['version'];before=b.boundary.snapshot(cur)
            by_admin=refused(cur,lambda:send(cur,key,'CLEAR',v,admin),OWNER_ONLY[family]);c.unchanged(cur,before,'admin '+key)
            # The accessory router's own first gate (require_internal) refuses a role that is neither OWNER, ADMIN nor STAFF.
            other='Internal ERP access required' if family=='ACCESSORY' else OWNER_ONLY[family]
            by_manager=refused(cur,lambda:send(cur,key,'CLEAR',v,manager),other);c.unchanged(cur,before,'custom manager '+key)
            by_auditor=refused(cur,lambda:send(cur,key,'CLEAR',v,auditor),other);c.unchanged(cur,before,'auditor '+key)
            out[key]=dict(admin=by_admin,custom_manage_role=by_manager,auditor=by_auditor)
        return dict(status='PASS',admin_holds_settings_erp_manage=True,screen_can_set_for_admin=False,**out)
    def denied_without_view():
        o=owner(cur);gudang=master.role_actor(cur,'GUDANG');produksi=master.role_actor(cur,'PRODUKSI_QC')
        assert 'settings.erp.view' not in role_keys(cur,'GUDANG') and 'settings.erp.view' not in role_keys(cur,'PRODUKSI_QC')
        inactive=master.role_actor(cur,'OWNER');b.api.admin(cur);cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(inactive,))
        before=b.boundary.snapshot(cur);out={}
        for label,fn in(('GUDANG',lambda:read(cur,gudang)),('PRODUKSI_QC',lambda:read(cur,produksi)),('inactive OWNER',lambda:read(cur,inactive)),
                        ('no ERP user',lambda:read(cur,str(uuid.uuid4()))),('anon token',lambda:read(cur,o,'anon'))):
            out[label]=refused(cur,fn,'CP7_ERP_SETTINGS_DENIED')
        c.unchanged(cur,before,'denied settings reads')
        b.api.admin(cur)
        for who in('anon','service_role'):
            assert not one(cur,"select has_function_privilege(%s,'public.erp_cp7_get_erp_settings_v1()','EXECUTE')",(who,)),who
        return dict(status='PASS',denied=out,anon_and_service_role_cannot_execute=True)
    def values_hidden():
        o=owner(cur);auditor=master.role_actor(cur,'AUDITOR_VIEW_ONLY')
        assert {'settings.erp.view','warehouse.accessory.view','production.laundry.view'}<=role_keys(cur,'AUDITOR_VIEW_ONLY')
        assert 'settings.erp.manage' not in role_keys(cur,'AUDITOR_VIEW_ONLY')
        for key in VALUE:send(cur,key,'SET',native(cur,FAMILY_OF[key])[key]['version'],o,value=VALUE[key])
        w=read(cur,auditor);seen=matches(cur,w,False)
        assert seen==13 and [f['can_set'] for f in w['families']]==[False,False]
        for key in VALUE:
            p=policy(w,key);assert (p['status'],p['value'],p['reason'],p['set_by'])==('SET',None,None,None),p
            assert all(e['value'] is None and e['reason'] is None and e['set_by'] is None for e in p['events']),p['events']
        # A family is read only with that family's Native read key, as on its own page.
        only=custom(cur,('settings.erp.view',));laundry=custom(cur,('settings.erp.view','production.laundry.view'))
        w1=read(cur,only);w2=read(cur,laundry)
        assert [(f['visible'],f['policies']) for f in w1['families']]==[(False,None),(False,None)],w1['families']
        assert [f['visible'] for f in w2['families']]==[False,True] and matches(cur,w2,False)==6
        return dict(status='PASS',auditor_sees_statuses_only=True,values_reasons_names_hidden=True,cutover_and_choices_hidden=True,
                    family_needs_its_native_read_key=True)
    def private_read_only():
        import cp7_erp_settings_bundle as bundle
        b.api.admin(cur);verified=bundle.verify(cur)
        o=owner(cur);admin=master.role_actor(cur,'ADMIN');auditor=master.role_actor(cur,'AUDITOR_VIEW_ONLY')
        before=b.boundary.snapshot(cur);rows=both(cur)
        for who in(o,admin,auditor):read(cur,who)
        c.unchanged(cur,before,'settings facade reads');assert both(cur)==rows
        inner=refused(cur,lambda:(auth.actor(cur,o),cur.execute('select cp7_erp_settings.workspace()')),'permission denied')
        b.api.admin(cur)
        return dict(status='PASS',verify=verified,reads_change_nothing=True,private_function_refused=inner)
    named=[facade_equals_native,set_only_that_policy,stale_refused,non_owner_refused,denied_without_view,values_hidden,private_read_only]
    assert len(named)==len(NATIVE)
    return list(zip(NATIVE,named))

def custom(cur,keys):
    """An active ERP user of a fresh custom role holding exactly these keys (isolation fixture, as cp7_snapshot_cases.custom_actor)."""
    b.api.admin(cur);role,subject=uuid.uuid4(),str(uuid.uuid4())
    cur.execute("insert into erp.app_roles(id,role_code,role_name,is_system,is_protected,is_active) values(%s,%s,%s,false,false,true)",
                (role,'R303_'+role.hex[:12].upper(),'CP17 R3-03 '+role.hex))
    for key in keys:cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,key))
    cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active) values(%s,%s,'CP17 R3-03 actor','STAFF',%s,true)",(uuid.uuid4(),subject,role))
    return subject


def races(tools,today):
    def two(fn,args):
        barrier=threading.Barrier(len(args))
        def go(a):
            with tools.connect()as conn,conn.cursor()as cur:
                barrier.wait(5)
                try:r=fn(cur,a);conn.commit();return('PASS',r)
                except psycopg.Error as e:conn.rollback();return('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=len(args))as pool:return [x.result(60) for x in [pool.submit(go,a) for a in args]]
    def same_policy(key):
        family=FAMILY_OF[key]
        def run():
            with tools.connect()as conn,conn.cursor()as cur:
                o=owner(cur);rows=native(cur,family);prior=state_of(rows[key]);v=rows[key]['version']
                events=len(rows[key]['events']);conn.commit()
            try:
                # Both tabs read version v and save the same policy with their own request UUID.
                results=two(lambda cur,n:send(cur,key,'SET',v,o,reason=f'CP17 R3-03 tab {n}',value=VALUE[key])['version'],[1,2])
                assert sorted(x[0] for x in results)==['PASS','REFUSED'] and 'STALE_VERSION' in next(x[1] for x in results if x[0]=='REFUSED'),results
                with tools.connect()as conn,conn.cursor()as cur:
                    n=native(cur,family)[key]
                assert (n['status'],n['version'],len(n['events']))==('SET',str(int(v)+1),events+1),n
                winner=next(x for x in results if x[0]=='PASS')
                assert str(winner[1])==n['version'] and n['reason']==f"CP17 R3-03 tab {results.index(winner)+1}",(winner,n['reason'])
                return dict(status='PASS',two_tabs=results,one_change=True,version=n['version'])
            finally:
                with tools.connect()as conn,conn.cursor()as cur:restore(cur,o,key,prior);conn.commit()
        return run
    return list(zip(RACES,[same_policy('ACC-DEC01'),same_policy('LAU-DEC04')]))


def http_cases(http,today):
    def owner_admin_auditor():
        o=http.login('OWNER','cp17-r3-03-owner');a=http.login('ADMIN','cp17-r3-03-admin')
        v=http.login('AUDITOR_VIEW_ONLY','cp17-r3-03-auditor');g=http.login('GUDANG','cp17-r3-03-gudang')
        with http.connect()as conn,conn.cursor()as cur:prior={k:state_of(native(cur,FAMILY_OF[k])[k]) for k in VALUE};conn.rollback()
        def write(user,key,op,version,value=None,request=None):
            return user.rpc(WRITER[FAMILY_OF[key]],dict(p_action='SET_POLICY',p_payload=payload(key,op,version,value=value),p_client_request_id=str(request or uuid.uuid4())))
        def put_back(key,op,version,value):
            r=write(o,key,op,version,value);assert r['status']==200,('CP17_R3_03_HTTP_RESTORE',r)
        try:
            w=o.rpc(FACADE);assert w['status']==200,w
            with http.connect()as conn,conn.cursor()as cur:matches(cur,w['body'],True);conn.rollback()
            out={}
            for key in VALUE:
                family=FAMILY_OF[key]
                with http.connect()as conn,conn.cursor()as cur:version=native(cur,family)[key]['version'];conn.rollback()
                request=uuid.uuid4();r=write(o,key,'SET',version,VALUE[key],request)
                assert r['status']==200 and r['body']['request_id']==str(request),r
                again=write(o,key,'SET',version,VALUE[key],request);body=dict(again['body'])
                if family=='LAUNDRY':assert body.pop('replayed') is True
                assert again['status']==200 and body==r['body'],again
                stale=write(o,key,'SET',version,VALUE[key]);assert stale['status']>=400 and 'STALE_VERSION' in json.dumps(stale['body']),stale
                with http.connect()as conn,conn.cursor()as cur:
                    n=native(cur,family)[key];conn.rollback()
                assert (n['status'],n['value'],n['version'])==('SET',VALUE[key],str(int(version)+1)) and [e[6] for e in n['events']].count(request)==1,n
                denied=write(a,key,'CLEAR',n['version']);assert denied['status']>=400 and OWNER_ONLY[family] in json.dumps(denied['body']),denied
                with http.connect()as conn,conn.cursor()as cur:assert native(cur,family)[key]==n;conn.rollback()
                out[key]=dict(set_version=n['version'],same_uuid_same_answer=True,stale_status=stale['status'],admin_status=denied['status'])
            aw=a.rpc(FACADE);assert aw['status']==200 and [f['can_set'] for f in aw['body']['families']]==[False,False],aw
            vw=v.rpc(FACADE);assert vw['status']==200,vw
            with http.connect()as conn,conn.cursor()as cur:matches(cur,aw['body'],True);matches(cur,vw['body'],False);conn.rollback()
            gw=g.rpc(FACADE);assert gw['status']==403 and 'CP7_ERP_SETTINGS_DENIED' in json.dumps(gw['body']),gw
            anon=http.anon_rpc(FACADE);assert anon['status']>=400,anon
            return dict(status='PASS',real_Auth=True,owner=out,admin_read_values_no_set=True,auditor_statuses_only=True,
                        gudang_status=gw['status'],anon_status=anon['status'])
        finally:
            with http.connect()as conn,conn.cursor()as cur:
                for key in VALUE:restore(cur,None,key,prior[key],via=put_back)
                conn.rollback()
    return list(zip(HTTP,[owner_admin_auditor]))


# ---------------------------------------------------------------- browser fixture operations (cp7_cp17_fix_browser_fixture.py)
def browser_state(cur,p=None):
    """Native rows only: every policy's status, value and version; for the two the journey changes, the newest event too."""
    out={}
    for family in KEYS:
        for key,n in native(cur,family).items():
            out[key]=dict(status=n['status'],value=n['value'],version=n['version'],events=len(n['events']),
                          last=dict(version=n['events'][0][0],status=n['events'][0][1],value=n['events'][0][2],reason=n['events'][0][3],
                                    request_id=None if n['events'][0][6] is None else str(n['events'][0][6])) if key in VALUE else None)
    b.api.admin(cur);return out
def browser_fixture(cur,p):
    """The state before the journey (to put back afterwards), read from the Native rows."""
    state=browser_state(cur);return dict(today=p.get('today'),before=state,prior={k:state_of(state[k]) for k in VALUE})
def browser_restore(cur,p):
    """Both policies back to their earlier status and value through the Native writers, as a fresh owner."""
    o=owner(cur)
    for key in VALUE:restore(cur,o,key,p['prior'][key])
    b.api.admin(cur);return browser_state(cur)
