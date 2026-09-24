alter table erp.journal_entries add column status text default 'POSTED';
alter table erp.fg_lots add column produced_at timestamptz;
create table erp.materials(id uuid primary key, material_type text, accessory_category_id uuid);
create table erp.fg_accessory_cost_snapshots(id uuid primary key, category_id uuid, hpp_method text, costing_basis_at timestamptz, category_avg_cost_base_snapshot numeric, hpp_unit_cost_base_snapshot numeric, po_id uuid, lot_id uuid, qty numeric, total_hpp_cost numeric generated always as (qty*hpp_unit_cost_base_snapshot) stored);
create table erp.fg_accessory_cost_revisions(id uuid primary key default gen_random_uuid(), snapshot_id uuid, material_id uuid, old_category_avg_cost numeric, new_category_avg_cost numeric, old_hpp_unit_cost numeric, new_hpp_unit_cost numeric, reason text, changed_by uuid);
create function erp.accessory_category_weighted_avg_cost_at(c uuid, t timestamptz) returns numeric language sql as $$select 2.2::numeric$$;
create function erp.rebuild_po_hpp(p uuid, r text) returns void language sql as $$select$$;
create function erp.propagate_conversion_hpp_for_po(p uuid) returns void language sql as $$select$$;
create function erp.sync_po_hpp_to_gl(p uuid, d date) returns void language sql as $$select$$;
