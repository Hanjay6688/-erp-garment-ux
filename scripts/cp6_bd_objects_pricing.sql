-- ================================================================ BD priced laundry deliveries (LAU-05b)
-- A delivery of a BD-priced vendor (package, components, lump sum, minimum charge, or a scoped rate under LAU-DEC05) keeps its
-- exact estimated amount per batch size line, built from charge lines. Physical quantity is the delivery's own quantity: a
-- component or package is a charge, never a second physical line (LAU-T03). A receipt takes the exact share of each size's
-- estimate; the last receipt of a size takes the residual, so the amounts of every receipt add up to the estimate to the cent
-- (LAU-T20). The uncosted remainder of accrual and HPP is the estimate less these shares. An UNKNOWN component price keeps the
-- known subtotal and marks the delivery incomplete (LAU-T12): accrual and HPP carry the known part only, close stays blocked,
-- and the owner sets the price later on the delivery (SET_CHARGE_PRICE).

create table erp.bd_laundry_priced_lines_v1(
  delivery_line_id uuid primary key references erp.laundry_delivery_lines(id),
  delivery_id uuid not null references erp.laundry_deliveries(id),
  vendor_id uuid not null,
  pricing_mode text not null check(pricing_mode in('RATE','SCOPED','PACKAGE','COMPONENTS','BATCH')),
  pricing_unit text not null check(pricing_unit in('PCS','BATCH')),
  qty_sent integer not null check(qty_sent>0),
  total_known numeric(18,2) not null check(total_known>=0),
  total_complete boolean not null,
  policy_versions jsonb not null,
  request_id uuid not null,
  created_at timestamptz not null default statement_timestamp()
);
comment on table erp.bd_laundry_priced_lines_v1 is 'BD: exact estimate of a BD-priced laundry delivery line (LAU-05b). The delivery line keeps estimated_rate_snapshot = round(total/qty, 2) when complete and NULL while a component price is unknown.';

create table erp.bd_laundry_charge_lines_v1(
  id uuid primary key default gen_random_uuid(),
  delivery_line_id uuid not null references erp.bd_laundry_priced_lines_v1(delivery_line_id),
  line_no integer not null,
  kind text not null check(kind in('RATE','SCOPED_RATE','PACKAGE','COMPONENT','EXTRA','BATCH','MINIMUM_TOPUP')),
  ref_id uuid,
  version_id uuid,
  label text not null,
  covered_qty integer not null check(covered_qty>0),
  rate_status text not null check(rate_status in('KNOWN','UNKNOWN')),
  unit_rate numeric(18,2) check(unit_rate>=0),
  amount numeric(18,2) check(amount>=0),
  included_components jsonb,
  price_set_by uuid,
  price_set_at timestamptz,
  price_set_request uuid,
  price_set_reason text,
  unique(delivery_line_id,line_no),
  check((rate_status='KNOWN')=(amount is not null))
);
create table erp.bd_laundry_charge_shares_v1(
  charge_line_id uuid not null references erp.bd_laundry_charge_lines_v1(id),
  delivery_batch_size_line_id uuid not null references erp.laundry_delivery_batch_size_lines(id),
  amount numeric(18,2) check(amount>=0),
  primary key(charge_line_id,delivery_batch_size_line_id)
);
create table erp.bd_laundry_size_estimates_v1(
  delivery_batch_size_line_id uuid primary key references erp.laundry_delivery_batch_size_lines(id),
  delivery_line_id uuid not null references erp.bd_laundry_priced_lines_v1(delivery_line_id),
  qty_sent integer not null check(qty_sent>0),
  known_amount numeric(18,2) not null check(known_amount>=0),
  complete boolean not null
);
create table erp.bd_laundry_receipt_allocations_v1(
  receipt_batch_size_line_id uuid primary key references erp.laundry_receipt_batch_size_lines(id),
  receipt_line_id uuid not null references erp.laundry_receipt_lines(id),
  delivery_batch_size_line_id uuid not null references erp.laundry_delivery_batch_size_lines(id),
  qty integer not null check(qty>0),
  amount numeric(18,2) not null check(amount>=0),
  complete boolean not null
);

-- Exact split of an amount over weights (largest remainder on cents, ties by order): the parts always add up to the amount.
CREATE OR REPLACE FUNCTION erp.bd_split_amount_v1(p_amount numeric,p_weights integer[])
 RETURNS numeric[] LANGUAGE plpgsql IMMUTABLE SET search_path TO ''
