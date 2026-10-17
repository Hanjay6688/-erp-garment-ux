"""R3-03 (owner D16-1, "selesain biar gausa sembunyiin"): the Audit Trail screen, connected.

Native, race and real-Auth HTTP cases for scripts/cp7-src/audit/audit.sql (public.erp_cp7_get_audit_trail_v1), spliced
into the CP17 harness through cp7_r3_cases.py, plus the browser fixture of cp7_r3_audit_browser.mjs. The rows under test
are written by a Native writer: the master screen facade (erp_cp7_save_master_v1) creates, renames and deactivates a
customer with a reason each time, and the Native audit trigger of erp.customers writes erp.audit_logs. Bulk rows for
paging, the WIB day boundaries and the size bounds are direct admin inserts into erp.audit_logs (an isolation fixture, as
other suites insert audit rows). Every oracle reads erp.audit_logs and erp.app_users directly and recomputes the order,
the filters, the changed keys and the values before and after in Python; the facade's answer is only compared with it.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal
from pathlib import Path
import json,threading,time,uuid
import cp7_snapshot_cases as auth
import cp7_master_cases as master
b=auth.b
refused=auth.refused
ROOT=Path(__file__).resolve().parents[1]

NATIVE=['CP17_R3_03_AUDIT_NATIVE_WRITE_ROWS','CP17_R3_03_AUDIT_FILTERS_AND_PAGING_COMPLETE','CP17_R3_03_AUDIT_DETAIL_ONE_ROW',
        'CP17_R3_03_AUDIT_DENIED_WITHOUT_VIEW','CP17_R3_03_AUDIT_EXPORT_FLAG_FOLLOWS_PERMISSION','CP17_R3_03_AUDIT_LARGE_PAGE_BOUNDED',
        'CP17_R3_03_AUDIT_FACADE_PRIVATE_READ_ONLY']
RACES=['CP17_RACE_R3_03_AUDIT_WRITE_BETWEEN_PAGES','CP17_RACE_R3_03_AUDIT_PAGING_WHILE_WRITER_RUNS']
HTTP=['CP17_HTTP_R3_03_AUDIT_OWNER_READS_LIMITED_REFUSED']
BROWSER=['CP17_BROWSER_R3_03_AUDIT_DESKTOP','CP17_BROWSER_R3_03_AUDIT_MOBILE']
FUNCTIONS=('erp_cp7_get_audit_trail_v1',)
WIB=timezone(timedelta(hours=7))
LOWEST=datetime.min.replace(tzinfo=timezone.utc)
ROW_KEYS={'id','at','entity_type','entity_id','action','actor_id','actor_name','reason','changed_keys','changed_key_count','has_before','has_after'}
DETAIL_KEYS=ROW_KEYS|{'data_bytes','too_large','fields','fields_total','raw_before','raw_after'}
LARGE=524288

def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]
def tag():return uuid.uuid4().hex[:8].upper()
def cp17():
    import cp7_cp17_fix_cases as m
    return m
def read(cur,query,subject=None,role='authenticated'):
    """The facade as a signed-in user (default: the harness operator, an OWNER)."""
    auth.actor(cur,subject,role);r=one(cur,'select public.erp_cp7_get_audit_trail_v1(%s)',(json.dumps(query),));b.api.admin(cur);return r
def person(cur,role_code,name):
    """A fresh active app user of a seeded role with a unique name (isolation fixture, as cp7_master_cases.role_actor)."""
    b.api.admin(cur);subject,user=str(uuid.uuid4()),str(uuid.uuid4())
    role=one(cur,'select id from erp.app_roles where role_code=%s',(role_code,))
    cur.execute('insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)values(%s,%s,%s,%s,%s,true)',(user,subject,name,role_code,role))
    return subject,user
def custom(cur,keys,name):
    """A fresh custom role holding exactly these permission keys, and one active user of it."""
    b.api.admin(cur);role=uuid.uuid4();subject,user=str(uuid.uuid4()),str(uuid.uuid4())
    cur.execute('insert into erp.app_roles(id,role_code,role_name,is_system,is_protected,is_active)values(%s,%s,%s,false,false,true)',(role,'R303_'+role.hex[:12].upper(),'CP17 R3-03 '+name))
    for key in keys:cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)',(role,key))
    cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)values(%s,%s,%s,'STAFF',%s,true)",(user,subject,name,role))
    return subject,user
def holds(cur,role_code,key):
    """Whether a seeded role holds a permission in the Native role matrix (the protected OWNER holds every key)."""
    b.api.admin(cur)
    return one(cur,"""select(r.role_code='OWNER'and r.is_protected)or exists(select 1 from erp.app_role_permissions p join erp.app_permissions k on k.permission_key=p.permission_key and k.is_active
        where p.role_id=r.id and p.permission_key=%s)from erp.app_roles r where r.role_code=%s""",(key,role_code))

# ---------------------------------------------------------------- the oracle (Native rows, recomputed in Python)
def loads(text):return None if text is None else json.loads(text,parse_float=Decimal)
def stored(cur,where,args=()):
    """Native rows straight from erp.audit_logs, the actor's name from erp.app_users."""
    b.api.admin(cur)
    rows=cur.execute(f"""select id,changed_at,entity_type,entity_id::text,action,changed_by::text,change_reason,old_data::text,new_data::text,
        coalesce(octet_length(old_data::text),0)+coalesce(octet_length(new_data::text),0) from erp.audit_logs where {where}""",args).fetchall()
    people={r[5] for r in rows if r[5]}
    names=dict(cur.execute('select id::text,full_name from erp.app_users where id=any(%s::uuid[])',(list(people),)).fetchall()) if people else {}
    return [dict(id=r[0],at=r[1],entity_type=r[2],entity_id=r[3],action=r[4],actor=r[5],name=names.get(r[5]),reason=r[6],old=loads(r[7]),new=loads(r[8]),bytes=r[9])
            for r in rows]
