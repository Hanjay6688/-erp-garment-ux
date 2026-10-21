"""Exact structural fix for an unassigned PL/pgSQL target RECORD on cash routes.

No monetary/date/permission/eligibility/posting expression is changed. The
optional target has typed nullable UUID/text slots on every fresh backend.
"""


def derive(original):
    replacements=(
      (' target uuid;cash uuid;original uuid;source_assignment record;target_assignment record;',
       ' target uuid;cash uuid;original uuid;source_assignment record;\n target_customer uuid;target_root uuid;target_leaf uuid;target_status text;'),
      ('  select *into strict target_assignment from cp7_credit.current_leaf_assignment(target);\n'
       '  if target_assignment.customer_id<>ch.customer_id or target_assignment.root_sale_id=source_assignment.root_sale_id then',
       '  select a.customer_id,a.root_sale_id,a.current_leaf_id,a.requested_status\n'
       '   into strict target_customer,target_root,target_leaf,target_status from cp7_credit.current_leaf_assignment(target)a;\n'
       '  if target_customer<>ch.customer_id or target_root=source_assignment.root_sale_id then'),
      ("  if target_assignment.requested_status not in('POSTED','PARTIAL_PAID','PAID')\n"
       '   or(target_assignment.root_sale_id,target_assignment.current_leaf_id)is distinct from(target,target)then',
       "  if target_status not in('POSTED','PARTIAL_PAID','PAID')\n"
       '   or(target_root,target_leaf)is distinct from(target,target)then'),
      ("  'target_root_sale_id',case when target is not null then target_assignment.root_sale_id end,\n"
       "  'target_current_leaf_id',case when target is not null then target_assignment.current_leaf_id end,",
       "  'target_root_sale_id',target_root,\n  'target_current_leaf_id',target_leaf,"),
    )
    answer=original
    for old,new in replacements:
        assert answer.count(old)==1,'SELECTOR_RECORD_FIX_SOURCE_ANCHOR_CHANGED'
        answer=answer.replace(old,new)
    assert 'target_assignment'not in answer
    return answer
