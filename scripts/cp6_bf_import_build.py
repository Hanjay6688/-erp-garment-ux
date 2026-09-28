"""PR29 SR03–05: identical resolution at validation/apply; native guards stay intact."""
import json,re
from pathlib import Path
from cp6_bc_build import last_definition,substitute
REPLACED=['erp.save_initial_import_action_v1(text,jsonb,uuid)','erp.bb_check_sales_import_row_v1(uuid,uuid)','erp.bb_apply_sales_imports_v1(uuid)',
 'erp.bc_check_import_row_v1(uuid,uuid)','erp.bc_apply_imports_v1(uuid)',
 'erp.be_check_pocket_import_v1(uuid,uuid)','erp.be_apply_pocket_imports_v1(uuid)',
 'erp.bb_check_rework_import_row_v1(uuid,uuid)']

def changed(BB,BD,BE):
    sales=last_definition(BB,'bb_check_sales_import_row_v1')
    start=sales.index('  if not exists(select 1 from erp.products p where lower(btrim(p.sku))')
    end=sales.index('  -- One draft:',start)
    sales=sales[:start]+"  perform erp.bf_resolve_import_product_v1(p_batch,j,true);\n"+sales[end:]
    sales_apply=substitute(last_definition(BB,'bb_apply_sales_imports_v1'),[
      ("select id into strict v_product from erp.products where lower(btrim(sku))=lower(btrim(j->>'product_sku'));", "v_product:=erp.bf_resolve_import_product_v1(p_batch,j,false);")],'BF imported sales physical product')
    custody=substitute(last_definition(BD,'bc_check_import_row_v1'),[
      ("  return jsonb_build_object('kind',v_kind,'qty',(j->>'qty')::numeric,'source',v_source);", "  if v_kind='CUSTOMER_GARMENT' then perform erp.bf_resolve_import_product_v1(p_batch,j,true,true);end if;\n  return jsonb_build_object('kind',v_kind,'qty',(j->>'qty')::numeric,'source',v_source);")],'BF custody validation')
    custody_apply=substitute(last_definition(BD,'bc_apply_imports_v1'),[
      ("(select id from erp.products where lower(btrim(sku))=lower(btrim(nullif(j->>'product_sku',''))))", "erp.bf_resolve_import_product_v1(p_batch,j,false,true)")],'BF custody physical product')
    pocket=last_definition(BE,'be_check_pocket_import_v1')
    start=pocket.index("   if not exists(select 1 from erp.products where sku=j->>'product_sku')")
    end=pocket.index('\n  else',start)
    pocket=pocket[:start]+"   perform erp.bf_resolve_import_product_v1(p_batch,j,true);"+pocket[end:]
    pocket_apply=substitute(last_definition(BE,'be_apply_pocket_imports_v1'),[
      ("(select id from erp.products where sku=j->>'product_sku')", "case when upper(j->>'target_kind')='COGS' then erp.bf_resolve_import_product_v1(p_batch,j,false) end")],'BF pocket COGS physical product')
    rework=last_definition(BB,'bb_check_rework_import_row_v1')
    start=rework.index('  select p.id,p.identity_root_id,p.model_id into v_product,v_root,v_model')
    end=rework.index('  if v_product is null',start)
    rework=rework[:start]+"""  v_product:=erp.bf_resolve_import_product_v1(p_batch,b,false);
  select p.identity_root_id,p.model_id into v_root,v_model from erp.products p where p.id=v_product;
"""+rework[end:]
    router=last_definition(BE,'save_initial_import_action_v1')
    old=re.search(r"v_catalog constant jsonb:=('.*?')::jsonb;",router,re.S);assert old
    catalog=json.loads(old.group(1)[1:-1].replace("''","'"))
    extensions=json.loads((Path(__file__).resolve().parents[1]/'src/initialImportCatalogBF.json').read_text())
    for entity,more in extensions.items():
      assert not set(more['fields'])&set(catalog[entity]['fields'])
      catalog[entity]['fields'].update(more['fields'])
    router=router.replace(old.group(0),"v_catalog constant jsonb:='"+json.dumps(catalog,ensure_ascii=False).replace("'","''")+"'::jsonb;")
    return [sales,sales_apply,custody,custody_apply,pocket,pocket_apply,rework,router]