def searched(cur,q):
    """Every Native row whose data id or reason holds the search text (any case)."""
    ql=q.strip().lower()
    return stored(cur,"position(%s in lower(coalesce(entity_id::text,'')))>0 or position(%s in lower(coalesce(change_reason,'')))>0",(ql,ql))
def newest_first(rows):return sorted(rows,key=lambda r:(r['at'] or LOWEST,r['id']),reverse=True)
def day_start(text):return datetime.combine(date.fromisoformat(text),datetime.min.time(),WIB)
def matches(r,f,as_of):
    q=(f.get('q') or '').strip().lower()
    return (r['id']<=as_of and(not f.get('from')or(r['at'] is not None and r['at']>=day_start(f['from'])))
        and(not f.get('to')or(r['at'] is not None and r['at']<day_start(f['to'])+timedelta(days=1)))
        and(not f.get('entity_type')or r['entity_type']==f['entity_type'])and(not f.get('action')or r['action']==f['action'])
        and(not f.get('actor_id')or r['actor']==f['actor_id'])
        and(not q or q in(r['entity_id']or'').lower()or q in(r['reason']or'').lower()))
def expect(rows,f,as_of):return newest_first([r for r in rows if matches(r,f,int(as_of))])
def obj(value):return value if isinstance(value,dict) else {}
def same(a,b):
    """JSON equality as jsonb compares (numbers by value; true is not 1)."""
    if isinstance(a,bool)or isinstance(b,bool):return type(a)is type(b)and a==b
    if isinstance(a,(int,Decimal))and isinstance(b,(int,Decimal)):return Decimal(a)==Decimal(b)
    if isinstance(a,dict)and isinstance(b,dict):return a.keys()==b.keys()and all(same(a[k],b[k])for k in a)
    if isinstance(a,list)and isinstance(b,list):return len(a)==len(b)and all(same(x,y)for x,y in zip(a,b))
    return type(a)is type(b)and a==b
def keyorder(keys):return sorted(keys,key=lambda k:k.encode())
def differs(o,n,k):return (k in o)!=(k in n)or(k in o and not same(o[k],n[k]))
def changed(old,new):
    o,n=obj(old),obj(new)
    return [k for k in keyorder(set(o)|set(n)) if differs(o,n,k)]
def check_rows(answer,oracle):
    """Each row shown equals its stored row: id, time, data, action, actor and name, reason, changed keys; nothing else."""
    assert [r['id'] for r in answer]==[str(o['id']) for o in oracle],('CP17_R3_03_ROWS',[r['id'] for r in answer],[o['id'] for o in oracle])
    for r,o in zip(answer,oracle):
        keys=changed(o['old'],o['new'])
        assert set(r)==ROW_KEYS,sorted(r)
        assert (None if r['at'] is None else datetime.fromisoformat(r['at']))==o['at'],(r['at'],o['at'])
        assert (r['entity_type'],r['entity_id'],r['action'],r['actor_id'],r['actor_name'],r['reason'])==(o['entity_type'],o['entity_id'],o['action'],o['actor'],o['name'],o['reason']),(r,o)
        assert (r['changed_keys'],r['changed_key_count'])==(keys[:30],len(keys)),(r['changed_keys'],keys)
        assert (r['has_before'],r['has_after'])==(o['old'] is not None,o['new'] is not None),r
def shown_text(text,data,key):
    if key not in data or data[key] is None:return text is None
    if isinstance(data[key],str):return text==data[key]
    return text is not None and same(loads(text),data[key])
def check_detail(d,o):
    """The detail of one row: per key the value before and after and whether it changed; withheld above 512 KB."""
    assert set(d)==DETAIL_KEYS,sorted(d)
    check_rows([{k:d[k] for k in ROW_KEYS}],[o])
    large=o['bytes']>LARGE
    assert (d['data_bytes'],d['too_large'])==(o['bytes'],large),(d['data_bytes'],o['bytes'])
    if large:
        assert (d['fields'],d['fields_total'],d['raw_before'],d['raw_after'])==([],0,None,None),d['fields_total'];return
    od,nd=obj(o['old']),obj(o['new']);keys=keyorder(set(od)|set(nd))
    assert d['fields_total']==len(keys) and [f['key'] for f in d['fields']]==keys[:500],(d['fields_total'],len(keys))
    for f in d['fields']:
        assert set(f)=={'key','before','after','changed'} and shown_text(f['before'],od,f['key']) and shown_text(f['after'],nd,f['key']),f
        assert f['changed']==differs(od,nd,f['key']),f
    for side,value in(('raw_before',o['old']),('raw_after',o['new'])):
        if value is None or isinstance(value,dict):assert d[side] is None,(side,d[side])
        else:assert same(loads(d[side]),value),(side,d[side])
