-- BF development family. NOT_READY until complete qualification. Generated; do not edit.
begin;set local search_path='';set local lock_timeout='10s';set local statement_timeout='240s';
do $guard$ begin if not exists(select 1 from erp.schema_migrations where version='v2.6.20be') then raise exception 'BF_REQUIRES_BE';end if;
if exists(select 1 from erp.schema_migrations where version='v2.6.20bf') then raise exception 'BF_ALREADY_INSTALLED';end if;end $guard$;

create table erp.bf_rollback_v1(payload jsonb not null);
insert into erp.bf_rollback_v1(payload)
select jsonb_build_object('functions',(select jsonb_object_agg(s,pg_get_functiondef(s::regprocedure)) from unnest(array['erp.commit_accessory_bom_for_lot(uuid)','erp.ensure_po_work_component_snapshots(uuid,timestamp with time zone)','erp.validate_work_completion()','erp.guard_work_completion_posting_consistency()','erp.seed_bs_case_component_baseline()','erp.classify_bs_case_v2(uuid,jsonb,uuid,bigint)','erp.cp6_lot_work_cost_v2620c(uuid,text)','erp.assert_new_stock_cutoff_coverage_v1()','erp.bd_compute_pricing_v1(jsonb,jsonb)','erp.bd_attach_delivery_pricing_v1(uuid)','erp.bd_post_priced_delivery_v1(jsonb,uuid)','erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)','erp.prepare_rework_component_line()','erp.run_v263c_bs_rework_integrity_checks()','erp.get_hpp_completeness(uuid)','erp.save_initial_import_action_v1(text,jsonb,uuid)','erp.bb_check_sales_import_row_v1(uuid,uuid)','erp.bb_apply_sales_imports_v1(uuid)','erp.bc_check_import_row_v1(uuid,uuid)','erp.bc_apply_imports_v1(uuid)','erp.be_check_pocket_import_v1(uuid,uuid)','erp.be_apply_pocket_imports_v1(uuid)','erp.bb_check_rework_import_row_v1(uuid,uuid)']) s),
 'snapshot_constraint',(select pg_get_constraintdef(oid) from pg_constraint where conrelid='erp.po_work_component_snapshots'::regclass and conname='po_work_component_snapshots_po_id_work_component_id_key'),
 'rework_constraint',(select pg_get_constraintdef(oid) from pg_constraint where conrelid='erp.rework_component_lines'::regclass and conname='rework_component_lines_rate_basis_check'));

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

CREATE OR REPLACE FUNCTION erp.bf_validate_rates_v1(p_sku uuid,p_settings jsonb)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare j jsonb; k text; ref uuid; vendor uuid; amount numeric; seen text[]:='{}'; key text;
begin
 for j in select value from jsonb_array_elements(p_settings->'work_rates') loop
   perform erp._cp3_assert_closed_json_object(j,array['work_component_id','rate'],array['contractor_id','work_component_id','rate','special'],'SKU work rate');
   vendor:=erp.bd_uuid_v1(j,'contractor_id',false);ref:=erp.bd_uuid_v1(j,'work_component_id',true);
   if (vendor is not null and not exists(select 1 from erp.contractors where id=vendor and is_active))
     or not exists(select 1 from erp.work_components where id=ref and is_active) then raise exception 'BF_WORK_RATE_REFERENCE';end if;
   if j ? 'special' and jsonb_typeof(j->'special') is distinct from 'boolean' then raise exception 'BF_SPECIAL_FLAG';end if;
   perform erp.bd_amount_v1(j->'rate','rate',true);key:=coalesce(vendor::text,'*')||':'||ref::text||':'||coalesce(j->>'special','false');
   if key=any(seen) then raise exception 'BF_DUPLICATE_RATE';end if;seen:=seen||key;
 end loop;
 seen:='{}';
 for j in select value from jsonb_array_elements(p_settings->'laundry_rates') loop
   perform erp._cp3_assert_closed_json_object(j,array['vendor_id','kind','ref_id','rate_status'],
     array['vendor_id','kind','ref_id','rate_status','rate','reason'],'SKU laundry rate');
   if not(j ?& array['rate','reason']) then raise exception 'BF_RATE_FIELDS';end if;
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

-- SKU base rate applies to every member size. Optional contractor/special overrides are still per SKU.
CREATE OR REPLACE FUNCTION erp.bf_work_rate_v1(p_version uuid,p_contractor uuid,p_component uuid,p_at timestamptz)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select (r->>'rate')::numeric from erp.bf_sku_versions_v1 v cross join lateral jsonb_array_elements(v.settings->'work_rates') r
 where v.id=p_version and r->>'work_component_id'=p_component::text
   and (r->>'contractor_id' is null or r->>'contractor_id'=p_contractor::text)
   and (not coalesce((r->>'special')::boolean,false) or exists(select 1 from erp.contractor_hpp_policy_versions pol
     where pol.contractor_id=p_contractor and pol.is_special and pol.effective_from<=erp._cp3_business_date(p_at)
       and (pol.effective_to is null or pol.effective_to>=erp._cp3_business_date(p_at))))
 order by (r->>'contractor_id' is not null) desc,coalesce((r->>'special')::boolean,false) desc limit 1
$function$;

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
 if bom is null then
   if exists(select 1 from erp.bf_sku_members_v1 where version_id=pinned and product_root=root) then
     raise exception 'BF_BOM_UNCONFIGURED: tentukan resep SKU (termasuk tanpa aksesori bila benar) sebelum penggunaan biaya';
   end if;
   raise exception 'BF_PO_NEW_MEMBER: ukuran baru tidak termasuk resep PO yang telah disepakati';
 end if;
 return bom;
end;$function$;

-- A wave can contain several ranges. Its reference chooses rates, never final FG identity.
alter table erp.rework_component_lines add column bf_sku_version_id uuid references erp.bf_sku_versions_v1(id);
alter table erp.rework_component_lines drop constraint rework_component_lines_rate_basis_check;
alter table erp.rework_component_lines add constraint rework_component_lines_rate_basis_check
 check(rate_basis in('CONTRACTOR_RATE','PO_SNAPSHOT','LAUNDRY_ZERO','LEGACY_CLIENT','SKU_RATE'));

CREATE OR REPLACE FUNCTION erp.bf_bind_wave_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare g erp.cutting_groups%rowtype; r jsonb; sid uuid; v_sku uuid; vid uuid; model uuid; seen uuid[]:='{}'; before_hash text;
begin
 perform erp._cp3_assert_closed_json_object(p_payload,array['cutting_group_id','references','expected_version'],array['cutting_group_id','references','expected_version'],'wave SKU references');
 perform pg_advisory_xact_lock(hashtextextended('BF:COMMERCIAL_SKUS',0));
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
   v_sku:=erp.bd_uuid_v1(r,'sku_id',true);sid:=erp.bd_uuid_v1(r,'size_id',true);
   if sid=any(seen) then raise exception 'BF_DUPLICATE_SIZE';end if;seen:=seen||sid;
   if not exists(select 1 from erp.cutting_group_size_slots where cutting_group_id=g.id and size_id=sid) then raise exception 'BF_SIZE_NOT_IN_WAVE';end if;
   select v.id into vid from erp.bf_sku_versions_v1 v join erp.bf_skus_v1 s on s.id=v.sku_id
     join erp.bf_sku_members_v1 m on m.version_id=v.id join erp.products p on p.id=m.product_root
     where s.id=v_sku and s.model_id=model and p.size_id=sid and v.effective_from<=statement_timestamp() and(v.effective_to is null or v.effective_to>statement_timestamp());
   if vid is null then raise exception 'BF_SKU_SIZE_MODEL: SKU referensi harus memuat ukuran/model saat dipilih';end if;
   insert into erp.bf_wave_skus_v1 values(g.id,sid,v_sku,clock_timestamp(),erp.current_app_user_id(),p_request);
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
 select case when p_product is null then
   (select min(w.sku_id::text)::uuid from erp.bf_wave_skus_v1 w where w.cutting_group_id=p_group having count(distinct w.sku_id)=1)
 else (select w.sku_id from erp.bf_wave_skus_v1 w join erp.products p on p.size_id=w.size_id where w.cutting_group_id=p_group and p.id=p_product) end
$function$;

CREATE OR REPLACE FUNCTION erp.bf_ensure_work_v1(p_po uuid,p_at timestamptz)
 RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare s record; base record; vid uuid; rate numeric; n integer:=0; contractor uuid;
begin
 perform pg_advisory_xact_lock(hashtextextended('BF:COMMERCIAL_SKUS',0));
 select contractor_id into contractor from erp.production_orders where id=p_po for update;
 for s in select distinct w.sku_id from erp.bf_wave_skus_v1 w join erp.cutting_groups g on g.id=w.cutting_group_id where g.po_id=p_po loop
   -- First financial use pins the SKU version for the PO. Merely cutting/binding does not pin a tariff.
   select x.bf_sku_version_id into vid from erp.po_work_component_snapshots x join erp.bf_sku_versions_v1 v on v.id=x.bf_sku_version_id
     where x.po_id=p_po and v.sku_id=s.sku_id order by x.committed_at,x.id limit 1;
   if vid is not null then continue;end if;
   select id into vid from erp.bf_sku_versions_v1 where sku_id=s.sku_id and effective_from<=p_at and(effective_to is null or effective_to>p_at);
   if vid is null then raise exception 'BF_WORK_VERSION_MISSING';end if;
   for base in select * from erp.po_work_component_snapshots where po_id=p_po and bf_sku_version_id is null order by sequence_no,id loop
     rate:=erp.bf_work_rate_v1(vid,contractor,base.work_component_id,p_at);
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
 select case when erp.bf_group_sku_v1(p_group,p_product) is null then s.bf_sku_version_id is null and not exists(select 1 from erp.bf_wave_skus_v1 w where w.cutting_group_id=p_group)
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

alter table erp.bd_laundry_charge_lines_v1 add column bf_sku_version_id uuid references erp.bf_sku_versions_v1(id);

-- A rate reference follows the wave size, not the final FG product. The returned business version is frozen on the charge.
CREATE OR REPLACE FUNCTION erp.bf_laundry_rate_v1(p_kind text,p_ref uuid,p_vendor uuid,p_group uuid,p_size uuid,p_at timestamptz)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare sku uuid;vid uuid;r jsonb;fallback record;reason text;amount numeric;
begin
 select sku_id into sku from erp.bf_wave_skus_v1 where cutting_group_id=p_group and size_id=p_size;
 if sku is not null then
   select id into vid from erp.bf_sku_versions_v1 where sku_id=sku and effective_from<=p_at and(effective_to is null or effective_to>p_at);
   if vid is null then raise exception 'BF_TARIFF_NOT_EFFECTIVE: referensi SKU belum berlaku pada tanggal jasa';end if;
   select j into r from erp.bf_sku_versions_v1 v cross join lateral jsonb_array_elements(v.settings->'laundry_rates') j
     where v.id=vid and j->>'kind'=p_kind and j->>'ref_id'=p_ref::text and j->>'vendor_id'=p_vendor::text;
   if r is not null then return r||jsonb_build_object('sku_version_id',vid,'version_id',null);end if;
 end if;
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

-- One physical identity for every historical row. Never distribute an imported aggregate.
CREATE OR REPLACE FUNCTION erp.bf_resolve_import_product_v1(p_batch uuid,p_value jsonb,p_allow_staged boolean DEFAULT false,p_optional boolean DEFAULT false)
 RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_at timestamptz;v_ids uuid[];v_count integer;v_staged integer;v_id uuid;v_key text;
