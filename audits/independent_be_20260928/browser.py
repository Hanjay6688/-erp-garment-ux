"""Actual candidate BE browser, Auth and HTTP. Independent inputs and readback."""
import browser_support as b
import json,time,re,traceback
from decimal import Decimal as D
from pathlib import Path
import psycopg
C={};F={};X={}

def save():
    data={'candidate':b.PRODUCT,'scope':'Independent BE; real GoTrue/PostgREST; actual desktop and Chromium mobile UI','results':b.RESULTS,'production_go':False,'limits':['Disposable synthetic fixtures only','Chromium device emulation is not a physical iPhone or Safari test','No writer or peer BE cases or expected values reused']}
    for name,thing in [('results.json',data),('events.json',b.EVENTS),('http-events.json',b.HTTP_EVENTS)]:
        (b.OUT/name).write_text(b.redact(json.dumps(thing,indent=2,default=str))+'\n')
b.save=save

def click(label,who='owner',exact=True):return b.mobile_button(label,who,exact) if who.startswith('mobile') else b.button(label,who,exact)
def snap(label,who='owner'):return b.mobile_snap(label,who) if who.startswith('mobile') else b.snap(label,who)
def nav(section,label,who='owner'):
    b.ab('wait','--fn','!!document.querySelector("aside.sidebar")',who=who)
    if who.startswith('mobile'):
        b.ab('scroll','up','5000',who=who)
        opened=b.evaluate('document.querySelector("aside.sidebar")?.classList.contains("sidebar-open")',who)
        if not opened:click('Buka menu',who)
        b.ab('wait','--fn','Math.abs(document.querySelector("aside.sidebar").getBoundingClientRect().left)<1',who=who)
    visible=b.evaluate('Array.from(document.querySelectorAll("aside.sidebar button")).filter(x=>x.getClientRects().length).map(x=>x.textContent.trim())',who)
    if not any(label in x and '•' in x for x in visible):click(section,who,False)
    b.ab('wait','--fn','Array.from(document.querySelectorAll("aside.sidebar button")).some(x=>x.textContent.includes('+json.dumps(label)+'))',who=who)
    click('• '+label,who)
    if who.startswith('mobile'):b.ab('wait','--fn','!document.querySelector("aside.sidebar").classList.contains("sidebar-open")&&document.querySelector("aside.sidebar").getBoundingClientRect().right<=1',who=who)
    ready={'Ganti Merek':'Array.from(document.querySelectorAll("label")).some(l=>l.textContent.trim()==="Cari lot / SKU")','Kain kantong':'!!document.querySelector('+json.dumps('select[aria-label="Roll kain kantong"]')+')','Barang BS & Rework':'!!document.querySelector(".cbsr-search input")','Laundry':'!!document.querySelector(".clq-tabs")'}[label]
    b.ab('wait','--fn',ready,who=who)
def wrapped(label,value,who='owner'):
    code='Array.from(document.querySelectorAll("label")).find(l=>Array.from(l.childNodes).filter(x=>!["INPUT","TEXTAREA","SELECT"].includes(x.nodeName)).map(x=>x.textContent).join("").trim()==='+json.dumps(label)+')?.querySelector("select")'
    # Get accessible selects through their wrapping label, as actual user input.
    b.ab('wait','--fn','(()=>{const e='+code+';return !!e&&!e.disabled&&Array.from(e.options).some(o=>o.value==='+json.dumps(value)+');})()',who=who)
    selector=b.control_selector(code,who);b.ab('snapshot','-i',who=who);b.ab('select',selector,value,who=who)
    b.ab('wait','--fn','(()=>{const e='+code+';return !!e&&!e.disabled&&e.value==='+json.dumps(value)+';})()',who=who)
def qty(lot):return b.sql('select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where lot_id=%s',(lot,),one=True)
def wait_db(fn,expected,seconds=25):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        v=fn()
        if v==expected:return v
        time.sleep(.2)
    raise AssertionError({'expected':expected,'last':v})

def metadata():
    x=json.loads((b.ROOT/'audit-results/be-fixtures.json').read_text());C.update(x['identity']);F.update(x['sources'])
    if (b.ROOT/'audit-results/be-flow-fixtures.json').exists():X.update(json.loads((b.ROOT/'audit-results/be-flow-fixtures.json').read_text()))
    return {'source_keys':list(F),'redye_keys':list(X.get('redye',{})),'pocket_fixture':bool(X.get('pocket_history'))}
