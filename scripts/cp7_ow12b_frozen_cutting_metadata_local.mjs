import {mkdir,writeFile} from 'node:fs/promises'
import {beginLocalStageAudit} from './cp7_local_stage_audit.mjs'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite'),db=new PGlite()
for(const schema of ['erp','cp7_plan_native','cp7_cutting_checked'])await db.exec('create schema '+schema)
const tables=['erp.material_stock_movements','erp.fg_stock_movements','erp.journal_entries','erp.journal_lines','erp.materials','erp.cutting_groups','cp7_plan_native.drafts','cp7_plan_native.staged_drafts','cp7_plan_native.intents','cp7_plan_native.commands','cp7_cutting_checked.receipts']
for(const table of tables)await db.exec(`create table ${table}(id uuid,recorded_at timestamptz,amount numeric);insert into ${table} values('11111111-1111-4111-8111-111111111111','2026-10-26T00:00:00.123456Z',1)`)
const audit=await beginLocalStageAudit(db,'cutting-metadata','scripts/cp7_ow12b_frozen_cutting_metadata_local.py')
const r=await audit.afterUse();console.log(JSON.stringify(r));await mkdir('cp6-proof/t3',{recursive:true});await writeFile('cp6-proof/t3/FROZEN_CUTTING_METADATA_LOCAL.json',JSON.stringify(r)+'\n');await db.close()