begin
 select cutover_at into strict v_at from erp.migration_batches where id=p_batch;
 if nullif(btrim(p_value->>'product_sku'),'') is null and nullif(btrim(p_value->>'product_id'),'') is null then
   if p_optional then return null;end if;raise exception 'BF_IMPORT_PRODUCT_REQUIRED';
 end if;
 v_id:=erp.bd_uuid_v1(p_value,'product_id',false);
 select coalesce(array_agg(p.id),'{}') into v_ids from erp.products p
 join erp.brands b on b.id=p.brand_id join erp.product_models m on m.id=p.model_id join erp.sizes z on z.id=p.size_id
 where p.effective_from<=v_at and (v_id is null or p.id=v_id)
   and (nullif(btrim(p_value->>'product_sku'),'') is null or lower(btrim(p.sku))=lower(btrim(p_value->>'product_sku')))
   and (nullif(btrim(p_value->>'size_code'),'') is null or lower(btrim(z.size_code))=lower(btrim(p_value->>'size_code')))
   and (nullif(btrim(p_value->>'brand_code'),'') is null or lower(btrim(b.brand_code))=lower(btrim(p_value->>'brand_code')))
   and (nullif(btrim(p_value->>'model_code'),'') is null or lower(btrim(m.model_code))=lower(btrim(p_value->>'model_code')))
   and (nullif(btrim(p_value->>'color_name'),'') is null or lower(btrim(p.color_name))=lower(btrim(p_value->>'color_name')));
 v_count:=cardinality(v_ids);v_staged:=0;
 if p_allow_staged and v_id is null then
   select count(*) into v_staged from erp.migration_staging_rows s
   where s.batch_id=p_batch and s.entity_type='PRODUCT' and s.validation_status='VALID'
     and lower(btrim(s.normalized_payload->>'sku'))=lower(btrim(p_value->>'product_sku'))
     and not exists(select 1 from unnest(array['size_code','brand_code','model_code','color_name']) k
       where nullif(btrim(p_value->>k),'') is not null and lower(btrim(s.normalized_payload->>k)) is distinct from lower(btrim(p_value->>k)))
     and not exists(select 1 from erp.products p join erp.brands b on b.id=p.brand_id join erp.product_models m on m.id=p.model_id join erp.sizes z on z.id=p.size_id
       where p.id=any(v_ids) and lower(btrim(b.brand_code))=lower(btrim(s.normalized_payload->>'brand_code'))
       and lower(btrim(m.model_code))=lower(btrim(s.normalized_payload->>'model_code')) and lower(btrim(z.size_code))=lower(btrim(s.normalized_payload->>'size_code'))
       and lower(btrim(p.color_name))=lower(btrim(s.normalized_payload->>'color_name')));
 end if;
 if v_count+v_staged=0 then raise exception 'BF_IMPORT_PRODUCT_NOT_FOUND: identitas fisik tidak cocok pada cutover';end if;
 if v_count+v_staged<>1 then raise exception 'SIZE_ALLOCATION_REQUIRED: SKU punya % identitas; isi product_id atau size_code/merek/model/warna sumber historis',v_count+v_staged;end if;
 return v_ids[1];
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
   where s.sku ilike '%'||q||'%' or b.brand_name ilike '%'||q||'%' or exists(select 1 from erp.bf_sku_members_v1 sm where sm.version_id=v.id and sm.product_root=any(roots))
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
   'related_groups',coalesce((select jsonb_agg(to_jsonb(x)) from(select id,sku,brand_id,brand_name,model_id,model_name,color_name,revision::text,version_id,effective_from,effective_to,members,case when money then settings end settings from g
     where exists(select 1 from jsonb_array_elements(members) mem where (mem->>'id')::uuid=any(roots)))x),'[]'),
   'selected_products',coalesce((select jsonb_agg(to_jsonb(x)) from products x where id=any(roots)),'[]'),
   'lookups',case when money then jsonb_build_object(
     'accessories',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',category_name,'unit',base_uom_code) order by category_name,id) from erp.accessory_categories where is_active),'[]'),
     'work',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',component_name,'category',component_category) order by sequence_default,id) from erp.work_components where is_active),'[]'),
     'contractors',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',contractor_name) order by contractor_name,id) from erp.contractors where is_active),'[]'),
     'vendors',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',vendor_name) order by vendor_name,id) from erp.laundry_vendors where is_active),'[]'),
     'laundry',coalesce((select jsonb_agg(to_jsonb(x)) from(
       select id,process_name name,'PROCESS' kind,null::uuid vendor_id from erp.wash_processes where is_active
       union all select id,component_name,'COMPONENT',vendor_id from erp.bd_laundry_components_v1 where is_active
       union all select id,package_name,'PACKAGE',vendor_id from erp.bd_laundry_packages_v1 where is_active)x),'[]')) end,
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
     (h.id is null or h.cost_state='ESTIMATED' or erp.bd_lot_laundry_unknown_v1(l.id) or (l.po_id is not null and exists(select 1 from erp.get_hpp_completeness(l.po_id) c where c.pending_reason_count>0))) provisional
   from stock st join erp.fg_lots l on l.id=st.lot_id join erp.products p on p.id=st.product_id
   join erp.brands b on b.id=p.brand_id join erp.sizes z on z.id=p.size_id
   left join erp.bf_sku_versions_v1 v on v.id=erp.bf_version_at_v1(p.id,at_time)
   left join erp.bf_skus_v1 s on s.id=v.sku_id
   left join lateral(select x.* from erp.hpp_versions x where x.lot_id=l.id and x.calculated_at<=at_time order by x.calculated_at desc,x.version_no desc limit 1) h on true
 ), groups as materialized(
   select group_key,sku,brand_id,brand_name,sum(qty)::bigint qty,
     case when bool_and(value is not null) then sum(value) end value,bool_or(provisional) provisional,
     jsonb_agg(jsonb_build_object('lot_id',lot_id,'lot_number',lot_number,'product_id',product_id,'size',size,'location_id',location_id,
       'grade',quality_grade,'qty',qty::text,'value',value::text,'hpp_version_id',hpp_version_id,'cost_state',cost_state,'provisional',provisional)
       order by size,lot_number,location_id,quality_grade) lots
   from facts group by group_key,sku,brand_id,brand_name
 ), filtered as materialized(
   select * from groups where (nullif(p_filters->>'brand_id','') is null or brand_id=(p_filters->>'brand_id')::uuid)
     and (sku ilike '%'||coalesce(p_filters->>'query','')||'%' or brand_name ilike '%'||coalesce(p_filters->>'query','')||'%')
 ) select jsonb_build_object('at',at_time,'page',page_no,'page_size',50,'total',(select count(*) from filtered),
   'groups',coalesce((select jsonb_agg(to_jsonb(x)) from(select group_key,sku,brand_id,brand_name,qty::text,value::text,
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

    -- BB (ALL-W02): wages after cutover on an opening WIP (no Potongan) have that opening WIP as their source.
    if new.cutting_group_id is null and new.bb_opening_item_id is not null then
      perform erp.bb_check_opening_work_v1(new.id);
      return new;
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
  v_status text;v_label text;v_kind text;bf_group uuid;bf_rate jsonb;
begin
  select * into t from erp.bd_laundry_vendor_terms_v1 where vendor_id=v_vendor;
  v_mode:=coalesce(t.pricing_mode,'RATE');v_unit:=coalesce(t.pricing_unit,'PCS');
  select po.model_id,g.id into v_model,bf_group from erp.cutting_distribution_batches b join erp.cutting_pickups p on p.id=b.pickup_id
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
      bf_rate:=null;
      if exists(select 1 from erp.bf_wave_skus_v1 where cutting_group_id=bf_group and size_id=v_sizeids[i]) then
        bf_rate:=erp.bf_laundry_rate_v1('PROCESS',v_process,v_vendor,bf_group,v_sizeids[i],v_at);
        v_rate:=(bf_rate->>'rate')::numeric;v_kind:='RATE';v_label:='Tarif bersama SKU';
      else
      select * into v_scoped from erp.bd_scoped_rate_at_v1(v_vendor,v_process,v_model,v_sizeids[i],v_color,v_at);
      if v_scoped.rate_per_pcs is not null then
        v_rate:=v_scoped.rate_per_pcs;v_kind:='SCOPED_RATE';v_label:='Tarif khusus '||v_scoped.scope;v_mode:='SCOPED';
        v_versions:=v_versions||jsonb_build_object('LAU_DEC05',erp.bd_policy_version_v1('LAU_DEC05'));
      else
        if v_dec05 is not null and v_dec05->>'fallback'='REFUSE' then
          raise exception 'BD_SCOPED_RATE_MISSING: tidak ada tarif khusus untuk ukuran ini dan LAU-DEC05 menolak tarif dasar';end if;
        v_rate:=erp.bd_process_rate_at_v1(v_vendor,v_process,v_at);v_kind:='RATE';v_label:='Tarif dasar vendor/proses';
      end if;
      end if;
      v_amount:=round(v_qtys[i]*v_rate,2);
      v_charges:=v_charges||jsonb_build_object('kind',v_kind,'ref_id',case when bf_rate is not null then v_process else v_scoped.rate_id end,'version_id',case when bf_rate is not null then (bf_rate->>'version_id')::uuid else v_scoped.rate_id end,'bf_sku_version_id',bf_rate->'sku_version_id','label',v_label,'covered_qty',v_qtys[i],
        'rate_status','KNOWN','unit_rate',v_rate::text,'amount',v_amount::text,
        'shares',jsonb_build_array(jsonb_build_object('size_id',v_sizeids[i],'amount',v_amount::text)));
      v_known:=v_known+v_amount;
    end loop;
  elsif v_mode='PACKAGE' then
    -- LAU-T02/T06: the package price covers its included components; the same component again as an extra is refused.
    perform erp._cp3_assert_closed_json_object(p_pricing,array['package_id'],array['package_id','extras'],'package pricing');
    select p.* into v_pkg from erp.bd_laundry_packages_v1 p where p.id=erp.bd_uuid_v1(p_pricing,'package_id',true) and p.vendor_id=v_vendor and p.is_active;
    if v_pkg.id is null then raise exception 'BD_PACKAGE_UNKNOWN: paket aktif vendor ini wajib dipilih';end if;
    select array_agg(component_id order by component_id) into v_included from erp.bd_laundry_package_components_v1 where package_id=v_pkg.id;
    v_charges:=v_charges||erp.bf_complete_shares_v1(erp.bf_package_charges_v1(v_vendor,v_pkg.id,bf_group,v_at,v_sizeids,v_qtys,v_included,v_pkg.package_name),v_sizeids);
    if p_pricing ? 'extras' and jsonb_typeof(p_pricing->'extras')<>'null' then
      if jsonb_typeof(p_pricing->'extras')<>'array' or jsonb_array_length(p_pricing->'extras')>30 then raise exception 'BD_PRICING_INVALID: extras wajib daftar';end if;
      for v_x in select value from jsonb_array_elements(p_pricing->'extras') loop
        perform erp._cp3_assert_closed_json_object(v_x,array['component_id','covered_qty','reason'],array['component_id','covered_qty','coverage','reason'],'extra component');
        if erp.bd_uuid_v1(v_x,'component_id',true)=any(v_included) then
          raise exception 'BD_COMPONENT_ALREADY_INCLUDED: komponen ini sudah termasuk dalam paket; biaya untuk cakupan yang sama tidak ditagih dua kali';end if;
        v_dec03:=erp.bd_require_policy_v1('LAU_DEC03','komponen tambahan di luar paket');
        if v_dec03->>'extra'<>'ALLOWED' then raise exception 'BD_EXTRA_REFUSED: LAU-DEC03 tidak mengizinkan komponen tambahan';end if;
        v_versions:=v_versions||jsonb_build_object('LAU_DEC03',erp.bd_policy_version_v1('LAU_DEC03'));
        v_charges:=v_charges||erp.bf_component_charge_v1(v_vendor,v_x,v_at,v_sizeids,v_qtys,v_total_qty,'EXTRA',v_seen,bf_group);
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
      perform erp._cp3_assert_closed_json_object(v_x,array['component_id','covered_qty'],array['component_id','covered_qty','coverage'],'component');
      v_charges:=v_charges||erp.bf_component_charge_v1(v_vendor,v_x,v_at,v_sizeids,v_qtys,v_total_qty,'COMPONENT',v_seen,bf_group);
      v_seen:=v_seen||erp.bd_uuid_v1(v_x,'component_id',true);
    end loop;
  end if;

  -- Known subtotal and completeness from the component charges.
  if v_mode in('PACKAGE','COMPONENTS') then
    v_known:=0;
    for v_line in select value from jsonb_array_elements(v_charges) loop
      if v_line->>'rate_status'<>'UNKNOWN' then v_known:=v_known+(v_line->>'amount')::numeric;else v_complete:=false;end if;
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
    insert into erp.bd_laundry_charge_lines_v1(delivery_line_id,line_no,kind,ref_id,version_id,label,covered_qty,rate_status,unit_rate,amount,included_components,price_reason,bf_sku_version_id)
    values(l.id,v_no,v_ch->>'kind',(v_ch->>'ref_id')::uuid,(v_ch->>'version_id')::uuid,v_ch->>'label',(v_ch->>'covered_qty')::integer,v_ch->>'rate_status',
      (v_ch->>'unit_rate')::numeric,(v_ch->>'amount')::numeric,v_ch->'included_components',v_ch->>'price_reason',(v_ch->>'bf_sku_version_id')::uuid)
    returning id into v_charge;
    for v_sh in select value from jsonb_array_elements(v_ch->'shares') loop
      select s.id into v_size from erp.laundry_delivery_batch_size_lines s where s.delivery_line_id=l.id and s.size_id=(v_sh->>'size_id')::uuid;
      if v_size is null then raise exception 'BD_INTERNAL: ukuran harga tidak ada pada kiriman';end if;
      insert into erp.bd_laundry_charge_shares_v1(charge_line_id,delivery_batch_size_line_id,amount,covered_qty)
      values(v_charge,v_size,(v_sh->>'amount')::numeric,coalesce((v_sh->>'covered_qty')::integer,
        (select qty_sent_pcs from erp.laundry_delivery_batch_size_lines where id=v_size)));
    end loop;
  end loop;
  perform erp.bd_refresh_size_estimates_v1(l.id);
end;$function$;
CREATE OR REPLACE FUNCTION erp.bd_post_priced_delivery_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_delivery jsonb;v_pricing jsonb;v_computed jsonb;v_response jsonb;v_version bigint;v_line uuid;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['delivery','expected_version','pricing'],array['delivery','expected_version','pricing'],
    'priced delivery payload');
  v_delivery:=p_payload->'delivery';v_pricing:=p_payload->'pricing';
  if jsonb_typeof(v_delivery) is distinct from 'object' then raise exception 'BD_PRICING_INVALID: delivery wajib objek POST_DELIVERY';end if;
  if jsonb_typeof(p_payload->'expected_version') is distinct from 'string' or p_payload->>'expected_version'!~'^[1-9][0-9]{0,18}$' then
    raise exception 'BD_FIELD_INVALID: expected_version wajib versi Potongan';end if;
  v_version:=(p_payload->>'expected_version')::bigint;
  perform pg_advisory_xact_lock(hashtextextended('BF:COMMERCIAL_SKUS',0));
  -- The prices read below stay as read until the delivery is posted: the version writers take the same locks (process and
  -- scoped rates per vendor/process, component and package prices per vendor) and the terms writer locks the vendor row.
  perform pg_advisory_xact_lock(hashtextextended('LRATE:'||erp.bd_uuid_v1(v_delivery,'vendor_id',true)::text||':'
    ||erp.bd_uuid_v1(v_delivery,'wash_process_id',true)::text,0));
  perform pg_advisory_xact_lock(hashtextextended('LRATE:'||erp.bd_uuid_v1(v_delivery,'vendor_id',true)::text||':*',0));
  perform 1 from erp.laundry_vendors where id=erp.bd_uuid_v1(v_delivery,'vendor_id',true) for share;
  v_computed:=erp.bd_compute_pricing_v1(v_delivery,v_pricing);
  insert into erp.bd_execution_context_v1(backend_pid,transaction_id,action,request_id,pricing)
  values(pg_backend_pid(),txid_current(),'POST_PRICED_DELIVERY',p_request,v_computed);
  v_response:=erp.save_laundry_qc_action_v1('POST_DELIVERY',v_delivery,p_request,v_version);
  delete from erp.bd_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current();
  select l.id into v_line from erp.laundry_delivery_lines l where l.delivery_id=(v_response->>'delivery_id')::uuid;
  if not exists(select 1 from erp.bd_laundry_priced_lines_v1 where delivery_line_id=v_line) then
    raise exception 'BD_INTERNAL: harga kiriman tidak tercatat';end if;
  return v_response||jsonb_build_object('estimated_cost',case when (v_computed->>'complete')::boolean
    then (v_computed->>'total_known')::numeric end,'pricing',erp.bd_priced_line_json_v1(v_line));
end;$function$;
CREATE OR REPLACE FUNCTION erp.save_laundry_qc_action_v1(p_action text, p_payload jsonb, p_client_request_id uuid, p_expected_version bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  v_action text:=upper(nullif(btrim(p_action),''));
  v_reason text:=nullif(btrim(p_payload->>'reason'),'');
  v_custody_outcome text:=upper(nullif(btrim(p_payload->>'custody_outcome'),''));
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_actor uuid:=erp.current_app_user_id();
  v_physical_raw text:=nullif(btrim(p_payload->>'physical_at'),'');
  v_physical_at timestamptz;
  v_batch_id uuid:=nullif(p_payload->>'distribution_batch_id','')::uuid;
  v_group_id uuid:=nullif(p_payload->>'cutting_group_id','')::uuid;
  v_delivery_id uuid:=nullif(p_payload->>'delivery_id','')::uuid;
  v_receipt_id uuid;
  v_failed_wash_attempt_id uuid;
  v_return_wip_event_id uuid;
  v_qc_id uuid:=nullif(p_payload->>'qc_inspection_id','')::uuid;
  v_vendor_id uuid:=nullif(p_payload->>'vendor_id','')::uuid;
  v_process_id uuid:=nullif(p_payload->>'wash_process_id','')::uuid;
  v_location_id uuid:=nullif(p_payload->>'destination_location_id','')::uuid;
  v_target_color text:=nullif(btrim(p_payload->>'target_dyeing_color'),'');
  v_lines jsonb:=p_payload->'lines';
  v_line jsonb;
  v_rate numeric(18,2);
  v_rate_count integer;
  v_group_count integer;
  v_total bigint;
  v_good bigint;
  v_bs bigint;
  v_available bigint;
  v_available_at_physical_time bigint;
  v_ready_after_qc bigint;
  v_delivery_line_id uuid;
  v_receipt_line_id uuid;
  v_number text;
  v_nested jsonb;
  v_group erp.cutting_groups%rowtype;
  v_po erp.production_orders%rowtype;
  v_delivery erp.laundry_deliveries%rowtype;
  v_receipt erp.laundry_receipts%rowtype;
  v_qc erp.qc_inspections%rowtype;
begin
  if p_client_request_id is null then raise exception 'client_request_id UUID is required'; end if;
  if v_actor is null then raise exception 'Active ERP app user is required'; end if;
  if v_action not in(
    'POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH','REVERSE_DELIVERY',
    'REVERSE_RECEIPT','POST_FINAL_SKU','REVERSE_FINAL_SKU'
  ) then raise exception 'Unsupported CP6 Laundry/QC action %',coalesce(v_action,'NULL'); end if;

  -- Physical time is operator intent. Validate it before the generic closed-payload
  -- gate so missing, timezone-less, and calendar-invalid values all fail with one
  -- actionable domain message instead of a helper or native cast error.
  if v_action in('POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH','POST_FINAL_SKU') then
    if jsonb_typeof(p_payload->'physical_at') is distinct from 'string'
       or v_physical_raw is null
       or v_physical_raw !~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}(:\d{2})?)$' then
      raise exception 'An explicit timezone-qualified physical_at is required; server time is never a transactional default';
    end if;
    begin
      v_physical_at:=v_physical_raw::timestamptz;
    exception
      when data_exception then
        raise exception 'An explicit timezone-qualified physical_at is required; server time is never a transactional default';
    end;
  end if;

  -- Do not let JSON coercion reinterpret a physical count or silently ignore
  -- a misspelled field.  Every connected writer uses one closed, canonical
  -- payload shape before idempotency or business mutation begins.
  if v_action='POST_DELIVERY' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,
      array['distribution_batch_id','vendor_id','wash_process_id','target_dyeing_color',
        'physical_at','reason','lines'],
      array['distribution_batch_id','vendor_id','wash_process_id','target_dyeing_color',
        'physical_at','reason','notes','lines'],
      'CP6 POST_DELIVERY payload'
    );
    if jsonb_typeof(p_payload->'distribution_batch_id')<>'string'
       or jsonb_typeof(p_payload->'vendor_id')<>'string'
       or jsonb_typeof(p_payload->'wash_process_id')<>'string'
       or jsonb_typeof(p_payload->'target_dyeing_color')<>'string'
       or jsonb_typeof(p_payload->'physical_at')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string'
       or jsonb_typeof(p_payload->'lines')<>'array'
       or(p_payload ? 'notes' and jsonb_typeof(p_payload->'notes') not in('string','null')) then
      raise exception 'CP6 POST_DELIVERY payload has invalid field types';
    end if;
    for v_line in select value from jsonb_array_elements(v_lines) loop
      perform erp._cp3_assert_closed_json_object(
        v_line,array['size_id','qty_sent_pcs'],array['size_id','qty_sent_pcs'],
        'CP6 POST_DELIVERY line'
      );
      if jsonb_typeof(v_line->'size_id')<>'string'
         or jsonb_typeof(v_line->'qty_sent_pcs')<>'number'
         or(v_line->>'qty_sent_pcs')!~'^(0|[1-9][0-9]*)$' then
        raise exception 'CP6 POST_DELIVERY line has invalid field types';
      end if;
    end loop;
  elsif v_action='POST_RECEIPT' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,array['delivery_id','wash_process_id','physical_at','reason','lines'],
      array['delivery_id','wash_process_id','physical_at','reason','lines'],
      'CP6 POST_RECEIPT payload'
    );
    if jsonb_typeof(p_payload->'delivery_id')<>'string'
       or jsonb_typeof(p_payload->'wash_process_id')<>'string'
       or jsonb_typeof(p_payload->'physical_at')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string'
       or jsonb_typeof(p_payload->'lines')<>'array' then
      raise exception 'CP6 POST_RECEIPT payload has invalid field types';
    end if;
    for v_line in select value from jsonb_array_elements(v_lines) loop
      perform erp._cp3_assert_closed_json_object(
        v_line,
        array['delivery_batch_size_line_id','qty_good_received','qty_bs_laundry'],
        array['delivery_batch_size_line_id','qty_good_received','qty_bs_laundry','bs_product_id'],
        'CP6 POST_RECEIPT line'
      );
      if not(v_line ? 'bs_product_id')
         or jsonb_typeof(v_line->'delivery_batch_size_line_id')<>'string'
         or jsonb_typeof(v_line->'qty_good_received')<>'number'
         or(v_line->>'qty_good_received')!~'^(0|[1-9][0-9]*)$'
         or jsonb_typeof(v_line->'qty_bs_laundry')<>'number'
         or(v_line->>'qty_bs_laundry')!~'^(0|[1-9][0-9]*)$'
         or jsonb_typeof(v_line->'bs_product_id') not in('string','null') then
        raise exception 'CP6 POST_RECEIPT line has invalid field types';
      end if;
    end loop;
  elsif v_action='POST_FAILED_WASH' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,
      array['delivery_id','wash_process_id','custody_outcome','physical_at','reason','lines'],
      array['delivery_id','wash_process_id','custody_outcome','physical_at','reason','lines'],
      'CP6 POST_FAILED_WASH payload'
    );
    if jsonb_typeof(p_payload->'delivery_id')<>'string'
       or jsonb_typeof(p_payload->'wash_process_id')<>'string'
       or jsonb_typeof(p_payload->'custody_outcome')<>'string'
       or v_custody_outcome not in('RETRY_AT_VENDOR','RETURN_UNPROCESSED')
       or jsonb_typeof(p_payload->'physical_at')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string'
       or jsonb_typeof(p_payload->'lines')<>'array' then
      raise exception 'CP6 POST_FAILED_WASH payload has invalid field types';
    end if;
    for v_line in select value from jsonb_array_elements(v_lines) loop
      perform erp._cp3_assert_closed_json_object(
        v_line,array['delivery_batch_size_line_id','qty_attempted_pcs'],
        array['delivery_batch_size_line_id','qty_attempted_pcs'],
        'CP6 POST_FAILED_WASH line'
      );
      if jsonb_typeof(v_line->'delivery_batch_size_line_id')<>'string'
         or jsonb_typeof(v_line->'qty_attempted_pcs')<>'number'
         or(v_line->>'qty_attempted_pcs')!~'^[1-9][0-9]*$' then
        raise exception 'CP6 POST_FAILED_WASH line has invalid field types';
      end if;
    end loop;
  elsif v_action='POST_FINAL_SKU' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,
      array['cutting_group_id','destination_location_id','physical_at','reason',
        'good_qty_pcs','completion_mode','lines'],
      array['cutting_group_id','destination_location_id','physical_at','reason',
        'good_qty_pcs','completion_mode','lines'],
      'CP6 POST_FINAL_SKU payload'
    );
    if jsonb_typeof(p_payload->'cutting_group_id')<>'string'
       or jsonb_typeof(p_payload->'destination_location_id')<>'string'
       or jsonb_typeof(p_payload->'physical_at')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string'
       or jsonb_typeof(p_payload->'good_qty_pcs')<>'number'
       or(p_payload->>'good_qty_pcs')!~'^(0|[1-9][0-9]*)$'
       or jsonb_typeof(p_payload->'completion_mode')<>'string'
       or(p_payload->>'completion_mode') not in('ALL_READY','PARTIAL_SELECTION')
       or jsonb_typeof(p_payload->'lines')<>'array' then
      raise exception 'CP6 POST_FINAL_SKU payload has invalid field types';
    end if;
    for v_line in select value from jsonb_array_elements(v_lines) loop
      perform erp._cp3_assert_closed_json_object(
        v_line,
        array['final_product_id','qty_good_pcs','qty_bs_pcs',
          'source_laundry_receipt_line_id','source_laundry_receipt_batch_size_line_id'],
        array['final_product_id','qty_good_pcs','qty_bs_pcs',
          'source_laundry_receipt_line_id','source_laundry_receipt_batch_size_line_id','notes'],
        'CP6 POST_FINAL_SKU line'
      );
      if jsonb_typeof(v_line->'final_product_id')<>'string'
         or jsonb_typeof(v_line->'qty_good_pcs')<>'number'
         or(v_line->>'qty_good_pcs')!~'^(0|[1-9][0-9]*)$'
         or jsonb_typeof(v_line->'qty_bs_pcs')<>'number'
         or(v_line->>'qty_bs_pcs')!~'^(0|[1-9][0-9]*)$'
         or jsonb_typeof(v_line->'source_laundry_receipt_line_id')<>'string'
         or jsonb_typeof(v_line->'source_laundry_receipt_batch_size_line_id')<>'string'
         or(v_line ? 'notes' and jsonb_typeof(v_line->'notes') not in('string','null')) then
        raise exception 'CP6 POST_FINAL_SKU line has invalid field types';
      end if;
    end loop;
  elsif v_action='REVERSE_DELIVERY' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,array['delivery_id','reason'],array['delivery_id','reason'],
      'CP6 REVERSE_DELIVERY payload'
    );
    if jsonb_typeof(p_payload->'delivery_id')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string' then
      raise exception 'CP6 REVERSE_DELIVERY payload has invalid field types';
    end if;
  elsif v_action='REVERSE_RECEIPT' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,array['receipt_id','reason'],array['receipt_id','reason'],
      'CP6 REVERSE_RECEIPT payload'
    );
    if jsonb_typeof(p_payload->'receipt_id')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string' then
      raise exception 'CP6 REVERSE_RECEIPT payload has invalid field types';
    end if;
  else
    perform erp._cp3_assert_closed_json_object(
      p_payload,array['qc_inspection_id','reason'],array['qc_inspection_id','reason'],
      'CP6 REVERSE_FINAL_SKU payload'
    );
    if jsonb_typeof(p_payload->'qc_inspection_id')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string' then
      raise exception 'CP6 REVERSE_FINAL_SKU payload has invalid field types';
    end if;
  end if;
  if v_reason is null or length(v_reason)<4 then raise exception 'A clear reason of at least 4 characters is required'; end if;
  if v_physical_at>clock_timestamp()+interval '5 minutes' then
    raise exception 'Physical time cannot be more than five minutes in the future';
  end if;

  if v_action in('POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH') then
    perform erp.require_permission('production.laundry.post');
    if v_action='POST_DELIVERY' then perform erp.require_permission('production.laundry.create'); end if;
  elsif v_action in('REVERSE_DELIVERY','REVERSE_RECEIPT') then
    perform erp.require_permission('production.laundry.reverse');
  elsif v_action='POST_FINAL_SKU' then
    perform erp.require_permission('production.final_sku.post');
  else
    perform erp.require_permission('production.final_sku.reverse');
  end if;

  v_hash:=erp._request_hash(jsonb_build_object(
    'action',v_action,'payload',p_payload,'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin(
    'cp6_laundry_qc_action_v1:'||lower(v_action),p_client_request_id,v_hash
  );
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);

  if v_action in('REVERSE_DELIVERY','REVERSE_RECEIPT','REVERSE_FINAL_SKU') then
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      case when v_action in('REVERSE_DELIVERY','REVERSE_RECEIPT')
        then 'production.laundry.reverse' else 'production.final_sku.reverse' end,
      p_client_request_id,p_payload
    );
  end if;

  if v_action='POST_DELIVERY' then
    if p_expected_version is null then raise exception 'Potongan expected_version is required'; end if;
    if v_batch_id is null or v_vendor_id is null or v_process_id is null
       or v_target_color is null then
      raise exception 'Distribution batch, vendor, wash process, and target color are required';
    end if;
    if jsonb_typeof(v_lines)<>'array' or jsonb_array_length(v_lines)=0 then
      raise exception 'Laundry delivery requires positive size lines';
    end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer)
      where x.size_id is null or coalesce(x.qty_sent_pcs,0)<=0
    ) or exists(
      select 1 from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer)
      group by x.size_id having count(*)>1
    ) then raise exception 'Laundry delivery size lines must be unique and positive'; end if;

    -- Resolve the immutable Potongan key without retaining a row lock, then
    -- take the shared CP6 fence before every business row.  The locked re-read
    -- below rejects a source that changed while this transaction waited; it
    -- must never continue under a fence for the wrong Potongan.
    select p.cutting_group_id into v_group_id
    from erp.cutting_distribution_batches b
    join erp.cutting_pickups p on p.id=b.pickup_id and p.status='POSTED'
    where b.id=v_batch_id;
    if v_group_id is null then raise exception 'Authoritative POSTED distribution batch was not found'; end if;
    -- Every CP6 mutation that can change Laundry/QC progress shares this
    -- transaction fence.  Cross-document actions on one Potongan therefore
    -- have one serial order even when their individual row locks do not meet.
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    perform 1
    from erp.cutting_distribution_batches b
    join erp.cutting_pickups p on p.id=b.pickup_id
    where b.id=v_batch_id and p.status='POSTED'
      and p.cutting_group_id=v_group_id
    for update of b,p;
    if not found then
      raise exception 'Authoritative POSTED distribution batch changed while waiting for the Potongan fence; refetch before retrying';
    end if;
    select * into v_group from erp.cutting_groups where id=v_group_id for update;
    if v_group.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_group.row_version;
    end if;
    select * into v_po from erp.production_orders where id=v_group.po_id for update;
    if v_po.status in('FINISHED','CANCELLED') then
      raise exception 'PO status % cannot receive a new Laundry delivery',v_po.status;
    end if;
    if v_physical_at<v_group.picked_up_at then
      raise exception 'Laundry send time cannot be earlier than the physical contractor pickup';
    end if;
    perform 1 from erp.laundry_vendors v
    where v.id=v_vendor_id and v.is_active for share;
    if not found then
      raise exception 'An active authoritative Laundry vendor is required';
    end if;
    perform 1 from erp.wash_processes w
    where w.id=v_process_id and w.is_active for share;
    if not found then
      raise exception 'An active authoritative wash process is required';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('LRATE:'||v_vendor_id::text||':'||v_process_id::text,0));
    if coalesce((erp.bd_context_v1()).action,'')='POST_PRICED_DELIVERY' then
      -- BD (LAU-05b): the BD facade priced this delivery; the line keeps the exact average rate when every price is known and
      -- NULL while a component price is unknown (the charge lines are attached below).
      v_rate:=((erp.bd_context_v1()).pricing->>'avg_rate')::numeric;v_rate_count:=1;
    elsif erp.bd_vendor_needs_pricing_v1(v_vendor_id,v_process_id) or exists(select 1 from erp.bf_wave_skus_v1 where cutting_group_id=v_group_id) then
      raise exception 'BD_PRICING_REQUIRED: vendor ini memakai harga paket/komponen/borongan/minimum/tarif khusus; kirim lewat tab Harga & tagihan di halaman Laundry (Kirim dengan harga)';
    else
      select count(*)::integer,min(r.rate_per_pcs) into v_rate_count,v_rate
      from erp.laundry_vendor_rate_versions r
      where r.vendor_id=v_vendor_id and r.wash_process_id=v_process_id
        and r.effective_from<=v_physical_at
        and(r.effective_to is null or r.effective_to>v_physical_at);
      if v_rate_count<>1 then
        raise exception 'Exactly one authoritative Laundry rate must be effective for this vendor/process/time; found %',v_rate_count;
      end if;
    end if;
    perform 1 from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at)
    order by r.id for share;

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
          and d.status not in('DRAFT','REVERSED')
      ) used on true
      where x.qty_sent_pcs>cap.qty-used.qty
    ) then raise exception 'Requested Laundry size quantity exceeds its remaining distribution-batch capacity'; end if;

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

    select sum(x.qty_sent_pcs)::bigint into v_total
    from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer);
    select coalesce(w.unsent_ready_qty_pcs,0)::bigint into v_available
    from erp.v_wip_control_status_v1 w where w.cutting_group_id=v_group.id;
    if v_total>coalesce(v_available,0) then
      raise exception 'Laundry send exceeds sewn-and-unsent capacity. Ready %, requested %',coalesce(v_available,0),v_total;
    end if;
    select greatest(
      coalesce((
        select sum(e.qty_signed) from erp.sewing_terminal_events e
        where e.cutting_group_id=v_group.id and e.physical_at<=v_physical_at
      ),0)
      -coalesce((
        select sum(dl.qty_sent_pcs)
        from erp.laundry_delivery_lines dl
        join erp.laundry_deliveries d on d.id=dl.delivery_id
        where dl.cutting_group_id=v_group.id
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
      -coalesce((
        select sum(i.qty_good_pcs+i.qty_bs_pcs)
        from erp.qc_inspection_items i
        join erp.qc_inspections q on q.id=i.inspection_id
        where i.cutting_group_id=v_group.id
          and i.source_laundry_receipt_line_id is null
          and q.status='POSTED' and q.physical_at<=v_physical_at
      ),0),0
    )::bigint into v_available_at_physical_time;
    if v_total>v_available_at_physical_time then
      raise exception 'Laundry send time predates sufficient authoritative sewing output. Ready at physical time %, requested %',
        v_available_at_physical_time,v_total;
    end if;

    perform erp.assert_cp6_dispatch_timeline_v2620b(
      v_batch_id,v_group.id,v_physical_at,v_lines
    );
    v_delivery_id:=gen_random_uuid();
    v_delivery_line_id:=gen_random_uuid();
    -- The UUID is already the immutable document identity. Keep all 128 bits
    -- in the unique human key so two valid postings can never be rejected by
    -- the former 40-bit display prefix collision surface.
    v_number:='LDR-'||to_char((v_physical_at AT TIME ZONE 'Asia/Jakarta'),'YYMMDD')||'-'
      ||upper(replace(v_delivery_id::text,'-',''));
    insert into erp.laundry_deliveries(
      id,delivery_number,po_id,vendor_id,target_dyeing_color,target_wash_process_id,
      special_instruction,physical_at,status,created_by
    ) values(
      v_delivery_id,v_number,v_group.po_id,v_vendor_id,v_target_color,v_process_id,
      nullif(btrim(p_payload->>'notes'),''),v_physical_at,'DRAFT',v_actor
    );
    insert into erp.laundry_delivery_lines(
      id,delivery_id,cutting_group_id,qty_sent_pcs,estimated_rate_snapshot,
      estimated_cost_status,notes
    ) values(
      v_delivery_line_id,v_delivery_id,v_group.id,v_total,v_rate,case when v_rate is null then 'PENDING' else 'ESTIMATED' end,
      'CP6 immutable distribution batch/size handoff: '||v_reason
    );
    insert into erp.laundry_delivery_batch_size_lines(
      delivery_line_id,distribution_batch_id,size_id,qty_sent_pcs,created_by
    ) select v_delivery_line_id,v_batch_id,x.size_id,x.qty_sent_pcs,v_actor
      from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer);
    -- BD: the priced charge lines and per-size estimates of this delivery (only inside the BD facade's context).
    perform erp.bd_attach_delivery_pricing_v1(v_delivery_line_id);
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      'production.laundry.post',p_client_request_id,p_payload
    );
    if exists(
      select 1 from erp.schema_migrations where version='v2.6.20d'
    ) then
      if to_regprocedure('erp.allocate_laundry_redispatch_participants_v2620e(uuid)') is null then
        raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20d redispatch allocator is missing';
      end if;
      perform erp.allocate_laundry_redispatch_participants_v2620e(v_delivery_line_id);
    end if;
    perform erp.post_laundry_delivery(v_delivery_id);
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current();
    if not found then raise exception 'CP6 execution context cleanup failed'; end if;
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery_id;
    select * into v_group from erp.cutting_groups where id=v_group.id;
    v_response:=jsonb_build_object(
      'action',v_action,'delivery_id',v_delivery.id,'delivery_number',v_delivery.delivery_number,
      'status',v_delivery.status,'row_version',v_delivery.row_version,
      'cutting_group_id',v_group.id,'cutting_group_row_version',v_group.row_version,
      'qty_sent_pcs',v_total,'rate_per_pcs',v_rate,
      'estimated_cost',round(v_total*v_rate,2),
      'stock_effect','SEWING_TO_LAUNDRY','hpp_effect','LAUNDRY_ACCRUAL_REBUILT'
    );

  elsif v_action='POST_RECEIPT' then
    if p_expected_version is null or v_delivery_id is null then
      raise exception 'Delivery and expected_version are required';
    end if;
    if v_process_id is null then raise exception 'Actual wash process is required'; end if;
    if jsonb_typeof(v_lines)<>'array' or jsonb_array_length(v_lines)=0 then
      raise exception 'Laundry receipt requires positive batch/size return lines';
    end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) where x.delivery_batch_size_line_id is null
        or coalesce(x.qty_good_received,0)<0 or coalesce(x.qty_bs_laundry,0)<0
        or coalesce(x.qty_good_received,0)+coalesce(x.qty_bs_laundry,0)<=0
        or(coalesce(x.qty_bs_laundry,0)>0 and x.bs_product_id is null)
        or(coalesce(x.qty_bs_laundry,0)=0 and x.bs_product_id is not null)
    ) or exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) group by x.delivery_batch_size_line_id having count(*)>1
    ) then raise exception 'Receipt size lines must be unique, positive, and bind every Laundry BS to a product'; end if;

    select min(dl.cutting_group_id::text)::uuid,count(*)::integer
      into v_group_id,v_group_count
    from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected CP6 receipt requires one authoritative delivery line';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery_id for update;
    if v_delivery.id is null or v_delivery.status not in('SENT','PARTIAL_RETURN') then
      raise exception 'Laundry receipt requires an active SENT/PARTIAL_RETURN delivery';
    end if;
    if v_delivery.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_delivery.row_version;
    end if;
    if v_physical_at<v_delivery.physical_at then
      raise exception 'Laundry return time cannot be earlier than the send time';
    end if;
    if exists(select 1 from erp.laundry_claims c where c.delivery_id=v_delivery.id
      and c.claim_type in('STUCK','MISSING') and c.status<>'REJECTED') then
      raise exception 'Reverse/reject the active STUCK/MISSING claim before posting a late physical return';
    end if;
    perform 1 from erp.wash_processes w
    where w.id=v_process_id and w.is_active for share;
    if not found then
      raise exception 'An active authoritative actual wash process is required';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('LRATE:'||v_delivery.vendor_id::text||':'||v_process_id::text,0));
    -- BA (round 9, W1 source inventory; M:4474 LAU-DEC03 / LAU-T14): the receipt prices the actual process at the rate that
    -- was effective when the goods were sent (the agreement snapshot), not at the return time; a rate version that starts
    -- between send and return does not reprice the delivery.
    if exists(select 1 from erp.bd_laundry_priced_lines_v1 bp where bp.delivery_id=v_delivery.id) then
      -- BD (LAU-05b): a priced delivery is received at its own exact estimate (erp.bd_allocate_receipt_v1 below), with the
      -- process it was priced for; its rate snapshot is the priced average (NULL while a component price is unknown).
      if v_process_id is distinct from v_delivery.target_wash_process_id then
        raise exception 'BD_PROCESS_CHANGED: kiriman dengan harga paket/komponen/borongan hanya diterima dengan proses yang dihargai saat kirim';
      end if;
      select dl.estimated_rate_snapshot into v_rate from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery.id;
      v_rate_count:=1;
    else
      select count(*)::integer,min(r.rate_per_pcs) into v_rate_count,v_rate
      from erp.laundry_vendor_rate_versions r
      where r.vendor_id=v_delivery.vendor_id and r.wash_process_id=v_process_id
        and r.effective_from<=v_delivery.physical_at
        and(r.effective_to is null or r.effective_to>v_delivery.physical_at);
      if v_rate_count<>1 then
        raise exception 'Exactly one authoritative actual Laundry rate must be effective for this vendor/process/time; found % (rate of the send time)',v_rate_count;
      end if;
    end if;
    perform 1 from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_delivery.vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_delivery.physical_at
      and(r.effective_to is null or r.effective_to>v_delivery.physical_at)
    order by r.id for share;
    select min(dl.id::text)::uuid into v_delivery_line_id
    from erp.laundry_delivery_lines dl
    where dl.delivery_id=v_delivery.id and dl.cutting_group_id=v_group_id;
    if v_delivery_line_id is null or(
      select count(*) from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery.id
    )<>1 then raise exception 'Connected CP6 receipt requires one authoritative delivery line'; end if;
    perform 1
    from erp.laundry_delivery_batch_size_lines sx
    join jsonb_to_recordset(v_lines) x(
      delivery_batch_size_line_id uuid,qty_good_received integer,
      qty_bs_laundry integer,bs_product_id uuid
    ) on x.delivery_batch_size_line_id=sx.id
    order by sx.id for update of sx;
    if(
      select count(*) from erp.laundry_delivery_batch_size_lines sx
      join jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) on x.delivery_batch_size_line_id=sx.id
      where sx.delivery_line_id=v_delivery_line_id
    )<>jsonb_array_length(v_lines) then
      raise exception 'A receipt source does not belong to this CP6 delivery';
    end if;
    if exists(
      select 1
      from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      )
      join erp.laundry_delivery_batch_size_lines sx on sx.id=x.delivery_batch_size_line_id
      where coalesce(x.qty_good_received,0)+coalesce(x.qty_bs_laundry,0)>
        sx.qty_sent_pcs-coalesce((
          select sum(rx.qty_good_received+rx.qty_bs_laundry)
          from erp.laundry_receipt_batch_size_lines rx
          join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
          join erp.laundry_receipts rh on rh.id=rl.receipt_id
          where rx.delivery_batch_size_line_id=sx.id and rh.status='POSTED'
        ),0)
    ) then raise exception 'Laundry receipt exceeds remaining quantity for an exact batch/size source'; end if;

    select sum(coalesce(x.qty_good_received,0))::bigint,
           sum(coalesce(x.qty_bs_laundry,0))::bigint
      into v_good,v_bs
    from jsonb_to_recordset(v_lines) x(
      delivery_batch_size_line_id uuid,qty_good_received integer,
      qty_bs_laundry integer,bs_product_id uuid
    );
    v_total:=v_good+v_bs;
    v_receipt_id:=gen_random_uuid();
    v_receipt_line_id:=gen_random_uuid();
    v_number:='LRC-'||to_char((v_physical_at AT TIME ZONE 'Asia/Jakarta'),'YYMMDD')||'-'
      ||upper(replace(v_receipt_id::text,'-',''));
    insert into erp.laundry_receipts(
      id,receipt_number,delivery_id,physical_at,status,created_by
    ) values(v_receipt_id,v_number,v_delivery.id,v_physical_at,'DRAFT',v_actor);
    insert into erp.laundry_receipt_lines(
      id,receipt_id,delivery_line_id,actual_wash_process_id,
      qty_good_received,qty_bs_laundry,qty_stuck,qty_missing,
      actual_rate_snapshot,actual_cost_status,actual_cost,notes
    ) values(
      v_receipt_line_id,v_receipt_id,v_delivery_line_id,v_process_id,
      -- A physical receipt proves the process/rate snapshot, not the vendor
      -- invoice.  Keep the amount ESTIMATED so the delivery accrual remains a
      -- liability until post_vendor_invoice atomically replaces it with AP.
      -- Marking this FINAL here would release accrual early and leave negative
      -- WIP after the same cost moves into FG/HPP.
      v_good,v_bs,0,0,v_rate,'ESTIMATED',round(v_total*v_rate,2),
      'CP6 immutable physical batch/size return: '||v_reason
    );
    insert into erp.laundry_receipt_batch_size_lines(
      receipt_line_id,delivery_batch_size_line_id,size_id,
      qty_good_received,qty_bs_laundry,bs_product_id,created_by
    ) select v_receipt_line_id,x.delivery_batch_size_line_id,sx.size_id,
        coalesce(x.qty_good_received,0),coalesce(x.qty_bs_laundry,0),x.bs_product_id,v_actor
      from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) join erp.laundry_delivery_batch_size_lines sx on sx.id=x.delivery_batch_size_line_id;
    -- BD: each size of a priced delivery takes its exact share of the estimate; the receipt line's cost is their sum.
    perform erp.bd_allocate_receipt_v1(v_receipt_line_id);
    insert into erp.laundry_receipt_bs_product_allocations(
      receipt_line_id,product_id,qty_bs,notes,created_by
    ) select v_receipt_line_id,x.bs_product_id,sum(x.qty_bs_laundry)::integer,
        'CP6 immutable Laundry-BS product/size declaration',v_actor
      from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) where x.qty_bs_laundry>0 group by x.bs_product_id;
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      'production.laundry.post',p_client_request_id,p_payload
    );
    perform erp.post_laundry_receipt(v_receipt_id);
    -- The predecessor function records every physical return as LAUNDRY → QC.
    -- Laundry BS is terminal at this boundary, so append the balancing
    -- QC → ON_HOLD event instead of rewriting/deleting the predecessor event.
    insert into erp.wip_stage_events(
      po_id,cutting_group_id,stage_from,stage_to,qty_pcs,
      source_type,source_id,physical_at,created_by,notes
    )
    select v_delivery.po_id,dl.cutting_group_id,'QC','ON_HOLD',x.qty_bs_laundry,
      'CP6_LAUNDRY_BS_SIZE_LINE',x.id,v_physical_at,v_actor,
      'Laundry BS is terminal and must never become QC-ready'
    from erp.laundry_receipt_batch_size_lines x
    join erp.laundry_receipt_lines rl on rl.id=x.receipt_line_id
    join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
    where x.receipt_line_id=v_receipt_line_id and x.qty_bs_laundry>0;
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current();
    if not found then raise exception 'CP6 execution context cleanup failed'; end if;
    select * into v_receipt from erp.laundry_receipts where id=v_receipt_id;
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery.id;
    v_response:=jsonb_build_object(
      'action',v_action,'receipt_id',v_receipt.id,'receipt_number',v_receipt.receipt_number,
      'receipt_status',v_receipt.status,'receipt_row_version',v_receipt.row_version,
      'delivery_id',v_delivery.id,'delivery_status',v_delivery.status,
      'delivery_row_version',v_delivery.row_version,'good_qty_pcs',v_good,'bs_qty_pcs',v_bs,
      'rate_per_pcs',v_rate,'actual_cost',coalesce((select sum(ba.amount) from erp.bd_laundry_receipt_allocations_v1 ba
        where ba.receipt_line_id=v_receipt_line_id),round(v_total*v_rate,2)),
      'cost_status','ESTIMATED_UNBILLED','accrual_effect','PRESERVED_UNTIL_VENDOR_INVOICE',
      'stock_effect','LAUNDRY_GOOD_TO_QC_AND_BS_TO_ON_HOLD',
      'hpp_effect','ACTUAL_LAUNDRY_COST_REBUILT'
    );

  elsif v_action='POST_FAILED_WASH' then
    if p_expected_version is null or v_delivery_id is null or v_process_id is null then
      raise exception 'Delivery, failed process, and expected_version are required';
    end if;
    if jsonb_typeof(v_lines)<>'array' or jsonb_array_length(v_lines)=0 then
      raise exception 'Paid failed wash requires positive attempted batch/size lines';
    end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_attempted_pcs integer
      ) where x.delivery_batch_size_line_id is null or coalesce(x.qty_attempted_pcs,0)<=0
    ) or exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_attempted_pcs integer
      ) group by x.delivery_batch_size_line_id having count(*)>1
    ) then
      raise exception 'Failed-wash size lines must be unique positive integer pieces';
    end if;

    select min(dl.cutting_group_id::text)::uuid,count(*)::integer
      into v_group_id,v_group_count
    from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected failed-wash action requires one authoritative delivery line';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_delivery from erp.laundry_deliveries
    where id=v_delivery_id for update;
    if v_delivery.id is null or v_delivery.status not in('SENT','PARTIAL_RETURN') then
      raise exception 'Paid failed wash requires an active SENT/PARTIAL_RETURN delivery';
    end if;
    if v_delivery.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_delivery.row_version;
    end if;
    if v_physical_at<v_delivery.physical_at
       or exists(select 1 from erp.laundry_receipts r
         where r.delivery_id=v_delivery.id and r.status='POSTED'
           and r.physical_at>v_physical_at) then
      raise exception 'Failed-wash physical time cannot precede the send or later posted Laundry history';
    end if;
    if exists(select 1 from erp.laundry_claims c
      where c.delivery_id=v_delivery.id and c.status<>'REJECTED') then
      raise exception 'Resolve/reject active Laundry claims before recording a failed-wash service attempt';
    end if;
    perform 1 from erp.wash_processes w
    where w.id=v_process_id and w.is_active for share;
    if not found then raise exception 'An active authoritative failed wash process is required'; end if;
    perform pg_advisory_xact_lock(hashtextextended(
      'LRATE:'||v_delivery.vendor_id::text||':'||v_process_id::text,0
    ));
    select count(*)::integer,min(r.rate_per_pcs) into v_rate_count,v_rate
    from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_delivery.vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at);
    if v_rate_count<>1 then
      raise exception 'Exactly one authoritative failed-wash rate must be effective for this vendor/process/time; found %',v_rate_count;
    end if;
    perform 1 from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_delivery.vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at)
    order by r.id for share;
    select min(dl.id::text)::uuid into v_delivery_line_id
    from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery.id;
    perform 1
    from erp.laundry_delivery_batch_size_lines s
    join jsonb_to_recordset(v_lines) x(
      delivery_batch_size_line_id uuid,qty_attempted_pcs integer
    ) on x.delivery_batch_size_line_id=s.id
    order by s.id for update of s;
    if (select count(*)
        from erp.laundry_delivery_batch_size_lines s
        join jsonb_to_recordset(v_lines) x(
          delivery_batch_size_line_id uuid,qty_attempted_pcs integer
        ) on x.delivery_batch_size_line_id=s.id
        where s.delivery_line_id=v_delivery_line_id)<>jsonb_array_length(v_lines)
       or exists(
         select 1
         from jsonb_to_recordset(v_lines) x(
           delivery_batch_size_line_id uuid,qty_attempted_pcs integer
         )
         join erp.laundry_delivery_batch_size_lines s
           on s.id=x.delivery_batch_size_line_id
         where x.qty_attempted_pcs>s.qty_sent_pcs-coalesce((
           select sum(rx.qty_good_received+rx.qty_bs_laundry)
           from erp.laundry_receipt_batch_size_lines rx
           join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
           join erp.laundry_receipts rh on rh.id=rl.receipt_id
           where rx.delivery_batch_size_line_id=s.id and rh.status='POSTED'
         ),0)
       ) then
      raise exception 'Failed-wash attempted quantity exceeds the exact pieces still in Laundry custody';
    end if;
    select sum(x.qty_attempted_pcs)::bigint into v_total
    from jsonb_to_recordset(v_lines) x(
      delivery_batch_size_line_id uuid,qty_attempted_pcs integer
    );
    if v_custody_outcome='RETURN_UNPROCESSED' and(
      v_delivery.status<>'SENT'
      or exists(
        select 1 from erp.laundry_receipt_lines rl
        join erp.laundry_receipts rh on rh.id=rl.receipt_id
        left join erp.laundry_failed_wash_attempts a on a.receipt_line_id=rl.id
        where rh.delivery_id=v_delivery.id and rh.status='POSTED'
          and a.id is null and rl.qty_good_received+rl.qty_bs_laundry>0
      )
      or jsonb_array_length(v_lines)<>(
        select count(*) from erp.laundry_delivery_batch_size_lines s
        where s.delivery_line_id=v_delivery_line_id
      )
      or exists(
        select 1 from erp.laundry_delivery_batch_size_lines s
        left join jsonb_to_recordset(v_lines) x(
          delivery_batch_size_line_id uuid,qty_attempted_pcs integer
        ) on x.delivery_batch_size_line_id=s.id
        where s.delivery_line_id=v_delivery_line_id
          and x.qty_attempted_pcs is distinct from s.qty_sent_pcs
      )
    ) then
      raise exception 'Return-unprocessed is deliberately all-or-nothing: every exact sent size must return before redispatch';
    end if;

    v_receipt_id:=gen_random_uuid();
    v_receipt_line_id:=gen_random_uuid();
    v_failed_wash_attempt_id:=gen_random_uuid();
    v_number:='LFW-'||to_char((v_physical_at AT TIME ZONE 'Asia/Jakarta'),'YYMMDD')||'-'
      ||upper(replace(v_receipt_id::text,'-',''));
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      'production.laundry.post',p_client_request_id,p_payload
    );
    insert into erp.laundry_receipts(
      id,receipt_number,delivery_id,physical_at,status,created_by
    ) values(v_receipt_id,v_number,v_delivery.id,v_physical_at,'DRAFT',v_actor);
    insert into erp.laundry_receipt_lines(
      id,receipt_id,delivery_line_id,actual_wash_process_id,
      qty_good_received,qty_bs_laundry,qty_stuck,qty_missing,
      actual_rate_snapshot,actual_cost_status,actual_cost,notes
    ) values(
      v_receipt_line_id,v_receipt_id,v_delivery_line_id,v_process_id,
      0,0,0,0,v_rate,'ESTIMATED',round(v_total*v_rate,2),
      'CP6 paid failed-wash service only; no physical Good/BS receipt: '||v_reason
    );
    insert into erp.laundry_failed_wash_attempts(
      id,receipt_id,receipt_line_id,delivery_id,custody_outcome,
      qty_attempted_pcs,reason,created_by
    ) values(
      v_failed_wash_attempt_id,v_receipt_id,v_receipt_line_id,v_delivery.id,
      v_custody_outcome,v_total,v_reason,v_actor
    );
    insert into erp.laundry_failed_wash_batch_size_lines(
      attempt_id,delivery_batch_size_line_id,size_id,qty_attempted_pcs,created_by
    ) select v_failed_wash_attempt_id,x.delivery_batch_size_line_id,s.size_id,
        x.qty_attempted_pcs,v_actor
      from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_attempted_pcs integer
      ) join erp.laundry_delivery_batch_size_lines s
        on s.id=x.delivery_batch_size_line_id;

    if v_custody_outcome='RETURN_UNPROCESSED' then
      perform set_config('app.physical_at',v_physical_at::text,true);
      update erp.laundry_deliveries
      set status='REVERSED',updated_at=clock_timestamp()
      where id=v_delivery.id;
      select min(rv.id::text)::uuid,count(*)::integer
        into v_return_wip_event_id,v_group_count
      from erp.wip_stage_events rv
      join erp.wip_stage_events src
        on src.id=rv.source_id and src.source_type='LAUNDRY_DELIVERY_LINE'
      join erp.laundry_delivery_lines dl
        on dl.id=src.source_id and dl.delivery_id=v_delivery.id
      where rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL';
      if v_group_count<>1 or v_return_wip_event_id is null then
        raise exception 'Return-unprocessed did not create exactly one linked physical WIP inverse';
      end if;
      update erp.laundry_failed_wash_attempts
      set return_wip_event_id=v_return_wip_event_id
      where id=v_failed_wash_attempt_id;
    else
      update erp.laundry_deliveries set updated_at=clock_timestamp()
      where id=v_delivery.id;
    end if;

    update erp.laundry_receipts
    set status='POSTED',updated_at=clock_timestamp()
    where id=v_receipt_id;

    if v_custody_outcome='RETURN_UNPROCESSED' then
      update erp.cutting_groups g
      set status=case
        when exists(
          select 1 from erp.laundry_receipt_lines rl
          join erp.laundry_receipts rh on rh.id=rl.receipt_id and rh.status='POSTED'
          join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
          join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
          where dl.cutting_group_id=g.id and rl.qty_good_received+rl.qty_bs_laundry>0
        ) then 'RETURNED'
        when exists(
          select 1 from erp.laundry_delivery_lines dl
          join erp.laundry_deliveries d on d.id=dl.delivery_id
          where dl.cutting_group_id=g.id and d.status not in('DRAFT','REVERSED')
        ) then 'LAUNDRY'
        when g.picked_up_at is not null then 'PICKED_UP' else 'CUT' end
      where g.id=v_group_id;
      select * into v_po from erp.production_orders where id=v_delivery.po_id for update;
      if v_po.status not in('ON_HOLD','CANCELLED') then
        update erp.production_orders po set
          status=case
            when exists(select 1 from erp.qc_inspections q
              where q.po_id=po.id and q.status='POSTED') then 'QC'
            when exists(select 1 from erp.laundry_deliveries d
              where d.po_id=po.id and d.status not in('DRAFT','REVERSED')) then 'LAUNDRY'
            when exists(select 1 from erp.cutting_groups g
              where g.po_id=po.id and g.picked_up_at is not null) then 'SEWING'
            else 'CUTTING' end,
          current_stage=case
            when exists(select 1 from erp.qc_inspections q
              where q.po_id=po.id and q.status='POSTED') then 'QC'
            when exists(select 1 from erp.laundry_deliveries d
              where d.po_id=po.id and d.status not in('DRAFT','REVERSED')) then 'LAUNDRY'
            when exists(select 1 from erp.cutting_groups g
              where g.po_id=po.id and g.picked_up_at is not null) then 'SEWING'
            else 'CUTTING' end,
          updated_at=clock_timestamp()
        where po.id=v_po.id;
      end if;
    end if;

    perform erp.sync_laundry_accrual(v_delivery.po_id,(v_physical_at AT TIME ZONE 'Asia/Jakarta')::date);
    if exists(select 1 from erp.fg_lots f where f.po_id=v_delivery.po_id) then
      perform erp.rebuild_po_hpp(
        v_delivery.po_id,'Paid failed-wash service attempt '||v_failed_wash_attempt_id::text
      );
      perform erp.propagate_conversion_hpp_for_po(v_delivery.po_id);
      perform erp.sync_po_hpp_to_gl(v_delivery.po_id,(v_physical_at AT TIME ZONE 'Asia/Jakarta')::date);
    end if;
    insert into erp.audit_logs(
      entity_type,entity_id,action,new_data,changed_by,change_reason
    ) values(
      'laundry_failed_wash_attempts',v_failed_wash_attempt_id,'POST',
      jsonb_build_object(
        'receipt_id',v_receipt_id,'delivery_id',v_delivery.id,
        'custody_outcome',v_custody_outcome,'qty_attempted_pcs',v_total,
        'rate_per_pcs',v_rate,'estimated_cost',round(v_total*v_rate,2),
        'history_deleted',false
      ),v_actor,v_reason
    );
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current();
    if not found then raise exception 'CP6 execution context cleanup failed'; end if;
    select * into v_receipt from erp.laundry_receipts where id=v_receipt_id;
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery.id;
    v_response:=jsonb_build_object(
      'action',v_action,'failed_wash_attempt_id',v_failed_wash_attempt_id,
      'receipt_id',v_receipt.id,'receipt_number',v_receipt.receipt_number,
      'receipt_status',v_receipt.status,'receipt_row_version',v_receipt.row_version,
      'delivery_id',v_delivery.id,'delivery_status',v_delivery.status,
      'delivery_row_version',v_delivery.row_version,
      'custody_outcome',v_custody_outcome,'qty_attempted_pcs',v_total,
      'rate_per_pcs',v_rate,'actual_cost',round(v_total*v_rate,2),
      'cost_status','ESTIMATED_UNBILLED',
      'stock_effect',case when v_custody_outcome='RETRY_AT_VENDOR'
        then 'PHYSICAL_STAYS_AT_LAUNDRY' else 'LAUNDRY_TO_SEWING_RETURN' end,
      'hpp_effect','FAILED_WASH_COST_REBUILT_WITHOUT_GOOD_BS_OR_FG'
    );

  elsif v_action='REVERSE_DELIVERY' then
    if p_expected_version is null or v_delivery_id is null then
      raise exception 'Delivery and expected_version are required';
    end if;
    select min(dl.cutting_group_id::text)::uuid,count(distinct dl.cutting_group_id)::integer
      into v_group_id,v_group_count
    from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected CP6 delivery reversal requires one Potongan';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery_id for update;
    if v_delivery.id is null then raise exception 'Laundry delivery not found'; end if;
    if v_delivery.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_delivery.row_version;
    end if;
    perform erp.reverse_laundry_delivery(v_delivery.id,v_reason);
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery.id;
    v_response:=jsonb_build_object(
      'action',v_action,'delivery_id',v_delivery.id,'status',v_delivery.status,
      'row_version',v_delivery.row_version,'history_deleted',false,
      'stock_effect','LAUNDRY_TO_SEWING_REVERSED','hpp_effect','LAUNDRY_ACCRUAL_REBUILT'
    );

  elsif v_action='REVERSE_RECEIPT' then
    if p_expected_version is null or nullif(p_payload->>'receipt_id','') is null then
      raise exception 'Receipt and expected_version are required';
    end if;
    v_receipt_id:=(p_payload->>'receipt_id')::uuid;
    select min(dl.cutting_group_id::text)::uuid,count(distinct dl.cutting_group_id)::integer
      into v_group_id,v_group_count
    from erp.laundry_receipt_lines rl
    join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
    where rl.receipt_id=v_receipt_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected CP6 receipt reversal requires one Potongan';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_receipt from erp.laundry_receipts where id=v_receipt_id for update;
    if v_receipt.id is null then raise exception 'Laundry receipt not found'; end if;
    if v_receipt.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_receipt.row_version;
    end if;
    select a.id,a.custody_outcome into v_failed_wash_attempt_id,v_custody_outcome
    from erp.laundry_failed_wash_attempts a where a.receipt_id=v_receipt.id
    for update;
    if v_failed_wash_attempt_id is null then
      perform erp.reverse_laundry_receipt(v_receipt.id,v_reason);
      select * into v_receipt from erp.laundry_receipts where id=v_receipt.id;
      v_response:=jsonb_build_object(
        'action',v_action,'receipt_id',v_receipt.id,'status',v_receipt.status,
        'row_version',v_receipt.row_version,'history_deleted',false,
        'stock_effect','LAUNDRY_RETURN_REVERSED','hpp_effect','LAUNDRY_AND_FG_HPP_REBUILT'
      );
    else
      if v_receipt.status='REVERSED' then
        v_response:=jsonb_build_object(
          'action',v_action,'receipt_id',v_receipt.id,'status',v_receipt.status,
          'row_version',v_receipt.row_version,'history_deleted',false,
          'stock_effect','NO_OP_ALREADY_REVERSED',
          'hpp_effect','NO_OP_ALREADY_REVERSED'
        );
      else
        if v_receipt.status<>'POSTED' then
          raise exception 'Only a POSTED failed-wash service attempt can be reversed';
        end if;
        select * into v_delivery from erp.laundry_deliveries
        where id=v_receipt.delivery_id for update;
        select * into v_po from erp.production_orders
        where id=v_delivery.po_id for update;
        if v_po.status='FINISHED' then
          raise exception 'PO sudah FINISHED. Reopen downstream before reversing failed-wash cost history.';
        end if;
        if exists(
          select 1 from erp.vendor_invoice_items i
          join erp.vendor_invoices h on h.id=i.invoice_id
          where i.receipt_line_id in(
            select l.id from erp.laundry_receipt_lines l where l.receipt_id=v_receipt.id
          ) and h.status<>'REVERSED'
        ) then
          raise exception 'Penerimaan laundry ini sudah masuk invoice vendor. Reverse invoice vendor aktif terlebih dahulu.';
        end if;
        if exists(
          select 1 from erp.qc_inspection_items i
          join erp.qc_inspections h on h.id=i.inspection_id
          where i.source_laundry_receipt_line_id in(
            select l.id from erp.laundry_receipt_lines l where l.receipt_id=v_receipt.id
          ) and h.status<>'REVERSED'
        ) or exists(
          select 1 from erp.laundry_receipt_batch_size_lines x
          join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
          where l.receipt_id=v_receipt.id
        ) then
          raise exception 'Failed-wash service-only receipt unexpectedly owns physical/QC facts; reversal stopped for investigation';
        end if;
        update erp.laundry_receipts
        set status='REVERSED',updated_at=clock_timestamp()
        where id=v_receipt.id;
        -- A RETURN_UNPROCESSED custody fact remains immutable. Reversing the
        -- vendor charge never resurrects the old dispatch; a later physical
        -- handoff is a new delivery with its own time, rate, and lineage.
        update erp.laundry_deliveries set updated_at=clock_timestamp()
        where id=v_delivery.id;
        perform erp.sync_laundry_accrual(v_delivery.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
        if exists(select 1 from erp.fg_lots f where f.po_id=v_delivery.po_id) then
          perform erp.rebuild_po_hpp(
            v_delivery.po_id,'Failed-wash service cost reversed '||v_failed_wash_attempt_id::text
          );
          perform erp.propagate_conversion_hpp_for_po(v_delivery.po_id);
          perform erp.sync_po_hpp_to_gl(v_delivery.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
        end if;
        insert into erp.audit_logs(
          entity_type,entity_id,action,new_data,changed_by,change_reason
        ) values(
          'laundry_failed_wash_attempts',v_failed_wash_attempt_id,'REVERSE',
          jsonb_build_object(
            'receipt_id',v_receipt.id,'custody_outcome',v_custody_outcome,
            'physical_return_preserved',v_custody_outcome='RETURN_UNPROCESSED',
            'history_deleted',false
          ),v_actor,v_reason
        );
        select * into v_receipt from erp.laundry_receipts where id=v_receipt.id;
        select * into v_delivery from erp.laundry_deliveries where id=v_delivery.id;
        v_response:=jsonb_build_object(
          'action',v_action,'receipt_id',v_receipt.id,'status',v_receipt.status,
          'row_version',v_receipt.row_version,'delivery_id',v_delivery.id,
          'delivery_status',v_delivery.status,'delivery_row_version',v_delivery.row_version,
          'history_deleted',false,'custody_outcome',v_custody_outcome,
          'stock_effect',case when v_custody_outcome='RETURN_UNPROCESSED'
            then 'PHYSICAL_RETURN_PRESERVED' else 'PHYSICAL_STAYS_AT_LAUNDRY' end,
          'hpp_effect','FAILED_WASH_COST_REVERSED_AND_REPORTS_REBUILT'
        );
      end if;
    end if;

  elsif v_action='POST_FINAL_SKU' then
    if p_expected_version is null or v_group_id is null or v_location_id is null then
      raise exception 'Potongan, destination FG location, and expected_version are required';
    end if;
    if jsonb_typeof(v_lines)<>'array' or jsonb_array_length(v_lines)=0 then
      raise exception 'Final SKU posting requires at least one allocation line';
    end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer,
        source_laundry_receipt_line_id uuid,
        source_laundry_receipt_batch_size_line_id uuid,notes text
      ) where x.final_product_id is null
        or coalesce(x.qty_good_pcs,0)<0 or coalesce(x.qty_bs_pcs,0)<0
        or coalesce(x.qty_good_pcs,0)+coalesce(x.qty_bs_pcs,0)<=0
        or x.source_laundry_receipt_line_id is null
        or x.source_laundry_receipt_batch_size_line_id is null
    ) then raise exception 'Every connected Final SKU line needs positive quantity and exact receipt/batch/size lineage'; end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer,
        source_laundry_receipt_line_id uuid,
        source_laundry_receipt_batch_size_line_id uuid,notes text
      ) group by x.final_product_id,x.source_laundry_receipt_line_id
      having count(*)>1
    ) then raise exception 'Duplicate Final SKU/source lines are not allowed'; end if;

    perform 1 from erp.locations l
    where l.id=v_location_id and l.is_active and l.location_type='FG_WAREHOUSE'
    for share;
    if not found then raise exception 'Destination must be an active FG warehouse'; end if;

    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    -- The shared Potongan fence is acquired before receipt headers. A
    -- concurrent reversal cannot change
    -- POSTED -> REVERSED after a child source was checked but before QC/FG was
    -- committed.  Lock every referenced header deterministically, then
    -- re-check the complete exact-source chain while those locks are held.
    perform 1
    from erp.laundry_receipts r
    where r.id in(
      select distinct rl.receipt_id
      from jsonb_to_recordset(v_lines) x(
        final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer,
        source_laundry_receipt_line_id uuid,
        source_laundry_receipt_batch_size_line_id uuid,notes text
      )
      join erp.laundry_receipt_batch_size_lines sx
        on sx.id=x.source_laundry_receipt_batch_size_line_id
      join erp.laundry_receipt_lines rl
        on rl.id=sx.receipt_line_id
    )
    order by r.id
    for update;
    if(
      select count(*)
      from jsonb_to_recordset(v_lines) x(
        final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer,
        source_laundry_receipt_line_id uuid,
        source_laundry_receipt_batch_size_line_id uuid,notes text
      )
      join erp.laundry_receipt_batch_size_lines sx
        on sx.id=x.source_laundry_receipt_batch_size_line_id
      join erp.laundry_receipt_lines rl
        on rl.id=sx.receipt_line_id
       and rl.id=x.source_laundry_receipt_line_id
      join erp.laundry_receipts r on r.id=rl.receipt_id and r.status='POSTED'
      join erp.laundry_delivery_lines dl
        on dl.id=rl.delivery_line_id and dl.cutting_group_id=v_group_id
      join erp.laundry_deliveries d
        on d.id=dl.delivery_id and d.status<>'REVERSED'
      join erp.cutting_groups g
        on g.id=v_group_id and g.po_id=d.po_id
    )<>jsonb_array_length(v_lines) then
      raise exception 'Every Final SKU source must belong to the same Potongan and an authoritative POSTED Laundry receipt';
    end if;
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      'production.final_sku.post',p_client_request_id,p_payload
    );
    v_nested:=erp.post_final_sku_allocation_v1(p_payload,p_client_request_id,p_expected_version);
    -- completion_mode is operational/reporting state, not browser-owned
    -- metadata.  The predecessor persists the declaration before returning
    -- the authoritative post-mutation progress.  Reject a lie in either
    -- direction here; the exception rolls the nested QC, FG, BS, HPP,
    -- journal, row-version, and both idempotency envelopes back atomically.
    v_ready_after_qc:=nullif(v_nested->>'ready_for_qc_qty_pcs','')::bigint;
    if v_ready_after_qc is null then
      raise exception 'CP6 Final-SKU writer did not return authoritative ready-for-QC balance';
    end if;
    if ((p_payload->>'completion_mode')='ALL_READY' and v_ready_after_qc<>0)
       or ((p_payload->>'completion_mode')='PARTIAL_SELECTION' and v_ready_after_qc=0) then
      raise exception
        'CP6 completion_mode % conflicts with authoritative ready-for-QC remainder % after atomic posting',
        p_payload->>'completion_mode',v_ready_after_qc;
    end if;
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current();
    if not found then raise exception 'CP6 execution context cleanup failed'; end if;
    v_qc_id:=nullif(v_nested->>'qc_inspection_id','')::uuid;
    select * into v_qc from erp.qc_inspections where id=v_qc_id;
    v_response:=v_nested||jsonb_build_object(
      'action',v_action,'qc_row_version',v_qc.row_version,
      'stock_effect','FG_GOOD_AND_QC_BS_POSTED',
      'hpp_effect','SERVER_REBUILT_FROM_IMMUTABLE_SNAPSHOTS',
      'browser_formula_used',false
    );

  else
    if p_expected_version is null or v_qc_id is null then
      raise exception 'QC inspection and expected_version are required';
    end if;
    select min(i.cutting_group_id::text)::uuid,count(distinct i.cutting_group_id)::integer
      into v_group_id,v_group_count
    from erp.qc_inspection_items i where i.inspection_id=v_qc_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected CP6 Final-SKU reversal requires one Potongan';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_qc from erp.qc_inspections where id=v_qc_id for update;
    if v_qc.id is null then raise exception 'QC inspection not found'; end if;
    if v_qc.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_qc.row_version;
    end if;
    perform erp.reverse_qc(v_qc.id,v_reason);
    select * into v_qc from erp.qc_inspections where id=v_qc.id;
    v_response:=jsonb_build_object(
      'action',v_action,'qc_inspection_id',v_qc.id,'status',v_qc.status,
      'row_version',v_qc.row_version,'history_deleted',false,
      'stock_effect','FG_AND_BS_REVERSED','hpp_effect','HPP_AND_GL_REBUILT'
    );
  end if;

  if v_action in('REVERSE_DELIVERY','REVERSE_RECEIPT','REVERSE_FINAL_SKU') then
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current()
      and actor_key=erp._idempotency_actor_key() and action=v_action
      and client_request_id=p_client_request_id;
    if not found then raise exception 'CP6 reverse execution context cleanup failed'; end if;
  end if;
  if exists(
    select 1 from erp.cp6_laundry_qc_execution_context c
    where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current()
  ) then raise exception 'CP6 execution context leaked after action'; end if;
  v_response:=v_response||jsonb_build_object(
    'contract_version','CP6_V2620',
    'client_request_id',p_client_request_id,
    'committed',true
  );
  return erp._idempotency_complete(
    'cp6_laundry_qc_action_v1:'||lower(v_action),p_client_request_id,v_response
  );
