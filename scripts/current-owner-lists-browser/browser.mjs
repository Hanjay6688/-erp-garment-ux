import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'

const fixture=(op,args={})=>JSON.parse(execFileSync('python',
 ['../auditor/scripts/current-owner-lists-browser/fixture.py',op],
 {cwd:'../writer',input:JSON.stringify(args),encoding:'utf8',maxBuffer:16*1024*1024}).trim())
const configs={
 notes:{group:'Produksi',menu:'Susun Nota FG',panel:'.cnota',rpc:'erp_cp7_get_nota_workspace_v1',title:'nota mandor',
  search:'Cari nota tersimpan',submit:'Cari nota',filter:'Status nota tersimpan',next:'nota berikutnya',previous:'nota sebelumnya',
  rows:'.cnota-note-row',number:'note_number'},
 fg:{group:'Gudang',menu:'Stock Adjustment',panel:'.cfga',rpc:'erp_cp7_get_fg_adjustments_v1',title:'dokumen penyesuaian FG',
  search:'Cari dokumen penyesuaian FG',submit:'Cari koreksi FG',filter:'Status dokumen penyesuaian FG',next:'Dokumen berikutnya',previous:'Dokumen sebelumnya',rows:'button.cproc-receipt'},
 count:{group:'Gudang',menu:'Stock Adjustment',panel:'.cmat',rpc:'erp_cp7_get_material_counts_v1',title:'dokumen hitung fisik',
  search:'Cari dokumen hitung fisik',submit:'Cari pemeriksaan',filter:'Status dokumen hitung fisik',next:'Pemeriksaan berikutnya',previous:'Pemeriksaan sebelumnya',rows:'button.cproc-receipt'},
 accessory:{group:'Keuangan',menu:'Nota Ambil Aksesori',panel:'.initial-import',rpc:'erp_get_accessory_issue_workspace_v1',title:'nota aksesori',
  search:'Cari nota aksesori',submit:'Cari nota',filter:'Status nota aksesori',next:'Nota berikutnya',previous:'Nota sebelumnya',rows:'section[aria-label="Riwayat nota aksesori"] tbody tr'},
 card:{group:'Gudang',menu:'Ringkasan Barang Jadi',panel:'.cfg-ledger',rpc:'erp_cp7_get_fg_ledger_v2',title:'mutasi posisi FG',
  search:'Cari mutasi barang jadi',submit:'Cari mutasi',filter:'Jenis mutasi FG',next:'Mutasi berikutnya',previous:'Mutasi sebelumnya',rows:'.cfg-movement'}
}
export const IDS=Object.keys(configs).flatMap(kind=>['DESKTOP','MOBILE390'].map(size=>`OW09_WHOLE_LIST_${kind.toUpperCase()}_${size}`))