def workspace_http():
    r=b.rpc('erp_get_product_conversion_workspace_v1',{'p_filters':{'source_lot_id':F['UI']['lot']}});assert len(r['lots'])==1,r
    viewer=b.rpc('erp_get_product_conversion_workspace_v1',{'p_filters':{'source_lot_id':F['UI']['lot']}},'viewer');assert viewer['lots'][0]['unit_hpp'] is None,viewer
    payload={'source_lot_id':F['UI']['lot'],'target_product_id':C['target'],'location_id':C['fg'],'qty_pcs':3,'physical_at':'2026-09-16T08:00:00+07:00','reason':'Independent HTTP permission boundary','expected_version':r['lots'][0]['source_revision']}
    status,body=b.rpc('erp_save_product_conversion_action_v1',{'p_action':'POST','p_payload':payload,'p_client_request_id':b.uid()},'viewer',False);assert status in(400,403),(status,body);assert qty(F['UI']['lot'])==13
    return {'owner_source':r['lots'][0],'viewer_source':viewer['lots'][0],'viewer_post_status':status,'viewer_post_refusal':body}

def prepare_conversion(key,who='owner',q=3,reason=None):
    nav('Gudang','Ganti Merek',who);lot=F[key]['lot']
    number=b.sql('select lot_number from erp.fg_lots where id=%s',(lot,),one=True)
    b.fill('Cari lot / SKU',number,who);click('Cari lot',who);wrapped('Lot dan gudang',lot+':'+C['fg'],who)
    wrapped('SKU tujuan',C['target'],who);b.fill('Jumlah PCS',str(q),who);b.fill('Waktu fisik · WIB','2026-09-16T08:00',who);b.fill('Alasan',reason or 'Independent browser conversion '+key,who)
    before=qty(lot);click('Lihat pratinjau',who);b.wait_text('Catat konversi fisik',who);assert qty(lot)==before
    snap(who+'-'+key+'-preview',who);return {'lot':lot,'before':before,'reason':reason or 'Independent browser conversion '+key}
def conversion(key='UI',who='owner'):
    x=prepare_conversion(key,who);click('Catat konversi fisik',who);wait_db(lambda:qty(x['lot']),x['before']-3)
    rows=b.sql('select c.id::text,c.qty_pcs,a.destination_lot_id::text,c.to_product_id::text from erp.product_conversions c join erp.product_conversion_allocations a on a.conversion_id=c.id join erp.be_conversion_sources_v1 s on s.conversion_id=c.id where s.source_lot_id=%s order by c.created_at',(x['lot'],));assert len(rows)==1 and rows[0][1]==3 and rows[0][3]==C['target'],rows
    assert qty(rows[0][2])==3
    b.wait_text(x['reason'],who);snap(who+'-'+key+'-posted',who);click('Muat ulang',who);b.wait_text(x['reason'],who);snap(who+'-'+key+'-reloaded',who)
    return {'source_before':x['before'],'source_after':qty(x['lot']),'posted_lineage':rows,'target_quantity':qty(rows[0][2]),'reload_preserved':True}
def lost_response():
    x=prepare_conversion('UI',q=2,reason='Independent real committed conversion with lost response');b.FIX['drop_conversion_until_release']=True;click('Catat konversi fisik');wait_db(lambda:qty(x['lot']),x['before']-2)
    try:
        b.wait_text('Reconcile transaksi');snap('owner-lost-response-pending');b.ab('reload');nav('Gudang','Ganti Merek');b.wait_text('Reconcile transaksi');snap('owner-lost-response-persisted-after-reload');b.FIX['drop_conversion_until_release']=False
        first=[e for e in b.HTTP_EVENTS if e.get('deliberately_lost_after_real_database_response')][-1];req=first['payload']['p_client_request_id']
        click('Reconcile transaksi');b.wait_text(x['reason']);snap('owner-lost-response-reconciled');assert qty(x['lot'])==x['before']-2
        calls=[e for e in b.HTTP_EVENTS if (e.get('payload') or {}).get('p_client_request_id')==req];assert len(calls)>=2,calls;assert all(e['payload']==first['payload'] for e in calls),calls
        assert b.sql('select count(*) from erp.product_conversions where id=%s',(req,),one=True)==1
        return {'same_uuid':req,'http_attempts':len(calls),'one_posted_conversion':True,'source_quantity':qty(x['lot']),'actual_first_response':first['response']}
    finally:b.FIX['drop_conversion_until_release']=False