AS $function$
declare v_total bigint:=0;v_cents bigint:=round(p_amount*100);v_parts numeric[]:='{}';v_base bigint[]:='{}';v_frac numeric[]:='{}';
  v_left bigint;i integer;j integer;v_best integer;
begin
  foreach i in array p_weights loop v_total:=v_total+i;end loop;
  if v_total<=0 then raise exception 'BD_INTERNAL: bobot pembagian kosong';end if;
  for i in 1..array_length(p_weights,1) loop
    v_base:=v_base||floor(v_cents::numeric*p_weights[i]/v_total)::bigint;
    v_frac:=v_frac||(v_cents::numeric*p_weights[i]/v_total-floor(v_cents::numeric*p_weights[i]/v_total));
  end loop;
  v_left:=v_cents;
  for i in 1..array_length(v_base,1) loop v_left:=v_left-v_base[i];end loop;
  while v_left>0 loop
    v_best:=1;
    for j in 2..array_length(v_frac,1) loop if v_frac[j]>v_frac[v_best] then v_best:=j;end if;end loop;
    v_base[v_best]:=v_base[v_best]+1;v_frac[v_best]:=-1;v_left:=v_left-1;
  end loop;
  for i in 1..array_length(v_base,1) loop v_parts:=v_parts||(v_base[i]::numeric/100);end loop;
  return v_parts;
end;$function$;

-- Does this vendor/process need BD pricing (so a direct POST_DELIVERY at the base rate would misprice it)?
CREATE OR REPLACE FUNCTION erp.bd_vendor_needs_pricing_v1(p_vendor uuid,p_process uuid)
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select exists(select 1 from erp.bd_laundry_vendor_terms_v1 t where t.vendor_id=p_vendor and (t.pricing_mode<>'RATE' or t.pricing_unit<>'PCS' or t.minimum_charge is not null))
      or exists(select 1 from erp.bd_laundry_scoped_rates_v1 r where r.vendor_id=p_vendor and r.wash_process_id=p_process)
$function$;

