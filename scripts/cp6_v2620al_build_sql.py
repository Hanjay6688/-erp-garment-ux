#!/usr/bin/env python3
"""AL: validate imported values and prevent silent no-op opening postings."""
from pathlib import Path
import json
import cp6_v2620ak_build_sql as prior

# Created by pinned Supabase CLI 2.116.0 migration new.
STAMP='20260917054049'
NAME='erp_v2_6_20al_cp6_opening_value_validation'
VERSION='v2.6.20al'
PREDECESSOR_HEAD='684b708dee785934fe5fe4fe567c454cba873ea9'
PREDECESSOR_TREE='1f4c57517c0d4abd6612d4a8b36b2e9cbe437834'
MIGRATION=Path(f'supabase/migrations/{STAMP}_{NAME}.sql')
ROLLBACK=Path(f'supabase/rollbacks/{STAMP}_{NAME}.rollback.sql')
PINS=Path('docs/evidence/cp6-al-runtime-pins.json')
INPUT=Path('docs/evidence/cp6-al-predecessor-functions.json')
CATALOG=Path('docs/evidence/cp6-al-ak-catalog-pins.json')
BUILDER=Path('scripts/cp6_v2620al_build_sql.py')
IDENTITIES=('erp._validate_migration_batch_base(uuid)','erp.post_opening_balance(uuid)')
sha,replace,block,rows=prior.sha,prior.replace,prior.block,prior.rows

TYPED_PREVIEW="""    -- Validate only fields consumed by the matching writer. Composite casts
    -- enforce the actual column types/widths without inserting any master.
    -- Empty optional values retain the writers' existing default semantics.
    for ref in select * from(values
      ('BRAND','brands',array['brand_code','brand_name','is_active']),
      ('SIZE','sizes',array['size_code','sort_order','is_active']),
      ('MODEL','product_models',array['model_code','model_name','description','is_active']),
      ('PRODUCT','products',array['sku','product_name','color_name','is_active','is_portal_visible']),
      ('CUSTOMER','customers',array['customer_code','customer_name','phone','address','is_active']),
      ('SUPPLIER','suppliers',array['supplier_code','supplier_name','supplier_type','phone','address','is_active']),
      ('CONTRACTOR','contractors',array['contractor_code','contractor_name','contractor_type','attendance_required','is_active','notes']),
      ('ACCESSORY_CATEGORY','accessory_categories',array['category_code','category_name','base_uom_code','is_active','notes']),
      ('MATERIAL','materials',array['material_sku','material_name','material_type','unit_code','is_active']),
      ('MATERIAL_ROLL','material_rolls',array['roll_number','notes']),
      ('OPEN_PO','production_orders',array['po_number','target_qty_pcs','target_dozens','status','current_stage','physical_start_at','notes']),
      ('OPENING_BALANCE_ITEM','opening_balance_items',array['balance_type','qty','amount','stage','quality_grade','notes','hpp_input_method','hpp_percent_of_price'])
    ) fields(entity,relation_name,field_names) where fields.entity=r.entity_type loop
      select coalesce(jsonb_object_agg(field,r.normalized_payload->field),'{}'::jsonb)
        into v_typed from unnest(ref.field_names) field
        where nullif(r.normalized_payload->>field,'') is not null;
      begin
        execute format('select jsonb_populate_record(null::erp.%I,$1)',ref.relation_name) using v_typed;
      exception when data_exception then
        -- Retain the fast whole-row cast for valid imports. On a bad value,
        -- identify its field so the persisted row error tells the user what
        -- to repair; keep the original SQLSTATE and refusal semantics.
        for k in select jsonb_object_keys(v_typed) loop
          begin
            execute format('select jsonb_populate_record(null::erp.%I,$1)',ref.relation_name)
              using jsonb_build_object(k,v_typed->k);
          exception when data_exception then
            raise exception using errcode=sqlstate,message=format('%s: %s',k,sqlerrm);
          end;
        end loop;
        raise;
      end;
    end loop;
    if r.entity_type='SUPPLIER' and coalesce(nullif(upper(r.normalized_payload->>'supplier_type'),''),'MATERIAL')
      not in('MATERIAL','ACCESSORY','OTHER') then raise exception 'supplier_type must be MATERIAL, ACCESSORY or OTHER'; end if;
    if r.entity_type='OPEN_PO' then
      if nullif(r.normalized_payload->>'target_qty_pcs','') is not null
         and (r.normalized_payload->>'target_qty_pcs')::integer<=0 then raise exception 'target_qty_pcs must be positive'; end if;
      if nullif(r.normalized_payload->>'target_dozens','') is not null
         and (r.normalized_payload->>'target_dozens')::numeric<=0 then raise exception 'target_dozens must be positive'; end if;
    end if;
    if r.entity_type='MATERIAL_ROLL' then
      perform (r.normalized_payload->>'opening_qty')::numeric(18,6);
      perform (r.normalized_payload->>'unit_cost')::numeric(18,6);
    end if;
    if r.entity_type='OPENING_BALANCE_ITEM' then
      if nullif(r.normalized_payload->>'unit_cost','') is not null then
        perform (r.normalized_payload->>'unit_cost')::numeric(18,6);
      end if;
      if upper(r.normalized_payload->>'balance_type')='BS' then
        v_number:=nullif(r.normalized_payload->>'qty','')::numeric;
        if v_number is null or v_number<=0 or v_number<>trunc(v_number) or v_number>2147483647 then
          raise exception 'AL_BS_REQUIRES_POSITIVE_WHOLE_PCS';
        end if;
      end if;
      if upper(r.normalized_payload->>'balance_type')='WIP' then
        if nullif(r.normalized_payload->>'amount','') is null and
           (nullif(r.normalized_payload->>'qty','') is null or nullif(r.normalized_payload->>'unit_cost','') is null) then
          raise exception 'AL_WIP_REQUIRES_AMOUNT_OR_QTY_AND_COST';
        end if;
        foreach k in array array['qty','amount','unit_cost'] loop
          if nullif(r.normalized_payload->>k,'') is not null and (r.normalized_payload->>k)::numeric<0 then
            raise exception 'AL_WIP_VALUE_MUST_BE_NONNEGATIVE: %',k;
          end if;
        end loop;
      end if;
    end if;
"""

