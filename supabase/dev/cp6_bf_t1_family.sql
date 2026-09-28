-- BF development family. NOT_READY until complete qualification. Generated; do not edit.
begin;set local search_path='';set local lock_timeout='10s';set local statement_timeout='240s';
do $guard$ begin if not exists(select 1 from erp.schema_migrations where version='v2.6.20be') then raise exception 'BF_REQUIRES_BE';end if;
if exists(select 1 from erp.schema_migrations where version='v2.6.20bf') then raise exception 'BF_ALREADY_INSTALLED';end if;end $guard$;
-- Commercial identity is separate from the exact-size physical identity root.
create table erp.bf_skus_v1(
 id uuid primary key default gen_random_uuid(), brand_id uuid not null references erp.brands(id),
 model_id uuid not null references erp.product_models(id), color_name text not null,
 sku text not null check(length(btrim(sku)) between 1 and 100), revision bigint not null default 0,
 unique(brand_id,sku)
);
create table erp.bf_sku_versions_v1(
 id uuid primary key default gen_random_uuid(), sku_id uuid not null references erp.bf_skus_v1(id), revision bigint not null,
 effective_from timestamptz not null, effective_to timestamptz, settings jsonb not null,
 reason text not null, actor uuid, request_id uuid not null, created_at timestamptz not null default clock_timestamp(),
 unique(sku_id,revision), check(effective_to is null or effective_to>effective_from)
);
create table erp.bf_sku_members_v1(
 version_id uuid not null references erp.bf_sku_versions_v1(id), product_root uuid not null references erp.products(id),
 price_version_id uuid references erp.product_price_versions(id), bom_version_id uuid references erp.accessory_bom_versions(id),
 primary key(version_id,product_root)
);
create index bf_sku_members_root on erp.bf_sku_members_v1(product_root,version_id);
create table erp.bf_wave_skus_v1(
 cutting_group_id uuid not null references erp.cutting_groups(id) on delete cascade,
 size_id uuid not null references erp.sizes(id), sku_id uuid not null references erp.bf_skus_v1(id),
 bound_at timestamptz not null default clock_timestamp(), actor uuid, request_id uuid not null,
 primary key(cutting_group_id,size_id)
);
alter table erp.po_work_component_snapshots add column bf_sku_version_id uuid references erp.bf_sku_versions_v1(id);
alter table erp.po_work_component_snapshots drop constraint po_work_component_snapshots_po_id_work_component_id_key;
create unique index bf_work_snapshot_scope on erp.po_work_component_snapshots(po_id,work_component_id,bf_sku_version_id) nulls not distinct;
create table erp.bf_po_boms_v1(
 po_id uuid not null references erp.production_orders(id), sku_id uuid not null references erp.bf_skus_v1(id),
 version_id uuid not null references erp.bf_sku_versions_v1(id), primary key(po_id,sku_id)
);
create table erp.bf_requests_v1(request_id uuid primary key,actor uuid,action text not null,payload jsonb not null,response jsonb not null);
create table erp.bf_context_v1(backend_pid integer not null,transaction_id bigint not null,version_id uuid references erp.bf_sku_versions_v1(id),primary key(backend_pid,transaction_id));

CREATE OR REPLACE FUNCTION erp.bf_version_at_v1(p_product uuid,p_at timestamptz)
 RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select v.id from erp.products p join erp.bf_sku_members_v1 m on m.product_root=p.identity_root_id
 join erp.bf_sku_versions_v1 v on v.id=m.version_id
 where p.id=p_product and v.effective_from<=p_at and (v.effective_to is null or v.effective_to>p_at)
$function$;

-- Guard every old single-size economic write, including import/direct RPC routes.
CREATE OR REPLACE FUNCTION erp.bf_guard_economic_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r uuid; previous_root uuid; b uuid;
begin
 if exists(select 1 from erp.bf_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current()) then
   if TG_OP='DELETE' then return old;else return new;end if;
 end if;
 if TG_TABLE_NAME='accessory_bom_items' then
   b:=case when TG_OP='DELETE' then old.bom_version_id else new.bom_version_id end;
   select product_id into r from erp.accessory_bom_versions where id=b;
   if TG_OP='UPDATE' then select product_id into previous_root from erp.accessory_bom_versions where id=old.bom_version_id;end if;
 else r:=case when TG_OP='DELETE' then old.product_id else new.product_id end;end if;
 if TG_TABLE_NAME<>'accessory_bom_items' and TG_OP='UPDATE' then previous_root:=old.product_id;end if;
 if exists(select 1 from erp.bf_sku_members_v1 where product_root in(r,previous_root)) then
   raise exception 'BF_SHARED_MASTER: ubah harga/resep melalui master SKU bersama';
 end if;
 if TG_OP='DELETE' then return old;else return new;end if;
end;$function$;
create trigger bf_shared_price before insert or update or delete on erp.product_price_versions for each row execute function erp.bf_guard_economic_v1();
create trigger bf_shared_bom before insert or update or delete on erp.accessory_bom_versions for each row execute function erp.bf_guard_economic_v1();
create trigger bf_shared_bom_item before insert or update or delete on erp.accessory_bom_items for each row execute function erp.bf_guard_economic_v1();

CREATE OR REPLACE FUNCTION erp.bf_legacy_basis_v1(p_roots uuid[],p_at timestamptz)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce(jsonb_agg(jsonb_build_object('product_root',p.id,'price',pr.price,'price_id',pr.id,
   'bom_id',b.id,'bom',case when b.id is not null then coalesce((select jsonb_agg(to_jsonb(i)-'id'-'bom_version_id' order by i.category_id,i.id)
   from erp.accessory_bom_items i where i.bom_version_id=b.id),'[]'::jsonb) end) order by p.id),'[]'::jsonb)
 from erp.products p
 left join lateral(select x.id,x.price from erp.product_price_versions x where x.product_id=p.id and x.effective_from<=p_at
   and (x.effective_to is null or x.effective_to>p_at) order by x.effective_from desc,x.id desc limit 1) pr on true
 left join lateral(select x.id from erp.accessory_bom_versions x where x.product_id=p.id and x.is_active and x.effective_from<=p_at
   and (x.effective_to is null or x.effective_to>p_at) order by x.effective_from desc,x.id desc limit 1) b on true
 where p.id=any(p_roots)
$function$;

CREATE OR REPLACE FUNCTION erp.bf_save_groups_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare at_time timestamptz; reason text; g jsonb; cfg jsonb; item jsonb; row_sku erp.bf_skus_v1%rowtype;
 root uuid; roots uuid[]; all_roots uuid[]:='{}'; group_ids uuid[]:='{}'; sid uuid; vid uuid; price_id uuid; bom_id uuid;
 result jsonb:='[]'; basis jsonb; current_v erp.bf_sku_versions_v1%rowtype; p erp.products%rowtype;