end
$function$;
CREATE OR REPLACE FUNCTION erp.prepare_rework_component_line()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_order erp.rework_orders%rowtype;
  v_case erp.bs_cases%rowtype;
  v_component erp.bs_case_components%rowtype;
  v_model uuid;
  v_original_contractor uuid;
  v_rate_id uuid;
  v_rate numeric(18,2);
  v_po_snapshot uuid;
  v_remaining integer;bf_sku uuid;bf_version uuid;
begin
  select * into v_order from erp.rework_orders where id=new.rework_order_id for update;
  if v_order.id is null then raise exception 'Rework order not found'; end if;
  if v_order.status not in('OPEN','IN_PROGRESS','PARTIAL') or v_order.cost_posted then
    raise exception 'Rework component lines are editable only before completion/cost posting';
  end if;
  select * into v_component from erp.bs_case_components where id=new.bs_case_component_id for update;
  if v_component.id is null then raise exception 'BS component not found'; end if;
  if v_component.bs_case_id<>v_order.bs_case_id then
    raise exception 'Rework component belongs to a different BS case';
  end if;
  select * into v_case from erp.bs_cases where id=v_order.bs_case_id;
  if new.qty_performed>v_order.qty_sent then
    raise exception 'Rework component qty performed % exceeds rework qty sent %',new.qty_performed,v_order.qty_sent;
  end if;
  v_remaining:=greatest(
    v_case.qty_pcs-v_component.completed_before_bs_qty-v_component.lifetime_newly_completed_qty,0
  );
  new.qty_newly_payable:=least(new.qty_performed,v_remaining);
  new.bf_sku_version_id:=null;
  new.source_contractor_rate_id:=null;
  new.source_po_component_snapshot_id:=null;

  if v_order.destination_type='LAUNDRY' then
    new.rate_snapshot:=0;
    new.rate_basis:='LAUNDRY_ZERO';
    return new;
  end if;

  select coalesce(po.model_id,p.model_id),coalesce(po.contractor_id,v_case.responsible_contractor_id)
  into v_model,v_original_contractor
  from erp.bs_cases bc
  left join erp.production_orders po on po.id=bc.po_id
  left join erp.products p on p.id=bc.product_id
  where bc.id=v_case.id;
  if v_model is null then
    raise exception 'Contractor rework requires PO or product model lineage for server-side rate resolution';
  end if;

  bf_sku:=erp.bf_group_sku_v1(v_case.cutting_group_id,v_case.product_id);
  if bf_sku is null and v_case.product_id is not null then
    select sku_id into bf_sku from erp.bf_sku_versions_v1 where id=erp.bf_version_at_v1(v_case.product_id,v_order.physical_sent_at);
  end if;
  if bf_sku is not null then
    if v_order.contractor_id is not distinct from v_original_contractor then
      select s.id,s.rate_per_pcs_snapshot into v_po_snapshot,v_rate from erp.po_work_component_snapshots s
        join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id
        where s.po_id=v_case.po_id and v.sku_id=bf_sku and s.work_component_id=v_component.work_component_id;
      if v_po_snapshot is not null then
        new.rate_snapshot:=v_rate;new.source_po_component_snapshot_id:=v_po_snapshot;new.rate_basis:='PO_SNAPSHOT';return new;
      end if;
    end if;
    select id into bf_version from erp.bf_sku_versions_v1 where sku_id=bf_sku and effective_from<=v_order.physical_sent_at
      and(effective_to is null or effective_to>v_order.physical_sent_at);
    v_rate:=erp.bf_work_rate_v1(bf_version,v_order.contractor_id,v_component.work_component_id,v_order.physical_sent_at);
    if v_rate is not null then
      new.rate_snapshot:=v_rate;new.bf_sku_version_id:=bf_version;new.rate_basis:='SKU_RATE';return new;
    end if;
  end if;

  select r.id,r.rate_per_pcs into v_rate_id,v_rate
  from erp.contractor_work_rates r
  where r.contractor_id=v_order.contractor_id
    and r.model_id=v_model
    and r.work_component_id=v_component.work_component_id
    and r.effective_from<=v_order.physical_sent_at
    and (r.effective_to is null or r.effective_to>v_order.physical_sent_at)
  order by r.effective_from desc,r.id desc limit 1;

  if v_rate_id is not null then
    new.rate_snapshot:=v_rate;
    new.source_contractor_rate_id:=v_rate_id;
    new.rate_basis:='CONTRACTOR_RATE';
    return new;
  end if;

  if v_order.contractor_id is distinct from v_original_contractor then
    raise exception 'Cross-Mandor rework requires an explicit effective contractor rate for this model/component';
  end if;
  select s.id,s.rate_per_pcs_snapshot into v_po_snapshot,v_rate
  from erp.po_work_component_snapshots s
  where s.po_id=v_case.po_id and s.work_component_id=v_component.work_component_id
    and erp.bf_snapshot_matches_v1(s.id,v_case.cutting_group_id,v_case.product_id)
  order by s.committed_at desc,s.id desc limit 1;
  if v_po_snapshot is null then
    raise exception 'No effective contractor rate or PO component snapshot exists for rework pricing';
  end if;
  new.rate_snapshot:=v_rate;
  new.source_po_component_snapshot_id:=v_po_snapshot;
  new.rate_basis:='PO_SNAPSHOT';
  return new;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.run_v263c_bs_rework_integrity_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
  select 'rework_component_wrong_bs_case','CRITICAL',count(*)::bigint,
         'Every rework component must belong to the order BS case'
  from erp.rework_component_lines l
  join erp.rework_orders o on o.id=l.rework_order_id
  join erp.bs_case_components c on c.id=l.bs_case_component_id
  where c.bs_case_id<>o.bs_case_id

  union all
  select 'rework_rate_provenance_mismatch','CRITICAL',count(*)::bigint,
         'Server-priced rework rate must equal its immutable source snapshot'
  from erp.rework_component_lines l
  left join erp.contractor_work_rates r on r.id=l.source_contractor_rate_id
  left join erp.po_work_component_snapshots s on s.id=l.source_po_component_snapshot_id
  where (l.rate_basis='CONTRACTOR_RATE' and (r.id is null or l.rate_snapshot<>r.rate_per_pcs))
     or (l.rate_basis='PO_SNAPSHOT' and (s.id is null or l.rate_snapshot<>s.rate_per_pcs_snapshot))
     or (l.rate_basis='LAUNDRY_ZERO' and l.rate_snapshot<>0)
     or (l.rate_basis='SKU_RATE' and (l.bf_sku_version_id is null or l.rate_snapshot is distinct from (
       select erp.bf_work_rate_v1(l.bf_sku_version_id,o.contractor_id,c.work_component_id,o.physical_sent_at)
       from erp.rework_orders o join erp.bs_case_components c on c.id=l.bs_case_component_id where o.id=l.rework_order_id)))

  union all
  select 'rework_component_qty_exceeds_sent','CRITICAL',count(*)::bigint,
         'Component performed qty cannot exceed physical rework qty sent'
  from erp.rework_component_lines l join erp.rework_orders o on o.id=l.rework_order_id
  where l.qty_performed>o.qty_sent

  union all
  select 'active_cross_mandor_without_explicit_rate','CRITICAL',count(*)::bigint,
         'Cross-Mandor contractor rework requires effective contractor-rate provenance'
  from erp.rework_component_lines l
  join erp.rework_orders o on o.id=l.rework_order_id
  join erp.bs_cases b on b.id=o.bs_case_id
  left join erp.production_orders po on po.id=b.po_id
  where o.destination_type='CONTRACTOR' and o.status<>'CANCELLED'
    and o.contractor_id is distinct from coalesce(po.contractor_id,b.responsible_contractor_id)
    and not ((l.rate_basis='CONTRACTOR_RATE' and l.source_contractor_rate_id is not null) or (l.rate_basis='SKU_RATE' and l.bf_sku_version_id is not null))

  union all
  select 'active_rework_bs_status_mismatch','CRITICAL',count(*)::bigint,
         'A BS case with active rework must project IN_REWORK while unresolved'
  from erp.bs_cases b
  where b.status not in('CANCELLED','RESOLVED','SCRAPPED','WRITTEN_OFF')
    and exists(select 1 from erp.rework_orders o where o.bs_case_id=b.id and o.status in('OPEN','IN_PROGRESS','PARTIAL'))
    and b.status<>'IN_REWORK'

  union all
  select 'bs_resolution_qty_exceeds_case','CRITICAL',count(*)::bigint,
         'Lifetime BS dispositions/resolutions cannot exceed case quantity'
  from (
    select b.id
    from erp.bs_cases b join erp.bs_resolutions r on r.bs_case_id=b.id
    group by b.id,b.qty_pcs having sum(r.qty_pcs)>b.qty_pcs
  ) excessive

  union all
  select 'cash_bs_resolution_invalid_claim','CRITICAL',count(*)::bigint,
         'Cash BS disposition requires matching settled laundry claim and capacity'
  from erp.bs_resolutions r
  join erp.bs_cases b on b.id=r.bs_case_id
  left join erp.laundry_claims c on c.id=r.source_laundry_claim_id
  where r.resolution_type='CASH_COMPENSATION'
    and (c.id is null or c.status<>'SETTLED' or c.vendor_id is distinct from b.responsible_vendor_id)

  union all
  select 'manual_bs_invalid_origin','CRITICAL',count(*)::bigint,
         'Manual/untracked BS must be only LEGACY or OUT_OF_NOWHERE with traceability'
  from erp.bs_cases b
  where b.untracked_type is not null
    and (b.untracked_type not in('LEGACY','OUT_OF_NOWHERE') or b.cause_source<>'UNKNOWN' or b.legacy_reference is null)

  union all
  select 'browser_direct_bs_rework_write_grant','CRITICAL',count(*)::bigint,
         'Authenticated browser must write BS/rework only through domain RPCs'
  from information_schema.role_table_grants g
  where g.table_schema='erp' and g.grantee='authenticated'
    and g.table_name in('bs_cases','bs_case_components','bs_resolutions','rework_orders','rework_component_lines')
    and g.privilege_type in('INSERT','UPDATE','DELETE');
