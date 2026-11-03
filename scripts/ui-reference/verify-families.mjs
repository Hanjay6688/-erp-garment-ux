/* B UI admission is separate from immutable A receipts and ERP runtime acceptance. */
import fs from 'node:fs'
import crypto from 'node:crypto'
import { execFileSync } from 'node:child_process'
const manifest=JSON.parse(fs.readFileSync('docs/cp7/d17-14/ui-b-families-20261103/B_SOURCE.json'))
const git=(...args)=>execFileSync('git',args)
const pin=raw=>({bytes:raw.length,sha256:crypto.createHash('sha256').update(raw).digest('hex')})
const exact=(a,b,label)=>{if(JSON.stringify(a)!==JSON.stringify(b))throw Error(label)}
const require=(ok,label)=>{if(!ok)throw Error(label)}
require(manifest.contract==='cp7.B.isolated-UI-successor.v1'&&manifest.production_go===false,'B_UI_SOURCE_CONTRACT')
const changed=git('diff','--name-only',manifest.base_head,'--','src').toString().trim().split('\n').filter(Boolean)
exact(changed.filter(p=>!manifest.new_runtime_paths.includes(p)).sort(),Object.keys(manifest.existing_UI_derivations).sort(),'EXACT_B_UI_EXISTING_PATHS')
for(const[name,pins]of Object.entries(manifest.existing_UI_derivations)){
  require(name.endsWith('.css')||name==='src/App.tsx','B_UI_ONLY_CSS_AND_SHELL')
  exact(pin(git('show',manifest.base_head+':'+name)),pins.before,'B_UI_PREIMAGE:'+name)
  exact(pin(fs.readFileSync(name)),pins.after,'B_UI_CURRENT:'+name)
}
for(const[name,p]of Object.entries(manifest.new_files))exact(pin(fs.readFileSync(name)),p,'B_UI_NEW_FILE:'+name)
for(const[name,p]of Object.entries(manifest.unchanged_runtime_sources)){
  exact(pin(git('show',manifest.base_head+':'+name)),p,'B_UI_EXACT_BASE_RUNTIME:'+name)
  exact(pin(fs.readFileSync(name)),p,'B_UI_NO_TRANSACTION_OR_PERMISSION_CHANGE:'+name)
}
for(const name of ['package.json','package-lock.json','src/auth/accessCatalog.ts','src/screenActivation.ts'])
  exact(fs.readFileSync(name).toString(),git('show',manifest.base_head+':'+name).toString(),'B_UI_UNCHANGED_CONTRACT:'+name)
const otherChanges=git('diff','--name-only',manifest.base_head,'--').toString().trim().split('\n').filter(Boolean)
for(const name of otherChanges)require(name in manifest.existing_UI_derivations||name in manifest.new_files||name==='docs/cp7/d17-14/ui-b-families-20261103/B_SOURCE.json','B_UI_NO_UNDECLARED_EXISTING_CHANGE:'+name)
const config=JSON.parse(fs.readFileSync('scripts/ui-reference/FAMILIES.json'))
require(config.surfaces.length===47&&new Set(config.surfaces.map(x=>x.id)).size===47,'B_UI_EXACT47_REAL_NAV_TARGETS')
exact(config.widths,[320,390,768,1440],'B_UI_FOUR_REQUIRED_WIDTHS')
const source=fs.readFileSync('src/App.tsx','utf8')
require(source.includes('canSeeNavLabel(item.navLabel) && (demoAccess || isPageAllowed(accessBundle, item.id)) && !isScreenHidden(runtime.mode, item.id))'),'B_UI_MOBILE_REUSES_ALL_CURRENT_ACCESS_GATES')
for(const command of [['node','scripts/check-source-ownership.mjs'],['node','scripts/check-access-catalog.mjs'],['node','scripts/check-css-ownership.mjs']])
  execFileSync(command[0],command.slice(1),{stdio:'inherit'})
console.log(JSON.stringify({status:'B_UI_EXACT_SOURCE_ONLY_ADMITTED_NOT_BACKEND_ACCEPTANCE',
  unchanged_runtime_sources:Object.keys(manifest.unchanged_runtime_sources).length,
  refined_existing_UI_files:Object.keys(manifest.existing_UI_derivations).length,
  real_navigation_routes:47,actual_financial_Auth_SQL_cases:0,production_go:false}))
