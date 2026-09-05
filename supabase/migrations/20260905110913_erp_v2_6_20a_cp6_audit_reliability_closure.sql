-- ERP Garment v2.6.20a / CP6 independent-audit reliability closure.
--
-- VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
-- Reliable data adalah dewa. Keuangan termasuk laporan, stok, dan HPP adalah raja.
-- This forward-only patch never edits the recorded v2.6.20 migration and never
-- deletes or rewrites posted business history.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

lock table erp.schema_migrations,
  supabase_migrations.schema_migrations,
  erp.vendor_invoices,
  erp.vendor_invoice_items,
  erp.laundry_deliveries,
  erp.laundry_delivery_lines,
  erp.laundry_receipts,
  erp.laundry_receipt_lines
in share row exclusive mode;

do $guard$
declare
  v_actual text;
  v_platform_match_count integer;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20') then
    raise exception 'ERP v2.6.20a requires the immutable v2.6.20 migration first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20a') then
    raise exception 'ERP v2.6.20a is already recorded; never replay or edit a recorded migration';
  end if;
  if to_regclass('erp.cp6_v2620a_rollback_capsule') is not null
     or to_regclass('erp.idx_laundry_failed_wash_attempts_delivery_v2620a') is not null then
    raise exception 'ERP v2.6.20a target guard: prior reliability-patch residue exists';
  end if;

  select count(*) into v_platform_match_count
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20_cp6_laundry_qc_fg_authoritative'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      'e5fcf69ddec8e2bebdc3c511b57af886666aadded62801ff34905df7bfc95485',
      '52e51f56f4b8b08b7797b1a92ca9b9e26cbe611e81615c3379c728b95877ada1'
    );
  if v_platform_match_count<>1 then
    raise exception 'ERP v2.6.20a requires one exact v2.6.20 platform-ledger row; found %',
      v_platform_match_count;
  end if;

  select md5(pg_get_functiondef('erp.post_vendor_invoice(uuid)'::regprocedure)) into v_actual;
  if v_actual is distinct from 'b2e8ffa3e9caf72aaa101a34bded5001' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: vendor invoice posting changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.reverse_vendor_invoice(uuid,text)'::regprocedure)) into v_actual;
  if v_actual is distinct from '43cec1668118c4a9c30939be72cc45b5' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: vendor invoice reversal changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef(
    'erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'::regprocedure
  )) into v_actual;
  if v_actual is distinct from 'c03b264c3e180c5d272f310e9374021a' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: CP6 Laundry/QC writer changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef(
    'erp.get_laundry_qc_workspace_v1(text,text)'::regprocedure
  )) into v_actual;
  if v_actual is distinct from '25ac6c923bc0c2ff213a09b541a26b12' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: CP6 Laundry/QC workspace changed (%)',v_actual;
  end if;
end
$guard$;

-- Preserve exact predecessor bytes, owner, and ACL.  Rollback can restore only
-- these authenticated objects; it never guesses an earlier definition.
create table erp.cp6_v2620a_rollback_capsule(
  object_identity text primary key,
  object_regidentity text not null unique,
  object_definition text not null,
  definition_sha256 text not null,
  installed_definition_sha256 text,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp()
);
alter table erp.cp6_v2620a_rollback_capsule enable row level security;
revoke all on table erp.cp6_v2620a_rollback_capsule
  from public,anon,authenticated,service_role;

insert into erp.cp6_v2620a_rollback_capsule(
  object_identity,object_regidentity,object_definition,definition_sha256,
  acl_snapshot,owner_snapshot
)
select
  format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,
  pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(
    select a::text from unnest(p.proacl) a order by a::text
  ) end,
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in(
  'erp.post_vendor_invoice(uuid)'::regprocedure,
  'erp.reverse_vendor_invoice(uuid,text)'::regprocedure,
  'erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'::regprocedure,
  'erp.get_laundry_qc_workspace_v1(text,text)'::regprocedure
);

do $capsule_guard$
begin
  if (select count(*) from erp.cp6_v2620a_rollback_capsule)<>4
     or exists(
       select 1 from erp.cp6_v2620a_rollback_capsule c
       where c.definition_sha256 is distinct from encode(extensions.digest(
         convert_to(c.object_definition,'UTF8'),'sha256'
       ),'hex')
     ) then
    raise exception 'ERP v2.6.20a exact rollback capsule is incomplete or corrupt';
  end if;
end
$capsule_guard$;

