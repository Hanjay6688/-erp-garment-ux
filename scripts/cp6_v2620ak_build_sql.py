#!/usr/bin/env python3
"""AK: preview resolves the same reference graph that import consumers use."""
from pathlib import Path
import json
import cp6_v2620aj_build_sql as prior

# Created with Supabase CLI 2.116.0 migration new, not a renamed admitted SQL.
STAMP='20260917033516'
NAME='erp_v2_6_20ak_cp6_import_reference_preview'
VERSION='v2.6.20ak'
PREDECESSOR_HEAD='47671d9ba2cfb8d02658388adb364b2ae6b89e8d'
PREDECESSOR_TREE='46f4f605444c72dc32282025b859ab66375178b3'
MIGRATION=Path(f'supabase/migrations/{STAMP}_{NAME}.sql')
ROLLBACK=Path(f'supabase/rollbacks/{STAMP}_{NAME}.rollback.sql')
PINS=Path('docs/evidence/cp6-ak-runtime-pins.json')
INPUT=Path('docs/evidence/cp6-ak-predecessor-functions.json')
CATALOG=Path('docs/evidence/cp6-ak-aj-catalog-pins.json')
BUILDER=Path('scripts/cp6_v2620ak_build_sql.py')
IDENTITIES=('erp._validate_migration_batch_base(uuid)',
 'erp.validate_migration_opening_stock_costs(uuid)',
 'erp.prepare_migration_opening_balance(uuid,text)',
 'erp.apply_migration_master_rows(uuid)','erp.apply_migration_open_pos(uuid)',
 'erp.finalize_migration_batch(uuid)',
 'erp.stage_migration_row(uuid,text,integer,text,jsonb,jsonb)',
 'erp.post_opening_balance(uuid)')
sha,replace,block,rows=prior.sha,prior.replace,prior.block,prior.rows

PREVIEW_GUARD="""  select status into v_status from erp.migration_batches where id=p_batch_id for update;
  if v_status is null then raise exception 'Migration batch not found'; end if;
  if v_status not in('DRAFT','VALIDATING','READY','POSTING')
     or exists(select 1 from erp.opening_balance_headers where migration_batch_id=p_batch_id and status<>'DRAFT') then
    raise exception 'AK_MIGRATION_PREVIEW_AFTER_POSTING_REFUSED';
  end if;
"""

