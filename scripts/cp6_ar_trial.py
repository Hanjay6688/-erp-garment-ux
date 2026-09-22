"""Native AR: two routes, two commit orders, exact economics and lock evidence."""
from pathlib import Path
from datetime import timedelta
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import json,os,time,traceback,uuid,subprocess
import psycopg
import cp6_ao_ap_installed as api
import cp6_ao_ap_maintenance as maintenance
import cp6_ao_ap_runtime as prior
import cp6_aq_runtime as aq
import cp6_ar_runtime as ar
import cp6_opening_overlap_probe as counterexample
from cp6_ao_ap_inventory import data,platform

OUT=Path('cp6-proof/ar')
PG='postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback'
ADMIN='postgresql://supabase_admin:postgres@127.0.0.1:54322/cp6_rollback'
CONTROL='postgresql://postgres:postgres@127.0.0.1:54322/postgres'
KINDS=['CUSTOMER_RECEIVABLE','SUPPLIER_PAYABLE','VENDOR_PAYABLE','CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE','CASH_BANK','MATERIAL','FINISHED_GOODS','WIP','BS']

def native(cur):
    api.admin(cur)
    api.actors.actors.claims(cur,dict(sub=api.base.OPERATOR_AUTH,role='authenticated'))

def fixture(cur,today,kind):
    tag='OV'+uuid.uuid4().hex[:12]
    batch=api.call(cur,'CREATE',dict(batch_code=tag,cutover_date=str(today-timedelta(days=1))))['batch_id']
    masters={}
    row=dict(balance_type=kind,control_key='CHECK')
    control=dict(balance_type=kind,control_key='CHECK',amount='17.25')
    mapping={
      'CUSTOMER_RECEIVABLE':('CUSTOMER','customer_code','customer_name',{}),
      'SUPPLIER_PAYABLE':('SUPPLIER','supplier_code','supplier_name',{'supplier_type':'MATERIAL'}),
      'VENDOR_PAYABLE':('LAUNDRY_VENDOR','vendor_code','vendor_name',{}),
      'CONTRACTOR_RECEIVABLE':('CONTRACTOR','contractor_code','contractor_name',{'contractor_type':'MANDOR'}),
      'CONTRACTOR_PAYABLE':('CONTRACTOR','contractor_code','contractor_name',{'contractor_type':'MANDOR'}),
    }
    if kind in mapping:
        entity,key,label,extra=mapping[kind]
        masters[entity]=[dict({key:tag,label:'Synthetic overlap party'},**extra)]
        row.update({key:tag,'amount':'17.25'})
    elif kind=='CASH_BANK':
        masters['CHART_ACCOUNT']=[dict(account_code=tag,account_name='Synthetic overlap cash',account_type='ASSET',report_group='CURRENT_ASSETS',normal_balance='DEBIT')]
        masters['CASH_ACCOUNT']=[dict(cash_account_code=tag,cash_account_name='Synthetic overlap cash',coa_account_code=tag,account_kind='BANK')]
        row.update(cash_account_code=tag,amount='17.25')
    elif kind=='MATERIAL':
        masters['LOCATION']=[dict(location_code=tag,location_name='Synthetic overlap raw',location_type='RAW_MATERIAL_WAREHOUSE')]
        masters['MATERIAL']=[dict(material_sku=tag,material_name='Synthetic overlap accessory',material_type='OTHER',unit_code='PCS')]
        row.update(material_sku=tag,location_code=tag,qty='7',unit_cost='2.25')
        control.update(qty='7',amount='15.75')
    elif kind in ('FINISHED_GOODS','BS'):
        masters['MODEL']=[dict(model_code=tag,model_name='Synthetic overlap model')]
        masters['BRAND']=[dict(brand_code=tag,brand_name='Synthetic overlap brand '+tag)]
        masters['SIZE']=[dict(size_code=tag)]
        masters['PRODUCT']=[dict(sku=tag,product_name='Synthetic overlap product',model_code=tag,brand_code=tag,size_code=tag,color_name='BLUE')]
        masters['LOCATION']=[dict(location_code=tag,location_name='Synthetic overlap FG',location_type='FG_WAREHOUSE')]
        row.update(product_sku=tag,location_code=tag,qty='7')
        control.update(qty='7',amount='15.75' if kind=='FINISHED_GOODS' else '0')
        if kind=='FINISHED_GOODS':row['unit_cost']='2.25'
    elif kind=='WIP':
        masters['MODEL']=[dict(model_code=tag,model_name='Synthetic overlap WIP')]
        row.update(model_code=tag,stage='SEWING',amount='17.25')
    else:raise AssertionError(kind)
    for entity,rows in masters.items():api.upload(cur,batch,entity,rows)
    api.upload(cur,batch,'OPENING_BALANCE_ITEM',[row]);api.upload(cur,batch,'OPENING_CONTROL',[control])
    result=api.invoke(cur,'VALIDATE',batch)
    assert result['error_rows']==0,api.read(cur,batch)
    native(cur)
    cur.execute('select erp.apply_migration_master_rows(%s)',(batch,))
    ident=cur.execute('select erp.prepare_migration_opening_balance(%s,null)',(batch,)).fetchone()[0]
    legacy=duplicate_draft(cur,ident)
    return dict(batch=batch,imported=ident,legacy=legacy,kind=kind,tag=tag)

