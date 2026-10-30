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
]){
 const raw=readFileSync(resolve(ROOT,path),'utf8'),start=raw.indexOf('<label>'+label+'<select')
 assert.ok(start>=0);assert.equal(raw.indexOf('<label>'+label+'<select',start+1),-1)
 const jsx=raw.slice(start,raw.indexOf('</label>',start)+8)
 // Render the complete current product JSX, including all option branches.
 const code=transformSync('const node=('+jsx+');',{loader:'tsx',target:'es2022',jsx:'transform'}).code
 const data={pairing:{can_edit:true,current:null,options:[{id:'target',brand_name:'Brand',sku:'Target',members:[{size:'34'}]}]},
   targets:[{id:'target',brand_name:'Brand',sku:'Target',size:'34',product_name:'Target size 34',recommended:false}],
   sources:[{product_id:'source',location_id:'warehouse',brand_name:'Brand',sku:'Source',size:'31',location_name:'FG',stock:{available:9}}]}
 const node=new Function('React','data','pairTarget','locked','source','target','selected',code+'return node;')(React,data,'',false,'','',{product_id:'source'})
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
const result={status:'SOURCE_JSX_AND_INSTALLED_PLAYWRIGHT_SELECTOR_CONTROLS_PASS',
 playwright_version:'1.62.1',injected_source_sha256:hash(engine),controls:rows,
 evidence_kind:'CURRENT_SOURCE_JSX_RENDERED_OFFLINE_NOT_CAPTURED_ACTUAL_BROWSER_DOM',
 actual_browser_cases:0,actual_Native_cases:0,product_accessibility_defect_claim:false,
 production_go:false,independent_acceptance:false}
if(process.argv[2]==='--output'){assert.ok(process.argv[3]);writeFileSync(process.argv[3],JSON.stringify(result,null,2)+'\n')}
console.log(JSON.stringify({status:result.status,controls:rows.length,actual_browser_cases:0}))
