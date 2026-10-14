-- bootstrap lines 12995-13078
CREATE OR REPLACE FUNCTION erp.post_fg_movement(p_product_id uuid, p_lot_id uuid, p_location_id uuid, p_quality_grade text, p_movement_type text, p_qty_signed integer, p_unit_hpp numeric, p_customer_id uuid, p_source_type text, p_source_id uuid, p_physical_at timestamp with time zone, p_note text DEFAULT NULL::text, p_allow_negative boolean DEFAULT false)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_id uuid;
  v_balance integer;
  v_lot_qty integer;
  v_lot_product uuid;
  v_lot_produced_at timestamptz;
begin
  perform erp.require_internal();
  if p_qty_signed=0 then raise exception 'FG movement qty cannot be zero'; end if;
  if p_physical_at is null then raise exception 'Finished-goods movement physical date/time is required'; end if;
  if p_location_id is null or not exists (
    select 1 from erp.locations l
    where l.id=p_location_id and l.is_active=true and l.location_type='FG_WAREHOUSE'
  ) then
    raise exception 'Finished-goods movement location must be an active FG warehouse';
  end if;

  insert into erp.fg_inventory_balances(product_id,location_id,quality_grade,cached_qty_pcs)
  values (p_product_id,p_location_id,coalesce(p_quality_grade,'GRADE_A'),0)
  on conflict (product_id,location_id,quality_grade) do nothing;

  select cached_qty_pcs into v_balance
  from erp.fg_inventory_balances
  where product_id=p_product_id
    and location_id=p_location_id
    and quality_grade=coalesce(p_quality_grade,'GRADE_A')
  for update;

  if not p_allow_negative and v_balance+p_qty_signed<0 then
    raise exception 'Finished goods stock cannot become negative';
  end if;

  if p_lot_id is not null then
    select cached_qty_pcs,product_id,produced_at
      into v_lot_qty,v_lot_product,v_lot_produced_at
    from erp.fg_lots where id=p_lot_id for update;
    if v_lot_qty is null then raise exception 'FG lot not found'; end if;
    if v_lot_product is distinct from p_product_id then
      raise exception 'FG lot product does not match movement product';
    end if;
    if p_physical_at<v_lot_produced_at then
      raise exception 'Tanggal mutasi FG % lebih awal dari tanggal barang/lot tersedia %. Koreksi tanggal transaksi atau sumber barang terlebih dahulu.',p_physical_at,v_lot_produced_at;
    end if;
    if not p_allow_negative and v_lot_qty+p_qty_signed<0 then
      raise exception 'FG lot stock cannot become negative';
    end if;
  end if;

  insert into erp.fg_stock_movements(
    product_id,lot_id,location_id,quality_grade,movement_type,qty_signed,
    unit_hpp_snapshot,customer_id,source_type,source_id,physical_at,created_by,notes
  ) values (
    p_product_id,p_lot_id,p_location_id,coalesce(p_quality_grade,'GRADE_A'),p_movement_type,p_qty_signed,
    coalesce(p_unit_hpp,0),p_customer_id,p_source_type,p_source_id,p_physical_at,erp.current_app_user_id(),p_note
  ) returning id into v_id;

  if not p_allow_negative then
    perform erp.assert_fg_chronological_nonnegative(p_product_id,p_lot_id,p_location_id,coalesce(p_quality_grade,'GRADE_A'));
  end if;

  update erp.fg_inventory_balances
  set cached_qty_pcs=cached_qty_pcs+p_qty_signed,updated_at=now()
  where product_id=p_product_id
    and location_id=p_location_id
    and quality_grade=coalesce(p_quality_grade,'GRADE_A');

  if p_lot_id is not null then
    update erp.fg_lots
    set cached_qty_pcs=cached_qty_pcs+p_qty_signed,
        is_open=(cached_qty_pcs+p_qty_signed)>0
    where id=p_lot_id;
  end if;
  return v_id;
end;
$function$;

alter function "erp"."post_fg_movement"(p_product_id uuid, p_lot_id uuid, p_location_id uuid, p_quality_grade text, p_movement_type text, p_qty_signed integer, p_unit_hpp numeric, p_customer_id uuid, p_source_type text, p_source_id uuid, p_physical_at timestamp with time zone, p_note text, p_allow_negative boolean) owner to "postgres";
