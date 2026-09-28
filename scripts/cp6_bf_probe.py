"""BF writer qualification on the disposable AN..BE chain. Never independent acceptance."""
from datetime import timedelta
import hashlib,json,re,uuid
import psycopg
import cp6_be_probe as be
import cp6_bf_build as build

b=be.bdp
one=b.one

def verified(cur):
    result=be.verified(cur)
    assert one(cur,"select count(*) from erp.schema_migrations where version='v2.6.20bf'")==1
    sql=build.OUT.read_text()
    for signature in dict.fromkeys(build.REPLACED+build.new_functions()):
        name=signature.split('(')[0];schema,fn=name.split('.')
        start=list(re.finditer(r'(?i)create or replace function '+re.escape(name)+r'\(',sql))[-1].start()
        pos=sql.index('$function$',start)+len('$function$');body=sql[pos:sql.index('$function$',pos)]
        rows=cur.execute('select p.prosrc from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s and p.proname=%s',(schema,fn)).fetchall()
        assert len(rows)==1 and rows[0][0]==body,('BF_INSTALLED_SOURCE_MISMATCH',signature)
    for table in build.NEW_TABLES:
        assert one(cur,'select relrowsecurity from pg_class where oid=%s::regclass','erp.'+table),table
    return dict(result,stage='BE_PLUS_BF_T1',bf_sql_sha256=hashlib.sha256(sql.encode()).hexdigest())

def install():
    with psycopg.connect(b.boundary.PG,autocommit=True) as conn:conn.execute(build.OUT.read_text(),prepare=False)
    with psycopg.connect(b.boundary.ADMIN) as conn,conn.cursor() as cur:
        result=verified(cur);conn.rollback()
    return result

def call(cur,action,payload,key=None,auth=None):
    if auth:b.bcp.session(cur,auth)
    else:b.chain.production.owner(cur)
    result=cur.execute('select public.erp_save_sku_action_v1(%s,%s::jsonb,%s)',
        (action,json.dumps(payload,default=str),str(key or uuid.uuid4()))).fetchone()[0]
    b.api.admin(cur);return result

def products(cur,labels=('31','32','33'),tag=None):
    b.api.admin(cur);tag=tag or 'BF-'+uuid.uuid4().hex[:8];rows=[]
    for i,label in enumerate(labels):
        sid=str(uuid.uuid4())
        cur.execute('insert into erp.sizes(id,size_code,sort_order,is_active) values(%s,%s,%s,true)',(sid,tag+'-'+label,100+i))
        cur.execute('insert into erp.product_model_sizes(model_id,size_id,sort_order) values(%s,%s,%s)',(b.chain.production.MODEL,sid,100+i))
        rows.append((b.sized_product(cur,sid,tag),sid))
    return rows

def group(cur,roots,at,sku=None,gid=None,revision=0,settings=None):
    brand,model,color=cur.execute('select brand_id::text,model_id::text,color_name from erp.products where id=%s',(roots[0],)).fetchone()
    basis=one(cur,'select erp.bf_legacy_basis_v1(%s::uuid[],%s)',roots,at)
    return dict(id=gid or str(uuid.uuid4()),expected_version=str(revision),brand_id=brand,model_id=model,color_name=color,
        sku=sku or 'BF-SKU-'+uuid.uuid4().hex[:8],members=roots,legacy_basis=basis,
        settings=settings or dict(price='185000.00',bom=[],work_rates=[],laundry_rates=[]))

def save(cur,groups,at,key=None):
    return call(cur,'SAVE_GROUPS',dict(effective_from=at,reason='BF synthetic owner scenario',groups=groups),key)

