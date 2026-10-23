-- A must run its global after-use guard before this pre-use rollback.
-- An explicit policy cannot be discarded even if called without A's guard.
do $$begin
 if exists(select 1 from cp7_stock_formula.material_settings where fabric_rule is not null)then
  raise exception 'CP7_PRODUCTION_STAGE_AFTER_USE_REQUIRES_BACKUP_RESTORE';
 end if;
end $$;
alter table cp7_stock_formula.material_settings drop column fabric_rule;
alter table cp7_stock_formula.material_evaluations drop column legacy_minimum_qty,drop column fabric_rule;

alter table cp7_stock_formula.material_settings alter column manual_point type numeric(18,4);