def duplicate_draft(cur,opening):
    native(cur)
    ident=cur.execute("insert into erp.opening_balance_headers(opening_number,opening_date,status,created_by,notes) select %s,opening_date,'DRAFT',erp.current_app_user_id(),'Synthetic direct legacy overlap' from erp.opening_balance_headers where id=%s returning id",('OV-LEGACY-'+uuid.uuid4().hex,opening)).fetchone()[0]
    cur.execute('''insert into erp.opening_balance_items(opening_id,balance_type,material_id,roll_id,product_id,model_id,contractor_id,customer_id,location_id,supplier_id,vendor_id,cash_account_id,stage,qty,amount,unit_cost_snapshot,quality_grade,notes,hpp_input_method,hpp_percent_of_price)
      select %s,balance_type,material_id,roll_id,product_id,model_id,contractor_id,customer_id,location_id,supplier_id,vendor_id,cash_account_id,stage,qty,amount,unit_cost_snapshot,quality_grade,'Synthetic direct legacy overlap',hpp_input_method,hpp_percent_of_price
      from erp.opening_balance_items where opening_id=%s''',(ident,opening))
    return ident

def post(cur,f,route):
    if route=='imported':return api.invoke(cur,'FINALIZE',f['batch'])
    native(cur);cur.execute('select erp.post_opening_balance(%s)',(f['legacy'],))
    return dict(status='POSTED')

def economic_state(cur,f):
    api.admin(cur)
    ids=[f['imported'],f['legacy']]
    items=[r[0] for r in cur.execute('select id from erp.opening_balance_items where opening_id=any(%s)',(ids,))]
    return dict(
      headers=cur.execute('select id,status from erp.opening_balance_headers where id=any(%s) order by id',(ids,)).fetchall(),
      subledger=cur.execute('select opening_item_id,original_amount,settled_amount from erp.opening_subledger_balances where opening_item_id=any(%s) order by opening_item_id',(items,)).fetchall(),
      material=cur.execute("select source_id,qty_signed,unit_cost_snapshot from erp.material_stock_movements where source_type='OPENING_BALANCE_ITEM' and source_id=any(%s) order by source_id",(items,)).fetchall(),
      fg=cur.execute("select source_id,qty_signed,unit_hpp_snapshot from erp.fg_stock_movements where source_type='OPENING_BALANCE_ITEM' and source_id=any(%s) order by source_id",(items,)).fetchall(),
      wip=cur.execute("select source_id,qty_pcs from erp.wip_stage_events where source_type='INITIAL_IMPORT_WIP_OPENING' and source_id=any(%s) order by source_id",(items,)).fetchall(),
      bs=cur.execute("select b.bs_number,b.qty_pcs from erp.bs_cases b join erp.opening_balance_headers h on b.bs_number like 'OBS-'||h.opening_number||'-%%' where h.id=any(%s) order by b.bs_number",(ids,)).fetchall(),
      journals=cur.execute("select j.source_id,j.status,j.economic_date,l.account_id,l.debit,l.credit from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where j.source_type='OPENING_BALANCE' and j.source_id=any(%s) order by j.source_id,l.account_id",(ids,)).fetchall())

