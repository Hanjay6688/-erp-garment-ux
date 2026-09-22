"""One-function successor: lock all issue materials before child FK insertion."""
from pathlib import Path
import copy,json
import cp6_ao_ap_build as package
import cp6_ao_ap_inventory as inventory
import cp6_v2620ao_definitions as ao

ROOT=Path(__file__).resolve().parents[1]
STAMP='20260922161019'
NAME='erp_v2_6_20aq_cp6_accessory_lock_order'
VERSION='v2.6.20aq'
CAP='erp.cp6_v2620aq_rollback_capsule'
IDENTITY='erp.save_contractor_material_issue_draft_v2(jsonb,uuid,bigint)'
MIGRATION=Path(f'supabase/migrations/{STAMP}_{NAME}.sql')
ROLLBACK=Path(f'supabase/rollbacks/{STAMP}_{NAME}.rollback.sql')
PINS=Path('docs/evidence/cp6-aq-pins.json')
PROVENANCE=Path('docs/evidence/cp6-aq-cli-provenance.json')
BASE_PINS_SHA='04f07884377b47684871faa92aaed380ea564dbfe3b67527ba2d59cc220fa50c'
q,j,sha=package.q,package.j,inventory.sha
OLD=ao.FUNCTIONS[IDENTITY]
NEEDLE='  delete from erp.contractor_material_issue_items where issue_id=v_id;'
assert OLD.count(NEEDLE)==1
NEW=OLD.replace(NEEDLE,"""  -- AQ: take the strongest material locks in one stable order before FK
  -- key-share locks are acquired by new issue lines. The same transaction can
  -- then post/recalculate without competing key-share-to-update upgrades.
  perform m.id from erp.materials m
  where m.id in(select (x->>'material_id')::uuid from jsonb_array_elements(p_payload->'items') x)
  order by m.id for update;
"""+NEEDLE)
INVENTORY_SQL=inventory.INVENTORY_SQL.replace("'cp6_v2620ap_rollback_capsule')","'cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule')")
assert INVENTORY_SQL!=inventory.INVENTORY_SQL

def model():
    raw=package.PINS.read_bytes();assert sha(raw)==BASE_PINS_SHA
    base=json.loads(raw);capture=json.loads(package.CATALOG.read_text())
    assert sha(package.CATALOG.read_bytes())==base['capture_sha256']
    for p in base['families'].values():
        for key in ('migration','rollback'):assert sha(Path(p[key]).read_bytes())==p[key+'_sha256']
    before=capture['stages']['AP'];after=copy.deepcopy(before)
    original=before['functions'][IDENTITY]
    assert sha(OLD)==original['sha256']
    assert sha(json.dumps([OLD,original['owner'],original['acl']],ensure_ascii=False))==before['objects']['FUNCTION:'+IDENTITY]
    after['functions'][IDENTITY]['sha256']=sha(NEW)
    after['objects']['FUNCTION:'+IDENTITY]=sha(json.dumps([NEW,original['owner'],original['acl']],ensure_ascii=False))
    pin=dict(version=VERSION,stamp=STAMP,name=NAME,migration=str(MIGRATION),rollback=str(ROLLBACK),capsule=CAP,previous='AP',
      functions=[dict(identity=IDENTITY,predecessor_sha256=sha(OLD),installed_sha256=sha(NEW),owner=original['owner'],acl=original['acl'])])
    return base,capture,before,after,pin

def guard(objects,label):
    return package.guard(objects,label).replace(inventory.INVENTORY_SQL,INVENTORY_SQL)

def prior_guard(base,capture):
    result=package.historical_guard(capture['history_capsules'],'AQ')
    for family,pin in base['families'].items():
        result+=package.capsule_guard(family,pin)
        result+=f"""do $prior_platform$ begin
 if not exists(select 1 from erp.schema_migrations where version={q(pin['version'])})
  or (select count(*) from supabase_migrations.schema_migrations where name={q(pin['name'])})<>1
  or not exists(select 1 from supabase_migrations.schema_migrations where version={q(pin['stamp'])} and name={q(pin['name'])}
   and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')={q(pin['migration_sha256'])})
 then raise exception 'AQ_PRIOR_PLATFORM_DRIFT';end if;
end $prior_platform$;
"""
    return result