$function$;
CREATE OR REPLACE FUNCTION erp.get_hpp_completeness(p_po_id uuid DEFAULT NULL::uuid)
 RETURNS TABLE(po_id uuid, po_number text, po_status text, current_hpp_total numeric, qty_basis_pcs bigint, hpp_per_pcs numeric, engine_cost_state text, display_status text, is_adjusted boolean, pending_reason_count integer, pending_reasons text[], latest_hpp_at timestamp with time zone)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
with po as (
  select p.id,p.po_number::text,p.status::text,p.contractor_id
  from erp.production_orders p
  where (p_po_id is null or p.id=p_po_id)
    and erp.current_app_role() in ('OWNER','ADMIN','STAFF')
), h as (
  select fl.po_id,
         count(*) filter(where fl.lot_origin='PRODUCTION')::int active_lots,
         count(hv.hpp_version_id) filter(where fl.lot_origin='PRODUCTION')::int hpp_lots,
         coalesce(sum(hv.total_cost) filter(where fl.lot_origin='PRODUCTION'),0)::numeric total_cost,
         coalesce(sum(hv.qty_basis_pcs) filter(where fl.lot_origin='PRODUCTION'),0)::bigint qty_basis,
         max(hv.calculated_at) filter(where fl.lot_origin='PRODUCTION') latest_at,
         bool_or(hv.cost_state='ESTIMATED') filter(where fl.lot_origin='PRODUCTION') any_estimated,
         bool_or(hv.cost_state='ADJUSTED') filter(where fl.lot_origin='PRODUCTION') any_adjusted
  from erp.fg_lots fl
  left join erp.v_current_hpp hv on hv.lot_id=fl.id
  where fl.lot_origin='PRODUCTION'
  group by fl.po_id
), flags as (
 select p.id po_id,
        coalesce(h.active_lots,0) active_lots,
        coalesce(h.hpp_lots,0) hpp_lots,
        coalesce(h.total_cost,0) total_cost,
        coalesce(h.qty_basis,0) qty_basis,
        h.latest_at,
        coalesce(h.any_estimated,false) any_estimated,
        coalesce(h.any_adjusted,false) any_adjusted,
        array_remove(array[
          case when coalesce(h.active_lots,0)=0 then 'BELUM_ADA_FG' end,
          case when coalesce(h.active_lots,0)>coalesce(h.hpp_lots,0) then 'HPP_CURRENT_BELUM_TERBENTUK' end,
          case when p.status<>'FINISHED' then 'PRODUKSI_BELUM_FINISHED' end,
          case when coalesce(erp.desired_laundry_accrual(p.id),0)>0.005 then 'BIAYA_LAUNDRY_MASIH_ESTIMASI/BELUM_FINAL' end,
          case when coalesce(h.any_estimated,false) then 'HPP_ENGINE_MASIH_ESTIMATED' end,
          case when exists(select 1 from erp.cost_recalc_queue q where q.entity_type='PO' and q.entity_id=p.id and q.status in('PENDING','RUNNING','FAILED')) then 'RECOST_BELUM_SELESAI' end,
          case when exists(select 1 from erp.bs_cases b where b.po_id=p.id and b.status in('OPEN','IN_REWORK','PARTIAL')) then 'BS/REWORK_BELUM_SELESAI' end,
          case when p.contractor_id is not null and coalesce(h.active_lots,0)>0 and not exists(select 1 from erp.po_work_component_snapshots s where s.po_id=p.id) then 'BIAYA_KERJA/BOM_BELUM_DIKONFIRMASI' end,
          case when exists(
            select 1 from erp.po_work_component_snapshots s
            where s.po_id=p.id and (s.bf_sku_version_id is not null or not exists(
              select 1 from erp.cutting_groups cg join erp.bf_wave_skus_v1 w on w.cutting_group_id=cg.id where cg.po_id=p.id)
              or exists(select 1 from erp.cutting_groups cg where cg.po_id=p.id and not exists(select 1 from erp.bf_wave_skus_v1 w where w.cutting_group_id=cg.id)))
            and not exists(
              select 1 from erp.work_completion_lines wcl join erp.work_completion_events wce on wce.id=wcl.completion_id
              where wcl.po_component_snapshot_id=s.id and wce.status='POSTED'
            )
          ) then 'ADA_KOMPONEN_KERJA_BELUM_PERNAH_DIPOST' end,
          case when exists(
            select 1 from erp.fg_lots fl
            where fl.po_id=p.id and fl.lot_origin='PRODUCTION'
              and exists(select 1 from erp.accessory_bom_versions abv join erp.accessory_bom_items abi on abi.bom_version_id=abv.id where abv.product_id=fl.product_id and abv.is_active=true and abv.effective_from<=fl.produced_at and (abv.effective_to is null or abv.effective_to>fl.produced_at))
              and not exists(select 1 from erp.fg_accessory_cost_snapshots s where s.lot_id=fl.id)
          ) then 'SNAPSHOT_BIAYA_AKSESORI_BELUM_ADA' end
        ]::text[],null) reasons
 from po p left join h on h.po_id=p.id
)
select p.id,
       p.po_number,
       p.status,
       f.total_cost,
       f.qty_basis,
       case when f.qty_basis>0 then f.total_cost/f.qty_basis else null end,
       case when f.any_estimated then 'ESTIMATED' when f.any_adjusted then 'ADJUSTED' when f.hpp_lots>0 then 'ACTUAL' else null end,
       case
         when f.active_lots=0 or f.hpp_lots=0 then 'BELUM_ADA_HPP'
         when p.status<>'FINISHED' then 'SEMENTARA'
         when cardinality(f.reasons)>0 then 'BELUM_LENGKAP'
         else 'LENGKAP_BERDASARKAN_DATA_SAAT_INI'
       end,
       f.any_adjusted,
       cardinality(f.reasons),
       f.reasons,
       f.latest_at
