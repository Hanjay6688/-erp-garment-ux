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
 if exists(select 1 from erp.bf_sku_members_v1 where product_root in(select identity_root_id from erp.products where id in(r,previous_root))) then
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
     if exists(select 1 from erp.po_work_component_snapshots where bf_sku_version_id=current_v.id and committed_at>=at_time)
       or exists(select 1 from erp.bd_laundry_charge_lines_v1 c join erp.laundry_delivery_lines l on l.id=c.delivery_line_id
         join erp.laundry_deliveries d on d.id=l.delivery_id where c.bf_sku_version_id=current_v.id and d.physical_at>=at_time)
       or exists(select 1 from erp.rework_component_lines c join erp.rework_orders o on o.id=c.rework_order_id
         where c.bf_sku_version_id=current_v.id and o.physical_sent_at>=at_time) then
       raise exception 'BF_TARIFF_HISTORY: waktu perubahan mendahului pemakaian tarif yang sudah tercatat';end if;
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
   perform erp._cp3_assert_closed_json_object(cfg,array['work_rates','laundry_rates'],array['price','bom','work_rates','laundry_rates'],'SKU settings');
   if not (cfg ?& array['price','bom']) then raise exception 'BF_SETTINGS_MISSING: harga/resep wajib disebut, boleh belum diisi';end if;
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
