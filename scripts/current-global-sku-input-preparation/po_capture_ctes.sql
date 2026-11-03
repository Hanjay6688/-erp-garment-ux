 -- PO inputs are selected by economic PO identity. Shared cutting batches and
 -- pocket sources are read dependencies, never material/account identity hubs.
 po_ids(id)as(select x::uuid from domain d cross join lateral jsonb_array_elements_text(d.value->'po_ids')x),
 po_orders as(select t.*from erp.production_orders t where t.id in(select id from po_ids)),
 po_groups as(select t.*from erp.cutting_groups t where t.po_id in(select id from po_ids)
  or t.cutting_batch_id in(select g.cutting_batch_id from erp.cutting_groups g where g.po_id in(select id from po_ids))),
 po_batches as(select t.*from erp.cutting_batches t where t.id in(select cutting_batch_id from po_groups)),
 po_rolls as(select t.*from erp.cutting_group_rolls t where t.cutting_group_id in(select id from po_groups)),
 po_yields as(select t.*from erp.cutting_roll_yields t where t.cutting_group_roll_id in(select id from po_rolls)),
 po_corrections as(select t.*from erp.cutting_qty_correction_lines t where t.cutting_group_id in(select id from po_groups)),
 po_qc as(select t.*from erp.qc_inspection_items t where t.id in(select qc_item_id from lots)
  or t.cutting_group_id in(select id from po_groups)),
 po_terminal_edges(a,b)as(select id,reversal_of_id from erp.sewing_terminal_events where reversal_of_id is not null
  union select reversal_of_id,id from erp.sewing_terminal_events where reversal_of_id is not null),
 po_terminal_ids(id)as(select id from erp.sewing_terminal_events where po_id in(select id from po_ids)
  union select e.b from po_terminal_ids p join po_terminal_edges e on e.a=p.id),
 po_terminal as(select t.*from erp.sewing_terminal_events t where t.id in(select id from po_terminal_ids)),
 po_lot_states as(select t.*from erp.po_hpp_gl_lot_state_v1 t where t.po_id in(select id from po_ids)
  or t.lot_id in(select id from lots)),
 po_material_states as(select t.*from erp.po_hpp_gl_material_state_v1 t where t.po_id in(select id from po_ids)),
 po_hpp_events as(select t.*from erp.po_hpp_gl_events t where t.po_id in(select id from po_ids)),
 po_destinations as(select t.*from erp.pocket_period_destinations t where t.po_id in(select id from po_ids)),
 po_pool_ids(id)as(select pool_id from po_destinations
  union select k::uuid from po_lot_states s cross join lateral jsonb_object_keys(s.pocket_by_pool)k),
 po_pools as(select t.*from erp.pocket_periods t where t.id in(select id from po_pool_ids)),
 po_pool_events as(select t.*from erp.pocket_period_events t where t.pool_id in(select id from po_pool_ids)),
 po_pool_sources as(select t.*from erp.pocket_period_sources t where t.pool_id in(select id from po_pool_ids)),
 po_usages as(select t.*from erp.be_pocket_usage_v1 t where t.id in(select historical_usage_id from po_pool_sources)),
 po_usage_events as(select t.*from erp.be_pocket_source_events_v1 t where t.usage_id in(select id from po_usages)),
 po_adjustments as(select t.*from erp.material_adjustments t where t.id in(select adjustment_id from po_pool_sources)),
 po_adjustment_items as(select t.*from erp.material_adjustment_items t where t.adjustment_id in(select adjustment_id from po_pool_sources)),
 po_purposes as(select t.*from erp.bc_adjustment_purposes_v1 t where t.adjustment_id in(select adjustment_id from po_pool_sources)),
 po_adjustment_facts as(select t.*from erp.material_adjustment_revaluation_facts t where t.adjustment_id in(select adjustment_id from po_pool_sources)),
 po_issues as(select t.*from erp.contractor_material_issues t where t.po_id in(select id from po_ids)),
 po_issue_items as(select t.*from erp.contractor_material_issue_items t where t.issue_id in(select id from po_issues)),
 po_movement_edges(a,b)as(select id,reversal_of_id from erp.material_stock_movements where reversal_of_id is not null
  union select reversal_of_id,id from erp.material_stock_movements where reversal_of_id is not null),
 po_movement_ids(id)as(select m.id from erp.material_stock_movements m where
  (m.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN')and m.source_id in(select id from po_groups))
  or(m.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM'and m.source_id in(select id from po_issue_items))
  or(m.source_type='MATERIAL_ADJUSTMENT_ITEM'and m.source_id in(select id from po_adjustment_items))
  union select e.b from po_movement_ids p join po_movement_edges e on e.a=p.id),
 po_movements as(select t.*from erp.material_stock_movements t where t.id in(select id from po_movement_ids)),
 po_revaluations as(select t.*from erp.material_cost_revaluation_events t where t.movement_id in(select id from po_movement_ids)
  or t.po_id in(select id from po_ids)),
 po_material_ids(id)as(select material_id from po_issue_items union select material_id from po_adjustment_items
  union select material_id from po_movements union select material_id from po_usages),
 po_materials as(select t.*from erp.materials t where t.id in(select id from po_material_ids)),
 po_input_journal_edges(a,b)as(select id,reversal_of_id from erp.journal_entries where reversal_of_id is not null
  union select reversal_of_id,id from erp.journal_entries where reversal_of_id is not null),
 po_input_journal_ids(id)as(
  (select journal_entry_id from po_revaluations union select journal_entry_id from po_adjustment_facts
   union select journal_entry_id from po_pool_events union select journal_id from po_usages
   union select journal_id from po_usage_events union select journal_entry_id from po_hpp_events)
  union select e.b from po_input_journal_ids p join po_input_journal_edges e on e.a=p.id),
 po_input_journals as(select t.*from erp.journal_entries t where t.id in(select id from po_input_journal_ids)),
 po_input_lines as(select t.*from erp.journal_lines t where t.journal_entry_id in(select id from po_input_journal_ids)),
 po_mappings as(select t.*from erp.accounting_account_mappings t where t.mapping_key in(
  'FG_INVENTORY','COGS','OTHER_EXPENSE','OTHER_INCOME','WIP','MATERIAL_INVENTORY')and exists(select 1 from po_ids)),
 po_accounts as(select t.*from erp.chart_accounts t where t.id in(select account_id from po_mappings)
  or t.id in(select account_id from po_purposes)or t.id in(select account_id from po_input_lines)),
 po_invoice_context as(select t.*from erp.invoice_recost_execution_context t where exists(select 1 from po_ids)),