begin
 perform erp._cp3_assert_closed_json_object(p_payload,array['effective_from','reason','groups'],array['effective_from','reason','groups'],'SKU changes');
 at_time:=erp.bd_at_v1(p_payload->>'effective_from','effective_from'); reason:=erp.bc_text_v1(p_payload,'reason',true,1000);
 if at_time<statement_timestamp()-interval '5 minutes' then raise exception 'BF_HISTORY: master baru hanya mulai sekarang atau mendatang';end if;
 if jsonb_typeof(p_payload->'groups') is distinct from 'array' or jsonb_array_length(p_payload->'groups') not between 1 and 30 then
   raise exception 'BF_GROUPS: wajib 1 sampai 30 kelompok';end if;
 -- One lock also serializes movements between groups and edits arriving via different member sizes.
 perform pg_advisory_xact_lock(hashtextextended('BF:COMMERCIAL_SKUS',0));
 insert into erp.bf_context_v1(backend_pid,transaction_id) values(pg_backend_pid(),txid_current());
 -- Validate the whole edit and close all old memberships before attaching any new membership.
 for g in select value from jsonb_array_elements(p_payload->'groups') loop
   perform erp._cp3_assert_closed_json_object(g,array['id','expected_version','brand_id','model_id','color_name','sku','members','settings','legacy_basis'],
     array['id','expected_version','brand_id','model_id','color_name','sku','members','settings','legacy_basis'],'SKU group');
   sid:=erp.bd_uuid_v1(g,'id',true); if sid=any(group_ids) then raise exception 'BF_DUPLICATE_SKU';end if;
   group_ids:=group_ids||sid;
   select * into row_sku from erp.bf_skus_v1 where id=sid for update;
   if not found then
     if g->>'expected_version'<>'0' then raise exception 'STALE_VERSION';end if;
     insert into erp.bf_skus_v1(id,brand_id,model_id,color_name,sku)
     values(sid,erp.bd_uuid_v1(g,'brand_id',true),erp.bd_uuid_v1(g,'model_id',true),erp.bc_text_v1(g,'color_name',true,100),erp.bc_text_v1(g,'sku',true,100)) returning * into row_sku;
   elsif row_sku.revision::text is distinct from g->>'expected_version' then raise exception 'STALE_VERSION';
   elsif row_sku.brand_id<>erp.bd_uuid_v1(g,'brand_id',true) or row_sku.model_id<>erp.bd_uuid_v1(g,'model_id',true)
     or row_sku.color_name<>g->>'color_name' or row_sku.sku<>g->>'sku' then raise exception 'BF_IDENTITY: gunakan SKU baru untuk identitas komersial lain';end if;
   if jsonb_typeof(g->'members') is distinct from 'array' then raise exception 'BF_MEMBERS';end if;
   select coalesce(array_agg(x::uuid order by x),'{}') into roots from jsonb_array_elements_text(g->'members') x;
   if cardinality(roots)<>(select count(distinct x) from unnest(roots) x) then raise exception 'BF_DUPLICATE_MEMBER';end if;
   if roots&&all_roots then raise exception 'BF_DUPLICATE_MEMBER';end if;all_roots:=all_roots||roots;
   foreach root in array roots loop
     select * into p from erp.products where id=root for update;
     if p.id is null or p.identity_root_id<>p.id or p.brand_id<>row_sku.brand_id or p.model_id<>row_sku.model_id or p.color_name<>row_sku.color_name then
       raise exception 'BF_MEMBER_IDENTITY: anggota wajib akar fisik dengan merek/model/warna sama';end if;
   end loop;
   if cardinality(roots)<>(select count(distinct size_id) from erp.products where id=any(roots)) then raise exception 'BF_DUPLICATE_SIZE';end if;
   basis:=erp.bf_legacy_basis_v1(roots,at_time);
   if g->'legacy_basis' is distinct from basis then raise exception 'BF_BASIS_CHANGED: baca semua harga/resep anggota lalu konfirmasi pengaturan bersama';end if;
   select * into current_v from erp.bf_sku_versions_v1 where sku_id=sid and effective_to is null;
   if current_v.id is not null then
     if at_time<=current_v.effective_from then raise exception 'BF_EFFECTIVE_ORDER';end if;
     update erp.bf_sku_versions_v1 set effective_to=at_time where id=current_v.id;
   end if;
 end loop;
 if exists(select 1 from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id
     where m.product_root=any(all_roots) and v.effective_to is null) then raise exception 'BF_MOVE_ATOMIC: sertakan revisi kelompok asal dalam perubahan yang sama';end if;
 if exists(select 1 from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id
     where v.sku_id=any(group_ids) and v.effective_to=at_time and not(m.product_root=any(all_roots))) then
   raise exception 'BF_ORPHAN_MEMBER: anggota yang dikeluarkan wajib dipindah ke SKU tujuan';end if;
 for g in select value from jsonb_array_elements(p_payload->'groups') loop
   sid:=(g->>'id')::uuid;cfg:=g->'settings';
   perform erp._cp3_assert_closed_json_object(cfg,array['price','bom','work_rates','laundry_rates'],array['price','bom','work_rates','laundry_rates'],'SKU settings');
   if jsonb_typeof(cfg->'bom') not in('array','null') or jsonb_typeof(cfg->'work_rates') is distinct from 'array'
     or jsonb_typeof(cfg->'laundry_rates') is distinct from 'array' then raise exception 'BF_SETTINGS_ARRAY';end if;
   if cfg->'price'<>'null'::jsonb then perform erp.bd_amount_v1(cfg->'price','price',true);end if;
   perform erp.bf_validate_rates_v1(sid,cfg);
   update erp.bf_skus_v1 set revision=revision+1 where id=sid returning * into row_sku;
   insert into erp.bf_sku_versions_v1(sku_id,revision,effective_from,settings,reason,actor,request_id)
     values(sid,row_sku.revision,at_time,cfg,reason,erp.current_app_user_id(),p_request) returning id into vid;
   for root in select x::uuid from jsonb_array_elements_text(g->'members') x loop
     -- Existing historical guards reject an effective date before any already-posted financial use.
     if exists(select 1 from erp.product_price_versions where product_id=root and effective_from>=at_time)
       or exists(select 1 from erp.accessory_bom_versions where product_id=root and effective_from>=at_time) then
       raise exception 'BF_FUTURE_MASTER: selesaikan versi ekonomi mendatang sebelum mengubah kelompok';end if;
     update erp.product_price_versions set effective_to=at_time where product_id=root and (effective_to is null or effective_to>at_time);
     update erp.accessory_bom_versions set effective_to=at_time where product_id=root and (effective_to is null or effective_to>at_time);
     price_id:=null;bom_id:=null;
     if cfg->'price'<>'null'::jsonb then
       insert into erp.product_price_versions(product_id,price,effective_from,change_note,created_by)
         values(root,(cfg->>'price')::numeric,at_time,reason,erp.current_app_user_id()) returning id into price_id;
     end if;
     if cfg->'bom'<>'null'::jsonb then
       insert into erp.accessory_bom_versions(product_id,version_label,effective_from,notes,created_by)
         values(root,'SKU revision '||row_sku.revision,at_time,reason,erp.current_app_user_id()) returning id into bom_id;
     end if;
     for item in select value from jsonb_array_elements(case when cfg->'bom'='null'::jsonb then '[]'::jsonb else cfg->'bom' end) loop
       perform erp._cp3_assert_closed_json_object(item,array['category_id','qty_per_good_fg_base','hpp_method','reimbursement_rate','reimbursement_uom_code'],
         array['category_id','qty_per_good_fg_base','hpp_method','hpp_standard_rate','hpp_uom_code','reimbursement_rate','reimbursement_uom_code','notes'],'SKU accessory');
       insert into erp.accessory_bom_items(bom_version_id,category_id,qty_per_good_fg_base,hpp_method,hpp_standard_rate,hpp_uom_code,reimbursement_rate,reimbursement_uom_code,notes)
       values(bom_id,(item->>'category_id')::uuid,(item->>'qty_per_good_fg_base')::numeric,item->>'hpp_method',
         (item->>'hpp_standard_rate')::numeric,item->>'hpp_uom_code',(item->>'reimbursement_rate')::numeric,item->>'reimbursement_uom_code',item->>'notes');
     end loop;
     insert into erp.bf_sku_members_v1 values(vid,root,price_id,bom_id);
   end loop;
   result:=result||jsonb_build_object('id',sid,'version_id',vid,'revision',row_sku.revision::text);
   insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
     values('bf_skus_v1',sid,'UPDATE',jsonb_build_object('version_id',vid,'members',g->'members'),erp.current_app_user_id(),reason);
 end loop;
 delete from erp.bf_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current();
 return jsonb_build_object('groups',result);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bf_validate_rates_v1(p_sku uuid,p_settings jsonb)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare j jsonb; k text; ref uuid; vendor uuid; amount numeric; seen text[]:='{}'; key text;
