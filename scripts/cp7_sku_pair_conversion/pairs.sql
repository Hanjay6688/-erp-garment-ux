-- One commercial SKU group is one endpoint, irrespective of its physical sizes.
create schema cp7_sku_conversion authorization postgres;
revoke all on schema cp7_sku_conversion from public,anon,authenticated,service_role;
create table cp7_sku_conversion.pairs_v1(
 left_id uuid not null references erp.bf_skus_v1(id),right_id uuid not null references erp.bf_skus_v1(id),
 primary key(left_id,right_id),check(left_id<right_id),unique(left_id),unique(right_id)
);
create table cp7_sku_conversion.pair_events_v1(
 request_id uuid primary key,actor uuid not null,source_id uuid not null,target_id uuid,
 payload jsonb not null,response jsonb not null,recorded_at timestamptz not null default statement_timestamp()
);
alter table cp7_sku_conversion.pairs_v1 enable row level security;
alter table cp7_sku_conversion.pair_events_v1 enable row level security;
create policy deny_pairs on cp7_sku_conversion.pairs_v1 for all using(false)with check(false);
create policy deny_pair_events on cp7_sku_conversion.pair_events_v1 for all using(false)with check(false);
create function cp7_sku_conversion.guard_pair_v1()returns trigger
language plpgsql volatile security definer set search_path=''as $$
begin
 perform pg_advisory_xact_lock(hashtextextended('CP7_SKU_PAIR_MASTER_V1',0));
 if exists(select 1 from cp7_sku_conversion.pairs_v1 p
  where(new.left_id in(p.left_id,p.right_id)or new.right_id in(p.left_id,p.right_id))
   and(TG_OP='INSERT'or(p.left_id,p.right_id)is distinct from(old.left_id,old.right_id)))then
  raise exception 'CP7_SKU_PAIR_ALREADY_LINKED: setiap SKU hanya memiliki satu padanan';end if;
 return new;
end $$;
create trigger pair_endpoint_unique before insert or update on cp7_sku_conversion.pairs_v1
 for each row execute function cp7_sku_conversion.guard_pair_v1();
create function cp7_sku_conversion.immutable_v1()returns trigger language plpgsql security invoker set search_path=''as $$
begin raise exception 'CP7_SKU_CONVERSION_APPEND_ONLY';end $$;
create trigger pair_events_immutable before update or delete on cp7_sku_conversion.pair_events_v1
 for each row execute function cp7_sku_conversion.immutable_v1();

create function cp7_sku_conversion.partner_v1(p_group uuid)returns uuid
language sql stable security definer set search_path=''as $$
 select case when left_id=p_group then right_id else left_id end
 from cp7_sku_conversion.pairs_v1 where p_group in(left_id,right_id)
$$;
create function cp7_sku_conversion.pair_revision_v1()returns text
language sql stable security definer set search_path=''as $$
 select md5(jsonb_build_object('pairs',(select coalesce(jsonb_agg(to_jsonb(p)order by p.left_id,p.right_id),'[]'::jsonb)from cp7_sku_conversion.pairs_v1 p),
 'groups',(select coalesce(jsonb_agg(jsonb_build_array(s.id,s.revision)order by s.id),'[]'::jsonb)from erp.bf_skus_v1 s))::text)
$$;
create function cp7_sku_conversion.group_v1(p_group uuid)returns jsonb
language sql stable security definer set search_path=''as $$
 select jsonb_build_object('id',s.id,'sku',s.sku,'brand_name',b.brand_name,'model_name',m.model_name,
 'members',coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'size',z.size_code)order by z.sort_order,z.size_code,p.id)
 from erp.bf_sku_members_v1 sm join erp.products p on p.id=sm.product_root and p.is_active
 join erp.sizes z on z.id=p.size_id where sm.version_id=v.id),'[]'::jsonb))
 from erp.bf_skus_v1 s join erp.brands b on b.id=s.brand_id join erp.product_models m on m.id=s.model_id
 join lateral(select x.id from erp.bf_sku_versions_v1 x where x.sku_id=s.id and x.effective_from<=statement_timestamp()
  and(x.effective_to is null or x.effective_to>statement_timestamp())order by x.revision desc limit 1)v on true
 where s.id=p_group
$$;

