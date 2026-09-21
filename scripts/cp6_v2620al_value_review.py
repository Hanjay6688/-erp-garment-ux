#!/usr/bin/env python3
"""Writer regression: original independent oracles plus affected value family."""
from pathlib import Path
from decimal import Decimal
from datetime import timedelta
import argparse, ast, hashlib, json, os, subprocess, traceback, uuid
import psycopg
import cp6_v2620al_runtime as runtime
import cp6_v2620al_review as setup
import cp6_final_ak_independent as oracle
from cp6_v2620n_rollback_guards import function_catalog

ROOT=Path('cp6-proof/writer-al')
actors,base,production=setup.actors,setup.base,setup.production


def extra_typed(cur,day,entity,field,value,valid):
    batch=oracle.new_batch(cur,day);actors.admin(cur);tag='ALV-'+uuid.uuid4().hex[:14]
    payloads={
        'BRAND':dict(brand_code=tag,brand_name='Synthetic AL brand'),
        'SIZE':dict(size_code=tag),
        'MODEL':dict(model_code=tag,model_name='Synthetic AL model'),
        'CUSTOMER':dict(customer_code=tag,customer_name='Synthetic AL customer'),
        'SUPPLIER':dict(supplier_code=tag,supplier_name='Synthetic AL supplier'),
        'CONTRACTOR':dict(contractor_code=tag,contractor_name='Synthetic AL contractor'),
        'ACCESSORY_CATEGORY':dict(category_code=tag,category_name='Synthetic AL category',base_uom_code='PCS'),
        'MATERIAL':dict(material_sku=tag,material_name='Synthetic AL material',material_type='OTHER',unit_code='PCS'),
    }
    if entity in ('PRODUCT','OPEN_PO'):
        product=base.create_product(cur,tag)
        brand,model,size,color=cur.execute('select b.brand_code,m.model_code,s.size_code,p.color_name from erp.products p join erp.brands b on b.id=p.brand_id join erp.product_models m on m.id=p.model_id join erp.sizes s on s.id=p.size_id where p.id=%s',(product,)).fetchone()
        payloads['PRODUCT']=dict(sku=tag+'-NEW',product_name='Synthetic AL product',brand_code=brand,model_code=model,size_code=size,color_name=color)
        payloads['OPEN_PO']=dict(po_number=tag,model_code=model,status='DRAFT',current_stage='CUTTING')
    payload=payloads[entity];payload[field]=value
    oracle.stage(cur,batch,entity,1,payload)
    preview=oracle.validate(cur,batch)
    assert preview['counts']==((1,1,0) if valid else (1,0,1)),preview
    if not valid:
        assert any(field in error for error in preview['rows'][0][2]),preview
        return dict(status='PASS',entity=entity,field=field,value=value,preview=preview)
    function='erp.apply_migration_open_pos' if entity=='OPEN_PO' else 'erp.apply_migration_master_rows'
    assert oracle.run_owner(cur,'select '+function+'(%s)',(batch,)).fetchone()[0]==1
    actors.admin(cur)
    ident=cur.execute('select posted_entity_id from erp.migration_staging_rows where batch_id=%s',(batch,)).fetchone()[0]
    if entity=='CUSTOMER':
        actual=cur.execute('select is_active from erp.customers where id=%s',(ident,)).fetchone()[0]
        expected=False if value in (False,'no','0') else True
        assert actual==expected,(value,actual,expected)
    elif entity=='SUPPLIER':
        actual=cur.execute('select supplier_type from erp.suppliers where id=%s',(ident,)).fetchone()[0]
        assert actual=='ACCESSORY',actual
    else:actual=str(ident)
    return dict(status='PASS',entity=entity,field=field,value=value,preview=preview,actual=actual)