begin
 for j in select value from jsonb_array_elements(p_settings->'work_rates') loop
   perform erp._cp3_assert_closed_json_object(j,array['contractor_id','work_component_id','rate'],array['contractor_id','work_component_id','rate'],'SKU work rate');
   vendor:=erp.bd_uuid_v1(j,'contractor_id',true);ref:=erp.bd_uuid_v1(j,'work_component_id',true);
   if not exists(select 1 from erp.contractors where id=vendor and is_active)
     or not exists(select 1 from erp.work_components where id=ref and is_active) then raise exception 'BF_WORK_RATE_REFERENCE';end if;
   perform erp.bd_amount_v1(j->'rate','rate',true);key:=vendor::text||':'||ref::text;
   if key=any(seen) then raise exception 'BF_DUPLICATE_RATE';end if;seen:=seen||key;
 end loop;
 seen:='{}';
 for j in select value from jsonb_array_elements(p_settings->'laundry_rates') loop
   perform erp._cp3_assert_closed_json_object(j,array['vendor_id','kind','ref_id','rate_status','rate','reason'],
     array['vendor_id','kind','ref_id','rate_status','rate','reason'],'SKU laundry rate');
   k:=j->>'kind';ref:=erp.bd_uuid_v1(j,'ref_id',true);vendor:=erp.bd_uuid_v1(j,'vendor_id',true);
   if not exists(select 1 from erp.laundry_vendors where id=vendor and is_active) then raise exception 'BF_VENDOR';end if;
   if k='PROCESS' then
     if not exists(select 1 from erp.wash_processes where id=ref and is_active) then raise exception 'BF_PROCESS';end if;
   elsif k='COMPONENT' then
     if not exists(select 1 from erp.bd_laundry_components_v1 where id=ref and vendor_id=vendor and is_active) then raise exception 'BF_COMPONENT';end if;
   elsif k='PACKAGE' then
     if not exists(select 1 from erp.bd_laundry_packages_v1 where id=ref and vendor_id=vendor and is_active) then raise exception 'BF_PACKAGE';end if;
   else raise exception 'BF_RATE_KIND';end if;
   if j->>'rate_status' not in('KNOWN','UNKNOWN','FREE','WAIVED') or j->>'rate_status' is null then raise exception 'BF_RATE_STATUS';end if;
   if k<>'COMPONENT' and j->>'rate_status'<>'KNOWN' then raise exception 'BF_COMPONENT_MODE_REQUIRED: gunakan komponen untuk UNKNOWN/FREE/WAIVED';end if;
   if j->>'rate_status'='UNKNOWN' then
     if j->'rate'<>'null'::jsonb then raise exception 'BF_UNKNOWN_RATE';end if;
   else
     amount:=erp.bd_amount_v1(j->'rate','rate',true);
     if j->>'rate_status'='KNOWN' and amount<=0 then raise exception 'BF_ZERO_USE_FREE';end if;
     if j->>'rate_status' in('FREE','WAIVED') and (amount<>0 or nullif(btrim(j->>'reason'),'') is null) then raise exception 'BF_FREE_REASON';end if;
   end if;
   key:=vendor::text||':'||k||':'||ref::text;
   if key=any(seen) then raise exception 'BF_DUPLICATE_RATE';end if;seen:=seen||key;
 end loop;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bf_context_rate_v1(p_kind text,p_ref uuid,p_vendor uuid DEFAULT NULL)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select r||jsonb_build_object('version_id',v.id) from erp.bf_context_v1 c
 join erp.bf_sku_versions_v1 v on v.id=c.version_id cross join lateral jsonb_array_elements(v.settings->'laundry_rates') r
 where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current() and r->>'kind'=p_kind and r->>'ref_id'=p_ref::text and(p_vendor is null or r->>'vendor_id'=p_vendor::text)
$function$;

CREATE OR REPLACE FUNCTION erp.bf_bom_for_lot_v1(p_lot uuid)
 RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare l erp.fg_lots%rowtype; vid uuid; pinned uuid; sid uuid; root uuid; bom uuid;
begin
 select * into l from erp.fg_lots where id=p_lot;
 vid:=erp.bf_version_at_v1(l.product_id,l.produced_at);
 if vid is null then return null;end if;
 select sku_id into sid from erp.bf_sku_versions_v1 where id=vid;
 select identity_root_id into root from erp.products where id=l.product_id;
 select version_id into pinned from erp.bf_po_boms_v1 where po_id=l.po_id and sku_id=sid;
 if pinned is null then
   -- A pre-adoption PO has already committed its old recipe. Never silently mix a new group recipe into that PO.
   if exists(select 1 from erp.po_accessory_bom_commitments c join erp.products p on p.id=c.product_id
     join erp.bf_sku_members_v1 m on m.product_root=p.identity_root_id and m.version_id=vid where c.po_id=l.po_id) then
     raise exception 'BF_PO_LEGACY_BOM: PO sudah memakai resep lama; selesaikan memakai komitmen lama sebelum adopsi SKU';end if;
   insert into erp.bf_po_boms_v1 values(l.po_id,sid,vid);pinned:=vid;
 end if;
 select bom_version_id into bom from erp.bf_sku_members_v1 where version_id=pinned and product_root=root;
 if bom is null then raise exception 'BF_PO_NEW_MEMBER: ukuran baru tidak termasuk resep PO yang telah disepakati';end if;
 return bom;
end;$function$;

-- A wave can contain several ranges. Its reference chooses rates, never final FG identity.
CREATE OR REPLACE FUNCTION erp.bf_bind_wave_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare g erp.cutting_groups%rowtype; r jsonb; sid uuid; sku uuid; vid uuid; model uuid; seen uuid[]:='{}'; before_hash text;
begin
 perform erp._cp3_assert_closed_json_object(p_payload,array['cutting_group_id','references','expected_version'],array['cutting_group_id','references','expected_version'],'wave SKU references');
 select * into g from erp.cutting_groups where id=erp.bd_uuid_v1(p_payload,'cutting_group_id',true) for update;
 if g.id is null then raise exception 'BF_WAVE_MISSING';end if;
 select model_id into model from erp.production_orders where id=g.po_id;
 before_hash:=erp.bf_wave_revision_v1(g.id);
 if p_payload->>'expected_version' is distinct from before_hash then raise exception 'STALE_VERSION';end if;
 if exists(select 1 from erp.work_completion_events where cutting_group_id=g.id and status='POSTED')
   or exists(select 1 from erp.fg_lots where cutting_group_id=g.id)
   or exists(select 1 from erp.laundry_deliveries d join erp.laundry_delivery_lines l on l.delivery_id=d.id
     where l.cutting_group_id=g.id and d.status not in('DRAFT','REVERSED')) then
   raise exception 'BF_WAVE_USED: referensi pekerjaan yang sudah dipakai terkunci';end if;
 if jsonb_typeof(p_payload->'references') is distinct from 'array' then raise exception 'BF_REFERENCES';end if;
 delete from erp.bf_wave_skus_v1 where cutting_group_id=g.id;
 for r in select value from jsonb_array_elements(p_payload->'references') loop
   perform erp._cp3_assert_closed_json_object(r,array['sku_id','size_id'],array['sku_id','size_id'],'wave size SKU');
   sku:=erp.bd_uuid_v1(r,'sku_id',true);sid:=erp.bd_uuid_v1(r,'size_id',true);
   if sid=any(seen) then raise exception 'BF_DUPLICATE_SIZE';end if;seen:=seen||sid;
   if not exists(select 1 from erp.cutting_group_size_slots where cutting_group_id=g.id and size_id=sid) then raise exception 'BF_SIZE_NOT_IN_WAVE';end if;
   select v.id into vid from erp.bf_sku_versions_v1 v join erp.bf_skus_v1 s on s.id=v.sku_id
     join erp.bf_sku_members_v1 m on m.version_id=v.id join erp.products p on p.id=m.product_root
     where s.id=sku and s.model_id=model and p.size_id=sid and v.effective_from<=g.cut_at and(v.effective_to is null or v.effective_to>g.cut_at);
   if vid is null then raise exception 'BF_SKU_SIZE_MODEL: SKU referensi harus memuat ukuran/model pada tanggal potong';end if;
   insert into erp.bf_wave_skus_v1 values(g.id,sid,sku,clock_timestamp(),erp.current_app_user_id(),p_request);
 end loop;
 if cardinality(seen)>0 and exists(select 1 from erp.cutting_group_size_slots where cutting_group_id=g.id and not(size_id=any(seen))) then
   raise exception 'BF_WAVE_COVERAGE: tentukan SKU referensi setiap ukuran wave';end if;
 insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
   values('cutting_groups',g.id,'UPDATE',p_payload,erp.current_app_user_id(),'Referensi tarif SKU per ukuran wave; bukan identitas FG');
 return jsonb_build_object('cutting_group_id',g.id,'revision',erp.bf_wave_revision_v1(g.id));
end;$function$;

CREATE OR REPLACE FUNCTION erp.bf_work_capacity_v1(p_group uuid,p_snapshot uuid,p_default bigint)
 RETURNS bigint LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select case when s.bf_sku_version_id is null then p_default else coalesce((
   select sum(y.qty_pcs)::bigint from erp.cutting_roll_yields y join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id
   join erp.cutting_group_size_slots slot on slot.id=y.size_slot_id
   join erp.bf_wave_skus_v1 w on w.cutting_group_id=r.cutting_group_id and w.size_id=slot.size_id
   where r.cutting_group_id=p_group and w.sku_id=v.sku_id),0) end
 from erp.po_work_component_snapshots s left join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id where s.id=p_snapshot
$function$;

CREATE OR REPLACE FUNCTION erp.bf_snapshot_sku_v1(p_snapshot uuid)
 RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select v.sku_id from erp.po_work_component_snapshots s join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id where s.id=p_snapshot
$function$;

CREATE OR REPLACE FUNCTION erp.bf_wave_revision_v1(p_group uuid)
 RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select md5(coalesce((select jsonb_agg(jsonb_build_array(size_id,sku_id,request_id) order by size_id)::text from erp.bf_wave_skus_v1 where cutting_group_id=p_group),'[]'))
$function$;

CREATE OR REPLACE FUNCTION erp.bf_group_sku_v1(p_group uuid,p_product uuid)
 RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select w.sku_id from erp.bf_wave_skus_v1 w join erp.products p on p.size_id=w.size_id where w.cutting_group_id=p_group and p.id=p_product
$function$;

