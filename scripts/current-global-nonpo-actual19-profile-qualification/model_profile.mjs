/** Explicit local SQL standins. No business Native, Auth or lock qualification. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import * as original from '../current-global-nonpo-native-graph-qualification/model.mjs?actual19-original-model';
export const {here,root,runtime,uuid,snapshot,inspect}=original;
const own=path.dirname(fileURLToPath(import.meta.url));
const ident=s=>'"'+s.replaceAll('"','""')+'"';
const role=s=>s==='PUBLIC'?'PUBLIC':ident(s);

export async function setup(options={}){
 const db=await original.setup(options);
 try{
  const captured=JSON.parse(await fs.readFile(path.join(own,'CAPTURE.json'),'utf8'));
  const two=await fs.readFile(path.join(own,'ACTUAL_TWO_FUNCTIONS.sql'));
  await db.exec(two.toString());
  for(const name of ['cp7_finance_read','cp7_credit_write'])await db.exec('create role '+ident(name));
  const cleared='PUBLIC,anon,authenticated,service_role,cp7_finance_read,cp7_credit_write';
  for(const [signature,row]of Object.entries(captured.functions)){
   if(!/^(erp|cp7_credit)\.[a-z0-9_]+\([a-z,]*\)$/.test(signature))throw Error('ACTUAL19_MODEL_FINITE_SIGNATURE_REQUIRED');
   await db.exec('revoke all on function '+signature+' from '+cleared);
   for(const [grantee,grantor,privilege,grantable]of row[18]){
    if(grantor!=='postgres'||privilege!=='EXECUTE'||grantable!==false)throw Error('ACTUAL19_MODEL_UNDECLARED_FUNCTION_ACL');
    await db.exec('grant execute on function '+signature+' to '+role(grantee));
   }
  }
  await db.exec('revoke all on erp.v_current_hpp from '+cleared);
  for(const [grantee,grantor,privilege,grantable]of captured.view_relation[12]){
   if(grantor!=='postgres'||grantable!==false||!['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER','MAINTAIN'].includes(privilege))throw Error('ACTUAL19_MODEL_UNDECLARED_VIEW_ACL');
   await db.exec('grant '+privilege+' on erp.v_current_hpp to '+role(grantee));
  }
  db.localSourcePins[path.relative(root,path.join(own,'ACTUAL_TWO_FUNCTIONS.sql'))]={bytes:two.length,sha256:createHash('sha256').update(two).digest('hex')};
  db.actual19LocalStandins={classification:'DECLARED_LOCAL_SOURCE_AND_EXPANDED_ACL_MODELS_ONLY',
   extra_role_standins:['cp7_finance_read','cp7_credit_write'],two_captured_definitions_installed_as_model_source:true,
   full_ERP_tables_FKs_RLS_roles_and_Native_writers:false,actual_Native_credit:0};
  return db;
 }catch(error){await db.close();throw error}
}