def walk(cur,f,limit,mode,subject=None):
    """Every page of one listing: the first fixes as_of; the next ones follow next_after (keyset) or next_offset."""
    first=read(cur,dict(f,limit=limit),subject);as_of=first['snapshot']['as_of'];pages=[first]
    while pages[-1]['page']['next_after'] is not None:
        p=pages[-1]['page'];q=dict(f,limit=limit,as_of=as_of)
        if mode=='after':q['after']=p['next_after']
        else:q['offset']=p['next_offset']
        pages.append(read(cur,q,subject));assert len(pages)<=300,'CP17_R3_03_PAGING_DOES_NOT_END'
    return as_of,pages
def flat(pages):return [r for p in pages for r in p['page']['rows']]
def check_walk(pages,oracle,limit,mode):
    """The pages together are the oracle exactly, in order, each row once; every page says the same total and its place."""
    rows=flat(pages);check_rows(rows,oracle);done=0
    for i,p in enumerate(pages):
        g=p['page'];last=i==len(pages)-1
        assert (g['total'],g['limit'])==(str(len(oracle)),limit) and p['snapshot']['as_of']==pages[0]['snapshot']['as_of'],(i,g['total'],len(oracle))
        assert (g['before'],g['offset'])==((str(done),0)if mode=='after'else('0',done)),(i,g['before'],g['offset'],done)
        assert len(g['rows'])==(len(oracle)-done if last else limit),(i,len(g['rows']))
        assert (g['next_after'] is None)==last,(i,g['next_after'])
        done+=len(g['rows'])
    assert done==len(oracle) and len({r['id'] for r in rows})==len(rows)
    return len(pages)
def insert(cur,entity_type,action,old,new,actor,reason,at=None,entity_id=None):
    """One direct admin row in erp.audit_logs (isolation fixture); the time is the statement time unless given."""
    b.api.admin(cur)
    return one(cur,"""insert into erp.audit_logs(entity_type,entity_id,action,old_data,new_data,changed_by,change_reason,changed_at)
        values(%s,%s::uuid,%s,%s::jsonb,%s::jsonb,%s::uuid,%s,coalesce(%s::timestamptz,statement_timestamp()))returning id""",
        (entity_type,entity_id or str(uuid.uuid4()),action,None if old is None else json.dumps(old),None if new is None else json.dumps(new),actor,reason,at))
def customer(cur,subject,t,reasons,name='Toko Audit'):
    """Native writes through the master screen facade: create, rename and (when three reasons are given) deactivate."""
    code='AUD'+t
    c=master.create(cur,'CUSTOMER',master.customer_fields(code,f'{name} {t}'),reason=reasons[0],subject=subject)
    if len(reasons)>1:master.act(cur,'CUSTOMER',c['id'],'UPDATE',master.customer_fields(code,f'{name} Jaya {t}'),reasons[1],subject=subject)
    if len(reasons)>2:master.act(cur,'CUSTOMER',c['id'],'DEACTIVATE',reason=reasons[2],subject=subject)
    b.api.admin(cur);return c['id']
def bulk(cur):
    """56 admin rows of a fresh data type on 2-4 Feb 2001 (WIB): the four rows around both WIB midnights, 20 rows sharing one
    instant (the id tie-break), and rows by two fresh users and by no user."""
    t='cp17_r303_'+tag().lower()
    s1,a1=person(cur,'OWNER','Audit pemilik '+t);s2,a2=person(cur,'ADMIN','Audit admin '+t)
    d2,d3,d4=(datetime(2001,2,n,tzinfo=WIB) for n in(2,3,4));tick=timedelta(microseconds=1)
    plan=[(d3-tick,'INSERT',a1),(d3,'UPDATE',a2),(d4-tick,'UPDATE',a1),(d4,'INSERT',None)]
    plan+=[(d3+timedelta(hours=9),('INSERT','UPDATE')[i%2],(a2 if i%3==0 else a1)) for i in range(20)]
    plan+=[(d2+timedelta(hours=i),('UPDATE','INSERT')[i%2],(a1,a2,None)[i%3]) for i in range(1,24)]
    plan+=[(d3+timedelta(minutes=17*i),'UPDATE',a2) for i in range(1,10)]
    for i,(at,action,actor) in enumerate(plan):
        old=None if action=='INSERT' else dict(name=f'lama {i}',qty=i,same='tetap',gone=i)
        insert(cur,t,action,old,dict(name=f'baru {i}',qty=i+(i%2),same='tetap',added=True),actor,f'Audit {t} baris {i:02d} Alasan Campur',at)
    rows=stored(cur,'entity_type=%s',(t,))
    assert sorted(r['at'] for r in rows)==sorted(at for at,_,_ in plan),'CP17_R3_03_FIXTURE_TIME_NOT_STORED'
    return dict(type=t,a1=a1,a2=a2,s1=s1,rows=rows,edges=dict(before_d3=d3-tick,d3=d3,end_d3=d4-tick,d4=d4))


