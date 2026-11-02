/* This admits isolated visual capture, never unified ERP execution. */
import fs from 'node:fs'
import crypto from 'node:crypto'
import {execFileSync} from 'node:child_process'

const manifest=JSON.parse(fs.readFileSync('docs/cp7/d17-14/ui-reference-20261103/UI_SOURCE.json','utf8'))
const git=(...args)=>execFileSync('git',args)
const pin=raw=>({bytes:raw.length,sha256:crypto.createHash('sha256').update(raw).digest('hex')})
const exact=(a,b,label)=>{if(JSON.stringify(a)!==JSON.stringify(b))throw Error(label)}
const require=(value,label)=>{if(!value)throw Error(label)}
require(manifest.contract==='cp7.isolated-owner-UI-source.v1','UI_SOURCE_CONTRACT')
require(manifest.unified_runtime_admission===false&&manifest.production_go===false,'UI_SOURCE_NOT_RUNTIME_ADMISSION')
const base=manifest.base_head
const changed=git('diff','--name-only',base,'--').toString().trim().split('\n').filter(Boolean)
exact(changed.filter(x=>!manifest.new_paths.includes(x)).sort(),Object.keys(manifest.existing_UI_derivations).sort(),'UI_SOURCE_EXACT_EXISTING_UI_CHANGES')
for(const [name,reference]of Object.entries(manifest.existing_UI_derivations)){
  const old=git('show',base+':'+name),actual=fs.readFileSync(name)
  exact(pin(old),reference.before,'UI_SOURCE_EXACT_BEFORE:'+name)
  exact(pin(actual),reference.after,'UI_SOURCE_EXACT_AFTER:'+name)
  require(name.endsWith('.css')||name==='src/main.tsx','UI_SOURCE_ONLY_STYLES_AND_IMPORT')
  if(name==='src/main.tsx')exact(actual.toString(),old.toString().replace("import './styles.css'","import './theme.css'\nimport './styles.css'"),'UI_SOURCE_MAIN_ONLY_THEME_IMPORT')
}
const basePaths=new Set(git('ls-tree','-r','--name-only',base).toString().trim().split('\n'))
const current=git('ls-files','--cached','--others','--exclude-standard','-z').toString().split('\0').filter(Boolean)
const added=[...new Set(current.filter(x=>!basePaths.has(x)))].sort()
exact(added,[...manifest.new_paths].sort(),'UI_SOURCE_EXACT_NEW_NAMESPACE')
for(const [name,reference]of Object.entries(manifest.new_files))exact(pin(fs.readFileSync(name)),reference,'UI_SOURCE_EXACT_NEW_FILE:'+name)
const checks=JSON.parse(fs.readFileSync('docs/cp7/d17-14/ui-reference-20261103/LOCAL_SOURCE_BUILD_CHECKS.json'))
require(checks.source_ownership==='PASS'&&checks.access_ownership==='PASS'&&checks.CSS_ownership==='PASS'
  &&checks.TypeScript_compile==='PASS'&&checks.Vite_build==='PASS'&&checks.client_secret_scan==='PASS','UI_SOURCE_RETAINED_ACTUAL_LOCAL_CHECKS_REQUIRED')
for(const [name,reference]of Object.entries(checks.current_UI_sources)){
  const expected=manifest.existing_UI_derivations[name]?.after??reference
  exact(pin(fs.readFileSync(name)),expected,'UI_SOURCE_CURRENT_INPUT_EXACT:'+name)
}
console.log(JSON.stringify({status:'ISOLATED_UI_SOURCE_AND_RETAINED_LOCAL_CHECK_INPUTS_EXACT_NOT_UNIFIED_RUNTIME',
  changed_existing_UI_files:Object.keys(manifest.existing_UI_derivations).length,new_files:added.length,
  actual_financial_source_changes:0,old_financial_tests_rerun:false,unified_runtime_admission:false,
  actual_UI_final_acceptance:false,production_go:false}))
