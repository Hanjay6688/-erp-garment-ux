// Controlled local source adapter, real frozen stage tables and SQL bodies.
import {readFile} from 'node:fs/promises'
import assert from 'node:assert/strict'
export const read=p=>readFile(p,'utf8')
export const block=(s,name)=>{const a=s.indexOf('create function '+name+'(');assert.ok(a>=0,name);return s.slice(a,s.indexOf('$$;',s.indexOf('as $$',a))+3)}
export async function controlledSupplyDb(){
 const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite'),db=new PGlite()
 await db.exec(`create role cp7_capture nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
  create role cp7_alert nologin;create role anon nologin;create role authenticated nologin;create role service_role nologin;
  create schema cp7_planning;create schema cp7_analysis_stage;create schema cp7_analysis_native;create schema cp7_netting_native;
  create schema cp7_fabric_native;create schema erp;create schema extensions;
  create function extensions.digest(bytea,text)returns bytea language sql immutable as $$select sha256($1)$$;
  create function cp7_netting_native.source_within(integer,integer)returns jsonb language sql stable as $$
   select '{"status":"COMPLETE","captured_at":"2026-10-23T00:00:00Z","facts":{"products":[]},"controlled_native":true}'::jsonb$$;
  create function cp7_analysis_native.material_source(jsonb,timestamptz)returns jsonb language sql stable as $$select '{}'::jsonb$$;
  create function cp7_fabric_native.source(jsonb,timestamptz)returns jsonb language sql stable as $$select '{}'::jsonb$$;
  create function erp.get_owner_financial_snapshot_v2(date,date,date)returns jsonb language sql stable as $$select '{}'::jsonb$$;
  create table cp7_analysis_native.runs(id uuid,actor uuid,request_id uuid,query jsonb,captured_at timestamptz,access_at_capture jsonb,facts jsonb,result jsonb,dependency_hash text);`)
 for(const p of['scripts/cp7-src/wip/bootstrap.sql','scripts/cp7-src/demand/bootstrap.sql','scripts/cp7_production_stage/sql/cp7_baseline__net.sql'])await db.exec(await read(p))
 await db.exec(block(await read('scripts/cp7-src/planning/bootstrap.sql'),'cp7_planning.utc'))
 const stages=await read('scripts/cp7-src/planning/analysis-stages.sql')
 await db.exec(stages.slice(stages.indexOf('create table cp7_analysis_stage.jobs('),stages.indexOf('create function cp7_analysis_stage.work_immutable(')))
 for(const name of['cp7_analysis_stage.bounds','cp7_analysis_stage.run_unit','cp7_analysis_stage.retention_days','cp7_analysis_stage.retention'])await db.exec(block(stages,name))
 const analysis=await read('scripts/cp7-src/planning/analysis.sql');await db.exec(block(analysis,'cp7_analysis_native.source_within'))
 await db.exec(`alter function cp7_analysis_stage.run_unit(cp7_analysis_stage.jobs,cp7_analysis_stage.units)owner to cp7_capture;
  alter function cp7_analysis_native.source_within(integer,integer)owner to cp7_capture;
  grant usage on schema erp,extensions,cp7_netting_native,cp7_analysis_native,cp7_analysis_stage,cp7_fabric_native,cp7_planning to cp7_capture;
  revoke all on function cp7_analysis_stage.run_unit(cp7_analysis_stage.jobs,cp7_analysis_stage.units),
  cp7_analysis_native.source_within(integer,integer)from public,anon,authenticated,service_role;
  do $$declare t record;begin for t in select c.oid::regclass name from pg_class c join pg_namespace n on n.oid=c.relnamespace
   where n.nspname='cp7_analysis_stage'and c.relkind='r'loop execute format('alter table %s owner to cp7_capture',t.name);end loop;end$$;`)
 return db
}
