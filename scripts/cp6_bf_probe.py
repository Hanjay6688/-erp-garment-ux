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
    return call(cur,'SAVE_GROUPS',dict(effective_from=at.isoformat(),reason='BF synthetic owner scenario',groups=groups),key)

def foundation(cur,today):
    rows=products(cur);roots=[r[0] for r in rows]
    now=one(cur,'select clock_timestamp()');at=now-timedelta(minutes=4)
    g=group(cur,roots,at);key=str(uuid.uuid4());result=save(cur,[g],at,key);again=save(cur,[g],at,key)
    b.chain.production.owner(cur)
    workspace=one(cur,'select public.erp_get_sku_workspace_v1(%s::jsonb)',json.dumps(dict(roots=roots),default=str))
    assert workspace['lookups'] is not None and len(workspace['selected_products'])==3
    b.api.admin(cur)
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


def rollback_sql():
    return (build.ROOT/'supabase/dev/cp6_bf_t2_rollback.sql').read_text().replace('\nbegin;\n','\n').replace('\ncommit;\n','\n')


def recovery_unused(cur,today):
    b.api.admin(cur)
    cur.execute(rollback_sql(),prepare=False)
    result=be.verified(cur)
    assert not one(cur,"select exists(select 1 from erp.schema_migrations where version='v2.6.20bf')")
    assert not one(cur,"select to_regclass('erp.bf_skus_v1') is not null")
    assert one(cur,"select count(*) from pg_constraint where conrelid='erp.po_work_component_snapshots'::regclass and conname='po_work_component_snapshots_po_id_work_component_id_key'")==1
    return b.verdict(dict(prior_family_exact=bool(result),tables_removed=True,unique_restored=True))


def recovery_used(cur,today):
    rows=products(cur,('27',));at=one(cur,"select clock_timestamp()-interval '4 minutes'")
    g=group(cur,[rows[0][0]],at);save(cur,[g],at)
    blocked=b.refused(cur,lambda:cur.execute(rollback_sql(),prepare=False),'BF_USED_ROLLBACK_REFUSED')
    return b.verdict(dict(refused=blocked['ok'],data_kept=one(cur,'select revision from erp.bf_skus_v1 where id=%s',g['id'])==1))