def foundation(cur,today):
    rows=products(cur);roots=[r[0] for r in rows]
    now=one(cur,'select clock_timestamp()');at=now-timedelta(minutes=4)
    g=group(cur,roots,at);key=str(uuid.uuid4());result=save(cur,[g],at,key);again=save(cur,[g],at,key)
    prices=[one(cur,'select erp.resolve_product_price_at(%s,%s)',r,now) for r in roots]
    ids=cur.execute('select product_root::text,price_version_id::text,bom_version_id::text from erp.bf_sku_members_v1 where version_id=%s',(result['groups'][0]['version_id'],)).fetchall()
    bad=b.refused(cur,lambda:cur.execute("insert into erp.product_price_versions(product_id,price,effective_from) values(%s,1,%s)",(roots[1],now+timedelta(days=1))),'BF_SHARED_MASTER')
    stale=b.refused(cur,lambda:save(cur,[g],now),'STALE_VERSION')
    return b.verdict(dict(same_price=prices==[b.D('185000.00')]*3,physical_roots=len({x[0] for x in ids})==3,
        one_revision=one(cur,'select revision from erp.bf_skus_v1 where id=%s',g['id'])==1,
        replay=again['groups']==result['groups'] and again['replayed'],guard=bad['ok'],stale=stale['ok'],
        child_versions=len({x[1] for x in ids})==3 and len({x[2] for x in ids})==3),prices=list(map(str,prices)))

def optional_economics(cur,today):
    rows=products(cur,('27',));roots=[rows[0][0]];at=one(cur,"select clock_timestamp()-interval '4 minutes'")
    g=group(cur,roots,at,settings=dict(price=None,bom=None,work_rates=[],laundry_rates=[]))
    value=save(cur,[g],at)
    member=cur.execute('select price_version_id,bom_version_id from erp.bf_sku_members_v1 where version_id=%s',(value['groups'][0]['version_id'],)).fetchone()
    return b.verdict(dict(singleton=one(cur,'select count(*) from erp.bf_sku_members_v1 where version_id=%s',value['groups'][0]['version_id'])==1,
        no_invented_economics=member==(None,None)))

def temporal_move(cur,today):
    roots=[r[0] for r in products(cur,('31','32','33','34'))]
    now=one(cur,'select clock_timestamp()');t0=now-timedelta(minutes=4);t1=now-timedelta(minutes=2)
    a=group(cur,roots[:3],t0);c=group(cur,[roots[3]],t0)
    save(cur,[a,c],t0)
    a2=group(cur,roots,t1,sku=a['sku'],gid=a['id'],revision=1)
    c2=group(cur,[roots[3]],t1,sku=c['sku'],gid=c['id'],revision=1);c2['members']=[];c2['legacy_basis']=[]
    refused=b.refused(cur,lambda:save(cur,[a2],t1),'BF_MOVE_ATOMIC')
    save(cur,[a2,c2],t1)
    def memberships(at):return [one(cur,'select sku_id::text from erp.bf_sku_versions_v1 where id=erp.bf_version_at_v1(%s,%s)',r,at) for r in roots]
    return b.verdict(dict(atomic=refused['ok'],old=memberships(t0)==[a['id']]*3+[c['id']],
        new=memberships(t1)==[a['id']]*4,no_stock=one(cur,'select count(*) from erp.fg_stock_movements where product_id=any(%s::uuid[])',roots)==0))

def conflicts(cur,today):
    roots=[r[0] for r in products(cur)];at=one(cur,"select clock_timestamp()-interval '4 minutes'")
    cur.execute('insert into erp.product_price_versions(product_id,price,effective_from) values(%s,123,%s)',(roots[1],at-timedelta(days=1)))
    g=group(cur,roots,at);correct=g['legacy_basis'];g['legacy_basis']=[]
    blocked=b.refused(cur,lambda:save(cur,[g],at),'BF_BASIS_CHANGED')
    g['legacy_basis']=correct;save(cur,[g],at)
    future=at+timedelta(minutes=1);g2=group(cur,roots,future,sku=g['sku'],gid=g['id'],revision=1)
    g2['settings']['price']='190000.00';save(cur,[g2],future)
    return b.verdict(dict(explicit_basis=blocked['ok'],historical=all(one(cur,'select erp.resolve_product_price_at(%s,%s)',r,at)==185000 for r in roots),
        successor=all(one(cur,'select erp.resolve_product_price_at(%s,%s)',r,future)==190000 for r in roots)))
