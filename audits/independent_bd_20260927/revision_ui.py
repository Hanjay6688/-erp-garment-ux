"""Independent actual browser revision probes; no mocked network or product fixes."""
import json,re
from decimal import Decimal as D
B=None

def native_datetime(label,value,who='owner'):
    b=B;selector='input[aria-label='+json.dumps(label)+']'
    b.ab('wait',selector,who=who)
    raw=b.ab('get','cdp-url',who=who)
    endpoints=re.findall(r'ws://(?:127\.0\.0\.1|localhost):\d+/[^\s"\x27]+',raw)
    assert len(endpoints)==1,{'cdp_endpoints':len(endpoints)}
    worker=r'''
import {pathToFileURL} from 'node:url';
const {chromium}=await import(pathToFileURL(process.env.BD_PLAYWRIGHT_CORE+'/index.mjs').href);
const [endpoint, selector, value]=process.argv.slice(1);
const browser=await chromium.connectOverCDP(endpoint);
try {
 const pages=browser.contexts().flatMap(c=>c.pages()).filter(p=>p.url().startsWith('http://127.0.0.1:4176/'));
 if(pages.length!==1)throw new Error('Expected exactly one real app page: '+pages.length);
 const locator=pages[0].locator(selector);await locator.fill(value);await locator.press('Tab');
 console.log(JSON.stringify({input_value:await locator.inputValue(),adapter:'playwright-native-locator-fill'}));
} finally {await browser.close();}
'''
    r=b.run(['node','--input-type=module','-e',worker,endpoints[0],selector,value],timeout=45)
    out=json.loads(r.stdout);assert out['input_value']==value,out
    b.EVENTS.append({'native_input':out,'selector':selector,'session':who})


def field(label):return B.evaluate('document.querySelector('+json.dumps('[aria-label='+json.dumps(label)+']')+').value')
def options():return B.evaluate('Array.from(document.querySelector(\'select[aria-label="Sumber baris 1"]\').options).map(x=>x.value)')

def pagination_browser():
    b=B;b.select('Vendor harga laundry',b.FIX['paging_vendor']);b.button('Invoice vendor');b.wait_text('AUD-UI-PAGE-054')
    b.fill('Nomor invoice vendor','AUD-PRESERVE-PAGE');b.fill('Total invoice','19.37');before={x:field(x) for x in ['Nomor invoice vendor','Total invoice']}
    pages=0
    while 'AUD-UI-PAGE-000' not in b.text_body() and pages<5:
        b.button('Muat invoice berikutnya');b.ab('wait','--fn',"!Array.from(document.querySelectorAll('button')).some(e=>e.textContent==='Muat invoice berikutnya'&&e.disabled)");pages+=1
    b.wait_text('AUD-UI-PAGE-000');assert {x:field(x) for x in before}==before
    b.fill('Cari invoice yang dimuat','AUD-UI-PAGE-000');b.wait_text('AUD-UI-PAGE-000');assert {x:field(x) for x in before}==before
    b.snap('revision-invoice-oldest-reachable');b.fill('Cari invoice yang dimuat','')
    return {'created':55,'oldest_found_by_actual_load_next':True,'next_clicks':pages,'draft_fields_preserved':before,'loaded_search_works':True}

def gap_receipt_api_reachability():
    b=B;f=b.FIX['receipt_gap'];seen=set();pages=[];filters={'vendor_id':f['vendor_id']}
    for _ in range(10):
        w=b.rpc('erp_get_laundry_bd_workspace_v1',{'p_filters':filters});ids=[x['receipt_line_id'] for x in w['billable_receipts']]
        assert not seen.intersection(ids),{'duplicate_page_ids':list(seen.intersection(ids))};seen.update(ids);pg=w['pagination'];pages.append({'count':len(ids),'pagination':pg})
        if not pg['receipt_next']:break
        filters={'vendor_id':f['vendor_id'],'receipt_after':pg['receipt_next'],'page_as_of':pg['as_of']}
    assert seen==set(f['receipt_line_ids']),{'expected':f['expected_count'],'actual':len(seen),'missing':list(set(f['receipt_line_ids'])-seen)}
    return {'all_201_reachable':True,'pages':pages,'no_duplicates':True,'snapshot_cursor_used':True}

