#!/usr/bin/env python3
"""AN read-only selectors, immutable AM admission, exact pre-use rollback."""
from pathlib import Path
import json
import cp6_v2620am_build_sql as prior
from cp6_v2620an_definitions import PRIVATE_ID,PUBLIC_ID,PRIVATE,PUBLIC

STAMP='20260921223438'
NAME='erp_v2_6_20an_cp6_cutting_selectors'
VERSION='v2.6.20an'
PREDECESSOR_HEAD='bf05659d4f8e99d0332215772d658417e4233cc8'
PREDECESSOR_TREE='e5ac4db612e5c9097daf0c6a446abeafffc29cd2'
MIGRATION=Path(f'supabase/migrations/{STAMP}_{NAME}.sql')
ROLLBACK=Path(f'supabase/rollbacks/{STAMP}_{NAME}.rollback.sql')
PINS=Path('docs/evidence/cp6-an-runtime-pins.json')
INPUT=Path('docs/evidence/cp6-an-predecessor-functions.json')
CATALOG=Path('docs/evidence/cp6-an-am-catalog-pins.json')
PROVENANCE=Path('docs/evidence/cp6-an-cli-provenance.json')
BUILDER=Path('scripts/cp6_v2620an_build_sql.py')
DEFINITIONS=Path('scripts/cp6_v2620an_definitions.py')
LEGACY='erp.get_cutting_workspace_v1(text,uuid,integer,integer)'
sha,replace,block,rows=prior.sha,prior.replace,prior.block,prior.rows


def new_reader_guard(functions,tag):
    return f"""do ${tag}_v2620an$
declare r record;v_actual text;
begin
  for r in select * from(values
    {rows(functions,'installed')}
  ) expected(identity,predecessor_sha256,installed_sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') into v_actual
    from pg_proc p where p.oid=to_regprocedure(r.identity) and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.installed_sha256 then raise exception 'AN_NEW_READER_DRIFT: %',r.identity; end if;
  end loop;
end
${tag}_v2620an$;
"""


