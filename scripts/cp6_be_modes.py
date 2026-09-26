"""Writer BE scenarios on the disposable real-Auth runtime; not independent acceptance.

Conversion races: a committed first writer invalidates the second source revision;
an aborted first writer leaves all ten pieces available. Same key replays one fact.
First-known redye price is set once; invoice capacity belongs to the actual service.
Historical period allocation is serialized by the existing try-lock, then rechecked.
"""
import json,uuid
import cp6_be_probe as be
import cp6_bd_modes as bd_modes
b=be.bdp

def read(tools,fn):
    with tools.connect() as conn,conn.cursor() as cur:
        result=fn(cur);conn.rollback();return result

def conversion_race(tools,today,commit,replay=False):
    with tools.connect() as conn,conn.cursor() as cur:
        f=be.fixture(cur,today);conn.commit()
    ka=str(uuid.uuid4());kb=ka if replay else str(uuid.uuid4())
    a=lambda cur:be.be(cur,'POST',f['payload'],ka)
    z=lambda cur:be.be(cur,'POST',f['payload'],kb)
    held,contention,outcome=tools.two_sessions(a,z,commit)
    state=read(tools,lambda cur:dict(source_qty=be.qty(cur,f['lot']),count=be.one(cur,"select count(*) from erp.be_conversion_sources_v1 s join erp.product_conversions c on c.id=s.conversion_id where s.source_lot_id=%s and c.status='POSTED'",f['lot'])))
    blocked=contention.get('kind')=='BLOCKED' and contention.get('holder_blocks_worker') is True
    second=outcome.get('ok') is True if replay or not commit else (not outcome.get('ok') and 'STALE_VERSION' in str(outcome.get('message')))
    return b.verdict(dict(contended=blocked,second=second,once=state==dict(source_qty=4,count=1)),first_committed=commit,same_key=replay,contention=contention,second=outcome,state=state)

def redye_price_race(tools,today,commit):
    with tools.connect() as conn,conn.cursor() as cur:
        f=be.redye_fixture(cur,today,False);conn.commit()
    def set_price(rate):return lambda cur:be.be(cur,'SET_REDYE_PRICE',dict(service_id=f['redye'],rate=rate,reason='BE first price race'))
    held,contention,outcome=tools.two_sessions(set_price('50.00'),set_price('60.00'),commit)
    state=read(tools,lambda cur:dict(cost=be.one(cur,'select erp.be_redye_cost_v1(%s)',f['redye']),events=be.one(cur,'select count(*) from erp.be_redye_price_events_v1 where service_id=%s',f['redye'])))
    return b.verdict(dict(contended=contention.get('kind')=='BLOCKED' and contention.get('holder_blocks_worker') is True,
      second=(not outcome.get('ok') and 'BE_PRICE_ALREADY_KNOWN' in str(outcome.get('message'))) if commit else outcome.get('ok') is True,
      once=state['events']==1 and state['cost']==(200 if commit else 240)),contention=contention,second=outcome,state=state)

def redye_invoice_race(tools,today,commit):
    with tools.connect() as conn,conn.cursor() as cur:
        f=be.redye_fixture(cur,today,True);b.invoice_policies(cur)
        payload=dict(vendor_id=f['vendor'],invoice_date=str(f['day']),header_total='240.00',lines=[dict(line_kind='BILL',rework_service_id=f['redye'],category='GOOD',qty=4,amount='240.00')])
        a=b.bd(cur,'SAVE_INVOICE_DRAFT',dict(payload,invoice_number='BE-RA-'+uuid.uuid4().hex))
        z=b.bd(cur,'SAVE_INVOICE_DRAFT',dict(payload,invoice_number='BE-RB-'+uuid.uuid4().hex));conn.commit()
    held,contention,outcome=tools.two_sessions(lambda cur:b.post_draft(cur,a),lambda cur:b.post_draft(cur,z),commit)
    cost=read(tools,lambda cur:be.one(cur,'select erp.be_redye_cost_v1(%s)',f['redye']))
    return b.verdict(dict(contended=contention.get('kind')=='BLOCKED' and contention.get('holder_blocks_worker') is True,
      second=(not outcome.get('ok') and 'BD_INVOICE_CAPACITY' in str(outcome.get('message'))) if commit else outcome.get('ok') is True,
      once=cost==240),contention=contention,second=outcome,cost=cost)

def races(tools,today):
    return [('BE_RACE:CONVERSION_FIRST_COMMITS',lambda:conversion_race(tools,today,True)),
      ('BE_RACE:CONVERSION_FIRST_ABORTS',lambda:conversion_race(tools,today,False)),
      ('BE_RACE:CONVERSION_IDENTICAL_REPLAY',lambda:conversion_race(tools,today,True,True)),
      ('BE_RACE:REDYE_PRICE_FIRST_COMMITS',lambda:redye_price_race(tools,today,True)),
      ('BE_RACE:REDYE_PRICE_FIRST_ABORTS',lambda:redye_price_race(tools,today,False)),
      ('BE_RACE:REDYE_INVOICE_FIRST_COMMITS',lambda:redye_invoice_race(tools,today,True)),
      ('BE_RACE:REDYE_INVOICE_FIRST_ABORTS',lambda:redye_invoice_race(tools,today,False))]