REFERENCES="""    -- Topological order matches apply_migration_master_rows. A staged parent
    -- must itself be VALID; presence alone never proves a usable reference.
    for ref in select * from(values
      ('material_sku','materials','material_sku','MATERIAL',array['MATERIAL_ROLL','OPENING_BALANCE_ITEM']),
      ('model_code','product_models','model_code','MODEL',array['PRODUCT','OPEN_PO','OPENING_BALANCE_ITEM']),
      ('brand_code','brands','brand_code','BRAND',array['PRODUCT']),
      ('size_code','sizes','size_code','SIZE',array['PRODUCT']),
      ('accessory_category_code','accessory_categories','category_code','ACCESSORY_CATEGORY',array['MATERIAL']),
      ('unit_code','uom_definitions','unit_code',null,array['MATERIAL']),
      ('contractor_code','contractors','contractor_code','CONTRACTOR',array['OPEN_PO','OPENING_BALANCE_ITEM']),
      ('customer_code','customers','customer_code','CUSTOMER',array['OPENING_BALANCE_ITEM']),
      ('supplier_code','suppliers','supplier_code','SUPPLIER',array['MATERIAL_ROLL','OPENING_BALANCE_ITEM']),
      ('location_code','locations','location_code',null,array['MATERIAL_ROLL','OPENING_BALANCE_ITEM']),
      ('vendor_code','laundry_vendors','vendor_code',null,array['OPENING_BALANCE_ITEM']),
      ('cash_account_code','cash_accounts','cash_account_code',null,array['OPENING_BALANCE_ITEM'])
    ) refs(field,relation_name,code_field,staged_type,consumers)
    where r.entity_type=any(refs.consumers) loop
      v_code:=r.normalized_payload->>ref.field;
      if nullif(btrim(v_code),'') is null then continue; end if;
      if ref.field='unit_code' then v_code:=upper(v_code); end if;
      -- Identifiers are selected only from the constant allowlist above.
      execute format('select exists(select 1 from erp.%I where %I=$1)',ref.relation_name,ref.code_field)
        into v_exists using v_code;
      if not v_exists and not exists(select 1 from erp.migration_staging_rows s
        where s.batch_id=p_batch_id and s.entity_type=ref.staged_type
          and s.validation_status='VALID' and s.normalized_payload->>ref.code_field=v_code) then
        e:=e||jsonb_build_array('Unknown or invalid staged reference: '||ref.field||' = '||v_code);
      end if;
    end loop;
    if r.entity_type='OPENING_BALANCE_ITEM' and v_bt='MATERIAL'
       and exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id
         and s.entity_type='MATERIAL' and s.validation_status='VALID'
         and s.normalized_payload->>'material_sku'=r.normalized_payload->>'material_sku'
         and upper(s.normalized_payload->>'material_type')='FABRIC') then
      e:=e||jsonb_build_array('FABRIC opening stock must use MATERIAL_ROLL rows');
    end if;
    if r.entity_type='PRODUCT' then
      -- Import may maintain display data, never rewrite identity/history.
      if exists(select 1 from erp.products p join erp.brands b on b.id=p.brand_id
        join erp.sizes sz on sz.id=p.size_id join erp.product_models m on m.id=p.model_id
        where b.brand_code=r.normalized_payload->>'brand_code'
          and sz.size_code=r.normalized_payload->>'size_code'
          and lower(btrim(p.sku))=lower(btrim(r.normalized_payload->>'sku'))
      ) and not exists(select 1 from erp.products p join erp.brands b on b.id=p.brand_id
        join erp.sizes sz on sz.id=p.size_id join erp.product_models m on m.id=p.model_id
        where b.brand_code=r.normalized_payload->>'brand_code'
          and sz.size_code=r.normalized_payload->>'size_code'
          and lower(btrim(p.sku))=lower(btrim(r.normalized_payload->>'sku'))
          and p.effective_from<=v_cutover and (p.effective_to is null or p.effective_to>v_cutover)
          and m.model_code=r.normalized_payload->>'model_code'
          and lower(btrim(p.color_name))=lower(btrim(r.normalized_payload->>'color_name'))) then
        e:=e||jsonb_build_array('PRODUCT identity/history conflicts at migration cutover');
      end if;
    end if;
"""

