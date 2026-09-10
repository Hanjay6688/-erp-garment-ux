-- Shared sequential SQL cases: executed on native PostgreSQL in CI and on
-- local PGlite by the writer. The driver rolls every case back; no hosted use.
-- pg_temp helpers are fixture/oracle code, never application migrations.

create function pg_temp.g_product() returns uuid language plpgsql as $$
declare p uuid:=gen_random_uuid();
begin
  insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,product_name,
    identity_root_id,effective_from,is_active,is_portal_visible)
  select p,'G-'||p,model_id,brand_id,'G-'||p,size_id,'G independent regression',
    p,effective_from,true,true from erp.products
  where id='c8c10000-0000-4000-8000-000000000004';
  insert into erp.accessory_bom_versions(product_id,version_label,effective_from,is_active,notes)
  values(p,'G-EMPTY','2026-01-01',true,'Explicit empty BOM');
  return p;
end $$;

create function pg_temp.g_open(p uuid,n integer,c numeric,lines integer default 1)
returns uuid language plpgsql as $$
declare h uuid:=gen_random_uuid(); i integer;
begin
  insert into erp.opening_balance_headers(id,opening_number,opening_date,status,created_by)
  values(h,'G-OPEN-'||h,'2026-09-01','DRAFT',erp.current_app_user_id());
  for i in 1..lines loop
    insert into erp.opening_balance_items(opening_id,balance_type,product_id,
      location_id,qty,unit_cost_snapshot,quality_grade,hpp_input_method)
    values(h,'FINISHED_GOODS',p,'c8c20000-0000-4000-8000-000000000001',
      n,c,'GRADE_A','MANUAL');
  end loop;
  perform erp.post_opening_balance(h);
  return h;
end $$;

create function pg_temp.g_adjust(l uuid,n integer) returns uuid language plpgsql as $$
declare r jsonb;
begin
  r:=erp.save_fg_adjustment_draft_v2(jsonb_build_object(
    'adjustment_number','G-ADJ-'||gen_random_uuid(),
    'location_id','c8c20000-0000-4000-8000-000000000001',
    'physical_at',clock_timestamp(),'reason_code',case when n<0 then 'LOSS' else 'FOUND' end,
    'reason','Physical stock count discrepancy','change_reason','G independent lifecycle',
    'items',jsonb_build_array(jsonb_build_object('lot_id',l,
      'product_id',(select product_id from erp.fg_lots where id=l),
      'quality_grade','GRADE_A','qty_signed',n,'notes','Observed physical count'))
  ),gen_random_uuid(),null);
  perform erp.post_fg_adjustment((r->>'fg_adjustment_id')::uuid);
  return (r->>'fg_adjustment_id')::uuid;
end $$;

create function pg_temp.g_sale(p uuid,n integer) returns uuid language plpgsql as $$
declare c uuid:=gen_random_uuid(); r jsonb;
begin
  insert into erp.customers(id,customer_code,customer_name,is_active)
  values(c,'G-'||substr(c::text,1,24),'G disposable customer',true);
  r:=erp.save_sale_draft_v2(jsonb_build_object('sale_number','G-SALE-'||gen_random_uuid(),
    'customer_id',c,'source_location_id','c8c20000-0000-4000-8000-000000000001',
    'sale_date',clock_timestamp(),'reason','Lawful physical sale after all prior events',
    'items',jsonb_build_array(jsonb_build_object('product_id',p,'qty_pcs',n,
      'unit_price_snapshot',20,'discount_amount',0))),gen_random_uuid(),null);
  perform erp.post_sale((r->>'sale_id')::uuid);
  return (r->>'sale_id')::uuid;
end $$;

create function pg_temp.g_return(s uuid,n integer) returns uuid language plpgsql as $$
declare r uuid:=gen_random_uuid(); a record; remaining integer:=n; q integer;
begin
  insert into erp.sales_returns(id,return_number,sale_id,customer_id,physical_at,
    status,notes,created_by)
  select r,'G-RET-'||r,id,customer_id,clock_timestamp(),'DRAFT',
    'G linked physical return',erp.current_app_user_id()
  from erp.sales_headers where id=s;
  for a in select alloc.*,fl.product_id from erp.sale_stock_allocations alloc
    join erp.sales_items i on i.id=alloc.sale_item_id join erp.fg_lots fl on fl.id=alloc.lot_id
    where i.sale_id=s order by alloc.id
  loop
    select least(remaining,a.qty_pcs-coalesce(sum(ri.qty_pcs),0))::integer into q
    from erp.sales_return_items ri join erp.sales_returns rh on rh.id=ri.return_id
    where ri.sale_stock_allocation_id=a.id and rh.status='POSTED';
    if q>0 then
      insert into erp.sales_return_items(return_id,sale_stock_allocation_id,
        product_id,lot_id,location_id,quality_grade,qty_pcs,unit_hpp_snapshot,refund_amount)
      values(r,a.id,a.product_id,a.lot_id,a.location_id,'GRADE_A',q,0,q*20);
      remaining:=remaining-q;
    end if;
    exit when remaining=0;
  end loop;
  if remaining<>0 then raise exception 'Fixture return exceeds allocation'; end if;
  perform erp.post_sales_return(r);
  return r;
