 // These providers are deliberately named and retained in the input. Native
 // permission functions do not become Auth evidence through this model.
 await db.exec(`
 create table public.model_legacy_visibility(show_money boolean not null);
 insert into public.model_legacy_visibility values(true);
 create function erp.has_permission(p_permission text)returns boolean language sql stable as
 $$select case when p_permission='finance.hpp.view'then show_money else true end from public.model_legacy_visibility$$;
 create table public.model_legacy_idempotency(namespace text,request_id uuid,request_hash text,result jsonb,primary key(namespace,request_id));
 create function erp._request_hash(p jsonb)returns text language sql immutable as $$select md5(p::text)$$;
 create function erp._idempotency_begin(n text,k uuid,h text)returns jsonb language plpgsql as $$
 declare r public.model_legacy_idempotency%rowtype;begin
  select *into r from public.model_legacy_idempotency where namespace=n and request_id=k;
  if found then
   if r.request_hash is distinct from h then raise exception 'MODEL_IDEMPOTENCY_PAYLOAD_CHANGED';end if;
   return r.result;
  end if;
  insert into public.model_legacy_idempotency values(n,k,h,null);return null;end$$;
 create function erp._idempotency_complete(n text,k uuid,r jsonb)returns jsonb language plpgsql as $$begin
  update public.model_legacy_idempotency set result=r where namespace=n and request_id=k;
  if not found then raise exception 'MODEL_IDEMPOTENCY_BEGIN_REQUIRED';end if;return r;end$$;
 alter table erp.be_execution_context_v1 add primary key(backend_pid,transaction_id);
 alter table cp7_sku_conversion.execution_v1 add primary key(backend_pid,transaction_id);
 alter table cp7_sku_conversion.members_v1 add primary key(conversion_id);
 alter table cp7_sku_conversion.members_v1 add unique(group_id,line_no);
 `);
 for(const definition of Object.values(input.legacy_helpers))await db.exec(definition);
 await db.exec(input.legacy_raw_revision_original.replace('FUNCTION erp.be_source_revision_v1(',
  'FUNCTION erp.model_legacy_original_physical_revision('));
 for(const definition of Object.values(input.legacy_definitions))await db.exec(definition);
 await db.exec(input.legacy_private_preview);
 const originalStatusDefault=input.columns['erp.bc_outstanding_returns_v1'].find(c=>c[0]==='status')[13];
 assert.equal(originalStatusDefault,"'OPEN'::text");
 await db.exec('alter table erp.bc_outstanding_returns_v1 alter column status set default '+originalStatusDefault);
 const originalSyncDefault=input.columns['erp.be_execution_context_v1'].find(c=>c[0]==='syncing_nonpo')[13];
 assert.equal(originalSyncDefault,'false');
 await db.exec('alter table erp.be_execution_context_v1 alter column syncing_nonpo set default '+originalSyncDefault);
 await db.exec("update erp.products set is_active=true,effective_from='2020-01-01T00:00:00Z',sku=id::text;"+
  "update erp.fg_lots set produced_at=coalesce(produced_at,'2026-01-01T00:00:00Z');");
 // The retained older model seeded movement rows directly. Exact Native
 // movement writers also require their materialized balances to agree first.
 await db.exec(`insert into erp.fg_inventory_balances(product_id,location_id,quality_grade,cached_qty_pcs)
  select product_id,location_id,quality_grade,sum(qty_signed)::integer from erp.fg_stock_movements
  group by product_id,location_id,quality_grade
  on conflict(product_id,location_id,quality_grade)do update set cached_qty_pcs=excluded.cached_qty_pcs;
  update erp.fg_lots l set cached_qty_pcs=(select coalesce(sum(m.qty_signed),0)::integer from erp.fg_stock_movements m where m.lot_id=l.id);
  update erp.fg_lots set is_open=cached_qty_pcs>0;`);
 assert.equal(Number(await scalar(`select count(*)from erp.fg_inventory_balances b where b.cached_qty_pcs is distinct from
  (select coalesce(sum(m.qty_signed),0)::integer from erp.fg_stock_movements m where m.product_id=b.product_id
   and m.location_id=b.location_id and m.quality_grade=b.quality_grade)`)),0);
 assert.equal(Number(await scalar(`select count(*)from erp.fg_lots l where l.cached_qty_pcs is distinct from
  (select coalesce(sum(m.qty_signed),0)::integer from erp.fg_stock_movements m where m.lot_id=l.id)`)),0);
 await insert('erp.uom_definitions',{unit_code:'PCS',dimension:'COUNT'});
 await insert('erp.materials',{id:id(97601),unit_code:'PCS',is_active:true});