def pocket_stock(who='owner'):
    nav('Gudang','Kain kantong',who);b.select('Roll kain kantong',C['pocket_roll']+':'+C['rawloc'],who);b.select('Cara mencatat','USED',who)
    b.fill('Jumlah kain kantong','0.75',who);b.fill('Tanggal pengurangan','2026-09-25',who);reason='Independent browser pocket '+who;b.fill('Catatan kain kantong',reason,who)
    before=b.sql('select sum(qty_signed) from erp.material_stock_movements where roll_id=%s',(C['pocket_roll'],),one=True);snap(who+'-pocket-before',who);click('Sahkan pengurangan stok',who)
    wait_db(lambda:b.sql('select sum(qty_signed) from erp.material_stock_movements where roll_id=%s',(C['pocket_roll'],),one=True),before-D('.75'))
    b.wait_text(reason,who);snap(who+'-pocket-posted',who);click('Muat ulang',who);b.wait_text(reason,who);snap(who+'-pocket-reloaded',who)
    h=b.sql('select a.id::text,u.issued_quantity,a.status from erp.pocket_fabric_usage u join erp.material_adjustments a on a.id=u.adjustment_id where a.notes=%s',(reason,));assert len(h)==1 and h[0][1]==D('.75') and h[0][2]=='POSTED',h
    return {'actual_ui_input':'0.75','stock_before':str(before),'stock_after':str(before-D('.75')),'stored_document':h}
def pocket_period(who='owner'):
    nav('Gudang','Kain kantong',who)
    b.fill('Awal periode kain kantong','2026-09-05',who);b.fill('Akhir periode kain kantong','2026-09-09',who);reason='Independent browser allocation '+who;b.fill('Alasan pembagian kain kantong',reason,who);click('Lihat pembagian',who);b.wait_text('116,71',who);snap(who+'-pocket-allocation-preview',who)
    before=b.sql('select count(*) from erp.material_stock_movements',one=True);click('Sahkan pembagian ke HPP',who)
    wait_db(lambda:b.sql('select count(*) from erp.pocket_periods where reason=%s',(reason,),one=True),1);assert b.sql('select count(*) from erp.material_stock_movements',one=True)==before
    snap(who+'-pocket-allocation-posted',who);click('Batalkan alokasi 2026-09-05',who);b.fill('Alasan pembatalan alokasi','Independent UI cancellation '+who,who);click('Sahkan pembatalan alokasi',who)
    wait_db(lambda:b.sql("select count(*) from erp.pocket_period_events e join erp.pocket_periods p on p.id=e.pool_id where p.reason=%s and e.kind='CANCEL'",(reason,),one=True),1);assert b.sql('select count(*) from erp.material_stock_movements',one=True)==before;snap(who+'-pocket-allocation-cancelled',who)
    return {'allocated_and_cancelled':True,'material_movement_count_unchanged':before}

