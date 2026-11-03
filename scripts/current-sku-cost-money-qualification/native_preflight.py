"""One complete read-only prerequisite check before any monetary callback."""
from datetime import timedelta
from zoneinfo import ZoneInfo

FUNCTIONS=(
 'public.erp_get_product_conversion_workspace_v1(jsonb)',
 'public.erp_save_product_conversion_action_v1(text,jsonb,uuid)',
 'public.erp_save_accessory_service_action_v1(text,jsonb,uuid)',
 'public.erp_cp7_save_sale_v1(text,jsonb,uuid,text)',
 'erp.be_source_revision_v1(uuid,uuid)',
 'erp.be_post_usage_v1(jsonb,uuid)',
 'erp.post_material_supplier_invoice_v2(uuid,uuid,bigint,text)',
 'erp.save_material_supplier_invoice_draft_v2(jsonb,uuid,bigint)',
 'erp.reverse_material_supplier_invoice_v2(uuid,text,uuid,bigint)',
 'erp.post_opening_hpp_correction(uuid,numeric,text,date)',
 'cp7_sku_conversion.legacy_source_revision_v4(uuid,uuid,text)',
 'cp7_sku_conversion.reprice_document_money_v3(uuid,date,jsonb,jsonb,numeric)',
)
PERMISSIONS={
 'conversion_and_owner_native':('warehouse.brand_conversion.view','warehouse.brand_conversion.post','warehouse.brand_conversion.reverse',
     'warehouse.stock.adjust','finance.hpp.view','finance.hpp.manage'),
 'accessory_operator':('warehouse.accessory.view','warehouse.stock.adjust','finance.hpp.manage'),
 'sales_owner':('finance.ar.view','sales.invoice.view','sales.invoice.create','sales.invoice.post','sales.invoice.reverse',
     'sales.return.view','sales.return.create','sales.return.post','sales.return.reverse'),
}

def check(cur,today,business):
    n,f=business.n,business.f;n.require_local(cur);f.admin(cur)
    before=n.capture(cur);errors=[]
    now=cur.execute('select clock_timestamp()').fetchone()[0].astimezone(ZoneInfo('Asia/Jakarta'))
    if now.date()!=today:errors.append('PLANNED_BUSINESS_DAY_CHANGED')
    if now.hour==0 and now.minute<5:errors.append('POSITIVE_FIXTURE_WOULD_CROSS_WIB_DAY')
    available={sig:cur.execute('select to_regprocedure(%s)is not null',(sig,)).fetchone()[0]for sig in FUNCTIONS}
    errors.extend('MISSING_FUNCTION:'+sig for sig,found in available.items()if not found)
    pcs=cur.execute("select unit_code from erp.uom_definitions where upper(unit_code)='PCS'and dimension='COUNT'and is_active").fetchall()
    if len(pcs)!=1:errors.append('ONE_ACTIVE_COUNT_PCS_REQUIRED')
    accounts={code:cur.execute('select is_active,is_postable,account_type::text from erp.chart_accounts where account_code=%s',(code,)).fetchall()for code in('4100','5100')}
    for code,rows in accounts.items():
        if len(rows)!=1:errors.append('ACCOUNT_NOT_UNIQUE:'+code)
        elif rows[0][:2]!=(True,True):errors.append('ACCOUNT_NOT_ACTIVE_POSTABLE:'+code)
    location=cur.execute('select is_active,location_type from erp.locations where id=%s',(f.BASE.LOCATION,)).fetchone()
    if location!=(True,'FG_WAREHOUSE'):errors.append('CANONICAL_ACTIVE_FG_WAREHOUSE_REQUIRED')
    actors={}
    for name,select_actor in(
        ('conversion_and_owner_native',lambda:f.owner(cur)),
        ('accessory_operator',lambda:n.bc.session(cur)),
        ('sales_owner',lambda:business.moving.sales_cmd.auth.actor(cur,None)),
    ):
        # Each actor check must leave the original role, JWT and transaction
        # usable even when a permission query or retained actor helper refuses.
        cur.execute('savepoint money_prerequisite_actor')
        try:
            select_actor()
            permissions={key:cur.execute('select erp.has_permission(%s)',(key,)).fetchone()[0]for key in PERMISSIONS[name]}
            actors[name]=dict(role=cur.execute('select erp.current_app_role()::text').fetchone()[0],permissions=permissions)
            errors.extend('ACTOR_PERMISSION:'+name+':'+key for key,value in permissions.items()if value is not True)
            if actors[name]['role']not in('OWNER','ADMIN'):
                errors.append('NATIVE_INVOICE_POLICY_AND_INVERSES_REQUIRE_OWNER_ADMIN:'+name)
        except Exception as error:
            actors[name]=dict(status='REFUSED',error_type=type(error).__name__,
                sqlstate=getattr(error,'sqlstate',None),error=str(error))
            errors.append('ACTOR_CHECK_REFUSED:'+name)
        finally:
            cur.execute('rollback to savepoint money_prerequisite_actor')
            cur.execute('release savepoint money_prerequisite_actor')
            f.admin(cur)
    if n.capture(cur)!=before:errors.append('READ_ONLY_PREFLIGHT_CHANGED_CATALOG_ROWS_OR_SEQUENCES')
    proof=dict(status='PASS'if not errors else'REFUSED',errors=errors,functions=available,actors=actors,
        active_PCS=pcs,accounts=accounts,canonical_location=list(location)if location else None,
        business_day=str(today),observed_WIB=now.isoformat(),fixture_offsets_seconds=[-60,-59,-45,-40,-30,-20,-10],
        earliest_opening_day=str(today-timedelta(days=4)),material_receipt_day=str(today-timedelta(days=6)),
        posted_financial_fixtures='EXISTING_NATIVE_WRITERS_ONLY',source_graph='EXACT_QUALIFIED_PARENT_AND_ALL22_INSTALLATION',
        actual_ERP_cases=0,clock_changed=False)
    return proof