def build():
    base,capture,before,after,pin=model();prev=base['families']['AP'];cap_name=CAP.split('.')[1]
    provenance=json.loads(PROVENANCE.read_text())
    assert provenance['cli_version']=='2.116.0' and provenance['generated_file']==MIGRATION.name and provenance['empty_file_sha256']==sha(b'')
    s='-- CP6 AQ: ordered material locks before accessory child insertion.\n'+package.START
    s+=f"""do $admission$ begin
 if exists(select 1 from erp.schema_migrations where version={q(VERSION)}) or to_regclass({q(CAP)}) is not null
  or exists(select 1 from supabase_migrations.schema_migrations where version>{q(prev['stamp'])})
 then raise exception 'AQ_EXACT_AP_WITHOUT_SUCCESSOR_REQUIRED';end if;
end $admission$;
"""+guard(before['objects'],'AQ_PREDECESSOR')+prior_guard(base,capture)
    s+=f"""create table {CAP}(like erp.cp6_v2620an_rollback_capsule including all);
alter table {CAP} enable row level security;
revoke all on {CAP} from public,anon,authenticated,service_role;
insert into {CAP}(object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),{q(IDENTITY)},pg_get_functiondef(p.oid),
 encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
 array(select a::text from unnest(p.proacl)a order by a::text),pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace where p.oid={q(IDENTITY)}::regprocedure;
do $before_data$ declare v_table text;v_hash jsonb;v_before jsonb; begin
 {package.data_sql('v_before',['schema_migrations',cap_name])}
 update {CAP} set boundary_snapshot=jsonb_build_object('before',v_before,'platform_before',{package.history_hash('supabase_migrations','schema_migrations')},'markers_before',{package.history_hash('erp','schema_migrations')});
end $before_data$;
"""+NEW.rstrip(';\n')+';\n'+guard(after['objects'],'AQ_INSTALLED')
    s+=f"""update {CAP} set installed_definition_sha256={q(sha(NEW))};
do $after_data$ declare v_table text;v_hash jsonb;v_after jsonb; begin
 {package.data_sql('v_after',['schema_migrations',cap_name])}
 if v_after is distinct from (select boundary_snapshot->'before' from {CAP}) then raise exception 'AQ_INSTALL_CHANGED_DATA';end if;
 update {CAP} set boundary_snapshot=boundary_snapshot||jsonb_build_object('after',v_after);
end $after_data$;
insert into erp.schema_migrations(version,description) values({q(VERSION)},'Order accessory material locks before saving child lines');
"""+package.capsule_guard('AQ',pin)+'commit;\n'
    MIGRATION.write_text(s);pin['migration_sha256']=sha(s)
    s='-- CP6 AQ: exact pre-use restore to AP under closed admission.\n'+package.START
    s+=f"""do $platform$ begin
 if not exists(select 1 from erp.schema_migrations where version={q(VERSION)})
  or (select count(*) from supabase_migrations.schema_migrations where name={q(NAME)})<>1
  or not exists(select 1 from supabase_migrations.schema_migrations where version={q(STAMP)} and name={q(NAME)}
   and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')={q(pin['migration_sha256'])})
  or exists(select 1 from supabase_migrations.schema_migrations where version>{q(STAMP)})
 then raise exception 'AQ_ROLLBACK_PLATFORM_OR_SUCCESSOR';end if;
end $platform$;
"""+guard(after['objects'],'AQ_ROLLBACK')+prior_guard(base,capture)+package.capsule_guard('AQ',pin)
    s+=f"""create temporary table cp6_aq_restore_boundary on commit drop as select boundary_snapshot from {CAP};
do $pre_use$ declare v_table text;v_hash jsonb;v_after jsonb;b jsonb; begin
 select boundary_snapshot into b from {CAP};
 {package.data_sql('v_after',['schema_migrations',cap_name])}
 if v_after is distinct from b->'after' then raise exception 'AQ_POST_USE_ROLLBACK_REFUSED';end if;
 if {package.history_hash('supabase_migrations','schema_migrations','version='+q(STAMP))} is distinct from b->>'platform_before'
  or {package.history_hash('erp','schema_migrations','version='+q(VERSION))} is distinct from b->>'markers_before'
 then raise exception 'AQ_PRIOR_HISTORY_DRIFT';end if;
end $pre_use$;
do $restore_function$ declare d text; begin select object_definition into d from {CAP};execute d;end $restore_function$;
drop table {CAP};
delete from erp.schema_migrations where version={q(VERSION)};
delete from supabase_migrations.schema_migrations where version={q(STAMP)} and name={q(NAME)};
"""+guard(before['objects'],'AQ_RESTORED')
    s+=f"""do $restored_data$ declare v_table text;v_hash jsonb;v_before jsonb;b jsonb; begin
 select boundary_snapshot into b from pg_temp.cp6_aq_restore_boundary;
 {package.data_sql('v_before',['schema_migrations'])}
 if v_before is distinct from b->'before'
  or {package.history_hash('supabase_migrations','schema_migrations')} is distinct from b->>'platform_before'
  or {package.history_hash('erp','schema_migrations')} is distinct from b->>'markers_before'
 then raise exception 'AQ_EXACT_RESTORE_FAILED';end if;
end $restored_data$;
commit;
"""
    ROLLBACK.write_text(s);pin['rollback_sha256']=sha(s)
    pin.update(builder_sha256=sha(Path(__file__).read_bytes()),base_pins_sha256=BASE_PINS_SHA,production_go=False,independent_acceptance=False)
    PINS.write_text(json.dumps(pin,indent=2)+'\n')
    print(json.dumps({k:pin[k] for k in ('migration','migration_sha256','rollback','rollback_sha256')}))

if __name__=='__main__':build()
