"""A narrow parent-interface derivation; no SQL, import, or connection here."""
from hashlib import sha256

ORIGINAL_SHA256 = "da1f275fa0e91ecbbaa5bcedff65ba0391b162108cc9e91b98a5e2c9f746465f"
CONTRACT = "cp7.sku-moving-average-on-current-mandor.v1"
REPLACEMENTS = (
    ("import cp7_sku_pair_conversion.composition as sku_parent", "sku_parent = _CURRENT_PARENT"),
    ("CONTRACT='cp7.sku-moving-average.v2'", "CONTRACT='" + CONTRACT + "'"),
    ("        actual_SQL=0,production_go=False,independent_acceptance=False)",
     "        current_parent_bridge=_BRIDGE_SOURCES(),actual_SQL=0,production_go=False,independent_acceptance=False)"),
    ("    return catalog.digest(dict(sources=prior['sources'],before=prior['before'],after=prior['after'],\n"
     "        parent_binding=prior['parent_binding'],definitions=prior['definitions'],originals=prior['originals'],\n"
     "        preinstall=prior['preinstall_data_and_sequences'],preuse=prior['preuse_data_and_sequences'],proof=proof))",
     "    return catalog.digest(dict(complete_current_parent=prior,verified_parent_proof=proof,\n"
     "        contract='cp7.current-mandor-complete-state-binding.v1'))"),
    ("        before=catalog._catalog_rows(cur);data=catalog._data(cur)\n",
     "        before=catalog._catalog_rows(cur);data=catalog._data(cur)\n"
     "        if before!=prior['after']:raise ValueError('SKU_COMPOSITE_FULL_CURRENT_PARENT_CATALOGUE_REQUIRED')\n"),
    ("preinstall_data_and_sequences=prior['preinstall_data_and_sequences'])",
     "preinstall_data_and_sequences=prior['parent']['preinstall_data_and_sequences'])"),
)


def derive(raw):
    if sha256(raw).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("SKU_COMPOSITE_EXACT_ORIGINAL_COMPOSITION_REQUIRED")
    source = raw.decode()
    for before, after in REPLACEMENTS:
        if source.count(before) != 1:
            raise ValueError("SKU_COMPOSITE_EXACT_PARENT_INTERFACE_ANCHOR_REQUIRED")
        source = source.replace(before, after, 1)
    compile(source, "SKU-current-parent-derived", "exec")
    recovered = source
    for before, after in reversed(REPLACEMENTS):
        if recovered.count(after) != 1:
            raise ValueError("SKU_COMPOSITE_REVERSIBLE_SOURCE_DERIVATION_REQUIRED")
        recovered = recovered.replace(after, before, 1)
    if recovered.encode() != raw:
        raise ValueError("SKU_COMPOSITE_ORIGINAL_RECOVERY_REQUIRED")
    return source, dict(original_sha256=ORIGINAL_SHA256,
                       derived_sha256=sha256(source.encode()).hexdigest(),
                       counted_changes=len(REPLACEMENTS), original_recovered_exactly=True,
                       actual_Native_cases=0, production_go=False)
