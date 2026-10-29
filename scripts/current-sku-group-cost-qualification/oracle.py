"""Independent fixture gold. No SQL reader or observed runtime feeds this math."""
from decimal import Decimal as D

PCS=(2,2)
SOURCE_UNITS=(D('10.01'),D('20.02'))
BASE_VALUES=(D('20.02'),D('40.04'))
USAGE_PCS=(1,2)
ORIGINAL_MATERIAL_UNIT=D('2.00')
INVOICED_MATERIAL_UNIT=D('3.00')
RETURN_VALUE=D('30.03')

def gold(sold_part):
    if sold_part not in(0,1):raise ValueError('DECLARED_PART_INDEX_REQUIRED')
    used=tuple(base+qty*ORIGINAL_MATERIAL_UNIT for base,qty in zip(BASE_VALUES,USAGE_PCS))
    repriced=tuple(base+qty*INVOICED_MATERIAL_UNIT for base,qty in zip(BASE_VALUES,USAGE_PCS))
    deltas=tuple(after-before for before,after in zip(used,repriced))
    sold_cogs=deltas[sold_part]/PCS[sold_part]
    return dict(base=BASE_VALUES,after_usage=used,after_invoice=repriced,
      source_units=SOURCE_UNITS,usage_material_qty=3,remaining_material_qty=97,
      invoice_part_deltas=deltas,group_before=sum(BASE_VALUES),group_after_usage=sum(used),group_after_invoice=sum(repriced),
      FG_invoice_delta=sum(deltas)-sold_cogs,COGS_invoice_delta=sold_cogs,
      descendant_before=used[1]/PCS[1],descendant_after=repriced[1]/PCS[1],
      material_inventory_invoice_delta=D('97.00'))

def recovery_limit():
    return dict(recovery=RETURN_VALUE,first_part=BASE_VALUES[0],whole_group=sum(BASE_VALUES),
      desired_first_unit=SOURCE_UNITS[0]-RETURN_VALUE/PCS[0],whole_group_arithmetic_remainder=sum(BASE_VALUES)-RETURN_VALUE,
      Native_safety_refusal_required=True,whole_group_recovery_capability=False)
