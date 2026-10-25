// Exercise the actual timeout-calibration control flow against PostgreSQL.
// The command and identity are controlled. This is not a latency benchmark.
import {mkdir,writeFile} from 'node:fs/promises'
import {beginLocalStageAudit} from './cp7_local_stage_audit.mjs'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite'),db=new PGlite()
await db.exec('create schema erp;create schema cp7_product_analog_choice;create schema local_choice;')
for(const table of ['erp.material_stock_movements','erp.fg_stock_movements','erp.journal_entries','erp.journal_lines','erp.materials'])await db.exec(`create table ${table}(id uuid,amount numeric);insert into ${table} values('11111111-1111-4111-8111-111111111111',1)`)
for(const table of ['choices','commands'])await db.exec('create table cp7_product_analog_choice.'+table+'(request_id uuid,payload jsonb)')
await db.exec(`create function local_choice.command(p jsonb,k uuid)returns jsonb language plpgsql as $$begin
 insert into cp7_product_analog_choice.choices values(k,p);insert into cp7_product_analog_choice.commands values(k,p);
 update erp.fg_stock_movements set amount=amount+1;
 if current_setting('track_functions')='all'or current_setting('local_choice.always_fail',true)='yes'then
  raise exception using errcode='57014',message='LOCAL_CONTROLLED_57014';end if;
 return jsonb_build_object('contract_version','cp7.product-analog-choice-outcome.v2');end$$;`)
const audit=await beginLocalStageAudit(db,'choice-calibration','scripts/cp7_ow12b_frozen_choice_calibration_local.py'),r=await audit.afterUse()
await mkdir('cp6-proof/t3',{recursive:true});await writeFile('cp6-proof/t3/FROZEN_CHOICE_CALIBRATION_LOCAL.json',JSON.stringify(r,null,2)+'\n');console.log(JSON.stringify(r));await db.close()