def redye(who='owner',key='UI'):
    nav('Produksi','Barang BS & Rework',who);number=b.sql('select bs_number from erp.bs_cases where id=%s',(X['redye'][key]['bs'],),one=True)
    b.ab('wait','--fn','!!document.querySelector(".cbsr-list button")',who=who)
    b.native_input('.cbsr-search input',number,who);b.ab('snapshot','-i',who=who)
    b.ab('click','.cbsr-search button',who=who) if not who.startswith('mobile') else b.ab('tap','.cbsr-search button',who=who)
    b.ab('wait','--fn','document.querySelectorAll(".cbsr-list button").length===1&&document.querySelector(".cbsr-list button").textContent.includes('+json.dumps(number)+')&&!document.querySelector(".cbsr-busy")',who=who)
    b.ab('snapshot','-i',who=who);b.ab('tap' if who.startswith('mobile') else 'click','.cbsr-list button',who=who)
    click('Rewash',who);b.fill('NOMOR ORDER · WAJIB','BE-AUD-BROWSER-'+who,who);wrapped('VENDOR REWASH',C['daily_vendor'],who);b.fill('QTY DIKIRIM','7',who);b.fill('WAKTU FISIK · WIB','2026-09-14T08:00',who);wrapped('GUDANG FG BILA GOOD',C['fg'],who);b.fill('CATATAN / ALASAN','Independent browser new-color service '+who,who)
    b.ab('snapshot','-i',who=who);b.ab('find','label','Hasil GOOD menjadi SKU lain','check',who=who)
    wrapped('SKU hasil baru',C['redye_target'],who);wrapped('Proses celup berbayar',C['redye_process'],who)
    if who=='mobile':wrapped('Harga jasa','UNKNOWN',who)
    snap(who+'-redye-ready',who);click('Buat order celup ulang',who)
    wait_db(lambda:b.sql('select count(*) from erp.rework_orders where rework_number=%s',('BE-AUD-BROWSER-'+who,),one=True),1);b.wait_text('GOOD KUMULATIF',who)
    b.fill('GOOD KUMULATIF','5',who);b.fill('BS KUMULATIF','2',who);b.fill('WAKTU SELESAI · WIB','2026-09-18T08:00',who);wrapped('GUDANG GOOD FG',C['fg'],who);b.fill('ALASAN HASIL FISIK','Independent browser actual five good and two BS '+who,who);snap(who+'-redye-completion-ready',who);click('Post hasil & recovery',who)
    wait_db(lambda:b.sql('select status from erp.rework_orders where rework_number=%s',('BE-AUD-BROWSER-'+who,),one=True),'COMPLETED');snap(who+'-redye-completed',who);click('Refetch',who);b.wait_text('5 Good · 2 BS',who);snap(who+'-redye-reloaded',who)
    rows=b.sql('select c.to_product_id::text,a.qty_pcs,a.destination_lot_id::text from erp.rework_orders r join erp.be_conversion_sources_v1 s on s.rework_id=r.id join erp.product_conversions c on c.id=s.conversion_id join erp.product_conversion_allocations a on a.conversion_id=c.id where r.rework_number=%s',('BE-AUD-BROWSER-'+who,));assert len(rows)==1 and rows[0][0]==C['redye_target'] and rows[0][1]==5,rows
    return {'browser_posted_order':'BE-AUD-BROWSER-'+who,'new_identity_and_quantity':rows,'residual_bs':2,'reload_preserved':True}

def redye_price_ui():
    who='mobile';number='BE-AUD-BROWSER-mobile';service=b.sql('select id::text from erp.rework_orders where rework_number=%s',(number,),one=True);assert service
    before=b.sql('select count(*) from erp.fg_stock_movements',one=True)
    nav('Produksi','Laundry',who);click('Harga & tagihan',who);b.select('Vendor harga laundry',C['daily_vendor'],who);click('Invoice vendor',who);b.wait_text(number,who)
    b.fill('Alasan pembatalan invoice','Independent actual redye quote entered after physical completion',who);b.fill('Tarif celup '+number,'197,31',who);snap('mobile-redye-price-before',who);click('Isi tarif celup '+number,who)
    wait_db(lambda:b.sql('select count(*) from erp.be_redye_price_events_v1 where service_id=%s',(service,),one=True),1)
    assert b.sql('select rate from erp.be_redye_price_events_v1 where service_id=%s',(service,),one=True)==D('197.31');assert b.sql('select count(*) from erp.fg_stock_movements',one=True)==before
    click('Muat ulang harga',who);b.wait_text(number,who);snap('mobile-redye-price-reloaded',who)
    return {'real_ui_service':service,'rate':'197.31','quoted_cost':'1381.17','physical_count_unchanged':before,'router':'public.erp_save_laundry_bd_action_v1 SET_REDYE_PRICE'}

def price_role_revoke():
    candidates=[x for x in b.HTTP_EVENTS if x.get('http_status')==200 and x.get('path')=='/rest/v1/rpc/erp_save_laundry_bd_action_v1' and (x.get('payload') or {}).get('p_action')=='SET_REDYE_PRICE']
    assert candidates,'Missing actual successful UI price request'
    payload=candidates[-1]['payload'];user=b.FIX['owner']['auth_id'];prior=b.sql('select role,role_id::text from erp.app_users where auth_user_id=%s',(user,))[0];viewer=b.sql('select role_id::text from erp.app_users where auth_user_id=%s',(b.FIX['viewer']['auth_id'],),one=True);before=b.sql('select count(*) from erp.be_redye_price_events_v1',one=True)
    with psycopg.connect(b.DSN) as c:
        c.execute("select set_config('app.change_reason','Independent removal of price-writing role, retain ordinary read',true)");c.execute("update erp.app_users set role='STAFF',role_id=%s where auth_user_id=%s",(viewer,user))
    try:
        fresh={**payload,'p_client_request_id':b.uid()};fs,fb=b.rpc('erp_save_laundry_bd_action_v1',fresh,expect_ok=False);assert fs in(400,403),(fs,fb)
        rs,rb=b.rpc('erp_save_laundry_bd_action_v1',payload,expect_ok=False);b.EVENTS.append({'actual_price_role_revocation':{'fresh_status':fs,'fresh':fb,'replay_status':rs,'replay':rb,'price_event_count_unchanged':b.sql('select count(*) from erp.be_redye_price_events_v1',one=True)==before}});assert rs in(400,403),{'fresh_denied':fs,'replay_after_role_revoked':rs,'cached_response':rb}
    finally:
        with psycopg.connect(b.DSN) as c:
            c.execute("select set_config('app.change_reason','Restore disposable browser owner',true)");c.execute('update erp.app_users set role=%s,role_id=%s where auth_user_id=%s',(*prior,user))
    return {'fresh':fs,'replay':rs}

