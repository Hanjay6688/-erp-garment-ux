import fs from 'node:fs'
import crypto from 'node:crypto'
import {execFileSync} from 'node:child_process'
import {gunzipSync} from 'node:zlib'
const file='docs/cp7/d17-14/ui-b-refusal-browser-20261104/SOURCE_V2.json',m=JSON.parse(fs.readFileSync(file))
const git=(...a)=>execFileSync('git',a),pin=b=>({bytes:b.length,sha256:crypto.createHash('sha256').update(b).digest('hex')})
const equal=(a,b,label)=>{if(JSON.stringify(a)!==JSON.stringify(b))throw Error(label)}
const require=(ok,label)=>{if(!ok)throw Error(label)}
require(m.base==='f801eba47ef38fbf43999b124149b40b66ef0b5a'&&m.production_go===false,'SUCCESSOR_SCOPE')
const changed=git('diff','--name-only',m.base,'--','src').toString().trim().split('\n').filter(Boolean).sort()
equal(changed,Object.keys(m.UI_changes).sort(),'ONLY_CAPTION_LAYOUT_CHANGES')
for(const[p,refs]of Object.entries(m.UI_changes)){
 const before=git('show',m.base+':'+p),after=fs.readFileSync(p);equal(pin(before),refs.before,'BEFORE:'+p);equal(pin(after),refs.after,'AFTER:'+p)
 if(p.endsWith('.tsx')){const marker='  return <section className="initial-import">';equal(before.toString().split(marker)[0],after.toString().split(marker)[0],'ALL_CONTROLLERS_PARSERS_RPC_PERMISSION_AND_RECOVERY_UNCHANGED')}
 if(p.endsWith('.css'))require(after.subarray(0,before.length).equals(before),'CSS_PREDECESSOR_PREFIX_UNCHANGED')
}
for(const[p,ref]of Object.entries(m.new_files))equal(pin(fs.readFileSync(p)),ref,'OWN_FILE_PIN:'+p)
for(const[p,ref]of Object.entries(m.deleted_files)){require(!fs.existsSync(p),'DIAGNOSTIC_MUST_BE_RETIRED');equal(pin(git('show',m.base+':'+p)),ref,'RETIRED_DIAGNOSTIC_SOURCE_PIN')}
for(const p of git('diff','--name-only',m.base).toString().trim().split('\n').filter(Boolean))require(p===file||p in m.UI_changes||p in m.new_files||p in m.deleted_files,'UNDECLARED_CHANGE:'+p)
const tests=JSON.parse(gunzipSync(fs.readFileSync('docs/cp7/d17-14/ui-b-refusal-browser-20261104/CAPTION_FIX54_FIRST.json.gz')))
require(tests.numPassedTests===54&&tests.numFailedTests===0&&tests.success,'FRESH_LOCAL54')
const transport=JSON.parse(gunzipSync(fs.readFileSync('docs/cp7/d17-14/ui-b-refusal-browser-20261104/RETAINED_C3_TRANSPORT5.json.gz')))
require(transport.numPassedTests===5&&transport.numFailedTests===0,'RETAINED_C3_TRANSPORT5')
console.log(JSON.stringify({status:'B_CAPTION_SUCCESSOR_SOURCE_ADMITTED_NOT_BACKEND_ACCEPTANCE',UI_delta_files:changed.length,local54:'PASS_CURRENT_PRODUCT',transport5:'RETAINED_UNCHANGED_TRANSPORT_FROM_C3',actual_Auth:0,actual_SQL:0,production_go:false}))
