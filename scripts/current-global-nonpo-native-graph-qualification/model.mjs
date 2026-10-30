/** Local in-memory PGlite structural SQL model. No Native business execution. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash}from'node:crypto';
export const here=path.dirname(fileURLToPath(import.meta.url));
export const root=path.resolve(here,'../..');
export const runtime=path.join(root,'scripts/cp7_global_nonpo_native_graph_adapter');
const modulePath=process.env.F04_PGLITE_MODULE;
if(!modulePath)throw Error('DECLARED_LOCAL_PGLITE_MODULE_REQUIRED_NO_INSTALL_OR_SERVER');
const {PGlite}=await import(pathToFileURL(modulePath).href);
export const uuid=n=>`00000000-0000-0000-0000-${String(n).padStart(12,'0')}`;
export async function setup({sqlSources={}}={}){
 const db=new PGlite();
 db.localSourcePins={};
 async function load(file){const raw=await fs.readFile(file);db.localSourcePins[path.relative(root,file)]={bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')};await db.exec(raw.toString())}
 await load(path.join(here,'model.sql'));
 await load(path.join(here,'retained/Native_authority.sql'));
 await load(path.join(here,'retained/Current_parent_readers.sql'));
 for(const file of ['authority.sql','scope.sql','capture.sql','inspect.sql'])await load(sqlSources[file]||path.join(runtime,file));
 await load(path.join(here,'seed.sql'));
 const tables=(await db.query("select n.nspname,p.relname from pg_class p join pg_namespace n on n.oid=p.relnamespace where p.relkind='r'and n.nspname in('erp','cp7_credit','cp7_note')order by 1,2")).rows;
 for(const {nspname,relname}of tables)await db.exec(`create trigger LOCAL_NO_WRITE before insert or update or delete on ${nspname}."${relname}" for each row execute function erp.LOCAL_MODEL_NO_WRITE()`);
 return db;
}
export async function snapshot(db){
 const tables=(await db.query("select n.nspname,p.relname from pg_class p join pg_namespace n on n.oid=p.relnamespace where p.relkind='r'and n.nspname in('erp','cp7_credit','cp7_note')order by 1,2")).rows;
 const result={};
 for(const {nspname,relname}of tables)result[nspname+'.'+relname]=(await db.query(`select md5(coalesce(jsonb_agg(v order by v)::text,'[]'))digest from(select to_jsonb(t)v from ${nspname}."${relname}" t)s`)).rows[0].digest;
 result.sequence=(await db.query('select last_value::text,is_called from erp.LOCAL_MODEL_NO_EFFECT_SEQUENCE')).rows[0];
 result.new_catalog=(await db.query("select p.oid::regprocedure::text,md5(pg_get_functiondef(p.oid)),p.proacl::text,pg_get_userbyid(p.proowner)from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_global_nonpo_native_graph'order by 1")).rows;
 return result;
}
export async function inspect(db,roots=[uuid(1)]){
 return(await db.query('select cp7_global_nonpo_native_graph.inspect_v1($1::uuid[])result',[roots])).rows[0].result;
}