def viewer_browser(who='viewer'):
    nav('Gudang','Ganti Merek',who);snap(who+'-conversion',who)
    values=b.evaluate('Array.from(document.querySelectorAll("button")).filter(x=>x.textContent.trim()==="Lihat pratinjau").map(x=>({disabled:x.disabled}))',who);assert len(values)==1 and values[0]['disabled'],values
    return {'viewer_logged_in':True,'conversion_available':True,'writer_disabled':values}

def capacity_ui():
    if 'capacity' not in X or 'state' not in X['capacity']:raise AssertionError('Independent volume fixture not completed')
    cap=X['capacity'];ident=cap['old']['id'];nav('Gudang','Kain kantong');b.ab('wait','--fn','Array.from(document.querySelectorAll("section")).some(x=>x.querySelector("h2")?.textContent==="Riwayat pembagian periode"&&x.querySelectorAll("tbody tr").length===50)');snap('owner-old-active-period-hidden')
    buttons=b.evaluate('Array.from(document.querySelectorAll("button")).map(x=>x.textContent.trim())')
    b.EVENTS.append({'older_active_period':cap['state'],'shown_cancel_buttons':[x for x in buttons if 'Batalkan alokasi' in x],'51_actual_cycles':len(cap['cycles'])})
    try:
        assert 'Batalkan alokasi 2026-09-05' in buttons,{'old_active_period_missing_in_actual_browser':ident,'actual_backend_state':cap['state'],'shown':buttons}
    finally:
        # Only after recording the UI problem: ordinary public command cleans the
        # audit fixture so independent UI allocation tests are still possible.
        r=b.rpc('erp_save_pocket_fabric_action_v1',{'p_action':'CANCEL_PERIOD','p_payload':{'id':ident,'expected_revision':cap['state']['revision'],'reason':'Independent volume fixture cleanup after real UI evidence'},'p_client_request_id':b.uid()})
        b.EVENTS.append({'hidden_period_public_cleanup':r})
    return {'older_active_period_reachable':True}

def selector_ui():
    nav('Gudang','Ganti Merek');b.fill('Cari lot / SKU','AUD-DAY-1');click('Cari lot')
    ready='Array.from(document.querySelectorAll("button")).some(x=>x.textContent.trim()==="Lot berikutnya"&&!x.disabled)'
    b.ab('wait','--fn',ready);click('Lot berikutnya');b.wait_text('halaman 2');b.ab('wait','--fn',ready);click('Lot berikutnya');b.wait_text('halaman 3');snap('owner-real-selector-page3')
    number=X['selector']['oldest'][1];b.fill('Cari lot / SKU',number);click('Cari lot');b.wait_text('1 lot/lokasi');snap('owner-oldest-source-search')
    return {'more_than_50_real_sources':True,'third_page_reached':True,'oldest_source_search':number}

