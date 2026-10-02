import {execFileSync} from 'node:child_process'
const fixture=(op,payload)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p10_browser_fixture.py',op,JSON.stringify(payload)],{cwd:'../writer',encoding:'utf8'}).trim())
async function openPage(ui,p,book){
 const menu=p.getByRole('button',{name:'Buka menu',exact:true})
 await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Gudang'})).toBeAttached({timeout:20000})
 if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:`• Mutasi Barang Jadi · ${book}`,exact:true})
 if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click()
 await link.click();await ui.expect(p.getByRole('heading',{name:`Mutasi Barang Jadi · ${book}`,exact:true})).toBeVisible()
}
async function bookFlow(ui,today,mobile){
 const f=fixture('create_book',{today,ops:mobile}),user=await ui.login(mobile?'ADMIN':'OWNER',{label:'p10-book-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),book=mobile?'Widie':'Vivo'
 try{
  const p=user.page;await openPage(ui,p,book);const panel=p.locator('.cfgb')
  async function chooseSource(){
   await ui.expect(panel.getByRole('button',{name:'Muat ulang buku',exact:true})).toBeEnabled()
   const brand=panel.locator('.cfgb-filter').first();if(!await brand.getAttribute('open'))await brand.locator('summary').click()
   const clear=brand.getByRole('button',{name:'Semua merek',exact:true});if(await clear.isEnabled())await clear.click()
   await panel.getByLabel('Cari buku mutasi',{exact:true}).fill(f.sku);await panel.getByRole('button',{name:'Terapkan filter buku',exact:true}).click();await ui.expect(panel.locator('.cfgb-card')).toHaveCount(3)
   await brand.locator('summary').click()
  }
  await chooseSource()
  if(!mobile)await p.evaluate(()=>{window.__bookDragEvents=[];for(const type of ['mousedown','mousemove','mouseup','dragstart','dragenter','dragover','drop','dragend'])document.addEventListener(type,e=>{const card=e.target.closest?.('[data-movement-id]');if(card)window.__bookDragEvents.push({type,id:card.getAttribute('data-movement-id'),prevented:e.defaultPrevented})})})
  const card=id=>panel.locator(`.cfgb-card[data-movement-id="${id}"]`)
  await ui.expect(card(f.sale).locator('.cfgb-balances>div').nth(0)).toContainText('15')
  let first=null,replay=null,lost=false
  if(mobile)await p.route('**/rest/v1/rpc/erp_cp7_save_fg_book_v1',async route=>{const body=route.request().postDataJSON();if(body.p_action==='MOVE'&&!lost){first=body;const result=await route.fetch();if(result.status()!==200)throw Error('Book move must commit before dropped response');lost=true;await route.abort('failed')}else{if(body.p_action==='MOVE'&&replay===null)replay=body;await route.continue()}})
  if(mobile)await card(f.sale).getByRole('button',{name:/ke atas$/}).click()
  else {
   await ui.expect(card(f.sale)).toHaveAttribute('draggable','true')
   const grip=card(f.sale).locator('.cfgb-grip');await grip.scrollIntoViewIfNeeded();const start=await grip.boundingBox();if(!start)throw Error('Drag grip not visible')
   const x=start.x+start.width/2,y=start.y+start.height/2
   await p.mouse.move(x,y);await p.mouse.down();await p.mouse.move(x+18,y-18,{steps:5})
   // Initiate the real mouse drag before scrolling a distant destination into view.
   await card(f.first).evaluate(el=>el.scrollIntoView({block:'center'}));const target=await card(f.first).boundingBox();if(!target)throw Error('Drag target not visible')
   await p.mouse.move(target.x+target.width/2,target.y+target.height*.25,{steps:12});await p.mouse.move(target.x+target.width/2+1,target.y+target.height*.25,{steps:2});await p.mouse.up()
  }
  const movedFirst=mobile?f.first:f.sale
  try{await ui.expect.poll(()=>fixture('read_book',f).book.page.rows.map(r=>r.id),{timeout:20000}).toEqual(mobile?[f.first,f.sale,f.second]:[f.sale,f.first,f.second])}catch(e){await p.screenshot({path:`cp6-proof/t3/P10_BOOK_FAILED_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true});throw Error(String(e)+' DnD events: '+JSON.stringify(await p.evaluate(()=>window.__bookDragEvents??[])))}
  if(mobile){
   await ui.expect(panel.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await openPage(ui,p,book)
   await panel.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(panel.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0)
   if(!lost||JSON.stringify(first)!==JSON.stringify(replay))throw Error('Book recovery changed UUID/payload')
   await chooseSource()
  }
  await ui.expect(panel.locator('.cfgb-card').first()).toHaveAttribute('data-movement-id',movedFirst)
  const actual=fixture('read_book',f);if(JSON.stringify(actual.facts)!==JSON.stringify(f.facts)||JSON.stringify(actual.qty)!=='[11,0,11]')throw Error('Presentation move changed money, HPP or physical stock')
  await card(f.sale).locator('details summary').click();await ui.expect(card(f.sale).locator('.cfgb-official')).toContainText('11 PCS')
  if((await panel.innerText()).includes('Rp'))throw Error('Book should not expose monetary fields')
  await ui.expect.poll(()=>panel.evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P10_BOOK_${mobile?'MOBILE':'DESKTOP'}.png`,fullPage:true})
  const reset=panel.getByRole('button',{name:'Kembalikan seluruh urutan buku',exact:true});await ui.expect(reset).toBeDisabled()
  await panel.getByLabel('Saya ingin mengatur ulang seluruh buku FG.',{exact:true}).check();await reset.click()
  await ui.expect(panel.locator('.cfgb-card').first()).toHaveAttribute('data-movement-id',f.first)
  await ui.expect.poll(()=>fixture('read_book',f).book.page.rows.map(r=>r.id)).toEqual([f.first,f.second,f.sale])
  if(mobile){await p.route('**/rest/v1/rpc/erp_cp7_get_fg_book_v2',r=>r.abort('failed'));await panel.getByRole('button',{name:'Muat ulang buku',exact:true}).click();await ui.expect(panel.locator('.cfgb-card')).toHaveCount(0);await ui.expect(panel.getByRole('alert').first()).toBeVisible()}
  return {status:'PASS',mobile,real_auth_ui_rpc_database:true,desktop_drag:mobile?null:true,mobile_move_and_lost_reply_exact_recovery:mobile?true:null,global_reset_review:true,all_movement_facts_hpp_journals_stock_unchanged:true,failed_read_clears_cards:mobile?true:null,screenshot:`P10_BOOK_${mobile?'MOBILE':'DESKTOP'}.png`}
 }finally{await user.context.close()}
}
export function bookCases(ui,today){return [['P10_BOOK_BROWSER_DESKTOP_DRAG',()=>bookFlow(ui,today,false)],['P10_BOOK_BROWSER_MOBILE_RECOVERY',()=>bookFlow(ui,today,true)]]}