end $$;

create function pg_temp.g_assert(p uuid,basis numeric,fg numeric,cogs numeric,other numeric)
returns void language plpgsql as $$
declare t record; b record; r jsonb;
begin
  select * into t from erp.compute_non_po_product_hpp_targets_v2620f(p);
  select * into b from erp.compute_non_po_product_hpp_book_v2620f(p);
  if row(t.hpp_total_cost,t.fg_value,t.cogs_value,t.other_out_value)
       is distinct from row(basis,fg,cogs,other)
     or row(b.hpp_total_cost,b.fg_value,b.cogs_value,b.other_out_value)
       is distinct from row(basis,fg,cogs,other) then
    raise exception 'G independent exact-cent oracle mismatch: expected %, target %, book %',
      array[basis,fg,cogs,other],array[t.hpp_total_cost,t.fg_value,t.cogs_value,t.other_out_value],
      array[b.hpp_total_cost,b.fg_value,b.cogs_value,b.other_out_value];
  end if;
  if basis<>fg+cogs+other then raise exception 'G oracle itself does not conserve source'; end if;
  if exists(select 1 from erp.journal_lines group by journal_entry_id having sum(debit-credit)<>0)
  then raise exception 'G unbalanced journal'; end if;
  r:=erp.get_owner_financial_snapshot_v2('2026-09-01',current_date,current_date);
  if r#>>'{data_confidence,status}'<>'READY' then raise exception 'G valid flow not READY: %',r->'data_confidence'; end if;
end $$;

create function pg_temp.g_n01_split_loss() returns jsonb language plpgsql as $$
declare p uuid:=pg_temp.g_product(); l uuid; a uuid[]:='{}'; s uuid; r uuid; i integer; c numeric;
begin
  perform pg_temp.g_open(p,10,.011);
  select id into l from erp.fg_lots where product_id=p;
  for i in 1..5 loop
    a:=array_append(a,pg_temp.g_adjust(l,-1));
    c:=round(i*.011,2);
    perform pg_temp.g_assert(p,.11,.11-c,0,c);
  end loop;
  s:=pg_temp.g_sale(p,5);
  perform pg_temp.g_assert(p,.11,0,.06,.05);
  r:=pg_temp.g_return(s,2);
  perform pg_temp.g_assert(p,.11,.02,.03,.06);
  perform erp.reverse_sales_return(r,'G linked return reversal');
  perform pg_temp.g_assert(p,.11,0,.06,.05);
  perform erp.reverse_sale(s,'G linked sale reversal');
  perform pg_temp.g_assert(p,.11,.05,0,.06);
  foreach i in array array[3,1,5,2,4] loop
    perform erp.reverse_fg_adjustment(a[i],'G non-FIFO loss reversal');
  end loop;
  perform pg_temp.g_assert(p,.11,.11,0,0);
  -- Idempotent inverse must not append any further financial event.
  select count(*) into c from erp.non_po_hpp_gl_sync_events_v2620f;
  perform erp.reverse_fg_adjustment(a[1],'G replay same inverse');
  if c<>(select count(*) from erp.non_po_hpp_gl_sync_events_v2620f) then
    raise exception 'G repeated inverse appended value';
  end if;
  if exists(select 1 from(select sum(qty_signed) over(order by physical_at,book_order) q
    from erp.fg_stock_movements where product_id=p)x where q<0)
  then raise exception 'G fixture violates physical chronology'; end if;
  return jsonb_build_object('status','PASS','source',.11,'sold_out_fg',0,
    'sold_out_cogs',.06,'sold_out_loss_net',.05,'final_fg',.11,'inverse_order',a);
end $$;

