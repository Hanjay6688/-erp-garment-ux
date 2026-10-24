import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'

const fixture=(op,p={})=>JSON.parse(execFileSync('python',
 ['../auditor/scripts/current-invoice-history-browser/fixture.py',op],
 {cwd:'../writer',input:JSON.stringify(p),encoding:'utf8',maxBuffer:16*1024*1024}).trim())

async function open(ui,page){
 await ui.expect(page.locator('.sidebar .nav-main').filter({hasText:'Penjualan'})).toBeAttached()
 const menu=page.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=page.getByRole('button',{name:'• Penjualan & Invoice',exact:true})
 if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:'Penjualan'}).click()
 await link.click();await ui.expect(page.locator('.csales').getByRole('heading',{name:'Penjualan & Invoice',exact:true})).toBeVisible()
}

async function history(ui,page,kind,f,mobile){
 const payment=kind==='payment',word=payment?'pembayaran':'retur'
 const ws=page.locator('.csales'),detail=ws.getByRole('complementary',{name:'Rincian invoice'})
 await ws.getByLabel('Cari invoice',{exact:true}).fill(f.tag)
 await ws.getByRole('button',{name:'Cari invoice',exact:true}).click()
 const invoice=ws.getByRole('region',{name:'Daftar invoice'}).locator('.cproc-receipt')
 await ui.expect(invoice).toHaveCount(1);await invoice.click()
 await ui.expect(detail.getByRole('heading',{name:f.tag,exact:true})).toBeVisible()
 const rpc=payment?'erp_cp7_get_sales_cash_v1':'erp_cp7_get_sales_returns_v1'
 const key=payment?{q:'payment_q',status:'payment_status',order:'payment_order',offset:'payment_offset'}:
  {q:'history_q',status:'history_status',order:'history_order',offset:'offset'}
 const panel=ws.getByRole('region',{name:payment?'Pembayaran invoice':'Retur fisik invoice',exact:true})
 const list=panel.getByRole('region',{name:`Riwayat ${word} invoice`,exact:true})
 const rows=()=>list.locator('article.cproc-item'),next=payment?'Pembayaran berikutnya':'Retur berikutnya'
 const previous=payment?'Pembayaran sebelumnya':'Retur sebelumnya',reader=response=>payment?response.payments:response.page
 const responseFor=want=>page.waitForResponse(response=>{
  if(!response.url().endsWith('/rpc/'+rpc))return false
  const q=response.request().postDataJSON()?.p_query??{}
  return q.sale_id===f.sale&&(payment||q.kind==='RETURNS')&&Object.entries(want).every(([k,v])=>q[k]===v)
 })
 // Attach the response rejection handler before the UI action can wait/fail.
 const act=async(want,operation)=>{
  const [response]=await Promise.all([responseFor(want),operation()])
  assert.equal(response.status(),200)
  const body=await response.json();return reader(body)
 }
 const shown=async(answer,want,total,offset)=>{
  assert.equal(answer.total,String(total));assert.equal(answer.offset,offset)
  assert.deepEqual(answer.rows.map(r=>({id:r.id,number:r.number})),want)
  await ui.expect(rows()).toHaveCount(want.length)
  assert.deepEqual(await rows().evaluateAll((nodes,attribute)=>nodes.map(n=>n.getAttribute(attribute)),
   payment?'data-payment-id':'data-return-id'),want.map(r=>r.id))
  const headings=await rows().locator(':scope > h4').allTextContents()
  assert.deepEqual(headings.map((heading,i)=>heading.startsWith(want[i].number+' · ')),want.map(()=>true))
  await ui.expect(list).toContainText(`Total ${total} ${word}`)
 }
 let answer=await act({[key.offset]:0},()=>detail.getByRole('button',
  {name:payment?'Pembayaran invoice':'Retur fisik invoice',exact:true}).click())
 const all=f.oracles['SOURCE:ALL'];assert.equal(all.length,31)
 await shown(answer,all.slice(0,25),31,0)
 answer=await act({[key.offset]:25},()=>list.getByRole('button',{name:next,exact:true}).click())
 await shown(answer,all.slice(25),31,25);await ui.expect(list.getByRole('button',{name:next,exact:true})).toBeDisabled()
 const secondPageNumber=all[25].number
 answer=await act({[key.offset]:0,[key.order]:'LABEL_DESC'},()=>list.getByLabel(`Urutkan riwayat ${word} invoice`,{exact:true}).selectOption('LABEL_DESC'))
 const descending=f.oracles['LABEL_DESC:ALL'];await shown(answer,descending.slice(0,25),31,0)
 answer=await act({[key.offset]:25,[key.order]:'LABEL_DESC'},()=>list.getByRole('button',{name:next,exact:true}).click())
 await shown(answer,descending.slice(25),31,25)
 answer=await act({[key.offset]:0,[key.order]:'LABEL_DESC'},()=>list.getByRole('button',{name:previous,exact:true}).click())
 await shown(answer,descending.slice(0,25),31,0)
 answer=await act({[key.offset]:0,[key.status]:'REVERSED',[key.order]:'LABEL_DESC'},()=>list.getByLabel(`Status ${word} invoice`,{exact:true}).selectOption('REVERSED'))
 const reversed=f.oracles['LABEL_DESC:REVERSED'];assert.equal(reversed.length,30)
 await shown(answer,reversed.slice(0,25),30,0)
 answer=await act({[key.offset]:25,[key.status]:'REVERSED'},()=>list.getByRole('button',{name:next,exact:true}).click())
 await shown(answer,reversed.slice(25),30,25)
 answer=await act({[key.offset]:0,[key.status]:null},()=>list.getByLabel(`Status ${word} invoice`,{exact:true}).selectOption(''))
 await shown(answer,descending.slice(0,25),31,0)
 const search=payment?'Cari pembayaran invoice':'Cari riwayat retur invoice',submit=payment?'Cari pembayaran':'Cari riwayat retur'
 await list.getByLabel(search,{exact:true}).fill(secondPageNumber)
 answer=await act({[key.offset]:0,[key.q]:secondPageNumber},()=>list.getByRole('button',{name:submit,exact:true}).click())
 const matches=descending.filter(r=>r.number.toLowerCase().includes(secondPageNumber.toLowerCase()))
 await shown(answer,matches,matches.length,0)
 assert.ok(matches.some(r=>r.number===secondPageNumber),'SEARCH_DID_NOT_REACH_OTHER_PAGE')
 await list.getByLabel(search,{exact:true}).fill(f.tag+'-DOES-NOT-EXIST')
 answer=await act({[key.offset]:0,[key.q]:f.tag+'-DOES-NOT-EXIST'},()=>list.getByRole('button',{name:submit,exact:true}).click())
 await shown(answer,[],0,0)
 answer=await act({[key.offset]:0,[key.q]:'',[key.status]:null,[key.order]:'SOURCE'},()=>list.getByRole('button',{name:payment?'Semua pembayaran':'Semua retur',exact:true}).click())
 await shown(answer,all.slice(0,25),31,0)
 await ui.expect(list.getByLabel(search,{exact:true})).toHaveValue('')
 await ui.expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
 const screenshot=`OW09_HISTORY31_${kind}_${mobile?'MOBILE390':'DESKTOP'}.png`
 await list.screenshot({path:'cp6-proof/t3/'+screenshot})
 await panel.getByRole('button',{name:payment?'Tutup pembayaran invoice':'Tutup retur invoice',exact:true}).click()
 return {status:'PASS',kind,source_records:31,source_pages:[25,6],reversed_records:30,
  reversed_pages:[25,5],independent_Native_ID_number_order_exact:true,
  search_finds_previous_second_page:true,changed_filter_restarts_page:true,
  forward_backward_and_browse_reset:true,empty_result_zero:true,screenshot}
}

