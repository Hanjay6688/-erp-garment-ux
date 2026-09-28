"""Writer continuation of explicitly open combined CP6 scenarios."""
import cp6_bf_combined_probe as p
import cp6_bf_vendor_modes as regression
INSTALL_BF=True


def cases(cur,today):
    return [
        ('R06:RUNNING_PO_NEW_MEMBER_IDENTICAL_RECIPE',lambda:p.new_member_running_po(cur,today)),
        ('R06:RUNNING_PO_NEW_MEMBER_DIFFERENT_RECIPE_ATOMIC',lambda:p.new_member_running_po(cur,today,True)),
        ('R07:COMMITTED_BS_RANGE_MOVE_SAME_CONTRACTOR_REWORK',lambda:p.range_rework(cur,today)),
        ('R07:UNCOMMITTED_BS_RANGE_MOVE_OTHER_CONTRACTOR_REWORK',lambda:p.range_rework(cur,today,False,True)),
        ('R11:SALE_MOVE_LATE_INVOICE_RETURN_INVERSE',lambda:p.late_invoice_return(cur,today)),
        ('R11:UNKNOWN_SALE_MOVE_LATE_INVOICE_RETURN_INVERSE',lambda:p.late_invoice_return(cur,today,True)),
    ]+regression.cases(cur,today)


races=regression.races
http_cases=regression.http_cases
