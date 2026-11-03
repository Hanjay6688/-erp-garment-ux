import fs from 'node:fs'
import crypto from 'node:crypto'
import {execFileSync} from 'node:child_process'
const file='docs/cp7/d17-14/ui-b-refusal-browser-20261104/SOURCE.json',m=JSON.parse(fs.readFileSync(file))
const git=(...a)=>execFileSync('git',a),pin=b=>({bytes:b.length,sha256:crypto.createHash('sha256').update(b).digest('hex')})
const equal=(a,b,label)=>{if(JSON.stringify(a)!==JSON.stringify(b))throw Error(label)}
const require=(ok,label)=>{if(!ok)throw Error(label)}
require(m.base==='e1eab85d271d0a6c888162e195ddb08169d1bdb6'&&m.production_go===false,'B_BROWSER_SOURCE_SCOPE')
const paths=git('diff','--name-only',m.base,'--','src').toString().trim().split('\n').filter(Boolean).sort()
equal(paths,Object.keys(m.UI_changes).sort(),'ONLY_THREE_DECLARED_UI_FILES')
const tested=JSON.parse(fs.readFileSync('docs/cp7/d17-14/ui-b-source-refusal-20261103/COMBINED_PROPOSAL_CHECK.json'))
for(const[p,refs]of Object.entries(m.UI_changes)){
 const before=git('show',m.base+':'+p),after=fs.readFileSync(p);equal(pin(before),refs.before,'BEFORE:'+p);equal(pin(after),refs.after,'AFTER:'+p)
 equal(refs.after.sha256,tested.source[p].after_sha256,'EXACT_RETAINED_LOCAL54_PRODUCT_BYTES:'+p)
 if(p.endsWith('ConnectedPocketFabricPage.tsx')){const a=before.toString(),b=after.toString(),start='  const handlers: ProductionMutationHandlers = {',end='  return <section className="initial-import">';equal(a.slice(0,a.indexOf('function PocketWorkspace()')),b.slice(0,b.indexOf('function PocketWorkspace()')),'POCKET_PARSERS_UNCHANGED');equal(a.slice(a.indexOf(start),a.indexOf(end)),b.slice(b.indexOf(start),b.indexOf(end)),'WRITERS_PAYLOADS_GUARDS_RECOVERY_UNCHANGED')}
 if(p.endsWith('ConnectedInitialImportPage.tsx')){const marker='  return <section className="initial-import">';equal(before.toString().split(marker)[0],after.toString().split(marker)[0],'IMPORT_CONTROLLER_UNCHANGED')}
}
for(const[p,ref]of Object.entries(m.new_files))equal(pin(fs.readFileSync(p)),ref,'OWN_FILE_PIN:'+p)
for(const p of git('diff','--name-only',m.base).toString().trim().split('\n').filter(Boolean))require(p===file||p in m.UI_changes||p in m.new_files,'UNDECLARED_CHANGE:'+p)
console.log(JSON.stringify({status:'B_UI_SOURCE_ADMITTED_NOT_BACKEND_ACCEPTANCE',product_files:paths.length,retained_local_unique_tests:54,new_browser_cases_expected:28,new_screenshots_expected:60,actual_Auth:0,actual_SQL:0,production_go:false}))