-- Charge lines and per-size shares of one delivery; nothing is written. p_delivery is the POST_DELIVERY payload.
CREATE OR REPLACE FUNCTION erp.bd_compute_pricing_v1(p_delivery jsonb,p_pricing jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_vendor uuid:=erp.bd_uuid_v1(p_delivery,'vendor_id',true);v_process uuid:=erp.bd_uuid_v1(p_delivery,'wash_process_id',true);
  v_batch uuid:=erp.bd_uuid_v1(p_delivery,'distribution_batch_id',true);v_at timestamptz:=erp.bd_at_v1(p_delivery->>'physical_at','physical_at');
  v_color text:=nullif(btrim(coalesce(p_delivery->>'target_dyeing_color','')),'');
  t erp.bd_laundry_vendor_terms_v1%rowtype;v_mode text;v_unit text;v_model uuid;v_sizes jsonb:='[]'::jsonb;v_sizeids uuid[]:='{}';v_qtys integer[]:='{}';
  v_total_qty integer:=0;v_charges jsonb:='[]'::jsonb;v_known numeric:=0;v_complete boolean:=true;v_units jsonb;v_dec05 jsonb;v_dec03 jsonb;
  v_versions jsonb:='{}'::jsonb;v_line jsonb;v_x jsonb;v_split numeric[];v_shares jsonb;i integer;v_rate numeric;v_scoped record;v_base numeric;
  v_pkg record;v_comp record;v_included uuid[];v_seen uuid[]:='{}';v_cov integer;v_amount numeric;v_lump numeric;v_min numeric;v_topup numeric;
  v_status text;v_label text;v_kind text;
begin
  select * into t from erp.bd_laundry_vendor_terms_v1 where vendor_id=v_vendor;
  v_mode:=coalesce(t.pricing_mode,'RATE');v_unit:=coalesce(t.pricing_unit,'PCS');
  select po.model_id into v_model from erp.cutting_distribution_batches b join erp.cutting_pickups p on p.id=b.pickup_id
    join erp.cutting_groups g on g.id=p.cutting_group_id join erp.production_orders po on po.id=g.po_id where b.id=v_batch;
  if jsonb_typeof(p_delivery->'lines') is distinct from 'array' or jsonb_array_length(p_delivery->'lines')=0 then
    raise exception 'BD_LINES_REQUIRED: baris ukuran kiriman wajib diisi';end if;
  for v_x in select value from jsonb_array_elements(p_delivery->'lines') loop
    v_sizeids:=v_sizeids||erp.bd_uuid_v1(v_x,'size_id',true);v_qtys:=v_qtys||erp.bd_qty_v1(v_x->'qty_sent_pcs','qty_sent_pcs');
  end loop;
  foreach i in array v_qtys loop v_total_qty:=v_total_qty+i;end loop;
  v_units:=coalesce(erp.bd_policy_v1('LAU_DEC01')->'units','[]'::jsonb);
  if jsonb_typeof(p_pricing) is distinct from 'object' then raise exception 'BD_PRICING_INVALID: pricing wajib objek';end if;

  if v_unit='BATCH' then
    -- LAU-T20: a lump sum agreed for this batch, spread over its sizes by quantity; the whole amount, not per receipt.
    if not v_units @> '["BATCH"]' then perform erp.bd_require_policy_v1('LAU_DEC01','satuan borongan per batch');
      raise exception 'BD_UNIT_NOT_ALLOWED: LAU-DEC01 belum mengizinkan satuan BATCH';end if;
    perform erp._cp3_assert_closed_json_object(p_pricing,array['lump_sum'],array['lump_sum'],'batch pricing');
    v_lump:=erp.bd_amount_v1(p_pricing->'lump_sum','lump_sum',true);
    v_versions:=v_versions||jsonb_build_object('LAU_DEC01',erp.bd_policy_version_v1('LAU_DEC01'));
    v_split:=erp.bd_split_amount_v1(v_lump,v_qtys);v_shares:='[]'::jsonb;
    for i in 1..array_length(v_sizeids,1) loop v_shares:=v_shares||jsonb_build_object('size_id',v_sizeids[i],'amount',v_split[i]::text);end loop;
    v_charges:=v_charges||jsonb_build_object('kind','BATCH','ref_id',null,'version_id',null,'label','Borongan batch','covered_qty',v_total_qty,
      'rate_status','KNOWN','unit_rate',null,'amount',v_lump::text,'shares',v_shares);
    v_known:=v_lump;v_mode:='BATCH';
  elsif v_mode='RATE' then
    perform erp._cp3_assert_closed_json_object(p_pricing,array[]::text[],array[]::text[],'rate pricing');
    v_dec05:=erp.bd_policy_v1('LAU_DEC05');
    for i in 1..array_length(v_sizeids,1) loop
      select * into v_scoped from erp.bd_scoped_rate_at_v1(v_vendor,v_process,v_model,v_sizeids[i],v_color,v_at);
      if v_scoped.rate_per_pcs is not null then
        v_rate:=v_scoped.rate_per_pcs;v_kind:='SCOPED_RATE';v_label:='Tarif khusus '||v_scoped.scope;v_mode:='SCOPED';
        v_versions:=v_versions||jsonb_build_object('LAU_DEC05',erp.bd_policy_version_v1('LAU_DEC05'));
      else
        if v_dec05 is not null and v_dec05->>'fallback'='REFUSE' then
          raise exception 'BD_SCOPED_RATE_MISSING: tidak ada tarif khusus untuk ukuran ini dan LAU-DEC05 menolak tarif dasar';end if;
        v_rate:=erp.bd_process_rate_at_v1(v_vendor,v_process,v_at);v_kind:='RATE';v_label:='Tarif dasar vendor/proses';
      end if;
      v_amount:=round(v_qtys[i]*v_rate,2);
      v_charges:=v_charges||jsonb_build_object('kind',v_kind,'ref_id',v_scoped.rate_id,'version_id',v_scoped.rate_id,'label',v_label,'covered_qty',v_qtys[i],
        'rate_status','KNOWN','unit_rate',v_rate::text,'amount',v_amount::text,
        'shares',jsonb_build_array(jsonb_build_object('size_id',v_sizeids[i],'amount',v_amount::text)));
      v_known:=v_known+v_amount;
    end loop;
  elsif v_mode='PACKAGE' then
    -- LAU-T02/T06: the package price covers its included components; the same component again as an extra is refused.
    perform erp._cp3_assert_closed_json_object(p_pricing,array['package_id'],array['package_id','extras'],'package pricing');
    select p.* into v_pkg from erp.bd_laundry_packages_v1 p where p.id=erp.bd_uuid_v1(p_pricing,'package_id',true) and p.vendor_id=v_vendor and p.is_active;
    if v_pkg.id is null then raise exception 'BD_PACKAGE_UNKNOWN: paket aktif vendor ini wajib dipilih';end if;
    select * into v_scoped from erp.bd_package_rate_at_v1(v_pkg.id,v_at);
    select array_agg(component_id order by component_id) into v_included from erp.bd_laundry_package_components_v1 where package_id=v_pkg.id;
    v_split:='{}';v_shares:='[]'::jsonb;
    for i in 1..array_length(v_sizeids,1) loop v_shares:=v_shares||jsonb_build_object('size_id',v_sizeids[i],'amount',round(v_qtys[i]*v_scoped.rate_per_pcs,2)::text);end loop;
    v_amount:=round(v_total_qty*v_scoped.rate_per_pcs,2);
    v_charges:=v_charges||jsonb_build_object('kind','PACKAGE','ref_id',v_pkg.id,'version_id',v_scoped.version_id,'label','Paket '||v_pkg.package_name,
      'covered_qty',v_total_qty,'rate_status','KNOWN','unit_rate',v_scoped.rate_per_pcs::text,'amount',v_amount::text,'shares',v_shares,
      'included_components',to_jsonb(v_included));
    v_known:=v_amount;
    if p_pricing ? 'extras' and jsonb_typeof(p_pricing->'extras')<>'null' then
      if jsonb_typeof(p_pricing->'extras')<>'array' or jsonb_array_length(p_pricing->'extras')>30 then raise exception 'BD_PRICING_INVALID: extras wajib daftar';end if;
      for v_x in select value from jsonb_array_elements(p_pricing->'extras') loop
        perform erp._cp3_assert_closed_json_object(v_x,array['component_id','covered_qty','reason'],array['component_id','covered_qty','reason'],'extra component');
        if erp.bd_uuid_v1(v_x,'component_id',true)=any(v_included) then
          raise exception 'BD_COMPONENT_ALREADY_INCLUDED: komponen ini sudah termasuk dalam paket; biaya untuk cakupan yang sama tidak ditagih dua kali';end if;
        v_dec03:=erp.bd_require_policy_v1('LAU_DEC03','komponen tambahan di luar paket');
        if v_dec03->>'extra'<>'ALLOWED' then raise exception 'BD_EXTRA_REFUSED: LAU-DEC03 tidak mengizinkan komponen tambahan';end if;
        v_versions:=v_versions||jsonb_build_object('LAU_DEC03',erp.bd_policy_version_v1('LAU_DEC03'));
        v_charges:=v_charges||erp.bd_component_charge_v1(v_vendor,v_x,v_at,v_sizeids,v_qtys,v_total_qty,'EXTRA',v_seen);
        v_seen:=v_seen||erp.bd_uuid_v1(v_x,'component_id',true);
      end loop;
    end if;
  elsif v_mode='COMPONENTS' then
    -- LAU-T03/T04/T05: the delivery's components, each with the pieces it really covers (partial coverage is not the whole
    -- delivery); the physical quantity stays the delivery quantity.
    perform erp._cp3_assert_closed_json_object(p_pricing,array['components'],array['components'],'component pricing');
    if jsonb_typeof(p_pricing->'components') is distinct from 'array' or jsonb_array_length(p_pricing->'components') not between 1 and 30 then
      raise exception 'BD_PRICING_INVALID: pilih 1-30 komponen';end if;
    for v_x in select value from jsonb_array_elements(p_pricing->'components') loop
      perform erp._cp3_assert_closed_json_object(v_x,array['component_id','covered_qty'],array['component_id','covered_qty'],'component');
      v_charges:=v_charges||erp.bd_component_charge_v1(v_vendor,v_x,v_at,v_sizeids,v_qtys,v_total_qty,'COMPONENT',v_seen);
      v_seen:=v_seen||erp.bd_uuid_v1(v_x,'component_id',true);
    end loop;
  end if;

  -- Known subtotal and completeness from the component charges.
  if v_mode in('PACKAGE','COMPONENTS') then
    v_known:=0;
    for v_line in select value from jsonb_array_elements(v_charges) loop
      if v_line->>'rate_status'='KNOWN' then v_known:=v_known+(v_line->>'amount')::numeric;else v_complete:=false;end if;
    end loop;
  end if;
  if t.minimum_charge is not null then
    if not v_units @> '["MINIMUM"]' then perform erp.bd_require_policy_v1('LAU_DEC01','minimum charge');
      raise exception 'BD_UNIT_NOT_ALLOWED: LAU-DEC01 tidak lagi mengizinkan minimum charge vendor ini';end if;
    if not v_complete then raise exception 'BD_MINIMUM_NEEDS_KNOWN_PRICE: minimum charge memerlukan semua harga komponen diketahui';end if;
    v_versions:=v_versions||jsonb_build_object('LAU_DEC01',erp.bd_policy_version_v1('LAU_DEC01'));
    if v_known<t.minimum_charge then
      v_topup:=t.minimum_charge-v_known;v_split:=erp.bd_split_amount_v1(v_topup,v_qtys);v_shares:='[]'::jsonb;
      for i in 1..array_length(v_sizeids,1) loop v_shares:=v_shares||jsonb_build_object('size_id',v_sizeids[i],'amount',v_split[i]::text);end loop;
      v_charges:=v_charges||jsonb_build_object('kind','MINIMUM_TOPUP','ref_id',null,'version_id',null,'label','Minimum charge vendor','covered_qty',v_total_qty,
        'rate_status','KNOWN','unit_rate',null,'amount',v_topup::text,'shares',v_shares);
      v_known:=t.minimum_charge;
    end if;
  end if;
  for i in 1..array_length(v_sizeids,1) loop v_sizes:=v_sizes||jsonb_build_object('size_id',v_sizeids[i],'qty',v_qtys[i]);end loop;
  return jsonb_build_object('mode',v_mode,'unit',v_unit,'vendor_id',v_vendor,'qty',v_total_qty,'sizes',v_sizes,'charges',v_charges,
    'total_known',round(v_known,2)::text,'complete',v_complete,
    'avg_rate',case when v_complete then round(v_known/v_total_qty,2)::text end,'policy_versions',v_versions);
