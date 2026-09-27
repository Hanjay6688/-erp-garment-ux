"""Targeted recheck of the corrected base-rate oracle; other gates retain prior evidence.
Not independent acceptance, commercial SKU qualification, or a stored-version-FK claim.
"""
import cp6_bd_probe as b
import cp6_bd_range_cases as ranges


def cases(cur,today):
    return [('RANGE:SAME_EFFECTIVE_BASE_RATE_MIXED_SINGLE_32_SINGLETON_27',
        lambda:ranges.same_rate(b,cur,b.case_day(today)))]