-- F01: every invoice lifecycle takes the same canonical CP6 order before it
-- reads a prior receipt cost: Potongan advisory fence, receipt headers, then
-- receipt lines.  A waiter therefore refreshes its cursor after the winning
-- transaction commits and cannot resurrect a stale FINAL amount later.
do $patch_invoice_lifecycle$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef('erp.post_vendor_invoice(uuid)'::regprocedure)
    into v_definition;
  v_anchor:=$anchor$  v_po uuid;
  v_lines jsonb:='[]'::jsonb;$anchor$;
  v_replacement:=$replacement$  v_po uuid;
  v_group_id uuid;
  v_lines jsonb:='[]'::jsonb;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: post_vendor_invoice declaration anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  if not exists (select 1 from erp.vendor_invoice_items where invoice_id=h.id) then raise exception 'Vendor invoice has no lines'; end if;

  for r in$anchor$;
  v_replacement:=$replacement$  if not exists (select 1 from erp.vendor_invoice_items where invoice_id=h.id) then raise exception 'Vendor invoice has no lines'; end if;

  for v_group_id in
    select distinct ldl.cutting_group_id
    from erp.vendor_invoice_items vii
    join erp.laundry_receipt_lines lrl on lrl.id=vii.receipt_line_id
    join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
    where vii.invoice_id=h.id
    order by ldl.cutting_group_id
  loop
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
  end loop;
  perform 1
  from erp.laundry_receipts lr
  where lr.id in(
    select distinct lrl.receipt_id
    from erp.vendor_invoice_items vii
    join erp.laundry_receipt_lines lrl on lrl.id=vii.receipt_line_id
    where vii.invoice_id=h.id
  )
  order by lr.id
  for update;
  perform 1
  from erp.laundry_receipt_lines lrl
  where lrl.id in(
    select vii.receipt_line_id
    from erp.vendor_invoice_items vii where vii.invoice_id=h.id
  )
  order by lrl.id
  for update;

  for r in$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: post_vendor_invoice lock anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);
  execute v_definition;

  select pg_get_functiondef('erp.reverse_vendor_invoice(uuid,text)'::regprocedure)
    into v_definition;
  v_anchor:=$anchor$  v_qty integer;
begin$anchor$;
  v_replacement:=$replacement$  v_qty integer;
  v_group_id uuid;
begin$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: reverse_vendor_invoice declaration anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  if h.status<>'POSTED' then raise exception 'Hanya invoice vendor laundry yang sudah POSTED yang dapat direverse'; end if;

  select id into v_journal$anchor$;
  v_replacement:=$replacement$  if h.status<>'POSTED' then raise exception 'Hanya invoice vendor laundry yang sudah POSTED yang dapat direverse'; end if;

  for v_group_id in
    select distinct ldl.cutting_group_id
    from erp.vendor_invoice_items vii
    join erp.laundry_receipt_lines lrl on lrl.id=vii.receipt_line_id
    join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
    where vii.invoice_id=h.id
    order by ldl.cutting_group_id
  loop
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
  end loop;
  perform 1
  from erp.laundry_receipts lr
  where lr.id in(
    select distinct lrl.receipt_id
    from erp.vendor_invoice_items vii
    join erp.laundry_receipt_lines lrl on lrl.id=vii.receipt_line_id
    where vii.invoice_id=h.id
  )
  order by lr.id
  for update;
  perform 1
  from erp.laundry_receipt_lines lrl
  where lrl.id in(
    select vii.receipt_line_id
    from erp.vendor_invoice_items vii where vii.invoice_id=h.id
  )
  order by lrl.id
  for update;

  select id into v_journal$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: reverse_vendor_invoice lock anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);
  execute v_definition;
end
$patch_invoice_lifecycle$;

