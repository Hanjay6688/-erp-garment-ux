// Auditor-owned boundary oracle; no product tests or expectations imported.
const {buildSync}=require('esbuild');const fs=require('fs'),os=require('os'),path=require('path'),assert=require('assert/strict');
const dir=fs.mkdtempSync(path.join(os.tmpdir(),'sku-own-'));
function subject(file){const out=path.join(dir,path.basename(file)+'.cjs');buildSync({entryPoints:[file],bundle:true,platform:'node',format:'cjs',outfile:out,logLevel:'silent'});return require(out)}
const {distributeDozensEvenly:f}=subject('src/sales/distributeDozensEvenly.ts');
const {alignSizeQuantities:g}=subject('src/sizeQuantities.ts');const results=[];
function test(id,input,fn){try{fn();results.push({id,input,status:'PASS'})}catch(e){results.push({id,input,status:'FAIL',error:e.message})}}
for(const count of [1,2,3,4,5,6])for(const pieces of [0,12,24,60,120])test(`SKU.Q.${count}.${pieces}`,{dozens:pieces/12,count},()=>{const actual=f(pieces/12,count);assert.deepEqual(actual,pieces%count===0?Array(count).fill(pieces/count):null);if(actual)assert.equal(actual.reduce((a,b)=>a+b,0),pieces)});
for(const [value,count] of [[-1,3],[0.1,3],[NaN,3],[Infinity,3],[1,0],[1,-1],[1,1.5],[Number.MAX_SAFE_INTEGER,3]])test('SKU.Q.INVALID.'+results.length,{value:String(value),count},()=>assert.equal(f(value,count),null));
test('SKU.Q.OLD3',{dozens:1},()=>assert.deepEqual(f(1),[4,4,4]));
test('SKU.Q.ALIGN',{sizes:['33','31','32'],qty:[3,5,8]},()=>assert.deepEqual(g(['33','31','32'],[3,5,8],['31','32','33','34']),[5,8,3,0]));
for(const [a,b,c] of [[['31'],[0],['32']],[['31','32'],[0,8],['32','33']]])test('SKU.Q.ZERO.'+results.length,{a,b,c},()=>assert.deepEqual(g(a,b,c),c.map(x=>x==='32'?8*(a.length===2):0)));
for(const [a,b,c] of [[['31'],[5],['32']],[['31','31'],[2,3],['31']],[['31'],[2],['31','31']],[['31'],[2.5],['31']],[['31'],[-1],['31']],[['31','32'],[2],['31']]])test('SKU.Q.REFUSE.'+results.length,{a,b,c},()=>assert.throws(()=>g(a,b,c)));
fs.mkdirSync('audit-results',{recursive:true});fs.writeFileSync('audit-results/sku-quantity-results.json',JSON.stringify({candidate:'23e9c9830c32dce10604c43d17e4476d2707b55d',layer:'Own pure-function tests; not browser acceptance',results},null,2));fs.rmSync(dir,{recursive:true});console.log(JSON.stringify({pass:results.filter(x=>x.status==='PASS').length,fail:results.filter(x=>x.status!=='PASS')}));