def build():
    provenance=json.loads(PROVENANCE.read_text())
    assert provenance['generated_file']==MIGRATION.name and provenance['cli_version']=='2.116.0'
    assert provenance['empty_file_sha256']==sha(b'')
    source=json.loads(INPUT.read_text());assert (source['head'],source['tree'])==(PREDECESSOR_HEAD,PREDECESSOR_TREE)
    original=source['functions'][0];assert len(source['functions'])==1 and original['identity']==LEGACY
    assert sha(original['definition'])==original['sha256']
    catalog={f['identity']:f for f in json.loads(CATALOG.read_text())['functions']};assert len(catalog)==533
    assert original['sha256']==catalog[LEGACY]['sha256']
    functions=[dict(identity=LEGACY,predecessor_sha256=original['sha256'],installed_sha256=original['sha256'],owner='postgres',acl=['postgres=X/postgres'])]
    new_functions=[dict(identity=i,predecessor_sha256='',installed_sha256=sha(d),owner='postgres',acl=a) for i,d,a in
        ((PRIVATE_ID,PRIVATE,['postgres=X/postgres']),
         (PUBLIC_ID,PUBLIC,['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']))]
    p=json.loads(prior.PINS.read_text())
    for path in (prior.MIGRATION,prior.ROLLBACK):assert sha(path.read_bytes())==p['source_pins'][str(path)]['sha256']
    old={mode:rows(p['functions'],mode) for mode in ('predecessor','installed','restore')}
    new={mode:rows(functions,mode) for mode in old}
    def advance(s):
        for before,tag in (('v2620am','__AN_CAP__'),('v2.6.20am','__AN_VER__'),('AM_','__AN_ERR__')):s=s.replace(before,tag)
        s=s.replace('v2620al','v2620am').replace('v2.6.20al','v2.6.20am')
        return s.replace('__AN_CAP__','v2620an').replace('__AN_VER__',VERSION).replace('__AN_ERR__','AN_').replace('<>225','<>226').replace('expected225','expected226')
    migration=prior.MIGRATION.read_text()
    assert migration.count(prior.DATA_ADMISSION)==1;migration=migration.replace(prior.DATA_ADMISSION,'')
    migration=advance(migration)
    migration='-- CP6 AN: independently paged PO/draft selectors with selected-row continuity.\n'+migration[migration.index('begin;\n'):]
    old_where="where p.oid in("+','.join("'"+i+"'::regprocedure" for i in prior.IDENTITIES)+");"
    migration=replace(migration,old_where,"where p.oid='"+LEGACY+"'::regprocedure;")
    admission=f"""do $predecessor_v2620an$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='{prior.VERSION}')
     or exists(select 1 from erp.schema_migrations where version='{VERSION}')
     or to_regclass('erp.cp6_v2620an_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620am_rollback_capsule') is null
     or to_regprocedure('{PRIVATE_ID}') is not null or to_regprocedure('{PUBLIC_ID}') is not null then
    raise exception 'AN_REQUIRES_EXACT_AM_WITHOUT_AN_RESIDUE'; end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='{prior.NAME}')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations where version='{prior.STAMP}' and name='{prior.NAME}'
       and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')='{sha(prior.MIGRATION.read_bytes())}')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'{prior.STAMP}')
     or (select count(*) from erp.cp6_v2620am_rollback_capsule)<>6 then raise exception 'AN_REQUIRES_EXACT_AM_PLATFORM_CAPSULE'; end if;
  for r in select * from(values
    {new['predecessor']}
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') into v_actual
    from pg_proc p where p.oid=to_regprocedure(r.identity) and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then raise exception 'AN_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity; end if;
  end loop;
end
$predecessor_v2620an$;"""
    migration=block(migration,'do $predecessor_v2620an$','$predecessor_v2620an$;',admission)
    canonical='do $canonical_reader_v2620an$\nbegin\n'+''.join('  execute $definition$'+d+'$definition$;\n' for d in (PRIVATE,PUBLIC))+'end\n$canonical_reader_v2620an$;\n'
    canonical+=f'revoke all on function {PRIVATE_ID},{PUBLIC_ID} from public,anon,authenticated,service_role;\ngrant execute on function {PUBLIC_ID} to authenticated,service_role;\n'
    canonical+=new_reader_guard(new_functions,'new_readers')
    migration=block(migration,'do $canonical_transfer_v2620an$','$canonical_transfer_v2620an$;',canonical)
    migration=replace(migration,old['installed'],new['installed'])
    migration=migration.replace('(select count(*) from erp.cp6_v2620an_rollback_capsule)<>6','(select count(*) from erp.cp6_v2620an_rollback_capsule)<>1')
    migration=migration.replace('Every transfer line posts atomically; paired historical costs are neutral and location roll prefixes remain valid','Independent PO and draft search pagination preserve selected rows without changing writes or financial policy')
    MIGRATION.write_text(migration)
    rollback=advance(prior.ROLLBACK.read_text()).replace('-> exact AL.','-> exact AM.')
    rollback=rollback.replace('(select count(*) from erp.cp6_v2620an_rollback_capsule)<>6','(select count(*) from erp.cp6_v2620an_rollback_capsule)<>1')
    for mode in old:
        if old[mode] in rollback:rollback=rollback.replace(old[mode],new[mode])
    rollback=rollback.replace(prior.STAMP,STAMP).replace(prior.NAME,NAME)
    rollback=rollback.replace(sha(prior.MIGRATION.read_bytes()),sha(migration)).replace(sha(prior.MIGRATION.read_text().removesuffix('\n')),sha(migration.removesuffix('\n')))
    rollback=replace(rollback,'do $restore_guard_v2620an$',new_reader_guard(new_functions,'rollback_readers')+'\ndo $restore_guard_v2620an$')
    marker='  for c in select * from erp.cp6_v2620an_rollback_capsule order by object_regidentity loop'
    rollback=replace(rollback,marker,f"  execute 'drop function {PUBLIC_ID}';\n  execute 'drop function {PRIVATE_ID}';\n"+marker)
    rollback=replace(rollback,"  if exists(select 1 from erp.schema_migrations where version='v2.6.20an')",f"  if to_regprocedure('{PRIVATE_ID}') is not null or to_regprocedure('{PUBLIC_ID}') is not null\n     or exists(select 1 from erp.schema_migrations where version='v2.6.20an')")
    ROLLBACK.write_text(rollback)
    pins=dict(format='CP6_AN_RUNTIME_PINS_V1',stamp=STAMP,name=NAME,version=VERSION,
        predecessor_head=PREDECESSOR_HEAD,predecessor_tree=PREDECESSOR_TREE,functions=functions,new_functions=new_functions,
        boundary_count=226,predecessor_function_count=533,predecessor_table_count=228,
        successor_erp_function_count=534,runtime_object_count=692,comparison_run=35663140263,production_go=False,
        source_pins={str(path):dict(sha256=sha(path.read_bytes()),bytes=path.stat().st_size)
            for path in (BUILDER,DEFINITIONS,PROVENANCE,INPUT,CATALOG,prior.MIGRATION,prior.ROLLBACK,MIGRATION,ROLLBACK)})
    PINS.write_text(json.dumps(pins,indent=2)+'\n')
    print(json.dumps({'migration':sha(migration),'rollback':sha(rollback),'pins':sha(PINS.read_bytes())}))
    return pins

if __name__=='__main__':build()
