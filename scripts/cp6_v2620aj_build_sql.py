#!/usr/bin/env python3
"""AJ: distinct rework outputs with source-owned cost and row import diagnostics."""
from pathlib import Path
import json
import cp6_v2620ai_build_sql as ai

STAMP='20260916202400'
NAME='erp_v2_6_20aj_cp6_rework_output_lineage'
VERSION='v2.6.20aj'
PREDECESSOR_HEAD='25fa4736329e5148dfdb3572bc169952cba23251'
PREDECESSOR_TREE='a5cb1e43d776a9ffc058f99c8d5c96ac7f6a9c0d'
MIGRATION=Path(f'supabase/migrations/{STAMP}_{NAME}.sql')
ROLLBACK=Path(f'supabase/rollbacks/{STAMP}_{NAME}.rollback.sql')
PINS=Path('docs/evidence/cp6-aj-runtime-pins.json')
INPUT=Path('docs/evidence/cp6-aj-predecessor-functions.json')
CATALOG=Path('docs/evidence/cp6-aj-ai-catalog-pins.json')
BUILDER=Path('scripts/cp6_v2620aj_build_sql.py')
IDENTITIES=('erp.post_rework_completion(uuid)','erp.rebuild_po_hpp(uuid,text)',
 'erp.cp6_lot_failed_wash_cost_v2620e(uuid)','erp._validate_migration_batch_base(uuid)',
 'erp.validate_migration_opening_stock_costs(uuid)','erp.validate_migration_batch(uuid)')
sha,replace,block,rows=ai.sha,ai.replace,ai.block,ai.rows

SOURCE_QC="""coalesce(fl.qc_item_id,(
      select bc.qc_item_id from erp.rework_orders ro
      join erp.bs_cases bc on bc.id=ro.bs_case_id
      where ro.good_fg_lot_id=fl.id
    ))"""

