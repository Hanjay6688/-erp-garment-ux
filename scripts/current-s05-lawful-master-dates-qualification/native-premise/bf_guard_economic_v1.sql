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
 if exists(select 1 from erp.products p join erp.bf_skus_v1 s on s.brand_id=p.brand_id and s.model_id=p.model_id and s.color_name=p.color_name
   where p.id in(r,previous_root) and (s.sku=p.sku or exists(select 1 from erp.bf_sku_versions_v1 v join erp.bf_sku_members_v1 m on m.version_id=v.id
     join erp.products member on member.id=m.product_root where v.sku_id=s.id and member.sku=p.sku))) then
   raise exception 'BF_MEMBER_ADOPTION_REQUIRED: hubungkan ukuran baru ke master SKU sebelum menetapkan harga/resep';end if;
 if TG_OP='DELETE' then return old;else return new;end if;
end;$function$;