def inactive_http():
    calls=[('erp_get_product_conversion_workspace_v1',{'p_filters':{}}),('erp_get_pocket_fabric_workspace_v1',{'p_query':''}),('erp_get_bs_resolution_workspace_v1',{'p_filter':'ACTIVE','p_kind':'ALL','p_query':None,'p_pattern_id':None,'p_limit':50,'p_offset':0})]
    outcomes=[]
    for name,payload in calls:
        status,r=b.request('http://127.0.0.1:54328/rest/v1/rpc/'+name,payload,{'apikey':b.KEYS['ANON_KEY']});assert status in(401,403,400),(name,status,r);outcomes.append({'anonymous_rpc':name,'http':status,'body':r})
    originals=[x for x in b.HTTP_EVENTS if x.get('http_status')==200 and x.get('path') in ['/rest/v1/rpc/erp_save_product_conversion_action_v1','/rest/v1/rpc/erp_save_pocket_fabric_action_v1','/rest/v1/rpc/erp_save_bs_resolution_action_v1']]
    byfamily={x['path']:x['payload'] for x in originals}
    with psycopg.connect(b.DSN) as c:
        c.execute("select set_config('app.change_reason','Independent browser owner inactive test',true)");c.execute('update erp.app_users set is_active=false where auth_user_id=%s',(b.FIX['owner']['auth_id'],))
    try:
        for name,payload in calls:
            status,r=b.rpc(name,payload,expect_ok=False);assert status in(400,401,403),(name,status,r);outcomes.append({'inactive_workspace':name,'http':status,'body':r})
        for path,payload in byfamily.items():
            for mode in ['REPLAY','FRESH']:
                actual=dict(payload)
                if mode=='FRESH':actual['p_client_request_id']=b.uid()
                status,r=b.rpc(path.split('/')[-1],actual,expect_ok=False);outcomes.append({'inactive_mutation':path,'mode':mode,'http':status,'body':r});assert status in(400,401,403),(path,mode,status,r)
    finally:
        with psycopg.connect(b.DSN) as c:
            c.execute("select set_config('app.change_reason','Restore independent browser owner',true)");c.execute('update erp.app_users set is_active=true where auth_user_id=%s',(b.FIX['owner']['auth_id'],))
    return {'families_with_positive_cache':list(byfamily),'outcomes':outcomes}
def main():
    b.OUT.mkdir(parents=True,exist_ok=True)
    try:
        b.setup_gateway();metadata()
        if not b.case('HTTP.AUTH','Actual GoTrue owner and restricted viewer',b.setup_identities):return
        b.case('HTTP.ACCESS','Authorized workspace and restricted money/write boundary',workspace_http)
        if not b.case('BROWSER.BUILD','Build and serve exact candidate UI',b.build_ui):return
        if b.case('BROWSER.LOGIN','Owner real browser password login',b.browser_auth):
            b.case('BROWSER.CAPACITY','Actual older active allocation remains reachable beyond 50 periods',capacity_ui)
            b.case('BROWSER.SELECTOR','Third source page and oldest-source search',selector_ui)
            b.case('BROWSER.CONVERSION','Preview, post three PCS, and reload with actual DB lineage',conversion)
            b.case('BROWSER.LOST_RESPONSE','Dropped response after real commit reconciles with identical UUID',lost_response)
            b.case('BROWSER.POCKET_STOCK','Actual pocket stock UI posts 0.75 and survives reload',pocket_stock)
            b.case('BROWSER.POCKET_ALLOCATION','Actual period preview, allocation and cancellation preserve stock',pocket_period)
            b.case('BROWSER.REDYE','Actual send and complete new-color BS service through UI',redye)
        if b.case('BROWSER.VIEWER_LOGIN','Restricted actor logs in with real Auth',lambda:b.browser_auth('viewer')):b.case('BROWSER.VIEWER','Restricted UI exposes no writer',viewer_browser)
        if b.case('MOBILE.LOGIN','Native-touch Chromium mobile emulation with real owner login',lambda:b.mobile_auth('mobile','owner')):
            b.case('MOBILE.CONVERSION','Touch conversion posts three PCS and reloads',lambda:conversion('UI_MOBILE','mobile'))
            b.case('MOBILE.POCKET_STOCK','Touch pocket issue posts only actual 0.75',lambda:pocket_stock('mobile'))
            b.case('MOBILE.POCKET_ALLOCATION','Touch period allocation and inverse preserve stock',lambda:pocket_period('mobile'))
            b.case('MOBILE.REDYE','Touch new-color BS service and completion',lambda:redye('mobile','MOBILE'))
            b.case('MOBILE.REDYE_PRICE','Unknown completed service priced through actual UI router',redye_price_ui)
        b.case('HTTP.ANON_INACTIVE','Anonymous and inactive same-token workspace fresh and cached boundaries',inactive_http)
        b.case('HTTP.PRICE_ROLE_REVOKE','Actual price UI replay rechecks removed owner privilege',price_role_revoke)
    finally:b.cleanup();save()
if __name__=='__main__':main()