-- F02: current-state capacity remains mandatory, but a second independent
-- prefix-time check now counts every historical dispatch until its linked
-- append-only return event has physically occurred.  A status flag can no
-- longer make stock appear back in Sewing before the operator's return time.
do $patch_physical_timeline$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef(
    'erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'::regprocedure
  ) into v_definition;

  v_anchor:=$anchor$    ) then raise exception 'Requested Laundry size quantity exceeds its remaining distribution-batch capacity'; end if;
    select sum(x.qty_sent_pcs)::bigint into v_total$anchor$;
  v_replacement:=$replacement$    ) then raise exception 'Requested Laundry size quantity exceeds its remaining distribution-batch capacity'; end if;

    if exists(
      select 1
      from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer)
      left join lateral(
        select coalesce(sum(a.qty_pcs),0)::bigint qty
        from erp.cutting_distribution_allocations a
        join erp.cutting_roll_yields y on y.id=a.cutting_roll_yield_id
        join erp.cutting_group_size_slots s on s.id=y.size_slot_id
        where a.batch_id=v_batch_id and s.size_id=x.size_id
      ) cap on true
      left join lateral(
        select coalesce(sum(sx.qty_sent_pcs),0)::bigint qty
        from erp.laundry_delivery_batch_size_lines sx
        join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
        join erp.laundry_deliveries d on d.id=dl.delivery_id
        where sx.distribution_batch_id=v_batch_id and sx.size_id=x.size_id
          and d.status<>'DRAFT' and d.physical_at<=v_physical_at
      ) dispatched_at_prefix on true
      left join lateral(
        select coalesce(sum(sx.qty_sent_pcs),0)::bigint qty
        from erp.laundry_delivery_batch_size_lines sx
        join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
        join erp.wip_stage_events src
          on src.source_type='LAUNDRY_DELIVERY_LINE' and src.source_id=dl.id
        join erp.wip_stage_events rv
          on rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
         and rv.source_id=src.id and rv.physical_at<=v_physical_at
        where sx.distribution_batch_id=v_batch_id and sx.size_id=x.size_id
      ) returned_at_prefix on true
      where x.qty_sent_pcs>cap.qty-dispatched_at_prefix.qty+returned_at_prefix.qty
    ) then
      raise exception 'Laundry redispatch time precedes sufficient linked physical return for this distribution batch/size';
    end if;

    select sum(x.qty_sent_pcs)::bigint into v_total$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: CP6 size-prefix anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$        where dl.cutting_group_id=v_group.id
          and d.status not in('DRAFT','REVERSED') and d.physical_at<=v_physical_at
      ),0)
      -coalesce(($anchor$;
  v_replacement:=$replacement$        where dl.cutting_group_id=v_group.id
          and d.status<>'DRAFT' and d.physical_at<=v_physical_at
      ),0)
      +coalesce((
        select sum(rv.qty_pcs)
        from erp.wip_stage_events rv
        join erp.wip_stage_events src
          on src.id=rv.source_id and src.source_type='LAUNDRY_DELIVERY_LINE'
        where rv.cutting_group_id=v_group.id
          and rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
          and rv.physical_at<=v_physical_at
      ),0)
      -coalesce(($replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: CP6 group-prefix anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);
  execute v_definition;
end
$patch_physical_timeline$;

-- F06: the connected workspace is explicitly bounded.  Each transactional
-- collection returns at most 200 rows and the relevant Final-SKU lookup at
-- most 500 rows, with machine-readable truncation flags.  Operators are told
-- to refine the server query; the browser never pretends a partial history is
-- complete.  Product lookup is narrowed to model/size combinations that have
-- a live QC source when scope=QC.
do $patch_bounded_workspace$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef(
    'erp.get_laundry_qc_workspace_v1(text,text)'::regprocedure
  ) into v_definition;

  v_anchor:=$anchor$  v_qc_history jsonb:='[]'::jsonb;
  v_lineage_issue_count bigint:=0;
begin$anchor$;
  v_replacement:=$replacement$  v_qc_history jsonb:='[]'::jsonb;
  v_lineage_issue_count bigint:=0;
  v_collection_limit constant integer:=200;
  v_product_limit constant integer:=500;
  v_products_truncated boolean:=false;
  v_ready_truncated boolean:=false;
  v_deliveries_truncated boolean:=false;
  v_qc_queue_truncated boolean:=false;
  v_qc_history_truncated boolean:=false;
begin$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: workspace declaration anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  select coalesce(jsonb_agg(jsonb_build_object(
    'id',p.id,'sku',p.sku,'name',p.product_name,'model_id',p.model_id,
    'model_code',m.model_code,'model_name',m.model_name,
    'brand_id',p.brand_id,'brand_code',b.brand_code,'brand_name',b.brand_name,
    'size_id',p.size_id,'size_code',s.size_code,'color',p.color_name,
    'effective_from',p.effective_from,'effective_to',p.effective_to
  ) order by b.brand_name,p.sku,m.model_name,p.color_name,s.sort_order,p.id),'[]'::jsonb) into v_products
  from erp.products p
  join erp.product_models m on m.id=p.model_id and m.is_active
  join erp.brands b on b.id=p.brand_id and b.is_active
  join erp.sizes s on s.id=p.size_id and s.is_active
  where p.is_active and p.is_portal_visible;$anchor$;
  v_replacement:=$replacement$  select coalesce(jsonb_agg(to_jsonb(x)-'size_sort'
    order by x.brand_name,x.sku,x.model_name,x.color,x.size_sort,x.id),'[]'::jsonb)
    into v_products
  from(
    select p.id,p.sku,p.product_name name,p.model_id,
      m.model_code,m.model_name,p.brand_id,b.brand_code,b.brand_name,
      p.size_id,s.size_code,s.sort_order size_sort,p.color_name color,
      p.effective_from,p.effective_to
    from erp.products p
    join erp.product_models m on m.id=p.model_id and m.is_active
    join erp.brands b on b.id=p.brand_id and b.is_active
    join erp.sizes s on s.id=p.size_id and s.is_active
    where p.is_active and p.is_portal_visible
      and v_scope='QC' and exists(
        select 1
        from erp.laundry_receipt_batch_size_lines rx
        join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
        join erp.laundry_receipts rh on rh.id=rl.receipt_id and rh.status='POSTED'
        join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
        join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
        join erp.cutting_groups g on g.id=dl.cutting_group_id and g.po_id=d.po_id
        join erp.production_orders po on po.id=g.po_id and po.model_id=p.model_id
        where rx.size_id=p.size_id
          and rx.qty_good_received>coalesce((
            select sum(qi.qty_good_pcs+qi.qty_bs_pcs)
            from erp.qc_inspection_items qi
            join erp.qc_inspections qh on qh.id=qi.inspection_id
            where qi.source_laundry_receipt_batch_size_line_id=rx.id
              and qh.status<>'REVERSED'
          ),0)
          and(v_query is null or lower(concat_ws(' ',rh.receipt_number,
            d.delivery_number,po.po_number,g.group_number,m.model_code,
            m.model_name,b.brand_code,b.brand_name,p.sku,p.product_name,
            s.size_code)) like '%'||v_query||'%')
      )
    order by b.brand_name,p.sku,m.model_name,p.color_name,s.sort_order,p.id
    limit v_product_limit+1
  ) x;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: workspace product anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$            where x.distribution_batch_id=b.id and x.size_id=cap.size_id
              and d.status not in('DRAFT','REVERSED')
          ),0)
        )
    ) z;

    select coalesce(jsonb_agg(to_jsonb(z) order by z.physical_at desc,z.delivery_id desc),'[]'::jsonb)$anchor$;
  v_replacement:=$replacement$            where x.distribution_batch_id=b.id and x.size_id=cap.size_id
              and d.status not in('DRAFT','REVERSED')
          ),0)
        )
      order by po.po_number,g.group_number,b.batch_no,b.id
      limit v_collection_limit+1
    ) z;

    select coalesce(jsonb_agg(to_jsonb(z) order by z.physical_at desc,z.delivery_id desc),'[]'::jsonb)$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: workspace ready-batch anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$        w.id,w.process_code,w.process_name,dl.id,dl.qty_sent_pcs,dl.estimated_rate_snapshot,
        x.distribution_batch_id,b.batch_no,rev.reversal_blocker
    ) z;
  else$anchor$;
  v_replacement:=$replacement$        w.id,w.process_code,w.process_name,dl.id,dl.qty_sent_pcs,dl.estimated_rate_snapshot,
        x.distribution_batch_id,b.batch_no,rev.reversal_blocker
      order by d.physical_at desc,d.id desc
      limit v_collection_limit+1
    ) z;
  else$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: workspace delivery anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$        and(v_query is null or lower(concat_ws(' ',r.receipt_number,d.delivery_number,po.po_number,
          g.group_number,m.model_code,m.model_name,v.vendor_name,s.size_code,b.batch_no::text)) like '%'||v_query||'%')
    ) z;

    select coalesce(jsonb_agg(to_jsonb(z) order by z.physical_at desc,z.qc_inspection_id desc),'[]'::jsonb)$anchor$;
  v_replacement:=$replacement$        and(v_query is null or lower(concat_ws(' ',r.receipt_number,d.delivery_number,po.po_number,
          g.group_number,m.model_code,m.model_name,v.vendor_name,s.size_code,b.batch_no::text)) like '%'||v_query||'%')
      order by po.po_number,g.group_number,b.batch_no,s.sort_order,s.size_code,rx.id
      limit v_collection_limit+1
    ) z;

    select coalesce(jsonb_agg(to_jsonb(z) order by z.physical_at desc,z.qc_inspection_id desc),'[]'::jsonb)$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: workspace QC-queue anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$      group by q.id,q.inspection_number,q.status,q.row_version,q.physical_at,
        q.destination_location_id,l.location_name,q.po_id,po.po_number,po.status,rev.reversal_blocker
    ) z;
  end if;

  return jsonb_build_object($anchor$;
  v_replacement:=$replacement$      group by q.id,q.inspection_number,q.status,q.row_version,q.physical_at,
        q.destination_location_id,l.location_name,q.po_id,po.po_number,po.status,rev.reversal_blocker
      order by q.physical_at desc,q.id desc
      limit v_collection_limit+1
    ) z;
  end if;

  v_products_truncated:=jsonb_array_length(v_products)>v_product_limit;
  v_ready_truncated:=jsonb_array_length(v_ready)>v_collection_limit;
  v_deliveries_truncated:=jsonb_array_length(v_deliveries)>v_collection_limit;
  v_qc_queue_truncated:=jsonb_array_length(v_qc_queue)>v_collection_limit;
  v_qc_history_truncated:=jsonb_array_length(v_qc_history)>v_collection_limit;
  if v_products_truncated then v_products:=v_products-v_product_limit; end if;
  if v_ready_truncated then v_ready:=v_ready-v_collection_limit; end if;
  if v_deliveries_truncated then v_deliveries:=v_deliveries-v_collection_limit; end if;
  if v_qc_queue_truncated then v_qc_queue:=v_qc_queue-v_collection_limit; end if;
  if v_qc_history_truncated then v_qc_history:=v_qc_history-v_collection_limit; end if;

  return jsonb_build_object($replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: workspace QC-history anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$    'ready_batches',v_ready,'deliveries',v_deliveries,
    'qc_queue',v_qc_queue,'qc_history',v_qc_history,$anchor$;
  v_replacement:=$replacement$    'collection_window',jsonb_build_object(
      'transaction_limit',v_collection_limit,
      'product_limit',v_product_limit,
      'query_required_for_more',true,
      'products_relevant_to_live_qc',v_scope='QC',
      'products_truncated',v_products_truncated,
      'ready_batches_truncated',v_ready_truncated,
      'deliveries_truncated',v_deliveries_truncated,
      'qc_queue_truncated',v_qc_queue_truncated,
      'qc_history_truncated',v_qc_history_truncated,
      'any_truncated',v_products_truncated or v_ready_truncated
        or v_deliveries_truncated or v_qc_queue_truncated or v_qc_history_truncated
    ),
    'ready_batches',v_ready,'deliveries',v_deliveries,
    'qc_queue',v_qc_queue,'qc_history',v_qc_history,$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: workspace return anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);
  execute v_definition;