def cases(cur,today):
    c=cp17()
    def native_rows():
        t=tag();name='Audit pemilik '+t;subject,app=person(cur,'OWNER',name)
        reasons=[f'Audit {t} pelanggan baru',f'Audit {t} nama dibetulkan',f'Audit {t} toko tutup']
        cid=customer(cur,subject,t,reasons)
        mine=stored(cur,'entity_id=%s::uuid',(cid,))
        # The Native trigger wrote the customer's rows: this user, data type customers, each reason, created then changed.
        for reason in reasons:
            hit=[r for r in mine if r['reason']==reason]
            assert hit and all((r['entity_type'],r['entity_id'],r['actor'],r['name'])==('customers',cid,app,name) for r in hit),('CP17_R3_03_NATIVE_ROW',reason,mine)
        assert any(r['action']=='INSERT' for r in mine if r['reason']==reasons[0]) and any(r['action']=='UPDATE' for r in mine if r['reason']==reasons[1]),mine
        before=b.boundary.snapshot(cur)
        by_id=read(cur,dict(q=cid,limit=100),subject);check_rows(by_id['page']['rows'],expect(searched(cur,cid),dict(q=cid),by_id['snapshot']['as_of']))
        q=f'AUDIT {t.lower()}';by_reason=read(cur,dict(q=q,limit=100),subject)
        check_rows(by_reason['page']['rows'],expect(searched(cur,q),dict(q=q),by_reason['snapshot']['as_of']))
        by_actor=read(cur,dict(actor_id=app,limit=100),subject)
        check_rows(by_actor['page']['rows'],expect(stored(cur,'changed_by=%s::uuid',(app,)),dict(actor_id=app),by_actor['snapshot']['as_of']))
        day=min(r['at'] for r in mine).astimezone(WIB).date().isoformat()
        f={'entity_type':'customers','from':day,'to':day,'q':t};dated=read(cur,dict(f,limit=100),subject)
        check_rows(dated['page']['rows'],expect(searched(cur,t),f,dated['snapshot']['as_of']))
        assert {x['reason'] for x in by_id['page']['rows']}>=set(reasons) and {x['reason'] for x in by_actor['page']['rows']}>=set(reasons)
        assert b.boundary.snapshot(cur)==before,'CP17_R3_03_READ_CHANGED_THE_BOOKS'
        return dict(status='PASS',native_writer='erp_cp7_save_master_v1 CUSTOMER CREATE/UPDATE/DEACTIVATE',rows=len(mine),
                    actions=sorted({r['action'] for r in mine}),actor=name,reasons=reasons,filters=['q=customer id','q=reason (any case)','actor_id',
                    'entity_type+WIB day+q'],read_changed_nothing=True)
    def filters_and_paging():
        g=bulk(cur);t=g['type'];edges=g['edges']
        window=stored(cur,'changed_at>=%s and changed_at<%s',(day_start('2001-02-02'),day_start('2001-02-05')))
        plans=[(dict(entity_type=t),g['rows']),(dict(entity_type=t,action='UPDATE'),g['rows']),(dict(entity_type=t,actor_id=g['a1']),g['rows']),
               ({'entity_type':t,'from':'2001-02-03','to':'2001-02-03'},g['rows']),
               ({'entity_type':t,'actor_id':g['a2'],'action':'UPDATE','from':'2001-02-02','to':'2001-02-03'},g['rows']),
               (dict(entity_type=t,q='alasan campur'),g['rows']),(dict(entity_type=t,q='BARIS 0'),g['rows']),
               ({'from':'2001-02-02','to':'2001-02-04'},window)]
        prefix=g['rows'][5]['entity_id'][:13].upper();plans.append((dict(q=prefix),searched(cur,prefix)))
        walked=[]
        for f,source in plans:
            for mode in('after','offset'):
                as_of,pages=walk(cur,f,7,mode,g['s1'])
                oracle=expect(source,f,as_of);walked.append((f,mode,len(oracle),check_walk(pages,oracle,7,mode)))
        # Each WIB midnight belongs to the day it starts.
        day3=[r['id'] for r in flat(walk(cur,{'entity_type':t,'from':'2001-02-03','to':'2001-02-03'},100,'after')[1])]
        at={r['at']:str(r['id']) for r in g['rows'] if r['at'] in edges.values()}
        assert at[edges['d3']] in day3 and at[edges['end_d3']] in day3 and at[edges['before_d3']] not in day3 and at[edges['d4']] not in day3,day3
        # The pickers of this listing: data types of the window, actions and users of this data type.
        o=read(cur,{'entity_type':t,'from':'2001-02-02','to':'2001-02-04','limit':1})['options']
        assert o['entity_types']==keyorder({r['entity_type'] for r in window})[:200] and t in o['entity_types'],o['entity_types']
        assert o['actions']==['INSERT','UPDATE'],o['actions']
        assert o['actors']==sorted([dict(id=g['a1'],name='Audit pemilik '+t),dict(id=g['a2'],name='Audit admin '+t)],key=lambda a:a['name'].encode()),o['actors']
        # Inside one listing a later row stays out (as_of); a new listing shows it first.
        first=read(cur,dict(entity_type=t,limit=7));late=insert(cur,t,'INSERT',None,dict(late=True),g['a1'],f'Audit {t} baris baru')
        second=read(cur,dict(entity_type=t,limit=7,as_of=first['snapshot']['as_of'],after=first['page']['next_after']))
        assert second['page']['total']==first['page']['total']==str(len(g['rows'])) and str(late) not in [r['id'] for r in second['page']['rows']] and second['snapshot']['newer'] is True
        fresh=read(cur,dict(entity_type=t,limit=7))
        assert fresh['page']['rows'][0]['id']==str(late) and fresh['page']['total']==str(len(g['rows'])+1) and fresh['snapshot']['newer'] is False
        return dict(status='PASS',fixture_rows=len(g['rows']),listings=len(walked),pages=sum(x[3] for x in walked),
                    modes=['keyset after','offset'],wib_midnight_inclusive_start=True,tie_break_same_instant=20,later_row_outside_listing=True)
    def detail_one_row():
        t=tag();subject,_=person(cur,'OWNER','Audit pemilik '+t)
        cid=customer(cur,subject,t,[f'Audit {t} pelanggan baru',f'Audit {t} nama dibetulkan'])
        mine=newest_first(stored(cur,'entity_id=%s::uuid',(cid,)))
        for r in mine:check_detail(read(cur,dict(q=cid,id=str(r['id'])),subject)['detail'],r)
        renamed=[r for r in mine if r['reason']==f'Audit {t} nama dibetulkan' and r['action']=='UPDATE']
        assert renamed and changed(renamed[0]['old'],renamed[0]['new']),renamed
        shapes=dict(array_before=([1,2,{'a':None}],{'x':None,'y':{'z':[1,2.5]},'s':'teks'}),many_keys=(None,{f'k{i:03d}':i for i in range(600)}),
                    too_large=({'big':'x'*300000},{'big':'y'*300000}),no_data=(None,None),scalars=('skalar',7),booleans=({'f':True,'n':1},{'f':1,'n':True}))
        kind='cp17_r303_shape_'+tag().lower();seen={}
        for label,(old,new) in shapes.items():
            n=insert(cur,kind,'UPDATE',old,new,None,f'Audit bentuk {label}',entity_id=None)
            r=stored(cur,'id=%s',(n,))[0];d=read(cur,dict(id=str(n)),subject)['detail'];check_detail(d,r)
            seen[label]=dict(fields=len(d['fields']),total=d['fields_total'],too_large=d['too_large'],changed=r and len(changed(r['old'],r['new'])))
        assert seen['many_keys']['fields']==500 and seen['many_keys']['total']==600 and seen['too_large']['too_large'] is True and seen['booleans']['changed']==2,seen
        listed=read(cur,dict(entity_type=kind,limit=100),subject)
        assert all(set(x)==ROW_KEYS for x in listed['page']['rows']) and len(json.dumps(listed))<100000,'CP17_R3_03_LIST_CARRIES_DATA'
        before=b.boundary.snapshot(cur)
        gone=refused(cur,lambda:read(cur,dict(id='999999999999999999'),subject),'CP7_AUDIT_NOT_FOUND');c.unchanged(cur,before,'unknown detail id')
        return dict(status='PASS',native_rows_in_detail=len(mine),rename_changed_keys=changed(renamed[0]['old'],renamed[0]['new'])[:10],shapes=seen,
                    list_rows_without_data=True,unknown_id_refused=gone)
    def denied():
        t=tag();roles=[x[0] for x in cur.execute('select role_code from erp.app_roles where is_active order by role_code').fetchall()]
        people={code:person(cur,code,f'Audit {code} {t}')[0] for code in roles}
        export_only,_=custom(cur,('settings.audit.export',),'ekspor saja '+t)
        inactive,inactive_user=person(cur,'ADMIN','Audit nonaktif '+t);cur.execute('update erp.app_users set is_active=false where id=%s',(inactive_user,))
        owner,_=person(cur,'OWNER','Audit pemilik '+t)
        before=b.boundary.snapshot(cur);out={}
        for code in roles:
            if holds(cur,code,'settings.audit.view'):
                r=read(cur,dict(limit=1),people[code]);assert r['contract_version']=='cp7.audit-trail.v1',r;out[code]='READS'
            else:out[code]=refused(cur,lambda:read(cur,dict(limit=1),people[code]),'CP7_AUDIT_DENIED')
        assert out.get('OWNER')=='READS' and out.get('ADMIN')=='READS' and out.get('AUDITOR_VIEW_ONLY')=='READS' and out.get('GUDANG')!='READS',out
        other=dict(export_without_view=refused(cur,lambda:read(cur,{},export_only),'CP7_AUDIT_DENIED'),
                   inactive_user=refused(cur,lambda:read(cur,{},inactive),'CP7_AUDIT_DENIED'),
                   no_app_user=refused(cur,lambda:read(cur,{},str(uuid.uuid4())),'CP7_AUDIT_DENIED'),
                   jwt_anon=refused(cur,lambda:read(cur,{},owner,'anon'),'CP7_AUDIT_DENIED'),
                   jwt_service_role=refused(cur,lambda:read(cur,{},owner,'service_role'),'CP7_AUDIT_DENIED'))
        def as_role(role,sql):
            b.api.admin(cur);cur.execute(f'set local role {role}');cur.execute(sql,(json.dumps({}),))
        other['anon_public']=refused(cur,lambda:as_role('anon','select public.erp_cp7_get_audit_trail_v1(%s)'),'permission denied')
        other['authenticated_private']=refused(cur,lambda:as_role('authenticated','select cp7_audit.workspace(%s)'),'permission denied')
        c.unchanged(cur,before,'audit refusals')
        return dict(status='PASS',per_role=out,**other)
    def export_flag():
        t=tag();seen={}
        for code in('OWNER','ADMIN','AUDITOR_VIEW_ONLY'):
            s,_=person(cur,code,f'Audit {code} {t}');seen[code]=read(cur,dict(limit=1),s)['can_export']
            assert seen[code]==holds(cur,code,'settings.audit.export'),(code,seen[code])
        assert seen=={'OWNER':True,'ADMIN':False,'AUDITOR_VIEW_ONLY':False},seen
        both,_=custom(cur,('settings.audit.view','settings.audit.export'),'lihat dan ekspor '+t);view,_=custom(cur,('settings.audit.view',),'lihat saja '+t)
        custom_flags=dict(view_and_export=read(cur,dict(limit=1),both)['can_export'],view_only=read(cur,dict(limit=1),view)['can_export'])
        assert custom_flags=={'view_and_export':True,'view_only':False},custom_flags
        catalog=(ROOT/'src/auth/accessCatalog.ts').read_text()
        assert "'admin-audit': 'settings.audit.view'" in catalog and "exportAudit: 'settings.audit.export'" in catalog
        return dict(status='PASS',templates=seen,custom_roles=custom_flags,screen_keys=dict(page='settings.audit.view',export='settings.audit.export'))
    def large_bounded():
        t='cp17_r303_big_'+tag().lower();b.api.admin(cur)
        cur.execute("""insert into erp.audit_logs(entity_type,entity_id,action,new_data,change_reason)
            select %s,gen_random_uuid(),'INSERT',jsonb_build_object('n',i,'pad',repeat('x',2000)),'Audit besar '||i from generate_series(1,230)i""",(t,))
        wide=insert(cur,t,'UPDATE',{f'w{i:02d}':0 for i in range(45)},{f'w{i:02d}':1 for i in range(45)},None,'Audit 45 kolom')
        oracle=newest_first(stored(cur,'entity_type=%s',(t,)))
        as_of,pages=walk(cur,dict(entity_type=t),100,'after');check_walk(pages,oracle,100,'after')
        assert [len(p['page']['rows']) for p in pages]==[100,100,31] and all(len(json.dumps(p))<300000 for p in pages),[len(json.dumps(p)) for p in pages]
        row=[r for r in flat(pages) if r['id']==str(wide)][0]
        assert (row['changed_keys'],row['changed_key_count'])==([f'w{i:02d}' for i in range(30)],45),row
        many='cp17_r303_kind_'+tag().lower()
        cur.execute("""insert into erp.audit_logs(entity_type,entity_id,action,change_reason,changed_at)
            select %s||lpad(i::text,3,'0'),gen_random_uuid(),'INSERT','Audit jenis '||i,timestamptz '2001-03-10 12:00+07' from generate_series(1,205)i""",(many,))
        o=read(cur,{'from':'2001-03-10','to':'2001-03-10','limit':1})['options']
        kinds=keyorder({r['entity_type'] for r in stored(cur,'changed_at>=%s and changed_at<%s',(day_start('2001-03-10'),day_start('2001-03-11')))})
        assert o['entity_types']==kinds[:200] and len(o['entity_types'])==200,len(o['entity_types'])
        before=b.boundary.snapshot(cur)
        bad={'limit_101':dict(limit=101),'limit_0':dict(limit=0),'limit_text':dict(limit='10'),'offset_negative':dict(offset=-1),'offset_big':dict(offset=1000001),
             'unknown_key':dict(sort='id'),'bad_date':{'from':'2026-02-30'},'from_after_to':{'from':'2026-10-02','to':'2026-10-01'},'year_1999':{'from':'1999-12-31'},
             'long_q':dict(q='x'*121),'bad_actor':dict(actor_id='bukan-uuid'),'bad_id':dict(id='abc'),'number_id':dict(id=5),'fraction_limit':dict(limit=1.5),
             'entity_type_number':dict(entity_type=3)}
        refusals={k:refused(cur,lambda q=q:read(cur,q),'CP7_AUDIT_QUERY') for k,q in bad.items()}
        refusals['not_an_object']=refused(cur,lambda:(auth.actor(cur),cur.execute('select public.erp_cp7_get_audit_trail_v1(%s)',(json.dumps([]),))),'CP7_AUDIT_QUERY')
        refusals['cursor_gone']=refused(cur,lambda:read(cur,dict(after='999999999999999999')),'CP7_AUDIT_CURSOR_GONE')
        c.unchanged(cur,before,'audit query refusals')
        return dict(status='PASS',rows=len(oracle),pages=[100,100,31],max_page_bytes=max(len(json.dumps(p)) for p in pages),changed_keys_named=30,
                    changed_key_count=45,entity_type_picker=200,refusals=sorted(refusals))
    def private_read_only():
        import cp7_audit_bundle as bundle
        b.api.admin(cur);proof=bundle.verify(cur);before=b.boundary.snapshot(cur)
        page=read(cur,dict(limit=100));rows=page['page']['rows']
        if rows:read(cur,dict(limit=100,id=rows[0]['id']))
        assert page['business_DML'] is False and b.boundary.snapshot(cur)==before,'CP17_R3_03_READ_CHANGED_THE_BOOKS'
        for who in('anon','authenticated','service_role'):
            assert not one(cur,"select has_schema_privilege(%s,'cp7_audit','USAGE')",(who,)),who
            assert not one(cur,"select has_function_privilege(%s,'cp7_audit.workspace(jsonb)','EXECUTE')",(who,)),who
        return dict(status='PASS',verify=proof,read_changed_nothing=True,rows_read=len(rows))
    named=[native_rows,filters_and_paging,detail_one_row,denied,export_flag,large_bounded,private_read_only]
    assert len(named)==len(NATIVE)
    return list(zip(NATIVE,named))


