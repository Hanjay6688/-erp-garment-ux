"""AS: recognition dates follow committed journals; WIP uses exact identity.

Economic invoice dates and all existing posted facts remain unchanged.
The import production validator applies every supplied identity qualifier.
"""
import cp6_v2620ao_definitions as ao
import cp6_v2620ap_definitions as ap

MATERIAL = 'erp.sync_material_cost_revaluation(uuid)'
ADJUSTMENT = 'erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)'
HPP = 'erp.sync_po_hpp_to_gl(uuid,date)'
OUTPUT = 'erp.complete_initial_import_wip_v1(jsonb)'
VALIDATE = 'erp.validate_initial_import_production_v1(uuid)'


def canonical(identity, arguments, result, settings=''):
    definition = ap.FUNCTIONS[identity]
    return ('CREATE OR REPLACE FUNCTION ' + identity.split('(')[0] + '(' + arguments + ')\n'
            ' RETURNS ' + result + '\n LANGUAGE plpgsql\n SECURITY DEFINER\n SET search_path TO \'\'\n'
            + settings + 'AS $function$' + definition.split('$function$', 1)[1]).rstrip(';\n') + '\n'


OLD = {key:ao.FUNCTIONS[key] for key in (MATERIAL, ADJUSTMENT, HPP)}
OLD[OUTPUT] = canonical(OUTPUT, 'p_payload jsonb', 'jsonb', ' SET "DateStyle" TO \'ISO, YMD\'\n')
OLD[VALIDATE] = canonical(VALIDATE, 'p_batch uuid', 'void')
FUNCTIONS = dict(OLD)


def replace(identity, old, new):
    assert FUNCTIONS[identity].count(old) == 1, (identity, old)
    FUNCTIONS[identity] = FUNCTIONS[identity].replace(old, new)


# post_journal owns the accounting-period row lock and resolves recognition.
# Copy the date from that exact journal, never re-resolve an unlocked period.
# Only the event created in this call is updated, before this transaction commits.
for identity, table in ((MATERIAL, 'material_cost_revaluation_events'), (HPP, 'po_hpp_gl_events')):
    replace(identity,
            f'update erp.{table} set journal_entry_id=v_journal where id=v_event;',
            f'update erp.{table} set journal_entry_id=v_journal,\n'
            '      effective_date=(select transaction_date from erp.journal_entries where id=v_journal) where id=v_event;')
replace(ADJUSTMENT,
        " ) values(v_event,p_adjustment,p_material,v_date,s->'book',s->'target',v_delta,v_journal);",
        " ) values(v_event,p_adjustment,p_material,(select transaction_date from erp.journal_entries where id=v_journal),s->'book',s->'target',v_delta,v_journal);")

replace(OUTPUT, ' v_batch uuid;v_product uuid;', ' v_product_count integer;v_batch uuid;v_product uuid;')
replace(OUTPUT,
        "  select p.id into v_product from erp.products p join erp.production_orders po on po.id=s.po_id\n"
        "    where p.sku=p_payload->>'product_sku' and p.is_active and p.model_id=po.model_id and p.size_id=s.size_id;\n"
        "  if v_product is null then raise exception 'product_sku: pilih produk aktif dengan model PO dan ukuran saldo yang sama';end if;",
        """  select count(*),(array_agg(x.id order by x.id))[1] into v_product_count,v_product
  from (
    select p.id from erp.products p join erp.production_orders po on po.id=s.po_id
    join erp.brands b on b.id=p.brand_id
    where lower(btrim(p.sku))=lower(btrim(p_payload->>'product_sku'))
      and p.is_active and p.model_id=po.model_id and p.size_id=s.size_id
      and p.effective_from<(v_date+1)::timestamp at time zone 'Asia/Jakarta'
      and (nullif(btrim(p_payload->>'brand_code'),'') is null
        or lower(btrim(b.brand_code))=lower(btrim(p_payload->>'brand_code')))
      and (nullif(p_payload->>'product_id','') is null or p.id=(p_payload->>'product_id')::uuid)
    order by p.id for share of p
  ) x;
  if v_product_count=0 then raise exception 'product_sku: pilih produk aktif dengan merek, model PO, ukuran saldo, dan tanggal hasil yang sesuai';end if;
  if v_product_count<>1 then raise exception 'AS_WIP_PRODUCT_AMBIGUOUS: SKU ada pada beberapa identitas produk; pilih merek atau identitas produk yang tepat';end if;""")

replace(VALIDATE, 'v_po jsonb;v_model text;v_size text;', 'v_po jsonb;v_model text;v_size text;v_product_count integer;v_cutover timestamptz;')
start = FUNCTIONS[VALIDATE].index('   select m.model_code into v_model from erp.products')
end = FUNCTIONS[VALIDATE].index("   if exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='OPENING_BALANCE_ITEM'", start)
FUNCTIONS[VALIDATE] = FUNCTIONS[VALIDATE][:start] + """   if nullif(btrim(j->>'product_sku'),'') is not null then
    select cutover_at into strict v_cutover from erp.migration_batches where id=p_batch;
    select count(*),min(m.model_code),min(z.size_code) into v_product_count,v_model,v_size
    from erp.products p join erp.product_models m on m.id=p.model_id
    join erp.sizes z on z.id=p.size_id join erp.brands b on b.id=p.brand_id
    where lower(btrim(p.sku))=lower(btrim(j->>'product_sku')) and p.effective_from<=v_cutover
      and (nullif(btrim(j->>'brand_code'),'') is null or lower(btrim(b.brand_code))=lower(btrim(j->>'brand_code')))
      and (nullif(btrim(j->>'model_code'),'') is null or lower(btrim(m.model_code))=lower(btrim(j->>'model_code')))
      and (nullif(btrim(j->>'size_code'),'') is null or lower(btrim(z.size_code))=lower(btrim(j->>'size_code')))
      and (nullif(btrim(j->>'color_name'),'') is null or lower(btrim(p.color_name))=lower(btrim(j->>'color_name')));
    if v_product_count=0 then
     select count(*),min(x.normalized_payload->>'model_code'),min(x.normalized_payload->>'size_code')
     into v_product_count,v_model,v_size from erp.migration_staging_rows x
     where x.batch_id=p_batch and x.entity_type='PRODUCT' and x.validation_status='VALID'
       and lower(btrim(x.normalized_payload->>'sku'))=lower(btrim(j->>'product_sku'))
       and (nullif(btrim(j->>'brand_code'),'') is null or lower(btrim(x.normalized_payload->>'brand_code'))=lower(btrim(j->>'brand_code')))
       and (nullif(btrim(j->>'model_code'),'') is null or lower(btrim(x.normalized_payload->>'model_code'))=lower(btrim(j->>'model_code')))
       and (nullif(btrim(j->>'size_code'),'') is null or lower(btrim(x.normalized_payload->>'size_code'))=lower(btrim(j->>'size_code')))
       and (nullif(btrim(j->>'color_name'),'') is null or lower(btrim(x.normalized_payload->>'color_name'))=lower(btrim(j->>'color_name')));
    end if;
    if v_product_count<>1 then raise exception 'product_sku: identitas produk harus tepat satu; periksa merek, model, warna, dan ukuran';end if;
    if v_model<>v_po->>'model_code' then raise exception 'product_sku: produk berbeda model dengan PO';end if;
    if v_size<>j->>'size_code' then raise exception 'size_code: ukuran fisik berbeda dengan produk';end if;
   end if;
""" + FUNCTIONS[VALIDATE][end:]
