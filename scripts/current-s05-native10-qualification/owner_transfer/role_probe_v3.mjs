import { createRequire } from 'node:module';
import { writeFile } from 'node:fs/promises';
const {PGlite}=createRequire(import.meta.url)(process.env.S05_PGLITE_MODULE);
const db=new PGlite();const out={classification:'LOCAL_PGLITE_ROLE_DDL_ONLY_NOT_NATIVE',Native_executions:0,steps:[]};
async function q(sql){return (await db.query(sql)).rows}
async function step(label,sql){const s={label,sql};try{s.rows=await q(sql);s.status='EXECUTED'}catch(e){s.status='REJECTED';s.error={code:e.code,message:e.message}}out.steps.push(s);return s}
try{
out.version=await q('select version(),current_database()');
const database=out.version[0].current_database.replaceAll('"','""');
await db.exec('create role s05_installer nologin nosuperuser createrole noinherit; grant usage,create on schema public to s05_installer; grant create on database "'+database+'" to s05_installer; set role s05_installer; begin;');
await step('BOUNDED_SELF_GRANT',"select set_config('createrole_self_grant','set, inherit',true)");
await step('CREATE_NEW_READER','create role cp7_accessory_standard_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication nobypassrls');
await step('RESTORE_SELF_GRANT',"select set_config('createrole_self_grant','',true)");
await step('EXACT_AUTO_EDGE',"select pg_get_userbyid(roleid) role,pg_get_userbyid(member) member,pg_get_userbyid(grantor) grantor,admin_option,inherit_option,set_option from pg_auth_members where roleid='cp7_accessory_standard_read'::regrole order by grantor");
await step('SCHEMA_AUTHORIZATION','create schema s05_reader_test authorization cp7_accessory_standard_read');
await db.exec('create function public.s05_role_probe()returns integer language sql as $$select 1$$; savepoint denied;');
await step('DENIED_WITH_SET_WITHOUT_CREATE','alter function public.s05_role_probe()owner to cp7_accessory_standard_read');
await db.exec('rollback to savepoint denied;');
out.before=await q("select nspacl::text raw_acl from pg_namespace where nspname='public'");
await step('TEMP_CREATE','grant create on schema public to cp7_accessory_standard_read');
await step('ALLOWED_WITH_SET_CREATE','alter function public.s05_role_probe()owner to cp7_accessory_standard_read');
await step('REVOKE_CREATE','revoke create on schema public from cp7_accessory_standard_read');
out.after=await q("select nspacl::text raw_acl from pg_namespace where nspname='public'");
await step('RESTORE_OUTER_ROLE','reset role');
await step('REVOKE_SELF_EDGE_FIRST','revoke cp7_accessory_standard_read from s05_installer granted by s05_installer');
await step('REVOKE_BOOTSTRAP_EDGE_SECOND','revoke cp7_accessory_standard_read from s05_installer granted by postgres');
await step('EXACT_ZERO_MEMBERSHIP',"select pg_get_userbyid(roleid) role,pg_get_userbyid(member) member,pg_get_userbyid(grantor) grantor,admin_option,inherit_option,set_option from pg_auth_members where roleid='cp7_accessory_standard_read'::regrole or member='cp7_accessory_standard_read'::regrole");
await db.exec('set local role s05_installer; savepoint uninstall_denied;');
await step('DROP_OWNED_DENIED_WITHOUT_HANDOVER','drop owned by cp7_accessory_standard_read cascade');
await db.exec('rollback to savepoint uninstall_denied; reset role;');
await step('TEMP_UNINSTALL_HANDOVER','grant cp7_accessory_standard_read to s05_installer with inherit true,set true');
await db.exec('set local role s05_installer;');
await step('DROP_OWNED_WITH_HANDOVER','drop owned by cp7_accessory_standard_read cascade');
await db.exec('reset role;');
await step('DROP_NEW_ROLE_OUTER','drop role cp7_accessory_standard_read');
await step('ABSENT',"select count(*) n from pg_roles where rolname='cp7_accessory_standard_read'");
await db.exec('rollback;');
}catch(e){out.error={code:e.code,message:e.message};process.exitCode=1}finally{await db.close();await writeFile('/workspace/scratch/ef468a447ac6/erp-s05-reader-ownerfix/scripts/current-s05-native10-qualification/owner_transfer/ROLE_PROBE_V3.json',JSON.stringify(out,null,2)+'\n',{flag:'wx'});process.stdout.write(JSON.stringify(out,null,2)+'\n')}