def gap_receipt_browser_reachability():
    b=B;f=b.FIX['receipt_gap'];b.gap_open_desktop_invoices(f['vendor_id']);b.button('Tambah baris');b.ab('wait','select[aria-label="Sumber baris 1"]')
    first={x[2:] for x in options() if x.startswith('r:')};assert first==set(f['returned_ids'])
    b.select('Sumber baris 1','r:'+sorted(first)[0]);b.fill('Nomor invoice vendor','AUD-REV-OLD-SOURCE');b.fill('Total invoice','17.31');b.fill('Qty baris 1','1');b.fill('Nominal baris 1','17.31')
    before={x:field(x) for x in ['Sumber baris 1','Nomor invoice vendor','Total invoice','Qty baris 1','Nominal baris 1']}
    b.button('Muat penerimaan berikutnya');b.ab('wait','--fn',"document.querySelector('select[aria-label=\"Sumber baris 1\"]').options.length>201")
    assert {x:field(x) for x in before}==before
    got={x[2:] for x in options() if x.startswith('r:')};assert got==set(f['receipt_line_ids'])
    old=f['missing_ids'][0];b.select('Sumber baris 1','r:'+old);b.enter_date_with_keys('Tanggal invoice','2026-09-21');b.fill('Alasan pembatalan invoice','Independent existing-source draft; no posting')
    b.button('Simpan draf invoice');b.wait_text('AUD-REV-OLD-SOURCE')
    rows=b.sql("select i.status,l.receipt_line_id::text from erp.bd_laundry_invoices_v1 i join erp.bd_laundry_invoice_lines_v1 l on l.invoice_id=i.id where i.invoice_number='AUD-REV-OLD-SOURCE'");assert rows==[('DRAFT',old)],rows
    b.snap('revision-old-receipt-saved-draft')
    return {'all_201_options_reachable':True,'selected_source_and_typed_draft_preserved':before,'previously_omitted_source_saved':rows}

