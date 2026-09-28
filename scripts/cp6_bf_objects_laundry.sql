alter table erp.bd_laundry_charge_lines_v1 add column bf_sku_version_id uuid references erp.bf_sku_versions_v1(id);

create table erp.bf_laundry_delivery_sources_v1(
 delivery_line_id uuid primary key references erp.bd_laundry_priced_lines_v1(delivery_line_id),
 details_pending boolean not null,
 created_at timestamptz not null default statement_timestamp()
);

-- Actual cost can come from invoices while the original quote stays unknown.
-- All pieces must be returned and every source billed; reversing a bill reopens
-- the cost. Later bills cannot clear a blocker at an earlier closing date.
CREATE OR REPLACE FUNCTION erp.bf_delivery_invoiced_v1(p_line uuid,p_through date DEFAULT NULL)
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce((select sum(r.qty_good_received+r.qty_bs_laundry)>=d.qty_sent_pcs
   and bool_and(exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 i on i.id=x.invoice_id
     where x.receipt_line_id=r.id and x.completes_source and i.status='POSTED'
       and(p_through is null or i.invoice_date<=p_through)))
   from erp.laundry_delivery_lines d join erp.laundry_receipt_lines r on r.delivery_line_id=d.id
   join erp.laundry_receipts h on h.id=r.receipt_id and h.status='POSTED'
   where d.id=p_line group by d.qty_sent_pcs),false)
$function$;

-- Vendor tariffs are authoritative. SKU membership is never a monetary override.
-- Keep this compatibility helper for existing callers; historical charge snapshots
-- are untouched and new charges carry the vendor rate version only.
CREATE OR REPLACE FUNCTION erp.bf_laundry_rate_v1(p_kind text,p_ref uuid,p_vendor uuid,p_group uuid,p_size uuid,p_at timestamptz)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare sku uuid;vid uuid;r jsonb;fallback record;reason text;amount numeric;
begin
 if p_kind='COMPONENT' then
   select * into fallback from erp.bd_component_rate_at_v1(p_ref,p_at);
   select x.reason into reason from erp.bd_laundry_component_rates_v1 x where id=fallback.version_id;
   return jsonb_build_object('rate',fallback.rate_per_pcs::text,'rate_status',fallback.rate_status,'reason',reason,'version_id',fallback.version_id,'sku_version_id',vid);
 elsif p_kind='PACKAGE' then
   select * into fallback from erp.bd_package_rate_at_v1(p_ref,p_at);
   return jsonb_build_object('rate',fallback.rate_per_pcs::text,'rate_status','KNOWN','version_id',fallback.version_id,'sku_version_id',vid);
 elsif p_kind='PROCESS' then
   amount:=erp.bd_process_rate_at_v1(p_vendor,p_ref,p_at);
   select id into sku from erp.laundry_vendor_rate_versions where vendor_id=p_vendor and wash_process_id=p_ref
     and effective_from<=p_at and(effective_to is null or effective_to>p_at);
   return jsonb_build_object('rate',amount::text,'rate_status','KNOWN','version_id',sku,'sku_version_id',vid);
 end if;
 raise exception 'BF_RATE_KIND';
end;$function$;

-- Combine only charges with identical tariff provenance. Two SKUs never acquire each other's price or receivers.
CREATE OR REPLACE FUNCTION erp.bf_merge_charges_v1(p_charges jsonb)
 RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path TO ''
AS $function$
 with charges as(select x, x-'amount'-'covered_qty'-'shares' metadata,n from jsonb_array_elements(p_charges) with ordinality j(x,n)),
 totals as(select metadata,min(n) n,sum((x->>'covered_qty')::bigint) qty,
   case when bool_and(x->>'amount' is not null) then sum((x->>'amount')::numeric)::text end amount from charges group by metadata)
 select coalesce(jsonb_agg(t.metadata||jsonb_build_object('covered_qty',t.qty,'amount',t.amount,
   'shares',(select jsonb_agg(s order by c.n) from charges c cross join lateral jsonb_array_elements(c.x->'shares') s where c.metadata=t.metadata)) order by t.n),'[]') from totals t
$function$;

CREATE OR REPLACE FUNCTION erp.bf_package_charges_v1(p_vendor uuid,p_package uuid,p_group uuid,p_at timestamptz,p_sizes uuid[],p_qtys integer[],p_included uuid[],p_name text)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare i integer;r jsonb;amount numeric;charges jsonb:='[]';
begin
 for i in 1..cardinality(p_sizes) loop
   r:=erp.bf_laundry_rate_v1('PACKAGE',p_package,p_vendor,p_group,p_sizes[i],p_at);
   amount:=round(p_qtys[i]*(r->>'rate')::numeric,2);
   charges:=charges||jsonb_build_object('kind','PACKAGE','ref_id',p_package,'version_id',r->'version_id','bf_sku_version_id',r->'sku_version_id',
     'label','Paket '||p_name,'covered_qty',p_qtys[i],'rate_status','KNOWN','unit_rate',r->>'rate','amount',amount::text,
     'shares',jsonb_build_array(jsonb_build_object('size_id',p_sizes[i],'amount',amount::text,'covered_qty',p_qtys[i])),
     'included_components',to_jsonb(p_included));
 end loop;
 return erp.bf_merge_charges_v1(charges);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bf_complete_shares_v1(p_charges jsonb,p_sizes uuid[])
 RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path TO ''