end
$patch_bounded_workspace$;

-- F06 hot dependency lookup.  FK constraints do not automatically create an
-- index on their referencing columns; preserve this index even while UAT is
-- empty because reversal/dependency checks use delivery_id repeatedly.
create index idx_laundry_failed_wash_attempts_delivery_v2620a
  on erp.laundry_failed_wash_attempts(delivery_id)
  include(receipt_id,receipt_line_id,custody_outcome,qty_attempted_pcs,return_wip_event_id);

do $installed_guard$
begin
  if position('CP6FLOW:' in pg_get_functiondef(
       'erp.post_vendor_invoice(uuid)'::regprocedure
     ))=0
     or position('CP6FLOW:' in pg_get_functiondef(
       'erp.reverse_vendor_invoice(uuid,text)'::regprocedure
     ))=0
     or position('returned_at_prefix' in pg_get_functiondef(
       'erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'::regprocedure
     ))=0
     or position('CP6_LAUNDRY_DELIVERY_WIP_REVERSAL' in pg_get_functiondef(
       'erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'::regprocedure
      ))=0
     or position('collection_window' in pg_get_functiondef(
       'erp.get_laundry_qc_workspace_v1(text,text)'::regprocedure
     ))=0 then
    raise exception 'ERP v2.6.20a reliability patch did not install completely';
  end if;

  update erp.cp6_v2620a_rollback_capsule c
  set installed_definition_sha256=encode(extensions.digest(convert_to(
    pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'
  ),'sha256'),'hex');
  if (select count(*) from erp.cp6_v2620a_rollback_capsule
      where installed_definition_sha256 is not null)<>4 then
    raise exception 'ERP v2.6.20a installed-definition capsule is incomplete';
  end if;
end
$installed_guard$;

insert into erp.schema_migrations(version,description)
values('v2.6.20a','CP6 audit closure: canonical invoice locks, physical-time prefix conservation, hot dependency index');

commit;