from po p join flags f on f.po_id=p.id
order by p.po_number;
$function$;
CREATE OR REPLACE FUNCTION erp.bb_check_sales_import_row_v1(p_batch uuid,p_row uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD'
AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;k text;v_cutover date;v_date date;v_due date;v_qty integer;v_price numeric;v_discount numeric;
begin
  perform erp.require_owner_admin();
  select * into r from erp.migration_staging_rows where id=p_row and batch_id=p_batch and entity_type='OPEN_SALES_DRAFT';
  if r.id is null then raise exception 'Baris draf penjualan tidak ditemukan';end if;
  j:=r.normalized_payload;
  foreach k in array array['draft_number','line_number','draft_date','customer_code','location_code','product_sku','qty_pcs','unit_price'] loop
    if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk draf penjualan terbuka',k;end if;
  end loop;
  if length(btrim(j->>'draft_number'))>60 or length(btrim(j->>'line_number'))>60 then raise exception 'draft_number: maksimal 60 karakter';end if;
  select (cutover_at at time zone 'Asia/Jakarta')::date into v_cutover from erp.migration_batches where id=p_batch;
  v_date:=erp.bb_parse_date_v1(j->>'draft_date','draft_date');
  if v_date>v_cutover then raise exception 'draft_date: draf harus dibuat sebelum saldo awal';end if;
  if nullif(btrim(j->>'due_date'),'') is not null then v_due:=erp.bb_parse_date_v1(j->>'due_date','due_date');end if;
  if j->>'qty_pcs' !~ '^[1-9][0-9]{0,8}$' then raise exception 'qty_pcs: jumlah pcs bilangan bulat positif';end if;
  v_qty:=(j->>'qty_pcs')::integer;
  v_price:=erp.bb_parse_amount_v1(j->>'unit_price','unit_price',true);
  v_discount:=case when nullif(btrim(j->>'discount_amount'),'') is null then 0 else erp.bb_parse_amount_v1(j->>'discount_amount','discount_amount',true) end;
  if v_discount>v_qty*v_price then raise exception 'discount_amount: potongan melebihi nilai baris';end if;
  if not exists(select 1 from erp.customers where customer_code=j->>'customer_code' and is_active)
    and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type='CUSTOMER' and validation_status='VALID'
      and normalized_payload->>'customer_code'=j->>'customer_code') then
    raise exception 'customer_code: pelanggan aktif tidak ditemukan';
  end if;
  if not exists(select 1 from erp.locations where location_code=j->>'location_code' and is_active and location_type='FG_WAREHOUSE')
    and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type='LOCATION' and validation_status='VALID'
      and normalized_payload->>'location_code'=j->>'location_code' and normalized_payload->>'location_type'='FG_WAREHOUSE') then
    raise exception 'location_code: gudang barang jadi aktif tidak ditemukan';
  end if;
  perform erp.bf_resolve_import_product_v1(p_batch,j,true);
  -- One draft: the same customer, warehouse, dates and terms on every line, and each line number once.
  if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPEN_SALES_DRAFT' and x.id<>r.id
      and lower(btrim(x.normalized_payload->>'draft_number'))=lower(btrim(j->>'draft_number'))
      and (lower(btrim(x.normalized_payload->>'line_number'))=lower(btrim(j->>'line_number'))
        or x.normalized_payload->>'customer_code'<>j->>'customer_code' or x.normalized_payload->>'location_code'<>j->>'location_code'
        or x.normalized_payload->>'draft_date'<>j->>'draft_date' or coalesce(x.normalized_payload->>'due_date','')<>coalesce(j->>'due_date','')
        or coalesce(x.normalized_payload->>'payment_terms','')<>coalesce(j->>'payment_terms',''))) then
    raise exception 'BB_S02_DUPLICATE_DRAFT: baris draf ganda atau kepala draf tidak konsisten';
  end if;
  if exists(select 1 from erp.sales_headers where lower(btrim(sale_number))=lower(btrim(j->>'draft_number')))
    or exists(select 1 from erp.bb_open_sales_drafts_v1 where lower(btrim(draft_number))=lower(btrim(j->>'draft_number'))) then
    raise exception 'BB_S02_DUPLICATE_DRAFT: nomor draf sudah dipakai penjualan lain';
  end if;
  return jsonb_build_object('cutover_date',v_cutover,'draft_date',v_date,'due_date',v_due,'qty_pcs',v_qty,'unit_price',v_price,'discount_amount',v_discount);
end;$function$;
CREATE OR REPLACE FUNCTION erp.bb_apply_sales_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare d record;r record;j jsonb;c jsonb;b erp.migration_batches%rowtype;v_customer uuid;v_location uuid;v_items jsonb;v_sale jsonb;
  v_sale_id uuid;v_product uuid;v_lines jsonb;l jsonb;
begin
  perform erp.require_owner_admin();
  select * into b from erp.migration_batches where id=p_batch;
  for d in select lower(btrim(normalized_payload->>'draft_number')) k,min(btrim(normalized_payload->>'draft_number')) draft_number
      from erp.migration_staging_rows where batch_id=p_batch and entity_type='OPEN_SALES_DRAFT' and posted_entity_id is null
      group by 1 order by 1 loop
    perform pg_advisory_xact_lock(hashtextextended('BB_S02_DRAFT:'||d.k,0));
    v_items:='[]'::jsonb;v_lines:='[]'::jsonb;j:=null;
    for r in select * from erp.migration_staging_rows where batch_id=p_batch and entity_type='OPEN_SALES_DRAFT' and posted_entity_id is null
        and lower(btrim(normalized_payload->>'draft_number'))=d.k order by lower(btrim(normalized_payload->>'line_number')),source_row_no loop
      if r.validation_status<>'VALID' then raise exception 'Draf penjualan belum lolos pemeriksaan';end if;
      j:=r.normalized_payload;c:=erp.bb_check_sales_import_row_v1(p_batch,r.id);
      v_product:=erp.bf_resolve_import_product_v1(p_batch,j,false);
      v_items:=v_items||jsonb_build_array(jsonb_build_object('product_id',v_product,'qty_pcs',(c->>'qty_pcs')::integer,
        'unit_price_snapshot',(c->>'unit_price')::numeric,'discount_amount',(c->>'discount_amount')::numeric,
        'notes','Baris '||btrim(j->>'line_number')||' draf lama '||d.draft_number));
      v_lines:=v_lines||jsonb_build_array(c||jsonb_build_object('row_id',r.id,'line_number',btrim(j->>'line_number'),'product_id',v_product));
    end loop;
    select id into strict v_customer from erp.customers where customer_code=j->>'customer_code' and is_active;
    select id into strict v_location from erp.locations where location_code=j->>'location_code' and is_active and location_type='FG_WAREHOUSE';
    -- The native draft and its one reservation. A reservation beyond the free finished goods of the warehouse (the lines of
    -- this draft and every draft before it) is refused by the native check and rolls the whole import back.
    begin
      v_sale:=erp.save_sale_draft_v2(jsonb_build_object('sale_number',d.draft_number,'customer_id',v_customer,'source_location_id',v_location,
        'sale_date',b.cutover_at,'due_date',c->>'due_date','payment_terms',nullif(btrim(j->>'payment_terms'),''),
        'notes','Draf penjualan terbuka saat saldo awal (draf lama '||d.draft_number||' tanggal '||(c->>'draft_date')
          ||'); ubah tanggal invoice ke tanggal nyata sebelum posting',
        'reason','Impor saldo awal: draf penjualan terbuka dengan reservasi resmi','items',v_items),
        md5('BB_S02:'||p_batch::text||':'||d.k)::uuid,null);
    exception when others then
      raise exception 'BB_S02_RESERVATION_REFUSED: draf %: %',d.draft_number,sqlerrm;
    end;
    v_sale_id:=(v_sale->>'sale_id')::uuid;
    insert into erp.bb_open_sales_drafts_v1(sale_id,batch_id,draft_number,draft_date,customer_id,cutover_at)
    values(v_sale_id,p_batch,d.draft_number,(c->>'draft_date')::date,v_customer,b.cutover_at);
    -- The lines as checked before the draft existed (a second check would see the draft's own number as taken).
    for l in select * from jsonb_array_elements(v_lines) loop
      insert into erp.bb_open_sales_draft_lines_v1(source_row_id,sale_id,line_number,product_id,qty_pcs,unit_price,discount_amount)
      values((l->>'row_id')::uuid,v_sale_id,l->>'line_number',(l->>'product_id')::uuid,(l->>'qty_pcs')::integer,(l->>'unit_price')::numeric,
        (l->>'discount_amount')::numeric);
      update erp.migration_staging_rows set posted_entity_id=v_sale_id,posted_entity_type='OPEN_SALES_DRAFT',posted_at=statement_timestamp(),
        updated_at=statement_timestamp() where id=(l->>'row_id')::uuid;
    end loop;
  end loop;
end;$function$;
CREATE OR REPLACE FUNCTION erp.bc_check_import_row_v1(p_batch uuid,p_row uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD'
AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;k text;v_qty numeric;v_amount numeric;v_count boolean;v_type text;v_doc record;v_kind text;
  v_zone text;v_total numeric;v_source text;
begin
  perform erp.require_owner_admin();
  select * into r from erp.migration_staging_rows where id=p_row and batch_id=p_batch
    and entity_type in('OPENING_ACCESSORY_NOTE_LINE','OPENING_ACCESSORY_CUSTODY');
  if r.id is null then raise exception 'Baris aksesori saldo awal tidak ditemukan';end if;
  j:=r.normalized_payload;
  if r.entity_type='OPENING_ACCESSORY_NOTE_LINE' then
    foreach k in array array['document_number','contractor_code','line_number','material_sku','qty','line_amount'] loop
      if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk baris nota aksesori lama',k;end if;
    end loop;
    if j->>'line_number'!~'^[1-9][0-9]{0,2}$' then raise exception 'line_number: nomor baris 1-999';end if;
    select m.material_type,u.dimension='COUNT' into v_type,v_count from erp.materials m join erp.uom_definitions u on u.unit_code=m.unit_code
      where m.material_sku=j->>'material_sku' and m.is_active;
    if v_type is null then
      select upper(s.normalized_payload->>'material_type'),(select u.dimension='COUNT' from erp.uom_definitions u where u.unit_code=s.normalized_payload->>'unit_code')
        into v_type,v_count from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='MATERIAL' and s.validation_status='VALID'
          and s.normalized_payload->>'material_sku'=j->>'material_sku' limit 1;
    end if;
    if v_type is distinct from 'ACCESSORY' then raise exception 'material_sku: nota aksesori hanya untuk aksesori aktif';end if;
    if (v_count and j->>'qty'!~'^[1-9][0-9]{0,11}$') or (not v_count and j->>'qty'!~'^[0-9]{1,12}(\.[0-9]{1,6})?$') then
      raise exception 'qty: % positif',case when v_count then 'PCS utuh' else 'angka maksimal enam desimal' end;end if;
    v_qty:=(j->>'qty')::numeric;
    if v_qty<=0 then raise exception 'qty: harus lebih dari nol';end if;
    v_amount:=erp.bb_parse_amount_v1(j->>'line_amount','line_amount',true);
    -- The note's CONTRACTOR_RECEIVABLE opening document in this batch.
    select s.id,s.normalized_payload into v_doc from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='OPENING_BALANCE_ITEM'
      and upper(s.normalized_payload->>'balance_type')='CONTRACTOR_RECEIVABLE' and s.normalized_payload->>'contractor_code'=j->>'contractor_code'
      and lower(btrim(s.normalized_payload->>'document_number'))=lower(btrim(j->>'document_number'));
    if v_doc.id is null then raise exception 'BC_C02_DOCUMENT_REQUIRED: piutang mandor saldo awal dengan nomor dokumen dan mandor ini tidak ada di impor';end if;
    if nullif(btrim(v_doc.normalized_payload->>'original_amount'),'') is null then
      raise exception 'BC_C02_DOCUMENT_REQUIRED: dokumen piutang mandor wajib membawa nominal dokumen awal';end if;
    if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_ACCESSORY_NOTE_LINE' and x.id<>r.id
        and lower(btrim(x.normalized_payload->>'document_number'))=lower(btrim(j->>'document_number'))
        and x.normalized_payload->>'contractor_code'=j->>'contractor_code' and x.normalized_payload->>'line_number'=j->>'line_number') then
      raise exception 'BC_C02_DUPLICATE_LINE: nomor baris nota ganda';end if;
    select sum(replace(btrim(x.normalized_payload->>'line_amount'),',','.')::numeric) into v_total from erp.migration_staging_rows x
      where x.batch_id=p_batch and x.entity_type='OPENING_ACCESSORY_NOTE_LINE' and x.normalized_payload->>'contractor_code'=j->>'contractor_code'
        and lower(btrim(x.normalized_payload->>'document_number'))=lower(btrim(j->>'document_number'))
        and btrim(x.normalized_payload->>'line_amount')~'^[0-9]+([.,][0-9]{1,2})?$';
    if v_total is distinct from replace(btrim(v_doc.normalized_payload->>'original_amount'),',','.')::numeric then
      raise exception 'BC_C02_TOTAL_MISMATCH: jumlah baris nota % tidak sama dengan nominal dokumen awal %',v_total,v_doc.normalized_payload->>'original_amount';end if;
    return jsonb_build_object('qty',v_qty,'line_amount',v_amount,'document_row_id',v_doc.id);
  end if;
  -- OPENING_ACCESSORY_CUSTODY
  v_kind:=upper(coalesce(j->>'custody_kind',''));
  if v_kind not in('PENDING_VALUE','UNRETURNED','CUSTOMER_GARMENT') then
    raise exception 'custody_kind: PENDING_VALUE, UNRETURNED atau CUSTOMER_GARMENT';end if;
  if nullif(btrim(j->>'custody_key'),'') is null or length(btrim(j->>'custody_key'))>80 then raise exception 'custody_key: wajib, maksimal 80 karakter';end if;
  if exists(select 1 from erp.migration_staging_rows x where x.entity_type='OPENING_ACCESSORY_CUSTODY' and x.id<>r.id
      and lower(btrim(x.normalized_payload->>'custody_key'))=lower(btrim(j->>'custody_key'))
      and (x.batch_id=p_batch or x.posted_entity_id is not null)) then
    raise exception 'BC_C03_DUPLICATE: custody_key sudah dipakai; satu barang fisik hanya satu baris';end if;
  -- D09 (owner 26 Sep 2026, ACC-C12 option a): the pending item names its source (count sheet + line, or source lot); the same
  -- source is one item whatever custody key a later request uses. Other lines of the same sheet are other goods.
  v_source:=erp.bd_custody_source_identity_v1(j);
  if exists(select 1 from erp.bd_custody_sources_v1 s where s.source_identity=v_source)
    or exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_ACCESSORY_CUSTODY' and x.id<>r.id
      and erp.bd_custody_source_identity_v1(x.normalized_payload,false)=v_source) then
    raise exception 'BC_C12_SAME_SOURCE: rujukan sumber % sudah dipakai; barang yang sama tetap satu item walau kunci permintaan baru',v_source;end if;
  if nullif(btrim(j->>'unit_cost'),'') is not null then
    raise exception 'BC_C03_VALUED_ROW: barang bernilai adalah stok saldo awal biasa (OPENING_BALANCE_ITEM MATERIAL di lokasi zona), bukan titipan';end if;
  if j->>'qty'!~'^[1-9][0-9]{0,11}$' then raise exception 'qty: PCS utuh positif';end if;
  if v_kind in('PENDING_VALUE','UNRETURNED') and not (v_kind='UNRETURNED' and nullif(btrim(j->>'material_sku'),'') is null) then
    if not exists(select 1 from erp.materials m join erp.uom_definitions u on u.unit_code=m.unit_code where m.material_sku=j->>'material_sku'
        and m.is_active and m.material_type='ACCESSORY' and u.dimension='COUNT')
      and not exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='MATERIAL' and s.validation_status='VALID'
        and s.normalized_payload->>'material_sku'=j->>'material_sku' and upper(s.normalized_payload->>'material_type')='ACCESSORY') then
      raise exception 'material_sku: aksesori hitung aktif tidak ditemukan';end if;
  end if;
  if v_kind='PENDING_VALUE' then
    if upper(coalesce(j->>'condition',''))not in('WAITING','USABLE','DAMAGED') then raise exception 'condition: WAITING, USABLE atau DAMAGED';end if;
    select z.zone_kind into v_zone from erp.locations l join erp.bc_accessory_zones_v1 z on z.location_id=l.id
      where l.location_code=j->>'location_code' and l.is_active;
    if v_zone is distinct from 'INSPECTION' then
      raise exception 'location_code: titipan bernilai pending berada di area pemeriksaan terdaftar';end if;
  elsif v_kind='UNRETURNED' then
    if nullif(btrim(j->>'holder'),'') is null or length(btrim(j->>'holder'))>120 then raise exception 'holder: pemegang wajib diisi';end if;
    if upper(coalesce(j->>'owner_kind',''))not in('COMPANY','CUSTOMER') then raise exception 'owner_kind: COMPANY atau CUSTOMER';end if;
    if nullif(btrim(j->>'material_sku'),'') is null and nullif(btrim(j->>'description'),'') is null then
      raise exception 'description: isi aksesori atau keterangan barang';end if;
  else
    if nullif(btrim(j->>'customer_code'),'') is null or nullif(btrim(j->>'description'),'') is null then
      raise exception 'customer_code/description: titipan pelanggan wajib pelanggan dan keterangan';end if;
    if not exists(select 1 from erp.customers where customer_code=j->>'customer_code' and is_active)
      and not exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='CUSTOMER' and s.validation_status='VALID'
        and s.normalized_payload->>'customer_code'=j->>'customer_code') then raise exception 'customer_code: pelanggan aktif tidak ditemukan';end if;
  end if;
  if v_kind='CUSTOMER_GARMENT' then perform erp.bf_resolve_import_product_v1(p_batch,j,true,true);end if;
  return jsonb_build_object('kind',v_kind,'qty',(j->>'qty')::numeric,'source',v_source);