AS $function$
 select coalesce(jsonb_agg(j.x||jsonb_build_object('shares',(
   select jsonb_agg(coalesce((select s from jsonb_array_elements(j.x->'shares') s where s->>'size_id'=u.size_id::text),
     jsonb_build_object('size_id',u.size_id,'covered_qty',0,'amount','0.00')) order by u.n)
   from unnest(p_sizes) with ordinality u(size_id,n))) order by j.n),'[]')
 from jsonb_array_elements(p_charges) with ordinality j(x,n)
$function$;

CREATE OR REPLACE FUNCTION erp.bf_component_charge_v1(p_vendor uuid,p_line jsonb,p_at timestamptz,p_sizes uuid[],p_qtys integer[],p_total integer,
  p_kind text,p_seen uuid[],p_group uuid)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_id uuid:=erp.bd_uuid_v1(p_line,'component_id',true);v_cov integer:=erp.bd_qty_v1(p_line->'covered_qty','covered_qty');c record;r record;
  v_amount numeric;v_shares jsonb:='[]'::jsonb;i integer;v_weights integer[];v_x jsonb;v_size uuid;v_index integer;
  v_seen_sizes uuid[]:='{}';v_sum bigint:=0;v_qty integer;v_price_reason text;bf_rate jsonb;bf_charges jsonb:='[]';
begin
  if v_id=any(p_seen) then raise exception 'BD_COMPONENT_DUPLICATE: komponen yang sama dipilih dua kali untuk kiriman ini';end if;
  select * into c from erp.bd_laundry_components_v1 where id=v_id and vendor_id=p_vendor and is_active;
  if c.id is null then raise exception 'BD_COMPONENT_UNKNOWN: komponen aktif vendor ini wajib dipilih';end if;
  if v_cov>p_total then raise exception 'BD_COVERAGE_EXCEEDS_DELIVERY: cakupan % PCS melebihi kiriman % PCS',v_cov,p_total;end if;
  if cardinality(p_sizes)<>cardinality(p_qtys) or cardinality(p_sizes)=0
     or (select count(distinct x) from unnest(p_sizes) x)<>cardinality(p_sizes) then
    raise exception 'BD_COVERAGE_INVALID: ukuran kiriman harus unik dan lengkap';end if;
  v_weights:=array_fill(0,array[cardinality(p_sizes)]);
  if p_line ? 'coverage' then
    if jsonb_typeof(p_line->'coverage') is distinct from 'array' or jsonb_array_length(p_line->'coverage') not between 1 and cardinality(p_sizes) then
      raise exception 'BD_COVERAGE_INVALID: coverage wajib daftar ukuran penerima jasa';end if;
    for v_x in select value from jsonb_array_elements(p_line->'coverage') loop
      perform erp._cp3_assert_closed_json_object(v_x,array['size_id','qty'],array['size_id','qty'],'component coverage');
      v_size:=erp.bd_uuid_v1(v_x,'size_id',true);v_qty:=erp.bd_qty_v1(v_x->'qty','coverage qty');
      v_index:=array_position(p_sizes,v_size);
      if v_index is null or v_size=any(v_seen_sizes) or v_qty>p_qtys[v_index] then
        raise exception 'BD_COVERAGE_INVALID: ukuran asing/ganda atau qty jasa melebihi ukuran kiriman';end if;
      v_weights[v_index]:=v_qty;v_sum:=v_sum+v_qty;v_seen_sizes:=v_seen_sizes||v_size;
    end loop;
    if v_sum<>v_cov then raise exception 'BD_COVERAGE_MISMATCH: jumlah coverage harus sama dengan covered_qty';end if;
  elsif v_cov=p_total then
    v_weights:=p_qtys;
  elsif cardinality(p_sizes)=1 then
    -- A single source size is unambiguous, including legacy single-size callers.
    v_weights[1]:=v_cov;
  else
    raise exception 'BD_COVERAGE_REQUIRED: jasa parsial pada beberapa ukuran wajib menyebut ukuran dan qty penerimanya';
  end if;
  if p_kind='EXTRA' then perform erp.bc_text_v1(p_line,'reason',true,1000);end if;
  for i in 1..cardinality(p_sizes) loop
    if v_weights[i]=0 then continue;end if;
    bf_rate:=erp.bf_laundry_rate_v1('COMPONENT',v_id,p_vendor,p_group,p_sizes[i],p_at);
    v_amount:=case when bf_rate->>'rate_status'<>'UNKNOWN' then round(v_weights[i]*(bf_rate->>'rate')::numeric,2) end;
    bf_charges:=bf_charges||jsonb_build_object('kind',p_kind,'ref_id',v_id,'version_id',bf_rate->'version_id',
      'bf_sku_version_id',bf_rate->'sku_version_id','label',c.component_name,'covered_qty',v_weights[i],
      'rate_status',bf_rate->>'rate_status','unit_rate',bf_rate->>'rate','amount',v_amount::text,
      'shares',jsonb_build_array(jsonb_build_object('size_id',p_sizes[i],'covered_qty',v_weights[i],'amount',v_amount::text)),
      'price_reason',bf_rate->>'reason','reason',nullif(btrim(coalesce(p_line->>'reason','')),''));
  end loop;
  return erp.bf_complete_shares_v1(erp.bf_merge_charges_v1(bf_charges),p_sizes);
end;$function$;
