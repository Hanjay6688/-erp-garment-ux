create table erp.pocket_fabric_usage(adjustment_id uuid);
create table erp.pocket_periods(id uuid primary key, period_start date, period_end date);
create table erp.pocket_period_sources(pool_id uuid, adjustment_id uuid);
create table erp.material_adjustment_revaluation_facts(id uuid primary key default gen_random_uuid(), adjustment_id uuid, effective_date date);
create table erp.pocket_log(pool uuid, d date, kind text);
create function erp.pocket_period_active_v1(p uuid) returns boolean language sql as $$select true$$;
create function erp.pocket_period_lock_v1() returns void language sql as $$select$$;
create function erp.sync_pocket_period_v1(p_pool uuid,p_date date,p_kind text,p_reason text) returns void language sql as $$insert into erp.pocket_log values(p_pool,p_date,p_kind)$$;