def mixed_repair(cur,day):
    batch,material=oracle.gaps.raw_batch(cur,day,'VALID')
    oracle.stage(cur,batch,'OPENING_BALANCE_ITEM',2,dict(balance_type='BS',qty='1.5'))
    preview=oracle.validate(cur,batch);assert preview['counts']==(2,1,1),preview
    refusal=oracle.attempt(cur,lambda:oracle.prepare(cur,batch));assert not refusal['ok']
    oracle.stage(cur,batch,'OPENING_BALANCE_ITEM',2,dict(balance_type='BS',qty='2'))
    assert oracle.validate(cur,batch)['counts']==(2,2,0)
    ident=oracle.prepare(cur,batch);oracle.post(cur,ident)
    state=oracle.opening_state(cur,ident)
    actual=cur.execute('select sum(qty_signed),sum(qty_signed*unit_cost_snapshot) from erp.material_stock_movements where material_id=%s',(material,)).fetchone()
    assert actual==(10,Decimal('12.5')) and state['bs']==[(2,)],(actual,state)
    assert dict(state['journal'])['MATERIAL_INVENTORY']==Decimal('12.5'),state
    return dict(status='PASS',invalid_preview=preview,prepare_refused=refusal,actual=actual,state=state)


def direct_nonfinite(cur,day,balance,field):
    actors.admin(cur)
    if balance=='MATERIAL':
        batch,_=oracle.gaps.raw_batch(cur,day,'VALID')
        assert oracle.validate(cur,batch)['counts']==(1,1,0)
        ident=oracle.prepare(cur,batch)
    else:
        ident=oracle.run_owner(cur,"insert into erp.opening_balance_headers(opening_number,opening_date,status) values(%s,%s,'DRAFT') returning id",('ALV-'+uuid.uuid4().hex,day-timedelta(days=1))).fetchone()[0]
        oracle.run_owner(cur,'insert into erp.opening_balance_items(opening_id,balance_type,qty,amount,unit_cost_snapshot) values(%s,%s,2,3.75,1.25)',(ident,balance))
    assert field in ('qty','amount','unit_cost_snapshot')
    oracle.run_owner(cur,'update erp.opening_balance_items set '+field+"='NaN'::numeric where opening_id=%s",(ident,))
    refused=oracle.attempt(cur,lambda:oracle.post(cur,ident))
    assert not refused['ok'] and refused['error']['message']=='AL_OPENING_VALUES_MUST_BE_FINITE',refused
    return dict(status='PASS',balance=balance,field=field,refusal=refused)