async function journey(ui,f,mobile){
 const user=await ui.login('OWNER',{label:'ow09-history31-'+mobile,mobile,
  timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'})
 const page=user.page,calls=[]
 const observe=request=>{if(request.url().includes('/rest/v1/rpc/')&&request.method()==='POST')calls.push(request.url().split('/').at(-1))}
 mkdirSync('cp6-proof/t3',{recursive:true})
 try{
  await open(ui,page);const before=fixture('state');page.on('request',observe)
  const results=[]
  for(const kind of ['payment','return'])results.push(await history(ui,page,kind,f[kind],mobile))
  assert.deepEqual(fixture('state'),before,'BROWSING_CHANGED_BUSINESS_ROWS_OR_SEQUENCE')
  const writes=calls.filter(r=>!r.startsWith('erp_cp7_get_'));assert.deepEqual(writes,[])
  return {status:'PASS',mobile,real_auth:true,synthetic_Native_fixture:true,
   actual_UI_sort_filter_search_and_pagination:true,histories:results,
   no_business_rows_sequences_changed:true,writer_RPC:0,production_go:false}
 }catch(error){
  writeFileSync(`cp6-proof/t3/OW09_HISTORY31_${mobile?'MOBILE':'DESKTOP'}_FAILURE.json`,
   JSON.stringify({error:String(error),stack:error.stack,calls,text:await page.locator('body').innerText().catch(()=> '')},null,2))
  await page.screenshot({path:`cp6-proof/t3/OW09_HISTORY31_${mobile?'MOBILE':'DESKTOP'}_FAILURE.png`,fullPage:true}).catch(()=>{})
  throw error
 }finally{page.off('request',observe);await user.context.close()}
}

export async function cases(ui,today){
 const f=fixture('prepare',{today})
 return [['OW09_INVOICE_HISTORY31_DESKTOP',()=>journey(ui,f,false)],
  ['OW09_INVOICE_HISTORY31_MOBILE390',()=>journey(ui,f,true)]]
}