end;$function$;
CREATE OR REPLACE FUNCTION erp.bc_apply_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;j jsonb;c jsonb;b erp.migration_batches%rowtype;v_balance uuid;v_material uuid;v_location uuid;v_id uuid;v_cond text;
begin
  perform erp.require_owner_admin();
  select * into b from erp.migration_batches where id=p_batch;
  for r in select * from erp.migration_staging_rows where batch_id=p_batch and entity_type in('OPENING_ACCESSORY_NOTE_LINE','OPENING_ACCESSORY_CUSTODY')
      and posted_entity_id is null order by entity_type,source_row_no loop
    if r.validation_status<>'VALID' then raise exception 'Baris aksesori saldo awal belum lolos pemeriksaan';end if;
    j:=r.normalized_payload;c:=erp.bc_check_import_row_v1(p_batch,r.id);v_id:=gen_random_uuid();
    if r.entity_type='OPENING_ACCESSORY_NOTE_LINE' then
      select ob.id into v_balance from erp.initial_import_financial_sources f join erp.opening_subledger_balances ob on ob.opening_item_id=f.opening_item_id
        where f.source_row_id=(c->>'document_row_id')::uuid;
      if v_balance is null then raise exception 'BC_C02_DOCUMENT_REQUIRED: piutang mandor dokumen % belum terbentuk',j->>'document_number';end if;
      select id into strict v_material from erp.materials where material_sku=j->>'material_sku';
      insert into erp.bc_opening_note_lines_v1(id,batch_id,source_row_id,balance_id,document_number,line_number,material_id,qty,line_amount)
      values(v_id,p_batch,r.id,v_balance,btrim(j->>'document_number'),(j->>'line_number')::int,v_material,(c->>'qty')::numeric,(c->>'line_amount')::numeric);
    elsif c->>'kind'='PENDING_VALUE' then
      select id into strict v_material from erp.materials where material_sku=j->>'material_sku';
      select id into strict v_location from erp.locations where location_code=j->>'location_code';
      v_cond:=upper(j->>'condition');
      insert into erp.bc_return_lots_v1(id,source_kind,owner_kind,value_mode,material_id,location_id,qty_received,init_usable,init_damaged,
        received_at,batch_id,source_row_id,reference)
      values(v_id,'OPENING_PENDING_VALUE','COMPANY','PENDING',v_material,v_location,(c->>'qty')::numeric,
        case when v_cond='USABLE' then (c->>'qty')::numeric else 0 end,case when v_cond='DAMAGED' then (c->>'qty')::numeric else 0 end,
        b.cutover_at,p_batch,r.id,'Opname awal '||btrim(j->>'custody_key')||coalesce(' — '||nullif(btrim(j->>'notes'),''),''));
    elsif c->>'kind'='UNRETURNED' then
      insert into erp.bc_outstanding_returns_v1(id,source_kind,owner_kind,material_id,description,qty_expected,holder,reference,batch_id,source_row_id)
      values(v_id,'OPENING_UNRETURNED',upper(j->>'owner_kind'),(select id from erp.materials where material_sku=nullif(btrim(j->>'material_sku'),'')),
        nullif(btrim(j->>'description'),''),(c->>'qty')::numeric,btrim(j->>'holder'),'Opname awal '||btrim(j->>'custody_key'),p_batch,r.id);
    else
      insert into erp.bc_customer_custody_v1(id,customer_id,product_id,description,qty,received_at,batch_id)
      values(v_id,(select id from erp.customers where customer_code=j->>'customer_code'),
        erp.bf_resolve_import_product_v1(p_batch,j,false,true),
        btrim(j->>'description'),(c->>'qty')::numeric,b.cutover_at,p_batch);
    end if;
    -- D09: the source identity stays with the goods (one row per source; a concurrent import of the same source fails here).
    if r.entity_type='OPENING_ACCESSORY_CUSTODY' then
      begin
        insert into erp.bd_custody_sources_v1(source_identity,custody_kind,record_id,batch_id,source_row_id,count_sheet,sheet_line,source_lot)
        values(c->>'source',c->>'kind',v_id,p_batch,r.id,nullif(btrim(j->>'count_sheet'),''),nullif(btrim(j->>'sheet_line'),''),nullif(btrim(j->>'source_lot'),''));
      exception when unique_violation then
        raise exception 'BC_C12_SAME_SOURCE: rujukan sumber % sudah dipakai; barang yang sama tetap satu item walau kunci permintaan baru',c->>'source';
      end;
    end if;
    update erp.migration_staging_rows set posted_entity_id=v_id,posted_entity_type=r.entity_type,posted_at=statement_timestamp(),
      updated_at=statement_timestamp() where id=r.id;
  end loop;
  -- Valued opening stock counted at an inspection area (ALL-C03 quarantine, value kept): one ledger lot per opening row so the
  -- inspection can later move it to the warehouse or the damaged area at its value.
  insert into erp.bc_return_lots_v1(source_kind,owner_kind,value_mode,material_id,location_id,qty_received,received_at,batch_id,source_row_id,reference)
  select 'OPENING_QUARANTINE','COMPANY','LEDGER',i.material_id,i.location_id,i.qty,b.cutover_at,p_batch,i.id,'Opname awal area pemeriksaan (saldo awal '||i.id||')'
  from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id
  join erp.bc_accessory_zones_v1 z on z.location_id=i.location_id and z.zone_kind='INSPECTION'
  where h.migration_batch_id=p_batch and i.balance_type='MATERIAL' and i.qty>0
    and not exists(select 1 from erp.bc_return_lots_v1 l where l.source_kind='OPENING_QUARANTINE' and l.source_row_id=i.id);
end;$function$;
CREATE OR REPLACE FUNCTION erp.be_check_pocket_import_v1(p_batch uuid,p_row uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD'
AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;k text;c date;d date;t record;v_qty numeric;v_amount numeric;v_kind text;
begin
 perform erp.require_owner_admin();perform erp.pocket_period_lock_v1();
 select * into strict r from erp.migration_staging_rows where id=p_row and batch_id=p_batch;
 j:=r.normalized_payload;select null::uuid id,null::jsonb p into t;
 foreach k in array array['document_number','line_number','physical_date','qty'] loop
  if nullif(btrim(j->>k),'') is null or length(j->>k)>120 then raise exception 'BE_POCKET_PROVENANCE: % wajib dan maksimal 120 karakter',k;end if;
 end loop;
 if j->>'physical_date' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'BE_POCKET_DATE';end if;
 d:=(j->>'physical_date')::date;select erp._cp3_business_date(cutover_at) into c from erp.migration_batches where id=p_batch;
 if d>=c or d::text<>j->>'physical_date' then raise exception 'BE_POCKET_DATE: riwayat harus sebelum tanggal cutover';end if;
 if j->>'qty' !~ '^[0-9]+([.][0-9]{1,6})?$' or (j->>'qty')::numeric<=0 then raise exception 'BE_POCKET_QTY';end if;
 v_qty:=(j->>'qty')::numeric(18,6);
 if exists(select 1 from erp.migration_staging_rows x where x.entity_type=r.entity_type and x.id<>r.id
   and lower(btrim(x.normalized_payload->>'document_number'))=lower(btrim(j->>'document_number'))
   and lower(btrim(x.normalized_payload->>'line_number'))=lower(btrim(j->>'line_number'))
   and (x.batch_id=p_batch or x.posted_entity_id is not null)) then raise exception 'BE_POCKET_DUPLICATE_SOURCE: dokumen dan baris telah dipakai';end if;
 if exists(select 1 from erp.pocket_periods p where erp.pocket_period_active_v1(p.id) and d between p.period_start and p.period_end) then
  raise exception 'BE_POCKET_PERIOD_ACTIVE: batalkan alokasi periode sebelum menambah sumber historis';end if;
 if r.entity_type='OPENING_POCKET_USAGE' then
  v_amount:=erp.bb_parse_amount_v1(j->>'amount','amount',false);v_kind:=upper(j->>'allocation_status');
  if v_kind is null or v_kind not in('ALLOCATED','UNALLOCATED') then raise exception 'BE_POCKET_ALLOCATION_STATUS';end if;
  if (v_kind='ALLOCATED')<>(nullif(btrim(j->>'prior_allocation_reference'),'') is not null) then raise exception 'BE_POCKET_PRIOR_ALLOCATION: referensi wajib hanya untuk nilai yang telah dialokasikan';end if;
  if not exists(select 1 from erp.materials where material_sku=j->>'material_sku' and is_active)
   and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type='MATERIAL' and validation_status='VALID' and normalized_payload->>'material_sku'=j->>'material_sku') then raise exception 'BE_POCKET_MATERIAL';end if;
  -- An independent source-sheet total is a control, never a second journal.
  if nullif(btrim(j->>'control_key'),'') is null then raise exception 'BE_POCKET_CONTROL_REQUIRED';end if;
  if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type=r.entity_type and x.normalized_payload->>'control_key'=j->>'control_key'
    and (x.normalized_payload->>'control_amount' is distinct from j->>'control_amount' or x.normalized_payload->>'control_qty' is distinct from j->>'control_qty')) then raise exception 'BE_POCKET_CONTROL_INCONSISTENT';end if;
  if (select sum((normalized_payload->>'amount')::numeric) from erp.migration_staging_rows where batch_id=p_batch and entity_type=r.entity_type and normalized_payload->>'control_key'=j->>'control_key')
      is distinct from erp.bb_parse_amount_v1(j->>'control_amount','control_amount',false)
   or (select sum((normalized_payload->>'qty')::numeric) from erp.migration_staging_rows where batch_id=p_batch and entity_type=r.entity_type and normalized_payload->>'control_key'=j->>'control_key')
      is distinct from (j->>'control_qty')::numeric then raise exception 'BE_POCKET_CONTROL_MISMATCH';end if;
  perform erp.be_pocket_check_receipt_origin_v1(p_batch,j);
  return jsonb_build_object('qty',v_qty,'amount',v_amount,'physical_date',d,'kind',v_kind);
 elsif r.entity_type='OPENING_POCKET_SEWING' then
  if v_qty<>trunc(v_qty) or v_qty>2147483647 then raise exception 'BE_POCKET_SEWING_PCS';end if;
  if nullif(btrim(j->>'control_key'),'') is null or coalesce(j->>'control_qty','') !~ '^[1-9][0-9]*$' then raise exception 'BE_POCKET_DENOMINATOR_CONTROL_REQUIRED';end if;
  if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type=r.entity_type and x.normalized_payload->>'control_key'=j->>'control_key'
     and x.normalized_payload->>'control_qty' is distinct from j->>'control_qty')
   or (select sum((x.normalized_payload->>'qty')::numeric) from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type=r.entity_type and x.normalized_payload->>'control_key'=j->>'control_key')
     is distinct from (j->>'control_qty')::numeric then raise exception 'BE_POCKET_DENOMINATOR_INCOMPLETE';end if;
  v_kind:=upper(j->>'target_kind');
  if v_kind is null or v_kind not in('WIP','BS','FINISHED_GOODS','COGS') then raise exception 'BE_POCKET_TARGET';end if;
  if not exists(select 1 from erp.contractors where contractor_code=j->>'contractor_code')
   and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type='CONTRACTOR' and validation_status='VALID' and normalized_payload->>'contractor_code'=j->>'contractor_code') then raise exception 'BE_POCKET_CONTRACTOR';end if;
  if v_kind='COGS' then
   if nullif(btrim(j->>'sold_reference'),'') is null or nullif(btrim(j->>'target_source_key'),'') is not null then raise exception 'BE_POCKET_SOLD_PROVENANCE';end if;
   perform erp.bf_resolve_import_product_v1(p_batch,j,true);
  else
   if nullif(btrim(j->>'sold_reference'),'') is not null then raise exception 'BE_POCKET_TARGET_AMBIGUOUS';end if;
   select s.id,s.normalized_payload p into t from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='OPENING_BALANCE_ITEM'
     and s.validation_status='VALID' and s.normalized_payload->>'opening_source_key'=j->>'target_source_key';
   if t.id is null or upper(t.p->>'balance_type')<>v_kind or (v_kind in('WIP','BS') and nullif(t.p->>'po_number','') is null) then raise exception 'BE_POCKET_TARGET_SOURCE_REQUIRED';end if;
   if (select sum((x.normalized_payload->>'qty')::numeric) from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type=r.entity_type and x.normalized_payload->>'target_source_key'=j->>'target_source_key')>(t.p->>'qty')::numeric then raise exception 'BE_POCKET_SEWING_EXCEEDS_OPENING';end if;
  end if;
  return jsonb_build_object('qty',v_qty,'physical_date',d,'kind',v_kind,'target_row',case when v_kind<>'COGS' then t.id end);
 end if;
 raise exception 'BE_POCKET_IMPORT_ENTITY';
end;$function$;
CREATE OR REPLACE FUNCTION erp.be_apply_pocket_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;j jsonb;c jsonb;v_id uuid;v_date date;v_journal uuid;v_item uuid;v_po uuid;
begin
 perform erp.require_owner_admin();
 -- The router already holds the batch row lock. Imports without pocket rows
 -- must retain their native request-lock behavior and not claim this domain lock.
 if not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch
   and entity_type in('OPENING_POCKET_USAGE','OPENING_POCKET_SEWING') and posted_entity_id is null) then
  return;
 end if;
 perform erp.pocket_period_lock_v1();
 select erp._cp3_business_date(cutover_at) into strict v_date from erp.migration_batches where id=p_batch;
 for r in select * from erp.migration_staging_rows where batch_id=p_batch and entity_type in('OPENING_POCKET_USAGE','OPENING_POCKET_SEWING') and posted_entity_id is null order by entity_type,source_row_no loop
  if r.validation_status<>'VALID' then raise exception 'BE_POCKET_IMPORT_NOT_VALID';end if;
  j:=r.normalized_payload;c:=erp.be_check_pocket_import_v1(p_batch,r.id);v_id:=gen_random_uuid();v_journal:=null;
  if r.entity_type='OPENING_POCKET_USAGE' then
   if c->>'kind'='UNALLOCATED' then
    v_journal:=erp.post_journal('BE_OPENING_POCKET_EXPENSE',v_id,v_date,'Pengeluaran kain kantong sebelum cutover '||btrim(j->>'document_number'),jsonb_build_array(
     jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',(c->>'amount')::numeric,'credit',0),
     jsonb_build_object('mapping_key','OPENING_EQUITY','debit',0,'credit',(c->>'amount')::numeric)));
   end if;
   insert into erp.be_pocket_usage_v1(id,source_row_id,batch_id,document_number,line_number,physical_date,material_id,material_qty,original_amount,allocation_status,prior_allocation_reference,journal_id)
   values(v_id,r.id,p_batch,btrim(j->>'document_number'),btrim(j->>'line_number'),(c->>'physical_date')::date,
    (select id from erp.materials where material_sku=j->>'material_sku'),(c->>'qty')::numeric,(c->>'amount')::numeric,c->>'kind',nullif(btrim(j->>'prior_allocation_reference'),''),v_journal);
   perform erp.be_pocket_link_receipt_origin_v1(v_id,p_batch,j);
  else
   v_item:=null;v_po:=null;
   if c->>'target_row' is not null then
    select opening_item_id into strict v_item from erp.initial_import_opening_stock_sources where batch_id=p_batch and source_row_id=(c->>'target_row')::uuid;
    select po_id into v_po from erp.initial_import_production_sources where opening_item_id=v_item;
   end if;
   insert into erp.be_pocket_sewing_v1(id,source_row_id,batch_id,document_number,line_number,physical_date,contractor_id,qty,target_kind,opening_item_id,po_id,product_id,sold_reference)
   values(v_id,r.id,p_batch,btrim(j->>'document_number'),btrim(j->>'line_number'),(c->>'physical_date')::date,
    (select id from erp.contractors where contractor_code=j->>'contractor_code'),(c->>'qty')::numeric::bigint,c->>'kind',v_item,v_po,
    case when upper(j->>'target_kind')='COGS' then erp.bf_resolve_import_product_v1(p_batch,j,false) end,nullif(btrim(j->>'sold_reference'),''));
  end if;
  update erp.migration_staging_rows set posted_entity_id=v_id,posted_entity_type=r.entity_type,posted_at=statement_timestamp(),updated_at=statement_timestamp() where id=r.id;
 end loop;
end;$function$;
CREATE OR REPLACE FUNCTION erp.bb_check_rework_import_row_v1(p_batch uuid,p_row uuid)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO '' SET "DateStyle" TO 'ISO, YMD'
AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;k text;v_cutover date;v_bs erp.migration_staging_rows%rowtype;b jsonb;v_po jsonb;
  w erp.migration_staging_rows%rowtype;wj jsonb;v_sent integer;v_returned integer;v_open integer;v_date date;v_total integer;
  v_product uuid;v_root uuid;v_model uuid;v_contractor uuid;v_component uuid;v_rate numeric;v_found numeric;v_before integer;v_qty integer;