create function pg_temp.g_n01_gain_lumped() returns jsonb language plpgsql as $$
declare p uuid:=pg_temp.g_product(); l uuid; a uuid; gains uuid[]:='{}'; i integer; s uuid;
begin
  perform pg_temp.g_open(p,10,.011);
  select id into l from erp.fg_lots where product_id=p;
  a:=pg_temp.g_adjust(l,-5);
  perform pg_temp.g_assert(p,.11,.05,0,.06);
  perform erp.reverse_fg_adjustment(a,'G lumped loss reversal');
  for i in 1..5 loop
    gains:=array_append(gains,pg_temp.g_adjust(l,1));
    perform pg_temp.g_assert(p,.11,.11+round(i*.011,2),0,-round(i*.011,2));
  end loop;
  s:=pg_temp.g_sale(p,15);
  perform pg_temp.g_assert(p,.11,0,.17,-.06);
  perform erp.reverse_sale(s,'G return all gained stock before count reversal');
  foreach i in array array[2,4,1,5,3] loop
    perform erp.reverse_fg_adjustment(gains[i],'G non-FIFO gain reversal');
  end loop;
  perform pg_temp.g_assert(p,.11,.11,0,0);
  return jsonb_build_object('status','PASS','lumped_equals_split',true,'gain_reversal',true);
end $$;

create function pg_temp.g_n02_multiline() returns jsonb language plpgsql as $$
declare p uuid:=pg_temp.g_product(); q uuid:=pg_temp.g_product(); h uuid; s uuid; r uuid;
  l uuid; corr uuid; deb numeric; cred numeric; x record;
begin
  h:=pg_temp.g_open(p,5,.011,2);
  select sum(j.debit),sum(j.credit) into deb,cred from erp.journal_lines j
  join erp.journal_entries e on e.id=j.journal_entry_id where e.source_id=h and e.source_type='OPENING_BALANCE';
  if deb<>.12 or cred<>.12 then raise exception 'G multiline must post .12/.12, got %/%',deb,cred; end if;
  perform pg_temp.g_assert(p,.12,.12,0,0);
  s:=pg_temp.g_sale(p,10);
  perform pg_temp.g_assert(p,.12,0,.12,0);
  r:=pg_temp.g_return(s,10);
  perform pg_temp.g_assert(p,.12,.12,0,0);
  perform erp.reverse_sales_return(r,'G inverse multiline return');
  perform erp.reverse_sale(s,'G inverse multiline sale');
  select id into l from erp.fg_lots where product_id=p order by id limit 1;
  corr:=erp.post_opening_hpp_correction(l,.0129,'G raw HPP change within same rounded source basis',current_date);
  perform pg_temp.g_assert(p,.12,.12,0,0);
  perform erp.reverse_opening_hpp_correction(corr,'G same-basis raw HPP correction inverse');
  perform pg_temp.g_assert(p,.12,.12,0,0);
  corr:=erp.post_opening_hpp_correction(l,.021,'G reprice one rounded source lot',current_date);
  perform pg_temp.g_assert(p,.17,.17,0,0);
  perform erp.reverse_opening_hpp_correction(corr,'G linked opening correction reversal');
  perform pg_temp.g_assert(p,.12,.12,0,0);
  s:=pg_temp.g_sale(p,10);
  perform pg_temp.g_assert(p,.12,0,.12,0);
  -- The second independent audit example uses different products in one header.
  h:=gen_random_uuid();
  insert into erp.opening_balance_headers(id,opening_number,opening_date,status,created_by)
  values(h,'G-OPEN2-'||h,'2026-09-01','DRAFT',erp.current_app_user_id());
  for x in select id from(values(pg_temp.g_product()),(q))v(id) loop
    insert into erp.opening_balance_items(opening_id,balance_type,product_id,location_id,
      qty,unit_cost_snapshot,quality_grade,hpp_input_method)
    values(h,'FINISHED_GOODS',x.id,'c8c20000-0000-4000-8000-000000000001',1,.006,'GRADE_A','MANUAL');
  end loop;
  perform erp.post_opening_balance(h);
  select sum(j.debit),sum(j.credit) into deb,cred from erp.journal_lines j
  join erp.journal_entries e on e.id=j.journal_entry_id where e.source_id=h and e.source_type='OPENING_BALANCE';
  if deb<>.02 or cred<>.02 then raise exception 'G two-SKU must post .02/.02'; end if;
  perform pg_temp.g_assert(q,.01,.01,0,0);
  return jsonb_build_object('status','PASS','same_sku_equity',.12,'two_sku_equity',.02,
    'multilot_sale_return_correction_inverse',true);