def production_ranges(cur,today):
    """Two real SKU tariffs in one wave, four physical sizes, ordinary work/laundry/QC posting. No ledger seeding."""
    prod,base=b.chain.production,b.chain.base
    now=one(cur,'select clock_timestamp()');at=now-timedelta(minutes=4)
    clock=lambda hour,minute=0:now-timedelta(seconds=(19-hour-minute/60)*10)
    rows=products(cur,('31','32','33','27'));roots=[p for p,_ in rows];sizes=[s for _,s in rows];qtys=[4,7,2,3]
    vendor,process=str(uuid.uuid4()),str(uuid.uuid4());tag=uuid.uuid4().hex[:8]
    cur.execute("insert into erp.laundry_vendors(id,vendor_code,vendor_name,is_active) values(%s,%s,'BF service',true)",(vendor,'BF-'+tag))
    cur.execute("insert into erp.wash_processes(id,process_code,process_name,is_active) values(%s,%s,'BF wash',true)",(process,'BF-'+tag))
    def cfg(work,laundry):return dict(price='185000.00',bom=[],work_rates=[dict(contractor_id=None,work_component_id=prod.COMPONENT,rate=work)],
        laundry_rates=[dict(vendor_id=vendor,kind='PROCESS',ref_id=process,rate_status='KNOWN',rate=laundry,reason='Synthetic shared SKU rate')])
    a=group(cur,roots[:3],at,settings=cfg('10.00','5.00'));c=group(cur,[roots[3]],at,settings=cfg('30.00','9.00'));save(cur,[a,c],at)
    snapshots={}
    def setup(cur,po,wave,batch,yields,when):
        call(cur,'BIND_WAVE',dict(cutting_group_id=wave,expected_version=one(cur,'select erp.bf_wave_revision_v1(%s)',wave),
            references=[dict(size_id=s,sku_id=a['id'] if i<3 else c['id']) for i,s in enumerate(sizes)]))
        cur.execute('insert into erp.po_work_component_snapshots(po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at) values(%s,%s,1,3,%s)',(po,prod.COMPONENT,when(9,30)))
        prod.owner(cur);cur.execute('select erp.ensure_po_work_component_snapshots(%s,%s)',(po,when(10)));b.api.admin(cur)
        for sku,qty in ((a['id'],13),(c['id'],3)):
            snap=one(cur,'select s.id::text from erp.po_work_component_snapshots s join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id where s.po_id=%s and v.sku_id=%s and s.work_component_id=%s',po,sku,prod.COMPONENT)
            snapshots[sku]=snap;e=str(uuid.uuid4());b.chain.peer.ordinary(cur)
            cur.execute("insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes,created_by) values(%s,%s,%s,%s,%s,%s,'DRAFT','BF scoped work',%s)",(e,'BF-'+e,po,prod.CONTRACTOR,wave,when(10),base.OPERATOR_APP))
            cur.execute('insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot) values(%s,%s,%s,%s,%s,0)',(e,snap,prod.COMPONENT,qty,qty))
            cur.execute('select erp.post_work_completion(%s)',(e,));prod.owner(cur)
            cur.execute('select public.erp_record_sewing_terminal_v1(%s::jsonb,%s)',(json.dumps(dict(work_completion_id=e,qty_pcs=qty,reason='BF scoped physical sewing')),uuid.uuid4()));b.api.admin(cur)
    fx=b.two_size_fixture(cur,b.case_day(today),'BF-RANGES',size_quantities=list(zip(sizes,qtys)),clock=clock,work_setup=setup,service_refs=(vendor,process))
    payload=dict(distribution_batch_id=fx['batch'],vendor_id=vendor,wash_process_id=process,target_dyeing_color='BF-BLUE',physical_at=clock(11).isoformat(),reason='BF two SKU tariffs one wave',lines=[dict(size_id=s,qty_sent_pcs=q) for s,q in zip(sizes,qtys)])
    sent=b.bd(cur,'POST_PRICED_DELIVERY',dict(delivery=payload,expected_version=str(base.group_version(cur,fx['group'])),pricing={}))
    delivery=sent['delivery_id']
    ds=dict(cur.execute('select s.size_id::text,s.id::text from erp.laundry_delivery_batch_size_lines s join erp.laundry_delivery_lines l on l.id=s.delivery_line_id where l.delivery_id=%s',(delivery,)).fetchall())
    received=b.chain.laundry_action(cur,'POST_RECEIPT',dict(delivery_id=delivery,wash_process_id=process,physical_at=clock(13).isoformat(),reason='BF exact-size return',
        lines=[dict(delivery_batch_size_line_id=ds[s],qty_good_received=q,qty_bs_laundry=0,bs_product_id=None) for s,q in zip(sizes,qtys)]),base.delivery_version(cur,delivery))
    line=b.receipt_line(cur,received['receipt_id'])
    rs=dict(cur.execute('select d.size_id::text,r.id::text from erp.laundry_receipt_batch_size_lines r join erp.laundry_delivery_batch_size_lines d on d.id=r.delivery_batch_size_line_id where r.receipt_line_id=%s',(line,)).fetchall())
    b.chain.laundry_action(cur,'POST_FINAL_SKU',dict(cutting_group_id=fx['group'],destination_location_id=base.LOCATION,physical_at=clock(14).isoformat(),reason='BF exact-size final goods',good_qty_pcs=16,completion_mode='ALL_READY',
        lines=[dict(final_product_id=p,qty_good_pcs=q,qty_bs_pcs=0,source_laundry_receipt_line_id=line,source_laundry_receipt_batch_size_line_id=rs[s]) for (p,s),q in zip(rows,qtys)]),base.group_version(cur,fx['group']))
    lots=[one(cur,"select id::text from erp.fg_lots where po_id=%s and product_id=%s and lot_origin='PRODUCTION'",fx['po'],p) for p in roots]
    labor=[one(cur,"select erp.cp6_lot_work_cost_v2620c(%s,'LABOR')",lot) for lot in lots]
    laundry=[one(cur,'select amount from erp.bd_laundry_receipt_allocations_v1 where receipt_batch_size_line_id=%s',rs[s]) for s in sizes]
    physical=[one(cur,'select sum(qty_signed) from erp.fg_stock_movements where lot_id=%s',lot) for lot in lots]
    price=[one(cur,'select erp.resolve_product_price_at(%s,%s)',p,clock(14)) for p in roots]
    return b.verdict(dict(four_physical_sizes=physical==qtys,work_costs=labor==[40,70,20,90],laundry_costs=laundry==[20,35,10,27],
        shared_selling_price=price==[185000]*4,exact_total=sent['estimated_cost']==92,
        immutable_provenance=one(cur,'select count(distinct c.bf_sku_version_id) from erp.bd_laundry_charge_lines_v1 c join erp.laundry_delivery_lines l on l.id=c.delivery_line_id where l.delivery_id=%s',delivery)==2),
        labor=list(map(str,labor)),laundry=list(map(str,laundry)),physical=physical)


