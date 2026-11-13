"""Conserve non-PO HPP cents in the owning SKU money composition."""
from hashlib import sha256
import json


NATIVE = 'erp.compute_non_po_product_hpp_targets_v2620f(uuid)'
CREDIT = 'cp7_credit.initial_hpp_targets_v1(uuid,uuid,jsonb,boolean)'
NATIVE_COGS = (
    "greatest(s.value+ls.value-r.value-lr.value"
    "+cp7_sku_conversion.cost_scope_value_v3(p_product_id,null,'SOLD')"
    "-cp7_sku_conversion.cost_scope_value_v3(p_product_id,null,'RETURNED'),0)"
)
ROUTES = {
    NATIVE: (
        f'round({NATIVE_COGS},2)::numeric cogs',
        f'(round(o.value+{NATIVE_COGS},2)-round(o.value,2))::numeric cogs',
        '1476efc2176ad189f15218d6217179304d1b1af3ff10cb0a6d68874205e4fc8a',
        '798c4a2959da01720c2283a29947e1f2339386d04770a5732c94bdc254b296a6',
    ),
    CREDIT: (
        'round(greatest(cogs,0),2)::numeric cogs from raw_values',
        '(case when p_po is null then round(fg+greatest(cogs,0),2)-round(fg,2) '
        'else round(greatest(cogs,0),2) end)::numeric cogs from raw_values',
        '3f60a963c752a7f3ecb53f5c35e9c1df95506ca78983ffc4fc55aeafe85a6918',
        '4b23090b8322fb7555200ad789c55757f4a29ef392c32f6dbd1c2270293a79a0',
    ),
}
ORIGINAL = 'CP7_SKU_MANAGED_RECOVERY_NATIVE27.json'
ORIGINAL_PIN = (30376182, '5e22077e71e34add6fd0627c89e9d21a2235f463818e45b233c7619bcfb0d48f')
ORIGINAL_CASE = 'SKU_NATIVE7_COST5_RACES3_PERMISSION_WAITS7_RECOVERY_BUSY1_AUTH_BROWSER4'


def source():
    return dict(
        contract='cp7.sku-non-po-cumulative-cent-rounding.v1',
        replacements={sig: dict(before_sha256=route[2], after_sha256=route[3])
                      for sig, route in ROUTES.items()},
    )


def correct(product, profile):
    """Project two SQL bodies onto an already validated PG17 catalogue."""
    definitions = dict(product['definitions'])
    rows = dict(profile['replacement_functions'])
    pins = dict(profile['derived_replacements'])
    for sig, (before, after, old_sha, new_sha) in ROUTES.items():
        definition = definitions[sig]
        if (definition != rows[sig][0] or sha256(definition.encode()).hexdigest() != old_sha
                or definition.count(before) != 1):
            raise ValueError('SKU_NON_PO_ROUNDING_EXACT_PREIMAGE_REQUIRED:' + sig)
        corrected = definition.replace(before, after, 1)
        encoded = corrected.encode()
        if sha256(encoded).hexdigest() != new_sha:
            raise ValueError('SKU_NON_PO_ROUNDING_EXACT_POSTIMAGE_REQUIRED:' + sig)
        definitions[sig] = corrected
        rows[sig] = [corrected, *rows[sig][1:]]
        pins[sig] = dict(bytes=len(encoded), sha256=new_sha)
    return (dict(product, definitions=definitions),
            dict(profile, replacement_functions=rows, derived_replacements=pins))


def bind(money):
    """Keep the original preparation checks in the private money instance."""
    retained_prepare = money.prepared
    retained_sources = money.sources

    def prepared(before, prior):
        product, profile, tables = retained_prepare(before, prior)
        product, profile = correct(product, profile)
        return product, profile, tables

    def sources():
        return dict(retained_sources(), non_po_rounding=source())

    money.prepared = prepared
    money.sources = sources


def preflight(automatic, directory):
    """Derive both layers from the pinned Native27 catalogue before DB setup."""
    path = directory / ORIGINAL
    if not path.is_file() or any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError('SKU_NON_PO_ROUNDING_EXACT_REGULAR_NATIVE27_REQUIRED')
    raw = path.read_bytes()
    if (len(raw), sha256(raw).hexdigest()) != ORIGINAL_PIN:
        raise ValueError('SKU_NON_PO_ROUNDING_NATIVE27_BYTES_CHANGED')
    catalogue = json.loads(raw)['committed'][ORIGINAL_CASE]['Native_to_copy_handoff']['raw_current_catalog']
    money = automatic.parent()
    originals = {sig: catalogue['functions'][sig][0]
                 for sig in money.prepared_product.parent_original_signatures()}
    _, profile, _ = money.prepared(catalogue, dict(originals=originals))
    functions = catalogue['functions'] | profile['groups']['functions'] | profile['replacement_functions']
    # The historical Native27 input predates the two Moving Average readers.
    # Replay the same retained source that installs them before Money at runtime.
    moving = money.parent()
    preview, _ = moving.private_delta.SIGNATURES
    position = moving.reader_access.FUNCTION
    if functions[preview] != catalogue['functions'][preview] or position in functions:
        raise ValueError('SKU_NON_PO_ROUNDING_EXACT_MOVING_PREDECESSOR_REQUIRED')
    private_originals = {sig: catalogue['functions'][sig][0] for sig in moving.private_delta.SIGNATURES}
    definitions = moving.private_delta.patched(private_originals)
    functions[preview] = [definitions[preview], *functions[preview][1:]]
    functions[position] = moving.catalog_additions.expected()['functions'][position]
    delta, additions, _ = automatic.prepared(dict(catalogue, functions=functions),
                                            dict(before=catalogue, predecessor=dict(originals=originals)))
    if ROUTES.keys() & (delta['definitions'].keys() | additions['groups']['functions'].keys()):
        raise ValueError('SKU_NON_PO_ROUNDING_AUTOMATIC_DELTA_OVERLAP')
    return dict(source=source(), original_sha256=ORIGINAL_PIN[1],
                money_replacements=len(profile['replacement_functions']),
                moving_read_predecessors=2,
                automatic_replacements=len(delta['definitions']), actual_SQL_executed=0)
