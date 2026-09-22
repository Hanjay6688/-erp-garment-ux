"""Build source-bound AO then AP migrations and exact pre-use inverses."""
from pathlib import Path
import json,re
import cp6_v2620ao_definitions as ao
import cp6_v2620ap_definitions as ap
import cp6_v2620an_build_sql as an
from cp6_ao_ap_inventory import INVENTORY_SQL,sha

ROOT=Path(__file__).resolve().parents[1]
CATALOG=Path('docs/evidence/cp6-ao-ap-catalog.json')
PINS=Path('docs/evidence/cp6-ao-ap-package-pins.json')
PROVENANCE=Path('docs/evidence/cp6-ao-ap-cli-provenance.json')
q=lambda s:"'"+str(s).replace("'","''")+"'"
j=lambda x:q(json.dumps(x,sort_keys=True,separators=(',',':')))+'::jsonb'

START="""begin;
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';set local search_path='';
set local role postgres;
do $closed_admission$
begin
 if session_user not in('postgres','supabase_admin')
  or (select datallowconn from pg_database where datname=current_database())
  or exists(select 1 from pg_stat_activity where datname=current_database() and pid<>pg_backend_pid()) then
  raise exception 'PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE';
 end if;
end $closed_admission$;
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;
do $lock_business$
declare n text;
begin
 for n in select c.relname from pg_class c join pg_namespace s on s.oid=c.relnamespace where s.nspname='erp' and c.relkind in('r','p') order by 1 loop
  execute format('lock table erp.%I in share row exclusive mode',n);
 end loop;
end $lock_business$;
"""

def data_sql(var,excluded,project=None):
    projection='to_jsonb(t)'
    if project:
        projection="to_jsonb(t)-case %L "+' '.join('when '+q(t)+' then array['+','.join(map(q,cols))+']::text[]' for t,cols in project.items())+" else array[]::text[] end"
    return f"""{var}:='{{}}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array[{','.join(map(q,excluded))}]::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to(({projection})::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,{('v_table,' if project else '')}v_table) into v_hash;
  {var}:={var}||jsonb_build_object(v_table,v_hash);
 end loop;
"""

def history_hash(schema,table,exclude='false'):
    return f"(select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from {schema}.{table} t where not({exclude}))"

def guard(objects,label):
    fingerprint=sha('\n'.join(f'{len(k)}:{k}:{v}' for k,v in sorted(objects.items())))
    return f"""do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from ({INVENTORY_SQL}) catalog;
 select count(*),encode(extensions.digest(convert_to(coalesce(string_agg(length(key)::text||':'||key||':'||value,E'\\n' order by key collate "C"),''),'UTF8'),'sha256'),'hex') into object_count,fingerprint from jsonb_each_text(actual);
 if object_count<>{len(objects)} or fingerprint is distinct from {q(fingerprint)} then
  raise exception '{label}_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
"""

def historical_guard(pins,label):
    return f"""do $historical_capsules$
declare r record;actual text;
begin
 for r in select * from jsonb_each_text({j(pins)}) loop
  execute format($caps$select encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex') from(select encode(extensions.digest(convert_to((to_jsonb(t)-array['captured_at','boundary_snapshot'])::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$caps$,r.key) into actual;
  if actual is distinct from r.value then raise exception '{label}_HISTORICAL_CAPSULE_DRIFT: %',r.key;end if;
 end loop;
end $historical_capsules$;
"""