def definitions(src):
 post=replace(src[IDENTITIES[0]][1],
  '      v_lot_number,b.po_id,b.qc_item_id,b.cutting_group_id,b.product_id,',
  '''      -- qc_item_id identifies the single original QC output. Recovery is
      -- identified by rework_orders.good_fg_lot_id -> bs_cases -> source QC.
      v_lot_number,b.po_id,null,b.cutting_group_id,b.product_id,''')
 hpp=replace(src[IDENTITIES[1]][1],
  '    select fl.*,coalesce(fl.cutting_group_id,qi.cutting_group_id) as lineage_group_id',
  '    select fl.*,'+SOURCE_QC+' as source_qc_item_id,\n      coalesce(fl.cutting_group_id,qi.cutting_group_id) as lineage_group_id')
 assert hpp.count('r.qc_item_id')==3
 hpp=hpp.replace('r.qc_item_id','r.source_qc_item_id')
 failed=replace(src[IDENTITIES[2]][1],
  '  join erp.qc_inspection_items qi on qi.id=fl.qc_item_id',
  '  join erp.qc_inspection_items qi on qi.id='+SOURCE_QC)
 base=replace(src[IDENTITIES[3]][1],
  'v_bt text;v_material_type text;', 'v_bt text;v_material_type text;v_number numeric;')
 base=replace(base,"    e:='[]'::jsonb;\n",'''    e:='[]'::jsonb;
    begin
      -- A malformed input is a row error. It must not roll back diagnostics
      -- for the entire batch or be accepted as NaN/infinite business quantity.
      foreach k in array array['qty','opening_qty','unit_cost','amount',
        'hpp_percent_of_price','target_qty_pcs','target_dozens'] loop
        if nullif(btrim(r.normalized_payload->>k),'') is not null then
          v_number:=(r.normalized_payload->>k)::numeric;
          if v_number::text in('NaN','Infinity','-Infinity') then
            e:=e||jsonb_build_array('Field must be a finite number: '||k);
          end if;
        end if;
      end loop;
''')
 base=replace(base,"    if r.validation_status='ERROR' and jsonb_array_length(r.validation_errors)>0 then",'''    exception when others then
      e:=e||jsonb_build_array('Invalid row value: '||sqlerrm);
    end;
    if r.validation_status='ERROR' and jsonb_array_length(r.validation_errors)>0 then''')
 cost=replace(src[IDENTITIES[4]][1],
  'r record;j jsonb;v_bt text;v_method text;v_product uuid;',
  'r record;j jsonb;v_bt text;v_method text;v_product uuid;v_number numeric;')
 cost=replace(cost,"    j:=r.normalized_payload;v_bt:=upper(coalesce(j->>'balance_type',''));v_method:=coalesce(nullif(upper(j->>'hpp_input_method'),''),'MANUAL');",'''    begin
    j:=r.normalized_payload;v_bt:=upper(coalesce(j->>'balance_type',''));v_method:=coalesce(nullif(upper(j->>'hpp_input_method'),''),'MANUAL');
    if v_bt in('MATERIAL','FINISHED_GOODS') and nullif(btrim(j->>'unit_cost'),'') is not null then
      v_number:=(j->>'unit_cost')::numeric;
      if v_number<0 or v_number::text in('NaN','Infinity','-Infinity') then
        raise exception 'unit_cost must be finite and zero or positive';
      end if;
    end if;
    if v_bt='FINISHED_GOODS' and (j->>'qty')::numeric<>trunc((j->>'qty')::numeric) then
      raise exception 'FINISHED_GOODS qty must be whole PCS';
    end if;''')
 cost=cost.replace("nullif(j->>'unit_cost','')", "nullif(btrim(j->>'unit_cost'),'')")
 cost=replace(cost,'  end loop;\nend$function$', '''    exception when others then
      update erp.migration_staging_rows
      set validation_status='ERROR',validation_errors=validation_errors||jsonb_build_array(sqlerrm),
          updated_at=statement_timestamp()
      where id=r.id;
    end;
  end loop;
  update erp.migration_batches b set
    status=case when exists(select 1 from erp.migration_staging_rows s
      where s.batch_id=b.id and s.validation_status<>'VALID') then 'DRAFT' else 'READY' end,
    validated_at=statement_timestamp(),
    error_message=case when exists(select 1 from erp.migration_staging_rows s
      where s.batch_id=b.id and s.validation_status='ERROR') then
      (select count(*) from erp.migration_staging_rows s where s.batch_id=b.id and s.validation_status='ERROR')||' staging row(s) failed validation'
      else null end
  where b.id=p_batch_id;
end$function$''')
 wrapper=replace(src[IDENTITIES[5]][1],
  '  return query select * from erp._validate_migration_batch_base(p_batch_id);',
  '  perform * from erp._validate_migration_batch_base(p_batch_id);')
 wrapper=replace(wrapper,'  perform erp.validate_migration_opening_stock_costs(p_batch_id);',
  '''  perform erp.validate_migration_opening_stock_costs(p_batch_id);
  return query select count(*),count(*) filter(where validation_status='VALID'),
    count(*) filter(where validation_status='ERROR')
  from erp.migration_staging_rows where batch_id=p_batch_id;''')
 return [post,hpp,failed,base,cost,wrapper]

