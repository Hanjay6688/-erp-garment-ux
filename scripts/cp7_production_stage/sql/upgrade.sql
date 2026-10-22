-- OW14b adds nullable private configuration/cache columns, preserving prior rows.
-- Caller owns the transaction and holds the integration's global envelope lock.
alter table cp7_stock_formula.material_settings add column fabric_rule text;
alter table cp7_stock_formula.material_settings
 add constraint ow14b_material_rule check(fabric_rule in('LEGACY_MINIMUM','FORMULA')),
 add constraint ow14b_legacy_requires_point check(fabric_rule is distinct from'LEGACY_MINIMUM'or manual_point is not null),
 add constraint ow14b_formula_clears_point check(fabric_rule is distinct from'FORMULA'or manual_point is null);
alter table cp7_stock_formula.material_evaluations
 add column legacy_minimum_qty numeric,
 add column fabric_rule text,
 add constraint ow14b_evaluation_rule check(fabric_rule in('LEGACY_MINIMUM','FORMULA'));
