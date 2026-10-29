"""Literal, cent-exact expectation model; no product or database imports."""
from decimal import Decimal, InvalidOperation


def cents(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError('D1_CONT_EXACT_DECIMAL_REQUIRED')
    try:
        amount = Decimal(value)
    except InvalidOperation as error:
        raise ValueError('D1_CONT_EXACT_DECIMAL_REQUIRED') from error
    if not amount.is_finite() or amount * 100 != (amount * 100).to_integral_value():
        raise ValueError('D1_CONT_WHOLE_CENTS_REQUIRED')
    return amount


def profile(issued, *, applications=(), refunds=()):
    """Only this full-paid source1000 / target500 / cash1000 fixture.

    Signed UNDO restores capacity and its original AR/cash channel separately.
    No production quote, response or materialized total supplies these numbers.
    """
    issued = cents(issued)
    incoming = sum(map(cents, applications), Decimal(0))
    cash_out = sum(map(cents, refunds), Decimal(0))
    available = issued - incoming - cash_out
    source_net = Decimal('1000.00') - issued
    target_ar = Decimal('500.00') - incoming
    cash = Decimal('1000.00') - cash_out
    if not (0 <= issued <= 1000 and incoming >= 0 and cash_out >= 0
            and available >= 0 and target_ar >= 0 and cash >= 0):
        raise ValueError('D1_CONT_UNFUNDED_OR_OUTSIDE_LITERAL_FIXTURE')
    return dict(source=dict(I=format(issued, '.2f'), available=format(available, '.2f'),
                            net=format(source_net, '.2f'), AR='0.00'),
                target=dict(net='500.00', P='0.00', U=format(incoming, '.2f'),
                            I='0.00', E=format(incoming, '.2f'), AR=format(target_ar, '.2f')),
                cash=format(cash, '.2f'))


GOLD = {
    'INITIAL_200': profile('200.00'),
    'D1_250': profile('250.00'),
    'APPLY_220': profile('250.00', applications=('220.00',)),
    'APPLY_UNDONE': profile('250.00', applications=('220.00', '-220.00')),
    'REFUND_230': profile('250.00', refunds=('230.00',)),
    'REFUND_UNDONE': profile('250.00', refunds=('230.00', '-230.00')),
    'SECOND_D1_275': profile('275.00', applications=('220.00', '-220.00')),
}
