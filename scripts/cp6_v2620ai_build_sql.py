#!/usr/bin/env python3
"""AI revalidates current work source at posting and preserves exact AH rollback."""
from pathlib import Path
import json
import cp6_v2620ah_build_sql as ah

STAMP='20260916090022'
NAME='erp_v2_6_20ai_cp6_work_source_lineage'
VERSION='v2.6.20ai'
PREDECESSOR_HEAD='965ceac45ef15ddc19c178d87a3606adffcf53a6'
PREDECESSOR_TREE='183a0c2af8ba201e3754e9db77fe47501c196f4d'
MIGRATION=Path(f'supabase/migrations/{STAMP}_{NAME}.sql')
ROLLBACK=Path(f'supabase/rollbacks/{STAMP}_{NAME}.rollback.sql')
PINS=Path('docs/evidence/cp6-ai-runtime-pins.json')
INPUT=Path('docs/evidence/cp6-ai-predecessor-functions.json')
CATALOG=Path('docs/evidence/cp6-ai-ah-catalog-pins.json')
BUILDER=Path(__file__).relative_to(Path.cwd())
IDENTITIES=('erp.validate_work_completion()',
            'erp.guard_work_completion_posting_consistency()',
            'erp.run_v268_financial_report_checks()')
sha,replace,block,rows=ah.sha,ah.replace,ah.block,ah.rows

DIRTY_QUERY="""select count(*)::bigint from (
 select ai_line.id
 from erp.work_completion_lines ai_line
 join erp.work_completion_events ai_event on ai_event.id=ai_line.completion_id and ai_event.status='POSTED'
 left join erp.po_work_component_snapshots ai_snapshot on ai_snapshot.id=ai_line.po_component_snapshot_id
 left join erp.production_orders ai_po on ai_po.id=ai_event.po_id
 left join erp.cutting_groups ai_group on ai_group.id=ai_event.cutting_group_id
 where ai_snapshot.id is null or ai_po.id is null or ai_group.id is null
   or ai_snapshot.po_id is distinct from ai_event.po_id
   or ai_snapshot.work_component_id is distinct from ai_line.work_component_id
   or ai_snapshot.rate_per_pcs_snapshot is distinct from ai_line.rate_snapshot
   or ai_group.po_id is distinct from ai_event.po_id
   or ai_po.contractor_id is distinct from ai_event.contractor_id
 union all
 select ai_event.id from erp.work_completion_events ai_event
 where ai_event.status='POSTED' and not exists(select 1 from erp.work_completion_lines ai_line where ai_line.completion_id=ai_event.id)
) ai_broken"""

VALIDATOR="""CREATE OR REPLACE FUNCTION erp.validate_work_completion()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  v_event_po uuid;
  v_event_contractor uuid;
  v_po_contractor uuid;
  v_snapshot_po uuid;
  v_snapshot_component uuid;
  v_snapshot_rate numeric(18,2);
begin
  perform erp.require_internal();
  select e.po_id,e.contractor_id into v_event_po,v_event_contractor
  from erp.work_completion_events e where e.id=new.completion_id for share of e;
  select p.contractor_id into v_po_contractor
  from erp.production_orders p where p.id=v_event_po;
  select s.po_id,s.work_component_id,s.rate_per_pcs_snapshot
  into v_snapshot_po,v_snapshot_component,v_snapshot_rate
  from erp.po_work_component_snapshots s where s.id=new.po_component_snapshot_id for share of s;
  if v_event_po is null then raise exception 'Completion event not found'; end if;
  if v_po_contractor is distinct from v_event_contractor then
    raise exception 'Completion contractor must match PO contractor';
  end if;
  if v_snapshot_po is distinct from v_event_po
     or v_snapshot_component is distinct from new.work_component_id
     or v_snapshot_rate is null then
    raise exception 'Work component snapshot does not match completion PO/component';
  end if;
  new.rate_snapshot:=v_snapshot_rate;
  return new;
end;
$function$
"""

POST_GUARD="""    -- The DRAFT header may have changed after its lines were normalized.
    -- Recheck the current source before any work, payable or HPP is recognized.
    if not exists(select 1 from erp.production_orders ai_po
      where ai_po.id=new.po_id and ai_po.contractor_id=new.contractor_id) then
      raise exception 'AI_WORK_SOURCE_CONTRACTOR_MISMATCH';
    end if;
    perform 1 from erp.po_work_component_snapshots ai_snapshot
      join erp.work_completion_lines ai_line on ai_line.po_component_snapshot_id=ai_snapshot.id
      where ai_line.completion_id=new.id order by ai_snapshot.id for share of ai_snapshot;
    if exists(
      select 1 from erp.work_completion_lines ai_line
      left join erp.po_work_component_snapshots ai_snapshot on ai_snapshot.id=ai_line.po_component_snapshot_id
      where ai_line.completion_id=new.id and (
        ai_snapshot.id is null or ai_snapshot.po_id is distinct from new.po_id
        or ai_snapshot.work_component_id is distinct from ai_line.work_component_id
        or ai_snapshot.rate_per_pcs_snapshot is distinct from ai_line.rate_snapshot)
    ) then
      raise exception 'AI_WORK_SOURCE_SNAPSHOT_MISMATCH: rebuild the draft lines for the selected PO before posting';
    end if;

"""

