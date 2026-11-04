"""Append current economic observations to the complete retained Native body.

The actual owning runtime must bind the original observer to the current
product first. No connection is opened and no fixture is created here.
"""


def observe(original, cur, fixture, label):
    value = original(cur, fixture, label)
    if 'current_economic_pools' in value:
        raise ValueError('CURRENT_SKU_ECONOMIC_OBSERVATION_MUST_NOT_REPLACE_ORIGINAL_FIELDS')
    pools = {product: cur.execute(
        "select cp7_sku_conversion.pool_quote_v2(%s,%s,'GRADE_A')",
        (product, fixture['location'])).fetchone()[0]
        for product in (fixture['source'], fixture['target'])}
    return dict(value, current_economic_pools=pools)
