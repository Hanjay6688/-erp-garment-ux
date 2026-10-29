-- A manual conversion selects product/size and location. Native selected-lot
-- conversions are the individual facts, all committed by one parent request.
create table cp7_sku_conversion.groups_v1(
 request_id uuid primary key,actor uuid not null,payload jsonb not null,
 created_at timestamptz not null default statement_timestamp()
);
create table cp7_sku_conversion.members_v1(
 conversion_id uuid primary key references erp.product_conversions(id),
 group_id uuid not null references cp7_sku_conversion.groups_v1(request_id),line_no int not null check(line_no>0),
 unique(group_id,line_no)
);
create table cp7_sku_conversion.execution_v1(
 backend_pid int not null,transaction_id bigint not null,group_id uuid not null references cp7_sku_conversion.groups_v1(request_id),
 mode text not null check(mode in('POST','REVERSE')),source_lot_id uuid,target_id uuid,location_id uuid,qty int,physical_at timestamptz,
 primary key(backend_pid,transaction_id)
);
alter table cp7_sku_conversion.groups_v1 enable row level security;
alter table cp7_sku_conversion.members_v1 enable row level security;
alter table cp7_sku_conversion.execution_v1 enable row level security;
create policy deny_groups on cp7_sku_conversion.groups_v1 for all using(false)with check(false);
create policy deny_members on cp7_sku_conversion.members_v1 for all using(false)with check(false);
create policy deny_execution on cp7_sku_conversion.execution_v1 for all using(false)with check(false);
create trigger groups_immutable before update or delete on cp7_sku_conversion.groups_v1
 for each row execute function cp7_sku_conversion.immutable_v1();
create trigger members_immutable before update or delete on cp7_sku_conversion.members_v1
 for each row execute function cp7_sku_conversion.immutable_v1();

create function cp7_sku_conversion.manual_allocation_v1(p_lot uuid,p_target uuid,p_location uuid,p_qty int,p_at timestamptz)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from cp7_sku_conversion.execution_v1 e where e.backend_pid=pg_backend_pid()and e.transaction_id=txid_current()
 and e.mode='POST'and e.source_lot_id=p_lot and e.target_id=p_target and e.location_id=p_location and e.qty=p_qty and e.physical_at=p_at)
$$;
create function cp7_sku_conversion.assert_group_reverse_v1(p_conversion uuid)returns void
language plpgsql stable security definer set search_path=''as $$
begin
 if exists(select 1 from cp7_sku_conversion.members_v1 m where m.conversion_id=p_conversion and not exists(
  select 1 from cp7_sku_conversion.execution_v1 e where e.backend_pid=pg_backend_pid()and e.transaction_id=txid_current()
   and e.group_id=m.group_id and e.mode='REVERSE'))then raise exception 'CP7_SKU_GROUP_REVERSE_REQUIRED: batalkan seluruh konversi dari riwayat Ganti Merek / SKU';end if;
end $$;

create function cp7_sku_conversion.stock_v1(p_product uuid,p_location uuid)returns jsonb
language sql stable security definer set search_path=''as $$
 with s as(select coalesce(sum(m.qty_signed),0)::bigint available,
 coalesce(sum(abs(m.qty_signed))filter(where m.movement_type='SALE_RESERVE'and not exists(
  select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id and rv.physical_at<=statement_timestamp())),0)::bigint reserved
 from erp.fg_stock_movements m where m.product_id=p_product and m.location_id=p_location and m.quality_grade='GRADE_A'
 and m.physical_at<=statement_timestamp())
 select jsonb_build_object('available',available,'reserved',reserved,'physical',available+reserved)from s
$$;
-- Timestamp-bearing facts must have the same canonical serialization for a
-- preview caller and the UTC posting coordinator. No field is excluded.
create function cp7_sku_conversion.revision_v1(p_source uuid,p_target uuid,p_location uuid)returns text
language sql stable security definer set search_path=''set timezone='UTC'as $$
 select md5(jsonb_build_object('source',p_source,'target',p_target,'location',p_location,
 'products',(select jsonb_agg(to_jsonb(p)order by p.id)from erp.products p where p.id in(p_source,p_target)),
 'location_row',(select to_jsonb(l)from erp.locations l where l.id=p_location),
 'movements',(select coalesce(jsonb_agg(to_jsonb(m)order by m.id),'[]'::jsonb)from erp.fg_stock_movements m
  where m.product_id in(p_source,p_target)and m.location_id=p_location and m.quality_grade='GRADE_A'),
 'hpp',(select coalesce(jsonb_agg(jsonb_build_array(l.id,to_jsonb(h))order by l.id),'[]'::jsonb)
  from erp.fg_lots l left join erp.v_current_hpp h on h.lot_id=l.id where l.product_id in(p_source,p_target)),
 'lots',(select coalesce(jsonb_agg(jsonb_build_array(l.id,l.produced_at,l.lot_origin,erp.be_source_revision_v1(l.id,p_location))order by l.produced_at,l.id),'[]'::jsonb)
 from erp.fg_lots l where l.product_id in(p_source,p_target)))::text)