begin
  perform erp.require_owner_admin();
  select * into r from erp.migration_staging_rows where id=p_row and batch_id=p_batch;
  if r.id is null then raise exception 'Baris impor tidak ditemukan';end if;
  select (cutover_at at time zone 'Asia/Jakarta')::date into v_cutover from erp.migration_batches where id=p_batch;
  if r.entity_type='OPENING_REWORK' then w:=r;
  else
    j:=r.normalized_payload;
    foreach k in array array['rework_number','work_component_code','completed_before_bs_qty','qty_performed','rate_per_pcs'] loop
      if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk komponen rework terbuka',k;end if;
    end loop;
    select * into w from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_REWORK'
      and lower(btrim(x.normalized_payload->>'rework_number'))=lower(btrim(j->>'rework_number'));
    if w.id is null then raise exception 'BB_REWORK_UNKNOWN: nomor rework tidak ada di file rework terbuka impor ini';end if;
  end if;
  wj:=w.normalized_payload;
  foreach k in array array['rework_number','bs_source_key','destination_type','sent_date','qty_sent_original','qty_returned_before_cutover','qty_open'] loop
    if nullif(btrim(wj->>k),'') is null then raise exception '%: wajib diisi untuk rework terbuka',k;end if;
  end loop;
  if length(btrim(wj->>'rework_number'))>50 then raise exception 'rework_number: maksimal 50 karakter';end if;
  if (select count(*) from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_REWORK'
      and lower(btrim(x.normalized_payload->>'rework_number'))=lower(btrim(wj->>'rework_number')))>1
     or exists(select 1 from erp.rework_orders ro where lower(ro.rework_number)=lower('ORW-'||btrim(wj->>'rework_number'))) then
    raise exception 'BB_REWORK_NUMBER_DUPLICATE: nomor rework sudah dipakai';
  end if;
  select * into v_bs from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_BALANCE_ITEM'
    and upper(x.normalized_payload->>'balance_type')='BS' and nullif(x.normalized_payload->>'po_number','') is not null
    and x.normalized_payload->>'opening_source_key'=wj->>'bs_source_key' and x.validation_status='VALID';
  if v_bs.id is null then
    raise exception 'BB_REWORK_BS_SOURCE_REQUIRED: bs_source_key harus menunjuk baris BS ber-PO yang valid di impor ini';
  end if;
  b:=v_bs.normalized_payload;
  v_sent:=erp.bb_parse_count_v1(wj->>'qty_sent_original','qty_sent_original',1);
  v_returned:=erp.bb_parse_count_v1(wj->>'qty_returned_before_cutover','qty_returned_before_cutover',0);
  v_open:=erp.bb_parse_count_v1(wj->>'qty_open','qty_open',1);
  if v_open<>v_sent-v_returned then
    raise exception 'BB_REWORK_OPEN_QTY_MISMATCH: sisa di rework (%) harus sama dengan dikirim (%) dikurangi kembali sebelum cutover (%)',v_open,v_sent,v_returned;
  end if;
  select coalesce(sum((x.normalized_payload->>'qty_open')::integer),0) into v_total from erp.migration_staging_rows x
    where x.batch_id=p_batch and x.entity_type='OPENING_REWORK' and x.normalized_payload->>'bs_source_key'=wj->>'bs_source_key'
      and x.normalized_payload->>'qty_open' ~ '^[0-9]{1,9}$';
  if v_total>(b->>'qty')::numeric then raise exception 'BB_REWORK_EXCEEDS_BS: rework terbuka melebihi jumlah BS asalnya';end if;
  v_date:=erp.bb_parse_date_v1(wj->>'sent_date','sent_date');
  if v_date>v_cutover then raise exception 'BB_REWORK_SENT_DATE: rework terbuka dikirim sebelum atau pada tanggal saldo awal';end if;
  if upper(wj->>'destination_type')='CONTRACTOR' then
    if nullif(btrim(wj->>'vendor_code'),'') is not null or nullif(btrim(wj->>'contractor_code'),'') is null
       or wj->>'contractor_code' is distinct from b->>'contractor_code' then
      raise exception 'BB_REWORK_HOLDER_MISMATCH: rework ke mandor harus ke mandor pemegang baris BS asalnya';
    end if;
    select c.id into v_contractor from erp.contractors c where c.contractor_code=wj->>'contractor_code' and c.is_active and c.contractor_type='MANDOR';
    if v_contractor is null then raise exception 'BB_REWORK_MANDOR: mandor rework harus mandor aktif yang sudah ada';end if;
    if not exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_REWORK_COMPONENT'
        and lower(btrim(x.normalized_payload->>'rework_number'))=lower(btrim(wj->>'rework_number'))) then
      raise exception 'BB_REWORK_COMPONENT_REQUIRED: rework ke mandor memerlukan komponen kerja';
    end if;
  elsif upper(wj->>'destination_type')='LAUNDRY' then
    if nullif(btrim(wj->>'contractor_code'),'') is not null or nullif(btrim(wj->>'vendor_code'),'') is null
       or wj->>'vendor_code' is distinct from b->>'vendor_code' then
      raise exception 'BB_REWORK_HOLDER_MISMATCH: rework ke laundry harus ke laundry pemegang baris BS asalnya';
    end if;
    if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_REWORK_COMPONENT'
        and lower(btrim(x.normalized_payload->>'rework_number'))=lower(btrim(wj->>'rework_number'))) then
      raise exception 'BB_REWORK_LAUNDRY_COMPONENT: rework laundry tidak memakai komponen upah mandor';
    end if;
  else raise exception 'destination_type: isi CONTRACTOR atau LAUNDRY';
  end if;
  -- The native rework of a BS with PO and product needs the product's accessory BOM (an explicit empty one is enough).
  v_product:=erp.bf_resolve_import_product_v1(p_batch,b,false);
  select p.identity_root_id,p.model_id into v_root,v_model from erp.products p where p.id=v_product;
  if v_product is null or not exists(select 1 from erp.accessory_bom_versions a where a.product_id=v_root and a.is_active
      and a.effective_from<=((v_cutover+1)::timestamp at time zone 'Asia/Jakarta')
      and (a.effective_to is null or a.effective_to>(v_cutover::timestamp at time zone 'Asia/Jakarta'))) then
    raise exception 'BB_REWORK_ACCESSORY_BOM_REQUIRED: produk BS asal belum punya BOM aksesori yang berlaku (BOM kosong pun harus dicatat)';
  end if;
  if r.entity_type='OPENING_REWORK' then
    return jsonb_build_object('kind','REWORK','open_qty',v_open,'sent_qty',v_sent,'returned_qty',v_returned,'sent_date',v_date);
  end if;
  -- Component row.
  if upper(wj->>'destination_type')<>'CONTRACTOR' then raise exception 'BB_REWORK_LAUNDRY_COMPONENT: rework laundry tidak memakai komponen upah mandor';end if;
  select id into v_component from erp.work_components where component_code=j->>'work_component_code' and is_active;
  if v_component is null then raise exception 'BB_REWORK_COMPONENT_UNKNOWN: komponen kerja aktif tidak ditemukan';end if;
  if (select count(*) from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_REWORK_COMPONENT'
      and lower(btrim(x.normalized_payload->>'rework_number'))=lower(btrim(j->>'rework_number'))
      and x.normalized_payload->>'work_component_code'=j->>'work_component_code')>1 then
    raise exception 'BB_REWORK_COMPONENT_DUPLICATE: komponen yang sama tercatat dua kali pada rework ini';
  end if;
  v_qty:=erp.bb_parse_count_v1(j->>'qty_performed','qty_performed',1);
  if v_qty>v_open then raise exception 'BB_REWORK_COMPONENT_QTY: qty dikerjakan tidak boleh melebihi sisa di rework';end if;
  v_before:=erp.bb_parse_count_v1(j->>'completed_before_bs_qty','completed_before_bs_qty',0);
  if v_before>(b->>'qty')::numeric then raise exception 'BB_REWORK_BASELINE: pcs yang sudah selesai sebelum BS tidak boleh melebihi jumlah BS';end if;
  if exists(select 1 from erp.migration_staging_rows x join erp.migration_staging_rows y on y.batch_id=x.batch_id and y.entity_type='OPENING_REWORK'
      and lower(btrim(y.normalized_payload->>'rework_number'))=lower(btrim(x.normalized_payload->>'rework_number'))
      where x.batch_id=p_batch and x.entity_type='OPENING_REWORK_COMPONENT' and x.id<>r.id
        and y.normalized_payload->>'bs_source_key'=wj->>'bs_source_key' and x.normalized_payload->>'work_component_code'=j->>'work_component_code'
        and x.normalized_payload->>'completed_before_bs_qty' is distinct from j->>'completed_before_bs_qty') then
    raise exception 'BB_REWORK_BASELINE_CONFLICT: pcs selesai sebelum BS untuk komponen yang sama harus sama pada setiap rework BS itu';
  end if;
  v_rate:=erp.bb_parse_amount_v1(j->>'rate_per_pcs','rate_per_pcs',true);
  select po.normalized_payload into v_po from erp.migration_staging_rows po where po.batch_id=p_batch and po.entity_type='OPEN_PO'
    and po.normalized_payload->>'po_number'=b->>'po_number' and po.validation_status='VALID';
  select m.id into v_model from erp.product_models m where m.model_code=v_po->>'model_code';
  select cwr.rate_per_pcs into v_found from erp.contractor_work_rates cwr where cwr.contractor_id=v_contractor and cwr.model_id=v_model
    and cwr.work_component_id=v_component and cwr.effective_from<=(v_cutover::timestamp at time zone 'Asia/Jakarta')
    and (cwr.effective_to is null or cwr.effective_to>(v_cutover::timestamp at time zone 'Asia/Jakarta'))
    order by cwr.effective_from desc,cwr.id desc limit 1;
  if v_found is null then raise exception 'BB_REWORK_RATE_MISSING: tarif mandor untuk model dan komponen ini belum berlaku pada cutover';end if;
  if v_found<>v_rate then raise exception 'BB_REWORK_RATE_MISMATCH: tarif baris (%) berbeda dengan tarif mandor yang berlaku (%)',v_rate,v_found;end if;
  return jsonb_build_object('kind','COMPONENT','work_component_id',v_component,'qty_performed',v_qty,'completed_before_bs_qty',v_before,'rate',v_rate);
