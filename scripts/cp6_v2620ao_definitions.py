"""Proposed invoice economic date and exact manually-priced retail PCS family."""
from pathlib import Path
import json
PREDECESSOR=json.loads(Path('docs/evidence/cp6-ao-predecessor-input.json').read_text())['functions']
FUNCTIONS={r[0]:r[1] for r in PREDECESSOR}
SCHEMA="""
create table erp.invoice_recost_execution_context(
 transaction_id bigint primary key,invoice_date date not null,source_id uuid not null
);
alter table erp.invoice_recost_execution_context enable row level security;
revoke all on erp.invoice_recost_execution_context from public,anon,authenticated,service_role;
alter table erp.contractor_material_issue_items add column manual_retail_unit_price numeric;
"""
DATE_ID='erp.invoice_recost_economic_date_v1()'
DATE="""CREATE OR REPLACE FUNCTION erp.invoice_recost_economic_date_v1()
RETURNS date LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO '' AS $function$
 select invoice_date from erp.invoice_recost_execution_context where transaction_id=txid_current();
$function$;
"""
def change(identity,old,new,count=1):
 assert FUNCTIONS[identity].count(old)==count,(identity,old)
 FUNCTIONS[identity]=FUNCTIONS[identity].replace(old,new)

# Context is private transactional data set exclusively by these admitted
# document writers, never a caller-controlled GUC or a new date argument.
for identity in list(FUNCTIONS):
 name=identity.split('(')[0]
 if name in {'erp.post_material_supplier_invoice','erp.reverse_material_supplier_invoice','erp.post_material_purchase_cost_correction','erp.reverse_material_purchase_cost_correction'}:
  s=FUNCTIONS[identity]
  # Do not affect idempotent already-reversed early returns.
  marker=next(line for line in s.splitlines() if "h.status<>" in line and 'raise exception' in line)
  # Posting corrects the receipt at invoice economic date. Cancellation uses
  # the existing reversal business-day contract for every valuation leg too.
  reversing=name.startswith('erp.reverse_')
  date_expression='erp._cp3_business_date(statement_timestamp())' if reversing else 'h.invoice_date'
  change(identity,marker,marker+"\n  insert into erp.invoice_recost_execution_context(transaction_id,invoice_date,source_id) values(txid_current(),"+date_expression+",h.id);")
  if reversing:
   change(identity,',h.id,h.invoice_date,p_reason,v_n_before,true);',',h.id,erp._cp3_business_date(statement_timestamp()),p_reason,v_n_before,true);')
  tail='end;\n$function$'
  change(identity,tail,'  delete from erp.invoice_recost_execution_context where transaction_id=txid_current();\n'+tail)

for identity in ['erp.sync_material_cost_revaluation(uuid)','erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)']:
 old='erp._cp3_business_date(statement_timestamp())'
 count=FUNCTIONS[identity].count(old);assert count>0
 change(identity,old,'coalesce(erp.invoice_recost_economic_date_v1(),erp._cp3_business_date(statement_timestamp()))',count)
change('erp.sync_po_hpp_to_gl(uuid,date)','  perform erp.require_internal();',"  perform erp.require_internal();\n  p_effective_date:=coalesce(erp.invoice_recost_economic_date_v1(),p_effective_date);")

# Invoice posting must complete downstream valuation before releasing context.
# Other ordinary material operations keep their admitted asynchronous behavior.
identity='erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)'
change(identity,'  v_location_minimum numeric;','  v_location_minimum numeric;\n  v_invoice_date date;\n  v_queue record;')
needle="  if not v_use_checkpoint and v_closed is not null then"
change(identity,needle,"""  v_invoice_date:=erp.invoice_recost_economic_date_v1();
  if v_invoice_date is not null then
    for v_queue in
      select q.* from erp.cost_recalc_queue q where q.entity_type='PO'
        and q.status in('PENDING','FAILED')
        and q.entity_id in(
          select cg.po_id from erp.cutting_groups cg join erp.material_stock_movements m
            on m.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN') and m.source_id=cg.id where m.material_id=p_material_id
          union select i.po_id from erp.contractor_material_issues i join erp.contractor_material_issue_items l on l.issue_id=i.id
            where l.material_id=p_material_id and i.po_id is not null
        ) order by q.entity_id,q.queued_at,q.id for update
    loop
      perform erp.rebuild_po_hpp(v_queue.entity_id,v_queue.reason);
      perform erp.propagate_conversion_hpp_for_po(v_queue.entity_id);
      perform erp.sync_po_hpp_to_gl(v_queue.entity_id,v_invoice_date);
      if exists(select 1 from erp.production_orders where id=v_queue.entity_id and status='FINISHED') then
        perform erp.sync_finished_po_wip_residual(v_queue.entity_id,v_invoice_date,'Invoice-date material correction');
      end if;
      update erp.cost_recalc_queue set status='DONE',started_at=statement_timestamp(),completed_at=statement_timestamp(),
        last_attempt_at=statement_timestamp(),attempt_count=attempt_count+1,error_message=null,next_attempt_at=null where id=v_queue.id;
    end loop;
  end if;

"""+needle)

