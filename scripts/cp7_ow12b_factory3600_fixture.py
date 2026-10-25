"""Separate SYNTHETIC 1200 commercial SKUs x 3 physical sizes timing fixture.

No default policy, price, rate, financial result or historical model is created.
The older qualified3600 fixture remains unchanged. Caller must be an isolated
Native qualification transaction running as the existing test administrator.
"""
SQL={
 'sizes':"""insert into erp.sizes(id,size_code,sort_order,is_active)
 select gen_random_uuid(),'OW12BF36-S'||g,g,true from generate_series(1,3)g""",
 'models':"""insert into erp.product_models(id,model_code,model_name,is_active)
 select gen_random_uuid(),'OW12BF36-M'||g,'OW12B SYNTHETIC three-size model '||g,true from generate_series(1,1200)g""",
 'products':"""insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,product_name,identity_root_id,effective_from,created_at,is_active,is_portal_visible)
 select x.id,'OW12BF36-'||m.n,m.id,b.brand_id,'OW12BF36',s.id,'OW12B SYNTHETIC SKU '||m.n||' size '||s.size_code,x.id,
 now()-interval'131 days',now()-interval'131 days',true,true
 from(select id,regexp_replace(model_code,'^OW12BF36-M','')::integer n from erp.product_models where model_code like 'OW12BF36-M%%')m
 cross join(select id,size_code from erp.sizes where size_code like 'OW12BF36-S%%')s
 cross join(select brand_id from erp.products where id=%s)b
 cross join lateral(select gen_random_uuid()id where m.id is not null and s.id is not null)x""",
 'commercial':"""insert into erp.bf_skus_v1(id,brand_id,model_id,color_name,sku,revision)
 select gen_random_uuid(),brand_id,model_id,color_name,sku,1 from erp.products where sku like 'OW12BF36-%%'
 group by brand_id,model_id,color_name,sku""",
 'versions':"""insert into erp.bf_sku_versions_v1(id,sku_id,revision,effective_from,settings,reason,actor,request_id)
 select gen_random_uuid(),id,1,now()-interval'131 days','{}'::jsonb,
 'EXPLICIT SYNTHETIC dimensional timing fixture; no prices, rates or policy assumed',%s,gen_random_uuid()
 from erp.bf_skus_v1 where sku like 'OW12BF36-%%'""",
 'members':"""insert into erp.bf_sku_members_v1(version_id,product_root)
 select v.id,p.identity_root_id from erp.products p join erp.bf_skus_v1 s on s.brand_id=p.brand_id and s.sku=p.sku
 join erp.bf_sku_versions_v1 v on v.sku_id=s.id and v.revision=1
 where p.sku like 'OW12BF36-%%'""",
 'openings':"""insert into erp.fg_stock_movements(id,product_id,lot_id,location_id,quality_grade,movement_type,qty_signed,unit_hpp_snapshot,source_type,physical_at,system_created_at)
 select gen_random_uuid(),p.id,null,%s,'GRADE_A','OPENING',800,10,'OW12BF36_SYNTHETIC',now()-interval'130 days',now()-interval'130 days'
 from erp.products p where p.sku like 'OW12BF36-%%'""",
 'movements':"""insert into erp.fg_stock_movements(id,product_id,lot_id,location_id,quality_grade,movement_type,qty_signed,unit_hpp_snapshot,source_type,physical_at,system_created_at)
 select gen_random_uuid(),p.id,null,%s,'GRADE_A','SALE',-(1+(g%%6)),10,'OW12BF36_SYNTHETIC',
 now()-((g%%120)||' days')::interval-interval'2 hours',now()-interval'1 hour'
 from erp.products p cross join generate_series(1,100)g where p.sku like 'OW12BF36-%%'""",
 'shape':"""select
 (select count(*)from erp.products where sku like 'OW12BF36-%%')product_count,
 (select count(*)from erp.bf_skus_v1 where sku like 'OW12BF36-%%')commercial_sku_count,
 (select count(distinct size_id)from erp.products where sku like 'OW12BF36-%%')size_count,
 (select count(distinct identity_root_id)from erp.products where sku like 'OW12BF36-%%')physical_root_count,
 (select count(*)from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id join erp.bf_skus_v1 s on s.id=v.sku_id where s.sku like 'OW12BF36-%%')member_count,
 (select count(*)from erp.fg_stock_movements where source_type='OW12BF36_SYNTHETIC')movement_count,
 (select count(*)from(select brand_id,sku from erp.products where sku like 'OW12BF36-%%'group by brand_id,sku having count(*)<>3 or count(distinct size_id)<>3)x)invalid_sku_count"""
}
EXPECTED=(3600,1200,3,3600,3600,363600,0)


def seed(cur,base_product,location,actor):
 """Bulk labelled fixture only; restore caller role setting even on refusal."""
 assert cur.execute("select current_user='postgres'").fetchone()[0],'FACTORY3600_TEST_ADMIN_REQUIRED'
 assert cur.execute("select count(*)from erp.products where sku like 'OW12BF36-%%'").fetchone()[0]==0,'FACTORY3600_FIXTURE_ALREADY_PRESENT'
 prior=cur.execute('show session_replication_role').fetchone()[0]
 cur.execute('savepoint ow12b_factory3600_seed')
 try:
  cur.execute("select set_config('session_replication_role','replica',true)")
  parameters=dict(products=(base_product,),versions=(actor,),openings=(location,),movements=(location,))
  for name in ('sizes','models','products','commercial','versions','members','openings','movements'):
   cur.execute(SQL[name],parameters.get(name,()))
  cur.execute("select set_config('session_replication_role',%s,true)",(prior,))
  for table in ('products','bf_skus_v1','bf_sku_versions_v1','bf_sku_members_v1','fg_stock_movements'):
   cur.execute('analyze erp.'+table)
  observed=cur.execute(SQL['shape']).fetchone();assert observed==EXPECTED,('FACTORY3600_DIMENSIONAL_SHAPE',observed)
 except Exception:
  cur.execute('rollback to savepoint ow12b_factory3600_seed');raise
 finally:cur.execute('release savepoint ow12b_factory3600_seed')
 return dict(products=3600,commercial_SKUs=1200,physical_sizes=3,physical_roots=3600,movements=363600,
  exactly_three_distinct_physical_sizes_per_commercial_SKU=True,synthetic_fixture=True,
  actual_Native_qualification=False,official_finance_included=False,full_factory3600_qualified=False,production_go=False)
