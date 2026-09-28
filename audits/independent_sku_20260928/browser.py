"""Own real Auth/HTTP and browser verification of frozen SKU screens."""
from pathlib import Path
import sys,json,re,time,copy
from decimal import Decimal as D
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'audits/independent_be_20260928'))
import browser_support as b
b.OUT=ROOT/'audit-results'/'sku-http-browser';b.OUT.mkdir(parents=True,exist_ok=True)
# Fixed localhost routes, explicitly listed; no browser-selected upstream.
b.PROXY_ROUTES.update({'/rest/v1/rpc/erp_get_sku_workspace_v1':[54329,'/rpc/erp_get_sku_workspace_v1'],'/rest/v1/rpc/erp_get_sku_hpp_v1':[54329,'/rpc/erp_get_sku_hpp_v1'],'/rest/v1/rpc/erp_save_sku_action_v1':[54329,'/rpc/erp_save_sku_action_v1']})
fixture=json.loads((ROOT/'audit-results/sku-fixture.json').read_text());C=fixture['identity'];F=fixture['fixtures']
def save():
 for file,data in [('results.json',{'candidate':b.PRODUCT,'results':b.RESULTS,'limits':['Synthetic isolated database','Chromium mobile emulation, not physical phone'],'production_go':False}),('events.json',b.EVENTS),('http-events.json',b.HTTP_EVENTS)]:
  (b.OUT/file).write_text(b.redact(json.dumps(data,indent=2,default=str)))
b.save=save

def http_boundaries():
 r=b.rpc('erp_get_sku_workspace_v1',{'p_filters':{'query':'AUD-SKU-RANGE'}});assert r['groups_total']==1,r
 w=b.rpc('erp_get_sku_workspace_v1',{'p_filters':{}},'viewer');assert w['can_edit'] is False and w['lookups'] is None and all(g['settings'] is None for g in w['groups']),w
 h=b.rpc('erp_get_sku_hpp_v1',{'p_filters':{'query':'AUD-SKU-RANGE'}});assert int(h['groups'][0]['qty'])==16,h
 outcomes=[]
 for name,args in [('erp_get_sku_hpp_v1',{'p_filters':{}}),('erp_save_sku_action_v1',{'p_action':'SAVE_GROUPS','p_payload':C['initial_payload'],'p_client_request_id':b.uid()})]:
  status,body=b.rpc(name,args,'viewer',False);assert status>=400,(status,body);outcomes.append({'name':name,'status':status,'response':body})
 return {'owner_group':r,'owner_hpp':h,'viewer_refusals':outcomes}
def private_helpers():
 # Bypass local browser allow-list and address actual public-only PostgREST.
 names=['bf_save_groups_v1','bf_bind_wave_v1','bf_ensure_work_v1','bf_legacy_basis_v1','bf_laundry_rate_v1','bf_resolve_import_product_v1','save_sku_action_v1','get_sku_workspace_v1','get_sku_hpp_v1'];out=[]
 for who in ['owner','viewer']:
  for name in names:
   status,body=b.request('http://127.0.0.1:54329/rpc/'+name,{},headers={'apikey':b.KEYS['ANON_KEY'],'Authorization':'Bearer '+b.TOKENS[who]});assert status==404,(who,name,status,body);out.append({'actor':who,'private_helper':name,'status':status})
 return out

def nav(section,label,who='owner'):
 click=b.mobile_button if who.startswith('mobile') else b.button
 if who.startswith('mobile'):
  b.ab('scroll','up','5000',who=who)
  if not b.evaluate('document.querySelector("aside.sidebar")?.classList.contains("sidebar-open")',who):click('Buka menu',who)
  b.ab('wait','--fn','Math.abs(document.querySelector("aside.sidebar").getBoundingClientRect().left)<1',who=who)
 visible=b.evaluate('Array.from(document.querySelectorAll("aside.sidebar button")).filter(e=>e.getClientRects().length).map(e=>e.textContent.trim())',who)
 if not any(label in x and '•' in x for x in visible):click(section,who,False)
 click('• '+label,who)
 b.ab('wait','--fn','!!document.querySelector('+json.dumps('.biz-invoice-draft' if label=='Penjualan & Invoice' else '.sku-workspace')+')',who=who)
 if who.startswith('mobile'):b.ab('wait','--fn','!document.querySelector("aside.sidebar").classList.contains("sidebar-open")',who=who)
def master_edit(who='owner',price='93456.78'):
 click=b.mobile_button if who.startswith('mobile') else b.button
 nav('Master Data','Produk & SKU',who);b.fill('Cari SKU atau merek','AUD-SKU-RANGE',who);click('Cari / muat ulang',who)
 b.ab('wait','--fn','document.body.innerText.includes("Ubah SKU AUD-SKU-RANGE")',who=who)
 click('Ubah SKU AUD-SKU-RANGE',who);b.fill('Harga jual per PCS untuk seluruh ukuran',price,who);b.fill('Alasan perubahan','Independent real browser all-size update',who)
 click('Periksa seluruh dampak perubahan',who);b.ab('wait','--fn','document.body.innerText.includes("Periksa sebelum menyimpan")',who=who)
 body=b.text_body(who);assert all(x in body for x in ['31, 32, 33, 34','Harga sebelumnya','Resep sebelumnya']),body
 disabled=b.evaluate('Array.from(document.querySelectorAll("button")).find(e=>e.textContent==="Simpan seluruh perubahan SKU")?.disabled',who);assert disabled is True
 selector=b.control_selector('Array.from(document.querySelectorAll("label")).find(e=>e.textContent.includes("Saya sudah memeriksa anggota"))?.querySelector("input")',who)
 b.ab('check',selector,who=who);click('Simpan seluruh perubahan SKU',who)
 b.ab('wait','--fn','!document.body.innerText.includes("Periksa sebelum menyimpan")',who=who)
 rows=b.sql('select p.price,m.product_root::text from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id join erp.bf_skus_v1 s on s.id=v.sku_id and s.revision=v.revision join erp.product_price_versions p on p.id=m.price_version_id where s.id=%s',(C['sku_id'],));assert len(rows)==4 and all(x[0]==D(price) for x in rows),rows
 b.ab('reload',who=who);b.ab('wait','--fn','!!document.querySelector(".sku-workspace")',who=who);b.snap('master-saved-'+who,who)
 return {'committed_members':rows,'all_size_price':price,'review_checkbox_required':True,'reload':True}