identity='erp.normalize_contractor_issue_item_uom_price()'
needle="    perform pg_advisory_xact_lock(hashtextextended('CAPRICE:'"
i=FUNCTIONS[identity].index(needle)
FUNCTIONS[identity]=FUNCTIONS[identity][:i]+"""    if new.manual_retail_unit_price is not null then
      if new.manual_retail_unit_price::text in('NaN','Infinity','-Infinity')
        or new.manual_retail_unit_price<0 or new.manual_retail_unit_price<>round(new.manual_retail_unit_price,2) then
        raise exception 'Harga eceran wajib nominal valid dengan paling banyak dua angka desimal'; end if;
      select u.dimension into v_dimension from erp.uom_definitions u where u.unit_code=v_base_uom;
      if v_dimension is distinct from 'COUNT' or new.qty is null or new.qty<=0
        or new.qty::text in('NaN','Infinity','-Infinity') or new.qty<>trunc(new.qty) then
        raise exception 'Eceran memerlukan jumlah fisik utuh dalam satuan dasar hitung'; end if;
      if new.transaction_qty is not null and new.transaction_qty<>new.qty then
        raise exception 'Jumlah eceran harus sama dengan jumlah fisik'; end if;
      new.transaction_qty:=new.qty;new.transaction_uom_code:=v_base_uom;new.base_qty_per_transaction_uom:=1;
      new.unit_sale_price_snapshot:=new.manual_retail_unit_price;
      new.accessory_price_version_id:=null;new.material_price_version_id:=null;
      return new;
    end if;

"""+FUNCTIONS[identity][i:]
# Do not silently round an impossible dozen/gross fraction into a physical count.
change(identity,'      new.transaction_qty:=new.qty/v_factor;',"""      if (new.qty/v_factor)::numeric(18,6)*v_factor<>new.qty then
        raise exception 'Jumlah PCS ini memerlukan harga eceran manual; pecahan lusin/gross tidak dibulatkan'; end if;
      new.transaction_qty:=new.qty/v_factor;""")
change(identity,"  else\n    if new.qty", "  else\n    if new.manual_retail_unit_price is not null then raise exception 'Harga eceran manual hanya untuk aksesori hitung'; end if;\n    if new.qty")
identity='erp.save_contractor_material_issue_draft_v2(jsonb,uuid,bigint)'
change(identity,'notes,transaction_qty\n','notes,transaction_qty,manual_retail_unit_price\n')
change(identity,"nullif(btrim(v_line->>'notes'),''),nullif(v_line->>'transaction_qty','')::numeric", "nullif(btrim(v_line->>'notes'),''),nullif(v_line->>'transaction_qty','')::numeric,nullif(v_line->>'manual_retail_unit_price','')::numeric")
change(identity,'    -- The normalizer overwrites selling price/version and reconciles transaction\n    -- UOM to base quantity. Client-supplied price fields are never accepted.', '    -- Explicit manual retail price is a separate base-PCS price. Configured\n    -- dozen/gross prices remain versioned and are never overwritten.')
# Reader must exist before the proposed consumers are compiled.
FUNCTIONS={DATE_ID:DATE,**FUNCTIONS}
identity='erp.save_contractor_material_issue_draft_v2(jsonb,uuid,bigint)'
needle="    v_qty:=coalesce(nullif(v_line->>'qty','')::numeric,nullif(v_line->>'transaction_qty','')::numeric);"
change(identity,needle,needle+"""
    if nullif(v_line->>'manual_retail_unit_price','') is not null then
      if v_qty is null or v_qty::text in('NaN','Infinity','-Infinity') or v_qty<=0 or v_qty<>trunc(v_qty)
        or (nullif(v_line->>'transaction_qty','') is not null and (v_line->>'transaction_qty')::numeric<>v_qty) then
        raise exception 'Jumlah eceran harus PCS utuh dan konsisten sebelum penyimpanan'; end if;
    end if;""")