def exactly_once(cur,f,winner):
    s=economic_state(cur,f);kind=f['kind']
    assert dict(s['headers'])=={f[winner]:'POSTED',f['legacy' if winner=='imported' else 'imported']:'DRAFT'},s
    amount=Decimal('15.75' if kind in ('MATERIAL','FINISHED_GOODS') else '17.25')
    if kind=='BS':assert not s['journals'] and len(s['bs'])==1 and s['bs'][0][1]==7,s
    else:
        assert len(s['journals'])==2 and {j[0] for j in s['journals']}=={f[winner]},s
        assert all(j[1]=='POSTED' for j in s['journals']),s
        assert sum(j[4] for j in s['journals'])==sum(j[5] for j in s['journals'])==amount,s
    if kind in KINDS[:5]:
        assert len(s['subledger'])==1 and s['subledger'][0][1:]==(Decimal('17.25'),Decimal('0')),s
    else:assert not s['subledger'],s
    for category,expected_kind in [('material','MATERIAL'),('fg','FINISHED_GOODS')]:
        if kind==expected_kind:
            assert len(s[category])==1 and s[category][0][1:]==(7,Decimal('2.25')),s
        else:assert not s[category],s
    if kind!='BS':assert not s['bs'],s
    # These ten counterexamples use value-only WIP; physical WIP/BS follows in
    # inherited production-origin cases, where events and HPP are asserted.
    assert not s['wip'],s
    return s

def refused(cur,operation,f):
    before=data(cur);economics=economic_state(cur,f)
    try:
        with cur.connection.transaction():
            result=operation()
            assert result['status']=='DRAFT' and result['error_rows']>0,result
            assert economic_state(cur,f)==economics,'VALIDATION_REFUSAL_CHANGED_ECONOMICS'
            # Preserve the whole test boundary after proving the normal API
            # validation response made no accounting/stock/subledger changes.
            raise ValueError('EXPECTED_VALIDATION_REFUSAL')
    except psycopg.Error as exc:
        assert exc.sqlstate=='P0001' and 'AR_OPENING_ROUTE_OVERLAP' in str(exc),str(exc)
        reason='AR_OPENING_ROUTE_OVERLAP'
    except ValueError as exc:
        assert str(exc)=='EXPECTED_VALIDATION_REFUSAL';reason='VALIDATION_ERRORS'
    api.admin(cur);assert data(cur)==before,'FAILED_POST_LEFT_PARTIAL_DATA'
    return reason

def sequential(cur,today,kind,winner):
    f=fixture(cur,today,kind);loser='legacy' if winner=='imported' else 'imported'
    assert post(cur,f,winner)['status']=='POSTED'
    reason=refused(cur,lambda:post(cur,f,loser),f)
    state=exactly_once(cur,f,winner)
    return dict(status='PASS',winner=winner,loser=loser,refusal=reason,all_erp_data_unchanged_on_refusal=True,economics=state)

def original_probe(cur,today,kind):
    opening=counterexample.imported(cur,today,kind)
    before=data(cur)
    try:
        with cur.connection.transaction():counterexample.duplicate_via_legacy(cur,opening)
    except psycopg.Error as exc:assert 'AR_OPENING_ROUTE_OVERLAP' in str(exc),str(exc)
    else:raise AssertionError('ORIGINAL_COUNTEREXAMPLE_STILL_REPRODUCES')
    api.admin(cur);assert data(cur)==before
    assert cur.execute('select status from erp.opening_balance_headers where id=%s',(opening,)).fetchone()==('POSTED',)
    return dict(status='PASS',original_probe_helpers_unchanged=True,public_finalize_without_native_prepare=True,duplicate_refused_all_erp_data_unchanged=True)