PRODUCT_PREVIEW="""    if nullif(btrim(j->>'product_sku'),'') is not null then
      -- Same historical matching rule as resolve_opening_product_identity.
      -- New, valid staged roots are included without creating any master row.
      with candidates as (
        select p.id,lower(btrim(p.sku)) sku,lower(btrim(p.color_name)) color_name,
          lower(btrim(sz.size_code)) size_code,lower(btrim(pm.model_code)) model_code,
          lower(btrim(br.brand_code)) brand_code
        from erp.products p join erp.sizes sz on sz.id=p.size_id
        join erp.product_models pm on pm.id=p.model_id join erp.brands br on br.id=p.brand_id
        where p.effective_from<=v_cutover
        union all
        select null::uuid,lower(btrim(s.normalized_payload->>'sku')),
          lower(btrim(s.normalized_payload->>'color_name')),lower(btrim(s.normalized_payload->>'size_code')),
          lower(btrim(s.normalized_payload->>'model_code')),lower(btrim(s.normalized_payload->>'brand_code'))
        from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.entity_type='PRODUCT'
          and s.validation_status='VALID' and not exists(
            select 1 from erp.products p join erp.brands br on br.id=p.brand_id join erp.sizes sz on sz.id=p.size_id
            where br.brand_code=s.normalized_payload->>'brand_code' and sz.size_code=s.normalized_payload->>'size_code'
              and lower(btrim(p.sku))=lower(btrim(s.normalized_payload->>'sku')))
      ) select count(*),(array_agg(id))[1] into v_count,v_product from candidates c
      where c.sku=lower(btrim(j->>'product_sku'))
        and (nullif(btrim(j->>'color_name'),'') is null or c.color_name=lower(btrim(j->>'color_name')))
        and (nullif(btrim(j->>'size_code'),'') is null or c.size_code=lower(btrim(j->>'size_code')))
        and (nullif(btrim(j->>'model_code'),'') is null or c.model_code=lower(btrim(j->>'model_code')))
        and (nullif(btrim(j->>'brand_code'),'') is null or c.brand_code=lower(btrim(j->>'brand_code')));
      if v_count<>1 then raise exception 'Opening product_sku must resolve exactly one identity at cutover (found %)',v_count; end if;
    end if;
    if v_bt='FINISHED_GOODS' then
      if nullif(btrim(j->>'location_code'),'') is null
         and (select count(*) from erp.locations where is_active and location_type='FG_WAREHOUSE')<>1 then
        raise exception 'Opening FG requires location when active FG warehouse count is not exactly one';
      end if;
      if v_method='PRICE_PERCENT' then
        if (j->>'hpp_percent_of_price')::numeric>1000 then raise exception 'Opening FG HPP percentage exceeds 1000'; end if;
        if v_product is null or erp.resolve_product_price_at(v_product,
          erp.product_opening_physical_at(v_product,(v_cutover at time zone 'Asia/Jakarta')::date)) is null then
          raise exception 'Opening FG selling price unavailable at cutover; use explicit manual HPP';
        end if;
      end if;
    end if;
"""

