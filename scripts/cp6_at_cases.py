"""AT controls preserve legacy opening rules while correcting new WIP output."""
from datetime import timedelta
import uuid
import cp6_at_probe as audit
import cp6_as_probe as peer
import cp6_ao_ap_installed as api
import cp6_initial_import_production_trial as production
import cp6_successor_regression as boundary


def historical_bs(cur,today,active_old,qualified):
    f=production.fixture(api,cur,today);code=f['code']
    model=cur.execute('insert into erp.product_models(model_code,model_name) values(%s,%s) returning id',(code,code)).fetchone()[0]
    brand=cur.execute('insert into erp.brands(brand_code,brand_name) values(%s,%s) returning id',(code,code)).fetchone()[0]
    size=cur.execute('insert into erp.sizes(size_code) values(%s) returning id',(code,)).fetchone()[0]
    old=uuid.uuid4();split=peer.invoice.at(today-timedelta(days=10),0)
    cur.execute('''insert into erp.products(id,sku,product_name,model_id,brand_id,size_id,color_name,is_active,effective_from,effective_to,identity_root_id)
        values(%s,%s,'Historical opening identity',%s,%s,%s,'Blue',%s,%s,%s,%s)''',
        (old,code,model,brand,size,active_old,peer.invoice.at(today-timedelta(days=20),0),split,old))
    new_color='Green' if qualified else 'Blue'
    new=cur.execute('''insert into erp.products(sku,product_name,model_id,brand_id,size_id,color_name,is_active,effective_from,identity_root_id,supersedes_product_id)
        values(%s,'Current identity',%s,%s,%s,%s,true,%s,%s,%s) returning id''',(code,model,brand,size,new_color,split,old,old)).fetchone()[0]
    api.upload(cur,f['batch'],'PRODUCT',[dict(sku=code,product_name='Current identity',model_code=code,brand_code=code,size_code=code,color_name=new_color)])
    for row in f['rows']:
        if row['balance_type'] in ('BS','FINISHED_GOODS'):
            row.update(brand_code=code,model_code=code,size_code=code,color_name='Blue' if row['balance_type']=='BS' else new_color)
    api.upload(cur,f['batch'],'OPENING_BALANCE_ITEM',f['rows'])
    before=production.effects(api,cur)
    result=api.invoke(cur,'FINALIZE',f['batch'])
    errors=[dict(entity=r['entity'],errors=r['errors']) for r in api.read(cur,f['batch'])['batch']['rows'] if r['validation_status']=='ERROR']
    if qualified:
        assert result['status']=='POSTED' and not errors,(result,errors)
        chosen=cur.execute('''select i.product_id from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id
            where h.migration_batch_id=%s and i.balance_type='BS' ''',(f['batch'],)).fetchone()[0]
        assert chosen==old,(chosen,old)
        production.truth(cur)
        return dict(status='PASS',qualified_historical_bs_preserved=True,display_active=active_old,chosen_product=chosen,current_product=new)
    assert result['status']=='DRAFT' and result['error_rows']>0 and errors,(result,errors)
    assert any('exactly one identity' in error for row in errors for error in row['errors']),errors
    assert production.effects(api,cur)==before
    assert cur.execute('select count(*) from erp.opening_balance_headers where migration_batch_id=%s and status=\'POSTED\'',(f['batch'],)).fetchone()==(0,)
    return dict(status='PASS',historical_ambiguity_refused=True,display_active=active_old,no_economic_posting=True,
                corrected_audit_assumption='Expiry does not disambiguate existing physical opening stock',errors=errors)


def intraday(cur,today,variant):
    f=production.fixture(api,cur,today);_,sources=production.finalize(api,cur,f)
    model,size=cur.execute('select model_id,size_id from erp.products where sku=%s',(f['code'],)).fetchone()
    code=f['code']+'DAY';brand=cur.execute('insert into erp.brands(brand_code,brand_name) values(%s,%s) returning id',(code,code)).fetchone()[0]
    day=today-timedelta(days=3)
    split=peer.invoice.at(day,0 if variant=='MIDNIGHT' else 12)
    old,new=audit.series(cur,f['code'],model,brand,size,peer.invoice.at(day-timedelta(days=2),0),split)
    p=dict(batch_id=f['batch'],opening_item_id=sources['WIP']['opening_item_id'],expected_remaining='8',operation='COMPLETE',
           qty_pcs='4',product_sku=f['code'],brand_code=code,location_code=f['code']+'F',date=str(day),reason='AT business day identity boundary')
    if variant=='EARLY_ID':p['product_id']=str(old)
    if variant=='LATE_ID':p['product_id']=str(new)
    before=boundary.snapshot(cur);result,error=audit.attempt(cur,lambda:api.call(cur,'WIP_OUTPUT',p))
    if variant=='AMBIGUOUS_DAY':
        assert error and 'AMBIGUOUS' in error['message'] and boundary.snapshot(cur)==before,(result,error)
        return dict(status='PASS',two_intraday_versions_require_explicit_id=True,refused_atomically=True)
    assert result and not error,(result,error)
    chosen,at,start,end=cur.execute('''select p.id,l.produced_at,p.effective_from,p.effective_to
        from erp.fg_lots l join erp.products p on p.id=l.product_id where l.id=%s''',(result['lot_id'],)).fetchone()
    assert chosen==(old if variant=='EARLY_ID' else new)
    assert start<=at and (end is None or at<end)
    production.truth(cur);production.reverse_output(api,cur,f,result)
    return dict(status='PASS',variant=variant,chosen=chosen,physical_at=at,valid_from=start,valid_to=end,linked_inverse=True)


def cases(cur,today):
    result=[]
    for zone in ('UTC','Pacific/Kiritimati'):
        for variant in ('AUTO_CURRENT','EXPLICIT_CURRENT','EXPIRED_ID','OLD_INACTIVE'):
            result.append(('WIP_VERSION:'+zone+':'+variant,lambda v=variant,z=zone:audit.versioned_wip(cur,today,v,z)))
    for active in (True,False):
        for qualified in (False,True):
            result.append(('HISTORICAL_BS:'+str(active)+':'+str(qualified),lambda a=active,q=qualified:historical_bs(cur,today,a,q)))
    for variant in ('MIDNIGHT','AMBIGUOUS_DAY','EARLY_ID','LATE_ID'):
        result.append(('INTRADAY:'+variant,lambda v=variant:intraday(cur,today,v)))
    return result
