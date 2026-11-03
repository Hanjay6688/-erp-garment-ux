"""Change only the monetary installer's parent interface; retain every SQL body."""
from hashlib import sha256

ORIGINAL_PIN=(6718,'7ddfc7a3b825d35146a93643b1427be04c29ed49fd5debcbada00a26718868f0')
CONTRACT='cp7.sku-cost-money-on-current-mandor.v1'
REPLACEMENTS=(
 ('from cp7_sku_moving_average import composition as moving_parent','moving_parent = _CURRENT_MOVING_PARENT'),
 ("CONTRACT='cp7.sku-cost-money.v4'","CONTRACT='"+CONTRACT+"'"),
 ('        base_and_additional_cents_conserved=True,actual_ERP_cases=0,production_go=False,independent_acceptance=False)',
  '        current_parent_bridge=_BRIDGE_SOURCES(),base_and_additional_cents_conserved=True,actual_ERP_cases=0,production_go=False,independent_acceptance=False)'),
 ("    return catalog.digest(dict(sources=prior['sources'],before=prior['before'],after=prior['after'],parent_binding=prior['parent_binding'],\n"
  "        definitions=prior['definitions'],originals=prior['originals'],preinstall=prior['preinstall_data_and_sequences'],\n"
  "        preuse=prior['preuse_data_and_sequences'],proof=proof))",
  "    return catalog.digest(dict(complete_current_moving_parent=prior,verified_parent_proof=proof,\n"
  "        contract='cp7.current-mandor-moving-money-complete-state-binding.v1'))"),
 ('        before=catalog._catalog_rows(cur);data=catalog._data(cur)\n',
  "        before=catalog._catalog_rows(cur);data=catalog._data(cur)\n"
  "        if before!=prior['after']:raise ValueError('SKU_MONEY_COMPOSITE_FULL_CURRENT_PARENT_CATALOGUE_REQUIRED')\n"),
)


def derive(raw):
    if (len(raw),sha256(raw).hexdigest())!=ORIGINAL_PIN:
        raise ValueError('SKU_MONEY_COMPOSITE_EXACT_ORIGINAL_COMPOSITION_REQUIRED')
    source=raw.decode()
    for before,after in REPLACEMENTS:
        if source.count(before)!=1 or after in source:
            raise ValueError('SKU_MONEY_COMPOSITE_EXACT_PARENT_INTERFACE_ANCHOR_REQUIRED')
        source=source.replace(before,after,1)
    compile(source,'SKU-money-current-parent-derived','exec')
    recovered=source
    for before,after in reversed(REPLACEMENTS):
        if recovered.count(after)!=1:raise ValueError('SKU_MONEY_COMPOSITE_INVERSE_ROUTE_REQUIRED')
        recovered=recovered.replace(after,before,1)
    if recovered.encode()!=raw:raise ValueError('SKU_MONEY_COMPOSITE_ORIGINAL_NOT_RECOVERED')
    return source,dict(original_bytes=len(raw),original_sha256=ORIGINAL_PIN[1],
        derived_sha256=sha256(source.encode()).hexdigest(),counted_changes=5,original_recovered_exactly=True,
        actual_Native_cases=0,production_go=False,independent_acceptance=False)
