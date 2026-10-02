-- Preserve invoice-line identity even when one SKU occurs more than once.
-- No posted Native facts or financial helper definitions are edited here.
create table cp7_note.item_lineage(
 replacement_item_id uuid primary key references erp.sales_items(id),
 previous_item_id uuid references erp.sales_items(id),
 correction_id uuid not null references cp7_note.revisions(id)deferrable initially deferred,
 request_position integer not null check(request_position>0),
 unique(correction_id,request_position),unique(correction_id,previous_item_id)
);
alter table cp7_note.item_lineage owner to postgres;
alter table cp7_note.item_lineage enable row level security;
create policy note_item_lineage_private on cp7_note.item_lineage for all using(false)with check(false);
revoke all on cp7_note.item_lineage from public,anon,authenticated,service_role,cp7_capture,cp7_sales_write;
create trigger note_item_lineage_immutable before update or delete on cp7_note.item_lineage
 for each row execute function cp7_note.immutable_revision();

create function cp7_note.bind_items(previous_sale uuid,replacement_sale uuid,correction uuid,items jsonb,source_ids jsonb)returns void
language plpgsql volatile security definer set search_path=''as $$
declare row record;previous uuid;replacement uuid;occurrence integer;
begin
 if jsonb_typeof(items)is distinct from'array'or jsonb_array_length(items)not between 1 and 100
  or jsonb_array_length(items)<>(select count(*)from erp.sales_items where sale_id=replacement_sale)then raise exception 'CP7_NOTE_ITEM_LINEAGE_SCOPE';end if;
 if source_ids is not null then
  if jsonb_typeof(source_ids)is distinct from'array'or jsonb_array_length(source_ids)<>jsonb_array_length(items)
   or exists(select 1 from jsonb_array_elements(source_ids)x where jsonb_typeof(x)not in('string','null')
    or jsonb_typeof(x)='string'and(x#>>'{}')!~*'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$')then raise exception 'CP7_NOTE_ITEM_LINEAGE_FIELDS';end if;
  if exists(select 1 from jsonb_array_elements_text(source_ids)x where x is not null group by x having count(*)>1)
   or exists(select 1 from jsonb_array_elements_text(source_ids)x where x is not null and not exists(select 1 from erp.sales_items i where i.id=x::uuid and i.sale_id=previous_sale))then raise exception 'CP7_NOTE_ITEM_LINEAGE_SOURCE';end if;
 end if;
 for row in select value,ordinality::integer position from jsonb_array_elements(items)with ordinality loop
  if source_ids is not null then previous:=(source_ids->>(row.position-1))::uuid;
  else
   -- Compatibility for already-held v1 requests. The existing reader orders
   -- Native lines by id; match each submitted SKU occurrence once in that order.
   select count(*)::integer-1 into occurrence from jsonb_array_elements(items)with ordinality x
    where x.ordinality<=row.position and(x.value->>'product_id')::uuid=(row.value->>'product_id')::uuid;
   select id into previous from erp.sales_items where sale_id=previous_sale and product_id=(row.value->>'product_id')::uuid order by id offset occurrence limit 1;
  end if;
  -- Native generates new ids and may normalize decimal strings/blank notes.
  -- Match its complete line values, never just SKU or random replacement order.
  select i.id into replacement from erp.sales_items i where i.sale_id=replacement_sale
   and i.product_id=(row.value->>'product_id')::uuid and i.qty_pcs=(row.value->>'qty_pcs')::integer
   and i.unit_price_snapshot=(row.value->>'unit_price_snapshot')::numeric
   and i.discount_amount=(row.value->>'discount_amount')::numeric
   and nullif(btrim(i.notes),'')is not distinct from nullif(btrim(row.value->>'notes'),'')
   and not exists(select 1 from cp7_note.item_lineage l where l.replacement_item_id=i.id)order by i.id limit 1;
  if replacement is null then raise exception 'CP7_NOTE_ITEM_LINEAGE_NATIVE_MISMATCH';end if;
  insert into cp7_note.item_lineage values(replacement,previous,correction,row.position);
 end loop;
end $$;

create function cp7_note.line_origin(previous_sale uuid,replacement_item uuid,p_product uuid,p_lot uuid,p_location uuid,p_grade text)returns uuid
language sql stable security definer set search_path=''as $$
 select coalesce(l.origin_id,m.id)from cp7_note.item_lineage item
 join erp.sales_items i on i.id=item.previous_item_id and i.sale_id=previous_sale
 join erp.fg_stock_movements m on m.source_id=i.id and m.source_type='SALE_ITEM'and m.movement_type='SALE'
 left join cp7_fg.correction_movements l on l.member_id=m.id
 where item.replacement_item_id=replacement_item and m.product_id=p_product
  and m.location_id=p_location and m.quality_grade=p_grade
 order by(m.lot_id is not distinct from p_lot)desc,m.book_order,m.id limit 1
$$;
alter function cp7_note.bind_items(uuid,uuid,uuid,jsonb,jsonb)owner to postgres;
alter function cp7_note.line_origin(uuid,uuid,uuid,uuid,uuid,text)owner to postgres;
revoke all on function cp7_note.bind_items(uuid,uuid,uuid,jsonb,jsonb),cp7_note.line_origin(uuid,uuid,uuid,uuid,uuid,text)
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_write;
