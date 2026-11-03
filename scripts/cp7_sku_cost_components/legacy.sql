-- New one-child Native conversions retain their original selected physical lot,
-- origin, preview and owning Native request. No historical rows are backfilled.
create table cp7_sku_conversion.legacy_groups_v4(
 group_id uuid primary key references cp7_sku_conversion.valuation_quotes_v2(group_id),
 source_lot_id uuid not null references erp.fg_lots(id),
 origin_kind text not null check(origin_kind in('FG','REWORK','REDYE')),
 rework_id uuid references erp.rework_orders(id),
 original_preview jsonb not null check(jsonb_typeof(original_preview)='object'),
 native_request_id uuid not null,
 admission_backend_pid integer not null,
 admission_transaction_id bigint not null,
 recorded_at timestamptz not null default statement_timestamp(),
 check((origin_kind='FG')=(rework_id is null))
);
create trigger legacy_groups_immutable_v4 before update or delete on cp7_sku_conversion.legacy_groups_v4
 for each row execute function cp7_sku_conversion.immutable_v1();
alter table cp7_sku_conversion.legacy_groups_v4 enable row level security;
revoke all on cp7_sku_conversion.legacy_groups_v4 from public,anon,authenticated,service_role;

create function cp7_sku_conversion.legacy_source_revision_v4(p_lot uuid,p_location uuid,p_native text)
returns text language plpgsql stable security definer set search_path=''as $$
declare v_product uuid;v_pool jsonb;v_error text;
begin
 -- Only the private admitted child translates its already checked combined
 -- revision back to the original Native physical revision.
 if exists(select 1 from cp7_sku_conversion.execution_v1 e
  join cp7_sku_conversion.valuation_quotes_v2 q on q.group_id=e.group_id
  join erp.fg_lots l on l.id=e.source_lot_id and l.product_id=q.source_product_id
  where e.backend_pid=pg_backend_pid()and e.transaction_id=txid_current()and e.mode='POST'
   and e.source_lot_id=p_lot and e.location_id=p_location and q.location_id=e.location_id
   and q.target_product_id=e.target_id)then return p_native;end if;
 select product_id into v_product from erp.fg_lots where id=p_lot;
 if v_product is null then return p_native;end if;
 begin
  v_pool:=cp7_sku_conversion.pool_quote_v2(v_product,p_location,'GRADE_A');
 exception when raise_exception then
  get stacked diagnostics v_error=MESSAGE_TEXT;
  if v_error not like 'CP7_SKU_POOL_HPP_UNKNOWN:%'then raise;end if;
  -- A read of an unknown lot remains possible. Posting still executes the
  -- exact pool quote and refuses unknown value; no unknown price is invented.
  v_pool:=jsonb_build_object('revision','UNKNOWN');
 end;
 if v_pool->>'revision'<>'UNKNOWN'then
  -- A known preview must also admit the existing raw custody, before a new
  -- opaque revision can be handed to a client. Non-unknown failures propagate.
  perform cp7_sku_conversion.base_scope_correction_v4(v_product);
 end if;
 return md5(jsonb_build_object('native',p_native,'source_value',v_pool->>'revision')::text);
end $$;
revoke all on function cp7_sku_conversion.legacy_source_revision_v4(uuid,uuid,text)from public,anon,authenticated,service_role;
