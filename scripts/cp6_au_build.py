"""Exact AT successor for controlled, history-preserving master identity edits."""
from pathlib import Path
import copy,json
import cp6_ao_ap_build as package
import cp6_ao_ap_inventory as inventory
import cp6_at_build as predecessor
from cp6_au_definitions import OLD,FUNCTIONS,SCHEMA

ROOT=Path(__file__).resolve().parents[1]
STAMP='20260923045944'
NAME='erp_v2_6_20au_cp6_controlled_product_lifecycle'
VERSION='v2.6.20au'
CAP='erp.cp6_v2620au_rollback_capsule'
MIGRATION=Path(f'supabase/migrations/{STAMP}_{NAME}.sql')
ROLLBACK=Path(f'supabase/rollbacks/{STAMP}_{NAME}.rollback.sql')
PINS=Path('docs/evidence/cp6-au-pins.json')
PROVENANCE=Path('docs/evidence/cp6-au-cli-provenance.json')
BASE_PINS_SHA='87ced118da7193cf274027e91e09cc858d6a60720b7e1ae58d367d5f5576ad6c'
q,j,sha=package.q,package.j,inventory.sha
INVENTORY_SQL=predecessor.INVENTORY_SQL.replace("'cp6_v2620at_rollback_capsule')","'cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule')")
assert INVENTORY_SQL!=predecessor.INVENTORY_SQL

CONTEXT='product_identity_mutation_context_v1'
CATALOG=Path('docs/evidence/cp6-au-schema-capture.json')
CATALOG_SHA='01a442e4e4e437b8ca398fee9f9ac2ae0acb34e4d128960ac54169d1de888b16'

def model():
    assert sha(predecessor.PINS.read_bytes())==BASE_PINS_SHA
    predecessor_pin=json.loads(predecessor.PINS.read_text())
    assert sha(Path(predecessor.__file__).read_bytes())==predecessor_pin['builder_sha256']
    for key in ('migration','rollback'):assert sha(Path(predecessor_pin[key]).read_bytes())==predecessor_pin[key+'_sha256']
    base,capture,_,before,_=predecessor.model();after=copy.deepcopy(before);functions=[]
    assert sha(CATALOG.read_bytes())==CATALOG_SHA
    native=json.loads(CATALOG.read_text())
    assert native['status']=='CAPTURE_PASS' and native['complete_boundary_restored']
    assert native['schema_sha256']==sha(SCHEMA) and native['before_sha256']=={k:sha(json.dumps(before[k],sort_keys=True,ensure_ascii=False)) for k in ('objects','functions')}
    additions=native['new_objects'];assert not set(additions)&set(before['objects'])
    assert len(additions)==8 and all(CONTEXT in k for k in additions)
    assert set(native['changed_existing_objects'])=={'FUNCTION:'+k for k in FUNCTIONS}
    after['objects'].update(additions)
    for identity,new in FUNCTIONS.items():
        original=before['functions'][identity];old=OLD[identity]
        assert sha(old)==original['sha256']
        assert sha(json.dumps([old,original['owner'],original['acl']],ensure_ascii=False))==before['objects']['FUNCTION:'+identity]
        after['functions'][identity]['sha256']=sha(new)
        after['objects']['FUNCTION:'+identity]=sha(json.dumps([new,original['owner'],original['acl']],ensure_ascii=False))
        functions.append(dict(identity=identity,predecessor_sha256=sha(old),installed_sha256=sha(new),owner=original['owner'],acl=original['acl']))
    pin=dict(version=VERSION,stamp=STAMP,name=NAME,migration=str(MIGRATION),rollback=str(ROLLBACK),capsule=CAP,previous='AT',functions=functions,new_tables=[CONTEXT],schema_capture_sha256=CATALOG_SHA,schema_sha256=sha(SCHEMA))
    return base,capture,before,after,pin

def guard(objects,label):
    return package.guard(objects,label).replace(inventory.INVENTORY_SQL,INVENTORY_SQL)

def prior_guard(base,capture):
    pin=json.loads(predecessor.PINS.read_text())
    result=predecessor.prior_guard(base,capture)+package.capsule_guard('AT',pin)
    result+=f"""do $as_platform$ begin
 if not exists(select 1 from erp.schema_migrations where version={q(pin['version'])})
  or (select count(*) from supabase_migrations.schema_migrations where name={q(pin['name'])})<>1
  or not exists(select 1 from supabase_migrations.schema_migrations where version={q(pin['stamp'])} and name={q(pin['name'])}
   and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')={q(pin['migration_sha256'])})
 then raise exception 'AU_PRIOR_AT_PLATFORM_DRIFT';end if;
end $as_platform$;
"""
    return result

