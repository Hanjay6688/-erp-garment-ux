-- MODEL ONLY. This is not the Native PO sync and is never installed as product.
-- It independently values the fresh fixture's unsold physical PO pieces.
-- The exact prepared economic targets are checked against this physical book
-- by the unmodified Native PO target/book assertion afterwards.
alter table erp.po_hpp_gl_state add primary key(po_id);
alter table erp.be_rework_targets_v1 add primary key(rework_id);
create table public.model_auto_pending(po_id uuid primary key,pending integer not null,laundry_unknown boolean not null);
create or replace function erp.get_hpp_completeness(uuid)returns table(pending_reason_count integer)
language sql stable as $$select coalesce((select pending from public.model_auto_pending where po_id=$1),0)$$;
create or replace function erp.bd_lot_laundry_unknown_v1(uuid)returns boolean
language sql stable as $$select coalesce((select p.laundry_unknown from public.model_auto_pending p
 join erp.fg_lots l on l.po_id=p.po_id where l.id=$1),false)$$;
create function erp.account_id(text)returns uuid language sql stable as $$
 select account_id from erp.accounting_account_mappings where mapping_key=$1
$$;
create function erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)returns numeric
language plpgsql stable as $$begin raise exception 'MODEL_AUTOMATIC_UNTAGGED_SALE_OUT_OF_SCOPE';end$$;
create function erp.sync_po_hpp_to_gl(p_po uuid,p_date date)returns void
language plpgsql as $$
declare physical_value numeric;book_value numeric;qty numeric;delta numeric;
begin
 if exists(select 1 from erp.sales_items i join erp.sales_headers s on s.id=i.sale_id
  join erp.sale_stock_allocations a on a.sale_item_id=i.id join erp.fg_lots l on l.id=a.lot_id
  where l.po_id=p_po and s.status in('POSTED','PARTIAL_PAID','PAID'))then
  raise exception 'MODEL_AUTOMATIC_PHYSICAL_GL_PROVIDER_HAS_NO_SALE_ORACLE';end if;
 if exists(select 1 from erp.fg_lots l left join erp.hpp_versions h on h.lot_id=l.id and h.is_current
  where l.po_id=p_po and l.lot_origin in('PRODUCTION','CONVERSION')
   and(h.id is null or h.hpp_per_pcs is null or h.hpp_per_pcs::text in('NaN','Infinity','-Infinity')))then
  raise exception 'MODEL_AUTOMATIC_PHYSICAL_GL_REQUIRES_PRESENT_NUMERIC_HPP';end if;
 with lots as(
  select l.id,h.hpp_per_pcs,coalesce(sum(m.qty_signed),0)qty
  from erp.fg_lots l join erp.hpp_versions h on h.lot_id=l.id and h.is_current
  left join erp.fg_stock_movements m on m.lot_id=l.id
  where l.po_id=p_po and l.lot_origin in('PRODUCTION','CONVERSION')group by l.id,h.hpp_per_pcs
 )select round(sum(lots.qty*lots.hpp_per_pcs),2),sum(lots.qty)into physical_value,qty from lots;
 if qty is null or qty<0 then raise exception 'MODEL_AUTOMATIC_PHYSICAL_PO_VALUE_REQUIRED';end if;
 select fg_value into book_value from erp.compute_po_hpp_gl_book_v2620e(p_po);
 delta:=physical_value-book_value;
 if delta<>0 then perform erp.post_journal('MODEL_PHYSICAL_PO_SYNC',p_po,p_date,
  'Explicit independent physical-only unsold PO model',jsonb_build_array(
   jsonb_build_object('mapping_key','FG_INVENTORY','po_id',p_po,'debit',greatest(delta,0),'credit',greatest(-delta,0)),
   jsonb_build_object('mapping_key','WIP','po_id',p_po,'debit',greatest(-delta,0),'credit',greatest(delta,0))));end if;
 perform erp.refresh_po_hpp_gl_baseline(p_po);
 perform erp.assert_po_hpp_target_book_v2620e(p_po);
end $$;