def nonoverlap(cur,today,kind):
    f=fixture(cur,today,kind)
    if kind in ('MATERIAL','FINISHED_GOODS'):
        native(cur)
        location=cur.execute("insert into erp.locations(location_code,location_name,location_type) select %s,'Distinct opening location',location_type from erp.locations where location_code=%s returning id",(f['tag']+'N',f['tag'])).fetchone()[0]
        cur.execute('update erp.opening_balance_items set location_id=%s where opening_id=%s',(location,f['legacy']))
    elif kind=='WIP':
        native(cur);cur.execute("update erp.opening_balance_items set stage='LAUNDRY' where opening_id=%s",(f['legacy'],))
    elif kind=='BS':
        other=fixture(cur,today,kind)
        native(cur);cur.execute('update erp.opening_balance_items set product_id=(select product_id from erp.opening_balance_items where opening_id=%s) where opening_id=%s',(other['legacy'],f['legacy']))
    else:
        other=fixture(cur,today,kind)
        fields={**{k:'contractor_id' for k in ('CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE')},'CUSTOMER_RECEIVABLE':'customer_id','SUPPLIER_PAYABLE':'supplier_id','VENDOR_PAYABLE':'vendor_id','CASH_BANK':'cash_account_id'}
        field=fields[kind];native(cur)
        cur.execute(f'update erp.opening_balance_items set {field}=(select {field} from erp.opening_balance_items where opening_id=%s) where opening_id=%s',(other['legacy'],f['legacy']))
    assert post(cur,f,'imported')['status']=='POSTED'
    assert post(cur,f,'legacy')['status']=='POSTED'
    assert [x[1] for x in economic_state(cur,f)['headers']]==['POSTED','POSTED']
    return dict(status='PASS',distinct_dimension_admitted=True)

def rpc_guards(cur,today):
    f=fixture(cur,today,'MATERIAL');payload=dict(batch_id=f['batch'],expected_revision=api.read(cur,f['batch'])['batch']['revision']);key=uuid.uuid4()
    def denied(operation,fragment=None):
        boundary=data(cur)
        try:
            with cur.connection.transaction():operation()
        except psycopg.Error as exc:
            message=str(exc)
            if fragment:assert fragment.lower() in message.lower(),message
        else:raise AssertionError('EXPECTED_RPC_REFUSAL')
        api.admin(cur);assert data(cur)==boundary
        return message
    stale=denied(lambda:api.call(cur,'FINALIZE',dict(payload,expected_revision='obsolete')),'STALE_VERSION')
    posted=api.call(cur,'FINALIZE',payload,key);assert posted['status']=='POSTED'
    boundary=data(cur);assert api.call(cur,'FINALIZE',payload,key)==posted and data(cur)==boundary
    changed=denied(lambda:api.call(cur,'FINALIZE',dict(payload,notes='different payload'),key))
    assert any(s in changed.lower() for s in ('idempot','request','permintaan')),changed
    # Keep the last-owner protection active while revoking the posting actor.
    backup=uuid.uuid4();native(cur)
    cur.execute("insert into auth.users(id,aud,role,email) values(%s,'authenticated','authenticated',%s)",(backup,'ar-backup-'+backup.hex+'@example.test'))
    cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active) select gen_random_uuid(),%s,'AR backup owner','OWNER',id,true from erp.app_roles where role_code='OWNER'",(backup,))
    cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(api.base.OPERATOR_AUTH,))
    revoked=denied(lambda:api.call(cur,'FINALIZE',payload,key))
    return dict(status='PASS',stale_refused=stale,replay_exact=True,changed_payload_refused=changed,revoked_owner_refused=revoked,all_refusals_atomic=True)

