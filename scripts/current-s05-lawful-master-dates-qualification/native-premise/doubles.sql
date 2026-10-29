-- Declared local SQL doubles, NOT a Native financial database or Auth fixture.
-- Exact six Native function bodies are loaded separately from pinned sources.
create schema erp;
create function erp.require_owner_admin() returns void language plpgsql as $$begin
 if current_setting('s05.local_denied',true)='true' then raise exception 'LOCAL_OWNER_DOUBLE_DENIED';end if;
end$$;
create function erp.current_app_user_id()returns uuid language sql as $$select '00000000-0000-4000-8000-000000000001'::uuid$$;
create function erp._cp3_assert_closed_json_object(jsonb,text[],text[],text)returns void language plpgsql as $$begin return;end$$;
create function erp.bd_at_v1(text,text)returns timestamptz language sql as $$select $1::timestamptz$$;
create function erp.bc_text_v1(jsonb,text,boolean,integer)returns text language sql as $$select $1->>$2$$;
create table erp.products(id uuid primary key,identity_root_id uuid,brand_id uuid,model_id uuid,color_name text,sku text);
create table erp.accessory_bom_versions(id uuid primary key default gen_random_uuid(),product_id uuid not null,version_label text,effective_from timestamptz not null default now(),effective_to timestamptz,is_active boolean not null default true,notes text,created_at timestamptz default now(),created_by uuid,check(effective_to is null or effective_to>effective_from));
create table erp.accessory_bom_items(id uuid primary key default gen_random_uuid(),bom_version_id uuid not null,category_id uuid not null,qty_per_good_fg_base numeric(18,6)not null,hpp_method text not null,hpp_standard_rate numeric(18,6),hpp_uom_code text,reimbursement_rate numeric(18,6)not null,reimbursement_uom_code text not null,notes text);
create table erp.po_accessory_bom_commitments(id uuid primary key default gen_random_uuid(),po_id uuid,product_id uuid,bom_version_id uuid,committed_at timestamptz);
create table erp.fg_accessory_cost_snapshots(id uuid primary key default gen_random_uuid(),bom_version_id uuid,bom_item_id uuid,costing_basis_at timestamptz);
create table erp.audit_logs(id bigserial primary key,entity_type text,entity_id uuid,action text,changed_by uuid,change_reason text,new_data jsonb);
create table erp.bf_context_v1(backend_pid int,transaction_id bigint);
create table erp.bf_skus_v1(id uuid,brand_id uuid,model_id uuid,color_name text,sku text,revision bigint);
create table erp.bf_sku_versions_v1(id uuid,sku_id uuid,revision bigint,effective_from timestamptz,effective_to timestamptz,settings jsonb,reason text,actor uuid,request_id uuid);
create table erp.bf_sku_members_v1(version_id uuid,product_root uuid,price_version_id uuid,bom_version_id uuid);
create table erp.local_ledger_double(id int,amount numeric(20,2));
create table erp.local_stock_double(id int,qty int);
insert into erp.local_ledger_double values(1,42.31);
insert into erp.local_stock_double values(1,7);