end;$function$;

-- One component charge (COMPONENT or EXTRA): covered pieces, its price version (KNOWN or UNKNOWN), per-size shares.
CREATE OR REPLACE FUNCTION erp.bd_component_charge_v1(p_vendor uuid,p_line jsonb,p_at timestamptz,p_sizes uuid[],p_qtys integer[],p_total integer,
  p_kind text,p_seen uuid[])
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_id uuid:=erp.bd_uuid_v1(p_line,'component_id',true);v_cov integer:=erp.bd_qty_v1(p_line->'covered_qty','covered_qty');c record;r record;
  v_amount numeric;v_split numeric[];v_shares jsonb:='[]'::jsonb;i integer;
begin
  if v_id=any(p_seen) then raise exception 'BD_COMPONENT_DUPLICATE: komponen yang sama dipilih dua kali untuk kiriman ini';end if;
  select * into c from erp.bd_laundry_components_v1 where id=v_id and vendor_id=p_vendor and is_active;
  if c.id is null then raise exception 'BD_COMPONENT_UNKNOWN: komponen aktif vendor ini wajib dipilih';end if;
  if v_cov>p_total then raise exception 'BD_COVERAGE_EXCEEDS_DELIVERY: cakupan % PCS melebihi kiriman % PCS',v_cov,p_total;end if;
  select * into r from erp.bd_component_rate_at_v1(v_id,p_at);
  if r.rate_status='KNOWN' then
    v_amount:=round(v_cov*r.rate_per_pcs,2);v_split:=erp.bd_split_amount_v1(v_amount,p_qtys);
    for i in 1..array_length(p_sizes,1) loop v_shares:=v_shares||jsonb_build_object('size_id',p_sizes[i],'amount',v_split[i]::text);end loop;
  else
    for i in 1..array_length(p_sizes,1) loop v_shares:=v_shares||jsonb_build_object('size_id',p_sizes[i],'amount',null);end loop;
  end if;
  return jsonb_build_object('kind',p_kind,'ref_id',v_id,'version_id',r.version_id,'label',c.component_name,'covered_qty',v_cov,
    'rate_status',r.rate_status,'unit_rate',r.rate_per_pcs::text,'amount',v_amount::text,'shares',v_shares,
    'reason',nullif(btrim(coalesce(p_line->>'reason','')),''));