def http_cases(http,today):
    def conversion():
        with http.connect() as conn,conn.cursor() as cur:
            with bd_modes._fixture_usage(cur):f=be.fixture(cur,today)
            conn.commit()
        owner=http.login('OWNER','be-owner');qc=http.login('PRODUKSI_QC','be-qc');warehouse=http.login('GUDANG','be-warehouse')
        args=dict(p_action='POST',p_payload=f['payload'],p_client_request_id=str(uuid.uuid4()))
        anon=http.anon_rpc('erp_save_product_conversion_action_v1',args)
        denied=qc.rpc('erp_save_product_conversion_action_v1',args)
        warehouse_view=warehouse.rpc('erp_get_product_conversion_workspace_v1',dict(p_filters=dict(source_lot_id=f['lot'])))
        # A real Owner creates an explicitly read-only role in this disposable copy.
        # The default GUDANG role has no conversion.view; never assume it does.
        code='BE_READER_'+uuid.uuid4().hex[:12].upper()
        role=owner.rpc('erp_save_role_v1',dict(p_payload=dict(code=code,name='BE read-only conversion fixture',
          permission_keys=['warehouse.brand_conversion.view'],confirm_high_risk=False,change_reason='BE isolated HTTP permission matrix'),
          p_client_request_id=str(uuid.uuid4()),p_expected_version=None))
        assert role['status']==200,('BE_READER_SETUP',role)
        reader=http.login(code,'be-reader')
        view=reader.rpc('erp_get_product_conversion_workspace_v1',dict(p_filters=dict(source_lot_id=f['lot'])))
        preview=reader.rpc('erp_get_product_conversion_workspace_v1',dict(p_filters=dict(preview=f['payload'])))
        reader_write=reader.rpc('erp_save_product_conversion_action_v1',args)
        done=owner.rpc('erp_save_product_conversion_action_v1',args);again=owner.rpc('erp_save_product_conversion_action_v1',args)
        changed=owner.rpc('erp_save_product_conversion_action_v1',{**args,'p_payload':{**f['payload'],'qty_pcs':5}})
        with http.connect() as conn,conn.cursor() as cur:
            count=be.one(cur,'select count(*) from erp.be_conversion_sources_v1 where source_lot_id=%s',f['lot']);conn.rollback()
        return b.verdict(dict(anon=anon['status'] in (401,403),qc_refused=denied['status']>=400,
          warehouse_refused=warehouse_view['status']==403,reader_refused=reader_write['status']==403,
          reader_hidden=view['status']==200 and bool(view['body'].get('lots')) and all(x['unit_hpp'] is None for x in view['body']['lots']),
          preview_hidden=preview['status']==200 and preview['body']['preview']['cost']=={},
          owner=done['status']==200 and done['body'].get('status')=='POSTED',replay=again==done and count==1,changed_key_refused=changed['status']>=400),
          http=dict(anon=anon['status'],qc=denied['status'],warehouse=warehouse_view['status'],reader=view['status'],reader_write=reader_write['status'],owner=done['status'],changed_key=changed['status']),body=done['body'])
    def redye_price():
        with http.connect() as conn,conn.cursor() as cur:
            with bd_modes._fixture_usage(cur):f=be.redye_fixture(cur,today,False)
            conn.commit()
        owner=http.login('OWNER','be-price-owner');warehouse=http.login('GUDANG','be-price-warehouse')
        args=dict(p_action='SET_REDYE_PRICE',p_payload=dict(service_id=f['redye'],rate='50.00',reason='BE real HTTP first known price'),p_client_request_id=str(uuid.uuid4()))
        denied=warehouse.rpc('erp_save_product_conversion_action_v1',args);done=owner.rpc('erp_save_product_conversion_action_v1',args)
        again=owner.rpc('erp_save_product_conversion_action_v1',args)
        with http.connect() as conn,conn.cursor() as cur:
            cost=be.one(cur,'select erp.be_redye_cost_v1(%s)',f['redye']);conn.rollback()
        return b.verdict(dict(warehouse_refused=denied['status']>=400,owner=done['status']==200,replay=again==done,real_cost=cost==200),http=dict(warehouse=denied['status'],owner=done['status']),cost=cost)
    return [('BE_HTTP:CONVERSION_AUTH_REPLAY_HIDDEN_COST',conversion),('BE_HTTP:REDYE_PRICE_OWNER_REPLAY',redye_price)]