def package_extras_browser():
    b=B;fixture=json.loads((b.ROOT/'audit-results/revision-browser-fixture.json').read_text());c=fixture['identity'];f=fixture['source']
    w=b.rpc('erp_get_laundry_bd_workspace_v1',{'p_filters':{'vendor_id':b.FIX['vendor']}});policy=next(x for x in w['policies'] if x['key']=='LAU-DEC03')
    b.cmd('SET_POLICY',{'policy_key':'LAU-DEC03','operation':'SET','expected_version':policy['version'],'value':{'discount':'ALLOWED','extra':'ALLOWED','rounding':'LAST_LINE'},'reason':'Independent synthetic package extra agreement'})
    b.select('Vendor harga laundry',b.FIX['vendor']);b.button('Harga vendor');b.wait_text('AUD-BROWSER-KNOWN')
    b.fill('Alasan','Independent agreed package and extra');b.select('Cara harga vendor','PACKAGE');b.select('Satuan harga vendor','PCS');b.button('Simpan ketentuan');b.wait_text('Cara harga PACKAGE')
    b.button('Kirim dengan harga');b.select('Batch kirim berharga',f['batch']);b.select('Proses kirim berharga',c['process']);b.fill('Warna kirim berharga','AUD-NAVY');native_datetime('Waktu kirim berharga','2026-09-16T08:00');b.fill('Bukti serah terima','Independent six actual L pieces plus five-piece extra')
    b.fill('Qty kirim berharga AUD-1','0');b.fill('Qty kirim berharga AUD-2','6');b.select('Paket kirim berharga',b.FIX['package'])
    b.ab('check','input[aria-label="Jasa AUD-BROWSER-EXTRA"]');b.select('Penerima jasa AUD-BROWSER-EXTRA','PARTIAL');b.fill('Cakupan AUD-BROWSER-EXTRA AUD-2','5');b.fill('Alasan tambahan AUD-BROWSER-EXTRA','Five L pieces require extra finishing')
    b.ab('find','label','Vendor, batch, ukuran, jumlah, warna, waktu, dan harga sudah dicocokkan dengan serah-terima.','check');b.button('Catat kiriman berharga')
    import time
    until=time.monotonic()+10
    while not any(x.get('payload',{}).get('p_action')=='POST_PRICED_DELIVERY' for x in b.HTTP_EVENTS) and time.monotonic()<until:time.sleep(.1)
    ev=[x for x in b.HTTP_EVENTS if x.get('payload',{}).get('p_action')=='POST_PRICED_DELIVERY' and x.get('payload',{}).get('p_payload',{}).get('delivery',{}).get('distribution_batch_id')==f['batch']]
    assert len(ev)==1 and ev[0]['http_status']==200,ev
    response=ev[0]['response'];assert D(response['pricing']['total_known'])==D('55668.65'),response
    payload=ev[0]['payload']['p_payload'];assert payload['pricing']['extras'][0]['coverage']==[{'size_id':c['s2'],'qty':5}],payload
    assert payload['delivery']['lines']==[{'size_id':c['s2'],'qty_sent_pcs':6}],payload
    line=b.sql('select id::text from erp.laundry_delivery_lines where delivery_id=%s',(response['delivery_id'],),one=True)
    rows=b.sql('select ch.kind,bs.size_id::text,sh.covered_qty,sh.amount from erp.bd_laundry_charge_lines_v1 ch join erp.bd_laundry_charge_shares_v1 sh on sh.charge_line_id=ch.id join erp.laundry_delivery_batch_size_lines bs on bs.id=sh.delivery_batch_size_line_id where ch.delivery_line_id=%s order by ch.kind',(line,));assert [(x[0],x[2],D(x[3])) for x in rows]==[('EXTRA',5,D('3394.55')),('PACKAGE',6,D('52274.10'))],rows
    b.snap('revision-extra-physical-posted')
    return {'actual_browser_post':response,'readback':rows,'zero_unsent_size_accepted':True,'expected_package':'52274.10','expected_extra':'3394.55','expected_total':'55668.65'}

def free_master():
    b=B;b.select('Vendor harga laundry',b.FIX['vendor']);b.button('Harga vendor');b.wait_text('AUD-UI-CREATED')
    comp=b.sql("select id::text from erp.bd_laundry_components_v1 where vendor_id=%s and component_code='AUD-UI-CREATED'",(b.FIX['vendor'],),one=True)
    b.select('Komponen harga',comp);responses=[]
    for status,day in [('FREE','22'),('WAIVED','23')]:
        b.fill('Alasan','Independent explicit '+status+' agreement from actual screen');native_datetime('Berlaku sejak (WIB)','2026-09-'+day+'T08:00');b.select('Status harga komponen',status);b.button('Simpan versi harga komponen')
        b.ab('wait','--fn',"!Array.from(document.querySelectorAll('button')).some(e=>e.textContent==='Simpan versi harga komponen'&&e.disabled)")
        rows=b.sql('select rate_status,rate_per_pcs,reason from erp.bd_laundry_component_rates_v1 where component_id=%s order by effective_from',(comp,))
        assert rows[-1][0]==status and D(rows[-1][1])==D(0) and rows[-1][2]=='Independent explicit '+status+' agreement from actual screen',rows
        responses.append(rows[-1])
    b.snap('revision-free-waived-configured-in-browser')
    return {'actual_UI_versions':responses,'explicit_zero_distinct_from_unknown':True}

def install(module):
    global B;B=module
    for f in [pagination_browser,gap_receipt_api_reachability,gap_receipt_browser_reachability,package_extras_browser]:setattr(module,f.__name__,f)