POST_PREFLIGHT="""
  -- Ordinary opening items remain editable while DRAFT. Validate the latest
  -- locked rows before any stock, BS, subledger or journal side effect.
  for r in select * from erp.opening_balance_items where opening_id=h.id order by id loop
    if r.qty::text in('NaN','Infinity','-Infinity')
       or r.amount::text in('NaN','Infinity','-Infinity')
       or r.unit_cost_snapshot::text in('NaN','Infinity','-Infinity')
       or r.hpp_percent_of_price::text in('NaN','Infinity','-Infinity')
       or r.reference_sell_price_snapshot::text in('NaN','Infinity','-Infinity') then
      raise exception 'AL_OPENING_VALUES_MUST_BE_FINITE';
    end if;
    if r.balance_type='BS' and
       (r.qty is null or r.qty<=0 or r.qty<>trunc(r.qty) or r.qty>2147483647) then
      raise exception 'AL_BS_REQUIRES_POSITIVE_WHOLE_PCS';
    end if;
    if r.balance_type='WIP' then
      if r.amount is null and (r.qty is null or r.unit_cost_snapshot is null) then
        raise exception 'AL_WIP_REQUIRES_AMOUNT_OR_QTY_AND_COST';
      end if;
      if r.amount<0 or r.qty<0 or r.unit_cost_snapshot<0 then
        raise exception 'AL_WIP_VALUE_MUST_BE_NONNEGATIVE';
      end if;
    end if;
  end loop;
"""


def definitions(src):
    preview=replace(src[IDENTITIES[0]][1],'v_code text;v_exists boolean;','v_code text;v_exists boolean;v_typed jsonb;')
    preview=replace(preview,"    if r.entity_type='ACCESSORY_CATEGORY'",TYPED_PREVIEW+"    if r.entity_type='ACCESSORY_CATEGORY'")
    post=replace(src[IDENTITIES[1]][1],
        '  where i.opening_id=h.id order by i.id for update;\n',
        '  where i.opening_id=h.id order by i.id for update;\n'+POST_PREFLIGHT)
    return [preview,post]


