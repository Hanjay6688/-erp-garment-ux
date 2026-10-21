// PostgreSQL RECORD descriptor control only. No ERP, Auth or financial stubs.
import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
const {PGlite}=await import(process.env.OW04_PGLITE_MODULE||'@electric-sql/pglite');
const db=new PGlite();
try{
 await db.exec(`create function old_optional_target(p_target uuid)returns jsonb language plpgsql as $$
 declare target_assignment record;
 begin
  if p_target is not null then select p_target as root_sale_id into strict target_assignment;end if;
  return jsonb_build_object('target_root_sale_id',case when p_target is not null then target_assignment.root_sale_id end);
 end $$;
 create function typed_optional_target(p_target uuid)returns jsonb language plpgsql as $$
 declare target_root uuid;
 begin
  if p_target is not null then select p_target into strict target_root;end if;
  return jsonb_build_object('target_root_sale_id',target_root);
 end $$;`);
 let failure;
 try{await db.query('select old_optional_target(null)')}catch(e){failure={code:e.code,message:e.message}}
 assert.equal(failure?.code,'55000');assert.equal(failure.message,'record "target_assignment" is not assigned yet');
 const id='11111111-1111-4111-8111-111111111111';
 const warm=(await db.query('select old_optional_target($1)as value',[id])).rows[0].value;
 assert.deepEqual(warm,{target_root_sale_id:id});
 const warmNull=(await db.query('select old_optional_target(null)as value')).rows[0].value;
 assert.deepEqual(warmNull,{target_root_sale_id:null});
 const fresh=(await db.query('select typed_optional_target(null)as value')).rows[0].value;
 assert.deepEqual(fresh,{target_root_sale_id:null});
 assert.deepEqual((await db.query('select typed_optional_target($1)as value',[id])).rows[0].value,warm);
 const report={classification:'LOCAL_POSTGRESQL_RECORD_DESCRIPTOR_CONTROL_NOT_NATIVE_OR_FINANCIAL_EXECUTION',
  status:'PASS',first_cold_null_record_failure:failure,warm_assigned_record_then_null_works:true,
  fresh_typed_null_works:true,non_null_output_identical:true,ERP_commands_executed:0,production_go:false};
 if(process.env.OW04_RECORD_CONTROL_OUTPUT)writeFileSync(process.env.OW04_RECORD_CONTROL_OUTPUT,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify(report));
}finally{await db.close()}