end;$function$;

-- Called by the replaced POST_DELIVERY right after the batch size lines exist (only inside the BD facade's context).
CREATE OR REPLACE FUNCTION erp.bd_attach_delivery_pricing_v1(p_delivery_line uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare c erp.bd_execution_context_v1%rowtype:=erp.bd_context_v1();p jsonb;l erp.laundry_delivery_lines%rowtype;v_ch jsonb;v_sh jsonb;
  v_no integer:=0;v_charge uuid;v_size uuid;
begin
  if c.backend_pid is null or c.action<>'POST_PRICED_DELIVERY' or c.pricing is null then return;end if;
  p:=c.pricing;
  select * into l from erp.laundry_delivery_lines where id=p_delivery_line;
  if l.qty_sent_pcs<>(p->>'qty')::integer then raise exception 'BD_INTERNAL: qty kiriman berbeda dari harga yang dihitung';end if;
  insert into erp.bd_laundry_priced_lines_v1(delivery_line_id,delivery_id,vendor_id,pricing_mode,pricing_unit,qty_sent,total_known,total_complete,
    policy_versions,request_id)
  values(l.id,l.delivery_id,(p->>'vendor_id')::uuid,p->>'mode',p->>'unit',l.qty_sent_pcs,(p->>'total_known')::numeric,(p->>'complete')::boolean,
    p->'policy_versions',c.request_id);
  for v_ch in select value from jsonb_array_elements(p->'charges') loop
    v_no:=v_no+1;
    insert into erp.bd_laundry_charge_lines_v1(delivery_line_id,line_no,kind,ref_id,version_id,label,covered_qty,rate_status,unit_rate,amount,included_components)
    values(l.id,v_no,v_ch->>'kind',(v_ch->>'ref_id')::uuid,(v_ch->>'version_id')::uuid,v_ch->>'label',(v_ch->>'covered_qty')::integer,v_ch->>'rate_status',
      (v_ch->>'unit_rate')::numeric,(v_ch->>'amount')::numeric,v_ch->'included_components')
    returning id into v_charge;
    for v_sh in select value from jsonb_array_elements(v_ch->'shares') loop
      select s.id into v_size from erp.laundry_delivery_batch_size_lines s where s.delivery_line_id=l.id and s.size_id=(v_sh->>'size_id')::uuid;
      if v_size is null then raise exception 'BD_INTERNAL: ukuran harga tidak ada pada kiriman';end if;
      insert into erp.bd_laundry_charge_shares_v1(charge_line_id,delivery_batch_size_line_id,amount) values(v_charge,v_size,(v_sh->>'amount')::numeric);
    end loop;
  end loop;
  perform erp.bd_refresh_size_estimates_v1(l.id);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bd_refresh_size_estimates_v1(p_delivery_line uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  insert into erp.bd_laundry_size_estimates_v1(delivery_batch_size_line_id,delivery_line_id,qty_sent,known_amount,complete)
  select s.id,s.delivery_line_id,s.qty_sent_pcs,coalesce(sum(sh.amount),0),bool_and(sh.amount is not null)
  from erp.laundry_delivery_batch_size_lines s join erp.bd_laundry_charge_shares_v1 sh on sh.delivery_batch_size_line_id=s.id
  where s.delivery_line_id=p_delivery_line group by s.id,s.delivery_line_id,s.qty_sent_pcs
  on conflict(delivery_batch_size_line_id) do update set known_amount=excluded.known_amount,complete=excluded.complete;
  update erp.bd_laundry_priced_lines_v1 p set total_known=x.known,total_complete=x.complete
  from (select coalesce(sum(known_amount),0) known,bool_and(complete) complete from erp.bd_laundry_size_estimates_v1 where delivery_line_id=p_delivery_line) x
  where p.delivery_line_id=p_delivery_line;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bd_line_complete_v1(p_delivery_line uuid)
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select coalesce((select total_complete from erp.bd_laundry_priced_lines_v1 where delivery_line_id=p_delivery_line),true) $function$;

-- The estimate of a delivery line not yet taken by posted receipts: BD lines by their exact shares; baseline lines unchanged.
CREATE OR REPLACE FUNCTION erp.bd_uncosted_estimate_v1(p_delivery_line uuid,p_qty_sent integer,p_costed numeric,p_rate numeric)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select case when exists(select 1 from erp.bd_laundry_priced_lines_v1 where delivery_line_id=p_delivery_line) then
    coalesce((select sum(e.known_amount) from erp.bd_laundry_size_estimates_v1 e where e.delivery_line_id=p_delivery_line),0)
    -coalesce((select sum(a.amount) from erp.bd_laundry_receipt_allocations_v1 a
      join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id join erp.laundry_receipts r on r.id=rl.receipt_id and r.status='POSTED'
      join erp.laundry_delivery_batch_size_lines s on s.id=a.delivery_batch_size_line_id
      where s.delivery_line_id=p_delivery_line and rl.actual_cost_status in('ESTIMATED','FINAL')),0)
  else greatest(p_qty_sent-p_costed,0)*coalesce(p_rate,0) end
$function$;

-- Called by the replaced POST_RECEIPT after its batch size lines exist: each size takes its exact share of the estimate, the
-- last return of a size its residual; the receipt line's actual cost is the sum (known part while a price is unknown).
CREATE OR REPLACE FUNCTION erp.bd_allocate_receipt_v1(p_receipt_line uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare rx record;e erp.bd_laundry_size_estimates_v1%rowtype;v_prior_qty bigint;v_prior_amount numeric;v_amount numeric;v_qty integer;v_total numeric:=0;
  v_line uuid;v_complete boolean:=true;
begin
  select rl.delivery_line_id into v_line from erp.laundry_receipt_lines rl where rl.id=p_receipt_line;
  if not exists(select 1 from erp.bd_laundry_priced_lines_v1 where delivery_line_id=v_line) then return;end if;
  delete from erp.bd_laundry_receipt_allocations_v1 where receipt_line_id=p_receipt_line;
  for rx in select x.id,x.delivery_batch_size_line_id,x.qty_good_received+x.qty_bs_laundry qty from erp.laundry_receipt_batch_size_lines x
    where x.receipt_line_id=p_receipt_line order by x.delivery_batch_size_line_id loop
    select * into e from erp.bd_laundry_size_estimates_v1 where delivery_batch_size_line_id=rx.delivery_batch_size_line_id for update;
    if e.delivery_batch_size_line_id is null then raise exception 'BD_INTERNAL: estimasi ukuran tidak ada';end if;
    select coalesce(sum(a.qty),0),coalesce(sum(a.amount),0) into v_prior_qty,v_prior_amount from erp.bd_laundry_receipt_allocations_v1 a
      join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id join erp.laundry_receipts r on r.id=rl.receipt_id
      where a.delivery_batch_size_line_id=rx.delivery_batch_size_line_id and a.receipt_line_id<>p_receipt_line and r.status='POSTED';
    v_qty:=rx.qty;
    if v_prior_qty+v_qty=e.qty_sent then v_amount:=e.known_amount-v_prior_amount;
    else v_amount:=round(e.known_amount*v_qty/e.qty_sent,2);end if;
    if v_amount<0 then raise exception 'BD_INTERNAL: alokasi negatif';end if;
    insert into erp.bd_laundry_receipt_allocations_v1(receipt_batch_size_line_id,receipt_line_id,delivery_batch_size_line_id,qty,amount,complete)
    values(rx.id,p_receipt_line,rx.delivery_batch_size_line_id,v_qty,v_amount,e.complete);
    v_total:=v_total+v_amount;v_complete:=v_complete and e.complete;
  end loop;
  -- The rate snapshot of a BD receipt is the delivery's average rate once every price is known (the amount is the exact share).
  update erp.laundry_receipt_lines set actual_cost=v_total,actual_rate_snapshot=case when v_complete then
      (select round(p.total_known/p.qty_sent,2) from erp.bd_laundry_priced_lines_v1 p where p.delivery_line_id=v_line and p.total_complete) end
  where id=p_receipt_line;
end;$function$;

-- Owner/admin sets an UNKNOWN component price on one delivery (like the owner estimate of an unknown rate): the charge becomes
-- KNOWN, the size estimates, the posted receipts' shares and the delivery's rate snapshot follow, and accrual/HPP resync
-- through the rate-snapshot trigger. Refused once a receipt of the delivery is invoiced.
CREATE OR REPLACE FUNCTION erp.bd_set_charge_price_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare ch erp.bd_laundry_charge_lines_v1%rowtype;v_rate numeric;v_amount numeric;v_split numeric[];v_ids uuid[];v_qtys integer[];i integer;
  p erp.bd_laundry_priced_lines_v1%rowtype;v_reason text:=nullif(btrim(p_payload->>'reason'),'');r record;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['charge_line_id','rate_per_pcs','reason'],array['charge_line_id','rate_per_pcs','reason'],'charge price');
  if v_reason is null then raise exception 'BD_REASON_REQUIRED: alasan wajib diisi';end if;
  select * into ch from erp.bd_laundry_charge_lines_v1 where id=erp.bd_uuid_v1(p_payload,'charge_line_id',true) for update;
  if ch.id is null then raise exception 'BD_CHARGE_UNKNOWN: baris harga tidak dikenal';end if;
  if ch.rate_status<>'UNKNOWN' then raise exception 'BD_PRICE_ALREADY_KNOWN: harga baris ini sudah diketahui; snapshot tidak ditimpa';end if;
  select * into p from erp.bd_laundry_priced_lines_v1 where delivery_line_id=ch.delivery_line_id for update;
  -- Same order as a receipt (delivery, then size estimates): a receipt posting at the same time waits or is waited for.
  perform 1 from erp.laundry_deliveries where id=p.delivery_id for update;
  if exists(select 1 from erp.laundry_deliveries where id=p.delivery_id and status='REVERSED') then raise exception 'BD_DELIVERY_REVERSED: kiriman sudah dibatalkan';end if;
  if exists(select 1 from erp.laundry_receipt_lines rl join erp.laundry_receipts rh on rh.id=rl.receipt_id and rh.status='POSTED'
            where rl.delivery_line_id=ch.delivery_line_id and rl.actual_cost_status='FINAL') then
    raise exception 'BD_ALREADY_INVOICED: kiriman sudah ditagih vendor';end if;
  v_rate:=erp.bd_amount_v1(p_payload->'rate_per_pcs','rate_per_pcs',true);
  v_amount:=round(ch.covered_qty*v_rate,2);
  select array_agg(s.id order by s.id),array_agg(s.qty_sent_pcs order by s.id) into v_ids,v_qtys
  from erp.laundry_delivery_batch_size_lines s where s.delivery_line_id=ch.delivery_line_id;
  v_split:=erp.bd_split_amount_v1(v_amount,v_qtys);
  update erp.bd_laundry_charge_lines_v1 set rate_status='KNOWN',unit_rate=v_rate,amount=v_amount,price_set_by=erp.current_app_user_id(),
    price_set_at=statement_timestamp(),price_set_request=p_request,price_set_reason=v_reason where id=ch.id;
  for i in 1..array_length(v_ids,1) loop
    update erp.bd_laundry_charge_shares_v1 set amount=v_split[i] where charge_line_id=ch.id and delivery_batch_size_line_id=v_ids[i];
  end loop;
  perform erp.bd_refresh_size_estimates_v1(ch.delivery_line_id);
  -- Reallocate the posted receipts from scratch in physical order, so each takes its share and the last of a size the residual.
  delete from erp.bd_laundry_receipt_allocations_v1 a using erp.laundry_receipt_lines rl,erp.laundry_receipts h
  where rl.id=a.receipt_line_id and h.id=rl.receipt_id and h.status='POSTED' and rl.delivery_line_id=ch.delivery_line_id;
  for r in select rl.id from erp.laundry_receipt_lines rl join erp.laundry_receipts h on h.id=rl.receipt_id and h.status='POSTED'
    where rl.delivery_line_id=ch.delivery_line_id order by h.physical_at,rl.id loop
    perform erp.bd_allocate_receipt_v1(r.id);
  end loop;
  select * into p from erp.bd_laundry_priced_lines_v1 where delivery_line_id=ch.delivery_line_id;
  update erp.laundry_delivery_lines set estimated_rate_snapshot=case when p.total_complete then round(p.total_known/p.qty_sent,2) end,
    estimated_cost_status=case when p.total_complete then 'ESTIMATED' else 'PENDING' end where id=ch.delivery_line_id;
  -- The rate-snapshot trigger returns early when the snapshot stays NULL (another price still unknown); resync explicitly.
  perform erp.bd_resync_delivery_v1(p.delivery_id);
  return jsonb_build_object('charge_line_id',ch.id,'amount',v_amount::text,'total_known',p.total_known::text,'complete',p.total_complete);
end;$function$;

-- The same resynchronization as trg_sync_laundry_accrual_after_rate_change, for a BD change that may leave the snapshot as it was.
CREATE OR REPLACE FUNCTION erp.bd_resync_delivery_v1(p_delivery uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_po uuid;v_status text;v_date date;
begin
  select ld.po_id,ld.status,(ld.physical_at at time zone 'Asia/Jakarta')::date into v_po,v_status,v_date from erp.laundry_deliveries ld where ld.id=p_delivery;
  if v_status in('DRAFT','REVERSED') then return;end if;
  perform erp.sync_laundry_accrual(v_po,v_date);
  if exists(select 1 from erp.fg_lots where po_id=v_po) then
    perform erp.rebuild_po_hpp(v_po,'BD laundry price completed');
    perform erp.propagate_conversion_hpp_for_po(v_po);
    perform erp.sync_po_hpp_to_gl(v_po,v_date);
  end if;
end;$function$;
