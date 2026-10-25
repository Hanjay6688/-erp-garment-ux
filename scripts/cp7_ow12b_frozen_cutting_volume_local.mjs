// Actual volume-preparation helper and profile/policy functions. Identity and
// dimensional tables are controlled local fixtures; no Native/Auth credit.
import {readFile,mkdir,writeFile} from 'node:fs/promises'
import assert from 'node:assert/strict'
import {beginLocalStageAudit} from './cp7_local_stage_audit.mjs'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite'),db=new PGlite()
const block=(s,name)=>{const a=s.indexOf('create function '+name+'(');assert.ok(a>=0,name);return s.slice(a,s.indexOf('$$;',s.indexOf('as $$',a)+5)+3)}
await db.exec('create role cp7_capture;create role anon;create role authenticated;create role service_role;create schema erp;create schema auth;create schema extensions;create schema cp7_identity;create schema cp7_profile;')
for(const p of ['wip/bootstrap.sql','demand/bootstrap.sql'])await db.exec(await readFile('scripts/cp7-src/'+p,'utf8'))
await db.exec(`create function auth.uid()returns uuid language sql as $$select '11111111-1111-4111-8111-111111111111'::uuid$$;
 create function cp7_identity.access_now(boolean)returns jsonb language sql as $$select jsonb_build_object('actor',auth.uid())$$;
 create function extensions.digest(bytea,text)returns bytea language sql as $$select sha256($1)$$;
 create table erp.products(id uuid primary key,identity_root_id uuid unique,size_id uuid,sku text,product_name text,effective_from timestamptz,effective_to timestamptz);
 create table erp.bf_skus_v1(id uuid primary key,sku text,brand_id uuid,revision bigint);
 create table erp.bf_sku_versions_v1(id uuid primary key,sku_id uuid,revision bigint,effective_from timestamptz,effective_to timestamptz);
 create table erp.bf_sku_members_v1(version_id uuid,product_root uuid);
 create index on erp.bf_sku_members_v1(version_id);create index on erp.bf_sku_versions_v1(sku_id);
 insert into erp.bf_skus_v1 select md5('sku'||n)::uuid,'OW12BF36-'||n,md5('brand')::uuid,1 from generate_series(1,1200)n;
 insert into erp.bf_sku_versions_v1 select md5('version'||sku)::uuid,id,1,'2026-01-01Z',null from erp.bf_skus_v1;
 insert into erp.products select md5('product'||sku||size)::uuid,md5('root'||sku||size)::uuid,md5('size'||size)::uuid,sku||'-'||size,'Synthetic local only','2026-01-01Z',null from erp.bf_skus_v1 cross join generate_series(1,3)size;
 insert into erp.bf_sku_members_v1 select v.id,p.identity_root_id from erp.bf_skus_v1 s join erp.bf_sku_versions_v1 v on v.sku_id=s.id join erp.products p on p.sku like s.sku||'-%';
 insert into erp.products values('22222222-2222-4222-8222-222222222222','33333333-3333-4333-8333-333333333333',md5('size1')::uuid,'ORIGINAL-LOCAL','Original local','2026-01-01Z',null);`)
const profile=await readFile('scripts/cp7-src/planning/profile.sql','utf8'),identity=await readFile('scripts/cp7-src/identity/bootstrap.sql','utf8')
for(const [source,tables]of [[profile,['cp7_profile.profiles','cp7_profile.commands']],[identity,['cp7_identity.production_policy','cp7_identity.commands']]])for(const table of tables){const a=source.indexOf('create table '+table);assert.ok(a>=0);await db.exec(source.slice(a,source.indexOf(';',a)+1))}
for(const name of ['source','workspace'])await db.exec(block(profile,'cp7_profile.'+name))
await db.exec(await readFile('scripts/cp7_target_policy_stage/sql/cp7_profile__apply.sql','utf8'))
await db.exec(block(identity,'cp7_identity.membership'))
const workspace=await readFile('scripts/cp7-src/identity/workspace.sql','utf8'),command=await readFile('scripts/cp7-src/identity/command.sql','utf8')
for(const name of ['workspace_data','workspace'])await db.exec(block(workspace,'cp7_identity.'+name))
await db.exec(block(command,'cp7_identity.apply_policy'))
for(const name of ['erp_cp7_get_planning_profiles_v1','erp_cp7_save_planning_profile_v1'])await db.exec(block(profile,'public.'+name))
for(const name of ['erp_cp7_get_production_policy_v1','erp_cp7_set_production_policy_v1'])await db.exec(block(command,'public.'+name))
const audit=await beginLocalStageAudit(db,'cutting-volume','scripts/cp7_ow12b_frozen_cutting_volume_local.py'),result=await audit.afterUse()
await mkdir('cp6-proof/t3',{recursive:true});await writeFile('cp6-proof/t3/FROZEN_CUTTING_VOLUME_LOCAL.json',JSON.stringify(result,null,2)+'\n')
console.log(JSON.stringify(result));await db.close()