def definitions(src):
 base=replace(src[IDENTITIES[0]][1],'v_number numeric;',
  'v_number numeric;v_status text;v_cutover timestamptz;ref record;v_code text;v_exists boolean;')
 base=replace(base,"  if not exists(select 1 from erp.migration_batches where id=p_batch_id) then raise exception 'Migration batch not found'; end if;\n",
  PREVIEW_GUARD+"  select cutover_at into v_cutover from erp.migration_batches where id=p_batch_id;\n")
 # Parents become VALID before consumers inspect them, independently of CSV order.
 base=replace(base,'order by entity_type,source_row_no loop',"""order by case entity_type
      when 'BRAND' then 10 when 'SIZE' then 20 when 'MODEL' then 30
      when 'CUSTOMER' then 40 when 'SUPPLIER' then 50 when 'CONTRACTOR' then 60
      when 'ACCESSORY_CATEGORY' then 70 when 'MATERIAL' then 80 when 'MATERIAL_ROLL' then 85
      when 'PRODUCT' then 90 when 'OPEN_PO' then 100 else 110 end,source_row_no loop""")
 dup="""  with keys as (
    select id,entity_type,case entity_type
      when 'PRODUCT' then jsonb_build_array(normalized_payload->>'brand_code',lower(btrim(normalized_payload->>'sku')),normalized_payload->>'size_code')
      else jsonb_build_array(normalized_payload->>case entity_type
        when 'BRAND' then 'brand_code' when 'SIZE' then 'size_code' when 'MODEL' then 'model_code'
        when 'CUSTOMER' then 'customer_code' when 'SUPPLIER' then 'supplier_code' when 'CONTRACTOR' then 'contractor_code'
        when 'ACCESSORY_CATEGORY' then 'category_code' when 'MATERIAL' then 'material_sku' when 'OPEN_PO' then 'po_number' end) end business_key
    from erp.migration_staging_rows where batch_id=p_batch_id and entity_type not in('MATERIAL_ROLL','OPENING_BALANCE_ITEM')
  ) update erp.migration_staging_rows s set validation_status='ERROR',
      validation_errors=s.validation_errors||jsonb_build_array('Duplicate master/PO identity inside migration batch')
    where s.id in(select k.id from keys k where exists(select 1 from keys d
      where d.id<>k.id and d.entity_type=k.entity_type and d.business_key=k.business_key));

"""
 base=replace(base,'  for r in select * from erp.migration_staging_rows',dup+'  for r in select * from erp.migration_staging_rows')
 base=replace(base,'    exception when others then\n',REFERENCES+'    exception when others then\n')
 base=replace(base,"and mr.roll_number=r.normalized_payload->>'roll_number') then", "and mr.roll_number=r.normalized_payload->>'roll_number' and mr.id is distinct from r.posted_entity_id) then")
 cost=replace(src[IDENTITIES[1]][1],'v_number numeric;',
  'v_number numeric;v_status text;v_cutover timestamptz;v_count integer;')
 cost=replace(cost,'  perform erp.require_owner_admin();\n','  perform erp.require_owner_admin();\n'+PREVIEW_GUARD+
  '  select cutover_at into v_cutover from erp.migration_batches where id=p_batch_id;\n')
 start=cost.index('      begin\n        v_product:=erp.resolve_opening_product_identity(')
 end=cost.index('      end;\n',start)+len('      end;\n')
 cost=cost[:start]+cost[end:]
 cost=replace(cost,'    exception when others then\n',PRODUCT_PREVIEW+'    exception when others then\n')
 prepare=replace(src[IDENTITIES[2]][1],"limit 1;return v_header;end if;", "limit 1;\n    perform 1 from erp.opening_balance_headers where id=v_header for update;\n    if exists(select 1 from erp.opening_balance_items where opening_id=v_header) then return v_header;end if;\n    if (select status from erp.opening_balance_headers where id=v_header)<>'DRAFT' then raise exception 'AK_POSTED_OPENING_REBUILD_REFUSED';end if;\n  end if;")
 prepare=replace(prepare,"insert into erp.opening_balance_headers(","if v_header is null then insert into erp.opening_balance_headers(")
 prepare=replace(prepare,"returning id into v_header;\n", "returning id into v_header;end if;\n")
 master=replace(src[IDENTITIES[3]][1],'  perform erp.require_owner_admin();\n',
  "  perform erp.require_owner_admin();\n  perform 1 from erp.migration_batches where id=p_batch_id for update;\n  if not found then raise exception 'Migration batch not found'; end if;\n")
 master=replace(master,"where batch_id=p_batch_id and validation_status='VALID'\n", "where batch_id=p_batch_id and validation_status='VALID' and posted_entity_id is null\n")
 pos=replace(src[IDENTITIES[4]][1],"FOR r IN SELECT *", "IF EXISTS(SELECT 1 FROM erp.migration_staging_rows WHERE batch_id=p_batch_id AND validation_status<>'VALID') THEN RAISE EXCEPTION 'Migration batch contains unvalidated/error rows'; END IF; UPDATE erp.migration_batches SET status='POSTING' WHERE id=p_batch_id; FOR r IN SELECT *")
 pos=replace(pos,"AND entity_type='OPEN_PO' AND validation_status='VALID'", "AND entity_type='OPEN_PO' AND validation_status='VALID' AND posted_entity_id IS NULL")
 final=replace(src[IDENTITIES[5]][1],"if v_status not in('READY','POSTING')", "if v_status is null then raise exception 'Migration batch not found';end if;if v_status='POSTED' then return;end if;if v_status not in('READY','POSTING')")
 stage=replace(src[IDENTITIES[6]][1],"('DRAFT','VALIDATING','READY')", "('DRAFT','VALIDATING','READY','POSTING')")
 stage=replace(stage,"  if p_source_row_no is null", """  -- Lock order is batch -> opening in both the editor and posting consumer.
  perform 1 from erp.opening_balance_headers where migration_batch_id=p_batch_id order by id for update;
  if exists(select 1 from erp.opening_balance_headers where migration_batch_id=p_batch_id and status<>'DRAFT') then
    raise exception 'AK_MIGRATION_STAGE_AFTER_POSTING_REFUSED';
  end if;
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type=v_type
    and source_row_no=p_source_row_no and posted_entity_id is not null and entity_type<>'OPENING_BALANCE_ITEM') then
    raise exception 'AK_APPLIED_MASTER_ROW_EDIT_REQUIRES_MASTER_CORRECTION';
  end if;
  if p_source_row_no is null""")
 stage=replace(stage,"  update erp.migration_batches set status='DRAFT'", """  -- Prepared opening is still a draft: edits remain allowed. Invalidate only
  -- its unposted lines, keep the header identity, and require fresh prepare.
  delete from erp.opening_balance_items i using erp.opening_balance_headers h
    where i.opening_id=h.id and h.migration_batch_id=p_batch_id and h.status='DRAFT';
  update erp.migration_staging_rows set posted_entity_type=null,posted_entity_id=null,posted_at=null
    where batch_id=p_batch_id and entity_type='OPENING_BALANCE_ITEM';
  update erp.migration_batches set status='DRAFT'""")
 post=replace(src[IDENTITIES[7]][1],"  select * into h from erp.opening_balance_headers where id=p_opening_id for update;", """  -- Serialize with staging before taking the header lock. A revalidated
  -- preview alone cannot revive the obsolete prepared lines removed by edit.
  perform 1 from erp.migration_batches b where b.id=(select migration_batch_id
    from erp.opening_balance_headers where id=p_opening_id) for update;
  if exists(select 1 from erp.migration_batches b join erp.opening_balance_headers h on h.migration_batch_id=b.id
    where h.id=p_opening_id and (b.status not in('READY','POSTING') or exists(
      select 1 from erp.migration_staging_rows s where s.batch_id=b.id and s.validation_status<>'VALID'))) then
    raise exception 'AK_OPENING_REQUIRES_CURRENT_VALIDATED_BATCH';
  end if;
  select * into h from erp.opening_balance_headers where id=p_opening_id for update;""")
 return [base,cost,prepare,master,pos,final,stage,post]