$$;

create function cp7_sku_conversion.preview_v1(p_payload jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare src erp.products%rowtype;dst erp.products%rowtype;loc erp.locations%rowtype;qty int;at_time timestamptz;
 need int;take_qty int;r record;allocation jsonb:='[]'::jsonb;source_stock jsonb;target_stock jsonb;revision text;value numeric:=0;money boolean;
begin
 perform erp.require_permission('warehouse.brand_conversion.view');
 perform erp._cp3_assert_closed_json_object(p_payload,array['source_product_id','target_product_id','location_id','qty_pcs','physical_at','reason'],
 array['source_product_id','target_product_id','location_id','qty_pcs','physical_at','reason','expected_version','expected_returns'],'konversi SKU');
 perform erp.pocket_period_lock_v1();
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform erp.require_permission('warehouse.brand_conversion.view');
 perform 1 from erp.products where id in(erp.bd_uuid_v1(p_payload,'source_product_id',true),erp.bd_uuid_v1(p_payload,'target_product_id',true))order by id for share;
 select *into src from erp.products where id=erp.bd_uuid_v1(p_payload,'source_product_id',true);
 select *into dst from erp.products where id=erp.bd_uuid_v1(p_payload,'target_product_id',true);
 select *into loc from erp.locations where id=erp.bd_uuid_v1(p_payload,'location_id',true)for share;
 perform erp.require_permission('warehouse.brand_conversion.view');
 if src.id is null or dst.id is null or not dst.is_active then raise exception 'CP7_SKU_TARGET_INACTIVE: pilih SKU tujuan aktif';end if;
 if src.id=dst.id then raise exception 'CP7_SKU_SAME_PRODUCT: SKU asal dan tujuan harus berbeda';end if;
 if loc.id is null or not loc.is_active or loc.location_type<>'FG_WAREHOUSE'then raise exception 'CP7_SKU_LOCATION_REQUIRED';end if;
 qty:=erp.bd_qty_v1(p_payload->'qty_pcs','qty_pcs');at_time:=erp.bd_at_v1(p_payload->>'physical_at','physical_at');
 perform erp.bc_text_v1(p_payload,'reason',true,1000);
 if at_time<src.effective_from or at_time<dst.effective_from or(dst.effective_to is not null and at_time>=dst.effective_to)then raise exception 'CP7_SKU_IDENTITY_DATE: waktu fisik tidak sesuai versi SKU';end if;
 source_stock:=cp7_sku_conversion.stock_v1(src.id,loc.id);target_stock:=cp7_sku_conversion.stock_v1(dst.id,loc.id);
 revision:=cp7_sku_conversion.revision_v1(src.id,dst.id,loc.id);
 if p_payload?'expected_version'and p_payload->>'expected_version'is distinct from revision then raise exception 'STALE_VERSION: stok, reservasi atau HPP berubah; periksa pratinjau terbaru';end if;
 need:=qty;money:=erp.has_permission('finance.hpp.view');
 for r in select l.id,l.lot_number,l.produced_at,h.hpp_per_pcs,
  least(coalesce(sum(m.qty_signed),0),coalesce(sum(m.qty_signed)filter(where m.physical_at<=at_time),0))::int available
  from erp.fg_lots l join erp.fg_stock_movements m on m.lot_id=l.id and m.location_id=loc.id and m.quality_grade='GRADE_A'
  left join erp.v_current_hpp h on h.lot_id=l.id
  where l.product_id=src.id and l.produced_at<=at_time and l.lot_origin<>'VOIDED_PRODUCTION'
  group by l.id,h.hpp_per_pcs having least(coalesce(sum(m.qty_signed),0),coalesce(sum(m.qty_signed)filter(where m.physical_at<=at_time),0))>0
  order by l.produced_at,l.id loop
  exit when need=0;
  if r.hpp_per_pcs is null then raise exception 'CP7_SKU_SOURCE_HPP_UNKNOWN: nilai lot sumber belum diketahui';end if;
  take_qty:=least(need,r.available);need:=need-take_qty;
  allocation:=allocation||jsonb_build_array(jsonb_build_object('source_lot_id',r.id,'lot_number',r.lot_number,'qty_pcs',take_qty,
   'source_revision',erp.be_source_revision_v1(r.id,loc.id),
   'source_value',case when money then round(take_qty*r.hpp_per_pcs,2)::text end));
  -- Same cent rounding as each Native selected-lot conversion journal.
  value:=value+round(take_qty*r.hpp_per_pcs,2);
 end loop;
 if need>0 then raise exception 'CP7_SKU_INSUFFICIENT: stok tersedia pada lokasi/tanggal tidak cukup, kurang % PCS',need;end if;
 return jsonb_build_object('source_product_id',src.id,'target_product_id',dst.id,'location_id',loc.id,'location_name',loc.location_name,
 'source_sku',src.sku,'target_sku',dst.sku,'qty_pcs',qty,'physical_at',at_time,'source_revision',revision,'allocations',allocation,
 'source_stock',source_stock,'target_stock',target_stock,'source_after',jsonb_build_object('available',(source_stock->>'available')::bigint-qty,'physical',(source_stock->>'physical')::bigint-qty,'reserved',(source_stock->>'reserved')::bigint),
 'target_after',jsonb_build_object('available',(target_stock->>'available')::bigint+qty,'physical',(target_stock->>'physical')::bigint+qty,'reserved',(target_stock->>'reserved')::bigint),
 'cost',case when money then jsonb_build_object('source_value',value::text)else '{}'::jsonb end);
end $$;

create function cp7_sku_conversion.action_v1(p_action text,p_payload jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare a text:=upper(btrim(coalesce(p_action,'')));v jsonb;prior jsonb;part jsonb;child_payload jsonb;child jsonb;
 ids jsonb:='[]'::jsonb;destinations jsonb:='[]'::jsonb;child_id uuid;v_group_id uuid;i int:=0;r record;
begin
 perform erp.require_permission('warehouse.brand_conversion.view');
 if a not in('POST','REVERSE','POST_USAGE','SAVE_REWORK','SAVE_REDYE','SET_REDYE_PRICE')then raise exception 'BE_ACTION_UNKNOWN: tindakan tidak dikenal';end if;
 if not(a='POST'and p_payload?'source_product_id')and not(a='REVERSE'and exists(select 1 from cp7_sku_conversion.members_v1 where conversion_id=(p_payload->>'conversion_id')::uuid))then
  return erp.save_product_conversion_action_v1(p_action,p_payload,p_request);end if;
 perform erp.require_permission('warehouse.brand_conversion.view');perform erp.require_permission(case when a='REVERSE'then 'warehouse.brand_conversion.reverse'else 'warehouse.brand_conversion.post'end);
 if a='REVERSE'then perform erp.require_owner_admin();end if;perform erp.require_internal();
 if p_request is null or jsonb_typeof(p_payload)is distinct from 'object'or octet_length(p_payload::text)>30000 then raise exception 'CP7_SKU_CONVERSION_REQUEST';end if;
 prior:=erp._idempotency_begin('cp7_sku_conversion_v1',p_request,erp._request_hash(jsonb_build_object('action',a,'payload',p_payload)));
 perform erp.require_permission('warehouse.brand_conversion.view');perform erp.require_permission(case when a='REVERSE'then 'warehouse.brand_conversion.reverse'else 'warehouse.brand_conversion.post'end);
 if a='REVERSE'then perform erp.require_owner_admin();end if;perform erp.require_internal();
 if prior is not null then return prior;end if;
 perform erp.pocket_period_lock_v1();perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform erp.require_permission('warehouse.brand_conversion.view');perform erp.require_permission(case when a='REVERSE'then 'warehouse.brand_conversion.reverse'else 'warehouse.brand_conversion.post'end);
 if a='REVERSE'then perform erp.require_owner_admin();end if;perform erp.require_internal();
 if a='POST'then
  if not(p_payload?'expected_version')then raise exception 'CP7_SKU_PREVIEW_REQUIRED';end if;
  v:=cp7_sku_conversion.preview_v1(p_payload);
  perform erp.require_permission('warehouse.brand_conversion.view');perform erp.require_permission('warehouse.brand_conversion.post');perform erp.require_internal();
  insert into cp7_sku_conversion.groups_v1(request_id,actor,payload)values(p_request,erp.current_app_user_id(),p_payload);
  insert into cp7_sku_conversion.execution_v1(backend_pid,transaction_id,group_id,mode)values(pg_backend_pid(),txid_current(),p_request,'POST');
  for part in select value from jsonb_array_elements(v->'allocations')with ordinality as parts(value,ordinal)order by ordinal loop
   i:=i+1;child_id:=case when i=1 then p_request else gen_random_uuid()end;
   update cp7_sku_conversion.execution_v1 set source_lot_id=(part->>'source_lot_id')::uuid,target_id=(v->>'target_product_id')::uuid,
    location_id=(v->>'location_id')::uuid,qty=(part->>'qty_pcs')::int,physical_at=(v->>'physical_at')::timestamptz
    where backend_pid=pg_backend_pid()and transaction_id=txid_current();
   child_payload:=jsonb_build_object('source_lot_id',part->'source_lot_id','target_product_id',v->'target_product_id','location_id',v->'location_id',
    'qty_pcs',part->'qty_pcs','physical_at',v->'physical_at','reason',p_payload->'reason','expected_version',part->'source_revision');
   if i=1 and p_payload?'expected_returns'then child_payload:=child_payload||jsonb_build_object('expected_returns',p_payload->'expected_returns');end if;
   child:=erp.save_product_conversion_action_v1('POST',child_payload,child_id);
   insert into cp7_sku_conversion.members_v1 values(child_id,p_request,i);
   ids:=ids||jsonb_build_array(child_id);destinations:=destinations||jsonb_build_array(child->'destination_lot_id');
  end loop;
  v:=v||jsonb_build_object('conversion_id',p_request,'destination_lot_id',destinations->0,'conversion_ids',ids,'destination_lot_ids',destinations,'status','POSTED');
 else
  perform erp._cp3_assert_closed_json_object(p_payload,array['conversion_id','reason'],array['conversion_id','reason'],'pembatalan konversi');
  perform erp.bc_text_v1(p_payload,'reason',true,1000);
  select m.group_id into strict v_group_id from cp7_sku_conversion.members_v1 m where m.conversion_id=(p_payload->>'conversion_id')::uuid;
  insert into cp7_sku_conversion.execution_v1(backend_pid,transaction_id,group_id,mode)values(pg_backend_pid(),txid_current(),v_group_id,'REVERSE');
  for r in select m.conversion_id from cp7_sku_conversion.members_v1 m where m.group_id=v_group_id order by line_no desc loop
   child:=erp.save_product_conversion_action_v1('REVERSE',jsonb_build_object('conversion_id',r.conversion_id,'reason',p_payload->'reason'),
     case when r.conversion_id=(p_payload->>'conversion_id')::uuid then p_request else gen_random_uuid()end);
   ids:=ids||jsonb_build_array(r.conversion_id);
  end loop;
  v:=jsonb_build_object('conversion_id',p_payload->'conversion_id','conversion_ids',ids,'status','REVERSED');
 end if;
 delete from cp7_sku_conversion.execution_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 return erp._idempotency_complete('cp7_sku_conversion_v1',p_request,v||jsonb_build_object('request_id',p_request,'action',a));
end $$;

create function cp7_sku_conversion.workspace_v1(p_filters jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare f jsonb:=coalesce(p_filters,'{}'::jsonb);answer jsonb;q text;tq text;src uuid;loc uuid;dst uuid;page_no int;target_page int;rec_group uuid;
begin
 perform erp.require_permission('warehouse.brand_conversion.view');
 if f?'preview'and(f->'preview')?'source_product_id'then return jsonb_build_object('preview',cp7_sku_conversion.preview_v1(f->'preview'));end if;
 answer:=erp.get_product_conversion_workspace_v1(f-'selection');
 q:=lower(coalesce(erp.bc_text_v1(f,'query',false,120),''));tq:=lower(coalesce(erp.bc_text_v1(f,'target_query',false,120),''));
 src:=erp.bd_uuid_v1(f,'source_product_id',false);page_no:=coalesce((f->>'page')::int,1);target_page:=coalesce((f->>'target_page')::int,1);
 select cp7_sku_conversion.partner_v1(v.sku_id)into rec_group from erp.products p
 join erp.bf_sku_members_v1 sm on sm.product_root=p.identity_root_id join erp.bf_sku_versions_v1 v on v.id=sm.version_id
 where p.id=src and v.effective_from<=statement_timestamp()and(v.effective_to is null or v.effective_to>statement_timestamp());
 with positions as materialized(
  select m.product_id,m.location_id,sum(m.qty_signed)::bigint available,
   coalesce(sum(abs(m.qty_signed))filter(where m.movement_type='SALE_RESERVE'and not exists(
    select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id and rv.physical_at<=statement_timestamp())),0)::bigint reserved
  from erp.fg_stock_movements m where m.quality_grade='GRADE_A'and m.physical_at<=statement_timestamp()
  group by m.product_id,m.location_id),
 sources as materialized(select p.id product_id,p.sku,p.product_name,b.brand_name,z.size_code size,locs.id location_id,locs.location_name,
  jsonb_build_object('available',positions.available,'reserved',positions.reserved,'physical',positions.available+positions.reserved)stock
  from positions join erp.products p on p.id=positions.product_id join erp.brands b on b.id=p.brand_id join erp.sizes z on z.id=p.size_id
  join erp.locations locs on locs.id=positions.location_id and locs.is_active and locs.location_type='FG_WAREHOUSE'
  where positions.available>0 and(q=''or lower(p.sku||' '||p.product_name||' '||b.brand_name)like '%'||q||'%')),
 pg as(select *from sources order by brand_name,sku,size,product_id,location_id limit 25 offset(page_no-1)*25)
 select answer||jsonb_build_object('contract_version','cp7.sku-conversion.v1','sources',coalesce((select jsonb_agg(to_jsonb(pg)order by brand_name,sku,size,product_id,location_id)from pg),'[]'::jsonb),'sources_total',(select count(*)from sources))into answer;
 with recommended_roots as materialized(select sm.product_root from erp.bf_sku_members_v1 sm
  join erp.bf_sku_versions_v1 v on v.id=sm.version_id where v.sku_id=rec_group and v.effective_from<=statement_timestamp()
   and(v.effective_to is null or v.effective_to>statement_timestamp())),
 targets as materialized(select p.id,p.sku,p.product_name,b.brand_name,z.size_code size,
 p.identity_root_id in(select product_root from recommended_roots)recommended
 from erp.products p join erp.brands b on b.id=p.brand_id join erp.sizes z on z.id=p.size_id
 where p.is_active and p.id is distinct from src and(tq=''or lower(p.sku||' '||p.product_name||' '||b.brand_name)like '%'||tq||'%')),
 pg as(select *from targets order by recommended desc,brand_name,sku,size,id limit 25 offset(target_page-1)*25)
 select answer||jsonb_build_object('targets',coalesce((select jsonb_agg(to_jsonb(pg)order by recommended desc,brand_name,sku,size,id)from pg),'[]'::jsonb),'targets_total',(select count(*)from targets))into answer;
 if f?'selection'then
  src:=erp.bd_uuid_v1(f->'selection','source_product_id',true);loc:=erp.bd_uuid_v1(f->'selection','location_id',true);dst:=erp.bd_uuid_v1(f->'selection','target_product_id',false);
  answer:=answer||jsonb_build_object('selection',jsonb_build_object('source_product_id',src,'target_product_id',dst,'location_id',loc,
   'source_stock',cp7_sku_conversion.stock_v1(src,loc),'target_stock',case when dst is not null then cp7_sku_conversion.stock_v1(dst,loc)end));
 end if;
 answer:=answer||jsonb_build_object('documents',coalesce((select jsonb_agg(d||coalesce((select jsonb_build_object(
  'group_id',m.group_id,'group_qty_pcs',(g.payload->>'qty_pcs')::int,'group_part_count',(select count(*)from cp7_sku_conversion.members_v1 all_members where all_members.group_id=m.group_id),
  'group_line_no',m.line_no)from cp7_sku_conversion.members_v1 m join cp7_sku_conversion.groups_v1 g on g.request_id=m.group_id where m.conversion_id=(d->>'id')::uuid),'{}'::jsonb)order by ordinal)
  from jsonb_array_elements(answer->'documents')with ordinality as docs(d,ordinal)),'[]'::jsonb));
 return answer;
end $$;