def capsule_guard(family,pins):
    cap=pins['capsule'];expected={f['identity']:f for f in pins['functions']}
    return f"""do $capsule_guard$
declare r record;c record;e jsonb;boundary jsonb;actual jsonb;expected jsonb;
begin
 if not exists(select 1 from pg_class where oid='{cap}'::regclass and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
  or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid='{cap}'::regclass and a.grantee<>p.relowner)
  or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid='{cap}'::regclass and a.grantee<>'postgres'::regrole)
  or exists(select 1 from pg_policy where polrelid='{cap}'::regclass)
  or exists(select 1 from pg_trigger where tgrelid='{cap}'::regclass and not tgisinternal)
  or (select count(*) from {cap})<>{len(expected)} then raise exception '{family}_CAPSULE_SECURITY_OR_COUNT';end if;
 -- Match the complete visible column/constraint/index shape to the source-pinned
 -- AN template. Names of generated capsule indexes are intentionally immaterial.
 for r in select unnest(array['{cap}','erp.cp6_v2620an_rollback_capsule']) as rel loop
  select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid=r.rel::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=r.rel::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid=r.rel::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid=r.rel::regclass)) into actual;
  if expected is null then expected:=actual;elsif actual is distinct from expected then raise exception '{family}_CAPSULE_SHAPE_DRIFT';end if;
 end loop;
 select boundary_snapshot into boundary from {cap} limit 1;
 if boundary is null or exists(select 1 from {cap} where boundary_snapshot is distinct from boundary)
  or not(boundary ?& array['before','after','platform_before','markers_before']) then raise exception '{family}_CAPSULE_BOUNDARY';end if;
 for r in select * from jsonb_each({j(expected)}) loop
  select * into c from {cap} where object_regidentity=r.key;e:=r.value;
  if c.object_regidentity is null or c.definition_sha256 is distinct from e->>'predecessor_sha256'
   or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex') is distinct from e->>'predecessor_sha256'
   or c.installed_definition_sha256 is distinct from e->>'installed_sha256'
   or c.owner_snapshot is distinct from e->>'owner' or to_jsonb(c.acl_snapshot) is distinct from e->'acl' then
   raise exception '{family}_CAPSULE_SOURCE_DRIFT: %',r.key;
  end if;
 end loop;
end $capsule_guard$;
"""

def undo_schema(family,model,capture):
    s=''
    for name,table in reversed(re.findall(r'create trigger\s+(\w+).*?\bon\s+(erp\.\w+).*?;',getattr(model,'TRIGGERS',''),re.S|re.I)):
        s+=f'drop trigger {name} on {table};\n'
    # Restore original functions before removing helpers or their tables.
    s+=f"do $restore_functions$ declare r record;begin for r in select object_definition from erp.cp6_v2620{family.lower()}_rollback_capsule order by object_regidentity loop execute r.object_definition;end loop;end $restore_functions$;\n"
    old={r[0] for r in model.PREDECESSOR}
    for identity in reversed(list(model.FUNCTIONS)):
        if identity not in old:s+=f'drop function {identity};\n'
    if family=='AP':
        assert len(capture['restore_constraints'])==1
        name,definition=capture['restore_constraints'][0]
        s+=f"""alter table erp.payroll_deductions drop constraint payroll_cash_advance_source_check;
alter table erp.payroll_deductions drop constraint payroll_deductions_deduction_type_check;
alter table erp.payroll_deductions add constraint {name} {definition};
alter table erp.payroll_deductions drop column opening_cash_advance_balance_id;
alter table erp.supplier_payments drop constraint supplier_prepayment_funding_check;
alter table erp.supplier_payments alter column cash_account_id set not null;
alter table erp.opening_subledger_settlements alter column cash_account_id set not null;
alter table erp.sales_payment_posting_facts drop constraint sales_prepayment_fact_funding_check;
alter table erp.sales_payment_posting_facts alter column cash_account_id set not null;
"""
    else:s+='alter table erp.contractor_material_issue_items drop column manual_retail_unit_price;\n'
    for table in reversed(re.findall(r'create table\s+(erp\.\w+)',model.SCHEMA,re.I)):s+=f'drop table {table};\n'
    return s