async function journey(ui,kind,f,mobile){
 const c=configs[kind],user=await ui.login('OWNER',{label:'ow09-pages-'+kind+'-'+mobile,mobile,
  timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),p=user.page,calls=[]
 const listen=request=>{if(request.url().includes('/rest/v1/rpc/')&&request.method()==='POST')calls.push(request.url().split('/').at(-1))}
 const panel=p.locator(c.panel),rows=panel.locator(c.rows)
 const tools=panel.getByRole('form',{name:'Cari, browse, urutkan dan filter '+c.title,exact:true})
 const keys=kind==='accessory'?{q:'query',status:'history_status',order:'history_order',offset:'history_offset'}:
  {q:'q',status:kind==='card'?'movement_type':'status',order:'order',offset:'offset'}
 const want=(q,offset,order='SOURCE',status=null)=>({[keys.q]:q,[keys.offset]:offset,[keys.order]:order,[keys.status]:status})
 const act=async(expected,operation)=>{
  const read=p.waitForResponse(r=>{
   if(!r.url().endsWith('/rpc/'+c.rpc))return false
   const data=r.request().postDataJSON(),query=data?.[kind==='accessory'?'p_filters':'p_query']??{}
   return (kind!=='notes'||data.p_section==='NOTES')&&Object.entries(expected).every(([k,v])=>query[k]===v)
  })
  const [reply]=await Promise.all([read,operation()]);assert.equal(reply.status(),200,await reply.text())
  const body=await reply.json()
  return kind==='accessory'?{rows:body.history,total:String(body.history_count),...body.history_page}:body.page
 }
 const shown=async(answer,expected,total,offset)=>{
  assert.equal(answer.total,String(total));assert.equal(answer.offset,offset);assert.equal(answer.limit,f.limit)
  assert.deepEqual(answer.rows.map(r=>r.id),expected.map(r=>r.id))
  await ui.expect(rows).toHaveCount(expected.length)
  if(kind==='card'){
   assert.deepEqual(await rows.evaluateAll(nodes=>nodes.map(n=>n.getAttribute('data-fg-movement-id'))),expected.map(r=>r.id))
   for(const r of answer.rows){const e=f.balances[r.id];assert.ok(e);assert.equal(Number(r.physical_delta),e.delta);assert.equal(Number(r.physical_balance),e.balance);assert.equal(Number(r.available_balance),e.balance)}
  }else{
   assert.deepEqual(answer.rows.map(r=>r[c.number??'number']),expected.map(r=>r.number))
   let labels
   if(kind==='notes')labels=await rows.locator('small').allTextContents()
   else if(kind==='accessory')labels=await rows.locator('td:first-child').allTextContents()
   else labels=await rows.locator('strong').allTextContents()
   assert.deepEqual(labels.map((v,i)=>kind==='notes'?v.endsWith(' · '+expected[i].number):v===expected[i].number),expected.map(()=>true))
  }
  await ui.expect(panel).toContainText('Total '+total)
 }
 const search=async(value,order='LABEL_DESC')=>{
  await tools.getByLabel(c.search,{exact:true}).fill(value)
  return act(want(value,0,order),()=>tools.getByRole('button',{name:c.submit,exact:true}).click())
 }
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:c.group})).toBeAttached()
  const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• '+c.menu,exact:true})
  if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:c.group}).click()
  await link.click()
  if(kind==='fg')await p.getByRole('navigation',{name:'Jenis persediaan'}).getByRole('button',{name:'Barang jadi',exact:true}).click()
  if(kind==='card'){
   await p.getByLabel('Cari barang jadi',{exact:true}).fill(f.sku)
   await p.getByRole('button',{name:'Cari stok',exact:true}).click()
   await ui.expect(p.locator('.cfg-position')).toHaveCount(1)
   await p.locator('.cfg-position').getByRole('button').click()
  }
  await ui.expect(tools).toBeVisible()
  const before=fixture('state');p.on('request',listen)
  let answer=await search(f.query,'SOURCE')
  const all=f.matched.SOURCE;assert.equal(all.length,f.count)
  await shown(answer,all.slice(0,f.limit),f.count,0)
  answer=await act(want(f.query,f.limit),()=>panel.getByRole('button',{name:c.next,exact:true}).click())
  await shown(answer,all.slice(f.limit),f.count,f.limit)
  await ui.expect(panel.getByRole('button',{name:c.next,exact:true})).toBeDisabled()
  answer=await act(want(f.query,0,'LABEL_DESC'),()=>tools.getByLabel('Urutkan '+c.title,{exact:true}).selectOption('LABEL_DESC'))
  const descending=f.matched.LABEL_DESC;await shown(answer,descending.slice(0,f.limit),f.count,0)
  answer=await act(want(f.query,f.limit,'LABEL_DESC'),()=>panel.getByRole('button',{name:c.next,exact:true}).click())
  await shown(answer,descending.slice(f.limit),f.count,f.limit)
  answer=await act(want(f.query,0,'LABEL_DESC'),()=>panel.getByRole('button',{name:c.previous,exact:true}).click())
  await shown(answer,descending.slice(0,f.limit),f.count,0)
  answer=await act(want(f.query,0,'LABEL_DESC',f.filter),()=>tools.getByLabel(c.filter,{exact:true}).selectOption(f.filter))
  const filtered=descending.filter(r=>r.status===f.filter);assert.equal(filtered.length,f.count-1)
  await shown(answer,filtered.slice(0,f.limit),filtered.length,0)
  answer=await act(want(f.query,f.limit,'LABEL_DESC',f.filter),()=>panel.getByRole('button',{name:c.next,exact:true}).click())
  await shown(answer,filtered.slice(f.limit),filtered.length,f.limit)
  answer=await act(want(f.query,0,'LABEL_DESC'),()=>tools.getByLabel(c.filter,{exact:true}).selectOption(kind==='accessory'?'ALL':''))
  await shown(answer,descending.slice(0,f.limit),f.count,0)
  const sought=kind==='card'?f.search:all[f.limit].number
  answer=await search(sought)
  const matches=kind==='card'?descending.filter(r=>r.id===f.search_id):f.whole.LABEL_DESC.filter(r=>r.number.toLowerCase().includes(sought.toLowerCase()))
  await shown(answer,matches,matches.length,0);assert.ok(matches.some(r=>r.id===all[f.limit].id))
  answer=await search('OW09-NO-MATCH-'+kind);await shown(answer,[],0,0)
  answer=await act(want('',0),()=>tools.getByRole('button',{name:'Browse semua',exact:true}).click())
  await shown(answer,f.whole.SOURCE.slice(0,f.limit),f.whole.SOURCE.length,0)
  await ui.expect(tools.getByLabel(c.search,{exact:true})).toHaveValue('')
  assert.deepEqual(fixture('state'),before,'BROWSING_CHANGED_BUSINESS_ROWS_OR_SEQUENCES')
  assert.deepEqual(calls.filter(name=>!/^erp_(?:cp7_)?get_/.test(name)),[])
  await ui.expect.poll(()=>p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  if(mobile)assert.equal(await p.evaluate(()=>innerWidth),390)
  const screenshot=`OW09_LIST_${kind}_${mobile?'MOBILE390':'DESKTOP'}.png`
  await panel.screenshot({path:'cp6-proof/t3/'+screenshot})
  return {status:'PASS',kind,mobile,real_auth:true,Native_fixture:true,matching_records:f.count,pages:[f.limit,f.count-f.limit],
   filtered_records:f.count-1,filtered_pages:[f.limit,f.count-1-f.limit],whole_result_order_exact:true,
   Native_UUID_and_DOM_order_exact:true,previous_second_page_search:true,empty_result_zero:true,browse_reset_exact:true,
   card_prefix_balances_exact:kind==='card',business_rows_sequences_unchanged:true,writer_RPC:0,screenshot,production_go:false}
 }catch(error){
  writeFileSync(`cp6-proof/t3/OW09_LIST_${kind}_${mobile?'MOBILE390':'DESKTOP'}_FAILURE.json`,JSON.stringify({error:String(error),stack:error.stack,calls,text:await p.locator('main').innerText().catch(()=> '')},null,2))
  await p.screenshot({path:`cp6-proof/t3/OW09_LIST_${kind}_${mobile?'MOBILE390':'DESKTOP'}_FAILURE.png`,fullPage:true}).catch(()=>{})
  throw error
 }finally{p.off('request',listen);await user.context.close()}
}

export async function cases(ui,today){
 const fixtures=fixture('prepare',{today})
 return Object.keys(configs).flatMap(kind=>[false,true].map(mobile=>[
  `OW09_WHOLE_LIST_${kind.toUpperCase()}_${mobile?'MOBILE390':'DESKTOP'}`,()=>journey(ui,kind,fixtures[kind],mobile)]))
}
