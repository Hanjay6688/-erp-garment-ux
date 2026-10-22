"""Independent exact rational/high-precision target oracle; no product imports."""
from decimal import Decimal, localcontext, ROUND_CEILING
from fractions import Fraction
import json
import random


def cases():
    rng = random.Random(20261023)
    rows = []
    for i in range(160):
        mode = 'DAYS' if i % 2 == 0 else 'STATISTICAL'
        total = rng.randint(0, 1000000)
        days = rng.randint(14, 365)
        lead = rng.choice(['0.5', '1', '3.25', '7', '14', '31.125'])
        review = rng.choice(['0', '1', '7', '14.5', '30'])
        buffer = rng.choice(['0', '0.25', '2', '7']) if mode == 'DAYS' else None
        sd = rng.choice(['0', '0.0000000000000001', '2.125', '10.6543210987654321']) if mode == 'STATISTICAL' else None
        level = rng.choice(['0.90', '0.95', '0.99']) if mode == 'STATISTICAL' else None
        value = dict(contract_version='cp7.target-input.v2', snapshot_id='oracle-snapshot', scope_id='oracle-scope', mode=mode,
                     daily_total_pcs=str(total), counted_days=str(days), daily_sd=sd, lead_days=lead, review_days=review,
                     buffer_days=buffer, service_level=level, refs=[dict(kind='SYNTHETIC_TEST_ONLY', id=str(i), revision='1')])
        if mode == 'DAYS':
            ceil = lambda q: -(-q.numerator // q.denominator)
            low = ceil(Fraction(total, days) * (Fraction(lead) + Fraction(buffer)))
            high = ceil(Fraction(total, days) * (Fraction(lead) + Fraction(review) + Fraction(buffer)))
        else:
            with localcontext() as ctx:
                ctx.prec = 80
                z = {'0.90': Decimal('1.2816'), '0.95': Decimal('1.6449'), '0.99': Decimal('2.3263')}[level]
                mean = Decimal(total)/Decimal(days)
                low = int((mean*Decimal(lead)+z*Decimal(sd)*Decimal(lead).sqrt()).to_integral_value(rounding=ROUND_CEILING))
                h = Decimal(lead)+Decimal(review)
                high = int((mean*h+z*Decimal(sd)*h.sqrt()).to_integral_value(rounding=ROUND_CEILING))
        rows.append(dict(input=value, expected=dict(reorder_point_pcs=str(low), target_pcs=str(high))))
    value = dict(rows[0]['input'], daily_total_pcs='230', counted_days='30', lead_days='3', review_days='0', buffer_days='0')
    rows.append(dict(input=value, expected=dict(reorder_point_pcs='23', target_pcs='23')))
    value = dict(rows[0]['input'], daily_total_pcs='1', counted_days='3', lead_days='3.000000000001', review_days='0', buffer_days='0')
    rows.append(dict(input=value, expected=dict(reorder_point_pcs='2', target_pcs='2')))
    # A measured lead can legitimately round to zero days. A zero horizon is
    # known, unlike a missing lead; DAYS still retains its one explicit buffer.
    for buffer, review, low, high in [('0', '0', '0', '0'), ('2', '0', '20', '20'), ('2', '7', '20', '90')]:
        value = dict(rows[0]['input'], daily_total_pcs='30', counted_days='3', lead_days='0', review_days=review, buffer_days=buffer)
        rows.append(dict(input=value, expected=dict(reorder_point_pcs=low, target_pcs=high)))
    for level in ['0.90', '0.95', '0.99']:
        value = dict(rows[1]['input'], daily_total_pcs='300', counted_days='30', lead_days='0', review_days='0',
                     daily_sd='10', service_level=level)
        rows.append(dict(input=value, expected=dict(reorder_point_pcs='0', target_pcs='0')))
    return rows


if __name__ == '__main__':
    print(json.dumps(cases()))