def isolation_guard(today):
    with psycopg.connect(ADMIN) as c,c.cursor() as cur:f=fixture(cur,today,'MATERIAL');before=data(cur)
    with psycopg.connect(ADMIN) as c:
        c.execute('set transaction isolation level repeatable read')
        try:
            with c.transaction():
                native(c.cursor());c.execute('select erp.post_opening_balance(%s)',(f['legacy'],))
        except psycopg.Error as exc:assert 'AR_OPENING_REQUIRES_READ_COMMITTED' in str(exc)
        else:raise AssertionError('STALE_SNAPSHOT_ADMITTED')
        c.rollback()
    with psycopg.connect(ADMIN) as c,c.cursor() as cur:assert data(cur)==before
    return dict(status='PASS',repeatable_read_refused_atomically=True)

def concurrency(today,kind,winner,commit=True,same_header=False):
    with psycopg.connect(ADMIN) as c,c.cursor() as cur:f=fixture(cur,today,kind)
    loser='legacy' if winner=='imported' else 'imported'
    if same_header:f['legacy']=f['imported']
    with psycopg.connect(ADMIN,application_name='ar-first') as first,psycopg.connect(ADMIN,application_name='ar-second') as second:
        for conn in (first,second):
            conn.execute("set statement_timeout='18s';set lock_timeout='15s'");conn.commit()
        # Freeze the second request before starting the competing operation.
        with second.cursor() as cur:
            payload=dict(batch_id=f['batch'],expected_revision=api.read(cur,f['batch'])['batch']['revision'])
        second.commit()
        result=post(first.cursor(),f,winner);assert result['status']=='POSTED'
        def worker():
            try:
                with second.cursor() as cur:
                    r=api.call(cur,'FINALIZE',payload) if loser=='imported' else post(cur,f,loser)
                second.commit();return dict(result=r,success=r['status']=='POSTED')
            except psycopg.Error as exc:
                second.rollback();return dict(success=False,sqlstate=exc.sqlstate,error=str(exc))
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(worker);blocked=None
            try:
                with psycopg.connect(ADMIN,autocommit=True) as observer:
                    deadline=time.monotonic()+7
                    while time.monotonic()<deadline and not future.done():
                        row=observer.execute('select pg_blocking_pids(pid),wait_event_type,wait_event from pg_stat_activity where pid=%s',(second.info.backend_pid,)).fetchone()
                        if row and first.info.backend_pid in row[0]:blocked=row;break
                        time.sleep(.03)
                assert blocked and blocked[1:] == ('Lock','advisory'),('LOCK_NOT_OBSERVED',blocked)
            finally:
                first.commit() if commit else first.rollback()
            outcome=future.result(timeout=20)
        assert outcome['success']==(not commit),outcome
        if not outcome['success']:
            assert outcome.get('sqlstate') in (None,'P0001'),outcome
            if outcome.get('sqlstate'):
                allowed=['AR_OPENING_ROUTE_OVERLAP'] if not same_header else ['STALE_VERSION','sudah disahkan','must be DRAFT','AK_OPENING_REQUIRES_CURRENT_VALIDATED_BATCH']
                assert any(x in outcome['error'] for x in allowed),outcome
            else:assert outcome['result']['status']=='DRAFT' and outcome['result']['error_rows']>0,outcome
        with psycopg.connect(ADMIN) as observer,observer.cursor() as cur:
            if same_header:
                # Both entry points target one document. Count side effects once.
                assert cur.execute("select count(*) from erp.material_stock_movements where source_id in(select id from erp.opening_balance_items where opening_id=%s)",(f['imported'],)).fetchone()==(1,)
                state=dict(same_header_once=True)
            else:state=exactly_once(cur,f,winner if commit else loser)
        return dict(status='PASS',winner_committed=commit,winner_route=winner,blocking_observed=True,wait_event=blocked[2],second=outcome,economics=state)

