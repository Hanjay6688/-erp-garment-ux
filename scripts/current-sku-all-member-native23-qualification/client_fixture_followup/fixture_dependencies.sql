-- DECLARED PGLITE/POSTGRES TABLE MODELS, NOT A NATIVE INSTALLATION.
-- Types/guarded columns follow BE source/cost/rework SQL and P00 catalogue.
-- Existing family tests already model posting/Auth/HPP/journals. Foreign keys,
-- RLS and immutable fact triggers of these ERP model tables are not installed;
-- the independent original six-ERP-parent-RI oracle remains unchanged.
alter table erp.fg_stock_movements add column source_type character varying(50);
create table erp.be_conversion_sources_v1(
 conversion_id uuid primary key,source_lot_id uuid not null,
 origin_kind text not null check(origin_kind in('FG','REWORK','REDYE')),
 rework_id uuid,source_revision text not null,created_by uuid,
 created_at timestamptz not null default statement_timestamp(),
 check((origin_kind='FG')=(rework_id is null))
);
create table erp.bc_documents_v1(
 id uuid primary key,status text not null default 'POSTED' check(status in('POSTED','REVERSED'))
);
create table erp.be_conversion_cost_sources_v1(
 document_id uuid primary key,conversion_id uuid not null,
 kind text not null check(kind in('USAGE','RECOVERY')),
 created_at timestamptz not null default statement_timestamp()
);
create table erp.bc_outstanding_returns_v1(
 id uuid primary key default gen_random_uuid(),status text not null default 'OPEN' check(status in('OPEN','CANCELLED'))
);
create table erp.be_conversion_returns_v1(
 outstanding_id uuid primary key,conversion_id uuid not null,
 line_no integer not null check(line_no>0),unique(conversion_id,line_no)
);
create table erp.bc_return_lots_v1(
 id uuid primary key default gen_random_uuid(),document_id uuid,
 outstanding_id uuid
);
create table erp.product_conversion_allocations(
 id uuid primary key default gen_random_uuid(),conversion_id uuid not null,
 source_lot_id uuid not null,destination_lot_id uuid,qty_pcs integer not null,
 original_hpp_per_pcs numeric(18,6)not null,conversion_cost_allocated numeric(20,2)not null default 0,
 new_hpp_per_pcs numeric(18,6)generated always as(original_hpp_per_pcs+conversion_cost_allocated/nullif(qty_pcs,0))stored
);
create table erp.journal_entries(
 id uuid primary key default gen_random_uuid(),journal_number character varying(70)not null,
 transaction_date date not null,posting_at timestamptz not null default statement_timestamp(),
 source_type character varying(50)not null,source_id uuid,description text not null,
 status character varying(20)not null default 'DRAFT',reversal_of_id uuid,created_by uuid,
 created_at timestamptz not null default statement_timestamp(),economic_date date not null,
 period_shifted boolean generated always as(economic_date<>transaction_date)stored
);