def hpp_screen(who='owner'):
 click=b.mobile_button if who.startswith('mobile') else b.button
 nav('Keuangan','HPP & Rekalkulasi',who)
 b.ab('wait','--fn','document.body.innerText.includes("HPP per SKU")',who=who);b.fill('Cari SKU atau merek','AUD-SKU-RANGE',who);click('Tampilkan',who)
 b.ab('wait','--fn','document.body.innerText.includes("Rincian AUD-SKU-RANGE")',who=who)
 body=b.text_body(who);assert '6.394,53' in body and '399,66' in body,body
 rows=b.evaluate('Array.from(document.querySelectorAll(".sku-workspace table")).map(t=>Array.from(t.querySelectorAll("tbody tr")).map(r=>r.innerText))',who);assert len(rows[-1])==3,rows;b.snap('hpp-'+who,who)
 return {'visible_tables':rows,'expected_stock_value':'6394.53','expected_weighted_unit_rounded':'399.66'}
def viewer_screen():
 nav('Master Data','Produk & SKU','viewer');b.ab('wait','--fn','document.body.innerText.includes("SKU bersama")',who='viewer')
 body=b.text_body('viewer');assert 'Anggota fisik tersedia' not in body and 'Terbatas' in body and 'Harga jual per PCS untuk seluruh ukuran' not in body,body;b.snap('restricted-sku','viewer');return {'no_editor':True,'prices_hidden':True}
def manual_sales(who='owner'):
 nav('Penjualan','Penjualan & Invoice',who);out=[]
 # Real inputs on the retained simulation UI; no backend posting claimed.
 for total in [12,13,23,24]:
  for i,q in enumerate([total,0,0],1):b.ab('fill',f'.biz-invoice-lines > article:first-child .biz-size-entry label:nth-child({i}) input',str(q),who=who)
  before=b.evaluate('({qty:Array.from(document.querySelectorAll(".biz-invoice-lines > article:first-child .biz-size-entry input")).map(e=>Number(e.value)),label:document.querySelector(".biz-invoice-lines > article:first-child .biz-line-total").innerText,helper:document.querySelector(".biz-invoice-lines > article:first-child .biz-dozen-helper input").value})',who)
  assert sum(before['qty'])==total and before['helper']=='',before
  assert f'{total//12} lusin · {total%12} potong' in before['label'],before
  b.ab('click','.biz-invoice-lines > article:first-child .biz-dozen-helper button',who=who)
  after=b.evaluate('Array.from(document.querySelectorAll(".biz-invoice-lines > article:first-child .biz-size-entry input")).map(e=>Number(e.value))',who);assert after==before['qty'],(before,after);out.append(before)
 b.snap('manual-sales-'+who,who);return {'layer':'Retained sales UX simulation only','manual_cases':out,'empty_helper_is_noop':True}
def main():
 native_results=json.loads((ROOT/'audit-results/sku-native-results.json').read_text())['results']
 if not any(x['id']=='SKU.L03' and x['status']=='PASS' for x in native_results):
  b.RESULTS.append({'id':'SKU.BROWSER.PREREQUISITE','status':'BLOCKED','reason':'Own exact-size FG fixture did not pass; no UI conclusion'});save();return
 try:
  b.setup_gateway()
  if not b.case('SKU.HTTP.AUTH','Real owner and viewer authentication',b.setup_identities):return
  b.case('SKU.HTTP.ACCESS','Actual REST economic access boundary',http_boundaries)
  b.case('SKU.HTTP.PRIVATE','Private helpers are absent from direct REST public schema',private_helpers)
  if not b.case('SKU.BROWSER.BUILD','Actual frozen product bundle',b.build_ui):return
  if b.case('SKU.BROWSER.LOGIN','Owner actual password form',b.browser_auth):
   b.case('SKU.BROWSER.MASTER','Review and save shared four-size price through actual UI',master_edit)
   b.case('SKU.BROWSER.HPP','Weighted summary and physical size detail through UI',hpp_screen)
   b.case('SKU.X.SR02.DESKTOP','Manual PCS does not round-trip through a rounded dozen helper',manual_sales)
  if b.case('SKU.BROWSER.VIEWER_LOGIN','Restricted actual password form',lambda:b.browser_auth('viewer')):b.case('SKU.BROWSER.VIEWER','Read-only SKU identity UI hides costs',viewer_screen)
  if b.case('MOBILE.SKU.LOGIN','Touch Chromium owner login',lambda:b.mobile_auth('mobile','owner')):
   b.case('MOBILE.SKU.MASTER','Touch save shared four-size price',lambda:master_edit('mobile','94567.89'))
   b.case('MOBILE.SKU.HPP','Touch weighted HPP with physical detail',lambda:hpp_screen('mobile'))
   b.case('MOBILE.SKU.SR02','Mobile manual PCS and empty helper preserve exact quantities',lambda:manual_sales('mobile'))
 finally:b.cleanup();save()
if __name__=='__main__':main()