end $$;

create function pg_temp.g_n02_corrected_loss() returns jsonb language plpgsql as $$
declare p uuid:=pg_temp.g_product(); l uuid; a uuid[]:='{}'; s uuid; corr uuid; i integer;
begin
  perform pg_temp.g_open(p,10,.011);
  select id into l from erp.fg_lots where product_id=p;
  for i in 1..5 loop a:=array_append(a,pg_temp.g_adjust(l,-1)); end loop;
  corr:=erp.post_opening_hpp_correction(l,.021,'G reprice after physically valid split losses',current_date);
  perform pg_temp.g_assert(p,.21,.10,0,.11);
  s:=pg_temp.g_sale(p,5);
  perform pg_temp.g_assert(p,.21,0,.11,.10);
  perform erp.reverse_sale(s,'G inverse sale after recost');
  for i in 1..5 loop perform erp.reverse_fg_adjustment(a[i],'G loss reversal after recost'); end loop;
  perform pg_temp.g_assert(p,.21,.21,0,0);
  perform erp.reverse_opening_hpp_correction(corr,'G recost inverse after physical restore');
  perform pg_temp.g_assert(p,.11,.11,0,0);
  return jsonb_build_object('status','PASS','loss_recost_sale_reversals',true);
end $$;

create function pg_temp.g_n02_zero_minor_units() returns jsonb language plpgsql as $$
declare p uuid:=pg_temp.g_product(); h uuid; s uuid;
begin
  h:=pg_temp.g_open(p,1,.004,2);
  perform pg_temp.g_assert(p,0,0,0,0);
  s:=pg_temp.g_sale(p,2);
  perform pg_temp.g_assert(p,0,0,0,0);
  perform erp.reverse_sale(s,'G zero-cent source sale inverse');
  perform pg_temp.g_assert(p,0,0,0,0);
  return jsonb_build_object('status','PASS','raw_unit_cost',.004,'rounded_lot_basis',0);
end $$;

create function pg_temp.g_n01_threshold_matrix() returns jsonb language plpgsql as $$
declare c numeric; p uuid; l uuid; losses uuid[]; s uuid; ret uuid; i integer;
  basis numeric; outflow numeric; cogs numeric; passed integer:=0;
begin
  foreach c in array array[0,.001,.004,.005,.006,.011,.015,.021,.333333,1.005] loop
    -- Use a subtransaction only to discard a completed fixture, never to retry
    -- or turn a failed business action into success.
    begin
      p:=pg_temp.g_product(); losses:='{}'; basis:=round(10*c,2);
      perform pg_temp.g_open(p,10,c);
      select id into l from erp.fg_lots where product_id=p;
      for i in 1..5 loop
        losses:=array_append(losses,pg_temp.g_adjust(l,-1));
        outflow:=round(i*c,2);
        perform pg_temp.g_assert(p,basis,basis-outflow,0,outflow);
      end loop;
      s:=pg_temp.g_sale(p,5); cogs:=round(5*c,2);
      perform pg_temp.g_assert(p,basis,0,cogs,basis-cogs);
      ret:=pg_temp.g_return(s,1); cogs:=round(4*c,2); outflow:=round(9*c,2);
      perform pg_temp.g_assert(p,basis,basis-outflow,cogs,outflow-cogs);
      perform erp.reverse_sales_return(ret,'G threshold return inverse');
      perform erp.reverse_sale(s,'G threshold sale inverse');
      for i in 1..5 loop perform erp.reverse_fg_adjustment(losses[i],'G threshold loss inverse'); end loop;
      perform pg_temp.g_assert(p,basis,basis,0,0);
      passed:=passed+1;
      raise exception using errcode='G0002',message='Discard completed threshold fixture';
    exception when sqlstate 'G0002' then null;
    end;
  end loop;
  if passed<>10 then raise exception 'G incomplete threshold matrix'; end if;
  return jsonb_build_object('status','PASS','independent_unit_cost_boundaries',passed,
    'unit_costs',array[0,.001,.004,.005,.006,.011,.015,.021,.333333,1.005]);
end $$;

