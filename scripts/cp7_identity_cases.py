"""P03 policy oracles. Native disposable fixtures; no hosted writes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json,time,uuid,threading
import psycopg
import cp7_snapshot_cases as p02
import cp6_bf_probe as bf
b=p02.b

def fixture(cur,today):
    f=p02.fixture(cur,today)
    more=bf.products(cur,('XS','L','34'),tag='P03-'+uuid.uuid4().hex[:8])
    roots=[f['root']]+[r for r,_ in more]
    at=cur.execute("select clock_timestamp()-interval '5 minutes'").fetchone()[0]
    groups=[bf.group(cur,roots[:3],at,settings=dict(price=None,bom=None,work_rates=[],laundry_rates=[])),
            bf.group(cur,roots[3:],at,settings=dict(price=None,bom=None,work_rates=[],laundry_rates=[]))]
    bf.save(cur,groups,at)
    return dict(f,roots=roots,groups=groups,skus=[g['id'] for g in groups])

def get(cur,skus,subject=None):
    p02.actor(cur,subject)
    value=cur.execute('select public.erp_cp7_get_production_policy_v1(%s::uuid[])',(skus,)).fetchone()[0]
    b.api.admin(cur);return value

def apply(cur,changes,key=None,subject=None):
    p02.actor(cur,subject)
    value=cur.execute('select public.erp_cp7_set_production_policy_v1(%s::jsonb,%s)',(json.dumps(changes,default=str),key or uuid.uuid4())).fetchone()[0]
    b.api.admin(cur);return value

def proposal(row,state='STOPPED',review=None):
    return {**{k:row[k] for k in ('sku_id','commercial_version_id','commercial_revision','members','policy_revision')},
            'state':state,'reason':'P03 explicit policy review','review_at':review}

def row(workspace,sku):return next(r for r in workspace['rows'] if r['sku_id']==sku)

def move(cur,f):
    at=cur.execute('select clock_timestamp()').fetchone()[0]
    a,c=f['groups']
    a2=bf.group(cur,f['roots'],at,sku=a['sku'],gid=a['id'],revision=1,settings=a['settings'])
    c2=bf.group(cur,f['roots'][3:],at,sku=c['sku'],gid=c['id'],revision=1,settings=c['settings']);c2['members']=[];c2['legacy_basis']=[]
    bf.save(cur,[a2,c2],at)

def smoke(cur,today):
    def qualify():
        f=fixture(cur,today);w=get(cur,f['skus'])
        assert len(w['rows'])==2
        result=apply(cur,[proposal(row(w,f['skus'][0]))])
        assert len(result['applied'])==1
        return dict(status='PASS',fixture_and_first_command_qualified=True)
    return [('P03_FIXTURE_AND_COMMAND_SMOKE',qualify)]

def cases(cur,today):
    def status_boundary():
        f=fixture(cur,today);w=get(cur,f['skus']);a=row(w,f['skus'][0]);c=row(w,f['skus'][1])
        assert len(a['members'])==3 and len(c['members'])==1 and a['policy']['quality']=='UNREVIEWED'
        before=b.boundary.snapshot(cur);apply(cur,[proposal(a)])
        updated=get(cur,f['skus'])
        assert row(updated,a['sku_id'])['policy']['state']=='STOPPED'
        assert row(updated,c['sku_id'])['policy']['quality']=='UNREVIEWED'
        assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',stopped_scope_only=True,erp_business_boundary_unchanged=True,member_counts=[3,1])
    def replay():
        f=fixture(cur,today);a=proposal(row(get(cur,f['skus']),f['skus'][0]));key=uuid.uuid4()
        first=apply(cur,[a],key);again=apply(cur,[a],key)
        assert first['applied']==again['applied'] and again['replayed']
        changed=dict(a,state='ACTIVE');p02.refused(cur,lambda:apply(cur,[changed],key),'CP7_POLICY_REQUEST_REUSED')
        assert cur.execute('select count(*) from cp7_identity.production_policy').fetchone()[0]==1
        return dict(status='PASS',one_outcome=True,changed_payload_denied=True)
    def atomic():
        f=fixture(cur,today);w=get(cur,f['skus']);a=proposal(row(w,f['skus'][0]));c=proposal(row(w,f['skus'][1]))
        apply(cur,[c]);p02.refused(cur,lambda:apply(cur,[a,c]),'CP7_POLICY_VERSION_STALE')
        assert cur.execute('select count(*) from cp7_identity.production_policy where sku_id=%s',(a['sku_id'],)).fetchone()[0]==0
        return dict(status='PASS',later_stale_rolls_back_earlier_member=True)
    def membership():
        f=fixture(cur,today);a=proposal(row(get(cur,f['skus']),f['skus'][0]));apply(cur,[a]);old=get(cur,f['skus'])
        p=cur.execute('select to_jsonb(x) from cp7_identity.production_policy x').fetchone()[0]
        move(cur,f);p02.refused(cur,lambda:apply(cur,[dict(a,policy_revision='1')]),'CP7_POLICY_MEMBERSHIP_STALE')
        changed=row(get(cur,f['skus']),a['sku_id'])
        assert changed['policy']['quality']=='MEMBERSHIP_CHANGED' and changed['policy']['state'] is None
        assert cur.execute('select to_jsonb(x) from cp7_identity.production_policy x').fetchone()[0]==p
        assert len(row(old,a['sku_id'])['members'])==3 and len(changed['members'])==4
        return dict(status='PASS',membership_change_refused=True,no_silent_activation=True,history_immutable=True)
    def past_review():
        f=fixture(cur,today);a=proposal(row(get(cur,f['skus']),f['skus'][0]),'PAUSED',cur.execute("select clock_timestamp()-interval '1 day'").fetchone()[0])
        apply(cur,[a]);p=row(get(cur,f['skus']),a['sku_id'])['policy']
        assert p['state']=='PAUSED' and p['review_due']
        return dict(status='PASS',past_review_never_reactivates=True)
    def price_only():
        f=fixture(cur,today);a=proposal(row(get(cur,f['skus']),f['skus'][0]));apply(cur,[a])
        at=cur.execute('select clock_timestamp()').fetchone()[0];g=f['groups'][0]
        updated=bf.group(cur,f['roots'][:3],at,sku=g['sku'],gid=g['id'],revision=1,
            settings=dict(price='190000.00',bom=None,work_rates=[],laundry_rates=[]))
        bf.save(cur,[updated],at)
        current=row(get(cur,f['skus']),a['sku_id'])
        assert current['commercial_revision']=='2' and current['policy_revision']=='1'
        assert current['policy']['quality']=='KNOWN' and current['policy']['state']=='STOPPED'
        return dict(status='PASS',price_revision_does_not_reactivate_or_invalidate_members=True)
    def future_members():
        f=fixture(cur,today);a=proposal(row(get(cur,f['skus']),f['skus'][0]));apply(cur,[a])
        at=cur.execute("select clock_timestamp()+interval '2 seconds'").fetchone()[0];g,h=f['groups']
        g2=bf.group(cur,f['roots'],at,sku=g['sku'],gid=g['id'],revision=1,settings=g['settings'])
        h2=bf.group(cur,f['roots'][3:],at,sku=h['sku'],gid=h['id'],revision=1,settings=h['settings']);h2['members']=[];h2['legacy_basis']=[]
        bf.save(cur,[g2,h2],at)
        current=row(get(cur,f['skus']),a['sku_id'])
        assert len(current['members'])==3 and current['policy']['state']=='STOPPED'
        deadline=time.monotonic()+5
        while cur.execute('select clock_timestamp()<%s',(at,)).fetchone()[0]:
            assert time.monotonic()<deadline,'FUTURE_MEMBERSHIP_CLOCK_TIMEOUT'
            time.sleep(.02)
        later=row(get(cur,f['skus']),a['sku_id'])
        assert len(later['members'])==4 and later['policy']['quality']=='MEMBERSHIP_CHANGED'
        assert later['policy']['state'] is None
        return dict(status='PASS',future_version_hidden_until_effective=True,no_new_member_activation=True)
    def privileges():
        f=fixture(cur,today);a=proposal(row(get(cur,f['skus']),f['skus'][0]));subject,role=p02.custom_actor(cur)
        p02.refused(cur,lambda:apply(cur,[a],subject=subject),'CP7_POLICY_ACCESS_DENIED')
        p02.refused(cur,lambda:apply(cur,[a],subject=str(uuid.uuid4())),'CP7_POLICY_ACCESS_DENIED')
        def service_shortcut():
            p02.actor(cur,role='service_role')
            cur.execute('select public.erp_cp7_set_production_policy_v1(%s::jsonb,%s)',(json.dumps([a]),uuid.uuid4()))
        p02.refused(cur,service_shortcut,'CP7_POLICY_ACCESS_DENIED')
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'master.product.manage')",(role,))
        key=uuid.uuid4();apply(cur,[a],key,subject)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='master.product.manage'",(role,))
        p02.refused(cur,lambda:apply(cur,[a],key,subject),'CP7_POLICY_ACCESS_DENIED')
        assert not cur.execute("select has_function_privilege('cp7_capture','public.erp_cp7_set_production_policy_v1(jsonb,uuid)','EXECUTE')").fetchone()[0]
        assert not cur.execute("select has_table_privilege('cp7_policy','erp.products','INSERT,UPDATE,DELETE')").fetchone()[0]
        def poisoned_compute():
            p02.actor(cur);b.api.admin(cur)
            cur.execute('set local role cp7_capture')
            cur.execute('select public.erp_cp7_set_production_policy_v1(%s::jsonb,%s)',(json.dumps([a]),uuid.uuid4()))
        p02.refused(cur,poisoned_compute,'permission denied')
        p02.refused(cur,lambda:cur.execute("update cp7_identity.production_policy set state='ACTIVE'"),'CP7_POLICY_HISTORY_IMMUTABLE')
        return dict(status='PASS',unauthorized_denied=True,replay_revocation_denied=True,compute_cannot_write_policy=True,policy_cannot_write_erp=True)
    def malformed():
        f=fixture(cur,today);a=proposal(row(get(cur,f['skus']),f['skus'][0]))
        for bad in [dict(a,policy_revision=0),dict(a,private_cost='1'),dict(a,reason={'text':'bad'})]:
            p02.refused(cur,lambda:apply(cur,[bad]),'CP7_POLICY_FIELDS_INVALID')
        p02.refused(cur,lambda:apply(cur,[a,a]),'CP7_POLICY_DUPLICATE_SCOPE')
        assert cur.execute('select count(*) from cp7_identity.production_policy').fetchone()[0]==0
        return dict(status='PASS',malformed_and_duplicate_refused=True,no_partial_rows=True)
    return [('P03_STATUS_DOMAIN_BOUNDARY',status_boundary),('P03_REPLAY_CONFLICT',replay),('P03_BULK_ATOMIC_STALE',atomic),
            ('P03_MEMBERSHIP_REVIEW',membership),('P03_PAST_REVIEW_PAUSED',past_review),('P03_PRIVILEGES_REVOKE',privileges),('P03_MALFORMED_NO_PARTIAL',malformed),
            ('P03_PRICE_REVISION_POLICY_STABLE',price_only),('P03_FUTURE_MEMBERSHIP_REVIEW',future_members)]

def races(tools,today):
    def competing():
        with tools.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);a=proposal(row(get(cur,f['skus']),f['skus'][0]));conn.commit()
        start=threading.Barrier(2)
        def save(state):
            with tools.connect() as conn,conn.cursor() as cur:
                start.wait(timeout=5)
                try:apply(cur,[dict(a,state=state)]);conn.commit();return 'PASS'
                except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            x=pool.submit(save,'STOPPED');y=pool.submit(save,'ACTIVE');results=[x.result(timeout=20),y.result(timeout=20)]
        assert results.count('PASS')==1 and results.count('CP7_POLICY_VERSION_STALE')==1,results
        with tools.connect() as conn,conn.cursor() as cur:assert cur.execute('select count(*) from cp7_identity.production_policy').fetchone()[0]==1
        return dict(status='PASS',exactly_one_committed=True,loser_stale=True)
    def waiting_change(kind):
        with tools.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);a=proposal(row(get(cur,f['skus']),f['skus'][0]));subject,role=p02.custom_actor(cur)
            cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'master.product.manage')",(role,));conn.commit()
        key=str(uuid.uuid4())
        with tools.connect() as holder,holder.cursor() as h:
            h.execute("select pg_advisory_xact_lock(hashtextextended('CP7_POLICY_REQUEST:'||%s||':'||%s,0))",(subject,key))
            def waiting():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:apply(cur,[a],key,subject);conn.commit();return 'UNEXPECTED_SUCCESS'
                    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(waiting);deadline=time.monotonic()+10;blocked=False
                try:
                    with tools.connect(autocommit=True) as inspect,inspect.cursor() as c:
                        while time.monotonic()<deadline:
                            c.execute('select pg_stat_clear_snapshot()')
                            blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event='advisory' and pid<>pg_backend_pid())").fetchone()[0]
                            if blocked:break
                            time.sleep(.03)
                    assert blocked,'POLICY_NOT_WAITING_ON_REAL_REQUEST_LOCK'
                    with tools.connect() as change,change.cursor() as c:
                        if kind=='REVOKE':c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='master.product.manage'",(role,))
                        else:move(c,f)
                        change.commit()
                finally:holder.rollback()
                error=future.result(timeout=15)
        expected='CP7_POLICY_ACCESS_DENIED' if kind=='REVOKE' else 'CP7_POLICY_MEMBERSHIP_STALE'
        assert expected in error,error
        with tools.connect() as conn,conn.cursor() as cur:
            assert cur.execute('select count(*) from cp7_identity.production_policy').fetchone()[0]==0
            assert cur.execute('select count(*) from cp7_identity.commands').fetchone()[0]==0
        return dict(status='PASS',change_during_wait=kind,refusal=error,partial_policy_rows=0,partial_command_rows=0)
    def duplicate():
        with tools.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);a=proposal(row(get(cur,f['skus']),f['skus'][0]));conn.commit()
        key=str(uuid.uuid4());start=threading.Barrier(2)
        def save():
            with tools.connect() as conn,conn.cursor() as cur:
                start.wait(timeout=5);r=apply(cur,[a],key);conn.commit();return r
        with ThreadPoolExecutor(max_workers=2) as pool:
            x=pool.submit(save);y=pool.submit(save);results=[x.result(timeout=20),y.result(timeout=20)]
        assert results[0]['applied']==results[1]['applied'] and sum(r['replayed'] for r in results)==1
        with tools.connect() as conn,conn.cursor() as cur:assert cur.execute('select count(*) from cp7_identity.production_policy').fetchone()[0]==1
        return dict(status='PASS',one_policy_for_duplicate_request=True)
    return [('P03_COMPETING_POLICY_REVISIONS',competing),('P03_REVOKE_WHILE_WAITING',lambda:waiting_change('REVOKE')),
        ('P03_MEMBERSHIP_WHILE_WAITING',lambda:waiting_change('MEMBERSHIP')),('P03_DUPLICATE_REQUEST_RACE',duplicate)]

def http_cases(http,today):
    def real_auth():
        owner=http.login('OWNER','p03-owner');operator=http.login('ADMIN','p03-read-only')
        with http.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today)
            cur.execute("delete from erp.app_role_permissions where role_id=(select id from erp.app_roles where role_code='ADMIN') and permission_key='master.product.manage'")
            conn.commit()
        got=owner.rpc('erp_cp7_get_production_policy_v1',dict(p_skus=f['skus']));assert got['status']==200,got
        a=proposal(row(got['body'],f['skus'][0]));args=dict(p_changes=[a],p_request=str(uuid.uuid4()))
        assert http.anon_rpc('erp_cp7_set_production_policy_v1',args)['status'] in (401,403,404)
        assert operator.rpc('erp_cp7_set_production_policy_v1',args)['status']==403
        result=owner.rpc('erp_cp7_set_production_policy_v1',args);assert result['status']==200,result
        assert owner.rpc('erp_cp7_set_production_policy_v1',args)['body']['replayed']
        with http.connect() as conn,conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_set_production_policy_v1',args)['status']==403
        return dict(status='PASS',real_auth=True,write_and_replay=True,same_token_revoked=True,read_only_actor_denied=True)
    return [('P03_HTTP_POLICY_AUTH_REPLAY_REVOKE',real_auth)]