def races(tools,today):
    def seeded(n,label):
        """n committed customers made through the master facade by a fresh OWNER-role user; every reason carries the tag."""
        t=tag();reason=f'Audit balapan {t}'
        with tools.connect()as conn,conn.cursor()as cur:
            subject,_=person(cur,'OWNER',f'Audit {label} {t}')
            for i in range(n):master.create(cur,'CUSTOMER',master.customer_fields(f'AUR{t}{i:02d}',f'Toko balapan {i}'),reason=f'{reason} awal {i:02d}',subject=subject)
            conn.commit()
        return t,reason,subject
    def page(f,subject):
        with tools.connect()as conn,conn.cursor()as cur:
            r=read(cur,f,subject);conn.rollback();return r
    def committed(q):
        with tools.connect()as conn,conn.cursor()as cur:
            r=searched(cur,q);conn.rollback();return r
    def write(subject,code,reason):
        with tools.connect()as conn,conn.cursor()as cur:
            cid=master.create(cur,'CUSTOMER',master.customer_fields(code,'Toko balapan baru'),reason=reason,subject=subject)['id'];conn.commit();return cid
    def write_between_pages():
        t,reason,subject=seeded(7,'antar halaman');f=dict(q=reason)
        # A write already open when the first page is read, committed after it.
        opened=tools.connect();ocur=opened.cursor()
        held=master.create(ocur,'CUSTOMER',master.customer_fields(f'AUR{t}OP','Toko balapan terbuka'),reason=f'{reason} terbuka',subject=subject)['id']
        try:
            first=page(dict(f,limit=3),subject);as_of=first['snapshot']['as_of']
            oracle=expect(committed(reason),f,as_of)
            opened.commit()
        finally:opened.close()
        late=write(subject,f'AUR{t}NW',f'{reason} baru')
        results={}
        for mode in('after','offset'):
            pages=[first]
            while pages[-1]['page']['next_after'] is not None:
                p=pages[-1]['page'];q=dict(f,limit=3,as_of=as_of,**({'after':p['next_after']} if mode=='after' else {'offset':p['next_offset']}))
                pages.append(page(q,subject))
            results[mode]=check_walk(pages,oracle,3,mode)
            assert all(p['snapshot']['newer'] for p in pages[1:]),'CP17_R3_03_NEWER_NOT_SAID'
        # Both writes are committed and lead the next listing (newest first); the listing above never showed them.
        now=committed(reason);fresh=page(dict(f,limit=100),subject)
        later=[r for r in now if r['reason'] in(f'{reason} terbuka',f'{reason} baru')]
        assert {r['entity_id'] for r in later}=={held,late} and not {str(r['id']) for r in later}&{str(o['id']) for o in oracle},later
        assert fresh['page']['total']==str(len(now)) and {x['id'] for x in fresh['page']['rows'][:len(later)]}=={str(r['id']) for r in later},fresh['page']['rows'][:3]
        return dict(status='PASS',listing_rows=len(oracle),pages=results,open_write_committed_after_page_1=True,write_committed_between_pages=True,
                    no_duplicate_no_skip=True,new_rows_in_next_listing=2)
    def paging_while_writer_runs():
        t,reason,subject=seeded(12,'penulis jalan');f=dict(q=reason);stop=threading.Event();written=[];errors=[]
        def writer():
            i=0
            while not stop.is_set() and i<30:
                try:write(subject,f'AUR{t}W{i:02d}',f'{reason} jalan {i:02d}');written.append(time.monotonic())
                except Exception as e:errors.append(str(e).splitlines()[0]);break
                i+=1;time.sleep(0.05)
        with ThreadPoolExecutor(max_workers=1)as pool:
            job=pool.submit(writer)
            try:
                first=page(dict(f,limit=1),subject);as_of=first['snapshot']['as_of'];pages=[first];started=time.monotonic()
                while pages[-1]['page']['next_after'] is not None:
                    time.sleep(0.05);pages.append(page(dict(f,limit=1,as_of=as_of,after=pages[-1]['page']['next_after']),subject))
                ended=time.monotonic()
            finally:
                stop.set();job.result(120)
        assert not errors,errors
        oracle=expect(committed(reason),f,as_of);check_walk(pages,oracle,1,'after')
        during=[w for w in written if started<w<ended]
        assert len(oracle)>=12 and all(f'{reason} awal {i:02d}' in {o['reason'] for o in oracle} for i in range(12)),len(oracle)
        assert during and not any('jalan' in x['reason'] for x in flat(pages)),('CP17_R3_03_NO_WRITE_DURING_PAGING',len(written))
        return dict(status='PASS',listing_rows=len(oracle),pages=len(pages),writes_committed_while_paging=len(during),writes_total=len(written),no_duplicate_no_skip=True)
    return list(zip(RACES,[write_between_pages,paging_while_writer_runs]))


