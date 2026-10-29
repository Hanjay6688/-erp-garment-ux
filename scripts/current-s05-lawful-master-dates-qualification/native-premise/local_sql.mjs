// Exact declared Native source on explicit table/Auth/helper doubles.
// In-process PGlite only. Zero qualified Native/financial/real-Auth cases.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
const here=path.dirname(fileURLToPath(import.meta.url));
const {PGlite}=await import(pathToFileURL(process.argv[2]).href);
const db=new PGlite();
const output={classification:'LOCAL_EXACT_SQL_SOURCE_ON_DECLARED_DOUBLES_NOT_NATIVE_QUALIFICATION',Native_executions:0,financial_Native_cases:0,real_Auth:0,cases:[],source_hashes:{}};
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
try{
 await db.exec(fs.readFileSync(path.join(here,'doubles.sql'),'utf8'));
 for(const name of ['accessory_bom_last_committed_at','save_accessory_bom_edit','guard_used_accessory_bom_item','guard_used_accessory_bom_version','bf_guard_economic_v1','bf_save_groups_v1']){
  const raw=fs.readFileSync(path.join(here,name+'.sql'));output.source_hashes[name]=sha(raw);await db.exec(raw.toString());
 }
 await db.exec(`create trigger used_item before update or delete on erp.accessory_bom_items for each row execute function erp.guard_used_accessory_bom_item();
 create trigger used_version before update or delete on erp.accessory_bom_versions for each row execute function erp.guard_used_accessory_bom_version();
 create trigger bf_shared_bom before insert or update or delete on erp.accessory_bom_versions for each row execute function erp.bf_guard_economic_v1();
 create trigger bf_shared_item before insert or update or delete on erp.accessory_bom_items for each row execute function erp.bf_guard_economic_v1();`);
 const product='10000000-0000-4000-8000-000000000001',bom='20000000-0000-4000-8000-000000000001',category='30000000-0000-4000-8000-000000000001';
 await db.query(`insert into erp.products values($1,$1,'40000000-0000-4000-8000-000000000001','50000000-0000-4000-8000-000000000001','BLUE','SKU-ONE')`,[product]);
 await db.query(`insert into erp.accessory_bom_versions(id,product_id,version_label,effective_from,notes)values($1,$2,'CP6-E-EMPTY','2026-01-01','Explicit empty BOM')`,[bom,product]);
 const tables=['products','accessory_bom_versions','accessory_bom_items','po_accessory_bom_commitments','fg_accessory_cost_snapshots','audit_logs','bf_context_v1','bf_skus_v1','bf_sku_versions_v1','bf_sku_members_v1','local_ledger_double','local_stock_double'];
 async function snapshot(){const x={};for(const t of tables)x[t]=(await db.query(`select coalesce(jsonb_agg(to_jsonb(t)order by to_jsonb(t)::text),'[]'::jsonb)as v from erp.${t} t`)).rows[0].v;x.sequence=(await db.query('select last_value::text,is_called from erp.audit_logs_id_seq')).rows;return x;}
 async function refused(name,sql,args,needle){const before=await snapshot();let failure;try{await db.transaction(async tx=>{await tx.query(sql,args);});}catch(e){failure={message:e.message,code:e.code};}assert.ok(failure,name+' must refuse');assert.equal(failure.code,'P0001');assert.ok(failure.message.includes(needle),JSON.stringify(failure));assert.deepEqual(await snapshot(),before);output.cases.push({id:name,status:'PASS',actual_SQL_refusal:failure,all_declared_rows_and_sequence_unchanged:true});}
 await refused('RETAINED_BF_HISTORICAL_NEW_MASTER_REFUSES',`select erp.bf_save_groups_v1($1::jsonb,$2)`,[JSON.stringify({effective_from:'2026-01-01T00:00:00+07:00',reason:'actual old Native date predicate',groups:[]}),crypto.randomUUID()],'BF_HISTORY: master baru hanya mulai sekarang atau mendatang');
 const initial=(await db.query('select *from erp.accessory_bom_versions where id=$1',[bom])).rows[0];
 const items=[{category_id:category,qty_per_good_fg_base:'0.5',hpp_method:'BOM_STANDARD',hpp_standard_rate:'2',hpp_uom_code:'PCS',reimbursement_rate:'2',reimbursement_uom_code:'PCS'}];
 let result=await db.query('select erp.save_accessory_bom_edit($1,$2::jsonb,null,$3)::text as id',[bom,JSON.stringify(items),'S05 unused master Native edit']);
 assert.equal(result.rows[0].id,bom);assert.deepEqual((await db.query('select id,product_id,effective_from,effective_to,is_active from erp.accessory_bom_versions where id=$1',[bom])).rows[0],Object.fromEntries(['id','product_id','effective_from','effective_to','is_active'].map(k=>[k,initial[k]])));
 const actual=(await db.query('select *from erp.accessory_bom_items where bom_version_id=$1',[bom])).rows;assert.equal(actual.length,1);assert.equal(actual[0].qty_per_good_fg_base,'0.500000');assert.equal(actual[0].hpp_standard_rate,'2.000000');
 assert.deepEqual((await db.query('select *from erp.local_ledger_double')).rows,[{id:1,amount:'42.31'}]);assert.deepEqual((await db.query('select *from erp.local_stock_double')).rows,[{id:1,qty:7}]);output.cases.push({id:'UNUSED_NATIVE_EDITOR_SAME_MASTER_WINDOW_EXACT_ITEMS',status:'PASS',Native_or_financial_qualification:false});
 await db.query(`insert into erp.po_accessory_bom_commitments(bom_version_id,product_id,committed_at)values($1,$2,'2026-01-02')`,[bom,product]);
 await db.query(`insert into erp.fg_accessory_cost_snapshots(bom_version_id,bom_item_id,costing_basis_at)values($1,$2,'2026-01-02')`,[bom,actual[0].id]);
 await refused('USED_EDITOR_OLD_EFFECTIVE_DATE_REFUSED',`select erp.save_accessory_bom_edit($1,$2::jsonb,'2026-01-01',$3)`,[bom,JSON.stringify(items),'too early'],'Tanggal mulai BOM baru harus setelah');
 await refused('USED_ITEM_DIRECT_MUTATION_REFUSED',`update erp.accessory_bom_items set qty_per_good_fg_base=3 where id=$1`,[actual[0].id],'financially committed');
 await refused('USED_VERSION_IDENTITY_MUTATION_REFUSED',`update erp.accessory_bom_versions set effective_from='2025-01-01'where id=$1`,[bom],'identity/start/active flag is immutable');
 await refused('USED_VERSION_CLOSE_AT_COMMITMENT_REFUSED',`update erp.accessory_bom_versions set effective_to='2026-01-02'where id=$1`,[bom],'effective_to cannot precede/equal');
 const oldItem=(await db.query('select *from erp.accessory_bom_items where id=$1',[actual[0].id])).rows[0];
 result=await db.query('select erp.save_accessory_bom_edit($1,$2::jsonb,statement_timestamp(),$3)::text as id',[bom,JSON.stringify([{...items[0],qty_per_good_fg_base:'3',hpp_standard_rate:'9',reimbursement_rate:'9'}]),'legitimate used master successor']);assert.notEqual(result.rows[0].id,bom);assert.deepEqual((await db.query('select *from erp.accessory_bom_items where id=$1',[oldItem.id])).rows[0],oldItem);output.cases.push({id:'USED_NATIVE_EDITOR_CREATES_SUCCESSOR_PRESERVES_OLD_ITEM',status:'PASS',no_clock_override:true});
 const sharedBom=crypto.randomUUID(),sharedProduct=crypto.randomUUID(),sku=crypto.randomUUID(),version=crypto.randomUUID();
 await db.query(`insert into erp.products values($1,$1,'40000000-0000-4000-8000-000000000001','50000000-0000-4000-8000-000000000001','RED','SKU-TWO')`,[sharedProduct]);await db.query(`insert into erp.accessory_bom_versions(id,product_id,effective_from)values($1,$2,'2026-01-01')`,[sharedBom,sharedProduct]);await db.query(`insert into erp.bf_sku_members_v1(version_id,product_root,bom_version_id)values($1,$2,$3)`,[version,sharedProduct,sharedBom]);
 await refused('SHARED_MASTER_NATIVE_EDITOR_STILL_REFUSED',`select erp.save_accessory_bom_edit($1,$2::jsonb,null,$3)`,[sharedBom,JSON.stringify(items),'foreign shared route'],'BF_SHARED_MASTER');
 assert.equal(output.cases.length,8);output.status='PASS';
}catch(error){output.status='FAIL';output.first_failure={name:error.name,message:error.message,stack:error.stack};process.exitCode=1;}
finally{await db.close();console.log(JSON.stringify(output,null,2));}
