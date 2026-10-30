-- LOCAL STRUCTURAL SQL MODEL ONLY. This is not the full ERP/Native schema.
-- Used column types (notably integer pcs, generated numeric(18,6) HPP,
-- numeric(24,6) total cost and numeric(20,2) GL) follow retained Native DDL.
create role anon; create role authenticated; create role service_role;
create schema erp; create schema cp7_credit; create schema cp7_note;
create schema cp7_global_nonpo_native_graph authorization postgres;
revoke all on schema cp7_global_nonpo_native_graph from public,anon,authenticated,service_role;
create table erp.sales_headers(id uuid primary key,customer_id uuid,status varchar(20),sale_date date default '2026-10-20');
create table erp.sales_items(id uuid primary key,sale_id uuid,product_id uuid,line_total numeric(20,2));
create table erp.sale_stock_allocations(id uuid primary key,sale_item_id uuid,lot_id uuid,qty_pcs integer);
create table erp.sales_returns(id uuid primary key,sale_id uuid,status varchar(20));
create table erp.sales_return_items(id uuid primary key,return_id uuid,lot_id uuid,qty_pcs integer);
create table erp.fg_lots(id uuid primary key,product_id uuid,po_id uuid,source_lot_id uuid,lot_origin varchar(20),initial_qty_pcs integer,produced_at timestamptz default '2026-10-20T01:00Z');
create table erp.hpp_versions(id uuid primary key,lot_id uuid,version_no integer,cost_state varchar(20),qty_basis_pcs integer not null check(qty_basis_pcs>0),total_cost numeric(24,6),
 hpp_per_pcs numeric(18,6) generated always as(total_cost/nullif(qty_basis_pcs,0))stored,is_current boolean,calculated_at timestamptz default '2026-10-20T01:00Z');
create table erp.hpp_version_components(id uuid primary key,hpp_version_id uuid,total_cost numeric(24,6),source_id uuid);
create table erp.product_conversions(id uuid primary key,from_product_id uuid,to_product_id uuid,status varchar(20),physical_at timestamptz,qty_pcs integer);
create table erp.product_conversion_allocations(id uuid primary key,conversion_id uuid,source_lot_id uuid,destination_lot_id uuid,qty_pcs integer,
 original_hpp_per_pcs numeric(18,6),conversion_cost_allocated numeric(20,2));
create table erp.be_execution_context_v1(backend_pid integer,transaction_id bigint,request_id uuid,syncing_nonpo boolean,primary key(backend_pid,transaction_id));
create table erp.be_conversion_sources_v1(conversion_id uuid primary key,source_lot_id uuid,origin_kind text check(origin_kind in('FG','REWORK','REDYE')));
create table erp.be_conversion_returns_v1(outstanding_id uuid primary key,conversion_id uuid,line_no integer);
create table erp.bc_outstanding_returns_v1(id uuid primary key,status text,qty_expected numeric(18,6));
create table erp.bc_return_lots_v1(id uuid primary key,outstanding_id uuid,document_id uuid,qty_received numeric(18,6),value_mode text);
create table erp.be_conversion_cost_sources_v1(document_id uuid primary key,conversion_id uuid,kind text);
create table erp.be_conversion_cost_events_v1(id uuid primary key,document_id uuid,adjustment_id uuid,previous_amount numeric(20,2),target_amount numeric(20,2),journal_id uuid,economic_date date);
create table erp.be_nonpo_transfer_events_v1(id uuid primary key,conversion_id uuid,previous_value numeric(20,2),target_value numeric(20,2),journal_id uuid,economic_date date);
create table erp.fg_stock_movements(id uuid primary key,lot_id uuid,qty_signed integer,movement_type varchar(40),reversal_of_id uuid);
create table erp.fg_inventory_balances(product_id uuid,location_id uuid,quality_grade text,qty_pcs integer,primary key(product_id,location_id,quality_grade));
create table erp.chart_accounts(id uuid primary key,account_code text,is_active boolean default true,is_postable boolean default true);
create table erp.accounting_account_mappings(mapping_key text primary key,account_id uuid);
create table erp.journal_entries(id uuid primary key,status varchar(20),source_type varchar(80),source_id uuid,reversal_of_id uuid,economic_date date default '2026-10-20',transaction_date date default '2026-10-20');
create table erp.journal_lines(id uuid primary key,journal_entry_id uuid,account_id uuid,debit numeric(20,2),credit numeric(20,2),product_id uuid,po_id uuid);
create table erp.non_po_hpp_gl_sync_events_v2620f(id uuid primary key,product_id uuid,journal_entry_id uuid);
create table erp.opening_lot_hpp_gl_state(lot_id uuid primary key);
create table erp.opening_hpp_corrections(id uuid primary key,lot_id uuid);
create table erp.po_hpp_gl_state(po_id uuid primary key);
create table erp.bc_documents_v1(id uuid primary key,status text);
create table erp.material_adjustments(id uuid primary key,amount numeric(20,2));
-- Additional documentary identities follow the exact BC release column types.
-- Local models intentionally omit unmodeled FK/role/trigger/business constraints.
create table erp.bc_document_links_v1(document_id uuid,link_kind text,link_id uuid,primary key(document_id,link_kind,link_id));
create table erp.bc_adjustment_purposes_v1(adjustment_id uuid primary key,document_id uuid,purpose text,account_id uuid,policy_key text,policy_version bigint);
create table erp.bc_lot_events_v1(id uuid primary key,document_id uuid,lot_id uuid,event_kind text,condition text,
 qty_usable numeric(18,6),qty_damaged numeric(18,6),qty numeric(18,6),inspector text,event_at timestamptz,target_location_id uuid,
 unit_value numeric(18,2),amount numeric(18,2),amount_unpaid numeric(18,2),amount_carry numeric(18,2),amount_refund numeric(18,2),cash_account_id uuid,created_at timestamptz);
