-- Capture requirements from Native masters. An issue or a valuation snapshot
-- is not proof of installation, eligible unused stock or job allocation.
create schema cp7_analysis_native authorization cp7_capture;
revoke all on schema cp7_analysis_native from public,anon,authenticated,service_role;
grant select on erp.accessory_bom_versions,erp.accessory_bom_items,erp.accessory_categories to cp7_capture;

create function cp7_analysis_native.material_source(products jsonb,p_at timestamptz)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with roots as materialized(select distinct (x->>'root_id')::uuid id from jsonb_array_elements(products)x),
 versions as materialized(select v.id,v.product_id,v.effective_from,v.effective_to,v.is_active,v.created_at
  from erp.accessory_bom_versions v join roots r on r.id=v.product_id where v.created_at<=p_at),
 items as materialized(select i.id,i.bom_version_id,i.category_id,i.qty_per_good_fg_base::text qty_per_good_fg_base
  from erp.accessory_bom_items i join versions v on v.id=i.bom_version_id),
 categories as materialized(select c.id,c.category_code,c.category_name,c.base_uom_code,c.is_active,c.row_version::text revision
  from erp.accessory_categories c where exists(select 1 from items i where i.category_id=c.id)),
 selected as materialized(select r.id root_id,
  (select count(*)from versions v where v.product_id=r.id and v.is_active and v.effective_from<=p_at
   and(v.effective_to is null or v.effective_to>p_at)) effective_version_count,
  (select v.id from versions v where v.product_id=r.id and v.is_active and v.effective_from<=p_at
   and(v.effective_to is null or v.effective_to>p_at)order by v.effective_from desc,v.id limit 1) version_id from roots r)
 select jsonb_build_object('contract_version','cp7.native-material-source.v1','captured_at',p_at,
  'scope','CURRENT_NATIVE_ACCESSORY_BOM_FOR_NEW_START_EXACT_PHYSICAL_ROOT',
  'selected',coalesce((select jsonb_agg(to_jsonb(s)order by s.root_id)from selected s),'[]'::jsonb),
  'versions',coalesce((select jsonb_agg(to_jsonb(v)order by v.id)from versions v),'[]'::jsonb),
  'items',coalesce((select jsonb_agg(to_jsonb(i)order by i.id)from items i),'[]'::jsonb),
  'categories',coalesce((select jsonb_agg(to_jsonb(c)order by c.id)from categories c),'[]'::jsonb),
  'installation_authority','NO_NATIVE_BOM_COST_SNAPSHOT_OR_ISSUE_IS_INSTALLATION_PROOF')
$$;

create function cp7_analysis_native.material_needs(c jsonb,r jsonb,assumptions jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare source jsonb:=c->'material_source';selected jsonb;version jsonb;item jsonb;category jsonb;
 refs jsonb:=r->'refs';item_refs jsonb;outcome jsonb:='[]';unit text;gross text;reason text;
 root text:=split_part(r->>'target_key',':',1);signature text;
begin
 select value into selected from jsonb_array_elements(source->'selected')where value->>'root_id'=root;
 if selected is null or(selected->>'effective_version_count')::integer<>1 then
  reason:=case when selected is not null and(selected->>'effective_version_count')::integer>1
   then 'BOM yang berlaku saling tumpang tindih; periksa versi sebelum menghitung kebutuhan.'
   else 'BOM aksesori yang berlaku belum tercatat. Kosong tidak berarti tanpa aksesori.'end;
  return jsonb_build_array(jsonb_build_object('target_key',r->'target_key','material_key',null,
   'gross',cp7_analysis_native.fact(null,'MATERIAL_BASE_UNIT',refs),
   'installed_proven',cp7_analysis_native.fact(null,'MATERIAL_BASE_UNIT',refs),
   'unused_allocated_proven',cp7_analysis_native.fact(null,'MATERIAL_BASE_UNIT',refs),
   'additional_external',cp7_analysis_native.fact(null,'MATERIAL_BASE_UNIT',refs),'reason',reason));
 end if;
 select value into version from jsonb_array_elements(source->'versions')where value->>'id'=selected->>'version_id';
 signature:=encode(extensions.digest(convert_to(version::text,'UTF8'),'sha256'),'hex');
 refs:=refs||jsonb_build_array(cp7_wip.ref('erp.accessory_bom_versions',version->>'id',signature));
 if not exists(select 1 from jsonb_array_elements(source->'items')x where x->>'bom_version_id'=version->>'id')then
  -- Explicitly empty means no accessory, even with an unreviewed quantity.
  -- This is not proof of fabric or production readiness.
  return jsonb_build_array(jsonb_build_object('target_key',r->'target_key','material_key','NO_ACCESSORY:'||root,
   'gross',cp7_analysis_native.fact('0','ACCESSORY_BASE_UNIT',refs),
   'installed_proven',cp7_analysis_native.fact('0','ACCESSORY_BASE_UNIT',refs),
   'unused_allocated_proven',cp7_analysis_native.fact('0','ACCESSORY_BASE_UNIT',refs),
   'additional_external',cp7_analysis_native.fact('0','ACCESSORY_BASE_UNIT',refs),
   'reason','BOM tercatat tanpa aksesori. Kain dan kemampuan produksi tetap perlu diperiksa.'));
 end if;
 for item in select value from jsonb_array_elements(source->'items')where value->>'bom_version_id'=version->>'id'order by value->>'id'loop
  select value into category from jsonb_array_elements(source->'categories')where value->>'id'=item->>'category_id';
  unit:=coalesce(category->>'base_uom_code','MATERIAL_BASE_UNIT');
  item_refs:=refs||jsonb_build_array(cp7_wip.ref('erp.accessory_bom_items',item->>'id',
   encode(extensions.digest(convert_to(item::text,'UTF8'),'sha256'),'hex')));
  if category is not null then item_refs:=item_refs||jsonb_build_array(cp7_wip.ref('erp.accessory_categories',category->>'id',category->>'revision'));end if;
  gross:=null;
  if category->'is_active'='true'::jsonb and r->>'conditional_gap_pcs'is not null then
   gross:=((r->>'conditional_gap_pcs')::numeric*(item->>'qty_per_good_fg_base')::numeric)::text;
  end if;
  -- Category identity/valuation does not prove physical interchangeability.
  -- Warehouse stock is not job-allocated stock. FG/issue/HPP is not installed.
  reason:=coalesce(category->>'category_name','Kategori aksesori belum terbukti')||
   ': kebutuhan BOM untuk rencana baru; pemasangan dan sisa yang dialokasikan belum terbukti. Pengeluaran bukan pemasangan.';
  if category->'is_active'is distinct from'true'::jsonb then reason:='Kategori BOM belum aktif atau tidak terbukti; periksa bahan.';end if;
  outcome:=outcome||jsonb_build_array(jsonb_build_object('target_key',r->'target_key',
   'material_key','ACCESSORY_CATEGORY:'||(item->>'category_id'),'gross',cp7_analysis_native.fact(gross,unit,item_refs,assumptions),
   'installed_proven',cp7_analysis_native.fact(null,unit,item_refs),
   'unused_allocated_proven',cp7_analysis_native.fact(null,unit,item_refs),
   'additional_external',cp7_analysis_native.fact(null,unit,item_refs),'reason',reason));
 end loop;
 return outcome;
end $$;