def run(original_mode=False):
    if original_mode:
        import cp6_v2620ak_runtime as tested_runtime
    else:
        tested_runtime=runtime
    head,tree=tested_runtime.verify_audit_source()
    path=runtime.ROOT/'scripts/cp6_final_ak_independent.py'
    original=subprocess.check_output(['git','-C',str(runtime.ROOT),'show','8435f15c3f1a3fe07a9b0eb55ceb043f6c865c60:scripts/cp6_final_ak_independent.py'])
    assert path.read_bytes()==original,'Original independent oracle was changed'
    # Reuse the case declarations themselves, without the old runtime runner.
    module=ast.parse(original)
    run_node=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='run')
    with_node=next(n for n in run_node.body if isinstance(n,ast.With))
    start=next(i for i,n in enumerate(with_node.body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='specs')
    end=next(i for i,n in enumerate(with_node.body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Subscript) and ast.unparse(n.targets[0])=="report['planned_case_ids']")
    declarations=ast.Module(body=with_node.body[start:end],type_ignores=[])
    report=dict(status='INCOMPLETE',head=head,tree=tree,production_go=False,independent_acceptance=False,
        runtime_generation='AK' if original_mode else 'AL',original_oracle_head='8435f15c3f1a3fe07a9b0eb55ceb043f6c865c60',original_oracle_sha256=hashlib.sha256(original).hexdigest(),cases={})
    ROOT.mkdir(parents=True,exist_ok=True)
    def save():(ROOT/('ORIGINAL_VALUES.json' if original_mode else 'VALUES.json')).write_text(json.dumps(report,indent=2,default=str)+'\n')
    with psycopg.connect(setup.ADMIN) as conn,conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
        assert len(tested_runtime.verified_successor(cur))==690
        initial,catalog=actors.boundary(cur),function_catalog(cur)
        usage=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        report['temporary_schema_usage_grant']=not usage
        if not usage:cur.execute('grant usage on schema erp to authenticated')
        actors.actors.claims(cur,dict(sub=base.OPERATOR_AUTH,role='authenticated'));base.load_fixture_foundation(cur);actors.admin(cur)
        day=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        namespace=dict(vars(oracle),day=day)
        exec(compile(declarations,str(path),'exec'),namespace)
        specs=namespace['specs'];assert len(specs)==27
        report['original_case_ids']=[n for n,_ in specs]
        if not original_mode:
            for entity in ('BRAND','SIZE','MODEL','PRODUCT','CUSTOMER','SUPPLIER','CONTRACTOR','ACCESSORY_CATEGORY','MATERIAL'):
                specs.append(('BOOL:'+entity,lambda c,e=entity:extra_typed(c,day,e,'is_active','invalid-value',False)))
            specs += [('PRODUCT_PORTAL_BOOL',lambda c:extra_typed(c,day,'PRODUCT','is_portal_visible','invalid-value',False))]
            for field,value in [('target_qty_pcs','1.5'),('target_qty_pcs','-1'),('target_dozens','-1'),('physical_start_at','not-a-date')]:
                specs.append(('OPEN_PO:'+field+':'+value,lambda c,f=field,v=value:extra_typed(c,day,'OPEN_PO',f,v,False)))
            specs.append(('SIZE_WIDTH',lambda c:extra_typed(c,day,'SIZE','size_code','S'*21,False)))
            for value in (False,True,'',None,'no','0'):
                specs.append(('VALID_BOOL:'+str(value),lambda c,v=value:extra_typed(c,day,'CUSTOMER','is_active',v,True)))
            specs.append(('VALID_ENUM_NORMALIZATION',lambda c:extra_typed(c,day,'SUPPLIER','supplier_type','accessory',True)))
            specs.append(('MIXED_REPAIR',lambda c:mixed_repair(c,day)))
            for balance in ('MATERIAL','WIP','BS'):
                for field in ('qty','amount','unit_cost_snapshot'):
                    specs.append(('DIRECT_NAN:'+balance+':'+field,lambda c,b=balance,f=field:direct_nonfinite(c,day,b,f)))
            for direct in (False,True):
                for payload in ({},{'qty':'2'},{'qty':'2','unit_cost':'-1'}):
                    specs.append(('WIP_EXPLICIT:'+str(direct)+':'+json.dumps(payload,sort_keys=True),lambda c,p=payload,d=direct:oracle.simple_balance(c,day,'WIP',p,True,d)))
        report['planned_case_ids']=[n for n,_ in specs];assert len(set(report['planned_case_ids']))==len(specs);save()
        for name,fn in specs:
            actors.admin(cur);before=actors.boundary(cur);cur.execute('savepoint al_value_case')
            try:row=fn(cur)
            except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
            finally:cur.execute('rollback to savepoint al_value_case');actors.admin(cur);cur.execute('release savepoint al_value_case')
            row['boundary_restored']=actors.boundary(cur)==before
            if not row['boundary_restored']:row['status']='INCOMPLETE'
            report['cases'][name]=row;save();print(json.dumps(dict(case=name,status=row['status'],error=row.get('error'))),flush=True)
        report['catalog_unchanged']=function_catalog(cur)==catalog
        conn.rollback();cur.execute("set local timezone='Asia/Jakarta'")
        report['boundary_restored']=actors.boundary(cur)==initial
        report['schema_usage_restored']=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==usage
        report['auth_users'],report['app_users']=cur.execute('select (select count(*) from auth.users),(select count(*) from erp.app_users)').fetchone();conn.rollback()
    report['counts']={s:sum(r['status']==s for r in report['cases'].values()) for s in ('PASS','BUG_PROVEN','GAP_PROVEN','INCOMPLETE')}
    clean=all(report[k] for k in ('catalog_unchanged','boundary_restored','schema_usage_restored')) and report['auth_users']==report['app_users']==0
    if original_mode:
        if clean and report['counts']==dict(PASS=11,BUG_PROVEN=12,GAP_PROVEN=4,INCOMPLETE=0):report['status']='PREDECESSOR_PROBES_COMPLETE'
    elif clean and len(report['cases'])==report['counts']['PASS']:report['status']='WRITER_PASS'
    save();return report


if __name__=='__main__':
    assert os.environ['PGURL']==setup.URL and os.environ['CP6_AI_INDEPENDENT_CONFIRM']=='postgres'
    parser=argparse.ArgumentParser();parser.add_argument('--original',action='store_true');args=parser.parse_args()
    r=run(args.original);print(json.dumps({k:v for k,v in r.items() if k not in ('cases','planned_case_ids','original_case_ids')}));raise SystemExit(0 if r['status'] in ('WRITER_PASS','PREDECESSOR_PROBES_COMPLETE') else 1)
