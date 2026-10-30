// Source/DOM selector controls only: no browser, Auth, HTTP or case credit.
import assert from 'node:assert/strict'
import {readFileSync,writeFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
import {createRequire} from 'node:module'
import {dirname,resolve} from 'node:path'
import {fileURLToPath} from 'node:url'
import vm from 'node:vm'

const HERE=dirname(fileURLToPath(import.meta.url)),ROOT=resolve(HERE,'../..')
const require=createRequire(resolve(process.env.SKU27_NODE_ROOT||ROOT,'package.json'))
const {JSDOM,VirtualConsole}=require('jsdom'),React=require('react'),{renderToStaticMarkup}=require('react-dom/server'),{transformSync}=require('esbuild')
const engineRoot=dirname(require.resolve('playwright-core/package.json'))
assert.equal(JSON.parse(readFileSync(resolve(engineRoot,'package.json'))).version,'1.62.1')
const bundle=readFileSync(resolve(engineRoot,'lib/coreBundle.js'),'utf8')
const literal=bundle.match(/source4 = ('(?:\\.|[^'\\])*');/s)
assert.ok(literal,'EXACT_INSTALLED_PLAYWRIGHT_INJECTED_SOURCE_REQUIRED')
const engine=vm.runInNewContext(literal[1]),hash=raw=>createHash('sha256').update(raw).digest('hex'),rows=[]

for(const[label,path]of[
 ['SKU padanan','src/ConnectedSkuMasterPage.tsx'],
 ['SKU asal dan gudang','src/ConnectedProductConversionPage.tsx'],
 ['SKU tujuan','src/ConnectedProductConversionPage.tsx'],
 ['Pengelompokan','src/NativeDemandHistoryPanel.tsx'],
]){
 const raw=readFileSync(resolve(ROOT,path),'utf8'),start=raw.indexOf('<label>'+label+'<select')
 assert.ok(start>=0);assert.equal(raw.indexOf('<label>'+label+'<select',start+1),-1)
 const jsx=raw.slice(start,raw.indexOf('</label>',start)+8)
 // Render the complete current product JSX, including all option branches.
 const code=transformSync('const node=('+jsx+');',{loader:'tsx',target:'es2022',jsx:'transform'}).code
 const data={pairing:{can_edit:true,current:null,options:[{id:'target',brand_name:'Brand',sku:'Target',members:[{size:'34'}]}]},
   targets:[{id:'target',brand_name:'Brand',sku:'Target',size:'34',product_name:'Target size 34',recommended:false}],
   sources:[{product_id:'source',location_id:'warehouse',brand_name:'Brand',sku:'Source',size:'31',location_name:'FG',stock:{available:9}}]}
 const node=new Function('React','data','pairTarget','locked','source','target','selected','basis','busy','recovery',code+'return node;')(React,data,'',false,'','',{product_id:'source'},'AS_SOLD',false,{pending:null,error:null})
 const html=renderToStaticMarkup(node),virtualConsole=new VirtualConsole(),cssWarnings=[]
 virtualConsole.on('jsdomError',error=>{assert.match(error.message,/Not implemented: window.getComputedStyle\(elt, pseudoElt\)/);cssWarnings.push(error.message)})
 const dom=new JSDOM('<section class="panel">'+html+'</section>',{runScripts:'outside-only',virtualConsole})
 const w=dom.window;w.module={exports:{}};w.eval(engine)
 const panel=w.document.querySelector('.panel'),select=panel.querySelector('select')
 const oldLabels=w.getElementLabels(new Map(),select)
 const oldMatcher=w.createTextMatcher(JSON.stringify(label)+'s',true).matcher
 assert.equal(oldLabels.some(oldMatcher),false,'ORIGINAL_EXACT_LABEL_MUST_REPRODUCE_MISMATCH')
 const role=w.createRoleEngine(true),selector='combobox[name='+JSON.stringify(label)+'s]'
 assert.equal(role.queryAll(panel,selector).length,1)
 assert.equal(role.queryAll(panel,'combobox[name='+JSON.stringify(label+' suffix')+'s]').length,0)
 assert.equal(w.getElementAccessibleNameText(select,false),label,'PRODUCT_ACCESSIBLE_NAME_IS_ALREADY_EXACT')
 const options=[...select.options].map(x=>({value:x.value,label:x.label}))
 assert.equal(options.length,2);assert.ok(options[1].value)
 select.value=options[1].value
 assert.equal(select.value,options[1].value)
 assert.equal(role.queryAll(panel,selector).length,1,'NAME_STAYS_EXACT_WHEN_SELECTION_CHANGES')
 const outside=w.document.createElement('select');outside.setAttribute('aria-label',label);w.document.body.append(outside)
 assert.equal(role.queryAll(w.document,selector).length,2)
 assert.equal(role.queryAll(panel,selector).length,1,'VISIBLE_FEATURE_PANEL_SCOPE_MUST_REMAIN')
 rows.push({label,product_source:path,product_sha256:hash(raw),exact_JSX_sha256:hash(jsx),rendered_HTML:html,
  old_exact_label_text:oldLabels.map(x=>x.normalized),old_exact_label_matches:0,
  actual_accessible_name_algorithm:label,exact_role_matches:1,wrong_name_matches:0,
  option_values:options.map(x=>x.value),selected_value_preserved:true,panel_scope_preserved:true,
  css_pseudo_layout_unavailable_in_jsdom:cssWarnings.length>0})
 w.close()
}
// Exercise the actual helper bodies against exact product JSX. These are
// offline DOM states, never posted database fixtures or browser case credit.
const current=readFileSync(resolve(HERE,'browser.mjs'),'utf8')
const retained=readFileSync(resolve(HERE,'retained_0938/browser.mjs'),'utf8')
const product=readFileSync(resolve(ROOT,'src/ConnectedProductConversionPage.tsx'),'utf8')
const failure=JSON.parse(readFileSync(resolve(HERE,'FIRST_0938_BROWSER_FAILURE.json')))
const observed=failure.mobile_display_control
assert.ok(failure.captured_mobile_text.includes(observed.source_sku+' → '+observed.target_sku))
assert.ok(failure.captured_mobile_text.includes('Batalkan '+observed.source_sku))
function render(jsx,names,values){
 const code=transformSync('const node=('+jsx+');',{loader:'tsx',target:'es2022',jsx:'transform'}).code
 return renderToStaticMarkup(new Function('React',...names,code+'return node;')(React,...values))
}
function domControls(html){
 const vc=new VirtualConsole();vc.on('jsdomError',e=>assert.match(e.message,/Not implemented: window.getComputedStyle\(elt, pseudoElt\)/))
 const dom=new JSDOM('<section>'+html+'</section>',{runScripts:'outside-only',virtualConsole:vc})
 const w=dom.window;w.module={exports:{}};w.eval(engine);const role=w.createRoleEngine(true)
 let clicked=0
 const locator=nodes=>({nodes,
  getByRole:(kind,opt={})=>locator(nodes.flatMap(n=>role.queryAll(n,kind+(opt.name===undefined?'':'[name='+JSON.stringify(opt.name)+'s]')))),
  filter:({hasText})=>locator(nodes.filter(n=>n.textContent.includes(hasText))),
  click:async()=>{assert.equal(nodes.length,1);assert.equal(nodes[0].disabled,false);clicked++},
 })
 const expect=loc=>({
  toBeVisible:async()=>assert.equal(loc.nodes.length,1),
  toBeEnabled:async()=>{assert.equal(loc.nodes.length,1);assert.equal(loc.nodes[0].disabled,false)},
  toBeDisabled:async()=>{assert.equal(loc.nodes.length,1);assert.equal(loc.nodes[0].disabled,true)},
  toHaveCount:async n=>assert.equal(loc.nodes.length,n),
  toContainText:async text=>{assert.equal(loc.nodes.length,1);assert.ok(loc.nodes[0].textContent.includes(text))},
 })
 return {dom,expect,root:()=>locator([w.document.querySelector('section')]),clicked:()=>clicked}
}
function open(text,control){
 const start=text.indexOf('async function openConversion('),end=text.indexOf('async function openInverse(',start)
 assert.ok(start>=0&&end>start)
 return new Function('menu','page','expect','conversion',text.slice(start,end)+';return openConversion;')(async()=>{},null,control.expect,control.root)
}
const sourceStart=product.indexOf('<label>SKU asal dan gudang<select')
const sourceJSX=product.slice(sourceStart,product.indexOf('</label>',sourceStart)+8)
const recoverySource=readFileSync(resolve(ROOT,'src/ProductionRecoveryNotice.tsx'),'utf8')
const recoveryCode=transformSync(recoverySource,{loader:'tsx',target:'es2022',jsx:'transform',format:'cjs'}).code
const recoveryModule={exports:{}};new Function('React','module','exports',recoveryCode)(React,recoveryModule,recoveryModule.exports)
function recoveryDOM(locked,pending,busy=false){
 const select=render(sourceJSX,['data','source','locked'],[{sources:[]},'',locked])
 const notice=renderToStaticMarkup(React.createElement(recoveryModule.exports.default,{recovery:{pending,error:pending?'Unknown result':null,busy,corruptedEnvelope:false},onReconcile:async()=>false,className:'notice'}))
 return domControls('<h1>Ganti Merek / SKU</h1>'+select+notice)
}
let c=recoveryDOM(true,true)
await assert.rejects(()=>open(retained,c)(true),assert.AssertionError)
await open(current,c)(true);c.dom.window.close()
for(const [locked,pending,busy] of [[false,true,false],[true,false,false],[true,true,true]]){
 c=recoveryDOM(locked,pending,busy);await assert.rejects(()=>open(current,c)(true),assert.AssertionError);c.dom.window.close()
}
c=recoveryDOM(false,false);await open(current,c)();c.dom.window.close()
assert.ok(current.includes('await page.reload();await openConversion(true)'))
assert.ok(current.includes("await expect(conversion().getByRole('combobox',{name:'SKU asal dan gudang',exact:true})).toBeEnabled()\n  let posted = state('POSTED')"))
const tableStart=product.indexOf('<table>'),tableJSX=product.slice(tableStart,product.indexOf('</table>',tableStart)+8)
const member=observed.member
const document={...member,id:member.conversion_id,conversion_number:member.number,source_sku:observed.source_sku,target_sku:observed.target_sku,
 target_value:member.destination_value,physical_at:'2026-10-30T15:46:00Z',notes:'Captured label control',returns:[],extra_cost:'0',value_state:'FINAL'}
const table=render(tableJSX,['data','locked','canReverse','canPost','accessories','formatCp6WibDateTime','displayRupiah'],
 [{documents:[document]},false,true,true,null,x=>x,x=>x])
const f={products:{source:{sku:observed.physical_source_sku}},group_labels:{source:{sku:observed.source_sku},target:{sku:observed.target_sku}}}
function inverse(text,control,fixture=f){
 const start=text.indexOf('async function openInverse(member){'),end=text.indexOf("  await history().getByLabel('Alasan pembatalan'",start)
 assert.ok(start>=0&&end>start)
 return new Function('history','expect','f','groupSource','groupTarget',text.slice(start,end)+'};return openInverse;')(control.root,control.expect,fixture,'source','target')
}
c=domControls(table);await assert.rejects(()=>inverse(retained,c)(member),assert.AssertionError);assert.equal(c.clicked(),0)
await inverse(current,c)(member);assert.equal(c.clicked(),1)
await assert.rejects(()=>inverse(current,c)({...member,number:'wrong document'}),assert.AssertionError)
await assert.rejects(()=>inverse(current,c)({...member,number:''}),assert.AssertionError)
await assert.rejects(()=>inverse(current,c,{...f,group_labels:{...f.group_labels,target:{sku:'wrong target'}}})(member),assert.AssertionError)
c.dom.window.close()
const result={status:'SOURCE_JSX_AND_INSTALLED_PLAYWRIGHT_SELECTOR_CONTROLS_PASS',
 playwright_version:'1.62.1',injected_source_sha256:hash(engine),controls:rows,
 recovery_and_history_controls:{retained_0938_both_helpers_reproduced_red:true,actual_current_helpers_pass:true,
  pending_requires_disabled_source_and_enabled_reconcile:true,authoritative_source_enabled:true,
  exact_document_commercial_source_target_and_posted_state:true,wrong_state_and_labels_refused:true},
 evidence_kind:'CURRENT_SOURCE_JSX_RENDERED_OFFLINE_NOT_CAPTURED_ACTUAL_BROWSER_DOM',
 actual_browser_cases:0,actual_Native_cases:0,product_accessibility_defect_claim:false,
 production_go:false,independent_acceptance:false}
if(process.argv[2]==='--output'){assert.ok(process.argv[3]);writeFileSync(process.argv[3],JSON.stringify(result,null,2)+'\n')}
console.log(JSON.stringify({status:result.status,controls:rows.length,actual_browser_cases:0}))
