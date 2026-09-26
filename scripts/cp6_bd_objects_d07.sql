-- D07 (owner 25 Sep 2026 ~18:30Z, auditor reading recorded open in OWNER_DECISIONS_CP6_DRAFT.md §D07; the formula below is the
-- auditors' technical proposal, implemented by the writer, not an owner-ratified formula): the v2.5.5 alarm
-- MATERIAL_RECOST_GL_STATE_DRIFT is reset from per movement to document level. Same row name, same severity (ERROR), same
-- signature; the second row (MATERIAL_GL_VALUATION_MISMATCH) is unchanged, word for word.
-- Why: the per-movement check predates v2.6.20t (a material adjustment's recost is kept per adjustment document in
-- material_adjustment_revaluation_facts, never in material_cost_revaluation_state) and BA W8 / T3 option A (the cents of the
-- purchase documents go with the next consumption, so one movement may carry several documents' cents). On exact books it
-- reported ERROR (auditor xaudit_12_f1f2: ADJUST+INVOICE x2, STACKED n=10).
-- What it counts now (one row, issue_count = the sum of the three parts):
--   1. consumption, per material: |round(sum of each movement's target qty x (cost now - cost posted), 2) - sum applied| above
--      one cent per purchase document of the material (the most a document's own rounding can move). A reversed movement
--      targets 0 and is summed with its reversal's state (the pair nets to 0).
--   2. adjustments, per adjustment document x material: |round(sum of its live items' targets, 2) - sum of the MATERIAL_INVENTORY
--      deltas of its v2.6.20t facts| above one cent.
--   3. no recost at all: a live consumption movement whose own target is above one cent with no state row, and an adjustment
--      document x material whose target is above one cent with no fact. These are the core of the alarm and have no tolerance.
CREATE OR REPLACE FUNCTION erp.run_v255_material_cost_integrity_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
begin
  perform erp.require_owner_admin();
  return query
  with mv as (
    select msm.id,msm.material_id,msm.source_type,msm.source_id,
      case when exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id) then 0::numeric
        else msm.qty_signed*(msm.unit_cost_snapshot-coalesce(msm.original_unit_cost_snapshot,msm.unit_cost_snapshot)) end target,
      exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id) reversed
    from erp.material_stock_movements msm
    where msm.movement_type<>'REVERSAL'
      and msm.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN','CONTRACTOR_MATERIAL_ISSUE_ITEM','MATERIAL_ADJUSTMENT_ITEM',
                             'MATERIAL_SUPPLIER_RETURN_ITEM','BC_NOTE_RETURN_CREDIT')
  ),
  consumption as (
    select mv.material_id,round(sum(mv.target),2) target,
      sum(coalesce(s.applied_inventory_delta,0)+coalesce((select sum(rs.applied_inventory_delta) from erp.material_stock_movements rv
        join erp.material_cost_revaluation_state rs on rs.movement_id=rv.id where rv.reversal_of_id=mv.id),0)) applied
    from mv left join erp.material_cost_revaluation_state s on s.movement_id=mv.id
    where mv.source_type<>'MATERIAL_ADJUSTMENT_ITEM'
    group by mv.material_id
  ),
  documents as (
    select m.material_id,count(distinct pi.purchase_id) n
    from erp.material_stock_movements m
    join erp.material_purchase_items pi on pi.id=case when m.source_type='MATERIAL_PURCHASE_ITEM' then m.source_id
      else (select mr.purchase_item_id from erp.material_rolls mr where mr.id=m.source_id) end
    where m.movement_type='PURCHASE' and m.source_type in('MATERIAL_PURCHASE_ITEM','MATERIAL_PURCHASE_ROLL')
    group by m.material_id
  ),
  adjustment as (
    select i.adjustment_id,mv.material_id,round(sum(mv.target),2) target,
      (select sum(coalesce((f.ledger_delta->>erp.account_id('MATERIAL_INVENTORY')::text)::numeric,0))
       from erp.material_adjustment_revaluation_facts f where f.adjustment_id=i.adjustment_id and f.triggering_material_id=mv.material_id) applied,
      exists(select 1 from erp.material_adjustment_revaluation_facts f where f.adjustment_id=i.adjustment_id and f.triggering_material_id=mv.material_id) has_fact
    from mv join erp.material_adjustment_items i on i.id=mv.source_id
    where mv.source_type='MATERIAL_ADJUSTMENT_ITEM'
    group by i.adjustment_id,mv.material_id
  )
  select 'MATERIAL_RECOST_GL_STATE_DRIFT','ERROR',
    ((select count(*) from consumption c left join documents d on d.material_id=c.material_id
       where abs(c.target-c.applied)>0.01*greatest(1,coalesce(d.n,0)))
     +(select count(*) from adjustment a where abs(a.target-coalesce(a.applied,0))>0.01)
     +(select count(*) from mv left join erp.material_cost_revaluation_state s on s.movement_id=mv.id
        where mv.source_type<>'MATERIAL_ADJUSTMENT_ITEM' and not mv.reversed and abs(round(mv.target,2))>0.01 and s.movement_id is null)
     +(select count(*) from adjustment a where abs(a.target)>0.01 and not a.has_fact))::bigint,
    'Material recost target differs from applied automatic GL revaluation: per material beyond one cent per purchase document, per adjustment document beyond one cent (v2.6.20t facts), or a corrected movement with no recost at all (D07)';

  return query
  select 'MATERIAL_GL_VALUATION_MISMATCH','ERROR',
    case when abs(v.ledger_value-v.gl_value)>0.05 then 1 else 0 end::bigint,
    'Material moving-average ledger value differs from Material Inventory GL by more than 0.05'
  from (
    select
      coalesce((select sum(coalesce(m.cached_stock_qty,0)*coalesce(m.moving_average_cost,0)) from erp.materials m),0)::numeric as ledger_value,
      coalesce((select sum(adb.debit_total-adb.credit_total) from erp.account_daily_balances adb where adb.account_id=erp.account_id('MATERIAL_INVENTORY')),0)::numeric as gl_value
  ) v;
end;
$function$;