def build():
    capture=json.loads(CATALOG.read_text());assert capture['status']=='CAPTURE_PASS' and capture['complete_boundary_restored']
    assert capture['inventory_sha256']==sha(Path('scripts/cp6_ao_ap_inventory.py').read_bytes())
    provenance=json.loads(PROVENANCE.read_text());families={}
    for family,model,previous in [('AO',ao,'AN'),('AP',ap,'AO')]:
        stage=capture['stages'][family];before=capture['stages'][previous]
        assert stage['schema_sha256']==sha(model.SCHEMA) and stage['triggers_sha256']==sha(getattr(model,'TRIGGERS','')) and stage['definitions_sha256']==sha(json.dumps(model.FUNCTIONS,sort_keys=True))
        generated=next(r for r in provenance if r['family']==family)
        assert generated['cli_version']=='2.116.0' and generated['empty_file_sha256']==sha(b'')
        filename=generated['generated_file'];stamp,name=filename[:-4].split('_',1)
        migration=Path('supabase/migrations')/filename;rollback=Path('supabase/rollbacks')/(filename[:-4]+'.rollback.sql')
        version='v2.6.20'+family.lower();cap='erp.cp6_v2620'+family.lower()+'_rollback_capsule';cap_name=cap.split('.')[1]
        prev=dict(version=an.VERSION,stamp=an.STAMP,name=an.NAME,migration_sha256=sha(an.MIGRATION.read_bytes())) if previous=='AN' else families[previous]
        functions=[]
        for identity,definition,acl,owner in model.PREDECESSOR:
            b=before['functions'][identity];a=stage['functions'][identity]
            assert b['sha256']==sha(definition) and b['owner']==owner and b['acl']==a['acl'] and owner==a['owner']=='postgres'
            functions.append(dict(identity=identity,predecessor_sha256=b['sha256'],installed_sha256=a['sha256'],owner=owner,acl=b['acl']))
        pin=dict(version=version,stamp=stamp,name=name,migration=str(migration),rollback=str(rollback),capsule=cap,previous=previous,
          functions=functions,new_functions={i:v for i,v in stage['functions'].items() if i not in before['functions']})
        new_tables=[t.split('.')[1] for t in re.findall(r'create table\s+(erp\.\w+)',model.SCHEMA,re.I)]
        projection={'contractor_material_issue_items':['manual_retail_unit_price']} if family=='AO' else {'payroll_deductions':['opening_cash_advance_balance_id']}
        pin.update(new_tables=new_tables,new_columns=projection)
        pre=f"""do $predecessor$
begin
 if not exists(select 1 from erp.schema_migrations where version={q(prev['version'])})
  or exists(select 1 from erp.schema_migrations where version={q(version)}) or to_regclass({q(cap)}) is not null
  or (select count(*) from supabase_migrations.schema_migrations where name={q(prev['name'])})<>1
  or not exists(select 1 from supabase_migrations.schema_migrations where version={q(prev['stamp'])} and name={q(prev['name'])}
   and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')={q(prev['migration_sha256'])})
  or exists(select 1 from supabase_migrations.schema_migrations where version>{q(prev['stamp'])}) then raise exception '{family}_EXACT_PREDECESSOR_REQUIRED';end if;
end $predecessor$;
"""
        original=','.join(q(f['identity'])+'::regprocedure' for f in functions)
        s=f'-- CP6 {family}: source-bound permanent package. Closed, drained maintenance required.\n'+START+pre+guard(before['objects'],family+'_PREDECESSOR')+historical_guard(capture['history_capsules'],family)
        s+=f"""create table {cap}(like erp.cp6_v2620an_rollback_capsule including all);
alter table {cap} enable row level security;
revoke all on {cap} from public,anon,authenticated,service_role;
insert into {cap}(object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
 format('%I.%I(%s)',n.nspname,p.proname,replace(oidvectortypes(p.proargtypes),', ',',')),pg_get_functiondef(p.oid),
 encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
 array(select a::text from unnest(p.proacl)a order by a::text),pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace where p.oid in({original});
do $before_data$
declare v_table text;v_hash jsonb;v_before jsonb;
begin
 {data_sql('v_before',['schema_migrations',cap_name])}
 update {cap} set boundary_snapshot=jsonb_build_object('before',v_before,'platform_before',{history_hash('supabase_migrations','schema_migrations')},'markers_before',{history_hash('erp','schema_migrations')});
end $before_data$;
"""
        s+=model.SCHEMA+'\n'
        for identity,definition in model.FUNCTIONS.items():
            s+=definition.rstrip(';\n')+';\n'
            if identity in pin['new_functions']:
                s+=f'revoke all on function {identity} from public,anon,authenticated,service_role;\n'
                if identity.startswith('public.'):s+=f'grant execute on function {identity} to authenticated,service_role;\n'
        s+=getattr(model,'TRIGGERS','')+'\n'+guard(stage['objects'],family+'_INSTALLED')
        s+=f"""update {cap} c set installed_definition_sha256=encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'),'sha256'),'hex');
do $after_data$
declare v_table text;v_hash jsonb;v_after jsonb;v_preserved jsonb;
begin
 {data_sql('v_after',['schema_migrations',cap_name])}
 {data_sql('v_preserved',['schema_migrations',cap_name]+new_tables,projection)}
 if v_preserved is distinct from (select boundary_snapshot->'before' from {cap} limit 1)
  or exists(select 1 from jsonb_each(v_after) where key=any(array[{','.join(map(q,new_tables))}]::text[]) and (value->>'count')::bigint<>0)
  then raise exception '{family}_INSTALL_CHANGED_BUSINESS_DATA';end if;
 update {cap} set boundary_snapshot=boundary_snapshot||jsonb_build_object('after',v_after);
end $after_data$;
insert into erp.schema_migrations(version,description) values({q(version)},{q('CP6 '+family+' source-bound connected import, inventory and financial lifecycle package')});
"""+capsule_guard(family,pin)+'commit;\n'
        migration.write_text(s);pin['migration_sha256']=sha(s)
        platform_guard=f"""do $platform_guard$
begin
 if not exists(select 1 from erp.schema_migrations where version={q(version)})
  or not exists(select 1 from erp.schema_migrations where version={q(prev['version'])})
  or (select count(*) from supabase_migrations.schema_migrations where name={q(name)})<>1
  or not exists(select 1 from supabase_migrations.schema_migrations where version={q(stamp)} and name={q(name)}
   and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')={q(pin['migration_sha256'])})
  or exists(select 1 from supabase_migrations.schema_migrations where version>{q(stamp)}) then raise exception '{family}_ROLLBACK_PLATFORM_OR_SUCCESSOR';end if;
end $platform_guard$;
"""
        s=f'-- CP6 {family}: exact pre-use restore to {previous}; closed, drained maintenance required.\n'+START+platform_guard+guard(stage['objects'],family+'_ROLLBACK')+historical_guard(capture['history_capsules'],family)+capsule_guard(family,pin)
        s+=f"""create temporary table cp6_package_restore_boundary on commit drop as select boundary_snapshot from {cap} limit 1;
do $pre_use$
declare v_table text;v_hash jsonb;v_after jsonb;b jsonb;
begin
 select boundary_snapshot into b from {cap} limit 1;
 {data_sql('v_after',['schema_migrations',cap_name])}
 if v_after is distinct from b->'after' then raise exception '{family}_POST_USE_ROLLBACK_REFUSED';end if;
 if {history_hash('supabase_migrations','schema_migrations','version='+q(stamp))} is distinct from b->>'platform_before'
  or {history_hash('erp','schema_migrations','version='+q(version))} is distinct from b->>'markers_before' then raise exception '{family}_PRIOR_MIGRATION_HISTORY_DRIFT';end if;
end $pre_use$;
"""+undo_schema(family,model,capture)
        s+=f"drop table {cap};\ndelete from erp.schema_migrations where version={q(version)};\ndelete from supabase_migrations.schema_migrations where version={q(stamp)} and name={q(name)};\n"+guard(before['objects'],family+'_RESTORED')
        s+=f"""do $restore_data$
declare v_table text;v_hash jsonb;v_before jsonb;b jsonb;
begin
 select boundary_snapshot into b from pg_temp.cp6_package_restore_boundary;
 {data_sql('v_before',['schema_migrations'])}
 if v_before is distinct from b->'before' or {history_hash('supabase_migrations','schema_migrations')} is distinct from b->>'platform_before'
  or {history_hash('erp','schema_migrations')} is distinct from b->>'markers_before' then raise exception '{family}_EXACT_RESTORE_FAILED';end if;
end $restore_data$;
commit;
"""
        rollback.write_text(s);pin['rollback_sha256']=sha(s);families[family]=pin
    pins=dict(format='CP6_AO_AP_PACKAGE_PINS_V1',capture_sha256=sha(CATALOG.read_bytes()),capture_head=capture['head'],families=families,
      inventory_sha256=sha(Path('scripts/cp6_ao_ap_inventory.py').read_bytes()),builder_sha256=sha(Path(__file__).read_bytes()),production_go=False,independent_acceptance=False)
    PINS.write_text(json.dumps(pins,indent=2)+'\n')
    print(json.dumps({k:{x:v[x] for x in ('migration','migration_sha256','rollback','rollback_sha256')} for k,v in families.items()},indent=2))
    return pins

if __name__=='__main__':build()
