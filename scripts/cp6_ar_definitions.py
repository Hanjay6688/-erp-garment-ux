"""AR closes legacy/import overlap at the shared posting boundary.

The inherited import registries still distinguish separate source documents and
stock lots. This successor prevents mixing a legacy opening with an overlapping
import opening, in either order. Values/dates are not identity or dedupe keys.
"""
import cp6_v2620ap_definitions as ap

POST='erp.post_opening_balance(uuid)'
PREPARE='erp.prepare_migration_opening_balance(uuid,text)'
ACTION='erp.save_initial_import_action_v1(text,jsonb,uuid)'
OLD={key:ap.FUNCTIONS[key] for key in (POST,PREPARE,ACTION)}
# Canonical pg_get_functiondef spelling; the builder checks its SHA against the
# independently captured AP catalog before trusting either predecessor or delta.
OLD[ACTION]="CREATE OR REPLACE FUNCTION erp.save_initial_import_action_v1(p_action text, p_payload jsonb, p_client_request_id uuid)\n RETURNS jsonb\n LANGUAGE plpgsql\n SECURITY DEFINER\n SET search_path TO ''\nAS $function$"+OLD[ACTION].split('$function$',1)[1]
OLD[ACTION]=OLD[ACTION].removesuffix(';\n')+'\n'
FUNCTIONS=dict(OLD)

def replace(identity,needle,replacement):
    assert FUNCTIONS[identity].count(needle)==1,(identity,needle)
    FUNCTIONS[identity]=FUNCTIONS[identity].replace(needle,replacement)

replace(POST,'  perform erp.require_owner_admin();',
    "  perform erp.require_owner_admin();\n"
    "  if current_setting('transaction_isolation')<>'read committed' then\n"
    "    raise exception 'AR_OPENING_REQUIRES_READ_COMMITTED';\n"
    "  end if;")

# Canonical posting already takes this transaction lock. Acquire it before batch,
# source-party, header and idempotency locks in the two import entry points too.
replace(PREPARE,'  perform erp.require_owner_admin();select * into b',
    "  perform erp.require_owner_admin();\n"
    "  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));\n"
    '  select * into b')
replace(ACTION," v_cached:=erp._idempotency_begin('save_initial_import_action_v1',p_client_request_id,",
    " -- AR: same lock order as native prepare/post, before any batch lock.\n"
    " if v_action='FINALIZE' then\n"
    "   perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));\n"
    " end if;\n"
    " v_cached:=erp._idempotency_begin('save_initial_import_action_v1',p_client_request_id,")

NEEDLE="  select count(*),(array_agg(id order by id))[1] into v_fg_count,v_default_fg_location from erp.locations where location_type='FG_WAREHOUSE' and is_active=true;"
GUARD=r"""
  -- AR: all canonical posts share the lock acquired above. READ COMMITTED
  -- rechecks here after waiting, before creating any economic side effect.
  -- A legacy line has no imported source document/lot identity: an overlapping
  -- import cannot prove it represents additional opening rights or goods.
  -- Keep the inherited rules for separate imported documents/physical sources.
  if exists(
    select 1 from erp.opening_balance_items i
    join erp.opening_balance_items o on o.balance_type=i.balance_type
    join erp.opening_balance_headers oh on oh.id=o.opening_id
    left join erp.products ip on ip.id=i.product_id
    left join erp.products op on op.id=o.product_id
    where i.opening_id=h.id and oh.id<>h.id and oh.status='POSTED'
      and ((h.migration_batch_id is null)<>(oh.migration_batch_id is null))
      and case i.balance_type
        when 'CUSTOMER_RECEIVABLE' then i.customer_id=o.customer_id
        when 'SUPPLIER_PAYABLE' then i.supplier_id=o.supplier_id
        when 'VENDOR_PAYABLE' then i.vendor_id=o.vendor_id
        when 'CONTRACTOR_RECEIVABLE' then i.contractor_id=o.contractor_id
        when 'CONTRACTOR_PAYABLE' then i.contractor_id=o.contractor_id
        when 'CASH_BANK' then i.cash_account_id=o.cash_account_id
        when 'MATERIAL' then i.material_id=o.material_id
          and i.location_id=o.location_id
          and (i.roll_id is null or o.roll_id is null or i.roll_id=o.roll_id)
        when 'FINISHED_GOODS' then i.product_id=o.product_id and exists(
          select 1 from erp.fg_stock_movements fm
          where fm.source_type='OPENING_BALANCE_ITEM' and fm.source_id=o.id
            and fm.movement_type='OPENING'
            and fm.location_id=coalesce(i.location_id,v_default_fg_location)
            and fm.quality_grade=coalesce(i.quality_grade,'GRADE_A'))
        when 'WIP' then
          (coalesce(i.model_id,ip.model_id) is null or coalesce(o.model_id,op.model_id) is null
            or coalesce(i.model_id,ip.model_id)=coalesce(o.model_id,op.model_id))
          and (i.stage is null or o.stage is null or i.stage=o.stage)
          and (i.contractor_id is null or o.contractor_id is null or i.contractor_id=o.contractor_id)
        when 'BS' then
          (i.product_id is null or o.product_id is null or i.product_id=o.product_id)
          and (coalesce(i.model_id,ip.model_id) is null or coalesce(o.model_id,op.model_id) is null
            or coalesce(i.model_id,ip.model_id)=coalesce(o.model_id,op.model_id))
          and (i.contractor_id is null or o.contractor_id is null or i.contractor_id=o.contractor_id)
          and (i.vendor_id is null or o.vendor_id is null or i.vendor_id=o.vendor_id)
        else false end
  ) then
    raise exception 'AR_OPENING_ROUTE_OVERLAP: saldo/stok awal sudah disahkan melalui jalur lain; rekonsiliasi sumber sebelum mengesahkan';
  end if;
"""
replace(POST,NEEDLE,NEEDLE+'\n'+GUARD)