alter table erp.bc_documents_v1 add document_number text,add action text,add physical_at timestamptz,add responsible text,add reference text,
 add reason text,add payload jsonb,add policy_versions jsonb,add row_version bigint,add created_by uuid,add created_at timestamptz,
 add reversed_by uuid,add reversed_at timestamptz,add reversal_reason text;
alter table erp.bc_outstanding_returns_v1 add source_kind text,add owner_kind text,add material_id uuid,add description text,add holder text,
 add reference text,add batch_id uuid,add source_row_id uuid,add document_id uuid,add created_at timestamptz;
alter table erp.bc_return_lots_v1 add line_number integer,add source_kind text,add owner_kind text,add material_id uuid,add location_id uuid,
 add init_usable numeric(18,6),add init_damaged numeric(18,6),add received_at timestamptz,add contractor_id uuid,add note_item_id uuid,
 add opening_note_line_id uuid,add parent_lot_id uuid,add parent_event_id uuid,add batch_id uuid,add source_row_id uuid,add reference text,add created_at timestamptz;
alter table erp.journal_lines add description text,add customer_id uuid,add vendor_id uuid,add contractor_id uuid;
alter table erp.journal_entries add journal_number varchar(70),add posting_at timestamptz,add description text,add created_by uuid,add created_at timestamptz,
 add period_shifted boolean generated always as(economic_date<>transaction_date)stored;
alter table erp.journal_entries alter source_type type varchar(50);
alter table erp.be_conversion_sources_v1 add rework_id uuid,add source_revision text,add created_by uuid,add created_at timestamptz;
alter table erp.be_conversion_cost_sources_v1 add created_at timestamptz;
alter table erp.be_conversion_cost_events_v1 add created_at timestamptz,add created_by uuid;
alter table erp.be_nonpo_transfer_events_v1 add created_at timestamptz;
alter table erp.material_adjustments add adjustment_number varchar(60),add reason_code varchar(30),add physical_at timestamptz,add status varchar(20),
 add notes text,add created_by uuid,add created_at timestamptz,add updated_at timestamptz,add location_id uuid,add row_version bigint;
-- amount is a pre-existing local fixture tag, not a claimed Native header column.
alter table erp.non_po_hpp_gl_sync_events_v2620f add trigger_source_type text,add trigger_source_id uuid,add effective_date date,
 add old_fg_value numeric(20,2),add new_fg_value numeric(20,2),add fg_delta numeric(20,2),
 add old_cogs_value numeric(20,2),add new_cogs_value numeric(20,2),add cogs_delta numeric(20,2),
 add old_other_out_value numeric(20,2),add new_other_out_value numeric(20,2),add other_delta numeric(20,2),add reason text,add created_by uuid,add created_at timestamptz;
create table erp.accounting_period_control(singleton_id integer primary key,closed_through date);
create table cp7_note.revisions(id uuid,root_sale_id uuid,previous_sale_id uuid,replacement_sale_id uuid,revision bigint);
create table cp7_credit.return_families(id uuid primary key,family_root_sale_id uuid);
create table cp7_credit.cohorts(id uuid primary key,family_id uuid,source_sale_id uuid,customer_id uuid);
create table cp7_credit.consumption_events(id uuid primary key,cohort_id uuid,event_kind text,target_sale_id uuid,restores_event_id uuid,amount numeric(20,2));
create sequence erp.LOCAL_MODEL_NO_EFFECT_SEQUENCE;
create function erp.LOCAL_MODEL_NO_WRITE()returns trigger language plpgsql as $$
begin if current_setting('local_model.inspecting',true)='on'then raise exception 'LOCAL_READONLY_INSPECTOR_BUSINESS_DML_ATTEMPT';end if;return coalesce(new,old);end $$;
