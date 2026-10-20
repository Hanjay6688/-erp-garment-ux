create schema erp;create schema cp7_note;create schema cp7_sales_return_correction;create schema cp7_payment_correction;create sequence erp.fg_stock_book_order_seq;
create role anon;
create role authenticated;
create role service_role;
create role cp7_capture;
create role cp7_sales_read;
create role cp7_sales_write;
create table "erp"."customers" (
  "id" uuid default gen_random_uuid() not null,
  "customer_code" character varying(30) not null,
  "customer_name" character varying(150) not null,
  "phone" character varying(50),
  "address" text,
  "is_active" boolean default true not null,
  "created_at" timestamp with time zone default now() not null,
  "updated_at" timestamp with time zone default now() not null
);
create table "erp"."chart_accounts" (
  "id" uuid default gen_random_uuid() not null,
  "account_code" character varying(30) not null,
  "account_name" character varying(150) not null,
  "account_type" character varying(20) not null,
  "report_group" character varying(40) not null,
  "parent_account_id" uuid,
  "normal_balance" character varying(10) not null,
  "is_postable" boolean default true not null,
  "is_active" boolean default true not null,
  "created_at" timestamp with time zone default now() not null
);
create table "erp"."accounting_account_mappings" (
  "mapping_key" character varying(50) not null,
  "account_id" uuid not null,
  "notes" text
);
create table "erp"."sales_headers" (
  "id" uuid default gen_random_uuid() not null,
  "sale_number" character varying(60) not null,
  "customer_id" uuid not null,
  "sale_date" timestamp with time zone not null,
  "due_date" date,
  "status" character varying(20) default 'DRAFT'::character varying not null,
  "payment_terms" character varying(100),
  "notes" text,
  "created_by" uuid,
  "created_at" timestamp with time zone default now() not null,
  "updated_at" timestamp with time zone default now() not null,
  "source_location_id" uuid,
  "row_version" bigint default 1 not null
);
create table "erp"."sales_items" (
  "id" uuid default gen_random_uuid() not null,
  "sale_id" uuid not null,
  "product_id" uuid not null,
  "qty_pcs" integer not null,
  "unit_price_snapshot" numeric(18,2) not null,
  "discount_amount" numeric(18,2) default 0 not null,
  "line_total" numeric(20,2) generated always as ((qty_pcs::numeric * unit_price_snapshot - discount_amount)) stored,
  "notes" text
);
create table "erp"."sales_returns" (
  "id" uuid default gen_random_uuid() not null,
  "return_number" character varying(60) not null,
  "sale_id" uuid not null,
  "customer_id" uuid not null,
  "physical_at" timestamp with time zone not null,
  "status" character varying(20) default 'DRAFT'::character varying not null,
  "notes" text,
  "created_by" uuid,
  "created_at" timestamp with time zone default now() not null
);
create table "erp"."sales_return_items" (
  "id" uuid default gen_random_uuid() not null,
  "return_id" uuid not null,
  "product_id" uuid not null,
  "lot_id" uuid,
  "location_id" uuid not null,
  "qty_pcs" integer not null,
  "unit_hpp_snapshot" numeric(18,6) default 0 not null,
  "refund_amount" numeric(20,2) default 0 not null,
  "quality_grade" character varying(20) default 'GRADE_A'::character varying not null,
  "notes" text,
  "sale_stock_allocation_id" uuid not null
);
create table "erp"."sales_payments" (
  "id" uuid default gen_random_uuid() not null,
  "sale_id" uuid not null,
  "payment_number" character varying(60) not null,
  "payment_date" timestamp with time zone not null,
  "amount" numeric(20,2) not null,
  "cash_account_id" uuid,
  "payment_method" character varying(30),
  "reference_number" character varying(100),
  "notes" text,
  "status" character varying(20) default 'DRAFT'::character varying not null,
  "created_by" uuid,
  "created_at" timestamp with time zone default now() not null
);
create table "erp"."sale_stock_allocations" (
  "id" uuid default gen_random_uuid() not null,
  "sale_item_id" uuid not null,
  "lot_id" uuid not null,
  "location_id" uuid not null,
  "qty_pcs" integer not null,
  "unit_hpp_snapshot" numeric(18,6) not null,
  "total_hpp" numeric(24,6) generated always as ((qty_pcs::numeric * unit_hpp_snapshot)) stored
);
create table "erp"."fg_stock_movements" (
  "id" uuid default gen_random_uuid() not null,
  "product_id" uuid not null,
  "lot_id" uuid,
  "location_id" uuid not null,
  "quality_grade" character varying(20) default 'GRADE_A'::character varying not null,
  "movement_type" character varying(40) not null,
  "qty_signed" integer not null,
  "unit_hpp_snapshot" numeric(18,6) default 0 not null,
  "customer_id" uuid,
  "source_type" character varying(50) not null,
  "source_id" uuid,
  "physical_at" timestamp with time zone not null,
  "system_created_at" timestamp with time zone default clock_timestamp() not null,
  "created_by" uuid,
  "reversal_of_id" uuid,
  "notes" text,
  "book_order" bigint default nextval('erp.fg_stock_book_order_seq'::regclass) not null
);
create table "erp"."journal_entries" (
  "id" uuid default gen_random_uuid() not null,
  "journal_number" character varying(70) not null,
  "transaction_date" date not null,
  "posting_at" timestamp with time zone default now() not null,
  "source_type" character varying(50) not null,
  "source_id" uuid,
  "description" text not null,
  "status" character varying(20) default 'DRAFT'::character varying not null,
  "reversal_of_id" uuid,
  "created_by" uuid,
  "created_at" timestamp with time zone default now() not null,
  "economic_date" date not null,
  "period_shifted" boolean generated always as (economic_date <> transaction_date) stored
);
create table "erp"."journal_lines" (
  "id" uuid default gen_random_uuid() not null,
  "journal_entry_id" uuid not null,
  "account_id" uuid not null,
  "description" text,
  "debit" numeric(20,2) default 0 not null,
  "credit" numeric(20,2) default 0 not null,
  "customer_id" uuid,
  "vendor_id" uuid,
  "contractor_id" uuid,
  "po_id" uuid,
  "product_id" uuid
);
create table "erp"."cash_accounts" (
  "id" uuid default gen_random_uuid() not null,
  "cash_account_code" character varying(30) not null,
  "cash_account_name" character varying(120) not null,
  "coa_account_id" uuid not null,
  "account_kind" character varying(20) not null,
  "is_active" boolean default true not null
);
alter table erp.customers add primary key(id);
alter table erp.chart_accounts add primary key(id);
alter table erp.sales_headers add primary key(id);
alter table erp.sales_items add primary key(id);
alter table erp.sales_returns add primary key(id);
alter table erp.sales_return_items add primary key(id);
alter table erp.sales_payments add primary key(id);
alter table erp.sale_stock_allocations add primary key(id);
alter table erp.fg_stock_movements add primary key(id);
alter table erp.journal_entries add primary key(id);
alter table erp.journal_lines add primary key(id);
alter table erp.cash_accounts add primary key(id);
alter table erp.accounting_account_mappings add primary key(mapping_key);
alter table erp.sales_payments add column replaces_payment_id uuid;
create table erp.sales_payment_posting_facts(
  payment_id uuid primary key,
  sale_id uuid not null,
  customer_id uuid not null,
  payment_number varchar(60) not null,
  payment_date timestamptz not null,
  amount numeric(20,2) not null check(amount>0),
  cash_account_id uuid not null,
  original_journal_entry_id uuid not null unique,
  journal_economic_date date not null,
  journal_transaction_date date not null,
  journal_posting_at timestamptz not null,
  replaces_payment_id uuid unique,
  predecessor_reversal_journal_id uuid unique,
  payment_snapshot jsonb not null,
  lineage_sha256 text not null check(lineage_sha256~'^[0-9a-f]{64}$'),
  recorded_at timestamptz not null default clock_timestamp(),
  recorded_by uuid,
  constraint sales_payment_posting_fact_replacement_pair check(
    (replaces_payment_id is null)=(predecessor_reversal_journal_id is null)
  )
);
create table erp.sales_payment_reversal_facts(
  payment_id uuid primary key,
  original_journal_entry_id uuid not null unique,
  reversal_journal_entry_id uuid not null unique,
  reversal_economic_date date not null,
  reversal_transaction_date date not null,
  reversal_posting_at timestamptz not null,
  lineage_sha256 text not null check(lineage_sha256~'^[0-9a-f]{64}$'),
  recorded_at timestamptz not null default clock_timestamp(),
  recorded_by uuid
);
alter table erp.sales_payment_posting_facts alter column cash_account_id drop not null;
create table erp.initial_import_prepayments(
 id uuid primary key default gen_random_uuid(),batch_id uuid not null,
 source_row_id uuid not null unique,
 party_type text not null check(party_type in('SUPPLIER','CUSTOMER','VENDOR')),party_id uuid not null,
 supplier_id uuid,customer_id uuid,vendor_id uuid,
 coa_account_id uuid not null,
 document_number text not null check(length(btrim(document_number)) between 1 and 120),
 document_date date not null,cutover_date date not null check(document_date<=cutover_date),
 original_amount numeric(20,2) not null,settled_before_cutover numeric(20,2) not null,amount numeric(20,2) not null,
 created_at timestamptz not null default statement_timestamp(),
 check(original_amount>0 and settled_before_cutover>=0 and amount>0 and original_amount-settled_before_cutover=amount),
 check(num_nonnulls(supplier_id,customer_id,vendor_id)=1 and party_id=coalesce(supplier_id,customer_id,vendor_id)
   and ((party_type='SUPPLIER' and supplier_id is not null) or (party_type='CUSTOMER' and customer_id is not null) or (party_type='VENDOR' and vendor_id is not null)))
);
create table erp.initial_import_prepayment_payments(
 payment_id uuid primary key,advance_id uuid not null,
 supplier_payment_id uuid unique,
 sales_payment_id uuid unique,
 vendor_payment_id uuid unique,
 opening_settlement_id uuid unique,
 payment_snapshot jsonb not null,created_at timestamptz not null default statement_timestamp(),
 check(num_nonnulls(supplier_payment_id,sales_payment_id,vendor_payment_id,opening_settlement_id)=1
   and payment_id=coalesce(supplier_payment_id,sales_payment_id,vendor_payment_id,opening_settlement_id))
);
create table cp7_note.revisions(
 id uuid primary key default gen_random_uuid(),root_sale_id uuid not null,
 previous_sale_id uuid not null unique,
 replacement_sale_id uuid not null unique,
 revision bigint not null,actor uuid not null,request_id uuid not null,reason text not null,
 effective_at timestamptz not null,recorded_at timestamptz not null default clock_timestamp(),
 unique(root_sale_id,revision),unique(actor,request_id)
);
create table cp7_note.payment_replays(
 previous_payment_id uuid primary key,
 replacement_payment_id uuid not null unique,
 correction_id uuid not null,
 recorded_at timestamptz not null default clock_timestamp()
);
create table cp7_note.journal_restatements(
 inverse_journal_id uuid primary key,
 source_journal_id uuid not null unique,
 previous_sale_id uuid not null,
 neutral_journal_id uuid not null unique,
 effective_journal_id uuid not null unique,
 native_economic_date date not null,corrected_economic_date date not null,
 recorded_at timestamptz not null default clock_timestamp()
);
create table cp7_sales_return_correction.links(
 id uuid primary key default gen_random_uuid(),original_id uuid not null unique,
 replacement_id uuid not null unique,sale_id uuid not null,
 actor uuid not null,request_id uuid not null,reason text not null,
 recorded_at timestamptz not null default clock_timestamp(),
 check(original_id<>replacement_id),check(length(btrim(reason))between 5 and 1000),unique(actor,request_id)
);
create table cp7_sales_return_correction.context(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 request_id uuid not null,sale_id uuid not null,return_id uuid not null,
 primary key(backend_pid,transaction_id)
);
create table cp7_sales_return_correction.journal_restatements(
 source_journal_id uuid primary key,
 inverse_journal_id uuid not null unique,
 original_return_id uuid not null unique,
 neutral_journal_id uuid not null unique,
 effective_journal_id uuid not null unique,
 native_economic_date date not null,corrected_economic_date date not null,
 recorded_at timestamptz not null default clock_timestamp()
);
create table cp7_payment_correction.links(
 original_id uuid primary key,
 replacement_id uuid not null unique,
 sale_id uuid not null,actor uuid not null,
 request_id uuid not null,reason text not null,
 time_neutral_id uuid,
 effective_inverse_id uuid,
 recorded_at timestamptz not null default statement_timestamp(),
 check(original_id<>replacement_id),check(length(btrim(reason))between 5 and 1000),
 check((time_neutral_id is null)=(effective_inverse_id is null)),unique(actor,request_id)
);
create table cp7_note.item_lineage(
 replacement_item_id uuid primary key,
 previous_item_id uuid,
 correction_id uuid not null,
 request_position integer not null check(request_position>0),
 unique(correction_id,request_position),unique(correction_id,previous_item_id)
);
