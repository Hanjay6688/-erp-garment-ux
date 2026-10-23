-- OW-09 deliberate raw reader stubs: the smallest Native shapes the eight list
-- readers touch (seven CP7 readers and the CP6 accessory note reader). Business
-- proof stays in the Native qualification cases (scripts/cp7_ow09_lists).
create role cp7_finance_read nologin;create role cp7_sales_read nologin;create role cp7_sales_write nologin;create role cp7_fg_read nologin;
create schema erp;create schema cp7_finance authorization cp7_finance_read;create schema cp7_sales authorization cp7_sales_read;
create schema cp7_payroll;create schema cp7_fg authorization cp7_fg_read;create schema cp7_material;
create function erp.has_permission(text)returns boolean language sql as $$select true$$;
create table erp.locations(id uuid primary key,location_name text,is_active boolean default true,location_type text default 'FG_WAREHOUSE');
create table erp.cash_accounts(id uuid primary key,coa_account_id uuid,cash_account_code text,cash_account_name text,account_kind text,is_active boolean default true);
create table erp.account_daily_balances(account_id uuid,balance_date date,debit_total numeric,credit_total numeric);
create table erp.journal_entries(id uuid primary key,journal_number text,source_type text,source_id uuid,reversal_of_id uuid,status text,economic_date date,transaction_date date,posting_at timestamptz);
create table erp.journal_lines(id uuid primary key default gen_random_uuid(),journal_entry_id uuid,account_id uuid,debit numeric,credit numeric);
create function erp.account_id(text)returns uuid language sql as $$select '0a000000-0000-4000-8000-000000000001'::uuid$$;
create function erp.get_owner_financial_snapshot_v2(date,date,date)returns jsonb language sql as $$select '{"performance":{"sales_revenue_gl":"100.00","gross_profit":"40.00"}}'::jsonb$$;
create function cp7_finance.access_now()returns void language plpgsql as $$begin end$$;
create function cp7_finance.exact_numbers(jsonb)returns jsonb language sql as $$select $1$$;
create table erp.sales_headers(id uuid primary key,row_version bigint);
create table erp.sales_payments(id uuid primary key,sale_id uuid,payment_number text,payment_date timestamptz,amount numeric,cash_account_id uuid,payment_method text,reference_number text,notes text,status text,replaces_payment_id uuid);
create table erp.sales_returns(id uuid primary key,sale_id uuid,return_number text,physical_at timestamptz,status text,notes text);
create table erp.sales_return_items(id uuid primary key,return_id uuid,sale_stock_allocation_id uuid,product_id uuid,lot_id uuid,location_id uuid,qty_pcs integer,quality_grade text,refund_amount numeric,notes text);
create table erp.products(id uuid primary key,sku text,product_name text,size_id uuid);
create table erp.fg_lots(id uuid primary key,lot_number text);
create function cp7_sales.access_now()returns boolean language sql as $$select true$$;
create function cp7_sales.review_token(uuid)returns text language sql as $$select md5($1::text)$$;
create table erp.contractors(id uuid primary key,contractor_name text,is_active boolean default true,contractor_type text default 'MANDOR');
create table erp.payroll_settlements(id uuid primary key,payroll_number text,contractor_id uuid,period_start date,period_end date,status text,row_version bigint);
create table cp7_payroll.notes(id uuid primary key,note_number text,contractor_id uuid,note_date date,period_start date,period_end date,notes text,status text,row_version bigint,
 target_payroll_id uuid,target_version text,posted_payroll_id uuid,posted_at timestamptz,void_reason text,created_at timestamptz,updated_at timestamptz,cards jsonb);
create function cp7_payroll.access_now(text)returns jsonb language sql as $$select '{"financial":false,"can_post_nota":false}'::jsonb$$;
create table erp.fg_adjustments(id uuid primary key,adjustment_number text,location_id uuid,physical_at timestamptz,reason_code text,reason text,notes text,status text,row_version bigint);
create table erp.fg_adjustment_items(id uuid primary key,adjustment_id uuid);
create table cp7_fg.adjustment_documents(adjustment_id uuid,source_signature text);
create function cp7_fg.adjust_access()returns jsonb language sql as $$select '{"can_value":false,"can_adjust":false}'::jsonb$$;
create table erp.fg_stock_movements(id uuid primary key,product_id uuid,lot_id uuid,location_id uuid,quality_grade text,physical_at timestamptz,system_created_at timestamptz,movement_type text,source_type text,source_id uuid,reversal_of_id uuid,customer_id uuid,notes text,book_order bigint,qty_signed numeric);
create table erp.customers(id uuid primary key,customer_name text);
create table cp7_fg.correction_movements(member_id uuid,origin_id uuid,correction_id uuid,recorded_at timestamptz);
create function erp.bf_commercial_sku_at_v1(uuid,timestamptz)returns text language sql as $$select 'SKU-OW09'::text$$;
create function cp7_fg.access_now(text)returns jsonb language sql as $$select '{"can_value":false}'::jsonb$$;
create function cp7_fg.lot_value(uuid,numeric)returns jsonb language sql as $$select '{"state":"UNKNOWN","unit_cost":null}'::jsonb$$;
create function cp7_fg.positions(text,boolean)returns table(product_id uuid,product_sku text,commercial_sku text,product_name text,size_code text,brand_name text,lot_id uuid,lot_number text,location_id uuid,location_name text,quality_grade text)
 language sql as $$select distinct m.product_id,'SKU','SKU','Product','M','Brand',m.lot_id,m.lot_id::text,m.location_id,'Warehouse',m.quality_grade from erp.fg_stock_movements m$$;