def build():
    base,capture,before,after,pin=model();prev=json.loads(predecessor.PINS.read_text());cap_name=CAP.split('.')[1]
    provenance=json.loads(PROVENANCE.read_text())
    assert provenance['cli_version']=='2.116.0' and provenance['generated_file']==MIGRATION.name and provenance['empty_file_sha256']==sha(b'')
    s='-- CP6 AU: Controlled product lifecycle with private one-use authority.\n'+package.START
    s+=f"""do $admission$ begin
 if exists(select 1 from erp.schema_migrations where version={q(VERSION)}) or to_regclass({q(CAP)}) is not null
  or exists(select 1 from supabase_migrations.schema_migrations where version>{q(prev['stamp'])})
 then raise exception 'AU_EXACT_AT_WITHOUT_SUCCESSOR_REQUIRED';end if;
end $admission$;
"""+guard(before['objects'],'AU_PREDECESSOR')+prior_guard(base,capture)
    s+=f"""create table {CAP}(like erp.cp6_v2620an_rollback_capsule including all);
alter table {CAP} enable row level security;
revoke all on {CAP} from public,anon,authenticated,service_role;
insert into {CAP}(object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),i.identity,pg_get_functiondef(p.oid),
 encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
 array(select a::text from unnest(p.proacl)a order by a::text),pg_get_userbyid(p.proowner)
from unnest(array[{','.join(q(i) for i in FUNCTIONS)}]) i(identity)
join pg_proc p on p.oid=i.identity::regprocedure join pg_namespace n on n.oid=p.pronamespace;
do $before_data$ declare v_table text;v_hash jsonb;v_before jsonb; begin
 {package.data_sql('v_before',['schema_migrations',cap_name])}
 update {CAP} set boundary_snapshot=jsonb_build_object('before',v_before,'platform_before',{package.history_hash('supabase_migrations','schema_migrations')},'markers_before',{package.history_hash('erp','schema_migrations')});
end $before_data$;
"""+SCHEMA+''.join(new.rstrip(';\n')+';\n' for new in FUNCTIONS.values())+guard(after['objects'],'AU_INSTALLED')
    s+=f"""update {CAP} set installed_definition_sha256=encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex');
do $after_data$ declare v_table text;v_hash jsonb;v_after jsonb; begin
 {package.data_sql('v_after',['schema_migrations',cap_name])}
 if (v_after-{q(CONTEXT)}) is distinct from (select boundary_snapshot->'before' from {CAP} limit 1) or (v_after->{q(CONTEXT)}->>'count')::bigint<>0 then raise exception 'AU_INSTALL_CHANGED_DATA';end if;
 update {CAP} set boundary_snapshot=boundary_snapshot||jsonb_build_object('after',v_after);
end $after_data$;
insert into erp.schema_migrations(version,description) values({q(VERSION)},'Controlled master identity lifecycle with immutable stock and financial history');
"""+package.capsule_guard('AU',pin)+'commit;\n'
    MIGRATION.write_text(s);pin['migration_sha256']=sha(s)
    s='-- CP6 AU: exact pre-use restore to AT under closed admission.\n'+package.START
    s+=f"""do $platform$ begin
 if not exists(select 1 from erp.schema_migrations where version={q(VERSION)})
  or (select count(*) from supabase_migrations.schema_migrations where name={q(NAME)})<>1
  or not exists(select 1 from supabase_migrations.schema_migrations where version={q(STAMP)} and name={q(NAME)}
   and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')={q(pin['migration_sha256'])})
  or exists(select 1 from supabase_migrations.schema_migrations where version>{q(STAMP)})
 then raise exception 'AU_ROLLBACK_PLATFORM_OR_SUCCESSOR';end if;
end $platform$;
"""+guard(after['objects'],'AU_ROLLBACK')+prior_guard(base,capture)+package.capsule_guard('AU',pin)
    s+=f"""create temporary table cp6_au_restore_boundary on commit drop as select boundary_snapshot from {CAP} limit 1;
do $pre_use$ declare v_table text;v_hash jsonb;v_after jsonb;b jsonb; begin
 select boundary_snapshot into b from {CAP} limit 1;
 {package.data_sql('v_after',['schema_migrations',cap_name])}
 if v_after is distinct from b->'after' then raise exception 'AU_POST_USE_ROLLBACK_REFUSED';end if;
 if {package.history_hash('supabase_migrations','schema_migrations','version='+q(STAMP))} is distinct from b->>'platform_before'
  or {package.history_hash('erp','schema_migrations','version='+q(VERSION))} is distinct from b->>'markers_before'
 then raise exception 'AU_PRIOR_HISTORY_DRIFT';end if;
end $pre_use$;
do $restore_function$ declare r record; begin for r in select object_definition from {CAP} order by object_regidentity loop execute r.object_definition;end loop;end $restore_function$;
drop table erp.{CONTEXT};
drop table {CAP};
delete from erp.schema_migrations where version={q(VERSION)};
delete from supabase_migrations.schema_migrations where version={q(STAMP)} and name={q(NAME)};
"""+guard(before['objects'],'AU_RESTORED')
    s+=f"""do $restored_data$ declare v_table text;v_hash jsonb;v_before jsonb;b jsonb; begin
 select boundary_snapshot into b from pg_temp.cp6_au_restore_boundary;
 {package.data_sql('v_before',['schema_migrations'])}
 if v_before is distinct from b->'before'
  or {package.history_hash('supabase_migrations','schema_migrations')} is distinct from b->>'platform_before'
  or {package.history_hash('erp','schema_migrations')} is distinct from b->>'markers_before'
 then raise exception 'AU_EXACT_RESTORE_FAILED';end if;
end $restored_data$;
commit;
"""
    ROLLBACK.write_text(s);pin['rollback_sha256']=sha(s)
    pin.update(builder_sha256=sha(Path(__file__).read_bytes()),definitions_sha256=sha(Path('scripts/cp6_au_definitions.py').read_bytes()),base_pins_sha256=BASE_PINS_SHA,production_go=False,independent_acceptance=False)
    PINS.write_text(json.dumps(pin,indent=2)+'\n')
    print(json.dumps({k:pin[k] for k in ('migration','migration_sha256','rollback','rollback_sha256')}))

if __name__=='__main__':build()