def inherited_cases(cur,today):
    a=SimpleNamespace(**vars(api))
    cases=[('LATEST_DRAFT_TOTAL_REPLAY',lambda:api.latest_draft(cur,today))]
    for module in (api.accessories,api.receipts,api.production_origins,api.pocket,api.periods):cases+=module.cases(a,cur,today)
    return cases

def main():
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback'
    assert os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    OUT.mkdir(parents=True,exist_ok=True)
    report=dict(status='INCOMPLETE',cases={},production_go=False,independent_acceptance=False)
    def save():(OUT/'AR_TRIAL.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    with psycopg.connect(CONTROL) as c,c.cursor() as cur:prior.verified(cur,'AN');primary=data(cur)
    try:
        for family in ('AO','AP'):
            maintenance.install(family=family,target_pgurl=PG,maintenance_pgurl=os.environ['CP6_ADMISSION_CONTROL_PGURL'],report_path=OUT/(family+'_INSTALL.json'))
        with psycopg.connect(ADMIN) as c,c.cursor() as cur:api.seed(cur)
        report['aq_install']=aq.change('install',PG,os.environ['CP6_ADMISSION_CONTROL_PGURL'])
        ar.qualify(PG,ADMIN,OUT)
        with psycopg.connect(ADMIN) as c,c.cursor() as cur:
            report['runtime']=ar.verified(cur);baseline=data(cur)
            today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
            cases=[]
            for kind in KINDS:
                cases.append((kind+'_ORIGINAL_PROBE',lambda k=kind:original_probe(cur,today,k)))
                for winner in ('imported','legacy'):
                    cases.append((kind+'_'+winner.upper()+'_FIRST',lambda k=kind,w=winner:sequential(cur,today,k,w)))
                cases.append((kind+'_NONOVERLAP',lambda k=kind:nonoverlap(cur,today,k)))
            cases.append(('RPC_REPLAY_STALE_PAYLOAD_REVOKED',lambda:rpc_guards(cur,today)))
            cases+=inherited_cases(cur,today)
            for name,operation in cases:
                cur.execute('savepoint ar_case')
                try:result=operation()
                except Exception as exc:result=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
                finally:cur.execute('rollback to savepoint ar_case');api.admin(cur);cur.execute('release savepoint ar_case')
                assert data(cur)==baseline,'AR_CASE_BOUNDARY_NOT_RESTORED'
                result['all_erp_tables_restored']=True;report['cases'][name]=result;save()
                print(json.dumps(dict(case=name,status=result['status'],error=result.get('error'))),flush=True)
            ar.verified(cur);c.rollback()
        for kind in KINDS:
            for winner in ('imported','legacy'):
                name='CONCURRENT_'+kind+'_'+winner.upper()+'_FIRST'
                try:result=concurrency(today,kind,winner)
                except Exception as exc:result=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
                report['cases'][name]=result;save();print(json.dumps(dict(case=name,status=result['status'],error=result.get('error'))),flush=True)
        for winner in ('imported','legacy'):
            for same in (False,True):
                name=('SAME_HEADER_' if same else 'WINNER_ABORT_')+winner.upper()
                try:result=concurrency(today,'MATERIAL',winner,commit=same,same_header=same)
                except Exception as exc:result=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
                report['cases'][name]=result;save()
        report['cases']['STALE_SNAPSHOT_ISOLATION']=isolation_guard(today);save()
        ar.refuse_post_use(PG,ADMIN,OUT)
        with psycopg.connect(ADMIN) as c,c.cursor() as cur:ar.verified(cur)
        report['status']='WRITER_PASS' if all(x['status']=='PASS' for x in report['cases'].values()) else 'INCOMPLETE'
    except Exception as exc:report.update(error=str(exc),traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(CONTROL) as c,c.cursor() as cur:
            prior.verified(cur,'AN');report['primary_unchanged']=data(cur)==primary
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        save()
    assert report['primary_unchanged'] and report['clone_remaining']==0
    assert report['status']=='WRITER_PASS',report.get('error','AR_CASE_FAILURE')

if __name__=='__main__':main()