def build():
    original=json.loads(INPUT.read_text());assert (original['head'],original['tree'])==(PREDECESSOR_HEAD,PREDECESSOR_TREE)
    src={r[0]:r for r in original['functions']};assert set(src)==set(IDENTITIES)
    prior=json.loads(ah.PINS.read_text())
    for p in (ah.MIGRATION,ah.ROLLBACK):assert sha(p.read_bytes())==prior['source_pins'][str(p)]['sha256']
    guard=replace(src[IDENTITIES[1]][1],"  if new.status='POSTED' and old.status is distinct from 'POSTED' then\n",
                  "  if new.status='POSTED' and old.status is distinct from 'POSTED' then\n"+POST_GUARD)
    report=replace(src[IDENTITIES[2]][1],"\nend\n$function$",
      "\n  return query select 'V2620AI_WORK_SOURCE_LINEAGE_MISMATCH'::text,'CRITICAL'::text,("+DIRTY_QUERY+"),'Posted work must retain the selected PO, contractor, component and committed rate snapshot'::text;\nend\n$function$")
    defs=[VALIDATOR,guard,report]
    functions=[dict(identity=i,predecessor_sha256=sha(src[i][1]),installed_sha256=sha(d),owner=src[i][3],acl=sorted(src[i][2].strip('{}').split(','))) for i,d in zip(IDENTITIES,defs,strict=True)]
    old_rows={m:rows(prior['functions'],m) for m in ('predecessor','installed','restore')}
    new_rows={m:rows(functions,m) for m in old_rows}
    def advance(sql):
        for old,tag in (('v2620ah','__AI_CAP__'),('v2.6.20ah','__AI_VER__'),('AH_','__AI_ERR__')):sql=sql.replace(old,tag)
        sql=sql.replace('v2620ag','v2620ah').replace('v2.6.20ag','v2.6.20ah')
        return sql.replace('__AI_CAP__','v2620ai').replace('__AI_VER__',VERSION).replace('__AI_ERR__','AI_').replace('<>220','<>221').replace('expected220','expected221')
    migration=advance(ah.MIGRATION.read_text());migration=migration[migration.index('begin;\n'):]
    migration='-- CP6 AI: work source is revalidated at posting; original posted history is unchanged.\n'+migration
    migration=replace(migration,"where p.oid in("+','.join("'"+i+"'::regprocedure" for i in ah.IDENTITIES)+");", "where p.oid in("+','.join("'"+i+"'::regprocedure" for i in IDENTITIES)+");")
    admission=f"""do $predecessor_v2620ai$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='{ah.VERSION}')
     or exists(select 1 from erp.schema_migrations where version='{VERSION}')
     or to_regclass('erp.cp6_v2620ai_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620ah_rollback_capsule') is null then raise exception 'AI_REQUIRES_EXACT_AH_WITHOUT_AI_RESIDUE'; end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='{ah.NAME}')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations where version='{ah.STAMP}' and name='{ah.NAME}'
       and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')='{sha(ah.MIGRATION.read_bytes())}')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'{ah.STAMP}')
     or (select count(*) from erp.cp6_v2620ah_rollback_capsule)<>5 then raise exception 'AI_REQUIRES_EXACT_AH_PLATFORM_CAPSULE'; end if;
  for r in select * from(values
    {new_rows['predecessor']}
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') into v_actual
    from pg_proc p where p.oid=to_regprocedure(r.identity) and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then raise exception 'AI_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity; end if;
  end loop;
  if ({DIRTY_QUERY})<>0 then raise exception 'AI_PREEXISTING_WORK_SOURCE_REVIEW_REQUIRED'; end if;
end
$predecessor_v2620ai$;"""
    migration=block(migration,'do $predecessor_v2620ai$','$predecessor_v2620ai$;',admission)
    canonical='do $canonical_opening_v2620ai$\nbegin\n'+'\n'.join('  execute $definition$'+d+'$definition$;' for d in defs)+'\nend\n$canonical_opening_v2620ai$;'
    migration=block(migration,'do $canonical_opening_v2620ai$','$canonical_opening_v2620ai$;',canonical)
    migration=replace(migration,old_rows['installed'],new_rows['installed'])
    migration=migration.replace('(select count(*) from erp.cp6_v2620ai_rollback_capsule)<>5','(select count(*) from erp.cp6_v2620ai_rollback_capsule)<>3')
    migration=migration.replace('Return allocation eligibility, destination and ordinary draft validation remain coherent','Work posting revalidates source PO, component, contractor and committed rate')
    MIGRATION.write_text(migration)
    rollback=advance(ah.ROLLBACK.read_text()).replace('-> exact AG.','-> exact AH.')
    for mode in old_rows:
        if old_rows[mode] in rollback:rollback=replace(rollback,old_rows[mode],new_rows[mode])
    rollback=rollback.replace(ah.STAMP,STAMP).replace(ah.NAME,NAME)
    rollback=rollback.replace(sha(ah.MIGRATION.read_bytes()),sha(migration)).replace(sha(ah.MIGRATION.read_text().removesuffix('\n')),sha(migration.removesuffix('\n')))
    rollback=rollback.replace('(select count(*) from erp.cp6_v2620ai_rollback_capsule)<>5','(select count(*) from erp.cp6_v2620ai_rollback_capsule)<>3')
    ROLLBACK.write_text(rollback)
    pins=dict(format='CP6_AI_RUNTIME_PINS_V1',stamp=STAMP,name=NAME,version=VERSION,predecessor_head=PREDECESSOR_HEAD,predecessor_tree=PREDECESSOR_TREE,functions=functions,boundary_count=221,predecessor_function_count=533,predecessor_table_count=223,comparison_run=35076310148,production_go=False,source_pins={str(p):dict(sha256=sha(p.read_bytes()),bytes=p.stat().st_size) for p in (BUILDER,INPUT,CATALOG,ah.MIGRATION,ah.ROLLBACK,MIGRATION,ROLLBACK)})
    PINS.write_text(json.dumps(pins,indent=2)+'\n')
    print(json.dumps({'migration':sha(migration),'rollback':sha(rollback),'pins':sha(PINS.read_bytes())}));return pins

if __name__=='__main__':build()