def build():
    original=json.loads(INPUT.read_text())
    assert (original['head'],original['tree'])==(PREDECESSOR_HEAD,PREDECESSOR_TREE)
    src={r[0]:r for r in original['functions']};assert set(src)==set(IDENTITIES)
    p=json.loads(prior.PINS.read_text())
    for path in (prior.MIGRATION,prior.ROLLBACK):
        assert sha(path.read_bytes())==p['source_pins'][str(path)]['sha256']
    defs=definitions(src)
    functions=[dict(identity=i,predecessor_sha256=sha(src[i][1]),installed_sha256=sha(d),owner=src[i][3],
                   acl=sorted(src[i][2].strip('{}').split(','))) for i,d in zip(IDENTITIES,defs,strict=True)]
    old={m:rows(p['functions'],m) for m in ('predecessor','installed','restore')}
    new={m:rows(functions,m) for m in old}
    def advance(sql):
        for before,tag in (('v2620ak','__AL_CAP__'),('v2.6.20ak','__AL_VER__'),('AK_','__AL_ERR__')):
            sql=sql.replace(before,tag)
        sql=sql.replace('v2620aj','v2620ak').replace('v2.6.20aj','v2.6.20ak')
        return sql.replace('__AL_CAP__','v2620al').replace('__AL_VER__',VERSION).replace('__AL_ERR__','AL_').replace('<>223','<>224').replace('expected223','expected224')
    migration=advance(prior.MIGRATION.read_text())
    migration='-- CP6 AL: complete opening values and typed row diagnostics.\n'+migration[migration.index('begin;\n'):]
    migration=replace(migration,"where p.oid in("+','.join("'"+i+"'::regprocedure" for i in prior.IDENTITIES)+");",
                      "where p.oid in("+','.join("'"+i+"'::regprocedure" for i in IDENTITIES)+");")
    admission=f"""do $predecessor_v2620al$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='{prior.VERSION}')
     or exists(select 1 from erp.schema_migrations where version='{VERSION}')
     or to_regclass('erp.cp6_v2620al_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620ak_rollback_capsule') is null then raise exception 'AL_REQUIRES_EXACT_AK_WITHOUT_AL_RESIDUE'; end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='{prior.NAME}')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations where version='{prior.STAMP}' and name='{prior.NAME}'
       and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')='{sha(prior.MIGRATION.read_bytes())}')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'{prior.STAMP}')
     or (select count(*) from erp.cp6_v2620ak_rollback_capsule)<>8 then raise exception 'AL_REQUIRES_EXACT_AK_PLATFORM_CAPSULE'; end if;
  for r in select * from(values
    {new['predecessor']}
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') into v_actual
    from pg_proc p where p.oid=to_regprocedure(r.identity) and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then raise exception 'AL_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity; end if;
  end loop;
end
$predecessor_v2620al$;"""
    migration=block(migration,'do $predecessor_v2620al$','$predecessor_v2620al$;',admission)
    canonical='do $canonical_opening_v2620al$\nbegin\n'+'\n'.join('  execute $definition$'+d+'$definition$;' for d in defs)+'\nend\n$canonical_opening_v2620al$;'
    migration=block(migration,'do $canonical_opening_v2620al$','$canonical_opening_v2620al$;',canonical)
    migration=replace(migration,old['installed'],new['installed'])
    migration=migration.replace('(select count(*) from erp.cp6_v2620al_rollback_capsule)<>8','(select count(*) from erp.cp6_v2620al_rollback_capsule)<>2')
    migration=migration.replace('Import preview resolves references; draft edits invalidate prepared lines without touching posted history','Opening BS and WIP values are checked before posting; master type errors persist per row')
    MIGRATION.write_text(migration)
    rollback=advance(prior.ROLLBACK.read_text()).replace('-> exact AJ.','-> exact AK.')
    rollback=rollback.replace('(select count(*) from erp.cp6_v2620al_rollback_capsule)<>8','(select count(*) from erp.cp6_v2620al_rollback_capsule)<>2')
    for mode in old:
        if old[mode] in rollback:rollback=rollback.replace(old[mode],new[mode])
    rollback=rollback.replace(prior.STAMP,STAMP).replace(prior.NAME,NAME)
    rollback=rollback.replace(sha(prior.MIGRATION.read_bytes()),sha(migration)).replace(sha(prior.MIGRATION.read_text().removesuffix('\n')),sha(migration.removesuffix('\n')))
    ROLLBACK.write_text(rollback)
    pins=dict(format='CP6_AL_RUNTIME_PINS_V1',stamp=STAMP,name=NAME,version=VERSION,
        predecessor_head=PREDECESSOR_HEAD,predecessor_tree=PREDECESSOR_TREE,functions=functions,
        boundary_count=224,predecessor_function_count=533,predecessor_table_count=226,
        comparison_run=35186147113,production_go=False,source_pins={str(path):dict(sha256=sha(path.read_bytes()),bytes=path.stat().st_size)
        for path in (BUILDER,INPUT,CATALOG,prior.MIGRATION,prior.ROLLBACK,MIGRATION,ROLLBACK)})
    PINS.write_text(json.dumps(pins,indent=2)+'\n')
    print(json.dumps({'migration':sha(migration),'rollback':sha(rollback),'pins':sha(PINS.read_bytes())}))
    return pins


if __name__=='__main__':
    build()
