// Local PGlite declared doubles only; preserve all eight frozen SQL assertions.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
const here=path.dirname(fileURLToPath(import.meta.url));
const old=path.resolve(here,'../current-s05-lawful-master-dates-qualification/native-premise');
const raw=fs.readFileSync(path.join(old,'local_sql.mjs'),'utf8');
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
assert.equal(sha(raw),'fed829315de67b0a34fd7d956da040bc450e27698c5ac44a09c8bb7ffa5e4062');
const replacements=[
 ["const here=path.dirname(fileURLToPath(import.meta.url));",'const here='+JSON.stringify(old)+';'],
 ["const raw=fs.readFileSync(path.join(here,name+'.sql'));", "const raw=fs.readFileSync(name==='save_accessory_bom_edit'?"+JSON.stringify(path.join(here,'CURRENT_AC_EDITOR_DEFINITION.sql'))+":path.join(here,name+'.sql'));"],
 [" const initial=(await db.query('select *from erp.accessory_bom_versions where id=$1',[bom])).rows[0];", ` const abi=(await db.query("select encode(sha256(convert_to(prosrc,'UTF8')),'hex')as digest from pg_proc where oid='erp.save_accessory_bom_edit(uuid,jsonb,timestamptz,text)'::regprocedure")).rows[0].digest;
 assert.equal(abi,'3f468d69475ebd199c7a0af7b4ee4486e6b71a5287a0ee63ac0e3dac24f15364');
 assert.notEqual(abi,'6c8c701395ab74874e7cb2f3e78f9912f7380a5a3199cba069b1aec6db09cd85');
 output.current_editor_ABI_controls={classification:'LOCAL_SQL_CURRENT_AC_ON_DECLARED_DOUBLES_NOT_NATIVE_CAPTURE',old_guard_expected_refusal:'S05_EXACT_NATIVE_LEGACY_EDITOR_BODY_REQUIRED',old_hash:'6c8c701395ab74874e7cb2f3e78f9912f7380a5a3199cba069b1aec6db09cd85',observed_local_AC_hash:abi,Native_credit:0};
 const initial=(await db.query('select *from erp.accessory_bom_versions where id=$1',[bom])).rows[0];`],
];
let code=raw;
for(const [before,after]of replacements){assert.equal(code.split(before).length-1,1);code=code.replace(before,after);}
assert.ok(code.includes('assert.equal(output.cases.length,8)'));
await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'));