create function pg_temp.g_n02_reserved_reprice() returns jsonb language plpgsql as $$
declare p uuid:=pg_temp.g_product(); l uuid; c uuid:=gen_random_uuid(); s jsonb; corr uuid; stock_before bigint;
begin
  perform pg_temp.g_open(p,10,.011);
  select id into l from erp.fg_lots where product_id=p;
  insert into erp.customers(id,customer_code,customer_name,is_active)
  values(c,'G-'||substr(c::text,1,24),'G reserved reprice customer',true);
  s:=erp.save_sale_draft_v2(jsonb_build_object('sale_number','G-DRAFT-'||gen_random_uuid(),
    'customer_id',c,'source_location_id','c8c20000-0000-4000-8000-000000000001',
    'sale_date',clock_timestamp(),'reason','G reserved ownership is not sold inventory',
    'items',jsonb_build_array(jsonb_build_object('product_id',p,'qty_pcs',5,
      'unit_price_snapshot',20,'discount_amount',0))),gen_random_uuid(),null);
  select cached_qty_pcs into stock_before from erp.fg_lots where id=l;
  if stock_before<>5 then raise exception 'G draft did not reserve exactly once'; end if;
  corr:=erp.post_opening_hpp_correction(l,.021,'G reprice while five owned pcs are reserved',current_date);
  perform pg_temp.g_assert(p,.21,.21,0,0);
  perform erp.post_sale_v2((s->>'sale_id')::uuid,gen_random_uuid(),(s->>'row_version')::bigint);
  if (select cached_qty_pcs from erp.fg_lots where id=l)<>stock_before then
    raise exception 'G post deducted reserved stock twice';
  end if;
  perform pg_temp.g_assert(p,.21,.10,.11,0);
  perform erp.reverse_sale((s->>'sale_id')::uuid,'G linked reserved sale inverse');
  perform erp.reverse_opening_hpp_correction(corr,'G reserved repricing inverse');
  perform pg_temp.g_assert(p,.11,.11,0,0);
  return jsonb_build_object('status','PASS','draft_sellable',5,'owned_value_after_reprice',.21,
    'post_stock_delta',0,'final_fg',.11);
end $$;

create function pg_temp.g_action(a text,p jsonb,v bigint) returns jsonb language plpgsql as $$
declare r jsonb;
begin
  -- The rollback-only driver encloses many RPCs in one outer transaction.
  -- Real HTTP RPCs get a fresh transaction; do not leak a failed-wash request's
  -- transaction-local physical timestamp into the next cancellation request.
  perform set_config('app.physical_at','',true);
  set local role authenticated;
  r:=public.erp_save_laundry_qc_action_v1(a,p,gen_random_uuid(),v);
  reset role;
  return r;
end $$;

create function pg_temp.g_dispatch(q integer,t timestamptz) returns jsonb language plpgsql as $$
begin
  return pg_temp.g_action('POST_DELIVERY',jsonb_build_object(
    'distribution_batch_id','c8c40000-0000-4000-8000-000000000008',
    'vendor_id','c8c20000-0000-4000-8000-000000000002',
    'wash_process_id','c8c20000-0000-4000-8000-000000000003',
    'target_dyeing_color','NAVY','physical_at',t,'reason','G actual dispatch',
    'lines',jsonb_build_array(jsonb_build_object(
      'size_id','c8c10000-0000-4000-8000-000000000002','qty_sent_pcs',q))),
    (select row_version from erp.cutting_groups where id='c8c40000-0000-4000-8000-000000000003'));
end $$;

create function pg_temp.g_n03_source_detector() returns jsonb language plpgsql as $$
declare d jsonb; f jsonb; d2 jsonb; baseline jsonb; r jsonb; src uuid; inv uuid;
  faults jsonb:='[]'; x record; evidence jsonb; rejected boolean:=false; outstanding bigint;