def http_cases(http,today):
    def owner_reads_limited_refused():
        owner=http.login('OWNER','cp17-r3-03-audit');gudang=http.login('GUDANG','cp17-r3-03-gudang');viewer=http.login('AUDITOR_VIEW_ONLY','cp17-r3-03-viewer')
        t=tag();reason=f'Audit HTTP {t} pelanggan baru'
        c=owner.rpc('erp_cp7_save_master_v1',dict(p_kind='CUSTOMER',p_request=str(uuid.uuid4()),
            p_payload=dict(action='CREATE',fields=master.customer_fields('AUH'+t,'Toko Audit HTTP'),reason=reason)))
        assert c['status']==200,c;cid=c['body']['id']
        r=owner.rpc('erp_cp7_get_audit_trail_v1',dict(p_query=dict(q=cid,limit=100)));assert r['status']==200,r;body=r['body']
        with http.connect()as conn,conn.cursor()as cur:
            oracle=expect(searched(cur,cid),dict(q=cid),body['snapshot']['as_of'])
            app=one(cur,'select id::text from erp.app_users where auth_user_id=%s',(owner.auth_user_id,));conn.rollback()
        check_rows(body['page']['rows'],oracle)
        mine=[x for x in body['page']['rows'] if x['reason']==reason]
        assert mine and all((x['entity_type'],x['actor_id'],x['actor_name'])==('customers',app,'Auditor HTTP cp17-r3-03-audit') for x in mine) and body['can_export'] is True,mine
        d=owner.rpc('erp_cp7_get_audit_trail_v1',dict(p_query=dict(q=cid,id=mine[0]['id'])));assert d['status']==200,d
        with http.connect()as conn,conn.cursor()as cur:check_detail(d['body']['detail'],stored(cur,'id=%s',(int(mine[0]['id']),))[0]);conn.rollback()
        g=gudang.rpc('erp_cp7_get_audit_trail_v1',dict(p_query=dict(q=cid)))
        assert g['status'] in(401,403) and 'CP7_AUDIT_DENIED' in json.dumps(g['body']),g
        v=viewer.rpc('erp_cp7_get_audit_trail_v1',dict(p_query=dict(q=cid,limit=100)))
        assert v['status']==200 and v['body']['can_export'] is False and [x['id'] for x in v['body']['page']['rows']]==[x['id'] for x in body['page']['rows']],v
        bad=owner.rpc('erp_cp7_get_audit_trail_v1',dict(p_query=dict(limit=101)));assert bad['status']==400 and 'CP7_AUDIT_QUERY' in json.dumps(bad['body']),bad
        anon=http.anon_rpc('erp_cp7_get_audit_trail_v1',dict(p_query={}));assert anon['status'] in(401,403,404),anon
        return dict(status='PASS',real_Auth=True,native_write='erp_cp7_save_master_v1 over HTTP',owner_reads=len(body['page']['rows']),owner_can_export=True,
                    gudang_refused=g['status'],auditor_view_only_reads_without_export=True,limit_101_refused=bad['status'],anon_refused=anon['status'])
    return list(zip(HTTP,[owner_reads_limited_refused]))