CREATE OR REPLACE FUNCTION erp.bf_ensure_work_v1(p_po uuid,p_at timestamptz)
 RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare s record; base record; vid uuid; rate numeric; n integer:=0; contractor uuid;
begin
 select contractor_id into contractor from erp.production_orders where id=p_po for update;
 for s in select distinct w.sku_id from erp.bf_wave_skus_v1 w join erp.cutting_groups g on g.id=w.cutting_group_id where g.po_id=p_po loop
   -- First financial use pins the SKU version for the PO. Merely cutting/binding does not pin a tariff.
   select x.bf_sku_version_id into vid from erp.po_work_component_snapshots x join erp.bf_sku_versions_v1 v on v.id=x.bf_sku_version_id
     where x.po_id=p_po and v.sku_id=s.sku_id order by x.committed_at,x.id limit 1;
   if vid is not null then continue;end if;
   select id into vid from erp.bf_sku_versions_v1 where sku_id=s.sku_id and effective_from<=p_at and(effective_to is null or effective_to>p_at);
   if vid is null then raise exception 'BF_WORK_VERSION_MISSING';end if;
   for base in select * from erp.po_work_component_snapshots where po_id=p_po and bf_sku_version_id is null order by sequence_no,id loop
     select (r->>'rate')::numeric into rate from erp.bf_sku_versions_v1 v cross join lateral jsonb_array_elements(v.settings->'work_rates') r
       where v.id=vid and r->>'contractor_id'=contractor::text and r->>'work_component_id'=base.work_component_id::text;
     insert into erp.po_work_component_snapshots(po_id,work_component_id,source_bom_version_id,sequence_no,rate_per_pcs_snapshot,source_bom_item_id,source_contractor_rate_id,committed_at,bf_sku_version_id)
       values(p_po,base.work_component_id,base.source_bom_version_id,base.sequence_no,coalesce(rate,base.rate_per_pcs_snapshot),base.source_bom_item_id,
         case when rate is null then base.source_contractor_rate_id end,p_at,vid);
     n:=n+1;
   end loop;
 end loop;
 return n;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bf_snapshot_matches_v1(p_snapshot uuid,p_group uuid,p_product uuid)
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select case when erp.bf_group_sku_v1(p_group,p_product) is null then s.bf_sku_version_id is null
   else v.sku_id=erp.bf_group_sku_v1(p_group,p_product) end
 from erp.po_work_component_snapshots s left join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id where s.id=p_snapshot
$function$;

CREATE OR REPLACE FUNCTION erp.bf_assert_work_scope_v1(p_completion uuid,p_snapshot uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare e erp.work_completion_events%rowtype; sku uuid; version uuid;
begin
 select * into e from erp.work_completion_events where id=p_completion;
 select s.bf_sku_version_id,v.sku_id into version,sku from erp.po_work_component_snapshots s left join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id where s.id=p_snapshot;
 if version is not null and not exists(select 1 from erp.bf_wave_skus_v1 where cutting_group_id=e.cutting_group_id and sku_id=sku) then raise exception 'BF_WORK_OTHER_SKU';end if;
 if version is null and exists(select 1 from erp.bf_wave_skus_v1 where cutting_group_id=e.cutting_group_id) then raise exception 'BF_WORK_SCOPE_REQUIRED: pilih tarif SKU anggota wave';end if;
end;$function$;

CREATE OR REPLACE FUNCTION erp.save_sku_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare a text:=upper(btrim(p_action)); prior erp.bf_requests_v1%rowtype; result jsonb;
begin
 if erp.current_app_user_id() is null then raise exception 'BF_AUTH_REQUIRED';end if;
 if p_client_request_id is null then raise exception 'BF_REQUEST_REQUIRED';end if;
 if a not in('SAVE_GROUPS','BIND_WAVE') then raise exception 'BF_ACTION';end if;
 perform pg_advisory_xact_lock(hashtextextended('BFREQ:'||p_client_request_id::text,0));
 -- Permissions before cache, including replay following a live role change.
 if a='SAVE_GROUPS' then
   perform erp.require_owner_admin();perform erp.require_permission('master.product.manage');perform erp.require_permission('finance.hpp.manage');
 else perform erp.require_permission('production.cutting.edit_draft');end if;
 select * into prior from erp.bf_requests_v1 where request_id=p_client_request_id;
 if prior.request_id is not null then
   if prior.actor is distinct from erp.current_app_user_id() or prior.action<>a or prior.payload<>p_payload then raise exception 'BF_REQUEST_REUSED';end if;
   return prior.response||jsonb_build_object('replayed',true);
 end if;
 result:=case a when 'SAVE_GROUPS' then erp.bf_save_groups_v1(p_payload,p_client_request_id) else erp.bf_bind_wave_v1(p_payload,p_client_request_id) end;
 result:=result||jsonb_build_object('action',a,'request_id',p_client_request_id,'status','SAVED');
 insert into erp.bf_requests_v1 values(p_client_request_id,erp.current_app_user_id(),a,p_payload,result);
 return result;
end;$function$;

CREATE OR REPLACE FUNCTION erp.get_sku_workspace_v1(p_filters jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare page_no integer:=greatest(1,coalesce((p_filters->>'page')::integer,1)); q text:=coalesce(p_filters->>'query','');
 at_time timestamptz:=coalesce((p_filters->>'at')::timestamptz,statement_timestamp()); roots uuid[]; result jsonb; money boolean;
begin
 perform erp.require_permission('master.product.view');
 money:=erp.has_permission('finance.hpp.view') or erp.has_permission('finance.hpp.manage');
 select coalesce(array_agg(x::uuid),'{}') into roots from jsonb_array_elements_text(coalesce(p_filters->'roots','[]')) x;
 if cardinality(roots)>500 then raise exception 'BF_MEMBER_LIMIT';end if;
 if cardinality(roots)>0 and not money then raise exception 'BF_PRICE_PERMISSION';end if;
 with g as materialized(
   select s.*,v.id version_id,v.effective_from,v.effective_to,v.settings,b.brand_name,m.model_name,
     coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'size_id',p.size_id,'size',z.size_code) order by z.sort_order,z.size_code,p.id)
       from erp.bf_sku_members_v1 sm join erp.products p on p.id=sm.product_root join erp.sizes z on z.id=p.size_id
       where sm.version_id=v.id),'[]') members
   from erp.bf_skus_v1 s join erp.brands b on b.id=s.brand_id join erp.product_models m on m.id=s.model_id
   left join lateral(select x.* from erp.bf_sku_versions_v1 x where x.sku_id=s.id order by x.revision desc limit 1) v on true
   where s.sku ilike '%'||q||'%' or b.brand_name ilike '%'||q||'%'
 ), products as materialized(
   select p.id,p.sku,p.brand_id,b.brand_name,p.model_id,m.model_name,p.color_name,p.size_id,z.size_code size,
     (select v.sku_id from erp.bf_sku_members_v1 sm join erp.bf_sku_versions_v1 v on v.id=sm.version_id
       where sm.product_root=p.id and v.effective_from<=at_time and(v.effective_to is null or v.effective_to>at_time)) group_id
   from erp.products p join erp.brands b on b.id=p.brand_id join erp.product_models m on m.id=p.model_id join erp.sizes z on z.id=p.size_id
   where p.id=p.identity_root_id and p.is_active and (p.sku ilike '%'||q||'%' or b.brand_name ilike '%'||q||'%' or p.id=any(roots))
 ) select jsonb_build_object('at',at_time,'page',page_no,'page_size',50,'groups_total',(select count(*) from g),
   'groups',coalesce((select jsonb_agg(to_jsonb(x)) from(select id,sku,brand_id,brand_name,model_id,model_name,color_name,revision::text,version_id,
      effective_from,effective_to,members,case when money then settings end settings from g order by brand_name,sku,id limit 50 offset (page_no-1)*50)x),'[]'),
   'products_total',(select count(*) from products),'products',coalesce((select jsonb_agg(to_jsonb(x)) from(select * from products order by brand_name,sku,size,id limit 50 offset (page_no-1)*50)x),'[]'),
   'legacy_basis',case when money then erp.bf_legacy_basis_v1(roots,at_time) end,'can_edit',erp.has_permission('master.product.manage') and erp.has_permission('finance.hpp.manage') and erp.current_app_role() in('OWNER','ADMIN')) into result;
 return result;
end;$function$;