def build():
 original=json.loads(INPUT.read_text())
 assert (original['head'],original['tree'])==(PREDECESSOR_HEAD,PREDECESSOR_TREE)
 src={r[0]:r for r in original['functions']};assert set(src)==set(IDENTITIES)
 prior=json.loads(ai.PINS.read_text())
 for p in (ai.MIGRATION,ai.ROLLBACK):assert sha(p.read_bytes())==prior['source_pins'][str(p)]['sha256']
 defs=definitions(src)
 functions=[dict(identity=i,predecessor_sha256=sha(src[i][1]),installed_sha256=sha(d),
  owner=src[i][3],acl=sorted(src[i][2].strip('{}').split(','))) for i,d in zip(IDENTITIES,defs,strict=True)]
 old_rows={m:rows(prior['functions'],m) for m in ('predecessor','installed','restore')}
 new_rows={m:rows(functions,m) for m in old_rows}
 def advance(sql):
  for old,tag in (('v2620ai','__AJ_CAP__'),('v2.6.20ai','__AJ_VER__'),('AI_','__AJ_ERR__')):sql=sql.replace(old,tag)
  sql=sql.replace('v2620ah','v2620ai').replace('v2.6.20ah','v2.6.20ai')
  return sql.replace('__AJ_CAP__','v2620aj').replace('__AJ_VER__',VERSION).replace('__AJ_ERR__','AJ_').replace('<>221','<>222').replace('expected221','expected222')
 migration=advance(ai.MIGRATION.read_text());migration=migration[migration.index('begin;\n'):]
 migration='-- CP6 AJ: distinct rework lot identity and retained cost lineage; row import diagnostics.\n'+migration
 migration=replace(migration,"where p.oid in("+','.join("'"+i+"'::regprocedure" for i in ai.IDENTITIES)+");",
  "where p.oid in("+','.join("'"+i+"'::regprocedure" for i in IDENTITIES)+");")
 admission=f"""do $predecessor_v2620aj$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='{ai.VERSION}')
     or exists(select 1 from erp.schema_migrations where version='{VERSION}')
     or to_regclass('erp.cp6_v2620aj_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620ai_rollback_capsule') is null then raise exception 'AJ_REQUIRES_EXACT_AI_WITHOUT_AJ_RESIDUE'; end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='{ai.NAME}')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations where version='{ai.STAMP}' and name='{ai.NAME}'
       and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')='{sha(ai.MIGRATION.read_bytes())}')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'{ai.STAMP}')
     or (select count(*) from erp.cp6_v2620ai_rollback_capsule)<>3 then raise exception 'AJ_REQUIRES_EXACT_AI_PLATFORM_CAPSULE'; end if;
  for r in select * from(values
    {new_rows['predecessor']}
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') into v_actual
    from pg_proc p where p.oid=to_regprocedure(r.identity) and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then raise exception 'AJ_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity; end if;
  end loop;
end
$predecessor_v2620aj$;"""
 migration=block(migration,'do $predecessor_v2620aj$','$predecessor_v2620aj$;',admission)
 canonical='do $canonical_opening_v2620aj$\nbegin\n'+'\n'.join('  execute $definition$'+d+'$definition$;' for d in defs)+'\nend\n$canonical_opening_v2620aj$;'
 migration=block(migration,'do $canonical_opening_v2620aj$','$canonical_opening_v2620aj$;',canonical)
 migration=replace(migration,old_rows['installed'],new_rows['installed'])
 migration=migration.replace('(select count(*) from erp.cp6_v2620aj_rollback_capsule)<>3','(select count(*) from erp.cp6_v2620aj_rollback_capsule)<>6')
 migration=migration.replace('Work posting revalidates source PO, component, contractor and committed rate','Rework outputs retain separate identity and original cost source; import errors persist per row')
 MIGRATION.write_text(migration)
 rollback=advance(ai.ROLLBACK.read_text()).replace('-> exact AH.','-> exact AI.')
 for mode in old_rows:
  if old_rows[mode] in rollback:rollback=replace(rollback,old_rows[mode],new_rows[mode])
 rollback=rollback.replace(ai.STAMP,STAMP).replace(ai.NAME,NAME)
 rollback=rollback.replace(sha(ai.MIGRATION.read_bytes()),sha(migration)).replace(sha(ai.MIGRATION.read_text().removesuffix('\n')),sha(migration.removesuffix('\n')))
 rollback=rollback.replace('(select count(*) from erp.cp6_v2620aj_rollback_capsule)<>3','(select count(*) from erp.cp6_v2620aj_rollback_capsule)<>6')
 ROLLBACK.write_text(rollback)
 pins=dict(format='CP6_AJ_RUNTIME_PINS_V1',stamp=STAMP,name=NAME,version=VERSION,
  predecessor_head=PREDECESSOR_HEAD,predecessor_tree=PREDECESSOR_TREE,functions=functions,
  boundary_count=222,predecessor_function_count=533,predecessor_table_count=224,
  comparison_run=35145449818,production_go=False,source_pins={str(p):dict(sha256=sha(p.read_bytes()),bytes=p.stat().st_size)
  for p in (BUILDER,INPUT,CATALOG,ai.MIGRATION,ai.ROLLBACK,MIGRATION,ROLLBACK)})
 PINS.write_text(json.dumps(pins,indent=2)+'\n')
 print(json.dumps({'migration':sha(migration),'rollback':sha(rollback),'pins':sha(PINS.read_bytes())}));return pins

if __name__=='__main__':build()
