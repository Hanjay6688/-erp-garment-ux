-- AZ rev2.1 stub (T1_FAMILY evidence helper; NOT release evidence): only what erp.sync_material_cost_revaluation reads.
create schema erp;
create table erp.settings(k text primary key, v text);
create function erp.require_internal() returns void language sql as $$select$$;
create function erp._cp3_business_date(t timestamptz) returns date language sql immutable as $$select (t at time zone 'Asia/Jakarta')::date$$;
create function erp.invoice_recost_economic_date_v1() returns date language sql as $$select (select v::date from erp.settings where k='E')$$;
create table erp.accounting_period_control(singleton_id int primary key, closed_through date);
insert into erp.accounting_period_control values(1,null);
create table erp.material_stock_movements(id uuid primary key, material_id uuid, source_type text, source_id uuid, movement_type text,
  qty_signed numeric, unit_cost_snapshot numeric, original_unit_cost_snapshot numeric, physical_at timestamptz,
  system_created_at timestamptz, roll_id uuid, reversal_of_id uuid);
create table erp.material_cost_history(material_id uuid, movement_id uuid, average_after numeric);
create table erp.cutting_groups(id uuid primary key, po_id uuid);
create table erp.contractor_material_issue_items(id uuid, issue_id uuid, material_id uuid);
create table erp.contractor_material_issues(id uuid, po_id uuid, contractor_id uuid);
create table erp.materials(id uuid, material_type text);
create table erp.material_cost_revaluation_state(movement_id uuid primary key, applied_inventory_delta numeric, updated_at timestamptz);
create table erp.material_cost_revaluation_events(id uuid primary key default gen_random_uuid(), material_id uuid, movement_id uuid, effective_date date,
  old_inventory_delta numeric, new_inventory_delta numeric, delta_amount numeric, counterpart_mapping_key text, po_id uuid, contractor_id uuid, journal_entry_id uuid);
create table erp.journal_entries(id uuid primary key default gen_random_uuid(), transaction_date date);
create table erp.journal_lines(journal_entry_id uuid, mapping_key text, debit numeric, credit numeric);
create function erp.post_journal(p_source text, p_id uuid, p_date date, p_desc text, p_lines jsonb) returns uuid language plpgsql as $$
declare v uuid; begin insert into erp.journal_entries(transaction_date) values(p_date) returning id into v;
 insert into erp.journal_lines select v,x->>'mapping_key',(x->>'debit')::numeric,(x->>'credit')::numeric from jsonb_array_elements(p_lines) x; return v; end $$;
create table erp.material_adjustment_items(id uuid, adjustment_id uuid, material_id uuid);
create table erp.pocket_fabric_usage(adjustment_id uuid);
create function erp._cp6_sync_material_adjustment_revaluation(a uuid, m uuid) returns void language sql as $$select$$;
