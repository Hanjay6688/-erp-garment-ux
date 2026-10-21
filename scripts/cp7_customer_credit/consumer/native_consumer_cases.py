"""Bounded9 consumer expectations plus9 cash-refund expectations.

Case registration performs no SQL. In particular the historical correction
case proves an unsafe actual intent is refused, not a successful correction.
"""
import native_basic_cases as basic
import native_refund_cases as refund

fixture=basic.fixture
IDS=basic.IDS+refund.IDS
assert len(IDS)==len(set(IDS))==18


def cases(cur,today):
    return basic.cases(cur,today)+refund.cases(cur,today)
