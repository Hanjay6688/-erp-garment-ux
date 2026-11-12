"""Adapt the closed Global authority check to the two reviewed SKU context functions."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from verify_focused_sku import AREA, CURRENT, git
from verify_terminal_sku import pin, require


ADAPTER = AREA + 'context_timezone.py'
ADAPTER_PIN = dict(bytes=4115, sha256='6f88447f2fa6d613655ef93b1f1035de6ab50809fde687e146251b5848783995')


def exact_adapter(checkout):
    path = Path(checkout) / ADAPTER
    raw = path.read_bytes()
    require(not path.is_symlink() and pin(raw) == ADAPTER_PIN
            and raw == git(checkout, 'show', CURRENT['head_sha'] + ':' + ADAPTER),
            'GLOBAL_REQUIRES_EXACT_REVIEWED_SKU_TIMEZONE_ADAPTER')
    spec = spec_from_file_location('global_exact_sku_timezone_adapter', path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def corrected_context(expected, adapter):
    """Derive the two expected rows from frozen authority, never from observed rows."""
    functions = dict(expected['functions'])
    changed = []
    for signature, _, _, before, after in adapter.REPAIRS:
        row = functions[signature]
        require(len(row) == 19 and pin(row[0].encode())['sha256'] == before
                and row[1] == 'postgres' and row[4] is True and row[12] == ['search_path=""']
                and row[18] == [['postgres', 'postgres', 'EXECUTE', False]],
                'GLOBAL_EXACT_CONTEXT_FUNCTION_PREIMAGE_REQUIRED:' + signature)
        revised = list(row)
        revised[0] = adapter.replace_one(row[0], adapter.NORMALIZED_BEFORE, adapter.NORMALIZED_AFTER, signature)
        require(pin(revised[0].encode())['sha256'] == after,
                'GLOBAL_EXACT_REPLAYED_CONTEXT_FUNCTION_REQUIRED:' + signature)
        revised[12] = row[12] + ['TimeZone=UTC']
        functions[signature] = revised
        changed.append(signature)
    require(len(changed) == len(set(changed)) == 2, 'GLOBAL_EXACTLY_TWO_CONTEXT_FUNCTIONS_REQUIRED')
    return dict(expected, functions=functions), changed


def review(actual, expected, reasons, sku_checkout):
    from review_native_authority import compare

    corrected, signatures = corrected_context(expected, exact_adapter(sku_checkout))
    reasons = dict(reasons)
    for signature in signatures:
        key = ('functions', signature)
        reasons[key] = [*reasons.get(key, []), 'reviewed_automatic_context_timezone']
    result = compare(actual, corrected, reasons)
    result.update(status='GLOBAL_FOCUSED_SKU_AUTHORITY_ROWS_MATCH' if not result['problems'] else
                  'GLOBAL_FOCUSED_SKU_AUTHORITY_DIFFERENCES', reviewed_context_functions=signatures,
                  sku_timezone_source=ADAPTER_PIN, runtime_admission=False, production_go=False)
    return result