# ---------------------------------------------------------------- browser fixture (cp7_cp17_fix_browser_fixture.py operations)
def display(data,key):
    v=data.get(key)
    return None if v is None else v if isinstance(v,str) else None
def browser_fixture(cur,today):
    """Committed: 25 customers made through the master facade by a fresh OWNER-role user, then the first renamed; each reason
    carries the tag, so the screen's search finds exactly these rows."""
    t=tag();name=f'Audit pemilik {t}';subject,app=person(cur,'OWNER',name);ids=[]
    for i in range(25):
        ids.append(master.create(cur,'CUSTOMER',master.customer_fields(f'AUB{t}{i:02d}',f'Toko Audit {t} {i:02d}'),reason=f'Audit {t} pelanggan {i:02d}',subject=subject)['id'])
    master.act(cur,'CUSTOMER',ids[0],'UPDATE',master.customer_fields(f'AUB{t}00',f'Toko Audit {t} Jaya'),f'Audit {t} nama dibetulkan',subject=subject)
    b.api.admin(cur)
    return dict(tag=t,actor=name,actor_id=app,customer=ids[0])
def browser_state(cur,p):
    """Native rows of the fixture, newest first, read from erp.audit_logs (never from the facade)."""
    rows=newest_first(searched(cur,p['tag']));first=rows[0];o,n=obj(first['old']),obj(first['new'])
    shown=[dict(key=k,before=display(o,k),after=display(n,k)) for k in changed(first['old'],first['new']) if display(o,k) or display(n,k)]
    return dict(total=len(rows),ids=[str(r['id']) for r in rows],actions=[r['action'] for r in rows],types=[r['entity_type'] for r in rows],
                names=[r['name'] for r in rows],reasons=[r['reason'] for r in rows],
                day_from=min(r['at'] for r in rows).astimezone(WIB).date().isoformat(),day_to=max(r['at'] for r in rows).astimezone(WIB).date().isoformat(),
                first=dict(id=str(first['id']),reason=first['reason'],changed=shown[:5]))
