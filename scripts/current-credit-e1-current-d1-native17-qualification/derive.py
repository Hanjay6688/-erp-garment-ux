"""Private admission routing only; all financial/oracle functions stay exact."""
from hashlib import sha256

OLD_PARENT = 'scripts/current-credit-de-native-qualification'
CURRENT_PARENT = 'scripts/current-credit-d1-product-phase-native13-qualification'
CHANGES = (
    ("old = json.loads((ROOT/'" + OLD_PARENT + "/SOURCE.json').read_bytes())",
     "old = json.loads((ROOT/'" + CURRENT_PARENT + "/SOURCE.json').read_bytes())"),
    ('prior = old.admitted(ROOT, original.parent, product.predecessor, derivation)',
     "prior = old.admitted(ROOT, ROOT/'" + CURRENT_PARENT + "', product.predecessor, derivation)"),
)


def admission(raw):
    text = raw.decode()
    for before, after in CHANGES:
        if text.count(before) != 1:
            raise ValueError('E1_CURRENT_EXACT_PRIVATE_ADMISSION_ANCHOR_REQUIRED')
        text = text.replace(before, after, 1)
    return text, dict(original_sha256=sha256(raw).hexdigest(), derived_sha256=sha256(text.encode()).hexdigest(),
        counted_source_routing_changes=2, private_HERE_relocated=True,
        retained_historical_D1_diff_endpoint_changes=1,
        all_original_current_hash_financial_parent_raw_checks_preserved=True)
