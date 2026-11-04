// Real PG17 catalogue/ACL observations on empty authority fixtures only.
import fs from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const {PGlite}=await import(pathToFileURL(process.env.CP7_PGLITE_MODULE));
const input=JSON.parse(await fs.readFile(process.env.CP7_SKU_AUTHORITY_INPUT,'utf8'));
const db=new PGlite();
const names=Object.keys(input.source.tables).sort();
const q=s=>'"'+s.replaceAll('"','""')+'"';
const relation=n=>n.split('.').map(q).join('.');
const commands=input.roles.map(name=>'create role '+q(name)+' nologin nosuperuser nobypassrls');
commands.push('create role unexpected_grantee nologin nosuperuser nobypassrls',
              'create schema cp7_sku_conversion authorization postgres');
for(const name of names){
  commands.push('create table '+relation(name)+'(id uuid,private_value text)',
                'alter table '+relation(name)+' enable row level security',
                'revoke all on '+relation(name)+' from public');
  for(const policy of input.source.tables[name].policies){
    commands.push('create policy '+q(policy[0])+' on '+relation(name)+' as permissive for all to public using(false)with check(false)');
  }
}
await db.exec(commands.join(';')+';');
let index=0;const sql=input.sql.replaceAll('%s',()=>'$'+(++index));
if(index!==2)throw new Error('Exactly two authority query parameters required');
const capture=async()=>Object.fromEntries((await db.query(sql,[names,input.roles])).rows.map(row=>[row.qualified,row.authority]));
const snapshots=[{name:'baseline',authority:await capture(),must_refuse:false}];
const info=input.source.eligible[0],deny=names.find(n=>input.source.tables[n].policies.length);
const mutations=[
 ['public_schema_usage','grant usage on schema cp7_sku_conversion to public'],
 ['unknown_role_schema_usage','grant usage on schema cp7_sku_conversion to unexpected_grantee'],
 ['unknown_role_table_grant','grant select on '+relation(info)+' to unexpected_grantee'],
 ['public_column_grant','grant select(private_value)on '+relation(info)+' to public'],
 ['service_column_grant','grant select(private_value)on '+relation(info)+' to service_role'],
 ['rls_disabled','alter table '+relation(info)+' disable row level security'],
 ['force_rls_changed','alter table '+relation(info)+' force row level security'],
 ['new_allow_policy','create policy unexpected_allow on '+relation(info)+' using(true)'],
 ['original_deny_policy_changed','alter policy '+q(input.source.tables[deny].policies[0][0])+' on '+relation(deny)+' using(true)'],
 ['owner_changed','alter table '+relation(info)+' owner to unexpected_grantee'],
 ['schema_owner_changed','alter schema cp7_sku_conversion owner to unexpected_grantee'],
 ['missing_table','drop table '+relation(info)],
];
for(const role of input.roles)mutations.push([role+'_select','grant select on '+relation(info)+' to '+q(role)]);
for(const [name,command] of mutations){
 await db.exec('begin');
 try{await db.exec(command);snapshots.push({name,authority:await capture(),must_refuse:true});}
 finally{await db.exec('rollback');}
}
const version=(await db.query('select version()version')).rows[0].version;
await db.close();
await fs.writeFile(process.env.CP7_SKU_AUTHORITY_OUTPUT,JSON.stringify({
 classification:'POSTGRES_CATALOGUE_EMPTY_FIXTURE_NOT_ERP_AUTH_OR_FINANCIAL_ACCEPTANCE',
 version,actual_ERP_cases:0,business_constraints_modeled:false,actual_Auth_HTTP_cases:0,snapshots
},null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:'AUTHORITY_SQL_OBSERVATIONS_COMPLETE_REVIEW_STILL_REQUIRED',tables:names.length,snapshots:snapshots.length,actual_ERP_cases:0}));