def imported_range_rows(today,explicit=True,stock='10'):
    import copy
    cut=today-timedelta(days=10);r=b.bbp.s02_rows(cut,stock=stock)
    r['SIZE'].append(dict(size_code='{C}32'))
    sibling=copy.deepcopy(r['PRODUCT'][0]);sibling['size_code']='{C}32';r['PRODUCT'].append(sibling)
    r['OPENING_BALANCE_ITEM'][0]['size_code']='{C}32'
    r['CONTRACTOR']=[dict(contractor_code='{C}',contractor_name='BF imported mandor',contractor_type='MANDOR')]
    r['OPENING_ACCESSORY_CUSTODY']=[dict(custody_kind='CUSTOMER_GARMENT',custody_key='{C}-KNOWN',customer_code='{C}',description='Celana servis ukuran 32',qty='1',product_sku='{C}P',source_lot='{C}-GARMENT32'),
      dict(custody_kind='CUSTOMER_GARMENT',custody_key='{C}-TEXT',customer_code='{C}',description='Celana pelanggan belum punya SKU',qty='1',source_lot='{C}-DESCRIPTIVE')]
    r['OPENING_POCKET_SEWING']=[dict(document_number='BF-JAHIT-{C}',line_number='1',physical_date=str(cut-timedelta(days=1)),contractor_code='{C}',qty='2',target_kind='COGS',control_key='SEWN',control_qty='2',product_sku='{C}P',sold_reference='HISTORICAL-SALE-{C}')]
    if explicit:
      for k in ['OPEN_SALES_DRAFT','OPENING_POCKET_SEWING']:
        r[k][0].update(size_code='{C}32',brand_code='{C}',model_code='{C}',color_name='Blue')
      r['OPENING_ACCESSORY_CUSTODY'][0].update(size_code='{C}32',brand_code='{C}',model_code='{C}',color_name='Blue')
    return r


def import_ambiguity(cur,today):
    f=b.bbp.production_post(cur,today,imported_range_rows(today,False),expect=True)
    errors={k:e for k,e in f['errors']}
    count=one(cur,'select count(*) from erp.products where sku=%s',f['code']+'P')
    return b.verdict(dict(all_three_fail_before_apply=all('SIZE_ALLOCATION_REQUIRED' in errors.get(k,'') for k in ['OPEN_SALES_DRAFT','OPENING_ACCESSORY_CUSTODY','OPENING_POCKET_SEWING']),no_partial_products=count==0),errors=errors)


def import_exact(cur,today):
    f=b.bbp.production_post(cur,today,imported_range_rows(today));code=f['code']
    p=one(cur,'select p.id from erp.products p join erp.sizes z on z.id=p.size_id where p.sku=%s and z.size_code=%s',code+'P',code+'32')
    sale=one(cur,'select i.product_id from erp.sales_items i join erp.sales_headers h on h.id=i.sale_id where h.sale_number=%s','SD-'+code)
    custody=cur.execute('select product_id from erp.bc_customer_custody_v1 where customer_id=(select id from erp.customers where customer_code=%s) order by product_id nulls last',(code,)).fetchall()
    sewing=one(cur,"select product_id from erp.be_pocket_sewing_v1 where batch_id=%s and target_kind='COGS'",f['batch'])
    counts=(one(cur,'select count(*) from erp.sales_headers where sale_number=%s','SD-'+code),one(cur,'select count(*) from erp.be_pocket_sewing_v1 where batch_id=%s',f['batch']))
    again=b.api.invoke(cur,'FINALIZE',f['batch']);b.api.admin(cur)
    return b.verdict(dict(sale_exact=sale==p,custody_exact=custody==[(p,),(None,)],cogs_exact=sewing==p,
      one_reservation=b.bbp.s02_free(cur,code)==7,replay=again['status']=='POSTED' and counts==(1,1)),product=str(p),counts=counts)


def import_insufficient(cur,today):
    rows=imported_range_rows(today,stock='2');rows['OPENING_CONTROL'][0]['amount']='12.00'
    before=one(cur,'select count(*) from erp.sales_headers')
    # Nested ordinary transaction refusal must roll back the complete import, including masters and custody.
    blocked=b.refused(cur,lambda:b.bbp.production_post(cur,today,rows),'BB_S02_RESERVATION_REFUSED')
    return b.verdict(dict(refused=blocked['ok'],no_partial_draft=one(cur,'select count(*) from erp.sales_headers')==before),refusal=blocked)


def import_rework_source(cur,today):
    code=b.bbp.rework_masters(cur,today);b.api.admin(cur)
    root=one(cur,'select id from erp.products where sku=%s',code+'P')
    sid=one(cur,'insert into erp.sizes(size_code,is_active) values(%s,true) returning id',code+'32')
    cur.execute('insert into erp.product_model_sizes(model_id,size_id) select model_id,%s from erp.products where id=%s',(sid,root))
    sibling=one(cur,"insert into erp.products(sku,model_id,brand_id,color_name,size_id,product_name,effective_from,is_active) select sku,model_id,brand_id,color_name,%s,product_name,effective_from,true from erp.products where id=%s returning id",sid,root)
    r=b.bbp.rework_import_rows()
    for x in r['OPENING_BALANCE_ITEM']:
      if x.get('balance_type')=='BS':x['size_code']=code+'32'
    refused=b.bbp.rework_post(cur,today,code,r,expect=True)
    errors=' '.join(e for _,e in refused['errors'])
    # A sibling's valid recipe must not satisfy the source BS size.
    return b.verdict(dict(source_bom_required='BB_REWORK_ACCESSORY_BOM_REQUIRED' in errors,
      source_without_recipe=one(cur,'select count(*) from erp.accessory_bom_versions where product_id=%s',sibling)==0,
      other_size_has_recipe=one(cur,'select count(*) from erp.accessory_bom_versions where product_id=%s',root)>0),errors=errors)