create table erp.material_adjustments(id uuid primary key,adjustment_number text,location_id uuid,physical_at timestamptz,reason_code text,status text,row_version bigint,notes text);
create table erp.material_adjustment_items(id uuid primary key,adjustment_id uuid);
create table cp7_material.count_documents(adjustment_id uuid,input jsonb,source_signature text);
create function cp7_material.access_now()returns jsonb language sql as $$select '{"can_value":false,"can_adjust":false,"can_reverse":false}'::jsonb$$;
grant usage on schema erp to cp7_finance_read,cp7_sales_read,cp7_fg_read;
grant select on all tables in schema erp,cp7_fg to cp7_finance_read,cp7_sales_read,cp7_fg_read;
-- Accessory note reader (erp.get_accessory_issue_workspace_v1): the two real helpers' semantics, the tables it reads.
create function erp.require_permission(text)returns void language plpgsql as $$begin end$$;
create function erp._cp3_assert_closed_json_object(p_value jsonb,p_required_keys text[],p_allowed_keys text[],p_label text)returns void language plpgsql as $$
declare v_key text;
begin
 if p_value is null or jsonb_typeof(p_value)is distinct from 'object' then raise exception '% must be a JSON object',coalesce(p_label,'payload');end if;
 foreach v_key in array coalesce(p_required_keys,array[]::text[])loop
  if not(p_value?v_key)or coalesce(jsonb_typeof(p_value->v_key),'missing')='null' then raise exception '% requires non-null key %',coalesce(p_label,'payload'),v_key;end if;
 end loop;
 select k into v_key from jsonb_object_keys(p_value)as x(k)where not(k=any(coalesce(p_allowed_keys,array[]::text[])))order by k limit 1;
 if v_key is not null then raise exception '% contains unexpected key %',coalesce(p_label,'payload'),v_key;end if;
end$$;
create function erp._cp3_business_date(p_value timestamptz)returns date language sql immutable as $$select case when p_value is null then null else(p_value at time zone 'Asia/Jakarta')::date end$$;
create table erp.contractor_material_issues(id uuid primary key,issue_number text,contractor_id uuid,location_id uuid,po_id uuid,physical_at timestamptz,status text,row_version bigint,notes text);
create table erp.uom_definitions(unit_code text primary key,dimension text,is_active boolean default true);
create table erp.accessory_categories(id uuid primary key,category_name text,base_uom_code text,is_active boolean default true);
create table erp.materials(id uuid primary key,material_sku text,material_name text,material_type text,unit_code text,accessory_category_id uuid,is_active boolean default true);
create table erp.contractor_material_issue_items(id uuid primary key,issue_id uuid,material_id uuid,qty numeric,manual_retail_unit_price numeric,unit_sale_price_snapshot numeric,
 base_qty_per_transaction_uom numeric,transaction_uom_code text,accessory_price_version_id uuid,total_receivable numeric,payroll_status text);
create table erp.bc_note_roundings_v1(id uuid primary key,issue_id uuid,amount numeric);
create table erp.bc_documents_v1(id uuid primary key,row_version bigint,status text);
create table erp.payroll_deductions(payroll_id uuid,contractor_issue_item_id uuid);
create table erp.bc_free_issue_lines_v1(issue_id uuid,material_id uuid);
create table erp.material_stock_movements(material_id uuid,location_id uuid,qty_signed numeric);
create table erp.bc_accessory_zones_v1(location_id uuid);
create table erp.production_orders(id uuid primary key,po_number text,contractor_id uuid,status text);
create function erp.bc_note_item_collectible_v1(uuid)returns numeric language sql as $$select 0::numeric$$;
create function erp.accessory_issue_quote_v1(uuid,uuid,timestamptz)returns jsonb language sql as $$select jsonb_build_object('id',$1,'name','Kancing')$$;
create function erp.bc_free_basis_v1(uuid,uuid,timestamptz)returns jsonb language sql as $$select null::jsonb$$;
