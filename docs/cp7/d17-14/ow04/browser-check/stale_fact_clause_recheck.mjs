// Fixed local DOM controls of the exact exported browser assertion.
// No product UI, Playwright browser, Auth, HTTP or database is started.
import assert from 'node:assert/strict'
import {readFileSync,writeFileSync} from 'node:fs'
import {resolve} from 'node:path'
import {pathToFileURL} from 'node:url'
import {createHash} from 'node:crypto'
import {JSDOM} from 'jsdom'
assert.equal(process.argv.length,4,'Usage: node stale_fact_clause_recheck.mjs SOURCE_BROWSER_CASES OUTPUT_JSON')
const source=resolve(process.argv[2]),out=resolve(process.argv[3])
const placeholder='<h2>Rincian invoice</h2><p>Pilih invoice untuk memeriksa barang dan pembayaran yang tercatat.</p>'
const aside=body=>'<aside aria-label="Rincian invoice">'+body+'</aside>'
const list=body=>'<section aria-label="Daftar invoice">'+body+'</section>'
const controls=[
 {name:'exact_empty_shell_and_empty_list',expected:'ACCEPT',html:aside(placeholder)+list('')},
 {name:'old_invoice_facts_without_placeholder',expected:'REFUSE',html:aside('<h2>NOTE-OLD</h2><p>Pelunasan efektif invoice Rp1000</p>')+list('')},
 {name:'placeholder_plus_old_financial_text',expected:'REFUSE',html:aside(placeholder+'<p>Pelunasan efektif invoice Rp1000</p>')+list('')},
 {name:'placeholder_plus_empty_financial_container',expected:'REFUSE',html:aside(placeholder+'<div aria-label="Nilai invoice"></div>')+list('')},
 {name:'placeholder_plus_empty_item_container',expected:'REFUSE',html:aside(placeholder+'<article class="cproc-item"></article>')+list('')},
 ...['button','input','select','textarea'].map(tag=>({name:'placeholder_plus_'+tag,expected:'REFUSE',html:aside(placeholder+'<'+tag+'></'+tag+'>')+list('')})),
 {name:'placeholder_plus_stale_source_list',expected:'REFUSE',html:aside(placeholder)+list('<button class="cproc-receipt">NOTE-OLD</button>')},
 {name:'placeholder_but_return_form_open',expected:'REFUSE',html:aside(placeholder)+list('')+'<section aria-label="Retur fisik invoice"></section>'},
 {name:'placeholder_but_settlement_form_open',expected:'REFUSE',html:aside(placeholder)+list('')+'<section aria-label="Penyelesaian nilai retur"></section>'},
 {name:'missing_detail_shell_not_validated',expected:'REFUSE',html:list('')},
 {name:'duplicate_detail_shell',expected:'REFUSE',html:aside(placeholder)+aside(placeholder)+list('')},
 {name:'placeholder_plus_hidden_stale_financial_text',expected:'REFUSE',html:aside(placeholder+'<p hidden>Pelunasan efektif invoice Rp1000</p>')+list('')},
]
const {assertNoStaleInvoiceFacts}=await import(pathToFileURL(source).href)
const results=[]
for(const control of controls){
 const dom=new JSDOM(control.html),document=dom.window.document
 const locator=nodes=>({nodes,locator:selector=>locator(nodes.flatMap(n=>[...n.querySelectorAll(selector)]))})
 const page={getByRole:(role,{name,exact})=>{
  assert.equal(exact,true);assert.ok(['complementary','region'].includes(role))
  const tag=role==='complementary'?'aside':'section'
  return locator([...document.querySelectorAll(tag+'[aria-label]')].filter(n=>n.getAttribute('aria-label')===name))
 }}
 const ui={expect:l=>({toHaveCount:async n=>assert.equal(l.nodes.length,n),toHaveText:async pattern=>{
  assert.equal(l.nodes.length,1);assert.match(l.nodes[0].textContent.replace(/\s+/g,' ').trim(),pattern)
 }})}
 let observed,error
 try{await assertNoStaleInvoiceFacts(ui,page);observed='ACCEPT'}catch(e){observed='REFUSE';error=String(e.message)}
 results.push({name:control.name,expected:control.expected,observed,agrees:observed===control.expected,...(error?{error}:{})})
 dom.window.close()
}
assert.equal(results.length,15);assert.ok(results.every(r=>r.agrees))
const report={classification:'LOCAL_JSDOM_EXACT_EXPORTED_ASSERTION_CONTROLS_NOT_PRODUCT_BROWSER_RUNTIME',
 source_sha256:createHash('sha256').update(readFileSync(source)).digest('hex'),
 controls_declared_before_execution:controls,results,status:'PASS',real_Auth_DB_browser:false}
writeFileSync(out,JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify({status:report.status,controls:results.length,source_sha256:report.source_sha256,real_Auth_DB_browser:false}))
