"""Only current-parent interfaces change; every private SQL body is retained."""
from hashlib import sha256

ORIGINAL_PIN = dict(bytes=7275, sha256='384bb580a937ce031973e257b7b992a58525a3d29e317e306d7428ab550d089d')
CONTRACT = 'cp7.sku-automatic-on-current-mandor-money.v5'
REPLACEMENTS = (
    ('from cp7_sku_cost_components import composition as money_parent, prepared_product as money_product',
     'from cp7_sku_cost_components import prepared_product as money_product\nmoney_parent = _CURRENT_MONEY_PARENT'),
    ("CONTRACT = 'cp7.sku-automatic-pending.v5'", "CONTRACT = '" + CONTRACT + "'"),
    ('return dict(contract=CONTRACT, predecessor=parent().sources(),',
     'return dict(contract=CONTRACT, predecessor=parent().sources(), current_parent_bridge=_BRIDGE_SOURCES(),'),
    ("    return catalog.digest(dict(sources=prior['sources'], before=prior['before'], after=prior['after'],\n"
     "                               parent_binding=prior['parent_binding'], definitions=prior['definitions'],\n"
     "                               originals=prior['originals'], preinstall=prior['preinstall_data_and_sequences'],\n"
     "                               preuse=prior['preuse_data_and_sequences'], proof=proof))",
     "    return catalog.digest(dict(complete_current_money_parent=prior, verified_parent_proof=proof,\n"
     "                               contract='cp7.current-automatic-complete-parent-state.v1'))"),
    ('        before, data = catalog._catalog_rows(cur), catalog._data(cur)\n',
     '        before, data = catalog._catalog_rows(cur), catalog._data(cur)\n'
     "        if before != prior['after']:\n"
     "            raise ValueError('SKU_AUTOMATIC_COMPLETE_CURRENT_PARENT_CATALOGUE_REQUIRED')\n"),
)


def derive(raw):
    if dict(bytes=len(raw), sha256=sha256(raw).hexdigest()) != ORIGINAL_PIN:
        raise ValueError('SKU_AUTOMATIC_EXACT_ORIGINAL_INSTALLER_REQUIRED')
    text = raw.decode()
    for before, after in REPLACEMENTS:
        if text.count(before) != 1 or after in text:
            raise ValueError('SKU_AUTOMATIC_EXACT_CURRENT_PARENT_ROUTE_REQUIRED')
        text = text.replace(before, after, 1)
    restored = text
    for before, after in reversed(REPLACEMENTS):
        if restored.count(after) != 1:
            raise ValueError('SKU_AUTOMATIC_EXACT_INVERSE_ROUTE_REQUIRED')
        restored = restored.replace(after, before, 1)
    if restored.encode() != raw:
        raise ValueError('SKU_AUTOMATIC_ORIGINAL_INSTALLER_NOT_RECOVERED')
    compile(text, 'current-parent-automatic-installer', 'exec')
    return text, dict(original=ORIGINAL_PIN, derived=sha256(text.encode()).hexdigest(),
                      exact_routes=5, original_recovered_exactly=True,
                      original_SQL_and_inverse_bodies_unchanged=True,
                      actual_ERP_cases=0, production_go=False)