begin
  d:=pg_temp.g_dispatch(10,'2026-09-01T11:00Z');
  f:=pg_temp.g_action('POST_FAILED_WASH',jsonb_build_object(
    'delivery_id',d->>'delivery_id','wash_process_id','c8c20000-0000-4000-8000-000000000003',
    'custody_outcome','RETURN_UNPROCESSED','physical_at','2026-09-02T11:00:00Z',
    'reason','G all ten physically returned unprocessed','lines',jsonb_build_array(jsonb_build_object(
      'delivery_batch_size_line_id',(select sx.id from erp.laundry_delivery_batch_size_lines sx
        join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id where dl.delivery_id=(d->>'delivery_id')::uuid),
      'qty_attempted_pcs',10))),
    (select row_version from erp.laundry_deliveries where id=(d->>'delivery_id')::uuid));
  d2:=pg_temp.g_dispatch(4,'2026-09-03T11:00Z');
  perform pg_temp.g_action('REVERSE_DELIVERY',jsonb_build_object('delivery_id',d2->>'delivery_id',
    'reason','G cancel unused four'),(select row_version from erp.laundry_deliveries where id=(d2->>'delivery_id')::uuid));
  perform pg_temp.g_action('REVERSE_RECEIPT',jsonb_build_object('receipt_id',f->>'receipt_id',
    'reason','G financial failed-wash cost reversal; custody remains'),
    (select row_version from erp.laundry_receipts where id=(f->>'receipt_id')::uuid));
  select s.id into src from erp.wip_stage_events s join erp.laundry_delivery_lines dl on dl.id=s.source_id
  where s.source_type='LAUNDRY_DELIVERY_LINE' and dl.delivery_id=(d->>'delivery_id')::uuid;
  select id into inv from erp.wip_stage_events where source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL' and source_id=src;
  baseline:=erp.get_owner_financial_snapshot_v2('2026-09-01',current_date,current_date);
  if baseline#>>'{data_confidence,status}'<>'READY' then raise exception 'G valid WIP baseline not READY: %',baseline->'data_confidence'; end if;
  select coalesce(sum(case when stage_to='LAUNDRY' then qty_pcs else 0 end
    -case when stage_from='LAUNDRY' then qty_pcs else 0 end),0) into outstanding
  from erp.wip_stage_events where po_id='c8c40000-0000-4000-8000-000000000001';
  if outstanding<>0 then raise exception 'G own PO custody not restored: %',outstanding; end if;
  begin
    set local role authenticated;
    update erp.wip_stage_events set qty_pcs=11 where id=src;
  exception when insufficient_privilege then rejected:=true;
  end;
  reset role;
  if not rejected then raise exception 'G ordinary authenticated WIP UPDATE unexpectedly allowed'; end if;
  for x in select * from(values
    ('source_qty','update erp.wip_stage_events set qty_pcs=11 where id=$1'),
    ('source_and_inverse_qty','update erp.wip_stage_events set qty_pcs=11 where id in($1,$2)'),
    ('source_direction','update erp.wip_stage_events set stage_from=''LAUNDRY'',stage_to=''SEWING'' where id=$1'),
    ('source_group','update erp.wip_stage_events set cutting_group_id=null where id=$1'),
    ('source_contractor','update erp.wip_stage_events set contractor_id=null where id=$1'),
    ('source_time','update erp.wip_stage_events set physical_at=physical_at-interval ''1 day'' where id=$1'),
    ('inverse_qty','update erp.wip_stage_events set qty_pcs=11 where id=$2'),
    ('inverse_direction','update erp.wip_stage_events set stage_from=''SEWING'',stage_to=''LAUNDRY'' where id=$2'),
    ('inverse_group','update erp.wip_stage_events set cutting_group_id=null where id=$2'),
    ('inverse_time','update erp.wip_stage_events set physical_at=''2026-08-31T00:00Z'' where id=$2'),
    ('missing_source','delete from erp.wip_stage_events where id=$1'),
    ('orphan_inverse','update erp.wip_stage_events set source_id=gen_random_uuid() where id=$2')
  ) v(name,statement) loop
    begin
      execute x.statement using src,inv;
      r:=erp.get_owner_financial_snapshot_v2('2026-09-01',current_date,current_date);
      if r#>>'{data_confidence,status}'<>'BLOCKED' or not exists(
        select 1 from erp.run_v268_financial_report_checks()
        where check_name='V2620G_LAUNDRY_WIP_CUSTODY_MISMATCH' and issue_count>0
      ) then raise exception 'G undetected privileged WIP fault: %',x.name; end if;
      evidence:=jsonb_build_object('case',x.name,'status','BLOCKED',
        'outstanding',r#>'{quality,laundry_outstanding_pcs}',
        'failed_checks',r#>'{data_confidence,failed_checks}');
      raise exception using errcode='G0001',message='Rollback isolated corruption after observation';
    exception when sqlstate 'G0001' then null;
    end;
    faults:=faults||jsonb_build_array(evidence);
    if (erp.get_owner_financial_snapshot_v2('2026-09-01',current_date,current_date)#>>'{data_confidence,status}')<>'READY'
    then raise exception 'G fault rollback did not restore READY'; end if;
  end loop;
  return jsonb_build_object('status','PASS','normal_update_denied',true,'own_po_outstanding',0,
    'baseline_owner_outstanding',baseline#>'{quality,laundry_outstanding_pcs}',
    'fixture_note','Separate first-accrual fixture owns ten physically dispatched pcs',
    'faults',faults,'restored','READY');
end $$;
