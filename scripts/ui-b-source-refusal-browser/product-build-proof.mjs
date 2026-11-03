import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
const out=path.resolve('../ui-refusal-product-proof')
const files=[]
function walk(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,e.name);if(e.isDirectory())walk(p);else if(/\.(js|css|html)$/.test(e.name)){const b=fs.readFileSync(p);for(const marker of ['B_REFUSAL_PROBE','__writerBUI','refusal_probe','fixture-notice'])if(b.includes(marker))throw Error('TEST_FIXTURE_IN_PRODUCT_BUILD:'+p+':'+marker);files.push({name:p,bytes:b.length,sha256:crypto.createHash('sha256').update(b).digest('hex')})}}}
walk('dist');if(files.length===0)throw Error('NO_PRODUCT_BUILD')
fs.writeFileSync(path.join(out,'BUILD_FIXTURE_ABSENCE.json'),JSON.stringify({status:'PASS',built_files:files.length,fixture_markers_absent:true,files},null,2)+'\n',{flag:'wx'})
console.log(JSON.stringify({product_build:'PASS',built_files:files.length,fixture_markers_absent:true}))