CREATE OR REPLACE FUNCTION erp.get_sku_hpp_v1(p_filters jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare at_time timestamptz:=coalesce((p_filters->>'at')::timestamptz,statement_timestamp()); result jsonb;
 page_no integer:=greatest(1,coalesce((p_filters->>'page')::integer,1));
begin
 perform erp.require_permission('finance.hpp.view');
 if at_time>statement_timestamp() then raise exception 'BF_REPORT_FUTURE';end if;
 with stock as materialized(
   select m.lot_id,m.product_id,m.location_id,m.quality_grade,sum(m.qty_signed)::bigint qty
   from erp.fg_stock_movements m where m.physical_at<=at_time
     and(nullif(p_filters->>'location_id','') is null or m.location_id=(p_filters->>'location_id')::uuid)
     and(nullif(p_filters->>'grade','') is null or m.quality_grade=p_filters->>'grade')
   group by m.lot_id,m.product_id,m.location_id,m.quality_grade having sum(m.qty_signed)<>0
 ), facts as materialized(
   select coalesce(s.id::text,p.brand_id::text||':'||p.sku) group_key,coalesce(s.sku,p.sku) sku,
     p.brand_id,b.brand_name,z.size_code size,st.*,l.lot_number,h.id hpp_version_id,h.cost_state,
     (st.qty*h.total_cost/nullif(h.qty_basis_pcs,0)) value,
     (h.id is null or h.cost_state='ESTIMATED' or erp.bd_lot_laundry_unknown_v1(l.id)) provisional
   from stock st join erp.fg_lots l on l.id=st.lot_id join erp.products p on p.id=st.product_id
   join erp.brands b on b.id=p.brand_id join erp.sizes z on z.id=p.size_id
   left join erp.bf_sku_versions_v1 v on v.id=erp.bf_version_at_v1(p.id,at_time)
   left join erp.bf_skus_v1 s on s.id=v.sku_id
   left join lateral(select x.* from erp.hpp_versions x where x.lot_id=l.id and x.calculated_at<=at_time order by x.calculated_at desc,x.version_no desc limit 1) h on true
 ), groups as materialized(
   select group_key,sku,brand_id,brand_name,sum(qty)::bigint qty,
     case when bool_and(value is not null) then sum(value) end value,bool_or(provisional) provisional,
     jsonb_agg(jsonb_build_object('lot_id',lot_id,'lot_number',lot_number,'product_id',product_id,'size',size,'location_id',location_id,
       'grade',quality_grade,'qty',qty,'value',value::text,'hpp_version_id',hpp_version_id,'cost_state',cost_state,'provisional',provisional)
       order by size,lot_number,location_id,quality_grade) lots
   from facts group by group_key,sku,brand_id,brand_name
 ), filtered as materialized(
   select * from groups where (nullif(p_filters->>'brand_id','') is null or brand_id=(p_filters->>'brand_id')::uuid)
     and (sku ilike '%'||coalesce(p_filters->>'query','')||'%' or brand_name ilike '%'||coalesce(p_filters->>'query','')||'%')
 ) select jsonb_build_object('at',at_time,'page',page_no,'page_size',50,'total',(select count(*) from filtered),
   'groups',coalesce((select jsonb_agg(to_jsonb(x)) from(select group_key,sku,brand_id,brand_name,qty,value::text,
     (value/nullif(qty,0))::text hpp_per_pcs,provisional,lots from filtered order by brand_name,sku,group_key limit 50 offset (page_no-1)*50)x),'[]')) into result;
 return result;
end;$function$;

CREATE OR REPLACE FUNCTION public.erp_save_sku_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
 RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path TO ''
AS $function$ select erp.save_sku_action_v1(p_action,p_payload,p_client_request_id) $function$;
CREATE OR REPLACE FUNCTION public.erp_get_sku_workspace_v1(p_filters jsonb DEFAULT '{}'::jsonb)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select erp.get_sku_workspace_v1(p_filters) $function$;
CREATE OR REPLACE FUNCTION public.erp_get_sku_hpp_v1(p_filters jsonb DEFAULT '{}'::jsonb)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select erp.get_sku_hpp_v1(p_filters) $function$;

CREATE OR REPLACE FUNCTION erp.commit_accessory_bom_for_lot(p_lot_id uuid)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  l erp.fg_lots%rowtype; p erp.production_orders%rowtype; v_product_model uuid; v_root uuid; v_bom uuid; v_distinct_boms integer;
begin
  perform erp.require_internal();
  select * into l from erp.fg_lots where id=p_lot_id for update;
  if l.id is null or l.lot_origin<>'PRODUCTION' then return null; end if;
  select * into p from erp.production_orders where id=l.po_id for update;
  if p.id is null then raise exception 'Production PO untuk lot FG tidak ditemukan'; end if;
  select model_id,identity_root_id into v_product_model,v_root from erp.products where id=l.product_id;
  if v_product_model is distinct from p.model_id then raise exception 'FG SKU model does not match production order model'; end if;

  select c.bom_version_id into v_bom from erp.po_accessory_bom_commitments c where c.po_id=l.po_id and c.product_id=l.product_id;
  if v_bom is not null then return v_bom; end if;

  select count(distinct c.bom_version_id) into v_distinct_boms
  from erp.po_accessory_bom_commitments c join erp.products cp on cp.id=c.product_id
  where c.po_id=l.po_id and cp.identity_root_id=v_root;
  if coalesce(v_distinct_boms,0)>1 then raise exception 'PO memiliki lebih dari satu accessory BOM commitment untuk logical SKU yang sama. Koreksi histori commitment sebelum membuat FG baru.'; end if;
  if coalesce(v_distinct_boms,0)=1 then
    select c.bom_version_id into v_bom from erp.po_accessory_bom_commitments c join erp.products cp on cp.id=c.product_id
    where c.po_id=l.po_id and cp.identity_root_id=v_root order by c.committed_at,c.id limit 1;
  else
    v_bom:=erp.bf_bom_for_lot_v1(p_lot_id);
    if v_bom is null then
    perform pg_advisory_xact_lock(hashtextextended('ABOM:'||v_root::text,0));
    select abv.id into v_bom from erp.accessory_bom_versions abv
    where abv.product_id=v_root and abv.is_active=true and abv.effective_from<=l.produced_at and (abv.effective_to is null or abv.effective_to>l.produced_at)
    order by abv.effective_from desc,abv.created_at desc,abv.id desc limit 1;
    end if;
    if v_bom is null then
      raise exception 'Accessory BOM SKU belum diset pada tanggal FG %. Setup BOM sebelum first HPP use. Jika produk memang tanpa aksesori, buat BOM version kosong sebagai deklarasi NO ACCESSORY.',l.produced_at;
    end if;
  end if;

  insert into erp.po_accessory_bom_commitments(po_id,product_id,bom_version_id,committed_at,commit_source,committed_by)
  values(l.po_id,l.product_id,v_bom,l.produced_at,'FIRST_FINANCIAL_USE',erp.current_app_user_id())
  on conflict (po_id,product_id) do nothing;
  select c.bom_version_id into v_bom from erp.po_accessory_bom_commitments c where c.po_id=l.po_id and c.product_id=l.product_id;
  return v_bom;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.ensure_po_work_component_snapshots(p_po_id uuid, p_basis_at timestamp with time zone DEFAULT statement_timestamp())
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  p erp.production_orders%rowtype;
  v_bom uuid;
  r record;
  v_rate_id uuid;
  v_rate numeric(18,2);
  v_count integer;
begin
  perform erp.require_internal();
  select * into p from erp.production_orders where id=p_po_id for update;
  if p.id is null then raise exception 'PO not found'; end if;
  if p.contractor_id is null then raise exception 'PO must have a mandor/contractor before work-rate snapshot'; end if;
  select count(*) into v_count from erp.po_work_component_snapshots where po_id=p.id and bf_sku_version_id is null;
  if v_count>0 then perform erp.bf_ensure_work_v1(p_po_id,p_basis_at);return v_count; end if;

  perform pg_advisory_xact_lock(hashtextextended('WBOM:'||p.model_id::text,0));
  select wbv.id into v_bom
  from erp.work_bom_versions wbv
  where wbv.model_id=p.model_id and wbv.is_active=true
    and wbv.effective_from<=p_basis_at and (wbv.effective_to is null or wbv.effective_to>p_basis_at)
    and exists(select 1 from erp.work_bom_items wbi where wbi.bom_version_id=wbv.id)
  order by wbv.effective_from desc,wbv.version_no desc,wbv.id desc limit 1;
  if v_bom is null then raise exception 'No active Work BOM for PO model at %',p_basis_at; end if;

  for r in select * from erp.work_bom_items where bom_version_id=v_bom order by sequence_no,id loop
    v_rate_id:=null; v_rate:=null;
    perform pg_advisory_xact_lock(hashtextextended('WRATE:'||p.contractor_id::text||':'||p.model_id::text||':'||r.work_component_id::text,0));
    select cwr.id,cwr.rate_per_pcs into v_rate_id,v_rate
    from erp.contractor_work_rates cwr
    where cwr.contractor_id=p.contractor_id and cwr.model_id=p.model_id and cwr.work_component_id=r.work_component_id
      and cwr.effective_from<=p_basis_at and (cwr.effective_to is null or cwr.effective_to>p_basis_at)
    order by cwr.effective_from desc,cwr.id desc limit 1;
    v_rate:=coalesce(v_rate,r.default_rate);
    if v_rate is null or v_rate<0 then raise exception 'No valid work rate for component %',r.work_component_id; end if;
    insert into erp.po_work_component_snapshots(
      po_id,work_component_id,source_bom_version_id,source_bom_item_id,source_contractor_rate_id,
      sequence_no,rate_per_pcs_snapshot,committed_at
    ) values(p.id,r.work_component_id,v_bom,r.id,v_rate_id,r.sequence_no,v_rate,p_basis_at);
  end loop;
  select count(*) into v_count from erp.po_work_component_snapshots where po_id=p.id and bf_sku_version_id is null;
  if v_count=0 then raise exception 'Work BOM snapshot produced no components'; end if;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('production_orders',p.id,'WORK_BOM_COMMIT',jsonb_build_object('bom_version_id',v_bom,'committed_at',p_basis_at,'component_count',v_count),erp.current_app_user_id(),'First work-rate/BOM use');
  perform erp.bf_ensure_work_v1(p_po_id,p_basis_at);
  return v_count;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.validate_work_completion()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  v_event_po uuid;
  v_event_contractor uuid;
  v_po_contractor uuid;
  v_snapshot_po uuid;
  v_snapshot_component uuid;
  v_snapshot_rate numeric(18,2);
begin
  perform erp.require_internal();
  select e.po_id,e.contractor_id into v_event_po,v_event_contractor
  from erp.work_completion_events e where e.id=new.completion_id for share of e;
  select p.contractor_id into v_po_contractor
  from erp.production_orders p where p.id=v_event_po;
  select s.po_id,s.work_component_id,s.rate_per_pcs_snapshot
  into v_snapshot_po,v_snapshot_component,v_snapshot_rate
  from erp.po_work_component_snapshots s where s.id=new.po_component_snapshot_id for share of s;
  if v_event_po is null then raise exception 'Completion event not found'; end if;
  if v_po_contractor is distinct from v_event_contractor then
    raise exception 'Completion contractor must match PO contractor';
  end if;
  if v_snapshot_po is distinct from v_event_po
     or v_snapshot_component is distinct from new.work_component_id
     or v_snapshot_rate is null then
    raise exception 'Work component snapshot does not match completion PO/component';
  end if;
  perform erp.bf_assert_work_scope_v1(new.completion_id,new.po_component_snapshot_id);
  new.rate_snapshot:=v_snapshot_rate;
  return new;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.guard_work_completion_posting_consistency()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_pickup timestamptz;
  v_effective bigint;
  r record;
  v_prior_completed bigint;
  v_prior_payable bigint;
  v_scope_capacity bigint;
begin
  if new.status='POSTED' and old.status is distinct from 'POSTED' then
    -- The DRAFT header may have changed after its lines were normalized.
    -- Recheck the current source before any work, payable or HPP is recognized.
    if not exists(select 1 from erp.production_orders ai_po
      where ai_po.id=new.po_id and ai_po.contractor_id=new.contractor_id) then
      raise exception 'AI_WORK_SOURCE_CONTRACTOR_MISMATCH';
    end if;
    perform 1 from erp.po_work_component_snapshots ai_snapshot
      join erp.work_completion_lines ai_line on ai_line.po_component_snapshot_id=ai_snapshot.id
      where ai_line.completion_id=new.id order by ai_snapshot.id for share of ai_snapshot;
    if exists(
      select 1 from erp.work_completion_lines ai_line
      left join erp.po_work_component_snapshots ai_snapshot on ai_snapshot.id=ai_line.po_component_snapshot_id
      where ai_line.completion_id=new.id and (
        ai_snapshot.id is null or ai_snapshot.po_id is distinct from new.po_id
        or ai_snapshot.work_component_id is distinct from ai_line.work_component_id
        or ai_snapshot.rate_per_pcs_snapshot is distinct from ai_line.rate_snapshot)
    ) then
      raise exception 'AI_WORK_SOURCE_SNAPSHOT_MISMATCH: rebuild the draft lines for the selected PO before posting';
    end if;

    if new.cutting_group_id is null then
      raise exception 'Hasil kerja mandor wajib terkait Potongan. Pilih Potongan sebelum posting agar qty/upah/HPP tidak masuk ke grup yang salah.';
    end if;

    -- Serialize all work postings for the same Potongan so two tabs cannot both
    -- consume the same remaining component entitlement concurrently.
    perform 1 from erp.cutting_groups cg where cg.id=new.cutting_group_id for update;
    if not found then raise exception 'Potongan sumber hasil kerja tidak ditemukan'; end if;

    select cg.picked_up_at,coalesce(v.total_pcs,0)
      into v_pickup,v_effective
    from erp.cutting_groups cg
    left join erp.v_cutting_group_totals v on v.cutting_group_id=cg.id
    where cg.id=new.cutting_group_id and cg.po_id=new.po_id;

    if v_pickup is null then
      raise exception 'Potongan belum diambil mandor. Hasil kerja/upah tidak boleh dipost sebelum assignment/pickup fisik.';
    end if;
    if new.physical_at < v_pickup then
      raise exception 'Tanggal hasil kerja (%) lebih awal dari tanggal Potongan diambil mandor (%). Periksa tanggal sebelum posting.',new.physical_at,v_pickup;
    end if;
    if new.physical_at > clock_timestamp()+interval '5 minutes' then
      raise exception 'Tanggal/jam hasil kerja berada di masa depan. Periksa tanggal/jam sebelum posting.';
    end if;
    if v_effective<=0 then
      raise exception 'Potongan tidak memiliki qty efektif yang dapat menjadi dasar upah.';
    end if;

    for r in
      select l.id,l.po_component_snapshot_id,l.work_component_id,l.qty_completed,l.qty_payable,wc.component_name
      from erp.work_completion_lines l
      join erp.work_components wc on wc.id=l.work_component_id
      where l.completion_id=new.id
      order by l.work_component_id,l.id
    loop
      perform erp.bf_assert_work_scope_v1(new.id,r.po_component_snapshot_id);
      v_scope_capacity:=erp.bf_work_capacity_v1(new.cutting_group_id,r.po_component_snapshot_id,v_effective);
      select coalesce(sum(l2.qty_completed),0),coalesce(sum(l2.qty_payable),0)
        into v_prior_completed,v_prior_payable
      from erp.work_completion_lines l2
      join erp.work_completion_events e2 on e2.id=l2.completion_id
      where e2.cutting_group_id=new.cutting_group_id
        and l2.work_component_id=r.work_component_id
        and erp.bf_snapshot_sku_v1(l2.po_component_snapshot_id) is not distinct from erp.bf_snapshot_sku_v1(r.po_component_snapshot_id)
        and e2.status='POSTED'
        and e2.id<>new.id;

      if v_prior_completed+r.qty_completed>v_scope_capacity then
        raise exception 'Qty selesai komponen % melebihi Potongan efektif. Potongan %, sudah dipost %, input %, maksimum %.',
          r.component_name,new.cutting_group_id,v_prior_completed,r.qty_completed,v_effective;
      end if;
      if v_prior_payable+r.qty_payable>v_scope_capacity then
        raise exception 'Qty bayar komponen % melebihi Potongan efektif. Sudah menjadi hak bayar %, input %, maksimum %. Koreksi hasil kerja, jangan membayar dua kali.',
          r.component_name,v_prior_payable,r.qty_payable,v_effective;
      end if;
    end loop;
  end if;
  return new;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.seed_bs_case_component_baseline()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
begin
  if new.po_id is null then return new; end if;
  insert into erp.bs_case_components(
    bs_case_id,po_component_snapshot_id,work_component_id,
    completed_before_bs_qty,notes
  )
  select
    new.id,s.id,s.work_component_id,
    least(
      new.qty_pcs,
      coalesce((
        select sum(wcl.qty_completed)::integer
        from erp.work_completion_lines wcl
        join erp.work_completion_events wce on wce.id=wcl.completion_id
        where wce.po_id=new.po_id
          and wcl.work_component_id=s.work_component_id
          and erp.bf_snapshot_sku_v1(wcl.po_component_snapshot_id) is not distinct from erp.bf_snapshot_sku_v1(s.id)
          and wce.status='POSTED'
          and wce.physical_at<=new.physical_at
          and (new.cutting_group_id is null or wce.cutting_group_id=new.cutting_group_id)
      ),0)
    ),
    'Auto baseline from posted work history at BS detection'
  from erp.po_work_component_snapshots s
  where s.po_id=new.po_id and erp.bf_snapshot_matches_v1(s.id,new.cutting_group_id,new.product_id)
  on conflict(bs_case_id,work_component_id) do nothing;
  return new;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.classify_bs_case_v2(p_bs_case_id uuid, p_payload jsonb, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;v_cached jsonb;v_response jsonb;
  v_case erp.bs_cases%rowtype;
  v_cause text;v_contractor uuid;v_vendor uuid;
  v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_component jsonb;v_snapshot uuid;
begin
  perform erp.require_internal();
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  if v_reason is null then raise exception 'change_reason is required'; end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'bs_case_id',p_bs_case_id,'payload',p_payload,'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin('classify_bs_case_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  select * into v_case from erp.bs_cases where id=p_bs_case_id for update;
  if v_case.id is null then raise exception 'BS case not found'; end if;
  if v_case.status not in('OPEN','PARTIAL','IN_REWORK') then raise exception 'Closed/cancelled BS case cannot be classified'; end if;
  if v_case.row_version<>p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_case.row_version;
  end if;
  v_cause:=upper(coalesce(nullif(p_payload->>'cause_source',''),v_case.cause_source));
  v_contractor:=case when p_payload?'responsible_contractor_id'
    then nullif(p_payload->>'responsible_contractor_id','')::uuid else v_case.responsible_contractor_id end;
  v_vendor:=case when p_payload?'responsible_vendor_id'
    then nullif(p_payload->>'responsible_vendor_id','')::uuid else v_case.responsible_vendor_id end;
  if v_cause='SEWING' and v_contractor is null then raise exception 'SEWING cause requires responsible contractor'; end if;
  if v_cause='LAUNDRY' and v_vendor is null then raise exception 'LAUNDRY cause requires responsible vendor'; end if;
  if v_cause not in('SEWING','LAUNDRY','UNKNOWN') then raise exception 'Invalid cause_source'; end if;
  perform set_config('app.change_reason',v_reason,true);
  update erp.bs_cases
  set cause_source=v_cause,responsible_contractor_id=v_contractor,
      responsible_vendor_id=v_vendor,
      untracked_type=case when v_cause='UNKNOWN' then untracked_type else null end,
      notes=case when p_payload?'notes' then nullif(btrim(p_payload->>'notes'),'') else notes end,
      legacy_reference=case when p_payload?'legacy_reference' then nullif(btrim(p_payload->>'legacy_reference'),'') else legacy_reference end,
      updated_at=statement_timestamp()
  where id=v_case.id returning * into v_case;

  if p_payload?'components' then
    if exists(
      select 1 from erp.rework_component_lines rcl
      join erp.bs_case_components bcc on bcc.id=rcl.bs_case_component_id
      where bcc.bs_case_id=v_case.id
    ) then raise exception 'BS components are frozen after rework lines exist'; end if;
    if jsonb_typeof(p_payload->'components')<>'array' then raise exception 'components must be an array'; end if;
    delete from erp.bs_case_components where bs_case_id=v_case.id;
    for v_component in select value from jsonb_array_elements(p_payload->'components') loop
      select id into v_snapshot from erp.po_work_component_snapshots
      where po_id=v_case.po_id and work_component_id=(v_component->>'work_component_id')::uuid
        and erp.bf_snapshot_matches_v1(id,v_case.cutting_group_id,v_case.product_id)
      order by committed_at desc,id desc limit 1;
      insert into erp.bs_case_components(
        bs_case_id,po_component_snapshot_id,work_component_id,completed_before_bs_qty,notes
      ) values(
        v_case.id,v_snapshot,(v_component->>'work_component_id')::uuid,
        coalesce(nullif(v_component->>'completed_before_bs_qty','')::integer,0),
        nullif(btrim(v_component->>'notes'),'')
      );
    end loop;
    update erp.bs_cases set updated_at=statement_timestamp() where id=v_case.id returning * into v_case;
  end if;
  v_response:=jsonb_build_object(
    'bs_case_id',v_case.id,'status',v_case.status,'cause_source',v_case.cause_source,
    'untracked_type',v_case.untracked_type,'legacy_reference',v_case.legacy_reference,
    'row_version',v_case.row_version,'component_count',(
      select count(*) from erp.bs_case_components where bs_case_id=v_case.id
    )
  );
  return erp._idempotency_complete('classify_bs_case_v2',p_client_request_id,v_response);
end
$function$;
CREATE OR REPLACE FUNCTION erp.cp6_lot_work_cost_v2620c(p_lot_id uuid,p_category text)
returns numeric
language sql
stable
security definer
set search_path=''
as $function$
with target as(
  select fl.id,fl.po_id,coalesce(fl.cutting_group_id,qi.cutting_group_id) group_id,
    fl.initial_qty_pcs::numeric lot_qty,fl.produced_at,fl.product_id
  from erp.fg_lots fl
  left join erp.qc_inspection_items qi on qi.id=fl.qc_item_id
  where fl.id=p_lot_id and fl.lot_origin='PRODUCTION'
), position as(
  select t.*,
    erp.bf_group_sku_v1(t.group_id,t.product_id) sku_id,
    coalesce((select sum(x.initial_qty_pcs)::numeric from erp.fg_lots x
      left join erp.qc_inspection_items xqi on xqi.id=x.qc_item_id
      where x.po_id=t.po_id and x.lot_origin='PRODUCTION'
        and coalesce(x.cutting_group_id,xqi.cutting_group_id)=t.group_id
        and erp.bf_group_sku_v1(t.group_id,x.product_id)=erp.bf_group_sku_v1(t.group_id,t.product_id)
        and (x.produced_at,x.id)<(t.produced_at,t.id)),0) sku_start,
    coalesce((select sum(x.initial_qty_pcs)::numeric from erp.fg_lots x
      left join erp.qc_inspection_items xqi on xqi.id=x.qc_item_id
      where x.po_id=t.po_id and x.lot_origin='PRODUCTION'
        and coalesce(x.cutting_group_id,xqi.cutting_group_id)=t.group_id
        and (x.produced_at,x.id)<(t.produced_at,t.id)),0) group_start,
    coalesce((select sum(x.initial_qty_pcs)::numeric from erp.fg_lots x
      where x.po_id=t.po_id and x.lot_origin='PRODUCTION'
        and (x.produced_at,x.id)<(t.produced_at,t.id)),0) po_start
  from target t
), source_lines as(
  select wce.cutting_group_id,wc.component_category,erp.bf_snapshot_sku_v1(wcl.po_component_snapshot_id) sku_id,wcl.qty_completed::numeric source_qty,
    wcl.amount_payable::numeric source_cost,
    coalesce(sum(wcl.qty_completed) over(
      partition by wce.po_id,wce.cutting_group_id,wcl.work_component_id,erp.bf_snapshot_sku_v1(wcl.po_component_snapshot_id)
      order by wce.physical_at,wce.id,wcl.id rows between unbounded preceding and 1 preceding
    ),0)::numeric source_start
  from position p
  join erp.work_completion_events wce on wce.po_id=p.po_id and wce.status='POSTED'
  join erp.work_completion_lines wcl on wcl.completion_id=wce.id
  join erp.work_components wc on wc.id=wcl.work_component_id
  where wc.component_category=case when upper(p_category)='COMMISSION' then 'COMMISSION' else wc.component_category end
    and (upper(p_category)='COMMISSION' or wc.component_category<>'COMMISSION')
    and (wce.cutting_group_id=p.group_id or wce.cutting_group_id is null)
)
select coalesce(sum(
  greatest(least(
    case when s.sku_id is not null then p.sku_start+p.lot_qty when s.cutting_group_id is null then p.po_start+p.lot_qty else p.group_start+p.lot_qty end,
    s.source_start+s.source_qty
  )-greatest(
    case when s.sku_id is not null then p.sku_start when s.cutting_group_id is null then p.po_start else p.group_start end,
    s.source_start
  ),0)*s.source_cost/nullif(s.source_qty,0)
),0)::numeric
from position p left join source_lines s on s.sku_id is null or s.sku_id=p.sku_id
$function$;
CREATE OR REPLACE FUNCTION erp.assert_new_stock_cutoff_coverage_v1()
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO ''
AS $function$
declare
  v_registry jsonb:='{"erp.accessory_bom_versions.product_id":{"class":"MASTER","reason":"Effective-dated accessory BOM; no stock instant"},"erp.bs_cases.product_id":{"class":"NEW_STOCK_FACT","reason":"physical_at of QC/laundry BS and manual OUT_OF_NOWHERE BS"},"erp.contractor_accessory_reimbursement_entitlements.product_id":{"class":"DERIVED","reason":"Accounting entitlement of an FG lot"},"erp.fg_accessory_cost_snapshots.product_id":{"class":"DERIVED","reason":"Cost snapshot of an FG lot"},"erp.fg_adjustment_items.product_id":{"class":"MOVEMENT","reason":"Adjusts an existing lot"},"erp.fg_inventory_balances.product_id":{"class":"DERIVED","reason":"Balance cache keyed by product/location/grade"},"erp.fg_lots.product_id":{"class":"NEW_STOCK_FACT","reason":"produced_at of every lot except GOOD returned by rework"},"erp.fg_stock_movements.product_id":{"class":"MOVEMENT","reason":"Movement of an existing lot"},"erp.bb_opening_sale_return_rights_v1.product_id":{"class":"SOURCE_DOCUMENT","reason":"Return right of an old invoice; the stock fact is the RETURN lot in fg_lots, validated as NEW_STOCK at receipt"},"erp.bb_opening_sale_return_receipts_v1.product_id":{"class":"DERIVED","reason":"Provenance of a return receipt; the stock fact is its fg_lots lot"},"erp.bb_wip_bs_splits_v1.product_id":{"class":"DERIVED","reason":"Provenance of an opening WIP BS split; the stock fact is its bs_cases row (NEW_STOCK_FACT at its physical_at)"},"erp.bb_open_sales_draft_lines_v1.product_id":{"class":"DERIVED","reason":"Provenance of a sales draft open at cutover; the sale is its native sales_items line (reservation of existing stock)"},"erp.be_pocket_sewing_v1.product_id":{"class":"SOURCE_DOCUMENT","reason":"Evidence of a sold SKU before cutover; no new stock identity is created"},"erp.be_rework_targets_v1.target_product_id":{"class":"SOURCE_DOCUMENT","reason":"Requested rework/redye target; checked as NEW_STOCK when the native GOOD lot is converted atomically"},"erp.bc_customer_custody_v1.product_id":{"class":"SOURCE_DOCUMENT","reason":"A customer-owned garment in service (ACC-C10); never company stock, no stock fact"},"erp.initial_import_wip_output_identity_v1.opening_product_id":{"class":"DERIVED","reason":"Provenance of an opening WIP output: the product filled in on its opening item"},"erp.initial_import_wip_output_identity_v1.output_product_id":{"class":"DERIVED","reason":"Provenance of an opening WIP output; the stock fact is its fg_lots lot"},"erp.journal_lines.product_id":{"class":"ACCOUNTING","reason":"Journal dimension"},"erp.laundry_receipt_batch_size_lines.bs_product_id":{"class":"SOURCE_DOCUMENT","reason":"Laundry receipt input; the BS fact is bs_cases"},"erp.laundry_receipt_bs_product_allocations.product_id":{"class":"SOURCE_DOCUMENT","reason":"Validated as NEW_STOCK; the BS fact is bs_cases"},"erp.non_po_hpp_gl_sync_events_v2620f.product_id":{"class":"ACCOUNTING","reason":"HPP to GL synchronisation event"},"erp.opening_balance_items.product_id":{"class":"SOURCE_DOCUMENT","reason":"Opening document; facts are OPENING lots and LEGACY BS"},"erp.po_accessory_bom_commitments.product_id":{"class":"MASTER","reason":"PO accessory BOM commitment"},"erp.product_conversions.from_product_id":{"class":"SOURCE_DOCUMENT","reason":"Conversion source, validated as EXISTING_STOCK"},"erp.product_conversions.to_product_id":{"class":"SOURCE_DOCUMENT","reason":"Conversion target; the fact is the CONVERSION lot in fg_lots"},"erp.product_identity_mutation_context_v1.product_id":{"class":"AUTHORIZATION","reason":"Private one-use identity edit context"},"erp.product_price_versions.product_id":{"class":"MASTER","reason":"Effective-dated price"},"erp.qc_inspection_items.final_product_id":{"class":"SOURCE_DOCUMENT","reason":"QC input; the facts are fg_lots and bs_cases"},"erp.sales_items.product_id":{"class":"SALES","reason":"Sale of existing stock"},"erp.sales_return_items.product_id":{"class":"SALES","reason":"Return of sold stock"},"erp.stock_explainability_snapshots.product_id":{"class":"REPORT","reason":"Stock explanation snapshot"},"erp.stock_policy_versions.product_id":{"class":"MASTER","reason":"Effective-dated stock policy"}}';
  v_helper_tables text[]:=array['bs_case_manual_origins_v1','bs_cases','fg_lots','rework_orders'];
  v_actual text[];
  v_unclassified text[];
  v_stale text[];
  v_facts text[];
  v_helper text[];
begin
  v_registry:=v_registry||'{"erp.bf_sku_members_v1.product_root":{"class":"MASTER","reason":"Commercial SKU membership; exact physical root is preserved"}}'::jsonb;
  -- Structural catalog read: any FK to erp.products in any schema, plus any
  -- product-named uuid column in erp/public that no FK protects.
  select array_agg(distinct ref order by ref) into v_actual from (
    select format('%s.%s.%s',n.nspname,c.relname,a.attname) ref
    from pg_constraint fk join pg_class c on c.oid=fk.conrelid
    join pg_namespace n on n.oid=c.relnamespace
    join pg_attribute a on a.attrelid=c.oid and a.attnum=any(fk.conkey)
    where fk.contype='f' and fk.confrelid='erp.products'::regclass and fk.conrelid<>'erp.products'::regclass
    union
    select format('%s.%s.%s',n.nspname,c.relname,a.attname)
    from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace
    where n.nspname in('erp','public') and c.relkind in('r','p') and c.oid<>'erp.products'::regclass
      and a.attnum>0 and not a.attisdropped and a.atttypid='uuid'::regtype
      and (a.attname='product_id' or a.attname like '%\_product\_id')
  ) r;
  select array_agg(k order by k) into v_unclassified from unnest(v_actual) k where not v_registry ? k;
  if v_unclassified is not null then
    raise exception 'NEW_STOCK_CUTOFF_REFERENCE_UNCLASSIFIED: %',array_to_string(v_unclassified,', ');
  end if;
  select array_agg(k order by k) into v_stale from jsonb_object_keys(v_registry) k where k<>all(v_actual);
  if v_stale is not null then
    raise exception 'NEW_STOCK_CUTOFF_REGISTRY_STALE: %',array_to_string(v_stale,', ');
  end if;
  select array_agg(distinct split_part(key,'.',2) order by split_part(key,'.',2)) into v_facts
  from jsonb_each(v_registry) where value->>'class'='NEW_STOCK_FACT';
  select array_agg(distinct m[1] order by m[1]) into v_helper
  from pg_proc p cross join lateral regexp_matches(lower(p.prosrc),'erp\.([a-z0-9_]+)','g') m
  where p.oid='erp.latest_new_stock_physical_at_v1(uuid)'::regprocedure;
  if v_helper is null or not (v_helper @> v_helper_tables and v_helper <@ v_helper_tables and v_helper @> v_facts) then
    raise exception 'NEW_STOCK_CUTOFF_HELPER_SCOPE_DRIFT: %',v_helper;
  end if;
  if lower((select p.prosrc from pg_proc p where p.oid='erp.edit_product_identity_effective(uuid,text,uuid,uuid,text,uuid,text,timestamp with time zone,text)'::regprocedure))
     !~ 'erp\.latest_new_stock_physical_at_v1\s*\(' then
    raise exception 'NEW_STOCK_CUTOFF_CONSUMER_DRIFT';
  end if;
  return jsonb_build_object('references',coalesce(array_length(v_actual,1),0),'new_stock_fact_tables',v_facts,'registry',v_registry);
end;
$function$;

do $grants$ declare t text;f record;begin
 foreach t in array ARRAY['bf_skus_v1','bf_sku_versions_v1','bf_sku_members_v1','bf_wave_skus_v1','bf_po_boms_v1','bf_requests_v1','bf_context_v1'] loop
   execute format('alter table erp.%I enable row level security',t);
   execute format('revoke all on erp.%I from public,anon,authenticated,service_role',t);
 end loop;
 for f in select p.oid::regprocedure sig,n.nspname from pg_proc p join pg_namespace n on n.oid=p.pronamespace
   where (n.nspname='erp' and(p.proname like 'bf\_%' or p.proname in('save_sku_action_v1','get_sku_workspace_v1','get_sku_hpp_v1')))
     or (n.nspname='public' and p.proname in('erp_save_sku_action_v1','erp_get_sku_workspace_v1','erp_get_sku_hpp_v1')) loop
   execute format('revoke all on function %s from public,anon,authenticated,service_role',f.sig);
   if f.nspname='public' then execute format('grant execute on function %s to authenticated,service_role',f.sig);end if;
 end loop;
end $grants$;

insert into erp.schema_migrations(version,description) values('v2.6.20bf','Commercial SKU ranges; physical-size lineage preserved');
commit;
