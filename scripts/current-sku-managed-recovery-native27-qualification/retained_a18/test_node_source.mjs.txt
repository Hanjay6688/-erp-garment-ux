// Actual old/new Node admission function bodies, no UI/RPC/DB responses.
// Positive unit controls stop at the authentic Python reader boundary.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync,writeFileSync,mkdtempSync,mkdirSync,rmSync,renameSync,symlinkSync,unlinkSync,lstatSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';

const here=dirname(fileURLToPath(import.meta.url)),ROOT=resolve(here,'../..');
const oldPath='scripts/current-sku-pair-browser-qualification/SOURCE.json';
const currentPath='scripts/current-sku-managed-recovery-native27-qualification/BROWSER_SOURCE.json';
const old=JSON.parse(readFileSync(resolve(ROOT,oldPath)));
const binding=JSON.parse(readFileSync(resolve(ROOT,currentPath)));
const text=readFileSync(resolve(here,'browser.mjs'),'utf8');
const boundary='AUTHENTIC_PYTHON_READER_BOUNDARY_NO_RESPONSE_DOUBLE';
let childCalls=0;
function run(body,root){
  const start=body.includes('function pinnedSource(')?body.indexOf('function pinnedSource('):body.indexOf('function admitted(');
  const end=body.indexOf('async function success');assert(start>=0&&end>start);
  const invoke=new Function('ROOT','IDS','assert','readFileSync','createHash','resolve','lstatSync','execFileSync',
    body.slice(start,end)+'\nreturn admitted()');
  return invoke(root,old.case_ids,assert,readFileSync,createHash,resolve,lstatSync,()=>{childCalls++;throw new Error(boundary)});
}
function reaches(root){assert.throws(()=>run(text,root),e=>e.message===boundary);}
function copied(fn){
  const root=mkdtempSync(resolve(tmpdir(),'sku27-node-source-'));
  try{
    const names=new Set([...Object.keys(old.files),...Object.keys(binding.current_files),oldPath,currentPath]);
    for(const name of names){const path=resolve(root,name);mkdirSync(dirname(path),{recursive:true});writeFileSync(path,readFileSync(resolve(ROOT,name)));}
    return fn(root);
  }finally{rmSync(root,{recursive:true,force:true});}
}

test('first frozen old reader refuses actual current product before any child/HTTP',()=>{
  const body=readFileSync(resolve(ROOT,'scripts/current-sku-pair-browser-qualification/browser.mjs'),'utf8');
  let first;try{run(body,ROOT)}catch(e){first=e;}
  assert(first);assert.match(first.message,/SKU29_BROWSER_SOURCE_CHANGED:scripts\/cp7_sku_pair_conversion\/(composition.py|conversion.sql)/);
  assert.equal(childCalls,0);
  if(process.env.SKU27_NODE_SOURCE_RECEIPT)writeFileSync(process.env.SKU27_NODE_SOURCE_RECEIPT,JSON.stringify({
    kind:'ACTUAL_FROZEN_NODE_SOURCE_GUARD_FIRST_RED',error:first.message,
    original_body_sha256:createHash('sha256').update(body).digest('hex'),
    source_HTTP_DB_or_browser_calls:0,actual_Native_cases:0,repair_scope:'SOURCE_READER_ONLY_SAME_REAL_JOURNEY_BODY'
  },null,2)+'\n');
});
test('new actual guard reaches authentic reader without a response double',()=>reaches(ROOT));
test('changed current source refuses then restored source reaches reader',()=>copied(root=>{
  const path=resolve(root,'scripts/cp7_sku_pair_conversion/recovery.sql'),raw=readFileSync(path),before=childCalls;
  writeFileSync(path,Buffer.concat([raw,Buffer.from('\n-- unexpected code\n')]));
  assert.throws(()=>run(text,root),/SKU27_CURRENT_BROWSER_RUNTIME_SOURCE_CHANGED/);assert.equal(childCalls,before);
  writeFileSync(path,raw);reaches(root);
}));
test('unknown metadata refuses then restored metadata reaches reader',()=>copied(root=>{
  const path=resolve(root,currentPath),raw=readFileSync(path),before=childCalls;
  writeFileSync(path,JSON.stringify({...JSON.parse(raw),unexpected_source_allowance:true}));
  assert.throws(()=>run(text,root),assert.AssertionError);assert.equal(childCalls,before);
  writeFileSync(path,raw);reaches(root);
}));
test('same-byte metadata symlink refuses before authentic reader',()=>copied(root=>{
  const path=resolve(root,oldPath),saved=path+'.saved',before=childCalls;
  renameSync(path,saved);symlinkSync(saved,path);
  assert.throws(()=>run(text,root),/SKU27_SOURCE_SYMLINK/);assert.equal(childCalls,before);
  unlinkSync(path);renameSync(saved,path);reaches(root);
}));
test('same-byte ancestor symlink refuses before authentic reader and restores',()=>copied(root=>{
  const folder=resolve(root,'scripts/cp7_sku_pair_conversion'),saved=folder+'-same-bytes',before=childCalls;
  renameSync(folder,saved);symlinkSync(saved,folder,'dir');
  assert.throws(()=>run(text,root),/SKU27_SOURCE_SYMLINK/);assert.equal(childCalls,before);
  unlinkSync(folder);renameSync(saved,folder);reaches(root);
}));