def build():
 original=json.loads(INPUT.read_text());assert (original['head'],original['tree'])==(PREDECESSOR_HEAD,PREDECESSOR_TREE)
 src={r[0]:r for r in original['functions']};assert set(src)==set(IDENTITIES)
 p=json.loads(prior.PINS.read_text())
 for path in (prior.MIGRATION,prior.ROLLBACK):assert sha(path.read_bytes())==p['source_pins'][str(path)]['sha256']
 defs=definitions(src)
 functions=[dict(identity=i,predecessor_sha256=sha(src[i][1]),installed_sha256=sha(d),owner=src[i][3],
   acl=sorted(src[i][2].strip('{}').split(','))) for i,d in zip(IDENTITIES,defs,strict=True)]
 old={m:rows(p['functions'],m) for m in ('predecessor','installed','restore')}
 new={m:rows(functions,m) for m in old}
 def advance(sql):
  for before,tag in (('v2620aj','__AK_CAP__'),('v2.6.20aj','__AK_VER__'),('AJ_','__AK_ERR__')):sql=sql.replace(before,tag)
  sql=sql.replace('v2620ai','v2620aj').replace('v2.6.20ai','v2.6.20aj')
  return sql.replace('__AK_CAP__','v2620ak').replace('__AK_VER__',VERSION).replace('__AK_ERR__','AK_').replace('<>222','<>223').replace('expected222','expected223')
 migration=advance(prior.MIGRATION.read_text());migration=migration[migration.index('begin;\n'):]
 migration='-- CP6 AK: complete reference preview and editable current opening drafts.\n'+migration
 migration=replace(migration,"where p.oid in("+','.join("'"+i+"'::regprocedure" for i in prior.IDENTITIES)+");", "where p.oid in("+','.join("'"+i+"'::regprocedure" for i in IDENTITIES)+");")
 admission=f"""do $predecessor_v2620ak$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='{prior.VERSION}')
     or exists(select 1 from erp.schema_migrations where version='{VERSION}')
     or to_regclass('erp.cp6_v2620ak_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620aj_rollback_capsule') is null then raise exception 'AK_REQUIRES_EXACT_AJ_WITHOUT_AK_RESIDUE'; end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='{prior.NAME}')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations where version='{prior.STAMP}' and name='{prior.NAME}'
       and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')='{sha(prior.MIGRATION.read_bytes())}')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'{prior.STAMP}')
     or (select count(*) from erp.cp6_v2620aj_rollback_capsule)<>6 then raise exception 'AK_REQUIRES_EXACT_AJ_PLATFORM_CAPSULE'; end if;
  for r in select * from(values
    {new['predecessor']}
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') into v_actual
    from pg_proc p where p.oid=to_regprocedure(r.identity) and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then raise exception 'AK_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity; end if;
  end loop;
end
$predecessor_v2620ak$;"""
 migration=block(migration,'do $predecessor_v2620ak$','$predecessor_v2620ak$;',admission)
 canonical='do $canonical_opening_v2620ak$\nbegin\n'+'\n'.join('  execute $definition$'+d+'$definition$;' for d in defs)+'\nend\n$canonical_opening_v2620ak$;'
 migration=block(migration,'do $canonical_opening_v2620ak$','$canonical_opening_v2620ak$;',canonical)
 migration=replace(migration,old['installed'],new['installed'])
 migration=migration.replace('(select count(*) from erp.cp6_v2620ak_rollback_capsule)<>6','(select count(*) from erp.cp6_v2620ak_rollback_capsule)<>8')
 migration=migration.replace('Rework outputs retain separate identity and original cost source; import errors persist per row','Import preview resolves references; draft edits invalidate prepared lines without touching posted history')
 MIGRATION.write_text(migration)
 rollback=advance(prior.ROLLBACK.read_text()).replace('-> exact AI.','-> exact AJ.')
 rollback=rollback.replace('(select count(*) from erp.cp6_v2620ak_rollback_capsule)<>6','(select count(*) from erp.cp6_v2620ak_rollback_capsule)<>8')
 for mode in old:
  if old[mode] in rollback:rollback=replace(rollback,old[mode],new[mode])
 rollback=rollback.replace(prior.STAMP,STAMP).replace(prior.NAME,NAME)
 rollback=rollback.replace(sha(prior.MIGRATION.read_bytes()),sha(migration)).replace(sha(prior.MIGRATION.read_text().removesuffix('\n')),sha(migration.removesuffix('\n')))
 ROLLBACK.write_text(rollback)
 pins=dict(format='CP6_AK_RUNTIME_PINS_V1',stamp=STAMP,name=NAME,version=VERSION,
  predecessor_head=PREDECESSOR_HEAD,predecessor_tree=PREDECESSOR_TREE,functions=functions,
  boundary_count=223,predecessor_function_count=533,predecessor_table_count=225,
  comparison_run=35176804544,production_go=False,source_pins={str(path):dict(sha256=sha(path.read_bytes()),bytes=path.stat().st_size)
  for path in (BUILDER,INPUT,CATALOG,prior.MIGRATION,prior.ROLLBACK,MIGRATION,ROLLBACK)})
 PINS.write_text(json.dumps(pins,indent=2)+'\n')
 print(json.dumps({'migration':sha(migration),'rollback':sha(rollback),'pins':sha(PINS.read_bytes())}));return pins

if __name__=='__main__':build()