end;$function$;
CREATE OR REPLACE FUNCTION erp.save_initial_import_action_v1(p_action text, p_payload jsonb, p_client_request_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
 v_action text:=upper(btrim(p_action)); v_batch uuid; v_type text;
 b erp.migration_batches%rowtype; v_cached jsonb; v_result jsonb; v_row jsonb; v_normal jsonb;
 v_field text; v_text text; v_number numeric; v_line integer; v_seen integer[]:='{}';
 v_total bigint; v_valid bigint; v_errors bigint; v_opening uuid; v_date date;
 v_catalog constant jsonb:='{"LAUNDRY_VENDOR": {"label": "Vendor laundry", "required": ["vendor_code", "vendor_name"], "fields": {"vendor_code": "Kode laundry", "vendor_name": "Nama laundry", "phone": "Telepon", "is_active": "Aktif", "notes": "Catatan"}}, "LOCATION": {"label": "Lokasi dan gudang", "required": ["location_code", "location_name", "location_type"], "fields": {"location_code": "Kode lokasi", "location_name": "Nama lokasi", "location_type": "Jenis lokasi", "is_active": "Aktif"}}, "CHART_ACCOUNT": {"label": "Akun buku besar", "required": ["account_code", "account_name", "account_type", "report_group", "normal_balance"], "fields": {"account_code": "Kode akun", "account_name": "Nama akun", "account_type": "Jenis akun", "report_group": "Kelompok laporan", "normal_balance": "Saldo normal", "parent_account_code": "Kode akun induk", "is_postable": "Boleh dipakai jurnal", "is_active": "Aktif"}}, "CASH_ACCOUNT": {"label": "Rekening kas dan bank", "required": ["cash_account_code", "cash_account_name", "coa_account_code", "account_kind"], "fields": {"cash_account_code": "Kode kas bank", "cash_account_name": "Nama kas bank", "coa_account_code": "Kode akun buku besar", "account_kind": "Jenis rekening", "is_active": "Aktif"}}, "BRAND": {"label": "Merek", "required": ["brand_code", "brand_name"], "fields": {"brand_code": "Kode merek", "brand_name": "Nama merek", "is_active": "Aktif"}}, "SIZE": {"label": "Ukuran", "required": ["size_code"], "fields": {"size_code": "Kode ukuran", "sort_order": "Urutan", "is_active": "Aktif"}}, "MODEL": {"label": "Model produk", "required": ["model_code", "model_name"], "fields": {"model_code": "Kode model", "model_name": "Nama model", "description": "Keterangan", "is_active": "Aktif"}}, "PRODUCT": {"label": "Produk per ukuran", "required": ["sku", "product_name", "model_code", "brand_code", "color_name", "size_code"], "fields": {"sku": "Kode produk", "product_name": "Nama produk", "model_code": "Kode model", "brand_code": "Kode merek", "color_name": "Warna", "size_code": "Kode ukuran", "is_active": "Aktif"}}, "CUSTOMER": {"label": "Pelanggan", "required": ["customer_code", "customer_name"], "fields": {"customer_code": "Kode pelanggan", "customer_name": "Nama pelanggan", "phone": "Telepon", "address": "Alamat", "is_active": "Aktif"}}, "SUPPLIER": {"label": "Supplier", "required": ["supplier_code", "supplier_name"], "fields": {"supplier_code": "Kode supplier", "supplier_name": "Nama supplier", "supplier_type": "Jenis supplier", "phone": "Telepon", "address": "Alamat", "is_active": "Aktif"}}, "CONTRACTOR": {"label": "Mandor", "required": ["contractor_code", "contractor_name"], "fields": {"contractor_code": "Kode mandor", "contractor_name": "Nama mandor", "contractor_type": "Jenis mandor", "attendance_required": "Wajib absensi", "is_active": "Aktif", "notes": "Catatan"}}, "ACCESSORY_CATEGORY": {"label": "Kategori aksesori", "required": ["category_code", "category_name", "base_uom_code"], "fields": {"category_code": "Kode kategori", "category_name": "Nama kategori", "base_uom_code": "Satuan dasar", "is_active": "Aktif", "notes": "Catatan"}}, "MATERIAL": {"label": "Bahan dan aksesori", "required": ["material_sku", "material_name", "material_type", "unit_code"], "fields": {"material_sku": "Kode bahan", "material_name": "Nama bahan", "material_type": "Jenis bahan", "unit_code": "Satuan dasar", "accessory_category_code": "Kode kategori aksesori", "is_active": "Aktif"}}, "MATERIAL_ROLL": {"label": "Stok awal kain per roll", "required": ["material_sku", "roll_number", "opening_qty", "unit_cost", "location_code", "control_key"], "fields": {"material_sku": "Kode bahan", "roll_number": "Nomor roll", "opening_qty": "Jumlah awal", "unit_cost": "Biaya per satuan", "location_code": "Kode gudang", "supplier_code": "Kode supplier", "notes": "Catatan", "control_key": "Kode total pembanding", "opening_source_key": "Kode rincian stok asal"}}, "OPENING_BALANCE_ITEM": {"label": "Stok dan saldo awal", "required": ["balance_type", "control_key"], "fields": {"balance_type": "Jenis saldo", "material_sku": "Kode bahan", "product_sku": "Kode produk", "brand_code": "Kode merek", "model_code": "Kode model", "color_name": "Warna", "size_code": "Kode ukuran", "location_code": "Kode gudang", "contractor_code": "Kode mandor", "customer_code": "Kode pelanggan", "supplier_code": "Kode supplier", "vendor_code": "Kode laundry", "cash_account_code": "Kode kas bank", "stage": "Tahap produksi", "qty": "Jumlah", "unit_cost": "Biaya per satuan", "amount": "Nominal", "quality_grade": "Kualitas", "hpp_input_method": "Cara isi HPP", "hpp_percent_of_price": "Persentase HPP", "notes": "Catatan", "control_key": "Kode total pembanding", "document_number": "Nomor dokumen asal", "document_date": "Tanggal dokumen asal", "due_date": "Tanggal jatuh tempo", "original_amount": "Nominal dokumen awal", "settled_before_cutover": "Sudah dibayar sebelum saldo awal", "opening_source_key": "Kode rincian stok asal", "source_kind": "Jenis sumber saldo", "po_number": "Nomor PO saldo fisik", "accessory_cost_included": "Biaya aksesoris sudah termasuk (true/false)"}}, "OPEN_PO": {"label": "Pesanan produksi berjalan", "required": ["po_number", "model_code", "status", "current_stage"], "fields": {"po_number": "Nomor pesanan", "model_code": "Kode model", "contractor_code": "Kode mandor", "target_qty_pcs": "Target buah", "target_dozens": "Target lusin", "status": "Status", "current_stage": "Tahap produksi", "physical_start_at": "Waktu mulai fisik", "notes": "Catatan"}}, "OPENING_CONTROL": {"label": "Total pembanding saldo awal", "required": ["control_key", "balance_type", "amount"], "fields": {"control_key": "Kode total pembanding", "balance_type": "Jenis saldo", "qty": "Total jumlah", "amount": "Total nominal", "notes": "Catatan"}}, "UNINVOICED_RECEIPT": {"label": "Penerimaan belum ditagih — sisa bahan dan asal biaya", "required": ["receipt_number", "receipt_line_number", "receipt_date", "supplier_code", "material_sku", "location_code", "qty", "unit_cost", "control_key"], "fields": {"receipt_number": "Nomor penerimaan asal", "receipt_line_number": "Nomor baris penerimaan", "receipt_date": "Tanggal penerimaan asal", "supplier_code": "Kode supplier", "material_sku": "Kode bahan", "location_code": "Kode gudang", "qty": "Jumlah belum ditagih", "unit_cost": "Biaya estimasi per satuan", "opening_source_key": "Kode rincian stok asal", "control_key": "Kode total pembanding", "notes": "Catatan", "invoice_document_number": "Nomor invoice asal untuk bagian yang sudah ditagih", "invoiced_qty": "Jumlah yang sudah ditagih sebelum saldo awal"}}, "OPENING_ADVANCE": {"label": "Uang muka tersisa", "required": ["party_type", "party_code", "coa_account_code", "document_number", "document_date", "original_amount", "settled_before_cutover", "amount", "control_key"], "fields": {"party_type": "Jenis pihak", "party_code": "Kode pihak", "coa_account_code": "Kode akun uang muka", "document_number": "Nomor bukti uang muka", "document_date": "Tanggal uang muka", "original_amount": "Nominal asal", "settled_before_cutover": "Terpakai atau kembali sebelum saldo awal", "amount": "Sisa uang muka", "control_key": "Kode total pembanding"}}, "OPENING_COST_ORIGIN": {"label": "Asal biaya yang sudah terpakai sebelum cutover", "fields": {"supplier_code": "Kode supplier", "receipt_number": "Nomor penerimaan asal", "receipt_line_number": "Nomor baris penerimaan", "target_source_key": "Kode rincian WIP/BS/FG tujuan", "qty": "Jumlah bahan yang sudah terpakai", "notes": "Catatan"}, "required": ["supplier_code", "receipt_number", "receipt_line_number", "target_source_key", "qty"]}, "LEGACY_DOCUMENT": {"label": "Dokumen lama yang sudah lunas penuh", "required": ["balance_type", "party_code", "document_number", "document_date", "original_amount", "settled_before_cutover"], "fields": {"balance_type": "Jenis saldo dokumen", "party_code": "Kode pihak", "document_number": "Nomor dokumen asal", "document_date": "Tanggal dokumen asal", "original_amount": "Nominal dokumen awal", "settled_before_cutover": "Sudah dibayar sebelum saldo awal", "notes": "Catatan"}}, "OPENING_CUSTOMER_CREDIT": {"label": "Kredit retur pelanggan yang belum dikembalikan", "required": ["customer_code", "coa_account_code", "document_number", "document_date", "original_amount", "settled_before_cutover", "amount"], "fields": {"customer_code": "Kode pelanggan", "coa_account_code": "Kode akun kredit pelanggan", "document_number": "Nomor nota retur/kredit", "document_date": "Tanggal nota retur/kredit", "original_amount": "Nominal kredit asal", "settled_before_cutover": "Sudah dikembalikan sebelum saldo awal", "amount": "Sisa kredit", "notes": "Catatan"}}, "OPENING_SALE_RETURN": {"label": "Hak retur penjualan lama yang barangnya belum kembali", "required": ["customer_code", "return_number", "invoice_document_number", "product_sku", "qty", "credit_unit_price", "unit_cost", "credit_coa_account_code"], "fields": {"customer_code": "Kode pelanggan", "return_number": "Nomor persetujuan retur", "invoice_document_number": "Nomor invoice asal", "product_sku": "Kode produk", "brand_code": "Kode merek", "model_code": "Kode model", "color_name": "Warna", "size_code": "Kode ukuran", "qty": "Jumlah pcs boleh diretur", "credit_unit_price": "Kredit per pcs", "unit_cost": "Nilai persediaan per pcs", "credit_coa_account_code": "Kode akun kredit pelanggan", "notes": "Catatan"}}, "OPEN_PURCHASE_ORDER": {"label": "PO pembelian yang belum diterima penuh saat saldo awal", "required": ["po_number", "po_line_number", "po_date", "supplier_code", "location_code", "material_sku", "ordered_qty", "received_before_cutover_qty", "cancelled_before_cutover_qty", "remaining_qty", "unit_price"], "fields": {"po_number": "Nomor PO pembelian", "po_line_number": "Nomor baris PO", "po_date": "Tanggal PO", "supplier_code": "Kode supplier", "location_code": "Kode gudang tujuan", "material_sku": "Kode bahan", "ordered_qty": "Jumlah dipesan", "received_before_cutover_qty": "Sudah diterima sebelum saldo awal", "cancelled_before_cutover_qty": "Sudah dibatalkan sebelum saldo awal", "remaining_qty": "Sisa yang masih ditunggu", "unit_price": "Harga estimasi per satuan", "expected_date": "Perkiraan tanggal datang", "notes": "Catatan"}}, "OPENING_PAYROLL_ENTITLEMENT": {"label": "Hak upah, absensi, atau reimburse sebelum saldo awal yang belum disetujui", "required": ["kind", "contractor_code", "document_number", "line_number", "document_date", "rate"], "fields": {"kind": "Jenis hak (SEWING_WORK/ATTENDANCE/ACCESSORY_REIMBURSEMENT)", "contractor_code": "Kode mandor", "document_number": "Nomor dokumen hutang mandor", "line_number": "Nomor baris", "document_date": "Tanggal hak timbul", "rate": "Tarif", "po_number": "Nomor PO (upah jahit)", "work_component_code": "Kode komponen kerja", "earned_qty": "Jumlah dikerjakan", "paid_before_qty": "Jumlah sudah dibayar sebelum saldo awal", "carry_qty": "Jumlah komponen dibawa (carry)", "worker_name": "Nama pekerja (absensi)", "period_start": "Awal periode absensi", "period_end": "Akhir periode absensi", "days": "Jumlah hari dibayar", "category_code": "Kode kategori aksesori", "good_qty": "Jumlah GOOD", "paid_before_amount": "Nominal sudah dibayar sebelum saldo awal", "notes": "Catatan"}}, "OPENING_REWORK": {"label": "Rework yang masih di mandor atau laundry saat saldo awal", "required": ["rework_number", "bs_source_key", "destination_type", "sent_date", "qty_sent_original", "qty_returned_before_cutover", "qty_open"], "fields": {"rework_number": "Nomor rework asal", "bs_source_key": "Kode rincian BS asal (opening_source_key baris BS)", "destination_type": "Tujuan rework (CONTRACTOR/LAUNDRY)", "contractor_code": "Kode mandor rework", "vendor_code": "Kode laundry rework", "sent_date": "Tanggal kirim rework", "qty_sent_original": "Jumlah dikirim", "qty_returned_before_cutover": "Sudah kembali sebelum saldo awal", "qty_open": "Masih di rework saat saldo awal", "notes": "Catatan"}}, "OPENING_REWORK_COMPONENT": {"label": "Komponen upah rework terbuka", "required": ["rework_number", "work_component_code", "completed_before_bs_qty", "qty_performed", "rate_per_pcs"], "fields": {"rework_number": "Nomor rework asal", "work_component_code": "Kode komponen kerja", "completed_before_bs_qty": "Pcs yang komponennya sudah selesai sebelum BS", "qty_performed": "Pcs yang akan dikerjakan", "rate_per_pcs": "Tarif per pcs"}}, "OPEN_SALES_DRAFT": {"label": "Draf penjualan yang masih terbuka saat saldo awal (dengan reservasi)", "required": ["draft_number", "line_number", "draft_date", "customer_code", "location_code", "product_sku", "qty_pcs", "unit_price"], "fields": {"draft_number": "Nomor draf penjualan", "line_number": "Nomor baris draf", "draft_date": "Tanggal draf lama", "customer_code": "Kode pelanggan", "location_code": "Kode gudang barang jadi", "product_sku": "Kode produk", "qty_pcs": "Jumlah pcs yang direservasi", "unit_price": "Harga per pcs", "discount_amount": "Potongan baris", "due_date": "Jatuh tempo", "payment_terms": "Syarat pembayaran", "notes": "Catatan", "product_id": "ID produk fisik asal (opsional; harus cocok dengan identitas baris)", "size_code": "Ukuran fisik asal", "brand_code": "Kode merek asal", "model_code": "Kode model asal", "color_name": "Warna asal"}}, "OPENING_ACCESSORY_NOTE_LINE": {"label": "Baris nota aksesori mandor lama (di balik piutang mandor saldo awal)", "required": ["document_number", "contractor_code", "line_number", "material_sku", "qty", "line_amount"], "fields": {"document_number": "Nomor nota lama (sama dengan dokumen piutang mandor)", "contractor_code": "Kode mandor", "line_number": "Nomor baris nota", "material_sku": "Kode aksesori", "qty": "Jumlah (PCS utuh untuk aksesori hitung)", "line_amount": "Nominal baris nota asal", "notes": "Catatan"}}, "OPENING_ACCESSORY_CUSTODY": {"label": "Aksesori yang bukan stok siap pakai: titipan belum dinilai, belum kembali, titipan pelanggan", "required": ["custody_kind", "custody_key", "qty"], "fields": {"custody_kind": "Jenis (PENDING_VALUE, UNRETURNED, CUSTOMER_GARMENT)", "custody_key": "Kode opname (satu barang fisik satu kode)", "material_sku": "Kode aksesori", "location_code": "Kode area pemeriksaan (PENDING_VALUE)", "condition": "Kondisi (WAITING, USABLE, DAMAGED)", "qty": "Jumlah PCS", "holder": "Pemegang (UNRETURNED)", "owner_kind": "Pemilik (COMPANY atau CUSTOMER)", "customer_code": "Kode pelanggan (CUSTOMER_GARMENT)", "product_sku": "Kode produk (opsional)", "description": "Keterangan barang", "notes": "Catatan", "count_sheet": "Nomor lembar hitung sumber (D09: isi bersama baris lembar, atau pakai lot sumber)", "sheet_line": "Baris/item di lembar hitung", "source_lot": "Lot sumber (pengganti lembar hitung + baris)", "product_id": "ID produk fisik asal (opsional; harus cocok dengan identitas baris)", "size_code": "Ukuran fisik asal", "brand_code": "Kode merek asal", "model_code": "Kode model asal", "color_name": "Warna asal"}}, "OPENING_LAUNDRY_CLAIM": {"label": "Klaim laundry yang terdokumentasi atas WIP di vendor (hilang, tertahan, rusak)", "required": ["claim_number", "source_key", "vendor_code", "claim_type", "qty", "claim_date"], "fields": {"claim_number": "Nomor klaim", "source_key": "Kode rincian WIP laundry (opening_source_key)", "vendor_code": "Kode laundry (sama dengan pemegang WIP)", "claim_type": "Jenis klaim (MISSING, STUCK, DAMAGE)", "qty": "Jumlah PCS yang diklaim", "claim_date": "Tanggal klaim (sebelum atau pada tanggal saldo awal)", "dispatch_number": "Nomor kirim laundry lama", "notes": "Catatan"}}, "OPENING_LAUNDRY_UNINVOICED": {"label": "Hasil laundry yang sudah kembali sebelum cutover tetapi belum ditagih vendor", "required": ["document_number", "vendor_code", "receipt_date", "category", "qty"], "fields": {"document_number": "Nomor terima laundry lama", "vendor_code": "Kode laundry", "receipt_date": "Tanggal terima (sebelum atau pada tanggal saldo awal)", "category": "Kategori tagihan (GOOD, BS, FAILED_ATTEMPT)", "qty": "Jumlah PCS belum ditagih", "estimated_amount": "Estimasi tagihan yang terbukti (kosong = belum diketahui)", "po_number": "Nomor PO asal", "dispatch_number": "Nomor kirim laundry lama", "notes": "Catatan"}}, "OPENING_POCKET_USAGE": {"label": "Kain kantong keluar sebelum cutover", "required": ["document_number", "line_number", "physical_date", "material_sku", "qty", "amount", "allocation_status", "control_key", "control_qty", "control_amount"], "fields": {"document_number": "Nomor lembar pengeluaran asal", "line_number": "Baris asal", "physical_date": "Tanggal keluar sebelum cutover", "material_sku": "Kode bahan", "qty": "Jumlah kain sudah keluar", "amount": "Nilai historis", "allocation_status": "ALLOCATED / UNALLOCATED", "prior_allocation_reference": "Referensi pembagian lama (ALLOCATED)", "control_key": "Identitas total pembanding", "control_qty": "Total jumlah pada lembar pembanding", "control_amount": "Total nilai pada lembar pembanding", "notes": "Catatan", "supplier_code": "Supplier penerimaan belum ditagih (opsional)", "receipt_number": "Nomor penerimaan asal (opsional)", "receipt_line_number": "Baris penerimaan asal (opsional)"}}, "OPENING_POCKET_SEWING": {"label": "Hasil jahit sebelum cutover untuk pembagian kain kantong", "required": ["document_number", "line_number", "physical_date", "contractor_code", "qty", "target_kind", "control_key", "control_qty"], "fields": {"document_number": "Nomor lembar hasil jahit", "line_number": "Baris asal", "physical_date": "Tanggal selesai dijahit sebelum cutover", "contractor_code": "Kode mandor (termasuk khusus)", "qty": "PCS selesai dijahit", "target_kind": "WIP / BS / FINISHED_GOODS / COGS", "target_source_key": "Kode rincian stok awal tujuan", "product_sku": "SKU yang sudah terjual (COGS)", "sold_reference": "Bukti penjualan historis (COGS)", "notes": "Catatan", "control_key": "Identitas total hasil jahit pembanding", "control_qty": "Total PCS pada lembar pembanding", "product_id": "ID produk fisik asal (opsional; harus cocok dengan identitas baris)", "size_code": "Ukuran fisik asal", "brand_code": "Kode merek asal", "model_code": "Kode model asal", "color_name": "Warna asal"}}}'::jsonb;
begin
 perform erp.require_owner_admin();
 perform erp.require_permission('settings.erp.view');
 if v_action is null or v_action not in('CREATE','SAVE_FILE','VALIDATE','FINALIZE','ALLOCATE_CASH_ADVANCE','PREPAYMENT','WIP_OUTPUT','OPENING_SETTLEMENT','CUSTOMER_CREDIT','OPENING_RETURN','PURCHASE_COMMITMENT','PAYROLL_ENTITLEMENT') then raise exception 'Aksi impor tidak dikenal'; end if;
 if p_payload is null or jsonb_typeof(p_payload)<>'object' or octet_length(p_payload::text)>5242880 then
   raise exception 'Isi impor harus berupa objek dan maksimal 5 MB'; end if;
 -- AR: same lock order as native prepare/post, before any batch lock.
 if v_action='WIP_OUTPUT' then perform erp.pocket_period_lock_v1();end if;
 if v_action in('FINALIZE','WIP_OUTPUT','OPENING_RETURN') then
   perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 end if;
 v_cached:=erp._idempotency_begin('save_initial_import_action_v1',p_client_request_id,
   erp._request_hash(jsonb_build_object('action',v_action,'payload',p_payload)));
 if v_cached is not null then return v_cached; end if;
 perform set_config('app.change_reason','Impor awal: '||v_action,true);
 if v_action='CREATE' then
   if p_payload->>'cutover_date' is null or p_payload->>'cutover_date' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then
     raise exception 'Tanggal saldo awal wajib memakai YYYY-MM-DD'; end if;
   v_date:=(p_payload->>'cutover_date')::date;
   if v_date::text<>p_payload->>'cutover_date' or v_date>(statement_timestamp() at time zone 'Asia/Jakarta')::date then
     raise exception 'Tanggal saldo awal tidak valid atau berada di masa depan'; end if;
   v_batch:=erp.create_migration_batch(p_payload->>'batch_code',v_date::timestamp at time zone 'Asia/Jakarta',
     'CSV UTF-8',p_payload->>'notes');
 elsif v_action='WIP_OUTPUT' then
   v_batch:=(p_payload->>'batch_id')::uuid;
   v_result:=erp.complete_initial_import_wip_v1(p_payload);
   v_result:=v_result||jsonb_build_object('request_id',p_client_request_id,'action',v_action,'batch_id',v_batch,'status','POSTED');
   return erp._idempotency_complete('save_initial_import_action_v1',p_client_request_id,v_result);
 elsif v_action in('OPENING_SETTLEMENT','CUSTOMER_CREDIT','OPENING_RETURN','PURCHASE_COMMITMENT','PAYROLL_ENTITLEMENT') then
   -- BB: continuations of a posted import (ALL-P02/S01/S03/Y01), one transaction and one request identity each.
   v_batch:=(p_payload->>'batch_id')::uuid;
   select * into b from erp.migration_batches where id=v_batch for update;
   if b.id is null or b.status<>'POSTED' then raise exception 'BB_IMPORT_NOT_POSTED: lanjutan hanya untuk impor yang sudah disahkan';end if;
   if p_payload->>'expected_revision' is distinct from erp.initial_import_revision_v1(b.id) then
     raise exception 'STALE_VERSION: saldo impor berubah; muat ulang sebelum melanjutkan';end if;
   v_result:=case v_action when 'OPENING_SETTLEMENT' then erp.bb_manage_opening_settlement_v1(p_payload,p_client_request_id)
     when 'CUSTOMER_CREDIT' then erp.bb_manage_customer_credit_v1(p_payload,p_client_request_id)
     when 'PURCHASE_COMMITMENT' then erp.bb_manage_purchase_commitment_v1(p_payload,p_client_request_id)
     when 'PAYROLL_ENTITLEMENT' then erp.bb_manage_payroll_entitlement_v1(p_payload,p_client_request_id)
     else erp.bb_manage_opening_sale_return_v1(p_payload,p_client_request_id) end;
   v_result:=v_result||jsonb_build_object('request_id',p_client_request_id,'action',v_action,'batch_id',v_batch,'status','POSTED',
     'revision',erp.initial_import_revision_v1(v_batch));
   return erp._idempotency_complete('save_initial_import_action_v1',p_client_request_id,v_result);
 elsif v_action='PREPAYMENT' then
   v_batch:=(p_payload->>'batch_id')::uuid;
   select * into b from erp.migration_batches where id=v_batch for update;
   if b.id is null or b.status<>'POSTED' then raise exception 'Uang muka harus berasal dari impor yang sudah disahkan';end if;
   perform erp.manage_initial_prepayment_v1(p_payload);
 elsif v_action='ALLOCATE_CASH_ADVANCE' then
   v_batch:=nullif(p_payload->>'batch_id','')::uuid;
   select * into b from erp.migration_batches where id=v_batch for update;
   if b.id is null or b.status<>'POSTED' then raise exception 'Kasbon harus berasal dari impor yang sudah disahkan';end if;
   perform 1 from erp.payroll_settlements where id=(p_payload->>'payroll_id')::uuid for update;
   perform 1 from erp.opening_subledger_balances where id=(p_payload->>'balance_id')::uuid for update;
   if p_payload->>'expected_revision' is distinct from erp.initial_import_revision_v1(b.id) then
     raise exception 'STALE_VERSION: saldo atau payroll berubah; muat ulang sebelum mengalokasikan';end if;
   if not exists(select 1 from erp.initial_import_financial_sources s join erp.opening_subledger_balances bs on bs.opening_item_id=s.opening_item_id
     where s.batch_id=b.id and s.source_kind='CONTRACTOR_CASH_ADVANCE' and bs.id=(p_payload->>'balance_id')::uuid) then
     raise exception 'Saldo kasbon bukan milik batch ini';end if;
   if coalesce(p_payload->>'amount','') !~ '^[0-9]+([.,][0-9]{1,2})?$' then
     raise exception 'amount: gunakan nominal positif tepat dua desimal atau nol untuk melepas alokasi';end if;
   perform erp.set_opening_cash_advance_payroll_v1((p_payload->>'balance_id')::uuid,
     (p_payload->>'payroll_id')::uuid,replace(p_payload->>'amount',',','.')::numeric,
     (p_payload->>'expected_payroll_version')::bigint);
 else
   v_batch:=nullif(p_payload->>'batch_id','')::uuid;
   select * into b from erp.migration_batches where id=v_batch for update;
   if b.id is null then raise exception 'Batch impor tidak ditemukan'; end if;
   if b.status not in('DRAFT','READY','VALIDATING','POSTING') or exists(
     select 1 from erp.opening_balance_headers where migration_batch_id=b.id and status<>'DRAFT') then
     raise exception 'Impor yang sudah disahkan tidak dapat diedit atau disahkan ulang dengan permintaan baru'; end if;
   if nullif(p_payload->>'expected_revision','') is null
     or p_payload->>'expected_revision'<>erp.initial_import_revision_v1(b.id) then
     raise exception 'STALE_VERSION: isi impor berubah. Muat ulang sebelum melanjutkan'; end if;
   if v_action='SAVE_FILE' then
     v_type:=p_payload->>'entity';
     if v_type is null or not v_catalog ? v_type then raise exception 'Jenis file impor tidak didukung'; end if;
     if jsonb_typeof(p_payload->'rows') is distinct from 'array'
       or jsonb_array_length(p_payload->'rows')>5000 then raise exception 'Maksimal 5000 baris per file'; end if;
     if (select count(*) from erp.migration_staging_rows where batch_id=b.id and entity_type<>v_type)
       +jsonb_array_length(p_payload->'rows')>5000 then raise exception 'Maksimal 5000 baris per batch; pecah menjadi batch terpisah'; end if;
     if exists(select 1 from erp.migration_staging_rows where batch_id=b.id
       and posted_entity_id is not null and entity_type<>'OPENING_BALANCE_ITEM') then
       raise exception 'Batch ini sudah menerapkan master melalui jalur lama; selesaikan di jalur asal'; end if;
     perform 1 from erp.opening_balance_headers where migration_batch_id=b.id order by id for update;
     delete from erp.opening_balance_items i using erp.opening_balance_headers h
       where i.opening_id=h.id and h.migration_batch_id=b.id and h.status='DRAFT';
     update erp.migration_staging_rows set posted_entity_type=null,posted_entity_id=null,posted_at=null
       where batch_id=b.id and entity_type='OPENING_BALANCE_ITEM';
     delete from erp.migration_staging_rows where batch_id=b.id and entity_type=v_type;
     for v_row in select value from jsonb_array_elements(p_payload->'rows') loop
       if jsonb_typeof(v_row)<>'object' or jsonb_typeof(v_row->'payload') is distinct from 'object'
         or coalesce(v_row->>'source_row_no','') !~ '^[1-9][0-9]{0,6}$' then raise exception 'Identitas baris impor tidak valid'; end if;
       v_line:=(v_row->>'source_row_no')::integer;
       if v_line=any(v_seen) then raise exception 'Baris sumber % ditulis dua kali',v_line; end if;
       v_seen:=array_append(v_seen,v_line);v_normal:='{}'::jsonb;
       for v_field,v_text in select key,value #>> '{}' from jsonb_each(v_row->'payload') loop
         if not (v_catalog->v_type->'fields') ? v_field or jsonb_typeof(v_row->'payload'->v_field)<>'string' then
           raise exception 'Baris %, kolom %: nama kolom atau tipe data tidak valid',v_line,v_field; end if;
         v_text:=btrim(v_text);
         if length(v_text)>20000 then raise exception 'Baris %, kolom % terlalu panjang',v_line,v_field; end if;
         if v_field in('qty','opening_qty','unit_cost','amount','original_amount','settled_before_cutover','hpp_percent_of_price','target_dozens','target_qty_pcs','sort_order','credit_unit_price','invoiced_qty') and v_text<>'' then
           if v_text !~ '^-?[0-9]+([.,][0-9]+)?$' then
             raise exception 'Baris %, kolom %: isi angka tanpa pemisah ribuan',v_line,v_field; end if;
           v_text:=replace(v_text,',','.');v_number:=v_text::numeric;
           if (v_field in('amount','original_amount','settled_before_cutover','credit_unit_price') and v_number<>round(v_number,2))
             or (v_field in('qty','opening_qty','unit_cost','target_dozens','invoiced_qty') and v_number<>round(v_number,6))
             or (v_field='hpp_percent_of_price' and v_number<>round(v_number,4))
             or (v_field in('target_qty_pcs','sort_order') and v_number<>trunc(v_number)) then
             raise exception 'Baris %, kolom %: ketelitian angka melebihi kolom tujuan; angka tidak dibulatkan otomatis',v_line,v_field; end if;
         end if;
         v_normal:=v_normal||jsonb_build_object(v_field,v_text);
       end loop;
       perform erp.stage_migration_row(b.id,v_type,v_line,null,
         (v_row->'payload')||jsonb_build_object('_filename',left(coalesce(p_payload->>'filename',''),255)),v_normal);
     end loop;
     update erp.migration_batches set status='DRAFT',validated_at=null,error_message=null where id=b.id;
   else
     if not exists(select 1 from erp.migration_staging_rows where batch_id=b.id) then raise exception 'Unggah data sebelum memeriksa atau mengesahkan'; end if;
     select * into v_total,v_valid,v_errors from erp.validate_migration_batch(b.id);
     perform erp.validate_initial_import_financial_sources_v1(b.id);
     perform erp.validate_initial_import_production_v1(b.id);
     perform erp.validate_initial_import_cost_origins_v1(b.id);
     perform erp.be_validate_pocket_imports_v1(b.id);
     perform erp.validate_initial_import_receipts_v1(b.id);
     perform erp.validate_initial_prepayments_v1(b.id);
     perform erp.bb_validate_financial_imports_v1(b.id);
     perform erp.bb_validate_purchase_imports_v1(b.id);
     perform erp.bb_validate_labour_imports_v1(b.id);
     perform erp.bb_validate_production_imports_v1(b.id);
     perform erp.bb_validate_sales_imports_v1(b.id);
     perform erp.bc_validate_imports_v1(b.id);
     perform erp.bd_validate_imports_v1(b.id);
     perform erp.validate_initial_import_totals_v1(b.id);
     select count(*),count(*) filter(where validation_status='VALID'),count(*) filter(where validation_status='ERROR')
       into v_total,v_valid,v_errors from erp.migration_staging_rows where batch_id=b.id;
     if v_action='FINALIZE' and v_errors=0 then
       -- Domain writers execute inside this same transaction. A refusal in any
       -- consumer rolls back masters, opening stock, journals, and application.
       perform erp.apply_migration_master_rows(b.id);
       perform erp.apply_migration_open_pos(b.id);
       if exists(select 1 from erp.migration_staging_rows where batch_id=b.id
         and entity_type in('OPENING_BALANCE_ITEM','MATERIAL_ROLL')) then
         v_opening:=erp.prepare_migration_opening_balance(b.id,null);
         perform erp.post_opening_balance(v_opening);
       end if;
       perform erp.apply_initial_import_receipts_v1(b.id);
       perform erp.apply_initial_prepayments_v1(b.id);
       perform erp.bb_apply_financial_imports_v1(b.id);
       perform erp.bb_apply_purchase_imports_v1(b.id);
       perform erp.bb_apply_labour_imports_v1(b.id);
       perform erp.bb_apply_production_imports_v1(b.id);
       perform erp.bb_apply_sales_imports_v1(b.id);
       perform erp.bc_apply_imports_v1(b.id);
       perform erp.bd_apply_imports_v1(b.id);
       perform erp.be_apply_pocket_imports_v1(b.id);
       perform erp.finalize_migration_batch(b.id);
     end if;
   end if;
 end if;
 v_result:=jsonb_build_object('request_id',p_client_request_id,'action',v_action,'batch_id',v_batch,
   'status',(select status from erp.migration_batches where id=v_batch),'total_rows',v_total,
   'valid_rows',v_valid,'error_rows',v_errors,'revision',erp.initial_import_revision_v1(v_batch));
 return erp._idempotency_complete('save_initial_import_action_v1',p_client_request_id,v_result);
end;$function$;

do $grants$ declare t text;f record;begin
 foreach t in array ARRAY['bf_rollback_v1','bf_skus_v1','bf_sku_versions_v1','bf_sku_members_v1','bf_wave_skus_v1','bf_po_boms_v1','bf_requests_v1','bf_context_v1'] loop
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


update erp.bf_rollback_v1 set payload=payload||jsonb_build_object('installed',(
 select jsonb_object_agg(p.oid::regprocedure::text,md5(pg_get_functiondef(p.oid))) from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname||'.'||p.proname=any(array['erp.commit_accessory_bom_for_lot','erp.ensure_po_work_component_snapshots','erp.validate_work_completion','erp.guard_work_completion_posting_consistency','erp.seed_bs_case_component_baseline','erp.classify_bs_case_v2','erp.cp6_lot_work_cost_v2620c','erp.assert_new_stock_cutoff_coverage_v1','erp.bd_compute_pricing_v1','erp.bd_attach_delivery_pricing_v1','erp.bd_post_priced_delivery_v1','erp.save_laundry_qc_action_v1','erp.prepare_rework_component_line','erp.run_v263c_bs_rework_integrity_checks','erp.get_hpp_completeness','erp.save_initial_import_action_v1','erp.bb_check_sales_import_row_v1','erp.bb_apply_sales_imports_v1','erp.bc_check_import_row_v1','erp.bc_apply_imports_v1','erp.be_check_pocket_import_v1','erp.be_apply_pocket_imports_v1','erp.bb_check_rework_import_row_v1','erp.bf_version_at_v1','erp.bf_guard_economic_v1','erp.bf_legacy_basis_v1','erp.bf_save_groups_v1','erp.bf_validate_rates_v1','erp.bf_work_rate_v1','erp.bf_context_rate_v1','erp.bf_bom_for_lot_v1','erp.bf_bind_wave_v1','erp.bf_work_capacity_v1','erp.bf_snapshot_sku_v1','erp.bf_wave_revision_v1','erp.bf_group_sku_v1','erp.bf_ensure_work_v1','erp.bf_snapshot_matches_v1','erp.bf_assert_work_scope_v1','erp.bf_laundry_rate_v1','erp.bf_merge_charges_v1','erp.bf_package_charges_v1','erp.bf_complete_shares_v1','erp.bf_component_charge_v1','erp.bf_resolve_import_product_v1','erp.save_sku_action_v1','erp.get_sku_workspace_v1','erp.get_sku_hpp_v1','public.erp_save_sku_action_v1','public.erp_get_sku_workspace_v1','public.erp_get_sku_hpp_v1'])));

insert into erp.schema_migrations(version,description) values('v2.6.20bf','Commercial SKU ranges; physical-size lineage preserved');
commit;