create function cp7_sku_conversion.save_pair_v1(p_payload jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare src uuid;dst uuid;prior cp7_sku_conversion.pair_events_v1%rowtype;answer jsonb;removed jsonb;
begin
 perform erp.require_owner_admin();perform erp.require_permission('master.product.manage');
 if p_request is null then raise exception 'CP7_SKU_PAIR_REQUEST_REQUIRED';end if;
 perform erp._cp3_assert_closed_json_object(p_payload,array['source_group_id','expected_version','reason'],
 array['source_group_id','target_group_id','expected_version','reason'],'padanan SKU');
 -- The screen sends an explicit JSON null to delete. The shared validator's
 -- required list means NON-NULL, so require target-key presence separately.
 if not(p_payload?'target_group_id')then raise exception 'CP7_SKU_PAIR_TARGET_KEY_REQUIRED: kirim SKU tujuan atau null untuk menghapus padanan';end if;
 perform erp.bc_text_v1(p_payload,'reason',true,1000);
 src:=erp.bd_uuid_v1(p_payload,'source_group_id',true);dst:=erp.bd_uuid_v1(p_payload,'target_group_id',false);
 perform pg_advisory_xact_lock(hashtextextended('CP7_SKU_PAIR_MASTER_V1',0));
 perform erp.require_owner_admin();perform erp.require_permission('master.product.manage');
 -- Authorization precedes replay; master edits never use a stock/HPP writer.
 select *into prior from cp7_sku_conversion.pair_events_v1 where request_id=p_request;
 if found then
  if prior.actor is distinct from erp.current_app_user_id()or prior.payload<>p_payload then raise exception 'CP7_SKU_PAIR_REQUEST_REUSED';end if;
  return prior.response||jsonb_build_object('replayed',true);
 end if;
 if src=dst then raise exception 'CP7_SKU_PAIR_SELF: pilih SKU lain';end if;
 perform 1 from erp.bf_skus_v1 where id in(src,dst)order by id for share;
 perform erp.require_owner_admin();perform erp.require_permission('master.product.manage');
 if cp7_sku_conversion.group_v1(src)is null or jsonb_array_length(cp7_sku_conversion.group_v1(src)->'members')=0
  or(dst is not null and(cp7_sku_conversion.group_v1(dst)is null or jsonb_array_length(cp7_sku_conversion.group_v1(dst)->'members')=0))then
  raise exception 'CP7_SKU_PAIR_INACTIVE: SKU tanpa anggota aktif tidak dapat dipilih';end if;
 if p_payload->>'expected_version'is distinct from cp7_sku_conversion.pair_revision_v1()then
  raise exception 'STALE_VERSION: padanan atau anggota SKU berubah; muat ulang sebelum menyimpan';end if;
 select coalesce(jsonb_agg(to_jsonb(p)order by left_id,right_id),'[]'::jsonb)into removed
 from cp7_sku_conversion.pairs_v1 p where src in(left_id,right_id)or dst in(left_id,right_id);
 delete from cp7_sku_conversion.pairs_v1 where src in(left_id,right_id)or dst in(left_id,right_id);
 if dst is not null then insert into cp7_sku_conversion.pairs_v1 values(least(src,dst),greatest(src,dst));end if;
 answer:=jsonb_build_object('request_id',p_request,'action','SAVE_PAIR','status','SAVED','source_group_id',src,
 'target_group_id',dst,'revision',cp7_sku_conversion.pair_revision_v1(),'removed',removed);
 insert into cp7_sku_conversion.pair_events_v1(request_id,actor,source_id,target_id,payload,response)
 values(p_request,erp.current_app_user_id(),src,dst,p_payload,answer);
 return answer;
end $$;

create function cp7_sku_conversion.sku_workspace_v1(p_filters jsonb)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare answer jsonb;f jsonb:=coalesce(p_filters,'{}'::jsonb);src uuid;q text;page_no int;options jsonb;total int;
begin
 answer:=erp.get_sku_workspace_v1(f-'pair_source_id'-'pair_query'-'pair_page');
 src:=erp.bd_uuid_v1(f,'pair_source_id',false);q:=lower(coalesce(erp.bc_text_v1(f,'pair_query',false,120),''));
 if f?'pair_page'and(jsonb_typeof(f->'pair_page')<>'number'or f->>'pair_page'!~'^[1-9][0-9]{0,5}$')then raise exception 'CP7_SKU_PAIR_PAGE';end if;
 page_no:=coalesce((f->>'pair_page')::int,1);
 with candidates as materialized(
  select s.id,b.brand_name,s.sku from erp.bf_skus_v1 s join erp.brands b on b.id=s.brand_id
  where src is not null and s.id<>src and(q=''or lower(b.brand_name||' '||s.sku)like '%'||q||'%')
   and exists(select 1 from erp.bf_sku_versions_v1 v join erp.bf_sku_members_v1 sm on sm.version_id=v.id
    join erp.products p on p.id=sm.product_root and p.is_active where v.sku_id=s.id and v.effective_from<=statement_timestamp()
     and(v.effective_to is null or v.effective_to>statement_timestamp()))),
 pg as(select *from candidates order by brand_name,sku,id limit 50 offset(page_no-1)*50)
 select(select count(*)from candidates),coalesce((select jsonb_agg(cp7_sku_conversion.group_v1(id)order by brand_name,sku,id)from pg),'[]'::jsonb)
 into total,options;
 answer:=answer||jsonb_build_object('groups',coalesce((select jsonb_agg(g||jsonb_build_object('counterpart',cp7_sku_conversion.group_v1(cp7_sku_conversion.partner_v1((g->>'id')::uuid))))
 from jsonb_array_elements(answer->'groups')g),'[]'::jsonb),'pairing',jsonb_build_object('revision',cp7_sku_conversion.pair_revision_v1(),
 'source',cp7_sku_conversion.group_v1(src),'current',cp7_sku_conversion.group_v1(cp7_sku_conversion.partner_v1(src)),
 'options',options,'total',total,'page',page_no,'page_size',50,'can_edit',erp.current_app_role()in('OWNER','ADMIN')and erp.has_permission('master.product.manage')));
 return answer;
end $$;

create function cp7_sku_conversion.sku_action_v1(p_action text,p_payload jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
begin
 if upper(btrim(p_action))='SAVE_PAIR'then return cp7_sku_conversion.save_pair_v1(p_payload,p_request);end if;
 return erp.save_sku_action_v1(p_action,p_payload,p_request);
end $$;
