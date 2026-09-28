"""Writer continuation of explicitly open combined CP6 scenarios."""
import cp6_bf_combined_probe as p
import cp6_bf_vendor_modes as regression
INSTALL_BF=True


def cases(cur,today):
    return [
        ('R03:SAME_SIZE_TWO_SKUS_DISTINCT_WAVES',lambda:p.same_size_two_skus(cur,today)),
        ('R06:RUNNING_PO_NEW_MEMBER_IDENTICAL_RECIPE',lambda:p.new_member_running_po(cur,today)),
        ('R06:RUNNING_PO_NEW_MEMBER_DIFFERENT_RECIPE_ATOMIC',lambda:p.new_member_running_po(cur,today,True)),
        ('R07:COMMITTED_BS_RANGE_MOVE_SAME_CONTRACTOR_REWORK',lambda:p.range_rework(cur,today)),
        ('R07:COMMITTED_BS_RANGE_MOVE_OTHER_CONTRACTOR_REWORK',lambda:p.range_rework(cur,today,True,True)),
        ('R07:UNCOMMITTED_BS_RANGE_MOVE_SAME_CONTRACTOR_REWORK',lambda:p.range_rework(cur,today,False,False)),
        ('R07:UNCOMMITTED_BS_RANGE_MOVE_OTHER_CONTRACTOR_REWORK',lambda:p.range_rework(cur,today,False,True)),
        ('R11:SALE_MOVE_LATE_INVOICE_RETURN_INVERSE',lambda:p.late_invoice_return(cur,today)),
        ('R11:UNKNOWN_SALE_MOVE_LATE_INVOICE_RETURN_INVERSE',lambda:p.late_invoice_return(cur,today,True)),
        ('R08:MULTI_SKU_UNIDENTIFIED_BS_NO_GUESSED_ENTITLEMENT',lambda:p.unknown_bs_scope(cur,today)),
        ('R09:COMMERCIAL_CONVERSION_EXACT_SIZE_INVERSE',lambda:p.commercial_selectors(cur,today)),
        ('R12:HISTORICAL_IMPORT_MEMBERSHIP_AND_PHYSICAL_VERSIONS',lambda:p.historical_import_identity(cur,today)),
        ('R13:PARTIAL_BS_REPEAT_WASH_PACKAGE_CORRECTION_CREDIT',lambda:p.partial_attempts_credit(cur,today)),
        ('R14:HPP_LOCATIONS_ZERO_MEMBER_PENDING_INVOICE_INVERSE',lambda:p.hpp_locations_pending(cur,today)),
    ]+regression.cases(cur,today)


races=regression.races
http_cases=regression.http_cases
